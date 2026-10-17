"""GET /api/v1/auth/me — who the Core API thinks the caller is (role resolved from Keycloak)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/me", response_model=CurrentUser, summary="Current user")
def read_current_user(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    return user
