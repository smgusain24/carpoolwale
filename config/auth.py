import secrets
import uuid
from typing import Callable, Any, Optional, List
from fastapi import Request, HTTPException
from pydantic import BaseModel
from config.http_status import *
from config.app_logger import logger
import bcrypt
from datetime import datetime, timedelta, timezone
from functools import wraps
import jwt
from cryptography.fernet import Fernet

from config.postgresql import db
from config.redis_config import redis_db


SECRET_KEY = "OJRuyUg7CMd6POJAy1jMfsXQPMtGpyB8"
FERNET_KEY = "oIPE4NQAmag20i-zdK-rxILCp7DaiTfA-0K6-1QhJ1o="


class EmergencyContact(BaseModel):
    phone_no: str
    name: str

class UserDetails(BaseModel):
    user_id: str
    is_active: int
    email: Optional[str] = None
    phone_no: str
    bio: Optional[str] = None
    profile_picture_url: Optional[str] = None
    first_name: str
    last_name: str
    emergency_contact: List[EmergencyContact]
    is_verified: int


class TokenData(BaseModel):
    exp: int
    type: str
    user_details: UserDetails


def hash_password(password: str) -> bytes:
    try:
        password = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password, salt)
        return hashed_password
    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)


def verify_password(user_password: str, hashed_password: bytes) -> bool:
    try:
        user_password = user_password.encode('utf-8')
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        if bcrypt.checkpw(user_password, hashed_password):
            return True
        else:
            return False
    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)


def invalidate_users_RT(user_id) -> None:
    # Invalidates all refresh tokens of a user
    redis_db.delete(f"USER:{user_id}")  # Delete redis entry


def generate_jwt_token(user_details, time_in_minutes, token_type='access') -> str:
    try:
        user_id = user_details['user_id']

        # Create a unique token identifier
        jti = str(uuid.uuid4())

        # Current timestamp
        now = datetime.now(tz=timezone.utc)

        # Build standard JWT payload
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=time_in_minutes),
            "jti": jti,
            "type": token_type,
            "user_details": user_details
        }

        # Generate the JWT
        token = jwt.encode(
            payload,
            SECRET_KEY,
            algorithm="HS256"
        )

        # Handle refresh token storage
        if token_type == 'refresh':

            # Store in database (instead of Redis)
            store_refresh_token_in_db(
                user_id=user_id,
                refresh_token=token,
                token_jti=jti,
                expires_at=payload["exp"]
            )



        return token

    except jwt.PyJWTError as e:
        logger.error(f"JWT encoding error: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.exception(f"Token generation error: {e}", exc_info=True)
        raise


def access_token_required(f: Callable[..., Any]) -> Callable[..., Any]:
    # JWT Access token authorization
    @wraps(f)
    async def decorated(*args, **kwargs) -> Any:
        try:
            request: Request = kwargs.get('request')
            if request is None:
                raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Request is required")

            user_id = None
            token = request.headers.get('Auth-Token')
            if not token:
                raise HTTPException(status_code=403, detail={'message': 'Token is missing!'})

            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            token_data = TokenData(**data)
            user_details = data['user_details']
            user_id = user_details['user_id']
            request.state.user_details = user_details

            if user_id and is_hacker(user_id, token_data.user_details.user_id):
                raise HTTPException(status_code=403, detail={'message': 'Please login to continue',
                                                             'reason': 'Hacker attack identified!'})

            if token_data.type != 'access':
                raise HTTPException(status_code=403, detail={'message': 'Please provide access token',
                                                             'reason': 'Invalid signature type'})

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail={'message': 'Please login to continue',
                                                         'reason': 'Token Expired'})

        except Exception as err:
            logger.error(f"{err}", exc_info=True, stack_info=True)
            raise HTTPException(status_code=403, detail={'message': 'Please login to continue',
                                                         'reason': 'Invalid signature'})
        return await f(*args, **kwargs)

    return decorated


def refresh_token_validation(user_id, refresh_token) -> bool:
    try:
        is_valid_RT = redis_db.get(f"USER:{user_id}")

        if is_valid_RT:
            encrypted_RT_str = is_valid_RT['refresh_token']
            encrypted_RT = eval(encrypted_RT_str)
            f = Fernet(FERNET_KEY)
            decrypted_RT = f.decrypt(encrypted_RT).decode()
            if decrypted_RT == refresh_token:
                return True

            invalidate_users_RT(user_id)
        return False
    except Exception as e:
        logger.exception(e, exc_info=True, stack_info=True)


def refresh_token_required(f: Callable[..., Any]) -> Callable[..., Any]:
    # JWT Refresh token authorization
    @wraps(f)
    async def decorated(request: Request, *args: Any, **kwargs: Any) -> Any:
        token = request.headers.get('Auth-Token')
        if not token:
            raise HTTPException(status_code=403, detail={'message': 'Token is missing!'})
        try:
            kwargs = jwt.decode(token, SECRET_KEY, algorithms="HS256")

            if kwargs['type'] != 'refresh':
                raise HTTPException(status_code=403, detail={'message': 'Please provide refresh token',
                                                             'reason': 'Invalid signature type'})

            if not refresh_token_validation(kwargs['id'], token):
                raise HTTPException(status_code=403, detail={'message': 'Please login to continue',
                                                             'reason': 'Attack identified!'})

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=403, detail={'message': 'Please login to continue',
                                                         'reason': 'Attack identified!'})

        except Exception as err:
            logger.error(f"{err}", exc_info=True, stack_info=True)
            raise HTTPException(status_code=403, detail={'message': 'Please login to continue',
                                                         'reason': 'Invalid signature'})
        return await f(request, *args, **kwargs)

    return decorated


def is_hacker(user_id, token_user_id) -> bool:
    try:
        if str(user_id) != str(token_user_id):
            return True
        return False
    except Exception as e:
        logger.exception(e, exc_info=True, stack_info=True)


def store_refresh_token_in_db(user_id, refresh_token, token_jti, expires_at):
    """
    Store a refresh token in the database and invalidate existing tokens.
    Implements a single-session policy where only one active session per user is allowed.

    Parameters:
    - user_id: ID of the user
    - refresh_token: The refresh token to store
    - token_jti: Unique ID of jwt token
    - expires_at: Expiration datetime of the token
    """
    try:

        query = """
                UPDATE user_sessions 
                SET revoked = TRUE, revoked_at = NOW(), is_active = False 
                WHERE user_id = %s AND revoked = FALSE
        """
        db.execute_update_query(query, params=(user_id,))

        # Insert the new refresh token
        query = """
                INSERT INTO user_sessions 
                (user_id, refresh_token, token_jti, expires_at)
                VALUES (%s, %s, %s, %s)
            """

        params = (user_id, refresh_token, token_jti, expires_at)

        session_id = db.execute_insert_query(query=query, params=params, return_id=True)

        return session_id

    except Exception as e:
        logger.exception(f"Error storing refresh token: {e}", exc_info=True)
        raise
