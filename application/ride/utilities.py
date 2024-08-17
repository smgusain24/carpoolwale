from typing import List, Dict

from config.app_logger import logger
from config.mongo_db import fetch_documents


def fetch_ride_data_by_ride_id(ride_id: int|List[int]) -> List[Dict[str, any]]:
    try:
        if isinstance(ride_id, int):
            ride_id = [ride_id]
        data = fetch_documents(
            collection_name='rides',
            filter_query= {'ride_id' : {'$in': ride_id}}
        )
        return data
    except Exception as e:
        logger.error(e, exc_info=True)
        return []
