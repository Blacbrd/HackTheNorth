# /// script
# requires-python = ">=3.10,<3.11"
# dependencies = ["bbos", "numpy<2", "opencv-python-headless"]
# [tool.uv.sources]
# bbos = { path = "/home/bracketbot/bbos", editable = true }
# ///
"""Find the sheet of paper in the head camera and map its surface to mm.

Prints a JSON page frame whose origin is the paper's top-left corner, with x
running along the top edge and y down the left edge, both in mm. The phone
sends drawing coordinates in exactly that frame.

The px-to-mm homography needs no camera calibration: four corners and the real
paper size determine it. The 3D pose it also reports leans on a guessed focal
length, so treat that as approximate.

Read-only. This never commands the robot.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

PAPER_SIZES_MM = {
    "letter": (215.9, 279.4),
    "a4": (210.0, 297.0),
    "a5": (148.0, 210.0),
    "legal": (215.9, 355.6),
}

# Quad filters. A page seen from the head camera is a big, convex, near-square
# blob whose corners stay well away from right angles only under heavy skew.
MIN_AREA_FRAC = 0.01
MAX_AREA_FRAC = 0.90
MIN_ANGLE_DEG = 45.0
MAX_ANGLE_DEG = 135.0
MIN_EDGE_PX = 40.0
MIN_FILL = 0.80          # source contour area over quad area
MAX_FILL = 1.20
MAX_ASPECT_LOG_ERR = 0.45   # accept up to ~1.57x off the paper's true ratio

STABLE_FRAMES = 8
STABLE_TOL_PX = 6.0
CORNER_NAMES = ("tl", "tr", "br", "bl")


# ============================================================================
# Geometry
# ============================================================================
def order_corners(points: np.ndarray) -> np.ndarray:
    """Return the four corners as TL, TR, BR, BL in image order.

    Sorting by angle around the centroid gives the ring in image-clockwise
    order; rolling the corner nearest the image origin to the front names them.
    """
    points = np.asarray(points, dtype=np.float64).reshape(4, 2)
    center = points.mean(axis=0)
    angles = np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0])
    ring = points[np.argsort(angles)]
    start = int(np.argmin(ring.sum(axis=1)))
    return np.roll(ring, -start, axis=0)


def corner_angles(quad: np.ndarray) -> list[float]:
    """Interior angle at each corner, in degrees."""
    angles = []
    for i in range(4):
        previous = quad[(i - 1) % 4] - quad[i]
        following = quad[(i + 1) % 4] - quad[i]
        cosine = float(np.dot(previous, following) / (
            np.linalg.norm(previous) * np.linalg.norm(following) + 1e-9))
        angles.append(math.degrees(math.acos(max(-1.0, min(1.0, cosine)))))
    return angles


def edge_lengths(quad: np.ndarray) -> tuple[float, float]:
    """Mean horizontal and mean vertical edge length, in pixels."""
    top = float(np.linalg.norm(quad[1] - quad[0]))
    bottom = float(np.linalg.norm(quad[2] - quad[3]))
    left = float(np.linalg.norm(quad[3] - quad[0]))
    right = float(np.linalg.norm(quad[2] - quad[1]))
    return 0.5 * (top + bottom), 0.5 * (left + right)


# ============================================================================
# Detection
# ============================================================================
def _quads_from_mask(mask: np.ndarray) -> list[tuple[np.ndarray, float]]:
    contours, _hierarchy = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    found = []
    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        if perimeter < 200.0:
            continue
        for epsilon in (0.02, 0.03, 0.05):
            approximation = cv2.approxPolyDP(contour, epsilon * perimeter, True)
            if len(approximation) == 4 and cv2.isContourConvex(approximation):
                found.append((approximation.reshape(4, 2).astype(np.float64),
                              float(cv2.contourArea(contour))))
                break
    return found


def candidate_quads(gray: np.ndarray) -> list[tuple[np.ndarray, float]]:
    """Propose page-shaped quads using three independent segmentations.

    Edges alone lose a page on a pale desk; Otsu alone loses it under a shadow.
    Running all three and scoring the union is cheaper than tuning one.
    """
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    kernel = np.ones((3, 3), np.uint8)
    quads = []

    median = float(np.median(blurred))
    edges = cv2.Canny(blurred, int(max(0.0, 0.66 * median)),
                      int(min(255.0, 1.33 * median)))
    quads += _quads_from_mask(cv2.dilate(edges, kernel, iterations=1))

    _threshold, otsu = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    quads += _quads_from_mask(cv2.morphologyEx(
        otsu, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)))

    adaptive = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, -10)
    quads += _quads_from_mask(cv2.morphologyEx(
        adaptive, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)))
    return quads


def score_quad(quad: np.ndarray, contour_area: float, shape: tuple,
               paper_mm: tuple[float, float],
               min_area_frac: float = MIN_AREA_FRAC) -> dict | None:
    """Score one quad as a page, or return None with the reason it failed."""
    quad = order_corners(quad)
    height, width = shape[:2]
    area = float(cv2.contourArea(quad.astype(np.float32)))
    if area <= 0.0:
        return {"reason": "degenerate"}

    fraction = area / float(width * height)
    if not min_area_frac <= fraction <= MAX_AREA_FRAC:
        return {"reason": "area"}

    angles = corner_angles(quad)
    if min(angles) < MIN_ANGLE_DEG or max(angles) > MAX_ANGLE_DEG:
        return {"reason": "angles"}

    fill = contour_area / area
    if not MIN_FILL <= fill <= MAX_FILL:
        return {"reason": "fill"}

    horizontal, vertical = edge_lengths(quad)
    if min(horizontal, vertical) < MIN_EDGE_PX:
        return {"reason": "tiny"}

    # A four-point homography fits any convex quad to any rectangle exactly, so
    # the aspect ratio has to be judged in pixels. Perspective skews it, hence
    # the loose tolerance; it only has to separate paper from desk clutter.
    short_mm, long_mm = min(paper_mm), max(paper_mm)
    observed = horizontal / vertical
    error_landscape = abs(math.log(observed / (long_mm / short_mm)))
    error_portrait = abs(math.log(observed / (short_mm / long_mm)))
    landscape = error_landscape <= error_portrait
    aspect_error = min(error_landscape, error_portrait)
    if aspect_error > MAX_ASPECT_LOG_ERR:
        return {"reason": "aspect"}

    squareness = 1.0 - (max(abs(a - 90.0) for a in angles) / 90.0)
    score = (fraction ** 0.5) * (1.0 - aspect_error / MAX_ASPECT_LOG_ERR) * squareness
    page_mm = (long_mm, short_mm) if landscape else (short_mm, long_mm)
    return {"quad": quad, "score": float(score), "page_mm": page_mm,
            "landscape": landscape, "aspect_error": float(aspect_error),
            "area_fraction": float(fraction), "angles": angles}


def find_page(image: np.ndarray, paper_mm: tuple[float, float],
              verbose: bool = False,
              min_area_frac: float = MIN_AREA_FRAC) -> dict | None:
    """Return the best page candidate in one frame, or None."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    best = None
    rejects: dict[str, int] = {}
    for quad, contour_area in candidate_quads(gray):
        scored = score_quad(quad, contour_area, image.shape, paper_mm,
                            min_area_frac)
        if scored is None or "reason" in scored:
            reason = "none" if scored is None else scored["reason"]
            rejects[reason] = rejects.get(reason, 0) + 1
            continue
        if best is None or scored["score"] > best["score"]:
            best = scored
    if verbose and best is None and rejects:
        print(f"  rejected: {rejects}", file=sys.stderr, flush=True)
    return best


def page_frame(quad: np.ndarray, page_mm: tuple[float, float]) -> dict:
    """Build the paper-surface frame: homographies and an approximate pose."""
    width_mm, height_mm = page_mm
    source = quad.astype(np.float32)
    destination = np.array([[0.0, 0.0], [width_mm, 0.0],
                            [width_mm, height_mm], [0.0, height_mm]],
                           dtype=np.float32)
    px_to_mm = cv2.getPerspectiveTransform(source, destination)
    mm_to_px = cv2.getPerspectiveTransform(destination, source)
    return {"px_to_mm": px_to_mm, "mm_to_px": mm_to_px}


def approximate_pose(quad: np.ndarray, page_mm: tuple[float, float],
                     image_shape: tuple) -> dict | None:
    """Solve the paper's pose in the camera frame with a guessed focal length.

    marker_alignment.py makes the same guess for the same reason: this robot
    has no saved intrinsics. Distances are indicative, not measured.
    """
    height, width = image_shape[:2]
    focal = width * 0.75
    camera_matrix = np.array([[focal, 0.0, width / 2.0],
                              [0.0, focal, height / 2.0],
                              [0.0, 0.0, 1.0]], dtype=np.float64)
    width_m, height_m = page_mm[0] / 1000.0, page_mm[1] / 1000.0
    object_points = np.array([[0.0, 0.0, 0.0], [width_m, 0.0, 0.0],
                              [width_m, height_m, 0.0], [0.0, height_m, 0.0]],
                             dtype=np.float64)
    ok, rvec, tvec = cv2.solvePnP(object_points, quad, camera_matrix,
                                  np.zeros(5), flags=cv2.SOLVEPNP_IPPE)
    translation = np.asarray(tvec, dtype=np.float64).reshape(3)
    if not ok or translation[2] <= 0.0:
        return None
    rotation, _jacobian = cv2.Rodrigues(rvec)
    return {"rotation": [float(v) for v in rotation.reshape(-1)],
            "translation_m": [float(v) for v in translation],
            "focal_pixels_assumed": float(focal)}


# ============================================================================
# Output
# ============================================================================
def to_paper_mm(homography: np.ndarray, point_px) -> tuple[float, float]:
    point = np.array([[[float(point_px[0]), float(point_px[1])]]],
                     dtype=np.float32)
    mapped = cv2.perspectiveTransform(point, homography).reshape(2)
    return float(mapped[0]), float(mapped[1])


def to_pixels(homography: np.ndarray, point_mm) -> tuple[float, float]:
    point = np.array([[[float(point_mm[0]), float(point_mm[1])]]],
                     dtype=np.float32)
    mapped = cv2.perspectiveTransform(point, homography).reshape(2)
    return float(mapped[0]), float(mapped[1])


def build_result(best: dict, quad: np.ndarray, image_shape: tuple,
                 frames: int) -> dict:
    frame = page_frame(quad, best["page_mm"])
    pose = approximate_pose(quad, best["page_mm"], image_shape)
    height, width = image_shape[:2]
    return {
        "found": True,
        "image_size_px": [int(width), int(height)],
        "page_mm": [round(best["page_mm"][0], 2), round(best["page_mm"][1], 2)],
        "orientation": "landscape" if best["landscape"] else "portrait",
        "corners_px": {name: [round(float(x), 2), round(float(y), 2)]
                       for name, (x, y) in zip(CORNER_NAMES, quad)},
        "homography_px_to_mm": frame["px_to_mm"].tolist(),
        "homography_mm_to_px": frame["mm_to_px"].tolist(),
        "pose_camera_approx": pose,
        "quality": {"score": round(best["score"], 4),
                    "area_fraction": round(best["area_fraction"], 4),
                    "aspect_error": round(best["aspect_error"], 4),
                    "corner_angles_deg": [round(a, 1) for a in best["angles"]],
                    "stable_frames": frames},
    }


def annotate(image: np.ndarray, result: dict, points_mm=()) -> np.ndarray:
    """Draw the detected page, its origin, and a 25 mm grid for eyeballing."""
    canvas = image.copy()
    quad = np.array([result["corners_px"][name] for name in CORNER_NAMES],
                    dtype=np.int32)
    cv2.polylines(canvas, [quad], True, (0, 255, 0), 2)

    mm_to_px = np.array(result["homography_mm_to_px"], dtype=np.float32)
    width_mm, height_mm = result["page_mm"]
    for offset in np.arange(25.0, width_mm, 25.0):
        start = to_pixels(mm_to_px, (offset, 0.0))
        end = to_pixels(mm_to_px, (offset, height_mm))
        cv2.line(canvas, tuple(np.int32(start)), tuple(np.int32(end)),
                 (90, 90, 90), 1)
    for offset in np.arange(25.0, height_mm, 25.0):
        start = to_pixels(mm_to_px, (0.0, offset))
        end = to_pixels(mm_to_px, (width_mm, offset))
        cv2.line(canvas, tuple(np.int32(start)), tuple(np.int32(end)),
                 (90, 90, 90), 1)

    origin = to_pixels(mm_to_px, (0.0, 0.0))
    x_axis = to_pixels(mm_to_px, (min(60.0, width_mm), 0.0))
    y_axis = to_pixels(mm_to_px, (0.0, min(60.0, height_mm)))
    cv2.arrowedLine(canvas, tuple(np.int32(origin)), tuple(np.int32(x_axis)),
                    (0, 0, 255), 3, tipLength=0.2)
    cv2.arrowedLine(canvas, tuple(np.int32(origin)), tuple(np.int32(y_axis)),
                    (255, 0, 0), 3, tipLength=0.2)
    for name, (x, y) in result["corners_px"].items():
        cv2.circle(canvas, (int(x), int(y)), 6, (0, 255, 255), -1)
        cv2.putText(canvas, name.upper(), (int(x) + 8, int(y) - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    for point in points_mm:
        pixel = to_pixels(mm_to_px, point)
        cv2.drawMarker(canvas, tuple(np.int32(pixel)), (255, 0, 255),
                       cv2.MARKER_CROSS, 18, 2)
        cv2.putText(canvas, f"{point[0]:.0f},{point[1]:.0f}",
                    (int(pixel[0]) + 8, int(pixel[1]) + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
    label = (f"{result['page_mm'][0]:.0f}x{result['page_mm'][1]:.0f}mm "
             f"{result['orientation']}")
    cv2.putText(canvas, label, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (0, 255, 0), 2)
    return canvas


# ============================================================================
# Capture
# ============================================================================
def head_frames(timeout_s: float):
    """Yield left-eye frames from the head camera until the timeout."""
    from bbos import Config, Reader

    eye_width = int(Config("cam_head").width // 2)
    started = time.monotonic()
    with Reader("camera.head.jpeg", keeptime=False, sync=True) as camera:
        while time.monotonic() - started < timeout_s:
            if not camera.ready():
                time.sleep(0.01)
                continue
            size = int(camera.data["jpeg_len"])
            if size <= 0:
                continue
            stereo = cv2.imdecode(
                np.frombuffer(camera.data["jpeg"][:size], np.uint8),
                cv2.IMREAD_COLOR)
            if stereo is None:
                continue
            try:
                yield np.ascontiguousarray(stereo[:, :eye_width])
            except GeneratorExit:
                # Breaking out of the caller's loop closes us here; return so
                # the Reader unwinds quietly instead of logging a teardown.
                return


def stable_quad(history: deque, needed: int,
                tolerance: float) -> np.ndarray | None:
    """Return the median quad once the corners have stopped drifting."""
    if len(history) < needed:
        return None
    stack = np.stack(history)
    spread = np.linalg.norm(stack - stack[-1], axis=2).max()
    if spread > tolerance:
        return None
    return np.median(stack, axis=0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", choices=sorted(PAPER_SIZES_MM),
                        default="letter")
    parser.add_argument("--paper-mm", type=float, nargs=2,
                        metavar=("SHORT", "LONG"),
                        help="measured paper size in mm, overrides --paper")
    parser.add_argument("--source", type=Path,
                        help="read an image file instead of the head camera")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--out", type=Path, help="write the JSON here too")
    parser.add_argument("--debug-image", type=Path,
                        help="write an annotated frame here")
    parser.add_argument("--point", type=float, nargs=2, action="append",
                        metavar=("X_MM", "Y_MM"), default=None,
                        help="mark this paper coordinate in the debug image")
    parser.add_argument("--min-area", type=float, default=MIN_AREA_FRAC,
                        help="smallest share of the frame the page may fill")
    parser.add_argument("--stable-frames", type=int, default=STABLE_FRAMES,
                        help="agreeing frames needed before reporting")
    parser.add_argument("--tolerance", type=float, default=STABLE_TOL_PX,
                        help="corner drift allowed across those frames, px")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    paper_mm = tuple(args.paper_mm) if args.paper_mm else PAPER_SIZES_MM[args.paper]
    points_mm = args.point or []

    best = None
    quad = None
    image = None
    frames = 0

    if args.source:
        image = cv2.imread(str(args.source), cv2.IMREAD_COLOR)
        if image is None:
            print(f"cannot read {args.source}", file=sys.stderr)
            return 2
        best = find_page(image, paper_mm, args.verbose, args.min_area)
        if best is not None:
            quad = best["quad"]
            frames = 1
    else:
        history: deque = deque(maxlen=max(1, args.stable_frames))
        last_print = 0.0
        misses = 0
        for image in head_frames(args.timeout):
            candidate = find_page(image, paper_mm, args.verbose, args.min_area)
            if candidate is None:
                # One dropped frame is glare or a passing hand, not the page
                # moving, so the run only resets after a real gap.
                misses += 1
                if misses >= 3:
                    history.clear()
                now = time.monotonic()
                if args.verbose and now - last_print > 1.0:
                    last_print = now
                    print("  no page this frame", file=sys.stderr, flush=True)
                continue
            misses = 0
            history.append(candidate["quad"])
            settled = stable_quad(history, args.stable_frames, args.tolerance)
            if settled is not None:
                best, quad, frames = candidate, settled, len(history)
                break

    if best is None or quad is None:
        print(json.dumps({"found": False,
                          "reason": "no stable page in view"}, indent=2))
        return 2

    result = build_result(best, quad, image.shape, frames)
    payload = json.dumps(result, indent=2)
    print(payload)
    if args.out:
        args.out.write_text(payload + "\n")
    if args.debug_image:
        cv2.imwrite(str(args.debug_image), annotate(image, result, points_mm))
        print(f"wrote {args.debug_image}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
