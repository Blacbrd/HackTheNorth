from fastapi.testclient import TestClient

from app.clients.robot import RobotClient, RobotCommandError, _parse_stage_line
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
    jobs.start([GeminiRecommendation(shelf_number=3, item="lentils")], "vegetarian")

    body = client.get("/api/robot/job").json()
    assert body["stage"] == "picking"
    assert body["stages"] == ["picking", "driving", "arrived"]
    assert body["active"] is True
    assert body["item"] == "lentils"
    jobs.advance("driving")
    assert client.get("/api/robot/job").json()["stage"] == "driving"


def test_advance_ignores_unknown_stages_and_never_moves_backwards():
    jobs = _fresh()
    jobs.start([GeminiRecommendation(shelf_number=3, item="lentils")], "vegetarian")

    jobs.advance("not-a-real-stage")
    assert jobs.current().stage_index == 0

    jobs.advance("driving")
    assert jobs.current().stage_index == 1

    jobs.advance("picking")  # an earlier stage -- must not move backwards
    assert jobs.current().stage_index == 1

    jobs.advance("arrived")
    assert jobs.current().stage_index == 2
    assert jobs.current().active is False


def test_complete_jumps_straight_to_the_last_stage():
    jobs = _fresh()
    jobs.start([GeminiRecommendation(shelf_number=1, item="peas")], "anything")
    jobs.complete()
    body = jobs.current()
    assert body.stage == "arrived"
    assert body.active is False


def test_two_item_job_uses_the_shared_route_stages():
    jobs = _fresh()
    jobs.start(
        [
            GeminiRecommendation(shelf_number=1, item="peas"),
            GeminiRecommendation(shelf_number=2, item="rice"),
        ],
        "two things",
        two_item=True,
    )
    body = client.get("/api/robot/job").json()
    assert body["stages"] == ["picking", "driving", "arrived"]
    assert body["two_item"] is True
    assert body["items"] == [
        {"shelf_number": 1, "item": "peas"},
        {"shelf_number": 2, "item": "rice"},
    ]
    # Back-compat mirrors of the first item.
    assert body["shelf_number"] == 1
    assert body["item"] == "peas"


def test_failure_is_recorded_at_the_current_stage():
    jobs = _fresh()
    jobs.start([GeminiRecommendation(shelf_number=3, item="lentils")], "vegetarian")
    jobs.advance("driving")

    body = client.post("/api/robot/job/fail/missing").json()
    assert body["failure"] == "missing"
    assert body["stage"] == "driving"
    assert body["active"] is False


def test_unknown_failure_is_rejected():
    _fresh()
    assert client.post("/api/robot/job/fail/exploded").status_code == 400


def test_recall_clears_the_job():
    jobs = _fresh()
    jobs.start([GeminiRecommendation(shelf_number=1, item="peas")], "anything")
    assert client.post("/api/robot/job/recall").json()["active"] is False
    assert client.get("/api/robot/job").json()["stage_index"] == -1


def test_history_records_the_request_and_its_outcome():
    jobs = _fresh()
    jobs.start([GeminiRecommendation(shelf_number=2, item="rice")], "a staple")

    entries = client.get("/api/robot/history").json()["entries"]
    assert entries[0]["item"] == "rice"
    assert entries[0]["succeeded"] is True
    assert entries[0]["user_input"] == "a staple"

    client.post("/api/robot/job/fail/blocked")
    entries = client.get("/api/robot/history").json()["entries"]
    assert entries[0]["succeeded"] is False
    assert entries[0]["failure"] == "blocked"


def test_job_stage_endpoint_advances_and_rejects_unknown_stage():
    _fresh().start([GeminiRecommendation(shelf_number=1, item="peas")], "anything")

    advanced = client.post("/api/robot/job/stage/driving")
    assert advanced.json()["stage"] == "driving"

    rejected = client.post("/api/robot/job/stage/not-a-stage")
    assert rejected.status_code == 400


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


def test_disabled_robot_client_rejects_dispatch():
    robot = RobotClient()
    assert robot.enabled is False
    try:
        robot.send_pick_command([GeminiRecommendation(shelf_number=1, item="peas")])
    except RobotCommandError as error:
        assert "disabled" in str(error)
    else:
        raise AssertionError("expected RobotCommandError")


def test_robot_client_builds_local_delivery_command():
    settings = Settings(
        robot_enabled=True,
        robot_transport="local",
        robot_app_dir="/home/bracketbot/bbapps/hampy_demo",
        robot_command="uv run transfer_both.py --execute --yes",
    )
    command = RobotClient(settings)._transport_command()
    script = command[-1]
    assert command[:2] == ["bash", "-lc"]
    # uv lives in ~/.local/bin, which a non-interactive ssh does not put on PATH.
    assert script.startswith('export PATH="$HOME/.local/bin:$PATH"')
    assert "cd /home/bracketbot/bbapps/hampy_demo" in script
    assert "uv run transfer_both.py --execute --yes" in script


def test_robot_client_builds_ssh_delivery_command():
    settings = Settings(
        robot_enabled=True,
        robot_transport="ssh",
        robot_host="bracketbot-0186.local",
        robot_user="bracketbot",
        robot_command="uv run transfer_both.py --execute --yes",
    )
    command = RobotClient(settings)._transport_command()
    assert command[:5] == ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5"]
    assert command[5] == "bracketbot@bracketbot-0186.local"
    assert "uv run transfer_both.py --execute --yes" in command[6]


def test_robot_client_rejects_unknown_transport():
    settings = Settings(robot_enabled=True, robot_transport="carrier-pigeon")
    try:
        RobotClient(settings)._transport_command()
    except RobotCommandError as error:
        assert "ROBOT_TRANSPORT" in str(error)
    else:
        raise AssertionError("expected RobotCommandError")


def test_marker_line_is_preferred_over_prose():
    stage, failure, complete = _parse_stage_line("HAMPY_STAGE: Dropping_First", two_item=True)
    assert stage == "dropping_first"
    assert failure is None
    assert complete is False


def test_marker_failure_line():
    stage, failure, complete = _parse_stage_line("HAMPY_FAIL: blocked", two_item=False)
    assert stage is None
    assert failure == "blocked"
    assert complete is False


def test_prose_compatibility_uses_the_shared_route_stage():
    line = "PICKUP COMPLETE: navigating to table_2 while holding the item..."
    single_stage, _, _ = _parse_stage_line(line, two_item=False)
    two_item_stage, _, _ = _parse_stage_line(line, two_item=True)
    assert single_stage == "driving"
    assert two_item_stage == "driving"


def test_prose_completion_and_failure_lines():
    _, _, complete = _parse_stage_line("TRANSFER COMPLETE.", two_item=False)
    _, failure, _ = _parse_stage_line("NAVIGATION FAILED (exit code 2).", two_item=False)
    assert complete is True
    assert failure == "blocked"


def test_unrecognized_line_is_ignored():
    stage, failure, complete = _parse_stage_line("Writer drive.ctrl using 1 buffers", two_item=False)
    assert stage is None
    assert failure is None
    assert complete is False
