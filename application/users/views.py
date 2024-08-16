from datetime import datetime

from fastapi.requests import Request
from fastapi.responses import JSONResponse

from application.users.utilities import hash_password, create_user, fetch_user_data_by_param, verify_password, \
    authorize_user
from config.app_logger import logger
from config.auth import generate_jwt_token
from config.http_status import *
from fastapi import APIRouter, Response

from application.constants import _VERSION

router = APIRouter(prefix=f"/{_VERSION}/users", tags=['Users'])


@router.post("/signup")
async def signup(request: Request):
    try:
        data = await request.json()
        first_name: str = data.get('first_name')
        last_name: str = data.get('last_name')
        phone_no: str = data.get('phone_no')
        email: str = data.get('email', '')
        bio: str = data.get('bio', '')
        password: str = data.get('password')
        emergency_contact: dict = data.get('emergency_contact', [])

        if fetch_user_data_by_param(param='phone_no', value=phone_no):
            return JSONResponse(content={'msg': 'User already exists'}, status_code=HTTP_409_CONFLICT)
        hashed_password = hash_password(password)
        user_id = create_user({
            "first_name": first_name,
            "last_name": last_name,
            "phone_no": phone_no,
            "email": email,
            "hashed_password": hashed_password,
            "bio": bio,
            "emergency_contact": emergency_contact
        })
        user_details = {
            "user_id": user_id,
            "is_active": 1,
            "email": email,
            "phone_no": phone_no,
            "bio": bio,
            "profile_picture_url": '',
            "first_name": first_name,
            "last_name": last_name,
            "emergency_contact": emergency_contact,
            "is_verified": 0
        }
        authorize_user(user_details)
        return JSONResponse(content=f"User created with id : {user_id}", status_code=HTTP_201_CREATED)

    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)
        return JSONResponse(content={'msg': f'{e}'}, status_code=HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/login")
async def user_login(request: Request, response: Response):
    try:
        data = await request.json()
        phone_no: str = data.get('phone_no')
        user_password: str = data.get('password')

        user = fetch_user_data_by_param(param='phone_no', value=phone_no)
        if not user:
            return JSONResponse(content={'msg': 'User does not exist'}, status_code=HTTP_400_BAD_REQUEST)

        hashed_password = user['hashed_password']
        if not verify_password(user_password, hashed_password):
            return JSONResponse(content={'msg': 'Invalid credentials'}, status_code=HTTP_401_UNAUTHORIZED)

        user_details = {
            "user_id": user['id'],
            "is_active": user['is_active'],
            "email": user['email'],
            "phone_no": phone_no,
            "bio": user.get('bio', ''),
            "profile_picture_url": user.get('profile_picture_url', ''),
            "first_name": user.get('first_name'),
            "last_name": user.get('last_name'),
            "emergency_contact": user.get('emergency_contact', []),
            "is_verified": user.get('is_verified')
        }

        access_token, refresh_token = authorize_user(user_details)

        login_response = JSONResponse(content={'msg': 'Logged in successfully'}, status_code=HTTP_200_OK)
        login_response.headers["Auth-Token"] = access_token
        login_response.headers["Refresh-Token"] = refresh_token

        return login_response

    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)
        return JSONResponse(content={'msg': 'Internal server error'}, status_code=HTTP_500_INTERNAL_SERVER_ERROR)
