from datetime import timedelta

import pytest

from app.models import Notification
from app.services import team_rules as rules
from tests.test_teams_api import (
    accept,
    lecturer,
    new_team,
    student,
    three_students,
    user_id,
)


def inbox(api, sub):
    api.sign_in(sub, email=f"{sub}@example.com")
    response = api.get("/me/notifications")
    assert response.status_code == 200, response.text
    return response.json()


def kinds(listing):
    return [item["kind"] for item in listing["items"]]


def offer_leadership(api, to="kim", by="sam"):
    target = user_id(api, to)
    api.sign_in(by, email=f"{by}@example.com")
    response = api.post("/teams/TEAM-ALPHA/leader-transfer", {"to_user_id": target})
    assert response.status_code == 200, response.text


# --- a leadership offer reaches the person, in the app and by email ----------------------------


def test_a_leadership_offer_shows_in_the_bell_with_buttons_and_is_emailed(api):
    three_students(api)
    api.email.outbox.clear()

    offer_leadership(api)

    listing = inbox(api, "kim")
    offer = next(i for i in listing["items"] if i["kind"] == "leadership_offered")
    assert offer["title"] == "Sam offered you team leadership of Team Alpha"
    assert offer["actions"] == ["accept", "decline"]
    assert offer["link"] == "/teams/TEAM-ALPHA/members"
    assert offer["data"]["team_code"] == "TEAM-ALPHA"
    assert listing["unread_count"] >= 1 and offer["read"] is False
    mail = [m for m in api.email.outbox if m.to == "kim@example.com"]
    assert len(mail) == 1 and "/teams/TEAM-ALPHA/members" in mail[0].text


def test_accepting_closes_the_offer_and_tells_the_offerer(api):
    three_students(api)
    offer_leadership(api)
    api.email.outbox.clear()

    api.sign_in("kim", email="kim@example.com")
    assert api.post("/teams/TEAM-ALPHA/leader-transfer/accept").status_code == 200

    mine = next(
        i for i in inbox(api, "kim")["items"] if i["kind"] == "leadership_offered"
    )
    assert mine["actions"] == [] and mine["read"] is True
    told = inbox(api, "sam")
    answer = next(i for i in told["items"] if i["kind"] == "leadership_answered")
    assert answer["title"] == "Kim is now the leader of Team Alpha"
    assert [m.to for m in api.email.outbox] == ["sam@example.com"]


def test_declining_tells_the_offerer_and_changes_nothing(api):
    three_students(api)
    offer_leadership(api)

    api.sign_in("kim", email="kim@example.com")
    api.post("/teams/TEAM-ALPHA/leader-transfer/decline")

    answer = next(
        i for i in inbox(api, "sam")["items"] if i["kind"] == "leadership_answered"
    )
    assert answer["title"] == "Kim declined to lead Team Alpha"
    assert (
        next(
            i for i in inbox(api, "kim")["items"] if i["kind"] == "leadership_offered"
        )["actions"]
        == []
    )


def test_withdrawing_an_offer_closes_it_for_the_student(api):
    three_students(api)
    offer_leadership(api)

    api.sign_in("sam", email="sam@example.com")
    assert api.delete("/teams/TEAM-ALPHA/leader-transfer").status_code == 200

    items = inbox(api, "kim")["items"]
    assert next(i for i in items if i["kind"] == "leadership_offered")["actions"] == []
    assert "leadership_withdrawn" in kinds({"items": items})


def test_a_new_offer_replaces_the_old_one(api):
    three_students(api)
    offer_leadership(api, to="kim")
    offer_leadership(api, to="kim")

    offers = [
        i for i in inbox(api, "kim")["items"] if i["kind"] == "leadership_offered"
    ]

    assert sorted(len(o["actions"]) for o in offers) == [0, 2]  # one closed, one open


def test_someone_who_is_removed_loses_the_offer_they_held(api):
    three_students(api)
    offer_leadership(api, to="kim")
    kim = user_id(api, "kim")  # (signs in as Kim to read the id)
    api.sign_in("ada", email="ada@example.com")
    assert api.delete(f"/teams/TEAM-ALPHA/members/{kim}").status_code == 204

    items = inbox(api, "kim")["items"]

    assert next(i for i in items if i["kind"] == "leadership_offered")["actions"] == []
    assert "member_removed" in kinds({"items": items})


# --- invitations --------------------------------------------------------------------------------


def test_an_invited_student_sees_the_invitation_in_the_bell_and_can_answer_it(api):
    lecturer(api)
    new_team(api, students=["sam@example.com"])
    student(api, "sam")

    listing = inbox(api, "sam")

    invite = next(i for i in listing["items"] if i["kind"] == "team_invitation")
    assert (
        invite["actions"] == ["accept", "decline"] and invite["link"] == "/invitations"
    )
    assert (
        invite["data"]["invitation_id"] and invite["data"]["team_code"] == "TEAM-ALPHA"
    )
    # answering it anywhere closes it, and the inviter hears about it
    accept(api, "sam")
    assert inbox(api, "sam")["items"][0]["actions"] == []
    told = inbox(api, "ada")
    assert "invitation_answered" in kinds(told)


def test_an_invitation_to_an_unfinished_team_is_not_shown(api):
    lecturer(api)
    new_team(api, finish=False, students=["sam@example.com"])
    student(api, "sam")

    assert inbox(api, "sam")["items"] == []


def test_nothing_is_shown_for_an_unverified_email(api):
    lecturer(api)
    new_team(api, students=["sam@example.com"])
    student(api, "sam")
    api.sign_in("sam", email="sam@example.com", verified=False)

    assert api.get("/me/notifications").json()["items"] == []


def test_a_withdrawn_invitation_closes_its_notification(api):
    lecturer(api)
    new_team(api, students=["sam@example.com"])
    student(api, "sam")
    inbox(api, "sam")  # seen once
    api.sign_in("ada", email="ada@example.com")
    sam = next(
        i
        for i in api.get("/teams/TEAM-ALPHA").json()["invitations"]
        if i["email"] == "sam@example.com"
    )
    api.delete(f"/teams/TEAM-ALPHA/invitations/{sam['id']}")

    assert inbox(api, "sam")["items"][0]["actions"] == []


# --- people leaving -------------------------------------------------------------------------------


def test_lecturers_are_told_when_a_student_leaves(api):
    three_students(api)
    api.email.outbox.clear()
    api.sign_in("lee", email="lee@example.com")
    api.delete(f"/teams/TEAM-ALPHA/members/{user_id(api, 'lee')}")

    told = inbox(api, "ada")["items"]

    assert any(
        i["kind"] == "member_left" and i["title"] == "Lee left Team Alpha" for i in told
    )
    assert [m.to for m in api.email.outbox] == ["ada@example.com"]


# --- reading, closing, paging ---------------------------------------------------------------------


def test_marking_read_and_dismissing(api):
    three_students(api)
    offer_leadership(api)
    listing = inbox(api, "kim")
    first = listing["items"][0]
    before = listing["unread_count"]

    assert api.post(f"/me/notifications/{first['id']}/read").status_code == 204
    assert api.get("/me/notifications").json()["unread_count"] == before - 1
    assert api.post("/me/notifications/read-all").status_code == 204
    assert api.get("/me/notifications").json()["unread_count"] == 0
    assert api.delete(f"/me/notifications/{first['id']}").status_code == 204
    assert all(
        i["id"] != first["id"] for i in api.get("/me/notifications").json()["items"]
    )


def test_nobody_can_touch_someone_elses_notification(api):
    three_students(api)
    offer_leadership(api)
    theirs = inbox(api, "kim")["items"][0]["id"]

    api.sign_in("lee", email="lee@example.com")

    assert api.post(f"/me/notifications/{theirs}/read").status_code == 404
    assert api.delete(f"/me/notifications/{theirs}").status_code == 404


def test_pages_are_newest_first_and_chained(api):
    three_students(api)
    for _ in range(3):  # each new offer is a new notification
        offer_leadership(api, to="kim")
    api.sign_in("kim", email="kim@example.com")

    page_one = api.get("/me/notifications?limit=2").json()
    page_two = api.get(
        "/me/notifications", params={"limit": 2, "before": page_one["next_before"]}
    ).json()

    assert len(page_one["items"]) == 2 and page_one["next_before"] is not None
    times = [i["created_at"] for i in page_one["items"] + page_two["items"]]
    assert times == sorted(times, reverse=True)
    ids = {i["id"] for i in page_one["items"]}
    assert ids.isdisjoint({i["id"] for i in page_two["items"]})


def test_old_notifications_are_dropped(api):
    three_students(api)
    offer_leadership(api)
    api.sign_in("kim", email="kim@example.com")
    db = api.db()
    old = Notification(
        user_id=db.query(Notification)
        .filter_by(kind="leadership_offered")
        .one()
        .user_id,
        kind="member_left",
        title="Ancient",
        created_at=rules.utcnow() - timedelta(days=200),
    )
    db.add(old)
    db.commit()

    titles = [i["title"] for i in api.get("/me/notifications").json()["items"]]

    assert "Ancient" not in titles


# --- email preferences ----------------------------------------------------------------------------


def test_by_default_every_email_is_wanted(api):
    student(api, "sam")

    categories = {
        c["category"]: c
        for c in api.get("/me/notification-preferences").json()["categories"]
    }

    assert set(categories) == {"invitations", "leadership", "activity"}
    assert all(c["email_enabled"] for c in categories.values())
    assert categories["invitations"]["configurable"] is False
    assert categories["leadership"]["configurable"] is True


def test_turning_off_leadership_email_keeps_the_in_app_notification(api):
    three_students(api)
    api.sign_in("kim", email="kim@example.com")
    assert (
        api.put(
            "/me/notification-preferences", {"email": {"leadership": False}}
        ).status_code
        == 200
    )
    api.email.outbox.clear()

    offer_leadership(api)

    assert [m for m in api.email.outbox if m.to == "kim@example.com"] == []
    assert "leadership_offered" in kinds(inbox(api, "kim"))
    # other people's choices are their own
    assert api.get("/me/notification-preferences").json() is not None


def test_invitation_emails_cannot_be_turned_off(api):
    student(api, "sam")

    refused = api.put("/me/notification-preferences", {"email": {"invitations": False}})

    assert refused.status_code == 400 and refused.json()["code"] == "not_configurable"
    unknown = api.put("/me/notification-preferences", {"email": {"nonsense": True}})
    assert unknown.status_code == 400 and unknown.json()["code"] == "unknown_category"


def test_a_choice_can_be_changed_back(api):
    student(api, "sam")
    api.put("/me/notification-preferences", {"email": {"activity": False}})
    api.put("/me/notification-preferences", {"email": {"activity": True}})

    categories = {
        c["category"]: c
        for c in api.get("/me/notification-preferences").json()["categories"]
    }

    assert categories["activity"]["email_enabled"] is True


@pytest.mark.parametrize("path", ["/me/notifications", "/me/notification-preferences"])
def test_a_new_account_must_finish_onboarding_first(api, path):
    api.sign_in("new", email="new@example.com")

    response = api.get(path)

    assert (
        response.status_code == 403 and response.json()["code"] == "onboarding_required"
    )
