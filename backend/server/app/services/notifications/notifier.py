"""The one place that tells people things.

Every event that someone should hear about goes through a `Notifier` method. For each recipient it
writes the in-app notification (the bell) and sends the email, honouring that person's email
preferences, so the two can never drift apart. Nothing else in the application builds an email or a
notification.

How it behaves:
  * The in-app row is added to the caller's database session, so it is saved or discarded together
    with the change that caused it (one commit, no notification for something that failed).
  * Email goes out as a background task after the response, only if the request succeeded, and a
    mail failure is logged and never fails the request (see EmailService.deliver).
  * A recipient without an account (an invitation to a new address) gets email only.
"""

from collections.abc import Callable

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Group, Notification, User
from app.services.email import Email, EmailService
from app.services.notifications import inbox
from app.services.notifications.catalog import CATEGORY_OF, Category, Kind


def _team_members_path(group: Group) -> str:
    return f"/teams/{group.code}/members"


class Notifier:
    def __init__(self, db: Session, mailer: EmailService, background: BackgroundTasks):
        self._db = db
        self._mailer = mailer
        self._background = background
        self._preferences: dict = {}

    # --- the machinery ---------------------------------------------------------------------

    def _wants_email(self, user: User | None, category: Category) -> bool:
        if user is None:
            return True  # no account, so no preferences: this is the only way to reach them
        if user.id not in self._preferences:
            self._preferences[user.id] = inbox.preferences(self._db, user.id)
        return self._preferences[user.id][category]

    def _deliver(
        self,
        kind: Kind,
        *,
        user: User | None,
        to_email: str | None = None,
        in_app: dict | None = None,
        email: Callable[[str], Email] | None = None,
    ) -> None:
        """`in_app` is the notification's fields; `email` builds the message for an address."""
        category = CATEGORY_OF[kind]
        if user is not None and in_app is not None:
            self._db.add(Notification(user_id=user.id, kind=kind.value, **in_app))
        address = to_email or (user.email if user else None)
        if email is not None and address and self._wants_email(user, category):
            self._background.add_task(self._mailer.deliver, email(address))

    def resolve(self, user_id, kind: Kind, ref: str) -> None:
        """What a notification asked about was answered: close it. See inbox.resolve."""
        inbox.resolve(self._db, user_id, kind, ref)

    # --- invitations -----------------------------------------------------------------------

    def invitation_sent(
        self,
        *,
        to_email: str,
        inviter: User,
        group: Group,
        as_lecturer: bool,
        token: str,
    ) -> None:
        """Email only. The invitee sees it in the bell once they can answer it (inbox.sync_invitations)."""
        self._deliver(
            Kind.TEAM_INVITATION,
            user=None,
            to_email=to_email,
            email=lambda to: self._mailer.team_invitation(
                to,
                inviter_name=inviter.name,
                team_name=group.name,
                as_lecturer=as_lecturer,
                token=token,
                expires_in_days=settings.INVITATION_TTL_DAYS,
            ),
        )

    def invitation_answered(
        self, inviter: User | None, *, member: User, group: Group, accepted: bool
    ) -> None:
        if inviter is None:
            return
        verb = "accepted" if accepted else "declined"
        path = _team_members_path(group)
        self._deliver(
            Kind.INVITATION_ANSWERED,
            user=inviter,
            in_app={
                "title": f"{member.name} {verb} your invitation to {group.name}",
                "link": path,
                "data": {"team_code": group.code},
                "ref": str(group.id),
            },
            email=lambda to: self._mailer.invitation_response(
                to,
                member_name=member.name,
                team_name=group.name,
                accepted=accepted,
                path=path,
            ),
        )

    # --- leadership ------------------------------------------------------------------------

    def leadership_offered(
        self, target: User, *, from_user: User, group: Group
    ) -> None:
        path = _team_members_path(group)
        # An earlier, unanswered offer for this team is replaced by this one.
        inbox.resolve(self._db, target.id, Kind.LEADERSHIP_OFFERED, str(group.id))
        self._deliver(
            Kind.LEADERSHIP_OFFERED,
            user=target,
            in_app={
                "title": f"{from_user.name} offered you team leadership of {group.name}",
                "body": "You become the team leader when you accept. Nothing changes until then.",
                "link": path,
                "data": {"team_code": group.code},
                "ref": str(group.id),
            },
            email=lambda to: self._mailer.leader_transfer_request(
                to, from_name=from_user.name, team_name=group.name, path=path
            ),
        )

    def leadership_answered(
        self, offerer: User | None, *, member: User, group: Group, accepted: bool
    ) -> None:
        if offerer is None or offerer.id == member.id:
            return
        path = _team_members_path(group)
        title = (
            f"{member.name} is now the leader of {group.name}"
            if accepted
            else f"{member.name} declined to lead {group.name}"
        )
        self._deliver(
            Kind.LEADERSHIP_ANSWERED,
            user=offerer,
            in_app={"title": title, "link": path, "data": {"team_code": group.code}},
            email=lambda to: self._mailer.leader_transfer_result(
                to,
                member_name=member.name,
                team_name=group.name,
                accepted=accepted,
                path=path,
            ),
        )

    def leadership_withdrawn(self, target: User, *, by: User, group: Group) -> None:
        path = _team_members_path(group)
        inbox.resolve(self._db, target.id, Kind.LEADERSHIP_OFFERED, str(group.id))
        sentence = f"{by.name} withdrew the offer to lead {group.name}."
        self._deliver(
            Kind.LEADERSHIP_WITHDRAWN,
            user=target,
            in_app={
                "title": f"The leadership offer for {group.name} was withdrawn",
                "body": f"{by.name} withdrew it.",
                "link": path,
                "data": {"team_code": group.code},
            },
            email=lambda to: self._mailer.notice(
                to,
                subject=f"Leadership offer for {group.name} withdrawn",
                heading="Offer withdrawn",
                sentence=sentence,
                path=path,
            ),
        )

    # --- people leaving --------------------------------------------------------------------

    def member_left(self, lecturers: list[User], *, member: User, group: Group) -> None:
        path = _team_members_path(group)
        for lecturer in lecturers:
            if lecturer.id == member.id:
                continue
            self._deliver(
                Kind.MEMBER_LEFT,
                user=lecturer,
                in_app={
                    "title": f"{member.name} left {group.name}",
                    "link": path,
                    "data": {"team_code": group.code},
                },
                email=lambda to: self._mailer.notice(
                    to,
                    subject=f"{member.name} left {group.name}",
                    heading="Someone left your team",
                    sentence=f"{member.name} left {group.name}.",
                    path=path,
                ),
            )

    def member_removed(self, member: User, *, by: User, group: Group) -> None:
        self._deliver(
            Kind.MEMBER_REMOVED,
            user=member,
            in_app={
                "title": f"You were removed from {group.name}",
                "body": f"{by.name} removed you from the team.",
                "link": "/home",
            },
            email=lambda to: self._mailer.notice(
                to,
                subject=f"You were removed from {group.name}",
                heading="Removed from a team",
                sentence=f"{by.name} removed you from {group.name}.",
                path="/home",
            ),
        )
