"""Students.

GET /api/v1/students/available?term=...   students with no team this term, from the lecturer's own
                                          institution (lecturers only); no emails. Invite them with
                                          POST /teams/{team}/invitations and `student_ids`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from shared.contracts import UserRole
from sqlalchemy.orm import Session

from app.api.deps import Account, require_account_role
from app.database.session import get_db
from app.schemas.team import AvailableStudent, AvailableStudents
from app.services import avatars, students

router = APIRouter(prefix="/students", tags=["Students"])

Lecturer = Annotated[Account, Depends(require_account_role(UserRole.LECTURER))]
Db = Annotated[Session, Depends(get_db)]


@router.get(
    "/available",
    response_model=AvailableStudents,
    summary="Students without a team this term",
)
def available_students(
    account: Lecturer, db: Db, term: Annotated[str, Query(min_length=1, max_length=32)]
) -> AvailableStudents:
    return AvailableStudents(
        term=term,
        institution=account.user.institution,
        students=[
            AvailableStudent(
                id=u.id,
                name=u.name,
                institution=u.institution,
                github_username=u.github_username,
                picture=avatars.picture_of(u),
            )
            for u in students.available(db, account.user, term)
        ],
    )
