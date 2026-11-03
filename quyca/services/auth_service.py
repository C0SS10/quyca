from typing import Any

from quyca.exceptions import ForbiddenException, InvalidParamException, NotEntityException, UnauthorizedException
from quyca.parsers.user_parser import parse_user_claims
from quyca.repositories import user_repository
from quyca.security import jwt_token_service

SESION_NO_INICIADA = "sesion_no_iniciada"
TOKEN_EXPIRADO = "token_expirado"
SESION_ACTIVA = "sesion_activa"


def login(email: str, password: str) -> dict:
    """Validates credentials and returns the user info plus an access token.
    Raises UnauthorizedException for wrong credentials and ForbiddenException for a deactivated account."""
    email = (email or "").strip()
    password = password or ""

    if not email or not password:
        raise InvalidParamException("correo y contraseña requeridos")

    try:
        user = user_repository.get_user_by_email_and_password(email, password)
    except NotEntityException as e:
        raise UnauthorizedException(str(e)) from e

    if not user.is_active:
        raise ForbiddenException("El usuario está desactivado. Contacte al administrador del sistema")

    parse_user = parse_user_claims(user)

    claims: dict[str, Any] = {
        "_id": parse_user["_id"],
        "institution": parse_user["institution"],
        "role": parse_user["role"],
    }

    token = jwt_token_service.create_access_token(subject=user.email, claims=claims)

    return {
        "success": True,
        **parse_user,
        "access_token": token,
    }


def get_session() -> dict[str, Any]:
    """Returns the current session status (one of the SESION_*/TOKEN_* constants) and the user when it is active."""
    token = jwt_token_service.get_access_token_cookie()
    if not token:
        return {"status": SESION_NO_INICIADA, "msg": "Sesión no iniciada"}

    claims = jwt_token_service.verify_cookie_claims()
    if not claims:
        return {"status": TOKEN_EXPIRADO, "msg": "Token expirado o inválido"}

    email = claims.get("sub")
    if not isinstance(email, str) or not email.strip():
        return {"status": TOKEN_EXPIRADO, "msg": "Token revocado o inválido"}

    return {
        "status": SESION_ACTIVA,
        "msg": "Sesión activa",
        "user": {
            "_id": claims.get("_id"),
            "institution": claims.get("institution"),
            "role": claims.get("role"),
            "email": email,
        },
    }
