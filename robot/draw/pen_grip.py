# /// script
# requires-python = ">=3.10,<3.11"
# dependencies = ["bbos", "numpy<2"]
# [tool.uv.sources]
# bbos = { path = "/home/bracketbot/bbos", editable = true }
# ///
"""Clamp one gripper onto a pen and keep it clamped.

Torque is enabled on the gripper joint alone, so every other joint stays limp.
Park the arm or rest it on the table before running this, or it will sag.

Nothing moves without --execute. The grip survives this process exiting; run
--release to open the jaw again.
"""

from __future__ import annotations

import argparse
import contextlib
import signal
import time

import numpy as np
from bbos import Config, Reader, Type, Writer

# Gripper targets in URDF space, taken from quest_teleop/main.py. urdf2q()
# applies gripper_sign on the way to motor turns, so these stay unsigned.
OPEN_POS = 0.8
CLOSED_POS = -0.15      # past the closed stop; the pen is what stops the jaw

# Nm at the gripper joint. quest_teleop commands 0.70 at a full trigger and
# warns to keep a held grasp under ~2.0. A pen barrel is thin and round, so the
# default sits a little above a full trigger with headroom to spare.
CLOSE_TAU = 0.9
MAX_TAU = 1.5
OPEN_TAU = -0.45        # only used to break a grasp open, never to hold

STATE_TIMEOUT_S = 3.0
WRITER_TIMEOUT_S = 20.0
TICK_S = 0.01
REPORT_S = 0.5
SQUEEZE_S = 1.2         # ease into the clamp instead of snapping the jaw shut
RELEASE_S = 1.5
TEMP_LIMIT_C = 65.0     # well under the daemon's own limit; we just bail out


@contextlib.contextmanager
def writer_wait(topic: str, type_: Type, timeout: float = WRITER_TIMEOUT_S):
    """Open a Writer, waiting out whoever holds it (quest_teleop, usually)."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            writer = Writer(topic, type_)
            break
        except RuntimeError:
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    f"{topic} is busy. Stop quest_teleop before gripping.")
            time.sleep(0.1)
    with writer:
        yield writer


def wait_for_state(reader: Reader, timeout: float = STATE_TIMEOUT_S) -> np.ndarray:
    """Return the arm's current joint positions in motor turns."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if reader.ready():
            return np.asarray(reader.data["pos"], dtype=np.float64).copy()
        time.sleep(0.01)
    raise RuntimeError("No arm state. Is the arm daemon running?")


def smoothstep(value: float) -> float:
    value = min(max(value, 0.0), 1.0)
    return value * value * (3.0 - 2.0 * value)


class Gripper:
    """One arm's gripper joint, driven while the rest of the arm hangs limp."""

    def __init__(self, arm: str):
        self.arm = arm
        self.cfg = Config(f"arm_{arm}")
        self.index = self.cfg.dof - 1

    def urdf_pose(self, reader: Reader) -> np.ndarray:
        return self.cfg.q2urdf(wait_for_state(reader))

    def enable(self, w_torque: Writer, tau_mode: bool) -> None:
        """Torque on for the gripper joint only; everything else stays off."""
        enable = np.zeros(self.cfg.dof, dtype=np.bool_)
        enable[self.index] = True
        modes = np.zeros(self.cfg.dof, dtype=np.bool_)
        modes[self.index] = tau_mode
        with w_torque.buf() as buf:
            buf["enable"] = enable
            buf["tau_mode"] = modes
            buf["compliance_mode"] = False

    def disable(self, w_torque: Writer) -> None:
        w_torque._keeptime = False
        with w_torque.buf() as buf:
            buf["enable"] = np.zeros(self.cfg.dof, dtype=np.bool_)
            buf["tau_mode"] = np.zeros(self.cfg.dof, dtype=np.bool_)

    def command(self, w_ctrl: Writer, pose: np.ndarray,
                grip_pos: float, grip_tau: float) -> None:
        """Write one control frame. `pose` is the live pose of the limp joints.

        Commanding the measured pose every tick keeps the disabled joints'
        setpoints tracking reality, so nothing jumps if torque is enabled later.
        """
        if not w_ctrl.ready():
            return
        pos = np.asarray(pose, dtype=np.float64).copy()
        pos[self.index] = grip_pos
        tau = np.zeros(self.cfg.dof, dtype=np.float32)
        tau[self.index] = self.cfg.gripper_sign * grip_tau
        w_ctrl["pos"] = self.cfg.urdf2q(pos)
        w_ctrl["tau"] = tau
        w_ctrl["alpha"] = 0.0


def run(args: argparse.Namespace) -> int:
    gripper = Gripper(args.arm)
    index = gripper.index
    tau_mode = args.mode == "tau"
    closing = not args.release

    stop = False

    def request_stop(*_args):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    with writer_wait(f"arm_{args.arm}.torque", Type("arm_torque")) as w_torque, \
         writer_wait(f"arm_{args.arm}.ctrl", Type("arm_ctrl")) as w_ctrl, \
         Reader(f"arm_{args.arm}.state") as r_state:

        pose = gripper.urdf_pose(r_state)
        start_grip = float(pose[index])
        print(f"gripper starts at {start_grip:+.3f} (open={OPEN_POS}, "
              f"closed={args.closed})", flush=True)

        # Command the pose the arm is already in, then enable torque, so the
        # first tick cannot jerk the jaw. quest_teleop enables the same way.
        gripper.command(w_ctrl, pose, start_grip, 0.0)
        gripper.enable(w_torque, tau_mode and closing)
        print(f"torque on: gripper joint only, {args.mode} mode. "
              f"Every other joint is limp.", flush=True)

        ramp_s = RELEASE_S if args.release else SQUEEZE_S
        target_pos = OPEN_POS if args.release else args.closed
        started = time.monotonic()
        reported = 0.0
        held_since = None
        temp = current = 0.0
        code = 0

        while not stop:
            now = time.monotonic()
            elapsed = now - started
            frac = smoothstep(elapsed / ramp_s)

            if r_state.ready():
                pose = gripper.cfg.q2urdf(
                    np.asarray(r_state.data["pos"], dtype=np.float64))
                temp = float(r_state.data["temp"][index])
                current = float(r_state.data["current"][index])
                if temp >= TEMP_LIMIT_C:
                    print(f"[!] gripper at {temp:.0f}C; releasing", flush=True)
                    code = 1
                    break

            if args.release or not tau_mode:
                grip_pos = start_grip + frac * (target_pos - start_grip)
                grip_tau = 0.0
            else:
                # Torque mode: the daemon ignores pos for this joint, so the
                # position is written only so the logged action matches.
                grip_pos = OPEN_POS + frac * (args.closed - OPEN_POS)
                grip_tau = frac * args.tau

            gripper.command(w_ctrl, pose, grip_pos, grip_tau)

            if now - reported >= REPORT_S:
                reported = now
                print(f"[grip] cmd={grip_pos:+.3f} tau={grip_tau:+.2f}Nm "
                      f"act={float(pose[index]):+.3f} "
                      f"cur={current:+.2f}A temp={temp:.0f}C", flush=True)

            if frac >= 1.0:
                if held_since is None:
                    held_since = now
                    print("clamped" if closing else "open", flush=True)
                if args.seconds and now - held_since >= args.seconds:
                    break
                if args.release:
                    break
            time.sleep(TICK_S)

        if args.release or code:
            gripper.disable(w_torque)
            print("gripper torque off", flush=True)
        else:
            print("Grip is still held after exit. "
                  f"Run: uv run pen_grip.py --arm {args.arm} --release --execute",
                  flush=True)
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("left", "right"), default="right")
    parser.add_argument("--mode", choices=("tau", "pos"), default="tau",
                        help="tau clamps with a set force, pos drives to a set "
                             "opening (default: tau)")
    parser.add_argument("--tau", type=float, default=CLOSE_TAU,
                        help=f"clamp torque in Nm, max {MAX_TAU}")
    parser.add_argument("--closed", type=float, default=CLOSED_POS,
                        help="closed target in URDF space for --mode pos")
    parser.add_argument("--seconds", type=float, default=0.0,
                        help="hold time; 0 holds until Ctrl+C")
    parser.add_argument("--release", action="store_true",
                        help="open the jaw and turn the gripper torque off")
    parser.add_argument("--execute", action="store_true",
                        help="actually drive the gripper")
    args = parser.parse_args()

    if not 0.0 <= args.tau <= MAX_TAU:
        parser.error(f"--tau must be between 0 and {MAX_TAU}")
    if args.tau > 1.2:
        print(f"[!] {args.tau} Nm is a hard squeeze; watch the gripper current.",
              flush=True)

    if not args.execute:
        action = "open the jaw" if args.release else (
            f"clamp at {args.tau} Nm" if args.mode == "tau"
            else f"close to {args.closed}")
        print(f"DRY RUN: would {action} on the {args.arm} gripper. "
              f"Add --execute to move it.")
        return 0

    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
