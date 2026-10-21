import pytest

from app.models import User, UserAvatar
from app.services import avatars
from tests.test_teams_api import accept, lecturer, new_team, student

# Just enough of each format for the checks that look at the first bytes.
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 64
GIF = b"GIF89a" + b"\x00" * 64

PROVIDER_PICTURE = "https://avatars.example.com/u/1"


def upload(api, data, content_type="image/jpeg"):
    return api.request(
        "PUT", "/me/picture", content=data, headers={"Content-Type": content_type}
    )


# --- uploading -----------------------------------------------------------------------------------


@pytest.mark.parametrize("data", [JPEG, PNG, WEBP])
def test_a_jpeg_png_or_webp_can_be_uploaded(api, data):
    student(api, "sam")

    response = upload(api, data)

    assert response.status_code == 200
    picture = response.json()["picture"]
    assert picture.startswith(f"/users/{response.json()['id']}/avatar?v=")


def test_what_is_stored_is_what_was_sent(api):
    sam = student(api, "sam")
    upload(api, PNG)

    fetched = api.get(f"/users/{sam}/avatar")

    assert fetched.status_code == 200
    assert fetched.content == PNG and fetched.headers["content-type"] == "image/png"
    assert fetched.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in fetched.headers["content-security-policy"]


@pytest.mark.parametrize("data", [GIF, b"<svg onload=alert(1)>", b"plain text", b""])
def test_other_files_are_refused_whatever_the_client_says(api, data):
    student(api, "sam")

    response = upload(api, data, content_type="image/jpeg")

    assert response.status_code == 400
    assert response.json()["code"] in ("unsupported_image", "empty_image")
    assert api.get("/me").json()["picture"] is None


def test_a_picture_over_500_kb_is_refused(api):
    student(api, "sam")

    response = upload(api, JPEG + b"\x00" * avatars.MAX_BYTES)

    assert response.status_code == 413 and response.json()["code"] == "image_too_large"


def test_uploading_again_replaces_the_picture(api):
    sam = student(api, "sam")
    upload(api, JPEG)
    upload(api, PNG)

    assert api.get(f"/users/{sam}/avatar").content == PNG
    assert api.db().query(UserAvatar).count() == 1


def test_a_picture_can_be_uploaded_before_onboarding_finishes(api):
    # onboarding sends the picture just after it creates the account
    api.sign_in("new", email="new@example.com")

    assert upload(api, JPEG).status_code == 200


# --- who sees it ------------------------------------------------------------------------------


def test_a_teammate_can_see_a_picture_but_a_stranger_cannot(api):
    lecturer(api)
    new_team(api, students=["sam@example.com", "kim@example.com"])
    for sub in ("sam", "kim"):
        student(api, sub)
        accept(api, sub)
    api.sign_in("sam", email="sam@example.com")
    sam_id = api.get("/me").json()["id"]
    upload(api, JPEG)

    api.sign_in("kim", email="kim@example.com")
    teammate = api.get(f"/users/{sam_id}/avatar")
    student(api, "zed")  # in no team with sam
    stranger = api.get(f"/users/{sam_id}/avatar")

    assert teammate.status_code == 200
    assert stranger.status_code == 404


def test_an_administrator_can_see_any_picture(api):
    sam = student(api, "sam")
    upload(api, JPEG)

    api.sign_in("root", email="root@example.com", admin=True)

    assert api.get(f"/users/{sam}/avatar").status_code == 200


def test_the_members_list_carries_each_persons_picture(api):
    lecturer(api)
    new_team(api, students=["sam@example.com"])
    student(api, "sam")
    accept(api, "sam")
    upload(api, PNG)

    api.sign_in("ada", email="ada@example.com")
    members = api.get("/teams/TEAM-ALPHA").json()["members"]

    sam = next(m for m in members if m["role"] != "lecturer")
    assert sam["picture"].startswith("/users/")
    assert next(m for m in members if m["role"] == "lecturer")["picture"] is None


# --- removing, and the provider's picture ----------------------------------------------------


def test_removing_the_upload_shows_the_providers_picture_again(api):
    api.sign_in("sam", email="sam@example.com", picture=PROVIDER_PICTURE)
    onboard_sam(api)
    assert api.get("/me").json()["picture"] == PROVIDER_PICTURE

    mine = upload(api, JPEG).json()["picture"]
    assert mine.startswith("/users/")

    removed = api.delete("/me/picture")

    assert removed.json()["picture"] == PROVIDER_PICTURE
    assert api.db().query(UserAvatar).count() == 0


def test_removing_with_nothing_uploaded_is_fine(api):
    student(api, "sam")

    response = api.delete("/me/picture")

    assert response.status_code == 200 and response.json()["picture"] is None


def onboard_sam(api):
    from app.services.accounts import CONSENT_VERSION

    api.sign_in("sam", email="sam@example.com", name="Sam", picture=PROVIDER_PICTURE)
    response = api.post(
        "/me/onboarding",
        {
            "account_type": "student",
            "display_name": "Sam",
            "github_username": "gh-sam",
            "accept_terms": True,
            "consent_version": CONSENT_VERSION,
        },
    )
    assert response.status_code == 200, response.text


def test_the_provider_picture_is_saved_and_kept_current(api):
    onboard_sam(api)
    assert api.get("/me").json()["picture"] == PROVIDER_PICTURE

    api.sign_in(
        "sam", email="sam@example.com", picture="https://avatars.example.com/u/2"
    )
    assert api.get("/me").json()["picture"] == "https://avatars.example.com/u/2"

    # a sign-in that carries no picture does not wipe it
    api.sign_in("sam", email="sam@example.com")
    assert api.get("/me").json()["picture"] == "https://avatars.example.com/u/2"


@pytest.mark.parametrize(
    "address",
    [
        "javascript:alert(1)",
        "data:image/png;base64,AAAA",
        "ftp://x/y.png",
        "https://x/" + "a" * 1100,
    ],
)
def test_only_plain_web_addresses_are_kept_as_a_provider_picture(api, address):
    api.sign_in("sam", email="sam@example.com", picture=address)

    assert api.get("/me").json()["picture"] is None
    assert api.db().query(User).one().picture_url is None


def test_an_upload_wins_over_the_providers_picture(api):
    onboard_sam(api)

    response = upload(api, JPEG)

    assert response.json()["picture"].startswith("/users/")
