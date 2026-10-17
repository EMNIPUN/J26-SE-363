"""The list of academic terms a team can belong to.

Lecturers pick one when they create a team, or add a new one on the spot. Names are compared
without regard to case, so "2026-s1" finds "2026-S1" instead of adding a near-duplicate.
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import bad_request, conflict
from app.models import Term, User


def all_terms(db: Session) -> list[Term]:
    return list(db.scalars(select(Term).order_by(Term.name.desc())))


def find(db: Session, name: str) -> Term | None:
    return db.scalar(select(Term).where(func.lower(Term.name) == name.strip().lower()))


def require(db: Session, name: str) -> Term:
    """The stored term for a name, or "unknown_term" (a team can only use a term that exists)."""
    term = find(db, name)
    if term is None:
        raise bad_request(
            "unknown_term", f"{name.strip()!r} is not in the term list. Add it first."
        )
    return term


def add(db: Session, name: str, creator: User) -> Term:
    if find(db, name) is not None:
        raise conflict("term_exists", f"{name.strip()} is already in the term list")
    term = Term(name=name.strip(), created_by_id=creator.id)
    db.add(term)
    try:
        db.commit()
    except IntegrityError as exc:  # two lecturers adding the same term at once
        db.rollback()
        raise conflict(
            "term_exists", f"{name.strip()} is already in the term list"
        ) from exc
    return term
