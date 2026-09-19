# /// script
# requires-python = ">=3.10,<3.11"
# dependencies = ["bbos", "numpy<2", "opencv-python-headless"]
# [tool.uv.sources]
# bbos = { path = "/home/bracketbot/bbos", editable = true }
# ///
"""Save one left-eye head-camera frame to /tmp/head.jpg."""
import time
import cv2, numpy as np
from bbos import Config, Reader

eye = int(Config("cam_head").width // 2)
t0 = time.monotonic()
with Reader("camera.head.jpeg", keeptime=False, sync=True) as cam:
    while time.monotonic() - t0 < 10:
        if not cam.ready():
            time.sleep(0.01); continue
        n = int(cam.data["jpeg_len"])
        if n <= 0: continue
        img = cv2.imdecode(np.frombuffer(cam.data["jpeg"][:n], np.uint8), cv2.IMREAD_COLOR)
        if img is None: continue
        left = np.ascontiguousarray(img[:, :eye])
        cv2.imwrite("/tmp/head.jpg", left, [cv2.IMWRITE_JPEG_QUALITY, 80])
        print("saved", left.shape)
        break
    else:
        print("no frame")
