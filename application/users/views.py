import json
from datetime import datetime

from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Response, Form, HTTPException

from starlette import status
from starlette.datastructures import UploadFile

from application.users.utilities import (
    hash_password,
    create_user,
    verify_password,
    authorize_user, verify_user_exists, get_user_data_by_phone_number,
)
from config.app_logger import logger

from application.constants import _VERSION
from config.auth import generate_jwt_token
from config.http_status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

router = APIRouter(prefix=f"/{_VERSION}/users", tags=["Users"])


@router.post("/signup")
async def signup(request: Request):

    try:
        content_type = request.headers.get('Content-Type')
        if content_type is None:
            raise HTTPException(status_code=400, detail='No Content-Type provided!')
        elif (content_type == 'application/x-www-form-urlencoded' or
              content_type.startswith('multipart/form-data')):
            try:
                data = await request.form()
            except Exception:
                raise HTTPException(status_code=400, detail='Invalid Form data')
        else:
            raise HTTPException(status_code=400, detail='Content-Type not supported!')

        first_name: str = data.get("first_name")
        last_name: str = data.get("last_name")
        country_code: str = data.get('country_code') or "+91"
        phone_no: str = data.get("phone_no")
        email: str = data.get("email", "")
        bio: str = data.get("bio", "")
        password: str = data.get("password")
        emergency_contact: dict = json.loads(data.get("emergency_contact", "{}"))
        file: UploadFile = data.get('display_picture')


        exists = verify_user_exists(phone_no=phone_no, country_code=country_code)
        if exists:
            return JSONResponse(
                content={"msg": "User already exists"}, status_code=status.HTTP_409_CONFLICT
            )


        hashed_password = hash_password(password)
        user_id = create_user(
            {
                "first_name": first_name,
                "last_name": last_name,
                "phone_no": phone_no,
                "email": email,
                "hashed_password": hashed_password,
                "bio": bio,
                "emergency_contact": emergency_contact,
            }
        )
        user_details = {
            "user_id": user_id,
            "is_active": 1,
            "email": email,
            "phone_no": phone_no,
            "bio": bio,
            "profile_picture_url": "",
            "first_name": first_name,
            "last_name": last_name,
            "emergency_contact": emergency_contact,
            "is_verified": 0,
        }
        return JSONResponse(
            content={"msg": "User Created", "user_id": user_id},
            status_code=status.HTTP_201_CREATED,
        )

    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)
        return JSONResponse(
            content={"msg": f"{e}"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/login")
async def user_login(request: Request):
    try:
        data = await request.json()
        phone_no: str = data.get("phone_no")
        user_password: str = data.get("password")
        country_code: str = data.get("country_code") or "+91"

        user = get_user_data_by_phone_number(
            phone_no=phone_no, country_code=country_code
        )

        if not user:
            return JSONResponse(
                content={"msg": "User does not exist"},
                status_code=HTTP_400_BAD_REQUEST
            )

        if not user['is_active']:
            return JSONResponse(
                content={"msg": "Your account has been deactivated."},
                status_code=HTTP_403_FORBIDDEN
            )

        hashed_password = user["hashed_password"]
        if not verify_password(user_password, hashed_password):
            return JSONResponse(
                content={"msg": "Invalid credentials"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        user_details = {
            "user_id": user["user_id"],
            "is_active": user["is_active"],
            "email": user["email"],
            "phone_no": phone_no,
            "bio": user.get("bio", ""),
            "profile_picture_url": user.get("profile_picture_url", ""),
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "is_verified": user.get("is_verified"),
        }

        access_token, refresh_token = generate_jwt_token(
            user_details=user_details, time_in_minutes=120
        ), generate_jwt_token(
            user_details=user_details, time_in_minutes=8400, token_type="refresh"
        )

        return JSONResponse(
            content={
                "msg": "Logged in successfully",
                "access_token": access_token,
                "refresh_token": refresh_token,
            },
            status_code=status.HTTP_200_OK,
        )


    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)
        return JSONResponse(
            content={"msg": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

