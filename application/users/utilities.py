import hashlib
from datetime import datetime

import bcrypt
from config.app_logger import logger
from config.auth import generate_jwt_token
from config.mongo_db import *


def hash_password(password: str) -> bytes | None:
    try:
        password = password.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password, salt)
        return hashed_password
    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)
        return None


def verify_password(user_password: str, hashed_password: bytes) -> bool:
    try:
        user_password = user_password.encode("utf-8")
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode("utf-8")
        if bcrypt.checkpw(user_password, hashed_password):
            return True
        else:
            return False
    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)
        return False


def create_user(user_data: dict) -> str:
    try:
        user_id = generate_hashed_user_id(user_data["phone_no"])
        user_data.update(
            {
                "user_id": user_id,
                "created_at": datetime.now(),
                "updated_at": None,
                "is_active": 1,
                "is_verified": 0,
                "profile_picture_url": "",
            }
        )
        insert_document(collection_name="users", document=user_data)
        return user_id
    except Exception as e:
        logger.error(e, exc_info=True)
        return ""


def fetch_user_data_by_param(param, value) -> dict:
    try:
        result = fetch_documents(
            collection_name="users", filter_query={param: value}, limit=1
        )
        if result:
            return result[0]
        return {}
    except Exception as e:
        logger.error(e, exc_info=True)
        return {}


def authorize_user(user_details: dict) -> (str, str):
    try:
        access_token = generate_jwt_token(
            user_details=user_details, time_in_minutes=120
        )
        refresh_token = generate_jwt_token(
            user_details=user_details, time_in_minutes=86400, token_type="refresh"
        )

        update_documents(
            collection_name="users",
            filter_query={"user_id": user_details["user_id"]},
            update_data={"$set": {"last_login": datetime.now()}},
        )
        return access_token, refresh_token
    except Exception as e:
        logger.error(e, exc_info=True)


def generate_hashed_user_id(phone_no: str) -> str:
    return hashlib.sha256(phone_no.encode()).hexdigest()
