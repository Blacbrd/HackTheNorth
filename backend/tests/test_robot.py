import time

from fastapi.testclient import TestClient

from app.dependencies import get_robot_job_service
from app.main import app
from app.schemas.recommendations import GeminiRecommendation

client = TestClient(app)


def _fresh():
    jobs = get_robot_job_service()
    jobs.clear()
    return jobs


def test_job_is_idle_before_anything_is_asked():
    _fresh()
    body = client.get("/api/robot/job").json()
    assert body["active"] is False
    assert body["stage_index"] == -1


def test_job_reports_the_stage_it_has_reached():
    jobs = _fresh()
    jobs.start(GeminiRecommendation(shelf_number=3, item="lentils"), "vegetarian")

    body = client.get("/api/robot/job").json()
    assert body["stage"] == "queued"
    assert body["active"] is True
    assert body["item"] == "lentils"
    # Says out loud that the timing is not robot telemetry.
    assert body["simulated"] is True

    time.sleep(2.2)
    assert client.get("/api/robot/job").json()["stage"] == "driving"


def test_failure_reports_the_stage_it_broke_at_not_the_last_one():
    jobs = _fresh()
    jobs.start(GeminiRecommendation(shelf_number=3, item="lentils"), "vegetarian")

    body = client.post("/api/robot/job/fail/missing").json()
    assert body["failure"] == "missing"
    assert body["stage"] == "picking"
    assert body["active"] is False


def test_unknown_failure_is_rejected():
    _fresh()
    assert client.post("/api/robot/job/fail/exploded").status_code == 400


def test_recall_clears_the_job():
    jobs = _fresh()
    jobs.start(GeminiRecommendation(shelf_number=1, item="peas"), "anything")
    assert client.post("/api/robot/job/recall").json()["active"] is False
    assert client.get("/api/robot/job").json()["stage_index"] == -1


def test_history_records_the_request_and_its_outcome():
    jobs = _fresh()
    jobs.start(GeminiRecommendation(shelf_number=2, item="rice"), "a staple")

    entries = client.get("/api/robot/history").json()["entries"]
    assert entries[0]["item"] == "rice"
    assert entries[0]["succeeded"] is True
    assert entries[0]["user_input"] == "a staple"

    client.post("/api/robot/job/fail/blocked")
    entries = client.get("/api/robot/history").json()["entries"]
    assert entries[0]["succeeded"] is False
    assert entries[0]["failure"] == "blocked"


def test_quantity_adds_that_many_copies_in_one_request():
    before = client.get("/api/shelves/1").json()["items"]
    after = client.post(
        "/api/shelves/1/items", json={"item": "banana", "quantity": 3}
    ).json()
    try:
        assert len(after["items"]) == len(before) + 3
    finally:
        for _ in range(3):
            client.delete("/api/shelves/1/items/banana")
    assert client.get("/api/shelves/1").json()["items"] == before


def test_quantity_must_be_at_least_one():
    response = client.post("/api/shelves/1/items", json={"item": "x", "quantity": 0})
    assert response.status_code == 422
