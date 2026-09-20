# /// script
# requires-python = ">=3.10,<3.11"
# dependencies = ["bbos", "numpy<2"]
# [tool.uv.sources]
# bbos = { path = "/home/bracketbot/bbos", editable = true }
# ///
"""Pick up two items, follow the recorded route, and release them."""

from __future__ import annotations

import argparse
import contextlib
import signal
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from bbos import Config, Reader, Type, Writer

QUEST_DIR = Path.home() / "bbapps" / "quest_teleop"
sys.path.insert(0, str(QUEST_DIR))
from scripts.homing import park_arms, staged_home_arms  # noqa: E402
from scripts.tracking import CFG_L, CFG_R, constrain_to_cylinders, home_ik  # noqa: E402

from base_mode import deactivate_lean, start_lean_hold


GRIPPER_OPEN = 0.8
GRIPPER_CLOSED = -0.15


def stage(name: str) -> None:
    print(f"HAMPY_STAGE: {name}", flush=True)


def failure(name: str) -> None:
    print(f"HAMPY_FAIL: {name}", flush=True)


@contextlib.contextmanager
def writer_wait(topic: str, type_: Type, timeout: float = 5.0):
    deadline = time.monotonic() + timeout
    while True:
        try:
            writer = Writer(topic, type_)
            break
        except RuntimeError:
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    f"{topic} is busy. Stop Quest teleop and other arm programs, then retry."
                )
            time.sleep(0.1)
    with writer:
        yield writer


def smoothstep(value: float) -> float:
    value = min(max(value, 0.0), 1.0)
    return value * value * (3.0 - 2.0 * value)


def solve_target(cfg, current: np.ndarray, delta: np.ndarray, side: str) -> np.ndarray:
    position, quaternion = cfg.ik.fk(list(current[:7]))
    target_position = constrain_to_cylinders(
        np.asarray(position, dtype=np.float64) + delta,
        side,
    )
    cfg.ik.reset(list(current[:7]))
    solution = cfg.ik.solve(target_position.tolist(), list(quaternion))
    if solution is None or len(solution) < 7:
        raise RuntimeError(f"{side} arm cannot reach the requested pose")
    target = current.copy()
    target[:7] = np.asarray(solution[:7], dtype=np.float64)
    if not np.all(np.isfinite(target)):
        raise RuntimeError(f"{side} arm IK returned invalid joint positions")
    actual_position, _ = cfg.ik.fk(list(target[:7]))
    error = float(np.linalg.norm(np.asarray(actual_position) - target_position))
    if error > 0.035:
        raise RuntimeError(f"{side} arm IK error is too large ({error:.3f}m)")
    if float(np.max(np.abs(target[:7] - current[:7]))) > 0.85:
        raise RuntimeError(f"{side} arm IK solution jumped too far")
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--route", type=Path, default=Path("routes/table1_to_table2.json"))
    parser.add_argument("--forward-m", type=float, default=0.18)
    parser.add_argument("--lower-m", type=float, default=0.10)
    parser.add_argument("--hold-seconds", type=float, default=1.0)
    args = parser.parse_args()

    if not args.route.is_file():
        raise SystemExit(f"recorded route does not exist: {args.route}")
    if not args.execute:
        print("Validated request. Add --execute to move the robot.")
        return 0
    if not args.yes:
        answer = input(
            "Clear both arm paths and the complete route, keep the emergency stop ready, "
            "then type TRANSFER: "
        )
        if answer.strip() != "TRANSFER":
            print("Cancelled.")
            return 1

    stopped = False
    route_process: subprocess.Popen | None = None

    def stop_now(_signum=None, _frame=None) -> None:
        nonlocal stopped
        stopped = True
        if route_process is not None and route_process.poll() is None:
            route_process.terminate()

    signal.signal(signal.SIGINT, stop_now)
    signal.signal(signal.SIGTERM, stop_now)

    lean_angle_deg = float(Config("base").lean_angle_deg)
    stage("picking")
    start_lean_hold(lean_angle_deg)

    with writer_wait("arm_left.torque", Type("arm_torque")) as torque_l, \
         writer_wait("arm_right.torque", Type("arm_torque")) as torque_r, \
         writer_wait("arm_left.ctrl", Type("arm_ctrl")) as ctrl_l, \
         writer_wait("arm_right.ctrl", Type("arm_ctrl")) as ctrl_r, \
         Reader("arm_left.state") as state_l, \
         Reader("arm_right.state") as state_r:

        arms = [
            dict(cfg=CFG_L, r_state=state_l, w_ctrl=ctrl_l, w_torque=torque_l,
                 tau_mode=np.zeros(CFG_L.dof, dtype=np.bool_)),
            dict(cfg=CFG_R, r_state=state_r, w_ctrl=ctrl_r, w_torque=torque_r,
                 tau_mode=np.zeros(CFG_R.dof, dtype=np.bool_)),
        ]
        deadline = time.monotonic() + 5.0
        while (state_l.data is None or state_r.data is None) and time.monotonic() < deadline:
            state_l.ready()
            state_r.ready()
            time.sleep(0.01)
        if state_l.data is None or state_r.data is None:
            raise RuntimeError("could not read the current arm positions")

        current_l = CFG_L.q2urdf(np.asarray(state_l.data["pos"], dtype=np.float64))
        current_r = CFG_R.q2urdf(np.asarray(state_r.data["pos"], dtype=np.float64))

        def write_pose(left: np.ndarray, right: np.ndarray) -> None:
            if ctrl_l.ready():
                with ctrl_l.buf() as buf:
                    buf["pos"][:] = CFG_L.urdf2q(left).astype(np.float32)
                    buf["tau"][:] = np.zeros(CFG_L.dof, dtype=np.float32)
                    buf["alpha"] = 0.0
            if ctrl_r.ready():
                with ctrl_r.buf() as buf:
                    buf["pos"][:] = CFG_R.urdf2q(right).astype(np.float32)
                    buf["tau"][:] = np.zeros(CFG_R.dof, dtype=np.float32)
                    buf["alpha"] = 0.0

        def move_to(
            target_l: np.ndarray,
            target_r: np.ndarray,
            seconds: float,
            label: str,
        ) -> None:
            nonlocal current_l, current_r
            start_l, start_r = current_l.copy(), current_r.copy()
            started = time.monotonic()
            print(label, flush=True)
            while not stopped:
                elapsed = time.monotonic() - started
                fraction = smoothstep(elapsed / seconds)
                write_pose(
                    start_l + fraction * (target_l - start_l),
                    start_r + fraction * (target_r - start_r),
                )
                if elapsed >= seconds:
                    break
                time.sleep(0.005)
            current_l, current_r = target_l.copy(), target_r.copy()

        try:
            CFG_L.ik.init()
            CFG_R.ik.init()
            print("Homing both arms safely...", flush=True)
            staged_home_arms(arms)
            current_l = CFG_L.q2urdf(np.asarray(CFG_L.home, dtype=np.float64))
            current_r = CFG_R.q2urdf(np.asarray(CFG_R.home, dtype=np.float64))
            home_ik()

            delta = np.array([args.forward_m, 0.0, -args.lower_m])
            pickup_l = solve_target(CFG_L, current_l, delta, "left")
            pickup_r = solve_target(CFG_R, current_r, delta, "right")
            move_to(pickup_l, pickup_r, 2.5, "Extending and lowering both arms...")

            opened_l, opened_r = current_l.copy(), current_r.copy()
            opened_l[CFG_L.dof - 1] = GRIPPER_OPEN
            opened_r[CFG_R.dof - 1] = GRIPPER_OPEN
            move_to(opened_l, opened_r, 0.8, "Opening both grippers...")

            closed_l, closed_r = current_l.copy(), current_r.copy()
            closed_l[CFG_L.dof - 1] = GRIPPER_CLOSED
            closed_r[CFG_R.dof - 1] = GRIPPER_CLOSED
            move_to(closed_l, closed_r, 0.8, "Closing both grippers...")
            hold_until = time.monotonic() + args.hold_seconds
            while not stopped and time.monotonic() < hold_until:
                write_pose(closed_l, closed_r)
                time.sleep(0.01)

            lift = np.array([0.0, 0.0, args.lower_m])
            lifted_l = solve_target(CFG_L, current_l, lift, "left")
            lifted_r = solve_target(CFG_R, current_r, lift, "right")
            lifted_l[CFG_L.dof - 1] = GRIPPER_CLOSED
            lifted_r[CFG_R.dof - 1] = GRIPPER_CLOSED
            move_to(lifted_l, lifted_r, 1.2, "Lifting the items...")

            carry_l = CFG_L.q2urdf(np.asarray(CFG_L.home, dtype=np.float64))
            carry_r = CFG_R.q2urdf(np.asarray(CFG_R.home, dtype=np.float64))
            carry_l[CFG_L.dof - 1] = GRIPPER_CLOSED
            carry_r[CFG_R.dof - 1] = GRIPPER_CLOSED
            move_to(carry_l, carry_r, 2.5, "Retracting both arms...")

            if stopped:
                return 130
            stage("driving")
            deactivate_lean(lean_angle_deg)
            route_command = [
                sys.executable,
                str(Path(__file__).with_name("recorded_route.py")),
                str(args.route),
                "--execute",
                "--yes",
            ]
            route_process = subprocess.Popen(route_command)
            while route_process.poll() is None and not stopped:
                write_pose(carry_l, carry_r)
                time.sleep(0.01)
            route_code = route_process.wait()
            route_process = None
            if stopped:
                return 130
            if route_code != 0:
                failure("blocked")
                return 2

            drop_l = solve_target(CFG_L, current_l, delta, "left")
            drop_r = solve_target(CFG_R, current_r, delta, "right")
            drop_l[CFG_L.dof - 1] = GRIPPER_CLOSED
            drop_r[CFG_R.dof - 1] = GRIPPER_CLOSED
            move_to(drop_l, drop_r, 2.5, "Extending and lowering both items...")

            stage("arrived")
            released_l, released_r = current_l.copy(), current_r.copy()
            released_l[CFG_L.dof - 1] = GRIPPER_OPEN
            released_r[CFG_R.dof - 1] = GRIPPER_OPEN
            move_to(released_l, released_r, 0.8, "Releasing both items...")
            hold_until = time.monotonic() + args.hold_seconds
            while not stopped and time.monotonic() < hold_until:
                write_pose(released_l, released_r)
                time.sleep(0.01)

            home_l = CFG_L.q2urdf(np.asarray(CFG_L.home, dtype=np.float64))
            home_r = CFG_R.q2urdf(np.asarray(CFG_R.home, dtype=np.float64))
            home_l[CFG_L.dof - 1] = GRIPPER_OPEN
            home_r[CFG_R.dof - 1] = GRIPPER_OPEN
            move_to(home_l, home_r, 2.5, "Retracting both arms...")

            audio = Path(__file__).with_name("completion_audio.wav")
            if audio.is_file() and not stopped:
                subprocess.run(
                    [
                        sys.executable,
                        str(Path(__file__).with_name("play_robot_audio.py")),
                        str(audio),
                        "--volume",
                        "0.95",
                    ],
                    check=False,
                )
            print("TRANSFER COMPLETE.", flush=True)
        finally:
            print("Parking arms and turning torque off...", flush=True)
            park_arms([
                dict(cfg=CFG_L, r_state=state_l, w_ctrl=ctrl_l, w_torque=torque_l,
                     waypoints=[*CFG_L.startup_waypoints, CFG_L.home],
                     seg_durations=CFG_L.startup_seg_durations),
                dict(cfg=CFG_R, r_state=state_r, w_ctrl=ctrl_r, w_torque=torque_r,
                     waypoints=[*CFG_R.startup_waypoints, CFG_R.home],
                     seg_durations=CFG_R.startup_seg_durations),
            ])

    return 130 if stopped else 0


if __name__ == "__main__":
    raise SystemExit(main())
