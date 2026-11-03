from functools import wraps
from typing import Any, Callable

from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from quyca.exceptions import ForbiddenException, UnauthorizedException

View = Callable[..., Any]

MISSING_TOKEN_MESSAGE = "Token no proporcionado o inválido. Por favor, inicia sesión nuevamente."


def get_session_email(missing_token_message: str = MISSING_TOKEN_MESSAGE) -> str:
    """Email of the session; raises UnauthorizedException when there is no valid token."""
    try:
        verify_jwt_in_request()
    except Exception as e:
        raise UnauthorizedException(missing_token_message) from e
    email = get_jwt_identity()
    if not isinstance(email, str) or not email.strip():
        raise UnauthorizedException("Identidad de sesión inválida")
    return email.strip().lower()


def require_admin(view: View) -> View:
    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        get_session_email()
        role = get_jwt().get("role")
        if not isinstance(role, str) or role.lower() != "admin":
            raise ForbiddenException("Permiso denegado: No pueden realizar esta acción.")
        return view(*args, **kwargs)

    return wrapper


def require_same_user(view: View) -> View:
    """For /users/<email>/...: a session only manages its own account. The view receives the email normalized."""

    @wraps(view)
    def wrapper(email: str, *args: Any, **kwargs: Any) -> Any:
        email = email.strip().lower()
        if get_session_email() != email:
            raise ForbiddenException("No tienes permiso para gestionar el API Key de otro usuario.")
        return view(email, *args, **kwargs)

    return wrapper
