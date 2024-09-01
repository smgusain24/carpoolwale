import hashlib
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi.requests import Request

from application.ride.utilities import fetch_ride_data_by_ride_id
from config.app_logger import logger
from config.auth import access_token_required
from config.mongo_db import insert_document


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
        ride_data = fetch_ride_data_by_ride_id(ride_id)
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
        created_at = datetime.now()
        self.ride_id = self._generate_unique_ride_id(self.driver['user_id'], self.start_datetime, created_at)
        ride = {
            "ride_id": self.ride_id,
            "publisher_id": self.driver['user_id'],
            "origin": self.origin,
            "destination": self.destination,
            "start_datetime": self.start_datetime,
            "end_datetime": self.end_datetime,
            "available_seats": self.available_seats,
            "cost_per_seat": self.cost_per_seat,
            "passengers": self.passengers,
            "additional_note": self.additional_note,
            "additional_stop": self.additional_stop,
            "created_at": created_at,
            "updated_at": None,
            "is_active": 1,
            "is_cancelled": 0
        }
        insert_document(collection_name='rides', document=ride)
        logger.info({'msg': 'Ride Created', 'ride_id': ride['ride_id']})

    @staticmethod
    def _generate_unique_ride_id(driver_user_id: str, start_datetime: datetime, created_at: datetime) -> str:
        """Combination of driver user id, start datetime and ride creation datetime"""

        raw_id = (f"{driver_user_id}_{start_datetime.strftime('%d%m%Y%H%M%S')}"
                  f"_{created_at.strftime('%d%m%Y%H%M%S')}_{datetime.now()}")
        return hashlib.sha256(raw_id.encode()).hexdigest()




