import json
from datetime import datetime

from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Response, Form, HTTPException
from pydantic import ValidationError

from starlette import status
from starlette.datastructures import UploadFile

from application.users.models import ProfileUpdate
from application.users.utilities import (
    hash_password,
    create_user,
    verify_password,
    authorize_user, verify_user_exists, get_user_data_by_phone_number,
    revoke_user_session, revoke_all_user_sessions, get_user_by_id, update_user_profile
)
from config.app_logger import logger
from config.postgresql import db

from application.constants import _VERSION
from config.auth import generate_jwt_token, access_token_required, SECRET_KEY
from config.http_status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN
import jwt

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


@router.post("/logout")
@access_token_required
async def logout(request: Request):
    """
    Logout user by revoking their current session.
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        # Revoke all sessions for this user
        success = revoke_all_user_sessions(current_user['user_id'])

        if not success:
            return JSONResponse(
                content={"msg": "Logout failed"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return JSONResponse(
            content={"msg": "Logged out successfully"},
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)
        return JSONResponse(
            content={"msg": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/refresh_token")
async def refresh_token(request: Request):
    """
    Get a new access token using a valid refresh token.

    Headers:
        - Auth-Token: The refresh token
    """
    try:
        token = request.headers.get('Auth-Token')
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is missing")

        try:
            # Decode the refresh token
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

            if data.get('type') != 'refresh':
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail="Please provide a refresh token")

            # Verify the token exists in database and is not revoked
            jti = data.get('jti')
            query = """
                SELECT id, user_id, revoked FROM user_sessions
                WHERE token_jti = %s AND expires_at > NOW()
            """
            results = db.execute_select_query(query, (jti,))

            if not results:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail="Invalid or expired refresh token")

            session = results[0]
            if session['revoked']:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail="Token has been revoked")

            # Get fresh user data
            user = get_user_by_id(session['user_id'])
            if not user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail="User not found")

            if not user['is_active']:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="Your account has been deactivated")

            user_details = {
                "user_id": user["id"],
                "is_active": user["is_active"],
                "email": user["email"],
                "phone_no": user["phone_no"],
                "bio": user.get("bio", ""),
                "profile_picture_url": user.get("profile_picture_url", ""),
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "is_verified": user.get("is_verified"),
            }

            # Generate new access token
            access_token = generate_jwt_token(user_details=user_details, time_in_minutes=120)

            return JSONResponse(
                content={
                    "msg": "Token refreshed successfully",
                    "access_token": access_token
                },
                status_code=status.HTTP_200_OK
            )

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Refresh token has expired. Please login again.")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid token")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)
        return JSONResponse(
            content={"msg": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.put("/profile")
@access_token_required
async def update_profile(request: Request):
    """
    Update user profile.

    Body (all optional):
        - first_name
        - last_name
        - email
        - bio
        - profile_picture_url
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        data = await request.json()
        try:
            update_data = ProfileUpdate(**data)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        # Filter out None values
        updates = {k: v for k, v in update_data.model_dump().items() if v is not None}

        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="No fields to update")

        success = update_user_profile(current_user['user_id'], updates)

        if success:
            return JSONResponse(
                content={"msg": "Profile updated successfully"},
                status_code=status.HTTP_200_OK
            )
        else:
            return JSONResponse(
                content={"msg": "Failed to update profile"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)
        return JSONResponse(
            content={"msg": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/profile")
@access_token_required
async def get_profile(request: Request):
    """
    Get current user's profile.
    """
    try:
        current_user = request.state.user_details
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        user = get_user_by_id(current_user['user_id'])
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return JSONResponse(
            content={
                "user": {
                    "id": user['id'],
                    "first_name": user['first_name'],
                    "last_name": user['last_name'],
                    "phone_no": user['phone_no'],
                    "email": user['email'],
                    "bio": user['bio'],
                    "profile_picture_url": user['profile_picture_url'],
                    "is_verified": user['is_verified'],
                    "created_at": user['created_at'].strftime("%d %B %Y") if user['created_at'] else None
                }
            },
            status_code=status.HTTP_200_OK
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)
        return JSONResponse(
            content={"msg": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
