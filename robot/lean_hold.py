# /// script
# requires-python = ">=3.10,<3.11"
# dependencies = ["bbos", "numpy<2"]
# [tool.uv.sources]
# bbos = { path = "/home/bracketbot/bbos", editable = true }
# ///
"""Hold the robot base in LEAN mode until terminated."""

from __future__ import annotations

import argparse
import os
import signal
import time
from pathlib import Path

from bbos import Config, Type, Writer
from bbos.daemons.base import constants as _base_constants  # noqa: F401


ROOT = Path(__file__).resolve().parent


def main() -> int:
    cfg = Config("base")
    parser = argparse.ArgumentParser()
    parser.add_argument("--angle", type=float, default=float(cfg.lean_angle_deg))
    parser.add_argument("--pid-file", type=Path, default=ROOT / ".lean_hold.pid")
    parser.add_argument("--ready-file", type=Path, default=ROOT / ".lean_hold.ready")
    args = parser.parse_args()
    if not float(cfg.lean_angle_min_deg) <= abs(args.angle) <= float(cfg.lean_angle_max_deg):
        raise SystemExit(
            f"lean angle must be between {cfg.lean_angle_min_deg} and "
            f"{cfg.lean_angle_max_deg} degrees"
        )

    stopping = False

    def request_stop(*_args) -> None:
        nonlocal stopping
        stopping = True

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, request_stop)

    args.ready_file.unlink(missing_ok=True)
    try:
        with Writer("base.mode", Type("base_mode"), keeptime=False) as writer:
            args.pid_file.write_text(f"{os.getpid()}\n")
            args.ready_file.write_text(f"{os.getpid()}\n")
            print(f"LEAN HOLD active at {args.angle:+.1f}deg", flush=True)
            while not stopping:
                with writer.buf() as command:
                    command["mode"] = int(cfg.MODE_LEAN)
                    command["lean_angle_deg"] = args.angle
                time.sleep(0.05)
    finally:
        args.ready_file.unlink(missing_ok=True)
        try:
            if args.pid_file.read_text().strip() == str(os.getpid()):
                args.pid_file.unlink(missing_ok=True)
        except OSError:
            pass
    print("LEAN HOLD stopped; base will return to BALANCE.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
