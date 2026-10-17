"""Every /api/v1 route requires a verified Keycloak user unless it is registered
on `public_router`. Add new routers to `protected_router` (any signed-in user) or
give them their own `require_roles(...)` dependency; tests/test_route_protection.py
fails if a route ends up without authentication.
"""

from fastapi import APIRouter, Depends

from app.api.v1.auth import router as auth_router
from app.api.v1.jobs import router as jobs_router
from app.core.security import get_current_user

# Nothing is public today: login happens in Keycloak, not in this API.
public_router = APIRouter()

# Any signed-in user. Routers that need a specific role add require_roles(...) on top.
protected_router = APIRouter(dependencies=[Depends(get_current_user)])
protected_router.include_router(auth_router)
protected_router.include_router(jobs_router)  # additionally admin-only (see jobs.py)

api_router = APIRouter()
api_router.include_router(public_router)
api_router.include_router(protected_router)
