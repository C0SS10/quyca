import random
import string
import time
from typing import Any, List

from quyca.exceptions import ConflictException, ForbiddenException, InvalidParamException, NotEntityException
from quyca.models.user_model import User
from quyca.services import notification_service
from quyca.repositories import user_repository
from quyca.security.password_hasher import hash_password


def create_user(
    email: str, institution: str, ror_id: str, role: str, raw_payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Creates a new user and sends credentials via email."""
    if raw_payload is None:
        raise InvalidParamException("Payload requerido: institution, ror_id y role.")

    _validate_create_user_payload(raw_payload)

    if role.lower() == "admin":
        raise ForbiddenException("No se pueden crear usuarios con el role 'admin'.")

    existing_by_ror = user_repository.get_user_by_ror_id(ror_id)
    if existing_by_ror:
        raise ConflictException(
            f"Para la institución: {existing_by_ror.institution} ya existe un correo registrado: "
            f"{existing_by_ror.email}. Si deseas asignar un nuevo correo, edita el usuario existente."
        )

    raw_password = _generate_password()
    hashe_password = hash_password(raw_password)

    user = User(
        id=ror_id,
        email=email.strip().lower(),
        password=hashe_password,
        institution=institution.strip(),
        role=role.strip(),
        is_active=True,
        apikey=None,
    )

    user_repository.create_user(user)

    subject = "Tu cuenta en la plataforma ImpactU ha sido creada exitosamente."

    notification_service.send_custom_email(subject, role, institution, email, raw_password, ror_id=ror_id)

    return {
        "success": True,
        "msg": f"Usuario {email} Creado exitosamente y contraseña enviada por correo electrónico.",
    }


def get_all_users() -> List[dict[str, Any]]:
    """Lists users excluding admins and sensitive fields."""
    users = user_repository.get_all_users()
    filtered_users = [u for u in users if u.role.lower() != "admin"]
    return [
        {"email": u.email, "institution": u.institution, "id": u.id, "role": u.role, "is_active": u.is_active}
        for u in filtered_users
    ]


def deactivate_user(email: str) -> dict[str, Any]:
    """Disables a user account by setting its 'is_active' flag to False."""
    user_repository.deactivate_user(email)
    return {"success": True, "msg": f"El usuario {email} ha sido desactivado."}


def activate_user(email: str) -> dict[str, Any]:
    """Reactivates a user account by setting its 'is_active' flag to True."""
    user_repository.activate_user(email)
    return {"success": True, "msg": f"El usuario {email} ha sido activado."}


def update_password(email: str) -> dict[str, Any]:
    """Resets password, stores hash, and emails the new credentials."""

    user = user_repository.get_user_by_email(email)

    if not user:
        raise NotEntityException(f"El usuario con correo {email} no fue encontrado")

    if not user.is_active:
        raise ForbiddenException(f"Cuenta desactivada para el usuario {email}")

    new_password = _generate_password()
    hashed = hash_password(new_password)

    user_repository.update_user_password(email, hashed)

    subject = "Tu contraseña ha sido restablecida"

    notification_service.send_email_change_password(
        email=email, subject=subject, password=new_password, institution=user.institution, ror_id=user.id
    )
    return {"success": True, "msg": f"La contraseña de {email} se actualizó correctamente."}


def update_user_info(old_email: str, new_email: str, new_role: str, raw_payload: dict[str, Any]) -> dict[str, Any]:
    """Edits email and/or role, blocks admin role and admin account edits, and reissues credentials on email change."""
    _validate_edit_user_payload(raw_payload)

    if new_role and new_role.strip().lower() == "admin":
        raise ForbiddenException("No se puede asignar el rol 'admin' a un usuario.")
    current = user_repository.get_user_by_email(old_email)
    if not current:
        raise NotEntityException(f"Usuario con correo {old_email} no encontrado.")

    if not current.is_active:
        raise ForbiddenException(f"Cuenta desactivada para el usuario {old_email}")

    if current.role.strip().lower() == "admin":
        raise ForbiddenException("No se pueden editar los datos de este usuario")

    correo_cambiado = old_email.strip().lower() != new_email.strip().lower()
    role_cambiado = bool(new_role) and new_role.strip().lower() != current.role.strip().lower()

    if not correo_cambiado and not role_cambiado:
        raise InvalidParamException("No se detectaron cambios para actualizar.")

    updated_user = user_repository.update_user_info(old_email, new_email, new_role)
    if not updated_user:
        raise NotEntityException(f"Usuario con correo {old_email} no encontrado.")

    if role_cambiado and not correo_cambiado:
        return {"success": True, "msg": f"Rol del usuario {old_email} actualizado correctamente."}

    if correo_cambiado:
        new_password = _generate_password()
        hashed = hash_password(new_password)

        user_repository.update_user_password(updated_user.email, hashed)

        subject = "Tu cuenta en la plataforma ImpactU ha sido creada exitosamente."
        notification_service.send_custom_email(
            subject=subject,
            role=updated_user.role,
            institution=updated_user.institution,
            email=updated_user.email,
            password=new_password,
            ror_id=updated_user.id,
        )

        msg = (
            f"Correo del usuario actualizado correctamente y notificación enviada a {new_email}."
            if not role_cambiado
            else f"Correo y rol del usuario actualizados correctamente. Notificación enviada a {new_email}."
        )

        return {"success": True, "msg": msg}

    return {"success": True, "msg": "Usuario actualizado correctamente."}


def regenerate_apikey(email: str, expires: int | None) -> dict[str, Any]:
    """Generates a new API key for the user, after validating expiration rules, and stores it."""
    _validate_apikey_expiration(expires)

    new_key = {"id": _generate_apikey_id(), "expires": expires}
    user_repository.regenerate_apikey(email, new_key)
    return {"success": True, "apikey": new_key}


def update_apikey_expiration(email: str, expires: int | None) -> dict[str, Any]:
    """Updates the expiration timestamp of the user's API key after validating it."""
    _validate_apikey_expiration(expires)

    user_repository.update_apikey_expiration(email, expires)
    return {"success": True, "msg": "Expiración del API key actualizada"}


def delete_apikey(email: str) -> dict[str, Any]:
    """Removes the user's API key by setting it to None."""
    user_repository.delete_apikey(email)
    return {"success": True, "msg": "API key eliminada correctamente"}


def _generate_password(length: int = 10) -> str:
    """Generates a random alphanumeric password."""
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def _generate_apikey_id(length: int = 10) -> str:
    """Generates a random API key identifier."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def _validate_create_user_payload(payload: dict[str, Any]) -> None:
    """Validates required fields for user creation."""
    required = {"institution", "ror_id", "role"}
    received = set(payload.keys())

    missing = required - received
    extra = received - required

    if missing or extra:
        msg_parts = []
        if missing:
            msg_parts.append("Faltan: " + ",".join(sorted(missing)))
        if extra:
            msg_parts.append("Sobran: " + ", ".join(sorted(extra)))
        raise InvalidParamException(" | ".join(msg_parts))


def _validate_edit_user_payload(payload: dict[str, Any]) -> None:
    """Validates fields allowed for user editing."""
    allowed = {"email", "role"}
    received = set(payload.keys())

    if not received:
        raise InvalidParamException("Debes enviar al menos email o role.")

    extra = received - allowed

    if extra:
        raise InvalidParamException("Sobran: " + ", ".join(sorted(extra)))


def _validate_apikey_expiration(expires: int | None) -> None:
    """Validates API key expiration timestamp."""
    if expires is None:
        return

    if not isinstance(expires, int):
        raise InvalidParamException("El campo 'expires' debe ser un timestamp entero o None")

    current = int(time.time())

    if expires <= current:
        raise InvalidParamException("La fecha de expiración debe ser futura")

    if expires - current < 86400:
        raise InvalidParamException("La expiración mínima del API key es de 1 día")
