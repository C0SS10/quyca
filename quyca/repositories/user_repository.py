from typing import Any, Dict, List, Optional

from quyca.exceptions import ConflictException, NotEntityException
from quyca.models.user_model import User
from quyca.clients.mongo import impactu_database
from quyca.security.password_hasher import verify_password

users_collection = impactu_database["users"]


def _to_user(document: dict) -> User:
    """Builds a User from a users document fetched without the password hash."""
    return User(
        id=str(document["_id"]),
        email=document["email"],
        password=None,
        institution=document["institution"],
        role=document["role"],
        is_active=document.get("is_active", True),
        apikey=document.get("apikey"),
    )


def get_user_by_email_and_password(email: str, password: str) -> User:
    """Validates credentials and returns the user data."""
    email = email.strip().lower()

    user_data = users_collection.find_one(
        {"email": email.strip().lower()},
        {"password": 1, "email": 1, "institution": 1, "role": 1, "is_active": 1, "apikey": 1},
    )

    if not user_data:
        raise NotEntityException(f"Usuario con correo {email} no encontrado o contraseña no conciden")

    stored_hash = user_data.get("password")
    try:
        if not stored_hash or not verify_password(password, stored_hash):
            raise NotEntityException(f"Usuario con correo {email} no encontrado o contraseña no conciden")
    except Exception:
        raise NotEntityException(f"Usuario con correo {email} no encontrado o contraseña no conciden")

    return User(
        id=str(user_data["_id"]),
        email=user_data["email"],
        institution=user_data["institution"],
        role=user_data["role"],
        is_active=user_data.get("is_active", True),
        apikey=user_data.get("apikey"),
    )


def get_user_by_email(email: str) -> Optional[User]:
    document = users_collection.find_one({"email": email.strip().lower()}, {"password": 0})
    return _to_user(document) if document else None


def create_user(user: User) -> None:
    """Inserts a new user if the email is not already registered."""
    email = user.email.strip().lower()
    existing = users_collection.find_one({"email": email}, {"password": 0})
    if existing:
        raise ConflictException(f"El usuario con correo {email} ya existe.")

    users_collection.insert_one(
        {
            "_id": user.id,
            "email": user.email,
            "password": user.password,
            "institution": user.institution,
            "role": user.role,
            "is_active": user.is_active,
            "apikey": user.apikey,
        }
    )


def get_all_users() -> List[User]:
    """Returns all users without exposing password hashes."""
    return [_to_user(u) for u in users_collection.find({}, {"password": 0})]


def update_user_password(email: str, new_password_hash: str) -> User:
    """Updates the password hash for a user and returns the updated user."""
    result = users_collection.update_one({"email": email.lower()}, {"$set": {"password": new_password_hash}})

    if result.matched_count == 0:
        raise NotEntityException(f"Usuario con correo {email} no encontrado")

    updated = users_collection.find_one({"email": email.lower()}, {"password": 0})
    if not updated:
        raise NotEntityException(f"Usuario con correo {email} no encontrado")
    return _to_user(updated)


def deactivate_user(email: str) -> None:
    """Sets is_active=False for the given email."""
    email = email.lower()
    user = users_collection.find_one({"email": email})
    if not user:
        raise NotEntityException(f"Usuario con correo {email} no encontrado")

    users_collection.update_one({"email": email}, {"$set": {"is_active": False}})


def activate_user(email: str) -> None:
    """Sets is_active=True for the given email."""
    email = email.lower()
    user = users_collection.find_one({"email": email})
    if not user:
        raise NotEntityException(f"Usuario con correo {email} no encontrado")

    users_collection.update_one({"email": email}, {"$set": {"is_active": True}})


def update_user_info(old_email: str, new_email: str, new_role: str) -> Optional[User]:
    """Updates email and/or role and returns the updated user (or None if missing)."""
    doc = users_collection.find_one({"email": old_email}, {"password": 0})
    if not doc:
        return None

    update = {}

    if new_email and new_email != old_email:
        if users_collection.find_one({"email": new_email}):
            raise ConflictException(f"Ya existe un usuario con el correo {new_email}")
        update["email"] = new_email

    if new_role:
        update["role"] = new_role

    if not update:
        return _to_user(doc)

    users_collection.update_one({"email": old_email}, {"$set": update})

    updated = users_collection.find_one({"email": update.get("email", old_email)}, {"password": 0})
    if not updated:
        return None

    return _to_user(updated)


def get_user_by_ror_id(ror_id: str) -> Optional[User]:
    """Finds a user by their ROR id (stored as _id)."""
    doc = users_collection.find_one({"_id": ror_id}, {"password": 0})
    if not doc:
        return None

    return _to_user(doc)


def regenerate_apikey(email: str, new_apikey: Dict[str, Any]) -> None:
    """Replaces the user's API key object."""
    result = users_collection.update_one({"email": email.lower()}, {"$set": {"apikey": new_apikey}})
    if result.matched_count == 0:
        raise NotEntityException(f"Usuario {email} no encontrado")


def update_apikey_expiration(email: str, new_expiration: int | None) -> None:
    """Updates only the apikey.expires field."""
    result = users_collection.update_one({"email": email.lower()}, {"$set": {"apikey.expires": new_expiration}})
    if result.matched_count == 0:
        raise NotEntityException(f"Usuario {email} no encontrado")


def delete_apikey(email: str) -> None:
    """Removes the API key by setting apikey=None."""
    result = users_collection.update_one({"email": email.lower()}, {"$set": {"apikey": None}})
    if result.matched_count == 0:
        raise NotEntityException(f"Usuario {email} no encontrado")
