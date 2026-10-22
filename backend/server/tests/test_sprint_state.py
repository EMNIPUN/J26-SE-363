"""A sprint's state (finished, current, upcoming) is what the Scrum board says; the pages and the agent read the same status."""
from app.api.v1 import performance as performance_api
from app.modules.performance import service
from tests.test_performance_api import perf, track  # noqa: F401  (fixtures and helpers)
from tests.test_teams_api import lecturer


def test_the_scrum_boards_status_wins_and_the_dates_decide_only_without_one():
    assert service.sprint_state("2099-01-01", "2099-01-14", board_status="completed") == "finished"   # the board says it is done, whatever the dates say
    assert service.sprint_state("2020-01-01", "2020-01-14", board_status="active") == "current"
    assert service.sprint_state("2020-01-01", "2020-01-14", board_status="planned") == "upcoming"
    assert service.sprint_state("2020-01-01", "2020-01-14") == "finished"                              # no status: by the dates
    assert service.sprint_state("2020-01-01", "2020-01-14", board_status="something new") == "finished"  # an unknown word is not trusted


def test_the_development_page_is_told_how_far_the_sprint_is(perf):
    lecturer(perf, "ada")
    track(perf, sprints=[{"id": "T9-S1", "start": "2020-03-01", "end": "2020-03-14"}])
    progress = perf.get("/performance/teams/T9/development").json()["progress"]
    assert progress["state"] == "finished" and progress["day"] == progress["days"] == 14 and progress["share"] == 1.0

    track(perf, sprints=[{"id": "T9-S1", "start": "2099-03-01", "end": "2099-03-14"}])
    progress = perf.get("/performance/teams/T9/development").json()["progress"]
    assert progress["state"] == "upcoming" and progress["day"] == 0 and progress["share"] == 0.0


def test_a_sprint_the_scrum_board_has_completed_is_finished_on_the_pages_too(perf, monkeypatch):
    class Board:
        def match(self, repo_url):
            return True

        def payload(self, operation, repo_url, **params):
            assert operation == "list_sprints"
            return [{"sprint_id": "T9-S1", "start_date": "2099-03-01", "end_date": "2099-03-14", "status": "completed"}]

    monkeypatch.setattr(performance_api, "ScrumSimulator", Board)
    lecturer(perf, "ada")
    track(perf, sprints=[{"id": "T9-S1", "start": "2099-03-01", "end": "2099-03-14"}])           # dates alone would say "upcoming"
    sprint = perf.get("/performance/teams/T9/overview").json()["sprints"][0]
    assert sprint["state"] == "finished" and sprint["board_status"] == "completed"
    assert perf.get("/performance/teams/T9/development").json()["progress"]["state"] == "finished"
