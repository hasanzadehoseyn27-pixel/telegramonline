from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import jwt


SECRET_KEY = "CHANGE_THIS_SECRET"
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60


ADMIN_USERNAME = "superadmin"
ADMIN_PASSWORD = "Admin123!"


def authenticate_user(
    username: str,
    password: str,
) -> bool:
    return (
        username == ADMIN_USERNAME
        and password == ADMIN_PASSWORD
    )


def create_access_token(
    username: str,
) -> str:

    expire = datetime.now(
        timezone.utc
    ) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": username,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )