import json
from datetime import datetime, timedelta, time
from typing import List

from fastapi.requests import Request
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from starlette.responses import JSONResponse
from starlette import status

from application.common import epoch_to_datetime
from application.ride.models import Ride, RideCreate, RideRequest, RideRequestAction
from application.vehicles.utilities import get_vehicle_by_id
from config.app_logger import logger
from config.auth import access_token_required
from application.constants import _VERSION

router = APIRouter(prefix=f"/{_VERSION}/rides", tags=["Rides"])



@router.post("/publish_ride")
@access_token_required
async def publish_ride(request: Request):
    """
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
            ride_data = RideCreate(**data)  # Use Pydantic for validation
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        # Validate vehicle ownership if vehicle_id is provided
        if ride_data.vehicle_id:
            vehicle = get_vehicle_by_id(ride_data.vehicle_id)
            if not vehicle:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
            if vehicle['user_id'] != current_user['user_id']:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="You can only use your own vehicles")
            # Validate that available_seats doesn't exceed vehicle capacity
            if ride_data.available_seats > vehicle['max_capacity']:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Available seats ({ride_data.available_seats}) exceeds vehicle capacity ({vehicle['max_capacity']})")

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
    - Body:
        - ride_id: The unique ride identifier
        - seats_requested: Number of seats requested (default: 1)
        - pickup_location: Optional custom pickup [lat, lng]
        - dropoff_location: Optional custom dropoff [lat, lng]

    Returns:
    - (dict): A dictionary containing a message and the ride ID.

    Raises:
    - `HTTPException`: If the user is not authenticated or the ride is no longer active or has been cancelled.
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        data = await request.json()
        try:
            request_data = RideRequest(**data)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        # Fetch the ride from database
        ride = Ride.fetch_by_ride_id(request_data.ride_id)

        if not ride:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")

        if not ride['is_active'] or ride['is_cancelled']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Ride is no longer active or has been cancelled")

        if ride['available_seats'] < request_data.seats_requested:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Only {ride['available_seats']} seats available")

        # Check if user already requested this ride
        if Ride.has_user_requested(ride['id'], current_user['user_id']):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You have already requested this ride")

        # Prevent driver from requesting their own ride
        if str(ride['publisher_id']) == str(current_user['user_id']):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="You cannot request your own ride")

        # Insert ride request
        success = Ride.insert_ride_request(
            ride_db_id=ride['id'],
            passenger_id=current_user['user_id'],
            seats_requested=request_data.seats_requested,
            pickup_location=request_data.pickup_location,
            dropoff_location=request_data.dropoff_location
        )

        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Failed to request ride")

        return JSONResponse(
            content={"msg": "Ride requested successfully", "ride_id": request_data.ride_id},
            status_code=status.HTTP_201_CREATED
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/view_rides")
@access_token_required
async def view_rides(request: Request):
    """
    View rides available for a given date, origin, destination and vicinity.

    Parameters:
        request (Request): The incoming request object.
        Query params:
            - epoch_date: Date in epoch format
            - origin: JSON [lat, lng]
            - destination: JSON [lat, lng]
            - vicinity: Radius in km (default: 10, max: 100)
            - page: Page number (default: 1)
            - per_page: Items per page (default: 20, max: 100)

    Returns:
        JSONResponse: A JSON response containing the list of rides with pagination.
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        data = dict(request.query_params)

        # Convert epoch time to datetime object
        date = epoch_to_datetime(int(data['epoch_date'])).date()

        # Convert origin and destination to list of latitude and longitude
        origin: List[float] = json.loads(data['origin'])
        destination: List[float] = json.loads(data['destination'])

        # Validate coordinates
        if len(origin) != 2 or len(destination) != 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Origin and destination must be [lat, lng] arrays")

        origin_lat, origin_lng = origin[0], origin[1]
        dest_lat, dest_lng = destination[0], destination[1]

        # Validate latitude (-90 to 90) and longitude (-180 to 180)
        if not (-90 <= origin_lat <= 90) or not (-180 <= origin_lng <= 180):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid origin coordinates")
        if not (-90 <= dest_lat <= 90) or not (-180 <= dest_lng <= 180):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid destination coordinates")

        # Convert vicinity to integer (in meters for ST_DWithin)
        vicinity_km: int = min(100, max(1, int(data.get('vicinity', 10))))
        vicinity_meters = vicinity_km * 1000

        # Pagination parameters
        page = max(1, int(data.get('page', 1)))
        per_page = min(100, max(1, int(data.get('per_page', 20))))
        offset = (page - 1) * per_page

        # Build start and end datetime for the day
        start_of_day = datetime.combine(date, time.min)
        end_of_day = datetime.combine(date + timedelta(days=1), time.min)

        # Use current time if searching for today
        if date == datetime.now().date():
            start_of_day = datetime.now()

        # Base query for counting and fetching
        base_conditions = """
            FROM rides r
            JOIN users u ON r.publisher_id = u.id
            WHERE r.is_active = TRUE
              AND r.is_cancelled = FALSE
              AND r.available_seats > 0
              AND r.start_datetime >= %s
              AND r.start_datetime < %s
              AND ST_DWithin(
                  r.origin,
                  ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                  %s
              )
              AND ST_DWithin(
                  r.destination,
                  ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                  %s
              )
        """

        base_params = (
            start_of_day,
            end_of_day,
            origin_lng, origin_lat, vicinity_meters,
            dest_lng, dest_lat, vicinity_meters
        )

        # Get total count
        from config.postgresql import db
        count_query = f"SELECT COUNT(*) as total {base_conditions}"
        count_result = db.execute_select_query(count_query, base_params)
        total = count_result[0]['total'] if count_result else 0

        # Query rides using PostGIS geospatial functions
        query = f"""
            SELECT
                r.id,
                r.ride_id,
                r.publisher_id,
                ST_Y(r.origin::geometry) as origin_lat,
                ST_X(r.origin::geometry) as origin_lng,
                ST_Y(r.destination::geometry) as destination_lat,
                ST_X(r.destination::geometry) as destination_lng,
                r.start_datetime,
                r.end_datetime,
                r.available_seats,
                r.cost_per_seat,
                r.additional_note,
                u.first_name,
                u.last_name
            {base_conditions}
            ORDER BY r.start_datetime ASC
            LIMIT %s OFFSET %s
        """

        params = base_params + (per_page, offset)
        rides = db.execute_select_query(query, params)

        # Format the response
        formatted_rides = []
        for ride in rides:
            formatted_rides.append({
                "id": ride['id'],
                "ride_id": ride['ride_id'],
                "publisher_id": ride['publisher_id'],
                "driver_name": f"{ride['first_name']} {ride['last_name']}",
                "origin": [ride['origin_lat'], ride['origin_lng']],
                "destination": [ride['destination_lat'], ride['destination_lng']],
                "start_datetime": ride['start_datetime'].strftime("%d %B %Y, %H:%M"),
                "end_datetime": ride['end_datetime'].strftime("%d %B %Y, %H:%M"),
                "available_seats": ride['available_seats'],
                "cost_per_seat": float(ride['cost_per_seat']),
                "additional_note": ride['additional_note']
            })

        return JSONResponse(
            content={
                "items": formatted_rides,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page if total > 0 else 0
            },
            status_code=status.HTTP_200_OK
        )

    except KeyError as e:
        logger.error(f"Missing required parameter: {e}", exc_info=True)
        return JSONResponse(
            content={"error": f"Missing required parameter: {str(e)}"},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except ValueError:
        return JSONResponse(
            content={"error": "Invalid parameter values"},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/my_rides")
@access_token_required
async def my_rides(request: Request):
    """
    Get all rides published by the current user (as driver).

    Query params:
        - status: 'active', 'completed', 'cancelled', or 'all' (default: 'active')
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        data = dict(request.query_params)
        ride_status = data.get('status', 'active')
        page = max(1, int(data.get('page', 1)))
        per_page = min(100, max(1, int(data.get('per_page', 20))))

        result = Ride.get_user_rides(current_user['user_id'], ride_status, page, per_page)

        return JSONResponse(content=result, status_code=status.HTTP_200_OK)

    except ValueError:
        return JSONResponse(
            content={"error": "Invalid pagination parameters"},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/my_bookings")
@access_token_required
async def my_bookings(request: Request):
    """
    Get all rides where the current user is a passenger (requested/confirmed).

    Query params:
        - status: 'pending', 'confirmed', 'rejected', 'cancelled', or 'all' (default: 'all')
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        data = dict(request.query_params)
        booking_status = data.get('status', 'all')
        page = max(1, int(data.get('page', 1)))
        per_page = min(100, max(1, int(data.get('per_page', 20))))

        result = Ride.get_user_bookings(current_user['user_id'], booking_status, page, per_page)

        return JSONResponse(content=result, status_code=status.HTTP_200_OK)

    except ValueError:
        return JSONResponse(
            content={"error": "Invalid pagination parameters"},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/ride_requests/{ride_id}")
@access_token_required
async def get_ride_requests(request: Request, ride_id: str):
    """
    Get all passenger requests for a specific ride (driver only).
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        # Verify the user is the driver of this ride
        ride = Ride.fetch_by_ride_id(ride_id)
        if not ride:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")

        if str(ride['publisher_id']) != str(current_user['user_id']):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not authorized to view requests for this ride")

        requests = Ride.get_ride_requests(ride['id'])

        return JSONResponse(content={"requests": requests}, status_code=status.HTTP_200_OK)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/respond_request")
@access_token_required
async def respond_to_request(request: Request):
    """
    Accept or reject a ride request (driver only).

    Body:
        - request_id: The ride request ID
        - action: 'accept' or 'reject'
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        data = await request.json()
        try:
            action_data = RideRequestAction(**data)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        # Get the request details
        ride_request = Ride.get_request_by_id(action_data.request_id)
        if not ride_request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

        # Verify the user is the driver of this ride
        ride = Ride.fetch_by_db_id(ride_request['ride_id'])
        if not ride:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")

        if str(ride['publisher_id']) != str(current_user['user_id']):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not authorized to respond to this request")

        if ride_request['status'] != 'pending':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Request has already been {ride_request['status']}")

        # Check seats availability for acceptance
        if action_data.action == 'accept':
            if ride['available_seats'] < ride_request['seats_requested']:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Not enough seats available. Only {ride['available_seats']} left.")

            success = Ride.accept_ride_request(action_data.request_id, ride['id'], ride_request['seats_requested'])
        else:
            success = Ride.reject_ride_request(action_data.request_id)

        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Failed to {action_data.action} request")

        return JSONResponse(
            content={"msg": f"Request {action_data.action}ed successfully"},
            status_code=status.HTTP_200_OK
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/cancel_ride")
@access_token_required
async def cancel_ride(request: Request):
    """
    Cancel a ride (driver only).

    Body:
        - ride_id: The unique ride identifier
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        data = await request.json()
        ride_id = data.get('ride_id')

        if not ride_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ride_id is required")

        # Verify the user is the driver
        ride = Ride.fetch_by_ride_id(ride_id)
        if not ride:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")

        if str(ride['publisher_id']) != str(current_user['user_id']):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not authorized to cancel this ride")

        if ride['is_cancelled']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Ride is already cancelled")

        success = Ride.cancel_ride(ride['id'])

        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Failed to cancel ride")

        return JSONResponse(
            content={"msg": "Ride cancelled successfully"},
            status_code=status.HTTP_200_OK
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/cancel_booking")
@access_token_required
async def cancel_booking(request: Request):
    """
    Cancel a ride booking (passenger only).

    Body:
        - request_id: The ride request ID
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        data = await request.json()
        request_id = data.get('request_id')

        if not request_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="request_id is required")

        # Get the request
        ride_request = Ride.get_request_by_id(request_id)
        if not ride_request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

        # Verify the user is the passenger
        if str(ride_request['passenger_id']) != str(current_user['user_id']):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not authorized to cancel this booking")

        if ride_request['status'] == 'cancelled':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Booking is already cancelled")

        # If it was confirmed, restore the seats
        seats_to_restore = ride_request['seats_requested'] if ride_request['status'] == 'confirmed' else 0

        success = Ride.cancel_booking(request_id, ride_request['ride_id'], seats_to_restore)

        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Failed to cancel booking")

        return JSONResponse(
            content={"msg": "Booking cancelled successfully"},
            status_code=status.HTTP_200_OK
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
