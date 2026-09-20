# /// script
# requires-python = ">=3.10,<3.11"
# dependencies = ["bbos", "numpy<2"]
# [tool.uv.sources]
# bbos = { path = "/home/bracketbot/bbos", editable = true }
# ///
"""Receive ring actions over stdin and control BracketBot."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from bbos import Type, Writer


ROOT = Path(__file__).resolve().parent
ACTIONS = {
    "top": ("backward", np.array([-0.10, 0.0], dtype=np.float32), 0.30),
    "bottom": ("forward", np.array([0.12, 0.0], dtype=np.float32), 0.30),
    "left": ("turn right", np.array([0.0, -0.40], dtype=np.float32), 0.30),
    "right": ("turn left", np.array([0.0, 0.40], dtype=np.float32), 0.30),
}


def drive_step(drive: Writer, twist: np.ndarray, duration: float) -> None:
    deadline = time.monotonic() + duration
    try:
        while time.monotonic() < deadline:
            with drive.buf() as command:
                command["twist"] = twist
            time.sleep(0.01)
    finally:
        with drive.buf() as command:
            command["twist"] = np.zeros(2, dtype=np.float32)


def run_program(filename: str, *arguments: str) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / filename), *arguments],
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{filename} exited with status {result.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print("top=backward bottom=forward left=turn-right right=turn-left")
        print("center=six-seven home=thank-you")
        return 0

    try:
        drive_context = Writer("drive.ctrl", Type("drive_ctrl"), keeptime=False)
    except RuntimeError as exc:
        raise RuntimeError(
            "drive.ctrl is busy; stop dashboard Manual Drive, navigation, and other base controllers"
        ) from exc

    with drive_context as drive:
        print("RING_BRIDGE_READY", flush=True)
        for raw_line in sys.stdin:
            button = raw_line.strip().lower()
            if button == "stop":
                with drive.buf() as command:
                    command["twist"] = np.zeros(2, dtype=np.float32)
                break
            try:
                if button in ACTIONS:
                    label, twist, duration = ACTIONS[button]
                    print(f"RING {button}: {label}", flush=True)
                    drive_step(drive, twist, duration)
                elif button == "center":
                    print("RING center: six-seven", flush=True)
                    run_program("six_seven.py", "--execute", "--yes")
                elif button == "home":
                    print("RING home: thank-you", flush=True)
                    run_program(
                        "play_robot_audio.py",
                        str(ROOT / "thank_you.wav"),
                        "--volume",
                        "0.95",
                    )
                else:
                    raise RuntimeError("unknown ring button")
            except Exception as exc:
                with drive.buf() as command:
                    command["twist"] = np.zeros(2, dtype=np.float32)
                print(f"ERROR {button} {exc}", flush=True)
            else:
                print(f"DONE {button}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
