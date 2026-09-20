#!/usr/bin/env python3
"""Forward decoded ring buttons to a persistent BracketBot control process."""

from __future__ import annotations

import atexit
import subprocess
import sys
import threading
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))
import ring_keyboard_mapper as mapper  # noqa: E402


ROBOT_HOST = "bracketbot@bracketbot-0186.local"
REMOTE_COMMAND = (
    'export PATH="$HOME/.local/bin:$PATH"; '
    "cd ~/bbapps/hampy_demo && uv run ring_robot_bridge.py"
)


class RobotLink:
    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None
        self.lock = threading.Lock()

    def start(self) -> None:
        self.close()
        self.process = subprocess.Popen(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=5",
                ROBOT_HOST,
                REMOTE_COMMAND,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        while True:
            line = self.process.stdout.readline() if self.process.stdout else ""
            if not line:
                raise RuntimeError("robot bridge exited before becoming ready")
            print(f"[robot] {line.rstrip()}")
            if line.strip() == "RING_BRIDGE_READY":
                return

    def send(self, button: str) -> None:
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                self.start()
            assert self.process is not None and self.process.stdin is not None
            assert self.process.stdout is not None
            self.process.stdin.write(button + "\n")
            self.process.stdin.flush()
            while True:
                line = self.process.stdout.readline()
                if not line:
                    raise RuntimeError("robot bridge disconnected")
                message = line.rstrip()
                print(f"[robot] {message}")
                if message == f"DONE {button}":
                    return
                if message.startswith(f"ERROR {button} "):
                    raise RuntimeError(message)

    def close(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            try:
                if self.process.stdin:
                    self.process.stdin.write("stop\n")
                    self.process.stdin.flush()
                self.process.wait(timeout=2)
            except (BrokenPipeError, subprocess.TimeoutExpired):
                self.process.terminate()
        self.process = None


link = RobotLink()
atexit.register(link.close)


def emit_robot_action(_mapping: dict[str, dict[str, object]], button: str) -> None:
    try:
        link.send(button)
    except Exception as exc:
        print(f"[ring-robot] {button} failed: {exc}", file=sys.stderr)


mapper._emit_action = emit_robot_action


if __name__ == "__main__":
    print("[ring-robot] arrows drive; center runs six-seven; home says thank you for listening")
    mapper.main()
