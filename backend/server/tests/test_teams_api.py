import re
import uuid
from datetime import timedelta

import pytest

from app.models import GroupMember, TeamInvitation
from app.services import invitations
from app.services import team_rules as rules
from app.services.accounts import CONSENT_VERSION

TERM = "2026-S1"


# --- helpers ---------------------------------------------------------------------------------


def onboard(api, sub, kind, email=None, **extra):
    email = email or f"{sub}@example.com"
    api.sign_in(sub, email=email, name=sub.title())
    body = {
        "account_type": kind,
        "display_name": sub.title(),
        "accept_terms": True,
        "consent_version": CONSENT_VERSION,
        **extra,
    }
    if kind == "student":
        body.setdefault("github_username", f"gh-{sub}")
    response = api.post("/me/onboarding", body)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def lecturer(api, sub="ada"):
    return onboard(api, sub, "lecturer")


def student(api, sub):
    return onboard(api, sub, "student")


def new_team(api, **overrides):
    body = {
        "name": "Team Alpha",
        "term": TERM,
        "project_title": "Food ordering system",
        "students": ["sam@example.com", "kim@example.com", "lee@example.com"],
        **overrides,
    }
    response = api.post("/teams", body)
    assert response.status_code == 201, response.text
    return response.json()


def token_from(api, to):
    """The secret from the link in the latest email sent to an address."""
    mails = [m for m in api.email.outbox if m.to == to]
    return re.search(r"token=([\w-]+)", mails[-1].text).group(1)


def invitation_id(api, email):
    invitations_ = api.get("/me/invitations").json()
    return invitations_[0]["id"]


def accept(api, sub, team_id=None):
    """Sign in as an already-onboarded person and accept the first invitation."""
    api.sign_in(sub, email=f"{sub}@example.com", name=sub.title())
    (first, *_) = api.get("/me/invitations").json()
    response = api.post(f"/invitations/{first['id']}/accept")
    assert response.status_code == 200, response.text
    return response.json()


def team_as(api, sub, code):
    api.sign_in(sub, email=f"{sub}@example.com")
    return api.get(f"/teams/{code}")


def join_all(api, code="TEAM-ALPHA", people=("sam", "kim", "lee")):
    for sub in people:
        student(api, sub)
        accept(api, sub)


# --- creating --------------------------------------------------------------------------------


def test_a_lecturer_creates_a_team_and_invites_students(api):
    lecturer(api)

    created = new_team(api, lecturers=["grace@example.com"])

    team = created["team"]
    assert team["name"] == "Team Alpha" and team["code"] == "TEAM-ALPHA"
    assert team["status"] == "forming" and team["term"] == TERM
    assert team["project"]["title"] == "Food ordering system"
    assert team["my_role"] == "lecturer"
    assert team["student_count"] == 0 and team["lecturer_count"] == 1
    assert team["pending_invitations"] == 4
    assert {r["outcome"] for r in created["invitations"]} == {"invited"}
    assert sorted(m.to for m in api.email.outbox) == [
        "grace@example.com",
        "kim@example.com",
        "lee@example.com",
        "sam@example.com",
    ]


def test_the_first_student_is_the_default_leader_unless_the_lecturer_picks_one(api):
    lecturer(api)
    new_team(api)
    new_team(api, name="Team Beta", leader_email="lee@example.com")

    db = api.db()
    flagged = {
        (i.group.code, i.email)
        for i in db.query(TeamInvitation).filter_by(as_leader=True).all()
    }
    assert flagged == {
        ("TEAM-ALPHA", "sam@example.com"),
        ("TEAM-BETA", "lee@example.com"),
    }


def test_students_cannot_create_teams(api):
    student(api, "sam")

    response = api.post("/teams", {"name": "X", "term": TERM, "project_title": "Y"})

    assert response.status_code == 403
    assert response.json()["code"] == "role_not_allowed"


def test_creating_a_team_needs_onboarding(api):
    api.sign_in("new", email="new@example.com")

    response = api.post("/teams", {"name": "X", "term": TERM, "project_title": "Y"})

    assert response.status_code == 403
    assert response.json()["code"] == "onboarding_required"


def test_team_codes_are_unique_and_generated_when_missing(api):
    lecturer(api)
    first = new_team(api)["team"]["code"]
    second = new_team(api)["team"]["code"]  # same name
    explicit = api.post(
        "/teams",
        {"name": "Other", "code": "j26-se-363", "term": TERM, "project_title": "P"},
    )
    clash = api.post(
        "/teams",
        {"name": "Other", "code": "J26-SE-363", "term": TERM, "project_title": "P"},
    )

    assert (first, second) == ("TEAM-ALPHA", "TEAM-ALPHA-2")
    assert explicit.json()["team"]["code"] == "J26-SE-363"
    assert clash.status_code == 409 and clash.json()["code"] == "team_code_taken"


@pytest.mark.parametrize(
    "change",
    [
        {"students": ["a@example.com", "A@example.com"]},
        {"students": ["not-an-email"]},
        {"students": ["a@example.com"], "leader_email": "other@example.com"},
        {"students": ["a@example.com"], "lecturers": ["a@example.com"]},
        {"code": "no spaces allowed"},
        {"term": ""},
        {"project_title": " "},
    ],
)
def test_invalid_team_requests_are_rejected(api, change):
    lecturer(api)

    response = api.post(
        "/teams", {"name": "X", "term": TERM, "project_title": "Y", **change}
    )

    assert response.status_code == 422
    assert api.get("/me/teams").json() == []


def test_a_lecturer_cannot_invite_their_own_address(api):
    lecturer(api, "ada")

    response = api.post(
        "/teams",
        {
            "name": "X",
            "term": TERM,
            "project_title": "Y",
            "students": ["ada@example.com"],
        },
    )

    assert (
        response.status_code == 400
        and response.json()["code"] == "cannot_invite_yourself"
    )
    assert api.get("/me/teams").json() == []


# --- answering invitations -------------------------------------------------------------------


def test_a_student_sees_the_invitation_and_joins_the_team(api):
    lecturer(api)
    new_team(api)
    student(api, "sam")

    waiting = api.get("/me/invitations").json()
    assert len(waiting) == 1
    assert waiting[0]["team_code"] == "TEAM-ALPHA" and waiting[0]["invited_by"] == "Ada"
    assert (
        waiting[0]["role"] == "member"
        and waiting[0]["project_title"] == "Food ordering system"
    )
    assert api.get("/me/teams").json() == []  # not a member yet

    team = accept(api, "sam")

    assert team["my_role"] == "leader"  # flagged first student, now the leader
    assert team["status"] == "active" and team["student_count"] == 1
    assert api.get("/me/invitations").json() == []
    assert [t["code"] for t in api.get("/me/teams").json()] == ["TEAM-ALPHA"]
    notified = [m for m in api.email.outbox if m.to == "ada@example.com"]
    assert len(notified) == 1 and "accepted" in notified[0].subject


def test_declining_removes_the_invitation_and_tells_the_lecturer(api):
    lecturer(api)
    new_team(api)
    student(api, "sam")
    (first,) = api.get("/me/invitations").json()

    response = api.post(f"/invitations/{first['id']}/decline")

    assert response.status_code == 204
    assert api.get("/me/invitations").json() == []
    assert api.get("/me/teams").json() == []
    assert any(
        "declined" in m.subject for m in api.email.outbox if m.to == "ada@example.com"
    )


def test_only_the_invited_address_can_answer(api):
    lecturer(api)
    new_team(api)
    student(api, "sam")
    (first,) = api.get("/me/invitations").json()
    student(api, "mallory")

    stolen = api.post(f"/invitations/{first['id']}/accept")

    assert stolen.status_code == 404
    assert api.get("/me/invitations").json() == []
    api.sign_in("sam", email="sam@example.com")
    assert len(api.get("/me/invitations").json()) == 1


def test_unverified_email_cannot_match_invitations(api):
    lecturer(api)
    new_team(api)
    onboard(api, "sam", "student")
    api.sign_in("sam", email="sam@example.com", verified=False)

    assert api.get("/me/invitations").json() == []
    fake = "00000000-0000-0000-0000-000000000000"
    response = api.post(f"/invitations/{fake}/accept")
    assert (
        response.status_code == 403 and response.json()["code"] == "email_not_verified"
    )


def test_a_lecturer_account_cannot_take_a_student_seat(api):
    lecturer(api, "ada")
    new_team(api, students=["grace@example.com"])
    onboard(api, "grace", "lecturer")
    (first,) = api.get("/me/invitations").json()

    response = api.post(f"/invitations/{first['id']}/accept")

    assert response.status_code == 403 and response.json()["code"] == "role_mismatch"


def test_the_email_link_secret_finds_the_invitation_for_the_right_person(api):
    lecturer(api)
    new_team(api)
    secret = token_from(api, "sam@example.com")
    student(api, "sam")
    (listed,) = api.get("/me/invitations").json()

    found = api.post("/invitations/lookup", {"token": secret})
    wrong_person = None
    student(api, "kim")
    wrong_person = api.post("/invitations/lookup", {"token": secret})
    bogus = api.post("/invitations/lookup", {"token": "x" * 40})

    assert found.status_code == 200 and found.json()["id"] == listed["id"]
    assert wrong_person.status_code == 403
    assert wrong_person.json()["code"] == "invitation_wrong_account"
    assert "s***@example.com" in wrong_person.json()["detail"]
    assert "sam@example.com" not in wrong_person.json()["detail"]
    assert bogus.status_code == 410 and bogus.json()["code"] == "invitation_invalid"


def test_expired_invitations_cannot_be_used(api):
    lecturer(api)
    new_team(api)
    student(api, "sam")
    (first,) = api.get("/me/invitations").json()
    db = api.db()
    row = db.get(TeamInvitation, uuid.UUID(first["id"]))
    row.expires_at = rules.utcnow() - timedelta(minutes=1)
    db.commit()

    assert api.get("/me/invitations").json() == []
    response = api.post(f"/invitations/{first['id']}/accept")
    assert (
        response.status_code == 410 and response.json()["code"] == "invitation_invalid"
    )


def test_an_invitation_can_only_be_answered_once(api):
    lecturer(api)
    new_team(api)
    student(api, "sam")
    (first,) = api.get("/me/invitations").json()
    api.post(f"/invitations/{first['id']}/accept")

    again = api.post(f"/invitations/{first['id']}/accept")

    assert again.status_code in (404, 410)
    assert len(api.get("/me/teams").json()) == 1


def test_a_student_can_be_in_one_team_per_term(api):
    lecturer(api)
    new_team(api, students=["sam@example.com"])
    new_team(api, name="Team Beta", students=["sam@example.com"])
    new_team(api, name="Team Gamma", term="2026-S2", students=["sam@example.com"])
    student(api, "sam")
    first, second, third = api.get("/me/invitations").json()[::-1]

    ok = api.post(f"/invitations/{first['id']}/accept")
    clash = api.post(f"/invitations/{second['id']}/accept")
    other_term = api.post(f"/invitations/{third['id']}/accept")

    assert ok.status_code == 200
    assert (
        clash.status_code == 409 and clash.json()["code"] == "already_in_team_for_term"
    )
    assert "Team Alpha" in clash.json()["detail"]
    assert other_term.status_code == 200
    assert len(api.get("/me/teams").json()) == 2


# --- the leader ------------------------------------------------------------------------------


def test_the_flagged_leader_waits_for_their_answer(api):
    lecturer(api)
    new_team(api, leader_email="lee@example.com")
    student(api, "sam")
    first = accept(api, "sam")  # not the flagged leader
    assert first["my_role"] == "member" and first["leader"] is None

    student(api, "lee")
    leader = accept(api, "lee")

    assert leader["my_role"] == "leader" and leader["leader"]["name"] == "Lee"


def test_if_the_flagged_leader_declines_the_first_student_who_joined_leads(api):
    lecturer(api)
    new_team(api, leader_email="lee@example.com")
    student(api, "sam")
    accept(api, "sam")
    student(api, "kim")
    accept(api, "kim")
    student(api, "lee")
    (lee_invite,) = api.get("/me/invitations").json()
    api.post(f"/invitations/{lee_invite['id']}/decline")

    api.sign_in("ada", email="ada@example.com")
    team = api.get("/teams/TEAM-ALPHA").json()

    assert team["leader"]["name"] == "Sam"


def test_a_team_with_students_always_has_a_leader(api):
    lecturer(api)
    new_team(api, students=["sam@example.com"], leader_email=None)
    student(api, "sam")
    team = accept(api, "sam")

    assert team["leader"]["name"] == "Sam"


# --- viewing ---------------------------------------------------------------------------------


def test_lecturers_see_emails_and_invitations_students_do_not(api):
    lecturer(api)
    new_team(api, students=["sam@example.com", "kim@example.com"])
    join_all(api, people=("sam",))

    as_student = team_as(api, "sam", "TEAM-ALPHA").json()
    as_lecturer = team_as(api, "ada", "TEAM-ALPHA").json()

    assert as_student["invitations"] == [] and as_student["pending_invitations"] is None
    assert all(m["email"] is None for m in as_student["members"])
    assert {m["email"] for m in as_lecturer["members"]} == {
        "ada@example.com",
        "sam@example.com",
    }
    assert [
        i["email"] for i in as_lecturer["invitations"] if i["status"] == "pending"
    ] == ["kim@example.com"]
    assert as_lecturer["members"][0]["role"] == "lecturer"


def test_outsiders_cannot_see_a_team_but_administrators_can(api):
    lecturer(api)
    new_team(api)
    other_id = new_team(api, name="Other")["team"]["id"]
    student(api, "stranger")

    hidden = api.get("/teams/TEAM-ALPHA")
    by_id = api.get(f"/teams/{other_id}")

    api.sign_in("root", email="root@example.com", admin=True)
    visible = api.get("/teams/TEAM-ALPHA")

    assert hidden.status_code == 404 and by_id.status_code == 404
    assert visible.status_code == 200 and visible.json()["name"] == "Team Alpha"
    assert api.get("/teams/NOPE").status_code == 404


# --- managing --------------------------------------------------------------------------------


def test_lecturers_can_invite_more_people_and_reopen_old_invitations(api):
    lecturer(api)
    new_team(api, students=["sam@example.com"], leader_email=None)
    student(api, "sam")
    (invite,) = api.get("/me/invitations").json()
    api.post(f"/invitations/{invite['id']}/decline")
    api.sign_in("ada", email="ada@example.com")

    result = api.post(
        "/teams/TEAM-ALPHA/invitations",
        {"students": ["sam@example.com", "new@example.com"], "lecturers": []},
    )

    assert {r["email"]: r["outcome"] for r in result.json()["results"]} == {
        "sam@example.com": "reinvited",
        "new@example.com": "invited",
    }
    again = api.post("/teams/TEAM-ALPHA/invitations", {"students": ["new@example.com"]})
    assert again.json()["results"][0]["outcome"] == "already_invited"


def test_already_members_are_not_invited_again(api):
    lecturer(api)
    new_team(api, students=["sam@example.com"])
    join_all(api, people=("sam",))
    api.sign_in("ada", email="ada@example.com")

    result = api.post(
        "/teams/TEAM-ALPHA/invitations", {"students": ["sam@example.com"]}
    )

    assert result.json()["results"][0]["outcome"] == "already_member"


def test_a_leader_cannot_be_flagged_when_the_team_already_has_one(api):
    lecturer(api)
    new_team(api, students=["sam@example.com"])
    join_all(api, people=("sam",))
    api.sign_in("ada", email="ada@example.com")

    response = api.post(
        "/teams/TEAM-ALPHA/invitations",
        {"students": ["new@example.com"], "leader_email": "new@example.com"},
    )

    assert response.status_code == 400 and response.json()["code"] == "leader_exists"


def test_only_the_teams_lecturers_can_invite(api):
    lecturer(api, "ada")
    new_team(api, students=["sam@example.com"])
    join_all(api, people=("sam",))
    lecturer(api, "other")

    outsider = api.post(
        "/teams/TEAM-ALPHA/invitations", {"students": ["x@example.com"]}
    )
    api.sign_in("sam", email="sam@example.com")
    member = api.post("/teams/TEAM-ALPHA/invitations", {"students": ["x@example.com"]})

    assert outsider.status_code == 404
    assert member.status_code == 403 and member.json()["code"] == "role_not_allowed"


def test_a_co_lecturer_joins_as_an_evaluator(api):
    lecturer(api, "ada")
    new_team(api, students=[], lecturers=["grace@example.com"])
    lecturer(api, "grace")
    accept(api, "grace")

    team = api.get("/teams/TEAM-ALPHA").json()

    assert team["lecturer_count"] == 2 and team["student_count"] == 0
    assert team["my_role"] == "lecturer" and team["status"] == "forming"
    assert team["leader"] is None


def test_resending_replaces_the_link_and_revoking_closes_it(api):
    lecturer(api)
    new_team(api, students=["sam@example.com", "kim@example.com"])
    old = token_from(api, "sam@example.com")
    detail = api.get("/teams/TEAM-ALPHA").json()
    sam_inv = next(i for i in detail["invitations"] if i["email"] == "sam@example.com")
    kim_inv = next(i for i in detail["invitations"] if i["email"] == "kim@example.com")

    api.post(f"/teams/TEAM-ALPHA/invitations/{sam_inv['id']}/resend")
    revoked = api.delete(f"/teams/TEAM-ALPHA/invitations/{kim_inv['id']}")
    new = token_from(api, "sam@example.com")

    student(api, "sam")
    assert new != old
    assert api.post("/invitations/lookup", {"token": old}).status_code == 410
    assert api.post("/invitations/lookup", {"token": new}).status_code == 200
    assert revoked.status_code == 204
    student(api, "kim")
    assert api.get("/me/invitations").json() == []


def test_lecturers_can_rename_and_leaders_can_set_the_repository(api):
    lecturer(api)
    new_team(api, students=["sam@example.com", "kim@example.com"])
    join_all(api, people=("sam", "kim"))

    api.sign_in("kim", email="kim@example.com")
    kim_repo = api.patch("/teams/TEAM-ALPHA", {"repo_url": "https://github.com/x/y"})
    api.sign_in("sam", email="sam@example.com")  # the leader
    repo = api.patch("/teams/TEAM-ALPHA", {"repo_url": "https://github.com/selvia/app"})
    rename = api.patch("/teams/TEAM-ALPHA", {"name": "Hacked"})
    bad = api.patch("/teams/TEAM-ALPHA", {"repo_url": "javascript:alert(1)"})
    api.sign_in("ada", email="ada@example.com")
    renamed = api.patch("/teams/TEAM-ALPHA", {"name": "Team Omega"})

    assert kim_repo.status_code == 403
    assert (
        repo.status_code == 200
        and repo.json()["repo_url"] == "https://github.com/selvia/app"
    )
    assert rename.status_code == 403
    assert bad.status_code == 422
    assert renamed.json()["name"] == "Team Omega"


def test_invitation_quota_is_enforced(api, monkeypatch):
    monkeypatch.setattr(invitations, "MAX_OPEN_INVITATIONS_PER_PERSON", 2)
    lecturer(api)

    response = api.post(
        "/teams",
        {
            "name": "X",
            "term": TERM,
            "project_title": "Y",
            "students": ["a@example.com", "b@example.com", "c@example.com"],
        },
    )

    assert (
        response.status_code == 429
        and response.json()["code"] == "too_many_invitations"
    )
    assert api.get("/me/teams").json() == []


# --- leadership ------------------------------------------------------------------------------


def three_students(api):
    lecturer(api)
    new_team(api)
    join_all(api)


def user_id(api, sub):
    api.sign_in(sub, email=f"{sub}@example.com")
    return api.get("/me").json()["id"]


def test_leadership_moves_only_when_the_student_accepts(api):
    three_students(api)
    kim = user_id(api, "kim")
    api.sign_in("sam", email="sam@example.com")  # leader

    offer = api.post("/teams/TEAM-ALPHA/leader-transfer", {"to_user_id": kim})
    assert offer.json()["pending_leader"]["name"] == "Kim"
    assert offer.json()["leader"]["name"] == "Sam"
    assert any(
        "asked you to lead" in m.subject
        for m in api.email.outbox
        if m.to == "kim@example.com"
    )

    api.sign_in("kim", email="kim@example.com")
    accepted = api.post("/teams/TEAM-ALPHA/leader-transfer/accept")

    assert (
        accepted.json()["leader"]["name"] == "Kim"
        and accepted.json()["pending_leader"] is None
    )
    assert accepted.json()["my_role"] == "leader"
    assert any(
        "is now the leader" in m.subject
        for m in api.email.outbox
        if m.to == "sam@example.com"
    )


def test_declining_leadership_keeps_the_current_leader(api):
    three_students(api)
    kim = user_id(api, "kim")
    api.sign_in("sam", email="sam@example.com")
    api.post("/teams/TEAM-ALPHA/leader-transfer", {"to_user_id": kim})

    api.sign_in("kim", email="kim@example.com")
    declined = api.post("/teams/TEAM-ALPHA/leader-transfer/decline")

    assert (
        declined.json()["leader"]["name"] == "Sam"
        and declined.json()["pending_leader"] is None
    )
    assert api.post("/teams/TEAM-ALPHA/leader-transfer/accept").status_code == 404


def test_only_the_leader_or_a_lecturer_can_offer_leadership(api):
    three_students(api)
    lee = user_id(api, "lee")
    api.sign_in("kim", email="kim@example.com")  # not the leader

    response = api.post("/teams/TEAM-ALPHA/leader-transfer", {"to_user_id": lee})

    assert response.status_code == 403
    assert api.get("/teams/TEAM-ALPHA").json()["pending_leader"] is None


def test_leadership_can_only_go_to_another_student_in_the_team(api):
    three_students(api)
    ada = user_id(api, "ada")
    sam = user_id(api, "sam")
    api.sign_in("sam", email="sam@example.com")

    to_lecturer = api.post("/teams/TEAM-ALPHA/leader-transfer", {"to_user_id": ada})
    to_self = api.post("/teams/TEAM-ALPHA/leader-transfer", {"to_user_id": sam})
    to_stranger = api.post(
        "/teams/TEAM-ALPHA/leader-transfer",
        {"to_user_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert to_lecturer.json()["code"] == "not_a_student_member"
    assert to_self.json()["code"] == "already_leader"
    assert to_stranger.json()["code"] == "not_a_student_member"


def test_an_offer_can_be_withdrawn(api):
    three_students(api)
    kim = user_id(api, "kim")
    api.sign_in("sam", email="sam@example.com")
    api.post("/teams/TEAM-ALPHA/leader-transfer", {"to_user_id": kim})

    withdrawn = api.delete("/teams/TEAM-ALPHA/leader-transfer")

    assert withdrawn.json()["pending_leader"] is None
    api.sign_in("kim", email="kim@example.com")
    assert api.post("/teams/TEAM-ALPHA/leader-transfer/accept").status_code == 404


# --- leaving and removing --------------------------------------------------------------------


def test_the_leader_must_hand_over_before_leaving(api):
    three_students(api)
    sam = user_id(api, "sam")
    api.sign_in("sam", email="sam@example.com")

    refused = api.delete(f"/teams/TEAM-ALPHA/members/{sam}")

    assert (
        refused.status_code == 409 and refused.json()["code"] == "leader_must_transfer"
    )


def test_a_student_can_leave_and_then_join_another_team_that_term(api):
    three_students(api)
    kim = user_id(api, "kim")
    api.sign_in("kim", email="kim@example.com")

    left = api.delete(f"/teams/TEAM-ALPHA/members/{kim}")

    assert left.status_code == 204
    assert api.get("/me/teams").json() == []
    assert api.get("/teams/TEAM-ALPHA").status_code == 404
    assert (
        api.db().query(GroupMember).filter_by(term=TERM).count() == 2
    )  # sam and lee remain


def test_a_lecturer_removing_the_leader_promotes_the_longest_serving_student(api):
    three_students(api)
    sam = user_id(api, "sam")
    api.sign_in("ada", email="ada@example.com")

    removed = api.delete(f"/teams/TEAM-ALPHA/members/{sam}")
    team = api.get("/teams/TEAM-ALPHA").json()

    assert removed.status_code == 204
    assert team["student_count"] == 2
    assert team["leader"]["name"] == "Kim"  # joined after Sam, before Lee


def test_students_cannot_remove_other_people(api):
    three_students(api)
    sam = user_id(api, "sam")
    api.sign_in("lee", email="lee@example.com")

    response = api.delete(f"/teams/TEAM-ALPHA/members/{sam}")

    assert response.status_code == 403
    assert api.get("/teams/TEAM-ALPHA").json()["student_count"] == 3


def test_the_last_lecturer_cannot_leave(api):
    lecturer(api)
    new_team(api, students=[])
    ada = user_id(api, "ada")

    response = api.delete(f"/teams/TEAM-ALPHA/members/{ada}")

    assert response.status_code == 409 and response.json()["code"] == "last_lecturer"


def test_removing_everyone_returns_the_team_to_forming(api):
    lecturer(api)
    new_team(api, students=["sam@example.com"])
    join_all(api, people=("sam",))
    sam = user_id(api, "sam")
    api.sign_in("sam", email="sam@example.com")

    api.delete(f"/teams/TEAM-ALPHA/members/{sam}")
    api.sign_in("ada", email="ada@example.com")
    team = api.get("/teams/TEAM-ALPHA").json()

    assert team["status"] == "forming" and team["leader"] is None


# --- the home page list ----------------------------------------------------------------------


def test_my_teams_lists_only_my_teams_newest_first(api):
    lecturer(api, "ada")
    new_team(api, name="Old", students=["sam@example.com"])
    new_team(api, name="New", students=["sam@example.com"], term="2026-S2")
    lecturer(api, "grace")
    new_team(api, name="Graces", students=[])

    api.sign_in("ada", email="ada@example.com")
    ada = [t["name"] for t in api.get("/me/teams").json()]
    api.sign_in("grace", email="grace@example.com")
    grace = [t["name"] for t in api.get("/me/teams").json()]

    assert ada == ["New", "Old"]
    assert grace == ["Graces"]
