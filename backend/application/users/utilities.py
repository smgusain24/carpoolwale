import hashlib
from datetime import datetime

import bcrypt
from config.app_logger import logger
from config.postgresql import db
from config.auth import generate_jwt_token



def hash_password(password: str) -> bytes | None:
    try:
        password = password.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password, salt)
        return hashed_password
    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)
        return None


def verify_password(user_password: str, hashed_password) -> bool:
    try:
        user_password = user_password.encode("utf-8")
        if isinstance(hashed_password, memoryview):
            hashed_password = bytes(hashed_password)
        elif isinstance(hashed_password, str):
            hashed_password = hashed_password.encode("utf-8")
        if bcrypt.checkpw(user_password, hashed_password):
            return True
        else:
            return False
    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)
        return False


def create_user(user_data: dict) -> int:
    """
    Create a new user
    """
    try:

        # Set default values if not provided
        user_data.setdefault("country_code", "+91")
        user_data.setdefault("bio", "")
        user_data.setdefault("profile_picture_url", "")
        user_data.setdefault("email", None)

        query = """
       INSERT INTO users (
           first_name, last_name, country_code, phone_no, email, 
           hashed_password, bio, profile_picture_url, created_at, 
           is_active, is_verified
       ) VALUES (
           %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
       )
       """

        # Prepare parameters
        params = (
            user_data["first_name"],
            user_data["last_name"],
            user_data["country_code"],
            user_data["phone_no"],
            user_data["email"],
            user_data["hashed_password"],
            user_data["bio"],
            user_data["profile_picture_url"],
            datetime.now(),
            True,  # is_active
            False  # is_verified
        )

        # Execute query and get the ID of the newly created user
        user_id = db.execute_insert_query(query, params, return_id=True)

        # Insert emergency contacts if provided
        if "emergency_contact" in user_data and user_data["emergency_contact"]:
            for contact in user_data["emergency_contact"]:
                contact_query = """
                   INSERT INTO emergency_contacts (
                       user_id, name, country_code, phone_no, relationship,
                       created_at, is_active
                   ) VALUES (
                       %s, %s, %s, %s, %s, %s, %s
                   )
               """

                # Get contact data with defaults
                contact_name = contact.get("name", "")
                contact_phone = contact.get("phone_no", "")
                contact_country_code = contact.get("country_code", "+91")
                contact_relationship = contact.get("relationship", "")

                contact_params = (
                    user_id,
                    contact_name,
                    contact_country_code,
                    contact_phone,
                    contact_relationship,
                    datetime.now(),
                    True
                )

                db.execute_insert_query(contact_query, contact_params)

        logger.info(f"User created successfully with ID: {user_id}")
        return user_id

    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        return 0



def verify_user_exists(phone_no: str, country_code: str = '+91') ->bool:
    """
    Verify if a user exists in the database and if they are active.
    """
    try:
        query = "SELECT id, is_active FROM users WHERE phone_no = %s AND country_code = %s LIMIT 1"
        result = db.execute_select_query(query, params=(phone_no, country_code))

        if not result:
            return False

        user_data = result[0]
        return True

    except Exception as e:
        logger.error(f"Error verifying user existence: {e}", exc_info=True)
        return False, False


def get_user_data_by_phone_number(phone_no: str, country_code: str = '+91'):
    """
        Verify if a user exists in the database and if they are active.
        """
    try:
        query = """
            SELECT 
                id AS user_id,
                email,
                profile_picture_url,
                first_name,
                last_name,
                is_verified,
                bio,
                is_active,
                hashed_password             
            FROM users 
            WHERE phone_no = %s AND country_code = %s 
            LIMIT 1
        """
        result = db.execute_select_query(query, params=(phone_no, country_code))

        if not result:
            return {}

        user_data = result[0]
        return user_data

    except Exception as e:
        logger.error(f"Error verifying user existence: {e}", exc_info=True)
        return False, False


def authorize_user(user_details: dict) -> (str, str):
    try:
        access_token = generate_jwt_token(
            user_details=user_details, time_in_minutes=120
        )
        refresh_token = generate_jwt_token(
            user_details=user_details, time_in_minutes=86400, token_type="refresh"
        )


        return access_token, refresh_token
    except Exception as e:
        logger.error(e, exc_info=True)


def generate_hashed_user_id(phone_no: str) -> str:
    return hashlib.sha256(phone_no.encode()).hexdigest()


def revoke_user_session(session_id: int) -> bool:
    """Revoke a specific user session"""
    try:
        query = """
            UPDATE user_sessions
            SET revoked = TRUE, revoked_at = NOW()
            WHERE id = %s
        """
        db.execute_update_query(query, (session_id,))
        return True
    except Exception as e:
        logger.error(f"Error revoking session: {e}", exc_info=True)
        return False


def revoke_all_user_sessions(user_id: int) -> bool:
    """Revoke all sessions for a user"""
    try:
        query = """
            UPDATE user_sessions
            SET revoked = TRUE, revoked_at = NOW()
            WHERE user_id = %s AND revoked = FALSE
        """
        db.execute_update_query(query, (user_id,))
        logger.info(f"All sessions revoked for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error revoking all sessions: {e}", exc_info=True)
        return False


def get_user_by_id(user_id: int) -> dict:
    """Get user details by user ID"""
    try:
        query = """
            SELECT
                id, first_name, last_name, country_code, phone_no, email,
                bio, profile_picture_url, created_at, updated_at, last_login,
                is_active, is_verified
            FROM users
            WHERE id = %s
            LIMIT 1
        """
        result = db.execute_select_query(query, params=(user_id,))
        return result[0] if result else {}
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}", exc_info=True)
        return {}


def update_user_profile(user_id: int, updates: dict) -> bool:
    """Update user profile fields"""
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
        params.append(user_id)

        query = f"""
            UPDATE users
            SET {', '.join(set_clauses)}
            WHERE id = %s
        """

        db.execute_update_query(query, tuple(params))
        logger.info(f"User {user_id} profile updated: {list(updates.keys())}")
        return True
    except Exception as e:
        logger.error(f"Error updating user profile: {e}", exc_info=True)
        return False
