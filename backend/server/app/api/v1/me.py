"""The signed-in person's own account.

GET   /api/v1/me             account, role and whether onboarding is finished
POST  /api/v1/me/onboarding  choose student or lecturer, give the details, accept the terms
PATCH /api/v1/me/profile     change the details later (the role cannot change)
PUT   /api/v1/me/picture     upload a profile picture (the image itself as the request body)
DELETE /api/v1/me/picture    remove the uploaded picture (the provider's, if any, shows again)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.deps import Account, get_account
from app.database.session import get_db
from app.schemas.account import AccountOut, OnboardingRequest, ProfileOut, ProfileUpdate
from app.services import accounts, avatars

router = APIRouter(prefix="/me", tags=["Account"])


def to_out(account: Account) -> AccountOut:
    user = account.user
    return AccountOut(
        id=user.id,
        name=user.name,
        email=user.email,
        email_verified=account.matching_email is not None,
        role=account.role,
        onboarding_completed=account.onboarded,
        profile=ProfileOut(
            institution=user.institution,
            student_number=user.student_number,
            github_username=user.github_username,
            department=user.department,
            title=user.title,
        ),
        picture=avatars.picture_of(user),
        consent_version=user.consent_version,
        current_consent_version=accounts.CONSENT_VERSION,
    )


@router.get("", response_model=AccountOut, summary="My account")
def read_me(account: Annotated[Account, Depends(get_account)]) -> AccountOut:
    return to_out(account)


@router.post(
    "/onboarding", response_model=AccountOut, summary="Finish setting up my account"
)
def finish_onboarding(
    body: OnboardingRequest,
    account: Annotated[Account, Depends(get_account)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountOut:
    accounts.complete_onboarding(db, account.user, account.identity, body)
    return to_out(account)


@router.patch("/profile", response_model=AccountOut, summary="Update my details")
def update_profile(
    body: ProfileUpdate,
    account: Annotated[Account, Depends(get_account)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountOut:
    accounts.update_profile(db, account.user, account.identity, body)
    return to_out(account)


async def _read_image(request: Request) -> bytes:
    """The request body, refused as soon as it is larger than a picture may be."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > avatars.MAX_BYTES:
        raise avatars.too_large()
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > avatars.MAX_BYTES:
            raise avatars.too_large()
    return bytes(body)


@router.put("/picture", response_model=AccountOut, summary="Upload my profile picture")
async def upload_picture(
    request: Request,
    account: Annotated[Account, Depends(get_account)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountOut:
    data = await _read_image(request)
    await run_in_threadpool(avatars.set_avatar, db, account.user, data)
    return to_out(account)


@router.delete(
    "/picture", response_model=AccountOut, summary="Remove my uploaded picture"
)
def remove_picture(
    account: Annotated[Account, Depends(get_account)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountOut:
    avatars.remove_avatar(db, account.user)
    return to_out(account)
