#!/usr/bin/env python3
"""
Standalone ring-to-key mapper.

This project sits outside AQual but reuses AQual's HID ring detection
helpers so the same ring button decoding can drive direct macOS key
presses without any UI.
"""

from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
import time
from pathlib import Path


STOP = False
ACCESSIBILITY_HINT_PRINTED = False
EXPECTED_BUTTONS = ("left", "right", "top", "bottom", "center", "home")
DEFAULT_ACTION_LABELS = {
    "keypress": "Key Press",
    "volume_up": "Volume Up",
    "volume_down": "Volume Down",
}
DEFAULT_KEY_LABELS = {
    36: "Enter",
    49: "Space",
    123: "Left Arrow",
    124: "Right Arrow",
    125: "Down Arrow",
    126: "Up Arrow",
}

PROJECT_DIR = Path(__file__).resolve().parent
AQUAL_ROOT = PROJECT_DIR.parent / "AQual"

if str(AQUAL_ROOT) not in sys.path:
    sys.path.insert(0, str(AQUAL_ROOT))

try:
    from servers.bionic import ring_monitor
except Exception as exc:  # pragma: no cover
    print(
        "[ring-keys] Failed to import AQual ring helpers.\n"
        f"[ring-keys] Expected AQual at: {AQUAL_ROOT}\n"
        f"[ring-keys] Import error: {exc}",
        file=sys.stderr,
    )
    raise


# ring-to-keyboard contains the six-button Yiser decoder, while the public
# AQual helper currently exposes only the original center-button profile.
# Supply the small protocol helpers expected by this mapper when that older
# helper version is installed. Yiser reports are report-id 1, followed by a
# contact/button byte and little-endian X/Y coordinates. The stationary
# button coordinate is (220, 300); moving coordinates represent directional
# swipes. Value 3 is center and value 2 is the secondary/home button.
if not hasattr(ring_monitor, "YISER_J6_HIGH_CONTRAST_VALUES"):
    ring_monitor.YISER_J6_HIGH_CONTRAST_VALUES = (2,)

if not hasattr(ring_monitor, "_extract_yiser_button_value"):
    def _extract_yiser_button_value(report) -> int | None:
        if len(report) < 6 or int(report[0]) != 1:
            return None
        x = (int(report[3]) << 8) | int(report[2])
        y = (int(report[5]) << 8) | int(report[4])
        if (x, y) != (220, 300):
            return None
        return int(report[1]) & 0xFF

    ring_monitor._extract_yiser_button_value = _extract_yiser_button_value

if not hasattr(ring_monitor, "_extract_yiser_directional_axes"):
    def _extract_yiser_directional_axes(report) -> dict[str, int | bool] | None:
        if len(report) < 6 or int(report[0]) != 1:
            return None
        value = int(report[1]) & 0xFF
        x = (int(report[3]) << 8) | int(report[2])
        y = (int(report[5]) << 8) | int(report[4])
        return {"pressed": bool(value & 1), "x": x, "y": y}

    ring_monitor._extract_yiser_directional_axes = _extract_yiser_directional_axes

if not hasattr(ring_monitor, "_classify_yiser_direction_button"):
    def _classify_yiser_direction_button(delta_x: int, delta_y: int) -> str | None:
        minimum_travel = 18
        if max(abs(delta_x), abs(delta_y)) < minimum_travel:
            return None
        if abs(delta_x) >= abs(delta_y):
            return "right" if delta_x > 0 else "left"
        return "bottom" if delta_y > 0 else "top"

    ring_monitor._classify_yiser_direction_button = _classify_yiser_direction_button


def _handle_signal(_signum, _frame):
    global STOP
    STOP = True


def _load_mapping(path: Path) -> dict[str, dict[str, object]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Mapping file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Mapping file is not valid JSON: {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise RuntimeError(f"Mapping file must contain a JSON object: {path}")

    mapping: dict[str, dict[str, object]] = {}
    for button in EXPECTED_BUTTONS:
        entry = raw.get(button)
        if not isinstance(entry, dict):
            raise RuntimeError(f"Missing mapping object for '{button}' in {path}")
        action = str(entry.get("action") or "keypress").strip().lower()
        if action == "keypress":
            key_code = entry.get("key_code")
            if key_code is None:
                raise RuntimeError(f"Missing 'key_code' for '{button}' in {path}")
            try:
                key_code_int = int(key_code)
            except Exception as exc:
                raise RuntimeError(f"Invalid key_code for '{button}' in {path}: {key_code}") from exc
            label = str(entry.get("label") or DEFAULT_KEY_LABELS.get(key_code_int) or f"Key code {key_code_int}")
            mapping[button] = {
                "action": action,
                "key_code": key_code_int,
                "label": label,
            }
            continue

        if action not in ("volume_up", "volume_down"):
            raise RuntimeError(f"Unsupported action for '{button}' in {path}: {action}")

        label = str(entry.get("label") or DEFAULT_ACTION_LABELS.get(action) or action)
        mapping[button] = {
            "action": action,
            "label": label,
        }
    return mapping


def _print_mapping_summary(mapping: dict[str, dict[str, object]]) -> None:
    print("[ring-keys] active mappings:")
    for button in EXPECTED_BUTTONS:
        entry = mapping[button]
        action = str(entry.get("action") or "keypress")
        if action == "keypress":
            print(
                f"[ring-keys]   {button:>6} -> {entry['label']} "
                f"(key code {entry['key_code']})"
            )
        else:
            print(
                f"[ring-keys]   {button:>6} -> {entry['label']} "
                f"({action})"
            )


def _run_osascript(script: str) -> None:
    subprocess.run(
        ["osascript", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )


def _emit_action(mapping: dict[str, dict[str, object]], button_label: str) -> None:
    global ACCESSIBILITY_HINT_PRINTED

    entry = mapping.get(button_label)
    if not entry:
        print(f"[ring-keys] No mapping configured for '{button_label}'", file=sys.stderr)
        return

    action = str(entry.get("action") or "keypress")
    label = str(entry["label"])

    try:
        if action == "keypress":
            key_code = int(entry["key_code"])
            _run_osascript(f'tell application "System Events" to key code {key_code}')
        elif action == "volume_up":
            _run_osascript(
                'set currentVolume to output volume of (get volume settings)\n'
                'set newVolume to currentVolume + 6\n'
                'if newVolume > 100 then set newVolume to 100\n'
                'set volume output volume newVolume'
            )
        elif action == "volume_down":
            _run_osascript(
                'set currentVolume to output volume of (get volume settings)\n'
                'set newVolume to currentVolume - 6\n'
                'if newVolume < 0 then set newVolume to 0\n'
                'set volume output volume newVolume'
            )
        else:
            print(f"[ring-keys] Unsupported action '{action}' for '{button_label}'", file=sys.stderr)
            return
        print(f"[ring-keys] button={button_label} -> {label}")
    except FileNotFoundError:
        print("[ring-keys] osascript was not found on this machine.", file=sys.stderr)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        detail = f": {stderr}" if stderr else ""
        print(f"[ring-keys] failed to emit {label}{detail}", file=sys.stderr)
        if action == "keypress" and not ACCESSIBILITY_HINT_PRINTED:
            ACCESSIBILITY_HINT_PRINTED = True
            print(
                "[ring-keys] hint: macOS may need Accessibility permission for "
                "Terminal and System Events before key presses can be sent.",
                file=sys.stderr,
            )


def _monitor_device(args, device_info, mapping: dict[str, dict[str, object]]) -> None:
    device, open_method = ring_monitor._open_hid_device(device_info)
    device.set_nonblocking(True)

    print(f"[ring-keys] connected: {ring_monitor._device_label(device_info)} via {open_method}")
    use_strict_yiser_profile = ring_monitor._is_preferred_ring(device_info) and not args.disable_yiser_filter
    if use_strict_yiser_profile:
        print(
            "[ring-keys] strict Yiser profile active: "
            f"byte_index={args.target_byte_index} press_value={args.yiser_press_value} "
            f"home_values={list(ring_monitor.YISER_J6_HIGH_CONTRAST_VALUES)}"
        )

    last_report = None
    last_press_ms = 0.0
    press_armed = True
    press_active = False
    press_started_ms = 0.0
    hold_reported = False
    directional_active = False
    directional_start_x = 0
    directional_start_y = 0
    directional_last_x = 0
    directional_last_y = 0
    directional_min_x = 0
    directional_max_x = 0
    directional_min_y = 0
    directional_max_y = 0
    directional_frame_count = 0

    try:
        while not STOP:
            now_ms = time.time() * 1000.0
            try:
                report = device.read(args.report_length)
            except Exception as exc:
                raise RuntimeError(f"HID read failed: {exc}") from exc

            if not report:
                if press_active and not hold_reported and (now_ms - press_started_ms >= args.hold_ms):
                    hold_reported = True
                    print(
                        f"[ring-keys] hold ongoing duration_ms={now_ms - press_started_ms:.1f} "
                        f"(threshold={args.hold_ms})"
                    )
                time.sleep(args.poll_ms / 1000.0)
                continue

            report_norm = tuple(int(byte) & 0xFF for byte in report)
            if last_report is None:
                last_report = report_norm
                if args.verbose:
                    print(f"[ring-keys] baseline={json.dumps(list(report_norm)[:16])}")
                continue

            if report_norm == last_report:
                continue

            rising_edge_indexes = []
            falling_edge_indexes = []
            changed = 0
            button_label = None
            unknown_button_value = None
            directional_emit = False

            if use_strict_yiser_profile:
                prev_value = ring_monitor._extract_yiser_button_value(last_report)
                curr_value = ring_monitor._extract_yiser_button_value(report_norm)

                if curr_value is None:
                    prev_directional = ring_monitor._extract_yiser_directional_axes(last_report)
                    curr_directional = ring_monitor._extract_yiser_directional_axes(report_norm)
                    if curr_directional is None:
                        if directional_active:
                            directional_active = False
                            directional_frame_count = 0
                            if args.verbose:
                                print(
                                    "[ring-keys] directional reset due to unexpected frame="
                                    f"{json.dumps(list(report_norm)[:16])}"
                                )
                        elif args.verbose:
                            print(f"[ring-keys] ignored non-target frame={json.dumps(list(report_norm)[:16])}")
                        last_report = report_norm
                        continue

                    prev_pressed = bool(prev_directional and prev_directional.get("pressed"))
                    curr_pressed = bool(curr_directional.get("pressed"))
                    prev_x = int(prev_directional.get("x")) if prev_directional else int(curr_directional.get("x"))
                    prev_y = int(prev_directional.get("y")) if prev_directional else int(curr_directional.get("y"))
                    curr_x = int(curr_directional.get("x"))
                    curr_y = int(curr_directional.get("y"))
                    if prev_pressed != curr_pressed or prev_x != curr_x or prev_y != curr_y:
                        changed = 1

                    if not prev_pressed and curr_pressed:
                        directional_active = True
                        directional_start_x = curr_x
                        directional_start_y = curr_y
                        directional_last_x = curr_x
                        directional_last_y = curr_y
                        directional_min_x = curr_x
                        directional_max_x = curr_x
                        directional_min_y = curr_y
                        directional_max_y = curr_y
                        directional_frame_count = 1
                        if args.verbose:
                            print(
                                f"[ring-keys] directional start x={curr_x} y={curr_y} "
                                f"report={json.dumps(list(report_norm)[:16])}"
                            )
                        last_report = report_norm
                        continue

                    if curr_pressed:
                        if not directional_active:
                            directional_active = True
                            directional_start_x = prev_x
                            directional_start_y = prev_y
                            directional_min_x = min(prev_x, curr_x)
                            directional_max_x = max(prev_x, curr_x)
                            directional_min_y = min(prev_y, curr_y)
                            directional_max_y = max(prev_y, curr_y)
                            directional_frame_count = 0
                        directional_last_x = curr_x
                        directional_last_y = curr_y
                        directional_min_x = min(directional_min_x, curr_x)
                        directional_max_x = max(directional_max_x, curr_x)
                        directional_min_y = min(directional_min_y, curr_y)
                        directional_max_y = max(directional_max_y, curr_y)
                        directional_frame_count += 1
                        last_report = report_norm
                        continue

                    if prev_pressed and directional_active:
                        directional_last_x = curr_x
                        directional_last_y = curr_y
                        directional_min_x = min(directional_min_x, curr_x)
                        directional_max_x = max(directional_max_x, curr_x)
                        directional_min_y = min(directional_min_y, curr_y)
                        directional_max_y = max(directional_max_y, curr_y)
                        directional_frame_count += 1
                        delta_x = int(directional_last_x - directional_start_x)
                        delta_y = int(directional_last_y - directional_start_y)
                        button_label = ring_monitor._classify_yiser_direction_button(delta_x, delta_y)
                        directional_active = False
                        if button_label:
                            directional_emit = True
                            print(
                                f"[ring-keys] directional button={button_label} "
                                f"dx={delta_x} dy={delta_y} frames={directional_frame_count}"
                            )
                        else:
                            print(
                                "[ring-keys] unknown directional press "
                                f"dx={delta_x} dy={delta_y} frames={directional_frame_count} "
                                f"report={json.dumps(list(report_norm)[:16])}"
                            )
                        directional_frame_count = 0
                    else:
                        last_report = report_norm
                        continue
                else:
                    if directional_active:
                        directional_active = False
                        directional_frame_count = 0

                if curr_value is not None:
                    if prev_value is None:
                        prev_value = 0

                    if prev_value != curr_value:
                        changed = 1

                    if prev_value == 0 and curr_value != 0:
                        rising_edge_indexes.append(int(args.target_byte_index))
                        if curr_value == int(args.yiser_press_value):
                            button_label = "center"
                        elif curr_value in ring_monitor.YISER_J6_HIGH_CONTRAST_VALUES:
                            button_label = "home"
                        else:
                            unknown_button_value = int(curr_value)

                    if prev_value != 0 and curr_value == 0:
                        falling_edge_indexes.append(int(args.target_byte_index))

                    if changed and not rising_edge_indexes and not falling_edge_indexes:
                        if args.verbose:
                            print(
                                "[ring-keys] ignored transition "
                                f"byte[{int(args.target_byte_index)}] {prev_value}->{curr_value}"
                            )
                        last_report = report_norm
                        continue
            else:
                for i in range(min(len(last_report), len(report_norm))):
                    if last_report[i] != report_norm[i]:
                        changed += 1
                        if last_report[i] == 0 and report_norm[i] != 0:
                            rising_edge_indexes.append(i)
                        if last_report[i] != 0 and report_norm[i] == 0:
                            falling_edge_indexes.append(i)

            rising_edge = len(rising_edge_indexes) > 0
            falling_edge = len(falling_edge_indexes) > 0

            if rising_edge and not press_active:
                press_active = True
                press_started_ms = now_ms
                hold_reported = False
                print(
                    f"[ring-keys] press down edge_indexes={rising_edge_indexes} "
                    f"report={json.dumps(list(report_norm)[:16])}"
                )

            should_emit = False
            if use_strict_yiser_profile:
                if directional_emit:
                    should_emit = True
                    press_armed = True
                elif rising_edge and press_armed:
                    press_armed = False
                    if button_label:
                        should_emit = True
                    elif unknown_button_value is not None:
                        print(
                            "[ring-keys] unknown key press "
                            f"value={unknown_button_value} "
                            f"known_center={int(args.yiser_press_value)} "
                            f"known_home={list(ring_monitor.YISER_J6_HIGH_CONTRAST_VALUES)} "
                            f"report={json.dumps(list(report_norm)[:16])}"
                        )
            else:
                if rising_edge:
                    if press_armed:
                        should_emit = True
                        press_armed = False
                elif changed > 0 and not falling_edge:
                    should_emit = True

            if falling_edge:
                press_armed = True
                if press_active:
                    duration_ms = now_ms - press_started_ms
                    if hold_reported or duration_ms >= args.hold_ms:
                        print(
                            f"[ring-keys] hold detected duration_ms={duration_ms:.1f} "
                            f"(threshold={args.hold_ms}) edge_indexes={falling_edge_indexes}"
                        )
                    else:
                        print(
                            f"[ring-keys] tap detected duration_ms={duration_ms:.1f} "
                            f"edge_indexes={falling_edge_indexes}"
                        )
                    press_active = False
                    hold_reported = False
                    press_started_ms = 0.0

            if should_emit and (now_ms - last_press_ms >= args.debounce_ms):
                if button_label:
                    _emit_action(mapping, button_label)
                    last_press_ms = now_ms
                else:
                    print("[ring-keys] event emitted without a decoded button label; ignoring.", file=sys.stderr)

            last_report = report_norm
            if args.verbose:
                print(
                    f"[ring-keys] report={json.dumps(list(report_norm)[:16])} "
                    f"rising_edge={rising_edge} falling_edge={falling_edge} "
                    f"armed={press_armed} press_active={press_active} changed={changed}"
                )
    finally:
        try:
            device.close()
        except Exception:
            pass
        print("[ring-keys] disconnected")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Map AQual ring buttons to macOS keyboard keys.")
    parser.add_argument(
        "--mapping-file",
        default=str(PROJECT_DIR / "ring_keymap.json"),
        help="Path to JSON file describing ring button to key mappings.",
    )
    parser.add_argument("--vid", default=None, help="Optional VID filter, e.g. 0x1234.")
    parser.add_argument("--pid", default=None, help="Optional PID filter, e.g. 0x5678.")
    parser.add_argument("--usage-page", default=None, help="Optional usage page filter, default auto=0x000D.")
    parser.add_argument("--all-usages", action="store_true", help="Do not restrict by usage page when auto-matching.")
    parser.add_argument("--name-contains", default="", help="Optional product/manufacturer substring.")
    parser.add_argument("--index", type=int, default=-1, help="Candidate index to use. -1 = auto-select best match.")
    parser.add_argument(
        "--allow-non-ring",
        action="store_true",
        help="Allow fallback to non-ring HID devices (disabled by default).",
    )
    parser.add_argument("--poll-ms", type=int, default=15, help="Read polling interval in ms.")
    parser.add_argument("--debounce-ms", type=int, default=260, help="Debounce for press events.")
    parser.add_argument("--hold-ms", type=int, default=450, help="Hold threshold in ms for hold logging.")
    parser.add_argument(
        "--disable-yiser-filter",
        action="store_true",
        help="Disable strict button filtering for Yiser-J6 devices.",
    )
    parser.add_argument(
        "--target-byte-index",
        type=int,
        default=ring_monitor.YISER_J6_DEFAULT_BUTTON_INDEX,
        help="Strict filter byte index used for center/home transitions.",
    )
    parser.add_argument(
        "--yiser-press-value",
        default=str(ring_monitor.YISER_J6_DEFAULT_PRESS_VALUE),
        help="Strict filter press value for the center button.",
    )
    parser.add_argument("--report-length", type=int, default=64, help="HID report read length.")
    parser.add_argument(
        "--open-retry-sec",
        type=float,
        default=2.0,
        help="Cooldown before retrying a candidate that failed to open.",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose HID logging.")
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()
    args.mapping_file = str(Path(args.mapping_file).expanduser().resolve())
    args.vid = ring_monitor._parse_int(args.vid, default=None) if args.vid is not None else None
    args.pid = ring_monitor._parse_int(args.pid, default=None) if args.pid is not None else None
    args.usage_page = ring_monitor._parse_int(args.usage_page, default=None) if args.usage_page is not None else None
    args.yiser_press_value = ring_monitor._parse_int(
        args.yiser_press_value,
        default=ring_monitor.YISER_J6_DEFAULT_PRESS_VALUE,
    )

    mapping = _load_mapping(Path(args.mapping_file))
    _print_mapping_summary(mapping)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    failed_open_until: dict[tuple[object, ...], float] = {}

    print("[ring-keys] starting. Press Ctrl+C to stop.")
    while not STOP:
        ranked = ring_monitor._rank_candidates(args)
        if not ranked:
            print("[ring-keys] waiting for matching HID device...")
            time.sleep(1.0)
            continue

        now = time.time()
        expired_keys = [key for key, until in failed_open_until.items() if until <= now]
        for key in expired_keys:
            failed_open_until.pop(key, None)

        attempted_any = False
        opened_any = False
        for device_info in ranked:
            device_key = ring_monitor._stable_device_key(device_info)
            blocked_until = failed_open_until.get(device_key, 0.0)
            if blocked_until > now:
                if args.verbose:
                    remaining = max(0.0, blocked_until - now)
                    print(
                        f"[ring-keys] skipping candidate (cooldown {remaining:.1f}s): "
                        f"{ring_monitor._device_label(device_info)}"
                    )
                continue

            attempted_any = True
            try:
                _monitor_device(args, device_info, mapping)
                opened_any = True
                failed_open_until.pop(device_key, None)
                if STOP:
                    break
            except Exception as exc:
                if STOP:
                    break
                message = str(exc)
                print(f"[ring-keys] device loop error: {message}", file=sys.stderr)
                message_lower = message.lower()
                if "open failed" in message_lower or "access denied" in message_lower or "permission" in message_lower:
                    failed_open_until[device_key] = time.time() + max(0.5, float(args.open_retry_sec))
                    if ring_monitor._is_os_protected_hid_profile(device_info):
                        print(
                            "[ring-keys] hint: macOS is likely denying user-level access to this "
                            "keyboard/consumer HID interface."
                        )
                    else:
                        print(
                            "[ring-keys] hint: another process may already hold this HID interface. "
                            "Disconnect the ring from other apps first."
                        )
                time.sleep(0.2)

        if STOP:
            break
        if not attempted_any:
            print("[ring-keys] all matching candidates are cooling down after open failures...")
            time.sleep(0.6)
            continue
        if not opened_any:
            time.sleep(1.0)
            continue

    print("[ring-keys] stopped.")


if __name__ == "__main__":
    main()
