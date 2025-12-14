from datetime import datetime
from typing import List, Optional

from config.app_logger import logger
from config.postgresql import db


def create_vehicle(user_id: int, vehicle_data: dict) -> Optional[int]:
    """Create a new vehicle for a user"""
    try:
        query = """
            INSERT INTO vehicles (
                user_id, vehicle_type, make, model, color,
                license_plate, max_capacity, created_at, is_active
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        params = (
            user_id,
            vehicle_data['vehicle_type'],
            vehicle_data.get('make'),
            vehicle_data.get('model'),
            vehicle_data.get('color'),
            vehicle_data['license_plate'],
            vehicle_data['max_capacity'],
            datetime.now(),
            True
        )

        vehicle_id = db.execute_insert_query(query, params, return_id=True)
        logger.info(f"Vehicle created: id={vehicle_id}, user={user_id}")
        return vehicle_id
    except Exception as e:
        logger.error(f"Error creating vehicle: {e}", exc_info=True)
        return None


def get_user_vehicles(user_id: int) -> List[dict]:
    """Get all active vehicles for a user"""
    try:
        query = """
            SELECT
                id, user_id, vehicle_type, make, model, color,
                license_plate, max_capacity, created_at
            FROM vehicles
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY created_at DESC
        """
        results = db.execute_select_query(query, (user_id,))

        formatted = []
        for v in results:
            formatted.append({
                "id": v['id'],
                "vehicle_type": v['vehicle_type'],
                "make": v['make'],
                "model": v['model'],
                "color": v['color'],
                "license_plate": v['license_plate'],
                "max_capacity": v['max_capacity'],
                "created_at": v['created_at'].strftime("%d %B %Y") if v['created_at'] else None
            })
        return formatted
    except Exception as e:
        logger.error(f"Error getting user vehicles: {e}", exc_info=True)
        return []


def get_vehicle_by_id(vehicle_id: int) -> Optional[dict]:
    """Get a specific vehicle by ID"""
    try:
        query = """
            SELECT
                id, user_id, vehicle_type, make, model, color,
                license_plate, max_capacity, created_at, is_active
            FROM vehicles
            WHERE id = %s AND is_active = TRUE
        """
        results = db.execute_select_query(query, (vehicle_id,))

        if results:
            v = results[0]
            return {
                "id": v['id'],
                "user_id": v['user_id'],
                "vehicle_type": v['vehicle_type'],
                "make": v['make'],
                "model": v['model'],
                "color": v['color'],
                "license_plate": v['license_plate'],
                "max_capacity": v['max_capacity'],
                "created_at": v['created_at'].strftime("%d %B %Y") if v['created_at'] else None
            }
        return None
    except Exception as e:
        logger.error(f"Error getting vehicle: {e}", exc_info=True)
        return None


def update_vehicle(vehicle_id: int, updates: dict) -> bool:
    """Update a vehicle"""
    try:
        if not updates:
            return False

        # Build dynamic SET clause
        set_clauses = []
        params = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            params.append(value)

        set_clauses.append("updated_at = NOW()")
        params.append(vehicle_id)

        query = f"""
            UPDATE vehicles
            SET {', '.join(set_clauses)}
            WHERE id = %s
        """

        db.execute_update_query(query, tuple(params))
        logger.info(f"Vehicle {vehicle_id} updated: {list(updates.keys())}")
        return True
    except Exception as e:
        logger.error(f"Error updating vehicle: {e}", exc_info=True)
        return False


def delete_vehicle(vehicle_id: int) -> bool:
    """Soft delete a vehicle"""
    try:
        query = """
            UPDATE vehicles
            SET is_active = FALSE, updated_at = NOW()
            WHERE id = %s
        """
        db.execute_update_query(query, (vehicle_id,))
        logger.info(f"Vehicle {vehicle_id} deleted (soft)")
        return True
    except Exception as e:
        logger.error(f"Error deleting vehicle: {e}", exc_info=True)
        return False
