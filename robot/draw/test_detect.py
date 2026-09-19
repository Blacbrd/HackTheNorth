# /// script
# requires-python = ">=3.10,<3.11"
# dependencies = ["numpy<2", "opencv-python-headless"]
# ///
"""Synthetic check: render a page at known corners, detect it, compare."""
import subprocess, json, sys
import cv2, numpy as np

W, H = 1280, 960
TRUE = np.array([[380, 250], [980, 300], [1040, 830], [300, 760]], dtype=np.float32)

img = np.full((H, W, 3), 60, np.uint8)
cv2.randn(img, 60, 8)
cv2.fillConvexPoly(img, TRUE.astype(np.int32), (238, 240, 243))
# a few pen strokes so it isn't a perfectly blank blob
cv2.line(img, (500, 400), (800, 600), (40, 40, 40), 3)
cv2.imwrite("/tmp/page_test.png", img)

out = subprocess.run([sys.executable, "detect_page.py", "--source", "/tmp/page_test.png",
                      "--paper", "letter", "--debug-image", "/tmp/page_debug.png",
                      "--point", "0", "0", "--point", "215.9", "279.4"],
                     capture_output=True, text=True, cwd="/home/bracketbot/bbapps/draw")
print(out.stderr.strip()[-400:])
data = json.loads(out.stdout)
if not data.get("found"):
    print("FAIL: no page found"); sys.exit(1)

print("orientation:", data["orientation"], "page_mm:", data["page_mm"])
det = np.array([data["corners_px"][k] for k in ("tl", "tr", "br", "bl")], np.float32)
print("corner error px:", np.linalg.norm(det - TRUE, axis=1).round(2).tolist())

# round-trip: page corners in mm must land back on the true pixel corners
mm2px = np.array(data["homography_mm_to_px"], np.float32)
px2mm = np.array(data["homography_px_to_mm"], np.float32)
w, h = data["page_mm"]
corners_mm = np.array([[[0, 0]], [[w, 0]], [[w, h]], [[0, h]]], np.float32)
back = cv2.perspectiveTransform(corners_mm, mm2px).reshape(4, 2)
print("mm->px round trip err:", np.linalg.norm(back - det, axis=1).round(3).tolist())

centre_px = cv2.perspectiveTransform(np.array([[[w/2, h/2]]], np.float32), mm2px).reshape(2)
centre_mm = cv2.perspectiveTransform(np.array([[centre_px]], np.float32), px2mm).reshape(2)
print(f"centre {w/2:.1f},{h/2:.1f}mm -> px {centre_px.round(1).tolist()} -> mm {centre_mm.round(3).tolist()}")
print("pose z (m):", round(data["pose_camera_approx"]["translation_m"][2], 3))
