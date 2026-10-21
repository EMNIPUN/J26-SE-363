"""Linking GitHub through the API with GitHub replaced by a fake: the leader installs the App and picks a repository, members sign in to GitHub, and the readiness the assessment starts from."""
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from shared.github_app import GitHubApp, sign_state

from app.api.v1.github import get_github_app
from app.main import app as fastapi_app
from tests.test_github_app import CONFIG, fake_github
from tests.test_teams_api import join_all, lecturer, new_team, student

GITHUB_IDS = {"good-ann": (4242, "Ann-Dev"), "good-bob": (4343, "bob"), "good-lee": (4444, "stranger")}


def handler_for(calls):
    base = fake_github(calls)

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/acme/app/collaborators/ann-dev/permission":
            return httpx.Response(200, json={"permission": "write"})
        if path == "/app/installations/7":
            return httpx.Response(200, json={"account": {"login": "sam-dev", "type": "User"}})
        if path == "/login/oauth/access_token":
            for code, who in GITHUB_IDS.items():
                if code.encode() in request.content:
                    return httpx.Response(200, json={"access_token": f"ghu_{who[0]}"})
            return httpx.Response(200, json={"error": "bad_verification_code"})
        if path == "/user":
            who = next(w for w in GITHUB_IDS.values() if f"ghu_{w[0]}" in request.headers["authorization"])
            return httpx.Response(200, json={"id": who[0], "login": who[1], "avatar_url": None})
        return base(request)

    return handler


@pytest.fixture()
def gh(api):
    calls = []
    fake = GitHubApp(CONFIG, client=httpx.Client(transport=httpx.MockTransport(handler_for(calls))))
    fastapi_app.dependency_overrides[get_github_app] = lambda: fake
    api.github, api.calls = fake, calls
    return api


def make_team(api):
    """Ada (lecturer) creates a team whose leader is Sam; Sam, Kim and Lee join."""
    lecturer(api, "ada")
    new_team(api, leader_email="sam@example.com")
    join_all(api)
    return "TEAM-ALPHA"


def as_user(api, sub):
    api.sign_in(sub, email=f"{sub}@example.com", name=sub.title())


def install(api, code="TEAM-ALPHA", installation=7, sub="sam"):
    as_user(api, sub)
    url = api.post(f"/teams/{code}/github/install").json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    api.sign_out()  # GitHub sends the browser back; the request carries the state, not a token
    return api.get("/github/installed", params={"installation_id": installation, "state": state, "setup_action": "install"}, follow_redirects=False)


def connect(api, sub, code, team="TEAM-ALPHA"):
    as_user(api, sub)
    url = api.post("/me/github/connect", params={"back": "/profile", "team": team}).json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    api.sign_out()
    return api.get("/github/callback", params={"code": code, "state": state}, follow_redirects=False)


def test_the_leader_installs_the_app_and_picks_the_repository(gh):
    code = make_team(gh)
    r = install(gh)
    assert r.status_code in (302, 307) and "/teams/TEAM-ALPHA/access?github=installed" in r.headers["location"]
    as_user(gh, "sam")
    repos = gh.get(f"/teams/{code}/github/repos").json()
    assert [x["full_name"] for x in repos] == ["acme/app", "acme/docs"]
    state = gh.put(f"/teams/{code}/github/repo", {"full_name": "acme/app"}).json()
    assert state["repo"] == "acme/app" and not state["ready"] and "connected a GitHub account" in state["blockers"][0]
    assert gh.get(f"/teams/{code}").json()["repo_url"] == "https://github.com/acme/app"
    assert gh.put(f"/teams/{code}/github/repo", {"full_name": "acme/secret"}).status_code == 400  # not a repository the App can see


def test_only_the_leader_and_lecturers_can_link_and_outsiders_see_nothing(gh):
    code = make_team(gh)
    as_user(gh, "kim")  # a member, not the leader
    assert gh.post(f"/teams/{code}/github/install").status_code == 403
    assert gh.get(f"/teams/{code}/github/repos").status_code == 403
    student(gh, "eve")  # signs up, belongs to no team
    assert gh.get(f"/teams/{code}/github").status_code == 404
    assert gh.post(f"/teams/{code}/github/install").status_code == 404
    as_user(gh, "ada")  # the lecturer may
    assert gh.post(f"/teams/{code}/github/install").status_code == 200


def test_a_forged_or_expired_link_back_from_github_changes_nothing(gh):
    code = make_team(gh)
    gh.sign_out()
    for state in ("garbage", sign_state("wrong-secret", {"purpose": "install", "user": "x", "team": "y"}), sign_state(CONFIG.state_secret, {"purpose": "connect", "user": "x"}),
                  sign_state(CONFIG.state_secret, {"purpose": "install", "user": "x", "team": "y"}, ttl=-5)):
        r = gh.get("/github/installed", params={"installation_id": 7, "state": state}, follow_redirects=False)
        assert r.status_code in (302, 307) and "github=error" in r.headers["location"]
    as_user(gh, "ada")
    assert gh.get(f"/teams/{code}/github").json()["repo"] is None


def test_a_student_who_is_not_the_leader_cannot_complete_an_install_for_the_team(gh):
    code = make_team(gh)
    as_user(gh, "kim")
    team_id = gh.get(f"/teams/{code}").json()["id"]
    user_id = gh.get("/me").json()["id"]
    gh.sign_out()
    state = sign_state(CONFIG.state_secret, {"purpose": "install", "user": user_id, "team": team_id})
    r = gh.get("/github/installed", params={"installation_id": 7, "state": state}, follow_redirects=False)
    assert "github=error" in r.headers["location"]


def test_members_connect_their_github_accounts_and_the_team_becomes_ready(gh):
    code = make_team(gh)
    install(gh)
    as_user(gh, "sam")
    gh.put(f"/teams/{code}/github/repo", {"full_name": "acme/app"})
    gh.sign_out()
    ok = connect(gh, "sam", "good-ann")  # Sam's own GitHub account is "ann-dev" in this fake
    assert ok.status_code in (302, 307) and ok.headers["location"].endswith("/profile?github=connected")
    as_user(gh, "sam")
    assert gh.get("/me/github").json()["login"] == "ann-dev"
    state = gh.get(f"/teams/{code}/github").json()
    sam = next(m for m in state["members"] if m["name"] == "Sam")
    assert sam["login"] == "ann-dev" and sam["permission"] == "write" and sam["state"] == "ready" and state["ready"]
    assert {m["state"] for m in state["members"] if m["name"] != "Sam"} == {"not_connected"} and len(state["notes"]) == 2
    connect(gh, "kim", "good-bob")  # "bob" has read access only
    connect(gh, "lee", "good-lee")  # "stranger" has none
    as_user(gh, "sam")
    states = {m["name"]: m["state"] for m in gh.get(f"/teams/{code}/github").json()["members"]}
    assert states == {"Sam": "ready", "Kim": "read_only", "Lee": "no_access"}


def test_a_member_cannot_connect_before_the_leader_has_linked_the_repository(gh):
    code = make_team(gh)
    as_user(gh, "kim")
    r = gh.post("/me/github/connect", params={"team": code})
    assert r.status_code == 400 and r.json()["code"] == "leader_must_link_first"
    student(gh, "eve")  # not in the team at all
    assert gh.post("/me/github/connect", params={"team": code}).status_code == 404


def test_a_github_account_can_belong_to_only_one_person(gh):
    code = make_team(gh)
    install(gh)
    as_user(gh, "sam")
    gh.put(f"/teams/{code}/github/repo", {"full_name": "acme/app"})
    connect(gh, "sam", "good-ann")
    r = connect(gh, "kim", "good-ann")
    assert "github=error" in r.headers["location"] and "reason=github_account_taken" in r.headers["location"]
    as_user(gh, "kim")
    assert gh.get("/me/github").json()["connected"] is False


def test_a_member_sees_only_their_own_github_row_but_the_leader_sees_all(gh):
    code = make_team(gh)
    install(gh)
    as_user(gh, "sam")
    gh.put(f"/teams/{code}/github/repo", {"full_name": "acme/app"})
    gh.sign_out()
    connect(gh, "sam", "good-ann")
    connect(gh, "kim", "good-bob")
    as_user(gh, "kim")
    view = gh.get(f"/teams/{code}/github").json()
    assert [m["name"] for m in view["members"]] == ["Kim"] and view["can_link"] is False and view["notes"] == []
    as_user(gh, "sam")
    assert len(gh.get(f"/teams/{code}/github").json()["members"]) == 3


def test_unlinking_removes_the_repository_and_what_github_said(gh):
    code = make_team(gh)
    install(gh)
    as_user(gh, "sam")
    gh.put(f"/teams/{code}/github/repo", {"full_name": "acme/app"})
    assert gh.delete(f"/teams/{code}/github").status_code == 204
    state = gh.get(f"/teams/{code}/github").json()
    assert state["repo"] is None and not state["ready"]
    assert gh.get(f"/teams/{code}").json()["repo_url"] is None
    assert gh.post("/me/github/connect", params={"team": code}).json()["code"] == "leader_must_link_first"  # nothing to join any more
    install(gh)
    as_user(gh, "sam")
    gh.put(f"/teams/{code}/github/repo", {"full_name": "acme/app"})
    connect(gh, "sam", "good-ann")
    as_user(gh, "sam")
    assert gh.delete("/me/github").status_code == 204 and gh.get("/me/github").json()["connected"] is False


def test_nothing_works_until_the_app_is_set_up(api):
    from shared.github_app import GitHubAppConfig

    fastapi_app.dependency_overrides[get_github_app] = lambda: GitHubApp(GitHubAppConfig())
    code = make_team(api)
    as_user(api, "sam")
    assert api.get("/github/config").json() == {"configured": False, "app_slug": None}
    r = api.post(f"/teams/{code}/github/install")
    assert r.status_code == 400 and r.json()["code"] == "github_not_configured"
    assert api.post("/me/github/connect", params={"team": code}).json()["code"] in ("github_not_configured", "leader_must_link_first")


# ---- the gate in front of the team --------------------------------------------------------------------------------------------------

def gate(api, sub, code="TEAM-ALPHA"):
    as_user(api, sub)
    return api.get(f"/teams/{code}/gate").json()


def test_a_student_is_stopped_until_the_leader_has_linked_the_repository(gh):
    make_team(gh)
    g = gate(gh, "kim")
    assert g["state"] == "repo_not_linked" and g["can_link"] is False and g["staff"] is False
    g = gate(gh, "sam")  # the leader can link it
    assert g["state"] == "repo_not_linked" and g["is_leader"] is True and g["can_link"] is True


def test_the_gate_asks_for_the_github_account_then_checks_its_access_live(gh):
    code = make_team(gh)
    install(gh)
    as_user(gh, "sam")
    gh.put(f"/teams/{code}/github/repo", {"full_name": "acme/app"})
    assert gate(gh, "kim")["state"] == "account_not_linked"
    gh.sign_out()
    connect(gh, "kim", "good-bob")  # "bob" can only read
    g = gate(gh, "kim")
    assert g["state"] == "read_only" and g["login"] == "bob" and g["permission"] == "read"
    gh.sign_out()
    connect(gh, "lee", "good-lee")  # "stranger" is not a collaborator
    assert gate(gh, "lee")["state"] == "no_access"
    gh.sign_out()
    connect(gh, "sam", "good-ann")  # "ann-dev" can write
    g = gate(gh, "sam")
    assert g["state"] == "ok" and g["permission"] == "write" and g["repo"] == "acme/app"


def test_the_gate_is_checked_again_every_time_so_lost_access_closes_it(gh):
    code = make_team(gh)
    install(gh)
    as_user(gh, "sam")
    gh.put(f"/teams/{code}/github/repo", {"full_name": "acme/app"})
    gh.sign_out()
    connect(gh, "sam", "good-ann")
    assert gate(gh, "sam")["state"] == "ok"
    original = gh.github.permission
    gh.github.permission = lambda *a, **k: "none"  # the collaborator was removed on GitHub
    assert gate(gh, "sam")["state"] == "no_access"
    gh.github.permission = original
    assert gate(gh, "sam")["state"] == "ok"

    def down(*a, **k):
        from shared.github_app import GitHubAppError

        raise GitHubAppError("GitHub is down")

    gh.github.permission = down
    assert gate(gh, "sam")["state"] == "github_unavailable"  # not let in when GitHub cannot be asked


def test_lecturers_and_administrators_pass_without_a_github_account(gh):
    make_team(gh)
    assert gate(gh, "ada")["state"] == "ok" and gate(gh, "ada")["staff"] is True
    gh.sign_in("root", admin=True, email="root@example.com")
    assert gh.get("/teams/TEAM-ALPHA/gate").json()["state"] == "ok"


def test_the_gate_does_not_open_for_someone_outside_the_team(gh):
    make_team(gh)
    student(gh, "eve")
    assert gh.get("/teams/TEAM-ALPHA/gate").status_code == 404


def test_a_rejected_person_can_ask_github_to_choose_another_account(gh):
    code = make_team(gh)
    install(gh)
    as_user(gh, "sam")
    gh.put(f"/teams/{code}/github/repo", {"full_name": "acme/app"})
    as_user(gh, "kim")
    plain = gh.post("/me/github/connect", params={"team": code}).json()["url"]
    other = gh.post("/me/github/connect", params={"team": code, "choose_account": "true"}).json()["url"]
    assert "select_account" not in plain and "prompt=select_account" in other


def test_when_the_app_is_not_set_up_nobody_is_locked_out(api):
    from shared.github_app import GitHubAppConfig

    fastapi_app.dependency_overrides[get_github_app] = lambda: GitHubApp(GitHubAppConfig())
    make_team(api)
    g = gate(api, "kim")
    assert g["state"] == "ok" and g["verified"] is False and g["configured"] is False


def test_the_gate_names_the_leader_so_a_waiting_member_knows_who_to_ask(gh):
    make_team(gh)
    assert gate(gh, "kim")["leader_name"] == "Sam"


def test_an_installation_that_github_sends_to_the_sign_in_address_is_accepted(gh):
    """With "request user authorization during installation" on, GitHub sends the install to the callback address with a code."""
    code = make_team(gh)
    as_user(gh, "sam")
    url = gh.post(f"/teams/{code}/github/install").json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    gh.sign_out()
    r = gh.get("/github/callback", params={"code": "unused", "installation_id": 7, "setup_action": "update", "state": state}, follow_redirects=False)
    assert r.status_code in (302, 307) and "/teams/TEAM-ALPHA/access?github=installed" in r.headers["location"]
    as_user(gh, "sam")
    assert [x["full_name"] for x in gh.get(f"/teams/{code}/github/repos").json()] == ["acme/app", "acme/docs"]


def test_an_install_returns_to_the_access_page_and_remembers_where_the_person_came_from(gh):
    make_team(gh)
    as_user(gh, "sam")
    url = gh.post("/teams/TEAM-ALPHA/github/install", params={"back": "/teams/TEAM-ALPHA/members"}).json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    gh.sign_out()
    r = gh.get("/github/installed", params={"installation_id": 7, "state": state}, follow_redirects=False)
    assert r.headers["location"].endswith("/teams/TEAM-ALPHA/access?github=installed&next=/teams/TEAM-ALPHA/members")
    as_user(gh, "sam")
    assert gh.post("/teams/TEAM-ALPHA/github/install", params={"back": "https://evil.example"}).status_code == 422


def test_a_popup_install_reports_back_to_the_window_that_opened_it(gh):
    make_team(gh)
    as_user(gh, "sam")
    url = gh.post("/teams/TEAM-ALPHA/github/install", params={"popup": True}).json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    gh.sign_out()
    r = gh.get("/github/installed", params={"installation_id": 7, "state": state}, follow_redirects=False)
    assert r.headers["location"].endswith("/github/popup-done?github=installed")
    bad = gh.get("/github/installed", params={"installation_id": 7, "state": state + "x"}, follow_redirects=False)
    assert "/?github=error" in bad.headers["location"]  # a state that cannot be read does not say it was a popup
