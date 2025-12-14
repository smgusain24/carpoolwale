from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from starlette import status

from application.vehicles.models import VehicleCreate, VehicleUpdate
from application.vehicles.utilities import (
    create_vehicle, get_user_vehicles, get_vehicle_by_id,
    update_vehicle, delete_vehicle
)
from config.app_logger import logger
from config.auth import access_token_required
from application.constants import _VERSION

router = APIRouter(prefix=f"/{_VERSION}/vehicles", tags=["Vehicles"])


@router.post("/add")
@access_token_required
async def add_vehicle(request: Request):
    """
    Add a new vehicle for the current user.

    Body:
        - vehicle_type: Type of vehicle (car, bike, etc.)
        - make: Vehicle manufacturer (optional)
        - model: Vehicle model (optional)
        - color: Vehicle color (optional)
        - license_plate: License plate number (required)
        - max_capacity: Maximum passenger capacity (required)
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        data = await request.json()
        try:
            vehicle_data = VehicleCreate(**data)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        vehicle_id = create_vehicle(
            user_id=current_user['user_id'],
            vehicle_data=vehicle_data.model_dump()
        )

        if vehicle_id:
            return JSONResponse(
                content={"msg": "Vehicle added successfully", "vehicle_id": vehicle_id},
                status_code=status.HTTP_201_CREATED
            )
        else:
            return JSONResponse(
                content={"msg": "Failed to add vehicle"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/list")
@access_token_required
async def list_vehicles(request: Request):
    """
    Get all vehicles for the current user.
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        vehicles = get_user_vehicles(current_user['user_id'])

        return JSONResponse(
            content={"vehicles": vehicles},
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(e, exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/{vehicle_id}")
@access_token_required
async def get_vehicle(request: Request, vehicle_id: int):
    """
    Get a specific vehicle by ID.
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        vehicle = get_vehicle_by_id(vehicle_id)

        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

        # Verify ownership
        if vehicle['user_id'] != current_user['user_id']:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not authorized to view this vehicle")

        return JSONResponse(
            content={"vehicle": vehicle},
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


@router.put("/{vehicle_id}")
@access_token_required
async def update_vehicle_endpoint(request: Request, vehicle_id: int):
    """
    Update a vehicle.

    Body (all optional):
        - vehicle_type
        - make
        - model
        - color
        - license_plate
        - max_capacity
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        # Verify ownership
        vehicle = get_vehicle_by_id(vehicle_id)
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

        if vehicle['user_id'] != current_user['user_id']:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not authorized to update this vehicle")

        data = await request.json()
        try:
            update_data = VehicleUpdate(**data)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        # Filter out None values
        updates = {k: v for k, v in update_data.model_dump().items() if v is not None}

        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="No fields to update")

        success = update_vehicle(vehicle_id, updates)

        if success:
            return JSONResponse(
                content={"msg": "Vehicle updated successfully"},
                status_code=status.HTTP_200_OK
            )
        else:
            return JSONResponse(
                content={"msg": "Failed to update vehicle"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete("/{vehicle_id}")
@access_token_required
async def delete_vehicle_endpoint(request: Request, vehicle_id: int):
    """
    Delete a vehicle (soft delete).
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        # Verify ownership
        vehicle = get_vehicle_by_id(vehicle_id)
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

        if vehicle['user_id'] != current_user['user_id']:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You are not authorized to delete this vehicle")

        success = delete_vehicle(vehicle_id)

        if success:
            return JSONResponse(
                content={"msg": "Vehicle deleted successfully"},
                status_code=status.HTTP_200_OK
            )
        else:
            return JSONResponse(
                content={"msg": "Failed to delete vehicle"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
