"""Academic terms.

GET  /api/v1/terms   the terms a team can belong to, newest first
POST /api/v1/terms   add one (lecturers); 409 term_exists if it is already there
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from shared.contracts import UserRole
from sqlalchemy.orm import Session

from app.api.deps import Account, get_onboarded_account, require_account_role
from app.database.session import get_db
from app.schemas.team import TermCreate, TermOut
from app.services import terms

router = APIRouter(tags=["Terms"])

Onboarded = Annotated[Account, Depends(get_onboarded_account)]
Lecturer = Annotated[Account, Depends(require_account_role(UserRole.LECTURER))]
Db = Annotated[Session, Depends(get_db)]


@router.get("/terms", response_model=list[TermOut], summary="Terms")
def list_terms(_: Onboarded, db: Db) -> list[TermOut]:
    return [TermOut(name=term.name) for term in terms.all_terms(db)]


@router.post(
    "/terms",
    response_model=TermOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a term",
)
def add_term(body: TermCreate, account: Lecturer, db: Db) -> TermOut:
    return TermOut(name=terms.add(db, body.name, account.user).name)
