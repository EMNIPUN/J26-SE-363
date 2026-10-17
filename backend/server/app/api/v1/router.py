"""Every /api/v1 route requires a verified Keycloak user unless it is registered
on `public_router`. Add new routers to `protected_router` (any signed-in user) or
give them their own `require_roles(...)` dependency; tests/test_route_protection.py
fails if a route ends up without authentication.
"""

from fastapi import APIRouter, Depends

from app.api.v1.auth import router as auth_router
from app.api.v1.invitations import router as invitations_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.me import router as me_router
from app.api.v1.students import router as students_router
from app.api.v1.teams import router as teams_router
from app.api.v1.terms import router as terms_router
from app.api.v1.users import router as users_router
from app.core.security import get_current_user

# Nothing is public today: login happens in Keycloak, not in this API.
public_router = APIRouter()

# Any signed-in user. Routers that need a specific role add require_roles(...) on top.
protected_router = APIRouter(dependencies=[Depends(get_current_user)])
protected_router.include_router(auth_router)
protected_router.include_router(me_router)
protected_router.include_router(students_router)
protected_router.include_router(teams_router)
protected_router.include_router(terms_router)
protected_router.include_router(users_router)
protected_router.include_router(invitations_router)
protected_router.include_router(jobs_router)  # additionally admin-only (see jobs.py)

api_router = APIRouter()
api_router.include_router(public_router)
api_router.include_router(protected_router)
