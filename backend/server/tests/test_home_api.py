import pytest

from tests.test_teams_api import (
    TERM,
    accept,
    add_term,
    new_team,
    onboard,
    student,
    three_students,
    user_id,
)

UNIVERSITY = "Example University"


def lecturer_at(api, sub="ada", institution=UNIVERSITY):
    extra = {"institution": institution} if institution else {}
    return onboard(api, sub, "lecturer", **extra)


def student_at(api, sub, institution=UNIVERSITY):
    extra = {"institution": institution} if institution else {}
    return onboard(api, sub, "student", **extra)


def available(api, term=TERM):
    response = api.get(f"/students/available?term={term}")
    assert response.status_code == 200, response.text
    return response.json()


# --- students without a team ---------------------------------------------------------------


def test_only_students_of_the_lecturers_institution_without_a_team_are_listed(api):
    student_at(api, "sam")
    student_at(
        api, "kim", institution="EXAMPLE university "
    )  # same place, spelled differently
    student_at(api, "lee", institution="Another College")
    student_at(api, "noi", institution=None)
    lecturer_at(api)

    listed = available(api)

    assert listed["institution"] == UNIVERSITY
    assert [s["name"] for s in listed["students"]] == ["Kim", "Sam"]


def test_the_list_carries_no_email(api):
    student_at(api, "sam")
    lecturer_at(api)

    only = available(api)["students"][0]

    assert set(only) == {"id", "name", "institution", "github_username", "picture"}


def test_a_student_already_in_a_team_this_term_is_left_out_but_not_for_another_term(
    api,
):
    student_at(api, "sam")
    student_at(api, "kim")
    lecturer_at(api)
    new_team(api, students=["sam@example.com"])
    accept(api, "sam")
    api.sign_in("ada", email="ada@example.com")

    assert [s["name"] for s in available(api)["students"]] == ["Kim"]
    assert {s["name"] for s in available(api, term="2027-S1")["students"]} == {
        "Kim",
        "Sam",
    }


def test_a_lecturer_without_an_institution_sees_nobody(api):
    student_at(api, "sam")
    lecturer_at(api, institution=None)

    listed = available(api)

    assert listed["institution"] is None and listed["students"] == []


def test_students_cannot_ask_for_the_list(api):
    student_at(api, "sam")

    response = api.get(f"/students/available?term={TERM}")

    assert response.status_code == 403 and response.json()["code"] == "role_not_allowed"


# --- inviting them by id ----------------------------------------------------------------------


def test_picked_students_are_invited_by_id_and_emailed(api):
    sam = student_at(api, "sam")
    lecturer_at(api)
    code = new_team(api, students=[])["team"]["code"]

    response = api.post(f"/teams/{code}/invitations", {"student_ids": [sam]})

    assert response.status_code == 200
    assert response.json()["results"][0]["outcome"] == "invited"
    assert [m.to for m in api.email.outbox] == ["sam@example.com"]


def test_a_student_from_another_institution_cannot_be_invited_by_id(api):
    stranger = student_at(api, "lee", institution="Another College")
    lecturer_at(api)
    code = new_team(api, students=[])["team"]["code"]
    api.email.outbox.clear()

    response = api.post(f"/teams/{code}/invitations", {"student_ids": [stranger]})

    assert (
        response.status_code == 400
        and response.json()["code"] == "student_not_available"
    )
    assert api.email.outbox == []


def test_a_student_already_in_a_team_that_term_cannot_be_invited_again(api):
    sam = student_at(api, "sam")
    lecturer_at(api)
    new_team(api, students=["sam@example.com"])
    accept(api, "sam")
    api.sign_in("ada", email="ada@example.com")
    add_term(api, TERM)
    other = api.post("/teams", {"name": "Other", "term": TERM}).json()["code"]

    response = api.post(f"/teams/{other}/invitations", {"student_ids": [sam]})

    assert (
        response.status_code == 400
        and response.json()["code"] == "student_not_available"
    )


def test_an_id_that_is_not_a_student_is_refused(api):
    boss = lecturer_at(api, "grace")
    lecturer_at(api, "ada")
    code = new_team(api, students=[])["team"]["code"]

    response = api.post(f"/teams/{code}/invitations", {"student_ids": [boss]})

    assert (
        response.status_code == 400
        and response.json()["code"] == "student_not_available"
    )


# --- invitations still waiting -----------------------------------------------------------------


def test_the_lecturer_sees_their_unanswered_invitations_oldest_first(api):
    lecturer(api)
    new_team(
        api,
        students=["sam@example.com", "kim@example.com"],
        lecturers=["grace@example.com"],
    )

    sent = api.get("/invitations/sent").json()

    assert {i["email"] for i in sent} == {
        "sam@example.com",
        "kim@example.com",
        "grace@example.com",
    }
    assert [i["created_at"] for i in sent] == sorted(i["created_at"] for i in sent)
    assert {"team_code", "team_name", "id", "expires_at", "role"} <= set(sent[0])


def test_answered_invitations_and_unfinished_teams_are_not_listed(api):
    lecturer(api)
    new_team(api, students=["sam@example.com", "kim@example.com"])
    new_team(api, name="Draft", finish=False, students=["lee@example.com"])
    student(api, "sam")
    accept(api, "sam")
    api.sign_in("ada", email="ada@example.com")

    sent = api.get("/invitations/sent").json()

    assert [i["email"] for i in sent] == ["kim@example.com"]


def test_nobody_sees_invitations_sent_by_someone_else(api):
    lecturer(api, "ada")
    new_team(api, students=["sam@example.com"])
    lecturer(api, "grace")

    assert api.get("/invitations/sent").json() == []


def test_students_cannot_list_sent_invitations(api):
    student(api, "sam")

    assert api.get("/invitations/sent").status_code == 403


# --- what the team list says about the viewer ---------------------------------------------------


def test_the_team_list_counts_waiting_student_invitations(api):
    lecturer(api)
    new_team(
        api,
        students=["sam@example.com", "kim@example.com"],
        lecturers=["grace@example.com"],
    )

    summary = api.get("/me/teams").json()[0]

    assert summary["pending_invitations"] == 3
    assert summary["pending_student_invitations"] == 2


def test_a_leadership_offer_is_flagged_for_the_student_it_is_offered_to(api):
    three_students(api)
    kim = user_id(api, "kim")
    api.sign_in("sam", email="sam@example.com")  # the leader
    api.post("/teams/TEAM-ALPHA/leader-transfer", {"to_user_id": kim})

    api.sign_in("kim", email="kim@example.com")
    assert api.get("/me/teams").json()[0]["leadership_offer_to_me"] is True

    api.sign_in("lee", email="lee@example.com")
    assert api.get("/me/teams").json()[0]["leadership_offer_to_me"] is False


@pytest.mark.parametrize("sub", ["ada"])
def test_students_see_no_invitation_counts(api, sub):
    three_students(api)

    api.sign_in("sam", email="sam@example.com")
    summary = api.get("/me/teams").json()[0]

    assert summary["pending_invitations"] is None
    assert summary["pending_student_invitations"] is None


def lecturer(api, sub="ada"):
    return onboard(api, sub, "lecturer")
