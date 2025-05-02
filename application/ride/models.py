from collections import defaultdict
from typing import List, Optional, Tuple
from fastapi.requests import Request
from config.app_logger import logger
from config.auth import access_token_required
from datetime import datetime
from config.postgresql import db
import hashlib

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

    @classmethod
    def create_for_rider(cls, ride_id):
        # Fetch ride details from the database using the ride_id
        ride_data = defaultdict()
        ride_data = ride_data[0]
        return cls(
            driver=ride_data["driver"],
            origin=ride_data["origin"],
            destination=ride_data["destination"],
            start_datetime=ride_data["start_datetime"],
            end_datetime=ride_data["end_datetime"],
            available_seats=ride_data["available_seats"],
            cost_per_seat=ride_data["cost_per_seat"],
            additional_note=ride_data["additional_note"],
            additional_stop=ride_data["additional_stop"],
            ride_id=ride_id
        )

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




