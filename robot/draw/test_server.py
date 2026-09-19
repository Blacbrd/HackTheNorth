# /// script
# requires-python = ">=3.10,<3.11"
# dependencies = ["bbos","numpy<2","opencv-python-headless","fastapi","uvicorn"]
# [tool.uv.sources]
# bbos = { path = "/home/bracketbot/bbos", editable = true }
# ///
"""Exercise page_server's logic without binding a port."""
import asyncio, json, time
import cv2
import page_server as ps

det = ps.Detector((215.9, 279.4), 0.008, 4, 12.0, 1.0)
app = ps.build_app(det)

def route(path, method="GET"):
    for r in app.routes:
        if getattr(r, "path", "") == path and method in getattr(r, "methods", set()):
            return r.endpoint
    raise RuntimeError(f"no {method} {path}")

img = cv2.imread("/tmp/head.jpg", cv2.IMREAD_COLOR)
assert img is not None, "no /tmp/head.jpg"
det.image_size = (img.shape[1], img.shape[0])

t0 = time.monotonic()
cand = det._detect(img)
print(f"_detect -> {'found' if cand else 'none'} in {(time.monotonic()-t0)*1000:.0f} ms")
assert cand, "detector found nothing on the real frame"

live = ps.build_result(cand, cand["quad"], img.shape, 1)
live["stable"] = True
det.live = det.locked = live
cv2.imwrite("/tmp/server_overlay.png", ps.annotate(img, live))
print("page:", live["page_mm"], live["orientation"], live["corners_px"])

async def go():
    page = json.loads((await route("/page")()).body)
    print("GET /page   -> found=", page["found"], "stable=", page.get("stable"))
    locked = json.loads((await route("/locked")()).body)
    print("GET /locked -> found=", locked["found"])

    to_mm = route("/to_mm")
    w, h = live["page_mm"]
    expect = {"tl": (0, 0), "tr": (w, 0), "br": (w, h), "bl": (0, h)}
    worst = 0.0
    for name, px in live["corners_px"].items():
        got = json.loads((await to_mm(x=float(px[0]), y=float(px[1]))).body)
        want = expect[name]
        err = max(abs(got["mm"][0]-want[0]), abs(got["mm"][1]-want[1]))
        worst = max(worst, err)
        print(f"  click {name.upper():2} {px} -> {got['mm']} mm "
              f"(expect {want}) on_page={got['on_page']}")
    print(f"  worst corner round-trip error: {worst:.2f} mm")
    assert worst < 0.2, "corner round-trip is off"

    tl = live["corners_px"]["tl"]
    off = json.loads((await to_mm(x=float(tl[0])-250, y=float(tl[1])-250)).body)
    print("  click off the sheet ->", off["mm"], "on_page=", off["on_page"])
    assert off["on_page"] is False, "off-sheet click should not read as on-page"

asyncio.run(go())
print("POST /config ->", det.update(min_area=0.02, stable_frames=6, tolerance=8.0))
print("ALL SERVER CHECKS PASSED")
