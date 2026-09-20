import time

from fastapi.testclient import TestClient

from app.clients.robot import RobotClient, RobotCommandError
from app.core.config import Settings
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


def test_disabled_robot_client_keeps_dummy_behavior():
    client = RobotClient()
    assert client.enabled is False
    client.send_pick_command(GeminiRecommendation(shelf_number=1, item="peas"))


def test_robot_client_builds_local_delivery_workflow():
    settings = Settings(
        robot_enabled=True,
        robot_transport="local",
        robot_app_dir="/home/bracketbot/bbapps/hampy_demo",
        robot_station_by_shelf="1:table_1,2:table_2",
        robot_dropoff_station="table_2",
        robot_pickup_motion_template="motions/{station}_{item}.json",
        robot_drop_motion="motions/drop.json",
    )
    command = RobotClient(settings)._transport_command(
        GeminiRecommendation(shelf_number=1, item="Can of Mushrooms")
    )
    script = command[-1]
    assert command[:2] == ["bash", "-lc"]
    assert "cd /home/bracketbot/bbapps/hampy_demo" in script
    assert "test -f motions/table_1_can_of_mushrooms.json" in script
    assert "uv run station_nav.py table_1 --direct --no-marker --execute --yes" in script
    assert "uv run station_nav.py table_2 --direct --no-marker --execute --yes" in script
    assert "uv run replay_trajectory.py motions/drop.json --execute --yes" in script


def test_robot_client_builds_ssh_delivery_workflow():
    settings = Settings(
        robot_enabled=True,
        robot_transport="ssh",
        robot_host="bracketbot-0186.local",
        robot_user="bracketbot",
        robot_station_by_shelf="2:table_2",
    )
    command = RobotClient(settings)._transport_command(
        GeminiRecommendation(shelf_number=2, item="rice")
    )
    assert command[:5] == ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5"]
    assert command[5] == "bracketbot@bracketbot-0186.local"
    assert "station_nav.py table_2" in command[6]


def test_robot_client_rejects_unmapped_shelf():
    settings = Settings(robot_enabled=True, robot_station_by_shelf="1:table_1")
    try:
        RobotClient(settings)._transport_command(
            GeminiRecommendation(shelf_number=9, item="peas")
        )
    except RobotCommandError as error:
        assert "No robot station configured for shelf 9" in str(error)
    else:
        raise AssertionError("expected RobotCommandError")


def test_robot_client_drives_without_arm_motions():
    """Arm motions must be taught physically, so an empty template gives a
    drive-only run rather than aborting on a `test -f` for a file nobody made."""
    settings = Settings(
        robot_enabled=True,
        robot_station_by_shelf="1:table_1",
        robot_dropoff_station="table_2",
        robot_pickup_motion_template="",
        robot_drop_motion="",
    )
    script = RobotClient(settings)._workflow_script(
        GeminiRecommendation(shelf_number=1, item="peas")
    )
    assert "test -f" not in script
    assert "replay_trajectory.py" not in script
    assert "station_nav.py table_1" in script
    assert "station_nav.py table_2" in script
    # uv lives in ~/.local/bin, which a non-interactive ssh does not put on PATH.
    assert script.startswith('export PATH="$HOME/.local/bin:$PATH"')
