from typing import List, Optional, Tuple
from datetime import datetime
import hashlib

from pydantic import BaseModel
from config.app_logger import logger
from config.postgresql import db


# Pydantic models for request/response validation
class RideCreate(BaseModel):
    origin: Tuple[float, float]
    destination: Tuple[float, float]
    available_seats: int
    cost_per_seat: float
    additional_note: Optional[str] = None
    additional_stop: Optional[List[Tuple[float, float]]] = None
    start_datetime: datetime
    end_datetime: datetime


class RideRequest(BaseModel):
    ride_id: str
    seats_requested: int = 1
    pickup_location: Optional[Tuple[float, float]] = None
    dropoff_location: Optional[Tuple[float, float]] = None


class RideRequestAction(BaseModel):
    request_id: int
    action: str  # 'accept' or 'reject'


# Database operations class
class Ride:
    def __init__(
        self,
        driver: dict,  # Optional: Set if the user is the driver
        origin: Tuple[float, float] ,  # Coordinates of origin (lat, long)
        destination: Tuple[float, float],  # Coordinates of destination (lat, long)
        start_datetime: datetime,  # Start date-time
        end_datetime: datetime,  # Estimated end date-time
        available_seats: int = 0,  # Number of seats available
        cost_per_seat: float = 0.0,  # Cost per seat charged
        additional_note: str = "",  # Additional note
        additional_stop: List[Optional[Tuple[float, float]]] = () ,  # List of coordinates of additional stops
        ride_id: str = None  # Optional: Used when a rider is requesting or viewing a ride
    ):
        self.driver = driver
        self.origin = origin
        self.destination = destination
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime
        self.available_seats = available_seats
        self.cost_per_seat = cost_per_seat
        self.passengers = []
        self.additional_note = additional_note
        self.additional_stop = additional_stop
        self.is_active = True
        self.is_cancelled = False
        self.ride_id = ride_id

    @classmethod
    def create_for_driver(cls, driver, origin, destination, start_datetime, end_datetime, available_seats,
                          cost_per_seat, additional_note="", additional_stop=None):
        return cls(
            driver=driver,
            origin=origin,
            destination=destination,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            available_seats=available_seats,
            cost_per_seat=cost_per_seat,
            additional_note=additional_note,
            additional_stop=additional_stop
        )

    @staticmethod
    def fetch_by_ride_id(ride_id: str) -> Optional[dict]:
        """Fetch ride details from database by ride_id"""
        query = """
            SELECT
                id, ride_id, publisher_id,
                ST_Y(origin::geometry) as origin_lat,
                ST_X(origin::geometry) as origin_lng,
                ST_Y(destination::geometry) as destination_lat,
                ST_X(destination::geometry) as destination_lng,
                start_datetime, end_datetime,
                available_seats, cost_per_seat, additional_note,
                is_active, is_cancelled, vehicle_id
            FROM rides
            WHERE ride_id = %s
        """
        results = db.execute_select_query(query, (ride_id,))
        return results[0] if results else None

    @staticmethod
    def has_user_requested(ride_db_id: int, user_id: int) -> bool:
        """Check if user has already requested this ride"""
        query = """
            SELECT id FROM ride_passengers
            WHERE ride_id = %s AND passenger_id = %s
        """
        results = db.execute_select_query(query, (ride_db_id, user_id))
        return len(results) > 0

    @staticmethod
    def insert_ride_request(
        ride_db_id: int,
        passenger_id: int,
        seats_requested: int = 1,
        pickup_location: Optional[Tuple[float, float]] = None,
        dropoff_location: Optional[Tuple[float, float]] = None
    ) -> bool:
        """Insert a ride request into ride_passengers table"""
        try:
            # Build the query based on whether custom locations are provided
            if pickup_location and dropoff_location:
                query = """
                    INSERT INTO ride_passengers (
                        ride_id, passenger_id, status, seats_requested,
                        pickup_location, dropoff_location, created_at
                    ) VALUES (
                        %s, %s, 'pending', %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        NOW()
                    )
                """
                params = (
                    ride_db_id, passenger_id, seats_requested,
                    pickup_location[1], pickup_location[0],  # lng, lat
                    dropoff_location[1], dropoff_location[0]  # lng, lat
                )
            elif pickup_location:
                query = """
                    INSERT INTO ride_passengers (
                        ride_id, passenger_id, status, seats_requested,
                        pickup_location, created_at
                    ) VALUES (
                        %s, %s, 'pending', %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        NOW()
                    )
                """
                params = (
                    ride_db_id, passenger_id, seats_requested,
                    pickup_location[1], pickup_location[0]
                )
            elif dropoff_location:
                query = """
                    INSERT INTO ride_passengers (
                        ride_id, passenger_id, status, seats_requested,
                        dropoff_location, created_at
                    ) VALUES (
                        %s, %s, 'pending', %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        NOW()
                    )
                """
                params = (
                    ride_db_id, passenger_id, seats_requested,
                    dropoff_location[1], dropoff_location[0]
                )
            else:
                query = """
                    INSERT INTO ride_passengers (
                        ride_id, passenger_id, status, seats_requested, created_at
                    ) VALUES (%s, %s, 'pending', %s, NOW())
                """
                params = (ride_db_id, passenger_id, seats_requested)

            result = db.execute_insert_query(query, params, return_id=True)
            logger.info(f"Ride request created: passenger={passenger_id}, ride={ride_db_id}, request_id={result}")
            return result is not None
        except Exception as e:
            logger.error(f"Error inserting ride request: {e}", exc_info=True)
            return False

    async def create_ride(self):
        """
            Create new ride
        """
        created_at = datetime.now()
        self.ride_id = self._generate_unique_ride_id(self.driver['user_id'], self.start_datetime, created_at)

        # Convert coordinates to PostGIS point format
        origin_lat, origin_lng = self.origin
        destination_lat, destination_lng = self.destination

        # Insert the ride record
        insert_ride_query = """
        INSERT INTO rides (
            ride_id, publisher_id, origin, destination, start_datetime, end_datetime,
            available_seats, cost_per_seat, additional_note, created_at,
            is_active, is_cancelled, vehicle_id
        ) VALUES (
            %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), ST_SetSRID(ST_MakePoint(%s, %s), 4326),
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) RETURNING id;
        """

        vehicle_id = getattr(self, 'vehicle_id')

        params = (
            self.ride_id,
            self.driver['user_id'],
            origin_lng, origin_lat,  # PostGIS uses longitude, latitude order
            destination_lng, destination_lat,
            self.start_datetime,
            self.end_datetime,
            self.available_seats,
            self.cost_per_seat,
            self.additional_note,
            created_at,
            True,
            False,
            vehicle_id
        )

        ride_db_id = db.execute_insert_query(insert_ride_query, params, return_id=True)

        # If there are additional stops, insert them as well
        if self.additional_stop and len(self.additional_stop) > 0:
            for idx, stop in enumerate(self.additional_stop):
                stop_lat, stop_lng = stop
                insert_stop_query = """
                INSERT INTO additional_stops (
                    ride_id, location, sequence_order, created_at, is_active
                ) VALUES (
                    %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s
                )
                """
                stop_params = (
                    ride_db_id,
                    stop_lng, stop_lat,
                    idx + 1,  # sequence_order starting from 1
                    created_at,
                    True
                )
                db.execute_insert_query(insert_stop_query, stop_params)

        logger.info({'msg': 'Ride Created', 'ride_id': self.ride_id, 'db_id': ride_db_id})
        return ride_db_id

    @staticmethod
    def _generate_unique_ride_id(driver_user_id: str, start_datetime: datetime, created_at: datetime) -> str:
        """Combination of driver user id, start datetime and ride creation datetime"""

        raw_id = (f"{driver_user_id}_{start_datetime.strftime('%d%m%Y%H%M%S')}"
                  f"_{created_at.strftime('%d%m%Y%H%M%S')}_{datetime.now()}")
        return hashlib.sha256(raw_id.encode()).hexdigest()

    @staticmethod
    def fetch_by_db_id(db_id: int) -> Optional[dict]:
        """Fetch ride details from database by internal ID"""
        query = """
            SELECT
                id, ride_id, publisher_id,
                ST_Y(origin::geometry) as origin_lat,
                ST_X(origin::geometry) as origin_lng,
                ST_Y(destination::geometry) as destination_lat,
                ST_X(destination::geometry) as destination_lng,
                start_datetime, end_datetime,
                available_seats, cost_per_seat, additional_note,
                is_active, is_cancelled, vehicle_id
            FROM rides
            WHERE id = %s
        """
        results = db.execute_select_query(query, (db_id,))
        return results[0] if results else None

    @staticmethod
    def get_user_rides(user_id: int, status: str = 'active') -> List[dict]:
        """Get all rides published by a user"""
        base_query = """
            SELECT
                r.id, r.ride_id, r.publisher_id,
                ST_Y(r.origin::geometry) as origin_lat,
                ST_X(r.origin::geometry) as origin_lng,
                ST_Y(r.destination::geometry) as destination_lat,
                ST_X(r.destination::geometry) as destination_lng,
                r.start_datetime, r.end_datetime,
                r.available_seats, r.cost_per_seat, r.additional_note,
                r.is_active, r.is_cancelled,
                (SELECT COUNT(*) FROM ride_passengers rp WHERE rp.ride_id = r.id AND rp.status = 'pending') as pending_requests,
                (SELECT COUNT(*) FROM ride_passengers rp WHERE rp.ride_id = r.id AND rp.status = 'confirmed') as confirmed_passengers
            FROM rides r
            WHERE r.publisher_id = %s
        """

        if status == 'active':
            base_query += " AND r.is_active = TRUE AND r.is_cancelled = FALSE AND r.start_datetime > NOW()"
        elif status == 'completed':
            base_query += " AND r.start_datetime < NOW() AND r.is_cancelled = FALSE"
        elif status == 'cancelled':
            base_query += " AND r.is_cancelled = TRUE"

        base_query += " ORDER BY r.start_datetime DESC"

        results = db.execute_select_query(base_query, (user_id,))

        formatted = []
        for r in results:
            formatted.append({
                "id": r['id'],
                "ride_id": r['ride_id'],
                "origin": [r['origin_lat'], r['origin_lng']],
                "destination": [r['destination_lat'], r['destination_lng']],
                "start_datetime": r['start_datetime'].strftime("%d %B %Y, %H:%M"),
                "end_datetime": r['end_datetime'].strftime("%d %B %Y, %H:%M"),
                "available_seats": r['available_seats'],
                "cost_per_seat": float(r['cost_per_seat']) if r['cost_per_seat'] else 0,
                "is_active": r['is_active'],
                "is_cancelled": r['is_cancelled'],
                "pending_requests": r['pending_requests'],
                "confirmed_passengers": r['confirmed_passengers']
            })
        return formatted

    @staticmethod
    def get_user_bookings(user_id: int, status: str = 'all') -> List[dict]:
        """Get all ride bookings for a user as passenger"""
        base_query = """
            SELECT
                rp.id as request_id, rp.status, rp.seats_requested, rp.created_at as requested_at,
                r.id as ride_db_id, r.ride_id,
                ST_Y(r.origin::geometry) as origin_lat,
                ST_X(r.origin::geometry) as origin_lng,
                ST_Y(r.destination::geometry) as destination_lat,
                ST_X(r.destination::geometry) as destination_lng,
                r.start_datetime, r.end_datetime,
                r.cost_per_seat, r.is_cancelled as ride_cancelled,
                u.first_name as driver_first_name, u.last_name as driver_last_name
            FROM ride_passengers rp
            JOIN rides r ON rp.ride_id = r.id
            JOIN users u ON r.publisher_id = u.id
            WHERE rp.passenger_id = %s
        """

        if status != 'all':
            base_query += f" AND rp.status = '{status}'"

        base_query += " ORDER BY r.start_datetime DESC"

        results = db.execute_select_query(base_query, (user_id,))

        formatted = []
        for r in results:
            formatted.append({
                "request_id": r['request_id'],
                "status": r['status'],
                "seats_requested": r['seats_requested'],
                "requested_at": r['requested_at'].strftime("%d %B %Y, %H:%M"),
                "ride_id": r['ride_id'],
                "driver_name": f"{r['driver_first_name']} {r['driver_last_name']}",
                "origin": [r['origin_lat'], r['origin_lng']],
                "destination": [r['destination_lat'], r['destination_lng']],
                "start_datetime": r['start_datetime'].strftime("%d %B %Y, %H:%M"),
                "end_datetime": r['end_datetime'].strftime("%d %B %Y, %H:%M"),
                "cost_per_seat": float(r['cost_per_seat']) if r['cost_per_seat'] else 0,
                "ride_cancelled": r['ride_cancelled']
            })
        return formatted

    @staticmethod
    def get_ride_requests(ride_db_id: int) -> List[dict]:
        """Get all passenger requests for a ride"""
        query = """
            SELECT
                rp.id as request_id, rp.status, rp.seats_requested, rp.created_at,
                u.id as passenger_id, u.first_name, u.last_name, u.phone_no,
                u.profile_picture_url, u.is_verified
            FROM ride_passengers rp
            JOIN users u ON rp.passenger_id = u.id
            WHERE rp.ride_id = %s
            ORDER BY rp.created_at DESC
        """
        results = db.execute_select_query(query, (ride_db_id,))

        formatted = []
        for r in results:
            formatted.append({
                "request_id": r['request_id'],
                "status": r['status'],
                "seats_requested": r['seats_requested'],
                "requested_at": r['created_at'].strftime("%d %B %Y, %H:%M"),
                "passenger": {
                    "id": r['passenger_id'],
                    "name": f"{r['first_name']} {r['last_name']}",
                    "phone_no": r['phone_no'],
                    "profile_picture": r['profile_picture_url'],
                    "is_verified": r['is_verified']
                }
            })
        return formatted

    @staticmethod
    def get_request_by_id(request_id: int) -> Optional[dict]:
        """Get a specific ride request by ID"""
        query = """
            SELECT id, ride_id, passenger_id, status, seats_requested, created_at
            FROM ride_passengers
            WHERE id = %s
        """
        results = db.execute_select_query(query, (request_id,))
        return results[0] if results else None

    @staticmethod
    def accept_ride_request(request_id: int, ride_db_id: int, seats: int) -> bool:
        """Accept a ride request and decrement available seats"""
        try:
            # Update request status
            update_request = """
                UPDATE ride_passengers
                SET status = 'confirmed', updated_at = NOW()
                WHERE id = %s
            """
            db.execute_update_query(update_request, (request_id,))

            # Decrement available seats
            update_seats = """
                UPDATE rides
                SET available_seats = available_seats - %s, updated_at = NOW()
                WHERE id = %s
            """
            db.execute_update_query(update_seats, (seats, ride_db_id))

            logger.info(f"Ride request {request_id} accepted, {seats} seats decremented from ride {ride_db_id}")
            return True
        except Exception as e:
            logger.error(f"Error accepting ride request: {e}", exc_info=True)
            return False

    @staticmethod
    def reject_ride_request(request_id: int) -> bool:
        """Reject a ride request"""
        try:
            query = """
                UPDATE ride_passengers
                SET status = 'rejected', updated_at = NOW()
                WHERE id = %s
            """
            db.execute_update_query(query, (request_id,))
            logger.info(f"Ride request {request_id} rejected")
            return True
        except Exception as e:
            logger.error(f"Error rejecting ride request: {e}", exc_info=True)
            return False

    @staticmethod
    def cancel_ride(ride_db_id: int) -> bool:
        """Cancel a ride and reject all pending requests"""
        try:
            # Cancel the ride
            cancel_query = """
                UPDATE rides
                SET is_cancelled = TRUE, is_active = FALSE, updated_at = NOW()
                WHERE id = %s
            """
            db.execute_update_query(cancel_query, (ride_db_id,))

            # Reject all pending requests
            reject_requests = """
                UPDATE ride_passengers
                SET status = 'cancelled', updated_at = NOW()
                WHERE ride_id = %s AND status IN ('pending', 'confirmed')
            """
            db.execute_update_query(reject_requests, (ride_db_id,))

            logger.info(f"Ride {ride_db_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling ride: {e}", exc_info=True)
            return False

    @staticmethod
    def cancel_booking(request_id: int, ride_db_id: int, seats_to_restore: int) -> bool:
        """Cancel a booking and restore seats if it was confirmed"""
        try:
            # Update booking status
            cancel_query = """
                UPDATE ride_passengers
                SET status = 'cancelled', updated_at = NOW()
                WHERE id = %s
            """
            db.execute_update_query(cancel_query, (request_id,))

            # Restore seats if booking was confirmed
            if seats_to_restore > 0:
                restore_seats = """
                    UPDATE rides
                    SET available_seats = available_seats + %s, updated_at = NOW()
                    WHERE id = %s
                """
                db.execute_update_query(restore_seats, (seats_to_restore, ride_db_id))

            logger.info(f"Booking {request_id} cancelled, {seats_to_restore} seats restored")
            return True
        except Exception as e:
            logger.error(f"Error cancelling booking: {e}", exc_info=True)
            return False
