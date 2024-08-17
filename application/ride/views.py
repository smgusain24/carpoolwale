from fastapi.requests import Request

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator, ValidationError, Field
from datetime import datetime
from typing import List, Tuple, Optional

from starlette.responses import JSONResponse

from application.common import epoch_to_datetime
from application.ride.models import Ride
from config.app_logger import logger
from config.auth import access_token_required
from config.http_status import HTTP_200_OK, HTTP_500_INTERNAL_SERVER_ERROR
from application.constants import _VERSION

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
            status_code=HTTP_200_OK
        )
        return login_response
    except Exception as e:
        logger.error(e, exc_info=True)
        return JSONResponse(
            content={
                "err": str(e)
            },
            status_code=HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/request_ride")
@access_token_required
async def request_ride(request: Request):
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

    return {"msg": "Ride requested successfully", "ride_id": ride.ride_id}