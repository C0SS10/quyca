from quyca.models.user_model import User


def parse_user_claims(user: User) -> dict:
    """Extracts user id, institution and role from a User object."""
    info_user = {"_id": user.id, "institution": user.institution, "role": user.role}
    return info_user
