from __future__ import annotations

import re
import shlex
import os
import signal
import subprocess
import threading
import time
from pathlib import Path

from app.core.config import Settings
from app.schemas.recommendations import GeminiRecommendation


class RobotCommandError(Exception):
    pass


class RobotClient:
    """Launch the robot-side Hampy scripts for a selected shelf item."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings and self.settings.robot_enabled)

    def send_pick_command(self, recommendation: GeminiRecommendation) -> None:
        if not self.enabled or self.settings is None:
            print(
                f"Dummy robot command: move to shelf {recommendation.shelf_number}, "
                f"pick {recommendation.item}",
                flush=True,
            )
            return

        command = self._transport_command(recommendation)
        log_path = Path("robot-run.log").resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log = log_path.open("ab", buffering=0)
        log.write(
            f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] starting robot job: "
            f"shelf={recommendation.shelf_number} item={recommendation.item}\n".encode()
        )
        try:
            process = subprocess.Popen(
                command,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError as error:
            log.close()
            raise RobotCommandError(f"Could not start robot command: {error}") from error

        threading.Thread(
            target=self._wait_and_log,
            args=(process, log, self.settings.robot_command_timeout_seconds),
            daemon=True,
        ).start()

    def _transport_command(self, recommendation: GeminiRecommendation) -> list[str]:
        assert self.settings is not None
        script = self._workflow_script(recommendation)
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

    def _workflow_script(self, recommendation: GeminiRecommendation) -> str:
        assert self.settings is not None
        station = self._station_for_shelf(recommendation.shelf_number)
        item_slug = self._slug(recommendation.item)
        # Arm motions are optional. They have to be physically taught with
        # Quest teleop or keyboard_teach before they exist, so leaving the
        # template empty gives a drive-only run: navigate to the shelf, then to
        # the drop-off, with the head camera streaming throughout.
        pickup_template = self.settings.robot_pickup_motion_template.strip()
        pickup_motion = (
            pickup_template.format(
                shelf=recommendation.shelf_number,
                station=station,
                item=item_slug,
            )
            if pickup_template
            else ""
        )
        drop_motion = self.settings.robot_drop_motion.strip()

        parts = [
            # A non-interactive `ssh host "cmd"` skips the login shell, so the
            # robot's PATH lacks ~/.local/bin and every `uv run` below would die
            # with "uv: command not found". Put it back before anything runs.
            'export PATH="$HOME/.local/bin:$PATH"',
            f"cd {shlex.quote(self.settings.robot_app_dir)}",
        ]
        # Only guard the motions this run will actually replay, or an unused
        # template would abort the drive before it started.
        if pickup_motion:
            parts.append(f"test -f {shlex.quote(pickup_motion)}")
        if drop_motion:
            parts.append(f"test -f {shlex.quote(drop_motion)}")

        parts.append(self._nav_command(station))
        if pickup_motion:
            parts.append(self._replay_command(pickup_motion))
        parts.append(self._nav_command(self.settings.robot_dropoff_station))
        if drop_motion:
            parts.append(self._replay_command(drop_motion))
        return " && ".join(parts)

    def _nav_command(self, station: str) -> str:
        return (
            "uv run station_nav.py "
            f"{shlex.quote(station)} --direct --no-marker --execute --yes"
        )

    def _replay_command(self, motion: str) -> str:
        return f"uv run replay_trajectory.py {shlex.quote(motion)} --execute --yes"

    def _station_for_shelf(self, shelf_number: int) -> str:
        assert self.settings is not None
        mapping: dict[int, str] = {}
        for chunk in self.settings.robot_station_by_shelf.split(","):
            if not chunk.strip():
                continue
            try:
                shelf, station = chunk.split(":", 1)
                mapping[int(shelf.strip())] = station.strip()
            except ValueError as error:
                raise RobotCommandError(
                    "ROBOT_STATION_BY_SHELF must look like '1:table_1,2:table_2'"
                ) from error
        try:
            return mapping[shelf_number]
        except KeyError as error:
            raise RobotCommandError(
                f"No robot station configured for shelf {shelf_number}"
            ) from error

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
        return slug or "item"

    @staticmethod
    def _wait_and_log(process: subprocess.Popen, log, timeout_seconds: int) -> None:
        try:
            try:
                code = process.wait(timeout=max(timeout_seconds, 1))
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                code = process.wait(timeout=5)
                log.write(f"robot job timed out after {timeout_seconds}s\n".encode())
            log.write(f"robot job exited with code {code}\n".encode())
        finally:
            log.close()
