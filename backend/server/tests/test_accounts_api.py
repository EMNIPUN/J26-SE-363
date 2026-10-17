import pytest

from app.models import User
from app.services.accounts import CONSENT_VERSION

STUDENT = {
    "account_type": "student",
    "display_name": "Sam Silva",
    "institution": "Example University",
    "student_number": "IT23155534",
    "github_username": "Sam-Silva",
    "accept_terms": True,
    "consent_version": CONSENT_VERSION,
}
LECTURER = {
    "account_type": "lecturer",
    "display_name": "Dr. Ada Perera",
    "institution": "Example University",
    "department": "Software Engineering",
    "title": "Senior Lecturer",
    "accept_terms": True,
    "consent_version": CONSENT_VERSION,
}


def onboard(api, sub, body, email=None):
    api.sign_in(sub, email=email or f"{sub}@example.com", name="From Keycloak")
    response = api.post("/me/onboarding", body)
    assert response.status_code == 200, response.text
    return response.json()


# --- first sight -----------------------------------------------------------------------------


def test_first_request_creates_the_account_without_a_role(api):
    api.sign_in("kc-1", email="Ada@Example.com", name="Ada Perera")

    response = api.get("/me")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Ada Perera"
    assert body["email"] == "ada@example.com"  # stored in lower case
    assert body["role"] is None
    assert body["onboarding_completed"] is False
    assert body["email_verified"] is True
    assert body["current_consent_version"] == CONSENT_VERSION
    assert api.db().query(User).count() == 1


def test_repeated_requests_reuse_the_account_and_follow_email_changes(api):
    api.sign_in("kc-1", email="old@example.com")
    first = api.get("/me").json()["id"]
    api.sign_in("kc-1", email="new@example.com")

    again = api.get("/me").json()

    assert again["id"] == first
    assert again["email"] == "new@example.com"
    assert api.db().query(User).count() == 1


def test_name_falls_back_to_username_then_email(api):
    api.sign_in("kc-1", email="ada@example.com", name=None)
    assert api.get("/me").json()["name"] == "kc-1"


def test_unverified_email_is_reported(api):
    api.sign_in("kc-1", email="ada@example.com", verified=False)
    assert api.get("/me").json()["email_verified"] is False


def test_requests_without_a_token_are_rejected(api):
    api.sign_out()
    assert api.get("/me").status_code == 401


# --- onboarding ------------------------------------------------------------------------------


def test_student_onboarding_sets_role_and_profile(api):
    body = onboard(api, "kc-1", STUDENT)

    assert body["role"] == "student"
    assert body["onboarding_completed"] is True
    assert body["name"] == "Sam Silva"
    assert body["profile"]["github_username"] == "sam-silva"  # stored in lower case
    assert body["profile"]["student_number"] == "IT23155534"
    assert body["profile"]["department"] is None
    assert body["consent_version"] == CONSENT_VERSION


def test_lecturer_onboarding_needs_no_approval(api):
    body = onboard(api, "kc-2", LECTURER)

    assert body["role"] == "lecturer"
    assert body["onboarding_completed"] is True
    assert body["profile"]["department"] == "Software Engineering"
    assert body["profile"]["github_username"] is None


def test_irrelevant_fields_are_dropped(api):
    body = onboard(
        api, "kc-2", {**LECTURER, "github_username": "ada", "student_number": "X1"}
    )

    assert body["profile"]["github_username"] is None
    assert body["profile"]["student_number"] is None


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"accept_terms": False}, "accept_terms"),
        ({"github_username": None}, "github_username"),
        ({"github_username": "-bad"}, "github_username"),
        ({"github_username": "has space"}, "github_username"),
        ({"github_username": "a" * 40}, "github_username"),
        ({"display_name": "   "}, "display_name"),
        ({"account_type": "admin"}, "account_type"),
    ],
)
def test_invalid_onboarding_is_rejected(api, change, field):
    api.sign_in("kc-1", email="a@example.com")

    response = api.post("/me/onboarding", {**STUDENT, **change})

    assert response.status_code == 422
    assert api.get("/me").json()["onboarding_completed"] is False


def test_onboarding_cannot_be_repeated_to_change_the_role(api):
    onboard(api, "kc-1", STUDENT)

    response = api.post("/me/onboarding", LECTURER)

    assert response.status_code == 409
    assert response.json()["code"] == "already_onboarded"
    assert api.get("/me").json()["role"] == "student"


def test_outdated_terms_are_refused(api):
    api.sign_in("kc-1", email="a@example.com")

    response = api.post("/me/onboarding", {**STUDENT, "consent_version": "1999-01"})

    assert response.status_code == 409
    assert response.json()["code"] == "consent_outdated"


def test_github_username_and_student_number_are_unique(api):
    onboard(api, "kc-1", STUDENT)
    api.sign_in("kc-2", email="b@example.com")

    same_github = api.post(
        "/me/onboarding",
        {**STUDENT, "student_number": "IT1", "github_username": "SAM-silva"},
    )
    same_number = api.post(
        "/me/onboarding", {**STUDENT, "github_username": "someone-else"}
    )

    assert same_github.status_code == 409
    assert same_github.json()["code"] == "github_username_taken"
    assert same_number.status_code == 409
    assert same_number.json()["code"] == "student_number_taken"
    assert api.get("/me").json()["onboarding_completed"] is False


def test_administrators_skip_onboarding_and_cannot_choose_a_role(api):
    api.sign_in("kc-admin", email="root@example.com", admin=True)

    me = api.get("/me").json()
    response = api.post("/me/onboarding", LECTURER)

    assert me["role"] == "admin"
    assert me["onboarding_completed"] is True
    assert response.status_code == 409


# --- profile ---------------------------------------------------------------------------------


def test_profile_updates_change_only_the_fields_sent(api):
    onboard(api, "kc-1", STUDENT)

    response = api.patch("/me/profile", {"institution": "Other University"})

    profile = response.json()["profile"]
    assert profile["institution"] == "Other University"
    assert profile["github_username"] == "sam-silva"
    assert profile["student_number"] == "IT23155534"


def test_profile_update_can_rename_and_change_github(api):
    onboard(api, "kc-1", STUDENT)

    body = api.patch(
        "/me/profile", {"display_name": "Samantha Silva", "github_username": "samantha"}
    ).json()

    assert body["name"] == "Samantha Silva"
    assert body["profile"]["github_username"] == "samantha"
    assert body["role"] == "student"


def test_students_cannot_remove_their_github_username(api):
    onboard(api, "kc-1", STUDENT)

    response = api.patch("/me/profile", {"github_username": None})

    assert response.status_code == 409
    assert response.json()["code"] == "github_username_required"


def test_profile_update_cannot_change_the_role(api):
    onboard(api, "kc-1", STUDENT)

    api.patch("/me/profile", {"account_type": "lecturer", "role": "lecturer"})

    assert api.get("/me").json()["role"] == "student"


def test_profile_needs_onboarding_first(api):
    api.sign_in("kc-1", email="a@example.com")

    response = api.patch("/me/profile", {"institution": "X"})

    assert response.status_code == 403
    assert response.json()["code"] == "onboarding_required"
