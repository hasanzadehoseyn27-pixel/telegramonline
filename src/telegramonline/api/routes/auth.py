from __future__ import annotations

from fastapi import APIRouter, HTTPException

from telegramonline.api.auth import (
    authenticate_user,
    create_access_token,
)

from telegramonline.api.schemas import (
    LoginRequest,
    LoginResponse,
)


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post(
    "/login",
    response_model=LoginResponse,
)
def login(
    payload: LoginRequest,
):

    valid = authenticate_user(
        payload.username,
        payload.password,
    )

    if not valid:
        raise HTTPException(
            status_code=401,
            detail="نام کاربری یا رمز عبور اشتباه است",
        )


    token = create_access_token(
        payload.username
    )


    return LoginResponse(
        token=token,
        username=payload.username,
    )