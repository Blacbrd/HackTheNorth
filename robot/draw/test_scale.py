# /// script
# requires-python = ">=3.10,<3.11"
# dependencies = ["bbos","numpy<2","opencv-python-headless","fastapi","uvicorn"]
# [tool.uv.sources]
# bbos = { path = "/home/bracketbot/bbos", editable = true }
# ///
"""Reproduce the claim that detection must run at full resolution.

Runs the detector over one real frame at several scales and prints the cost and
the result, so the default in page_server.py is a measurement you can re-check
rather than a number someone asserted.

    uv run grab_frame.py        # saves /tmp/head.jpg
    uv run test_scale.py

Expect scale 1.0 to find a plausible page (aspect error well under 0.05) and
the smaller scales to get slightly faster while getting the answer wrong.
"""

import argparse
import time

import cv2

import page_server as ps
from detect_page import PAPER_SIZES_MM


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="/tmp/head.jpg")
    parser.add_argument("--paper", choices=sorted(PAPER_SIZES_MM),
                        default="letter")
    parser.add_argument("--paper-mm", type=float, nargs=2,
                        metavar=("SHORT", "LONG"))
    parser.add_argument("--min-area", type=float, default=0.008)
    parser.add_argument("--scales", type=float, nargs="+",
                        default=[1.0, 0.75, 0.5])
    args = parser.parse_args()

    paper_mm = tuple(args.paper_mm) if args.paper_mm else PAPER_SIZES_MM[args.paper]
    image = cv2.imread(args.source, cv2.IMREAD_COLOR)
    if image is None:
        print(f"cannot read {args.source}; run grab_frame.py first")
        return 2
    print(f"{args.source}  {image.shape[1]}x{image.shape[0]}  "
          f"paper {paper_mm[0]}x{paper_mm[1]}mm\n")

    for scale in args.scales:
        detector = ps.Detector(paper_mm, args.min_area, 4, 12.0, scale)
        best_ms = min(_time_once(detector, image) for _ in range(5))
        candidate = detector._detect(image)
        if candidate is None:
            print(f"scale {scale:<5} {best_ms:6.0f} ms  NOT FOUND")
            continue
        result = ps.build_result(candidate, candidate["quad"], image.shape, 1)
        quality = result["quality"]
        verdict = "looks like paper" if quality["aspect_error"] < 0.05 else \
            "WRONG OBJECT"
        print(f"scale {scale:<5} {best_ms:6.0f} ms  found  "
              f"area={quality['area_fraction']:.4f}  "
              f"aspect_err={quality['aspect_error']:.3f}  {verdict}")
    return 0


def _time_once(detector: ps.Detector, image) -> float:
    started = time.monotonic()
    detector._detect(image)
    return (time.monotonic() - started) * 1000.0


if __name__ == "__main__":
    raise SystemExit(main())
