import json
from email.policy import default

from fastapi.requests import Request

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator, ValidationError, Field
from datetime import datetime, timedelta, time
from typing import List, Tuple, Optional

from starlette.responses import JSONResponse
from starlette import status

from application.common import epoch_to_datetime
from application.ride.models import Ride
from config.app_logger import logger
from config.auth import access_token_required
from application.constants import _VERSION
from config.mongo_db import fetch_documents

router = APIRouter(prefix=f"/{_VERSION}/rides", tags=["Rides"])

class RideDetails(BaseModel):
    origin: Tuple[float, float]
    destination: Tuple[float, float]
    available_seats: int
    cost_per_seat: float
    additional_note: Optional[str] = None
    additional_stop: Optional[List[tuple[float, float]]] = None
    start_datetime: datetime
    end_datetime: datetime



@router.post("/publish_ride")
@access_token_required
async def publish_ride(request: Request):
    """
    Publish a ride by creating a new ride document in the database with the provided data.

    Parameters:
    - `request` (Request): The incoming request object.

    Returns:
    - (JSONResponse): A JSON response containing a success message and the ID of the published ride.
                      The status code is 200 (OK).

    Raises:
    - `HTTPException`: If the user is not authenticated.
                        If there is a validation error in the input data.
    - `Exception`: If there is an error in creating the ride or publishing it.
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        data = await request.json()

        try:
            data['start_datetime'], data['end_datetime'] = (epoch_to_datetime(data['start_datetime']),
                                                            epoch_to_datetime(data['end_datetime']))
            ride_data = RideDetails(**data)  # Use Pydantic for validation
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        ride = Ride.create_for_driver(
            driver=current_user,
            **ride_data.model_dump()  # Extract data from validated model
        )

        await ride.create_ride()
        login_response = JSONResponse(
            content={
                "msg": "Ride published successfully",
                "ride_id": ride.ride_id
            },
            status_code=status.HTTP_200_OK
        )
        return login_response
    except Exception as e:
        logger.error(e, exc_info=True)
        return JSONResponse(
            content={
                "err": str(e)
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/request_ride")
@access_token_required
async def request_ride(request: Request):
    """
    Request to join a ride.

    Parameters:
    - `request` (Request): The incoming request object.

    Returns:
    - (dict): A dictionary containing a message and the ride ID. The message is "Ride requested successfully"
              and the ride ID is the ID of the ride that was requested.

    Raises:
    - `HTTPException`: If the user is not authenticated or the ride is no longer active or has been cancelled.
                        If the request to join the ride is not successful.
    """
    current_user = request.state.user_details
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    ride = Ride.create_for_rider(ride_id=request['ride_id'])

    if not ride.is_active or ride.is_cancelled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Ride is no longer active or has been cancelled")

    success = ride.request_ride(passenger=current_user)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Unable to request ride. It might be full or inactive.")

    return JSONResponse(
        content={"msg": "Ride requested successfully", "ride_id": ride.ride_id},
        status_code=status.HTTP_201_CREATED
    )


@router.get("/view_rides")
@access_token_required
async def view_rides(request: Request):
    """
    View rides available for a given date, origin, destination and vicinity.

    Parameters:
        request (Request): The incoming request object.

    Returns:
        JSONResponse: A JSON response containing the list of rides.
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        data =  dict(request.query_params)
        # Convert epoch time to datetime object
        date: datetime = epoch_to_datetime(int(data['epoch_date'])).date()
        # Convert origin and destination to list of latitude and longitude
        origin: List[float, float] = json.loads(data['origin'])
        destination: List[float, float] = json.loads(data['destination'])
        # Convert vicinity to integer
        vicinity: int = int(data.get('vicinity', 10))

        # Calculate maximum radius in radians
        max_radius_in_radians = vicinity / 6378.1

        # Create filters for origin, destination and start_datetime

        filters = {
            "origin": {
                "$geoWithin": {
                    "$centerSphere": [origin, max_radius_in_radians]
                }
            },
            "destination": {
                "$geoWithin": {
                    "$centerSphere": [destination, max_radius_in_radians]
                }
            },
            "start_datetime": {
                "$gte": datetime.combine(date, time.min) if date != date.today() else datetime.now(),
                "$lt": datetime.combine(date + timedelta(days=1), time.min)
            },
            "is_active": 1
        }

        projection = ['_id', 'ride_id',  'publisher_id', 'origin', 'destination', 'start_datetime',
                      'end_datetime', 'available_seats', 'cost_per_seat']
        # Fetch rides from the database
        rides = fetch_documents(
            collection_name="rides",
            filter_query=filters,
            sort_by=[("start_datetime", 1)],
            limit=10,
            projection=projection
        )

        for ride in rides:
            ride['_id'] = str(ride['_id'])
            ride['start_datetime'] = ride['start_datetime'].strftime("%d %B %Y")
            ride['end_datetime'] = ride['end_datetime'].strftime("%d %B %Y")

        # Return the list of rides
        return JSONResponse(content=rides, status_code=status.HTTP_200_OK)

    except Exception as e:
        logger.error(e, exc_info=True)
        return JSONResponse(content={"error": "Internal server error"},
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

