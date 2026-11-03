from pydantic import BaseModel
from typing import Optional

"""
User entity used for authentication and account management.
"""


class User(BaseModel):
    """Represents a system user for authentication and account management."""

    id: str
    email: str
    password: Optional[str] = None
    institution: str
    role: str
    is_active: bool = True
    apikey: Optional[dict] = None
