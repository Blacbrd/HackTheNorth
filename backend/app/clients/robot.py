from __future__ import annotations

import os
import shlex
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.config import Settings
from app.schemas.recommendations import GeminiRecommendation

if TYPE_CHECKING:
    from app.services.robot_jobs import RobotJobService


class RobotCommandError(Exception):
    pass


# The explicit "HAMPY_STAGE:"/"HAMPY_FAIL:" markers are the preferred way for
# the robot script to report progress -- they are checked first below. These
# prose tables are only a fallback for a robot process that predates those
# markers, matched against the lines drop_both.py is already known to print.
# The same line means different things depending on whether one or two items
# are in flight, hence two tables.
_SINGLE_PROSE_STAGES: tuple[tuple[str, str], ...] = (
    ("PICKUP COMPLETE", "driving"),
    ("At table_2: extending", "driving"),
    ("Dropping: opening both grip", "arrived"),
)
_TWO_ITEM_PROSE_STAGES: tuple[tuple[str, str], ...] = (
    ("PICKUP COMPLETE", "dropping_first"),
    ("At table_2: extending", "dropping_second"),
    ("Dropping: opening both grip", "dropping_second"),
)
_PROSE_COMPLETE = "TRANSFER COMPLETE"
_PROSE_FAILURE = "NAVIGATION FAILED"


def _parse_stage_line(line: str, two_item: bool) -> tuple[str | None, str | None, bool]:
    """Maps one line of robot stdout to (stage, failure, complete).

    At most one of the three is ever non-empty/true for a given line. Unknown
    lines return all-empty, which the caller just ignores.
    """
    if "HAMPY_STAGE:" in line:
        token = line.split("HAMPY_STAGE:", 1)[1].strip().lower()
        return (token or None), None, False
    if "HAMPY_FAIL:" in line:
        token = line.split("HAMPY_FAIL:", 1)[1].strip().lower()
        return None, (token or None), False
    if _PROSE_COMPLETE in line:
        return None, None, True
    if _PROSE_FAILURE in line:
        return None, "blocked", False
    for needle, stage in (_TWO_ITEM_PROSE_STAGES if two_item else _SINGLE_PROSE_STAGES):
        if needle in line:
            return stage, None, False
    return None, None, False


class RobotClient:
    """Launch the robot-side Hampy transfer script for the picked item(s)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings and self.settings.robot_enabled)

    def send_pick_command(
        self,
        recommendations: list[GeminiRecommendation],
        jobs: "RobotJobService | None" = None,
    ) -> None:
        if not self.enabled or self.settings is None:
            # No jobs calls here -- the caller (RecommendationService) is the
            # one that knows this run is simulated and records it as such.
            for recommendation in recommendations:
                print(
                    f"Dummy robot command: move to shelf {recommendation.shelf_number}, "
                    f"pick {recommendation.item}",
                    flush=True,
                )
            return

        two_item = len(recommendations) > 1
        command = self._transport_command()
        log_path = Path("robot-run.log").resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log = log_path.open("a", buffering=1, encoding="utf-8", errors="replace")
        items_desc = ", ".join(f"shelf={r.shelf_number} item={r.item}" for r in recommendations)
        log.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] starting robot job: {items_desc}\n")
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                start_new_session=True,
            )
        except OSError as error:
            log.close()
            raise RobotCommandError(f"Could not start robot command: {error}") from error

        threading.Thread(
            target=self._read_and_log,
            args=(process, log, self.settings.robot_command_timeout_seconds, jobs, two_item),
            daemon=True,
        ).start()

    def _transport_command(self) -> list[str]:
        assert self.settings is not None
        script = self._workflow_script()
        transport = self.settings.robot_transport.strip().lower()
        if transport == "local":
            return ["bash", "-lc", script]
        if transport == "ssh":
            destination = f"{self.settings.robot_user}@{self.settings.robot_host}"
            return [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=5",
                destination,
                script,
            ]
        raise RobotCommandError("ROBOT_TRANSPORT must be 'local' or 'ssh'")

    def _workflow_script(self) -> str:
        assert self.settings is not None
        return " && ".join(
            [
                # A non-interactive `ssh host "cmd"` skips the login shell, so
                # the robot's PATH lacks ~/.local/bin and `uv run` would die
                # with "uv: command not found". Put it back before anything
                # runs.
                'export PATH="$HOME/.local/bin:$PATH"',
                f"cd {shlex.quote(self.settings.robot_app_dir)}",
                self.settings.robot_command,
            ]
        )

    @staticmethod
    def _read_and_log(
        process: subprocess.Popen,
        log,
        timeout_seconds: int,
        jobs: "RobotJobService | None",
        two_item: bool,
    ) -> None:
        # `for line in process.stdout` blocks on readline(), so a monotonic
        # deadline checked inside that loop would never fire while the robot
        # process is simply quiet. A watchdog timer that kills the process
        # group closes the pipe instead, which unblocks the loop on its own.
        completed = False
        failed = False
        timed_out = threading.Event()

        def _kill_on_timeout() -> None:
            timed_out.set()
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

        timer = threading.Timer(max(timeout_seconds, 1), _kill_on_timeout)
        timer.daemon = True
        timer.start()
        try:
            assert process.stdout is not None
            for line in process.stdout:
                log.write(line)
                stage, failure, complete = _parse_stage_line(line, two_item)
                if jobs is not None:
                    if failure:
                        jobs.fail(failure)
                        failed = True
                    elif complete:
                        jobs.complete()
                        completed = True
                    elif stage:
                        jobs.advance(stage)

            code = process.wait(timeout=5)
            if timed_out.is_set():
                log.write(f"robot job timed out after {timeout_seconds}s\n")
            log.write(f"robot job exited with code {code}\n")

            if code != 0 and jobs is not None and not failed and not completed:
                jobs.fail("fault")
        finally:
            timer.cancel()
            log.close()
