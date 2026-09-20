# /// script
# requires-python = ">=3.10,<3.11"
# dependencies = ["bbos", "numpy<2"]
# [tool.uv.sources]
# bbos = { path = "/home/bracketbot/bbos", editable = true }
# ///
"""Validate and replay the table-1-to-table-2 base route."""

from __future__ import annotations

import argparse
import json
import signal
import time
from pathlib import Path

import numpy as np
from bbos import Type, Writer

from base_mode import deactivate_lean
from bbos import Config


MAX_DURATION_S = 180.0
MAX_LINEAR_MPS = 0.50
MAX_ANGULAR_RPS = 1.50


def load_route(path: Path) -> tuple[np.ndarray, np.ndarray]:
    payload = json.loads(path.read_text())
    if payload.get("kind") != "timed_base_twist_route" or payload.get("version") != 1:
        raise ValueError("file is not a supported recorded base route")
    samples = payload.get("samples") or []
    if len(samples) < 2:
        raise ValueError("route needs at least two samples")
    times = np.asarray([sample["t"] for sample in samples], dtype=np.float64)
    twists = np.asarray([sample["twist"] for sample in samples], dtype=np.float64)
    if twists.shape != (len(samples), 2) or not np.all(np.isfinite(twists)):
        raise ValueError("route contains invalid drive commands")
    if (
        not np.all(np.isfinite(times))
        or times[0] != 0.0
        or np.any(np.diff(times) <= 0.0)
        or times[-1] > MAX_DURATION_S
    ):
        raise ValueError("route timestamps are invalid")
    if np.max(np.abs(twists[:, 0])) > MAX_LINEAR_MPS:
        raise ValueError("route exceeds the linear-speed limit")
    if np.max(np.abs(twists[:, 1])) > MAX_ANGULAR_RPS:
        raise ValueError("route exceeds the angular-speed limit")
    return times, twists


def replay(path: Path, execute: bool, assume_yes: bool) -> int:
    times, twists = load_route(path)
    print(f"Validated recorded route: {times[-1]:.2f}s, {len(times)} commands.")
    if not execute:
        print("DRY RUN: nothing moved. Add --execute to replay.")
        return 0
    if not assume_yes:
        answer = input(
            "Place the robot at the table_1 recording pose, clear the complete route, "
            "keep a hand near emergency stop, then type REPLAY: "
        )
        if answer.strip() != "REPLAY":
            print("Cancelled; nothing moved.")
            return 1

    stopped = False

    def request_stop(*_args) -> None:
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    cfg = Config("base")
    deactivate_lean(float(cfg.lean_angle_deg))
    try:
        with Writer("drive.ctrl", Type("drive_ctrl"), keeptime=False) as drive:
            print("REPLAYING RECORDED BASE ROUTE — Ctrl-C stops immediately.", flush=True)
            started = time.monotonic()
            index = 0
            while not stopped:
                elapsed = time.monotonic() - started
                while index + 1 < len(times) and times[index + 1] <= elapsed:
                    index += 1
                command = twists[index] if elapsed < times[-1] else np.zeros(2)
                with drive.buf() as buffer:
                    buffer["twist"] = command.astype(np.float32)
                if elapsed >= times[-1]:
                    break
                time.sleep(0.01)
            with drive.buf() as buffer:
                buffer["twist"] = np.zeros(2, dtype=np.float32)
    except RuntimeError as exc:
        raise RuntimeError(
            "drive.ctrl is busy; stop Manual Drive, Quest teleop, navigation, "
            "and other base-control programs"
        ) from exc

    if stopped:
        print("RECORDED ROUTE STOPPED.", flush=True)
        return 130
    print("RECORDED ROUTE COMPLETE.", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("route", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    return replay(args.route, args.execute, args.yes)


if __name__ == "__main__":
    raise SystemExit(main())
