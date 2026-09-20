# /// script
# requires-python = ">=3.10,<3.11"
# dependencies = ["bbos", "numpy<2"]
# [tool.uv.sources]
# bbos = { path = "/home/bracketbot/bbos", editable = true }
# ///
"""Coordinate the base's LEAN and BALANCE modes."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from bbos import Config, Type, Writer


ROOT = Path(__file__).resolve().parent
LEAN_HOLD_SCRIPT = ROOT / "lean_hold.py"
LEAN_HOLD_PID = ROOT / ".lean_hold.pid"
LEAN_HOLD_READY = ROOT / ".lean_hold.ready"
LEAN_HOLD_LOG = ROOT / "lean_hold.log"


def _lean_holder_pid() -> int | None:
    try:
        pid = int(LEAN_HOLD_PID.read_text().strip())
        command = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ")
        if b"lean_hold.py" in command:
            return pid
    except (OSError, ValueError):
        pass
    LEAN_HOLD_PID.unlink(missing_ok=True)
    LEAN_HOLD_READY.unlink(missing_ok=True)
    return None


def stop_lean_hold() -> None:
    pid = _lean_holder_pid()
    if pid is None:
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and Path(f"/proc/{pid}").exists():
        time.sleep(0.05)
    if Path(f"/proc/{pid}").exists():
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    LEAN_HOLD_PID.unlink(missing_ok=True)
    LEAN_HOLD_READY.unlink(missing_ok=True)
    print("LEAN mode holder stopped.", flush=True)


def hold_base_mode(mode: int, lean_angle_deg: float, duration_s: float) -> None:
    with Writer("base.mode", Type("base_mode"), keeptime=False) as writer:
        deadline = time.monotonic() + duration_s
        while time.monotonic() < deadline:
            with writer.buf() as command:
                command["mode"] = mode
                command["lean_angle_deg"] = lean_angle_deg
            time.sleep(0.05)


def deactivate_lean(lean_angle_deg: float) -> None:
    stop_lean_hold()
    cfg = Config("base")
    print("LEAN OFF: switching to BALANCE before moving.", flush=True)
    hold_base_mode(int(cfg.MODE_BALANCE), lean_angle_deg, 0.50)


def start_lean_hold(lean_angle_deg: float) -> None:
    stop_lean_hold()
    LEAN_HOLD_READY.unlink(missing_ok=True)
    log = LEAN_HOLD_LOG.open("ab", buffering=0)
    process = subprocess.Popen(
        [
            sys.executable,
            str(LEAN_HOLD_SCRIPT),
            "--angle",
            str(lean_angle_deg),
            "--pid-file",
            str(LEAN_HOLD_PID),
            "--ready-file",
            str(LEAN_HOLD_READY),
        ],
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log.close()
    deadline = time.monotonic() + 4.0
    while time.monotonic() < deadline:
        if LEAN_HOLD_READY.exists() and _lean_holder_pid() == process.pid:
            print(f"LEAN ON: holding {lean_angle_deg:+.1f}deg at the table.", flush=True)
            return
        if process.poll() is not None:
            break
        time.sleep(0.05)
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
    try:
        tail = "\n".join(LEAN_HOLD_LOG.read_text(errors="replace").splitlines()[-8:])
    except OSError:
        tail = ""
    raise RuntimeError(f"could not activate LEAN mode. Log:\n{tail}")
