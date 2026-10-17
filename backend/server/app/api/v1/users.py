"""People.

GET /api/v1/users/{id}/avatar   a person's uploaded profile picture (their own, a teammate's, or
                                anyone's for an administrator); 404 otherwise
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from shared.contracts import UserRole
from sqlalchemy.orm import Session

from app.api.deps import Account, get_onboarded_account
from app.database.session import get_db
from app.services import avatars

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/{user_id}/avatar", summary="A person's uploaded profile picture")
def read_avatar(
    user_id: uuid.UUID,
    account: Annotated[Account, Depends(get_onboarded_account)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    row = avatars.visible_avatar(
        db, account.user, user_id, is_admin=account.role is UserRole.ADMIN
    )
    return Response(
        content=row.data,
        media_type=row.content_type,
        headers={
            "Cache-Control": "private, max-age=300",
            "X-Content-Type-Options": "nosniff",
            # An image is never a page: nothing in it may run or load.
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )
