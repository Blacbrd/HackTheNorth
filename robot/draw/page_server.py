# /// script
# requires-python = ">=3.10,<3.11"
# dependencies = [
#   "bbos",
#   "numpy<2",
#   "opencv-python-headless",
#   "fastapi",
#   "uvicorn",
# ]
# [tool.uv.sources]
# bbos = { path = "/home/bracketbot/bbos", editable = true }
# ///
"""Live page detection in a browser, for checking the detector by eye.

Opens the head camera as a Reader only, so it runs safely next to teleop or
anything else driving the arms. Nothing here commands the robot.

    uv run page_server.py
    # then open http://bracketbot-0186.local:8005/

The page shows the annotated camera feed, the live numbers behind the
detection, sliders to retune without restarting, and click-to-measure: click
anywhere on the paper and it tells you that point in paper mm.
"""

from __future__ import annotations

import argparse
import json
import socket
import threading
import time
from queue import Empty, Queue

import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response, StreamingResponse

from detect_page import (PAPER_SIZES_MM, MIN_AREA_FRAC, STABLE_FRAMES,
                         STABLE_TOL_PX, annotate, build_result, find_page,
                         head_frames, stable_quad, to_paper_mm)

PORT = 8005
STREAM_FPS = 15
JPEG_QUALITY = 75


class Detector:
    """Runs detection on the newest camera frame and keeps the latest results.

    Detection defaults to full resolution: at 1280x960 it costs ~77 ms, and a
    desk-distance page measured only 1.4% of the frame, small enough that
    halving the image lost it entirely. Corners are rescaled to full-resolution
    pixels when `scale` is below 1.0.
    """

    def __init__(self, paper_mm, min_area, stable_frames, tolerance, scale):
        self.lock = threading.Lock()
        self.paper_mm = tuple(paper_mm)
        self.min_area = float(min_area)
        self.stable_frames = int(stable_frames)
        self.tolerance = float(tolerance)
        self.scale = float(scale)
        self.frames = Queue(maxsize=2)
        self.live: dict | None = None      # newest frame's detection
        self.locked: dict | None = None    # last detection that held still
        self.history: list = []
        self.misses = 0
        self.fps = 0.0
        self.image_size = (0, 0)

    def settings(self) -> dict:
        with self.lock:
            return {"paper_mm": list(self.paper_mm), "min_area": self.min_area,
                    "stable_frames": self.stable_frames,
                    "tolerance": self.tolerance, "scale": self.scale}

    def update(self, **changes) -> dict:
        with self.lock:
            for key, value in changes.items():
                if value is None:
                    continue
                if key == "paper_mm":
                    self.paper_mm = (float(value[0]), float(value[1]))
                elif key in ("min_area", "tolerance"):
                    setattr(self, key, float(value))
                elif key == "stable_frames":
                    self.stable_frames = max(1, int(value))
            self.history.clear()
            self.locked = None
        return self.settings()

    def _detect(self, image: np.ndarray) -> dict | None:
        settings = self.settings()
        scale = settings["scale"]
        small = (cv2.resize(image, None, fx=scale, fy=scale,
                            interpolation=cv2.INTER_AREA)
                 if scale < 0.999 else image)
        candidate = find_page(small, settings["paper_mm"], False,
                              settings["min_area"])
        if candidate is None:
            return None
        candidate["quad"] = candidate["quad"] / scale
        return candidate

    def run(self) -> None:
        """Capture, detect, annotate. Restarts if the camera stream stops."""
        last = time.monotonic()
        while True:
            for image in head_frames(3600.0):
                now = time.monotonic()
                self.fps = 0.9 * self.fps + 0.1 / max(now - last, 1e-3)
                last = now
                self.image_size = (image.shape[1], image.shape[0])

                candidate = self._detect(image)
                settings = self.settings()
                if candidate is None:
                    self.misses += 1
                    if self.misses >= 3:
                        with self.lock:
                            self.history.clear()
                        self.live = None
                    canvas = image.copy()
                    cv2.putText(canvas, "NO PAGE", (12, 32),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                else:
                    self.misses = 0
                    live = build_result(candidate, candidate["quad"],
                                        image.shape, 1)
                    with self.lock:
                        self.history.append(candidate["quad"])
                        del self.history[:-settings["stable_frames"]]
                        settled = stable_quad(list(self.history),
                                              settings["stable_frames"],
                                              settings["tolerance"])
                        held = len(self.history)
                    live["quality"]["stable_frames"] = held
                    live["stable"] = settled is not None
                    if settled is not None:
                        self.locked = build_result(candidate, settled,
                                                   image.shape, held)
                    self.live = live
                    canvas = annotate(image, live)
                    colour = (0, 255, 0) if live["stable"] else (0, 200, 255)
                    cv2.putText(canvas,
                                "STABLE" if live["stable"]
                                else f"settling {held}/{settings['stable_frames']}",
                                (12, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                                colour, 2)

                ok, buffer = cv2.imencode(
                    ".jpg", canvas, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
                if ok:
                    try:
                        self.frames.put_nowait(buffer.tobytes())
                    except Exception:
                        try:
                            self.frames.get_nowait()
                            self.frames.put_nowait(buffer.tobytes())
                        except Exception:
                            pass
            time.sleep(0.5)


INDEX_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Page detection</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
 :root{color-scheme:dark}
 body{margin:0;background:#111;color:#eee;font:14px/1.5 system-ui,sans-serif}
 .wrap{display:flex;flex-wrap:wrap;gap:16px;padding:16px}
 .feed{flex:1 1 640px;min-width:320px}
 img{width:100%;border-radius:8px;display:block;cursor:crosshair}
 .side{flex:0 1 320px;min-width:260px}
 .card{background:#1b1b1b;border:1px solid #2c2c2c;border-radius:8px;
       padding:12px;margin-bottom:12px}
 h2{margin:0 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:.08em;
    color:#9aa}
 table{width:100%;border-collapse:collapse}
 td{padding:2px 0;vertical-align:top}
 td:last-child{text-align:right;font-variant-numeric:tabular-nums}
 .ok{color:#4ade80}.bad{color:#f87171}.warn{color:#fbbf24}
 label{display:block;margin:8px 0 2px;color:#9aa;font-size:12px}
 input[type=range]{width:100%}
 #probe{font-size:18px;font-variant-numeric:tabular-nums}
 code{background:#222;padding:1px 5px;border-radius:4px}
</style></head><body>
<div class="wrap">
 <div class="feed">
  <img id="v" src="/stream" alt="camera">
  <p style="color:#9aa">Click anywhere on the paper to read that point in
     paper millimetres.</p>
  <div class="card"><h2>Clicked point</h2><div id="probe">—</div></div>
 </div>
 <div class="side">
  <div class="card"><h2>Detection</h2><table id="stats"></table></div>
  <div class="card"><h2>Tuning</h2>
   <label>Min area <span id="lmin"></span></label>
   <input type="range" id="min" min="1" max="200" step="1">
   <label>Stable frames <span id="lsf"></span></label>
   <input type="range" id="sf" min="1" max="20" step="1">
   <label>Tolerance px <span id="ltol"></span></label>
   <input type="range" id="tol" min="1" max="40" step="1">
  </div>
  <div class="card"><h2>Paper</h2><div id="paper"></div>
   <p style="color:#9aa">Set the measured size with
      <code>--paper-mm SHORT LONG</code> at startup.</p></div>
 </div>
</div>
<script>
let size = [1280, 960];
function row(k, v, cls){return `<tr><td>${k}</td><td class="${cls||''}">${v}</td></tr>`}
async function tick(){
 const r = await fetch('/page').then(r=>r.json()).catch(()=>null);
 const t = document.getElementById('stats');
 if(!r || !r.found){ t.innerHTML = row('page','not found','bad'); return; }
 size = r.image_size_px;
 const q = r.quality, ang = q.corner_angles_deg.map(a=>a.toFixed(0)).join(' ');
 t.innerHTML = row('page','found','ok')
  + row('stable', r.stable ? 'yes' : `${q.stable_frames} frames`,
        r.stable ? 'ok' : 'warn')
  + row('size', r.page_mm[0].toFixed(0)+' x '+r.page_mm[1].toFixed(0)+' mm')
  + row('orientation', r.orientation)
  + row('area', (q.area_fraction*100).toFixed(1)+'%')
  + row('aspect err', q.aspect_error.toFixed(3))
  + row('corners', ang+'&deg;');
}
async function loadCfg(){
 const c = await fetch('/config').then(r=>r.json());
 document.getElementById('min').value = Math.round(c.min_area*1000);
 document.getElementById('sf').value = c.stable_frames;
 document.getElementById('tol').value = c.tolerance;
 document.getElementById('paper').textContent =
   c.paper_mm[0]+' x '+c.paper_mm[1]+' mm';
 labels();
}
function labels(){
 document.getElementById('lmin').textContent =
   (document.getElementById('min').value/10)+'%';
 document.getElementById('lsf').textContent = document.getElementById('sf').value;
 document.getElementById('ltol').textContent = document.getElementById('tol').value;
}
async function push(){
 labels();
 const p = new URLSearchParams({
  min_area: document.getElementById('min').value/1000,
  stable_frames: document.getElementById('sf').value,
  tolerance: document.getElementById('tol').value});
 await fetch('/config?'+p, {method:'POST'});
}
for(const id of ['min','sf','tol'])
 document.getElementById(id).addEventListener('change', push);
document.getElementById('v').addEventListener('click', async e=>{
 const b = e.target.getBoundingClientRect();
 const x = (e.clientX-b.left)*size[0]/b.width;
 const y = (e.clientY-b.top)*size[1]/b.height;
 const r = await fetch(`/to_mm?x=${x}&y=${y}`).then(r=>r.json());
 document.getElementById('probe').innerHTML = r.on_page
  ? `<span class="ok">${r.mm[0].toFixed(1)}, ${r.mm[1].toFixed(1)} mm</span>`
  : `<span class="warn">${r.mm ? r.mm[0].toFixed(1)+', '+r.mm[1].toFixed(1)
       +' mm (off the sheet)' : 'no page'}</span>`;
});
loadCfg(); setInterval(tick, 400);
</script></body></html>"""


def build_app(detector: Detector) -> FastAPI:
    app = FastAPI()

    @app.get("/")
    async def index():
        return Response(content=INDEX_HTML, media_type="text/html")

    @app.get("/stream")
    async def stream():
        import asyncio

        async def frames():
            while True:
                try:
                    frame = detector.frames.get_nowait()
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                           + frame + b"\r\n")
                except Empty:
                    pass
                await asyncio.sleep(1 / STREAM_FPS)

        return StreamingResponse(
            frames(),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get("/page")
    async def page():
        """The newest detection, whether or not it has settled."""
        live = detector.live
        if live is None:
            return JSONResponse({"found": False, "fps": round(detector.fps, 1)})
        return JSONResponse({**live, "fps": round(detector.fps, 1)})

    @app.get("/locked")
    async def locked():
        """The last detection that held still: what a drawing job should use."""
        if detector.locked is None:
            return JSONResponse({"found": False,
                                 "reason": "no stable page yet"}, status_code=404)
        return JSONResponse(detector.locked)

    @app.get("/to_mm")
    async def to_mm(x: float, y: float):
        live = detector.live
        if live is None:
            return JSONResponse({"on_page": False, "mm": None})
        homography = np.array(live["homography_px_to_mm"], dtype=np.float32)
        millimetres = to_paper_mm(homography, (x, y))
        width, height = live["page_mm"]
        on_page = (-1.0 <= millimetres[0] <= width + 1.0
                   and -1.0 <= millimetres[1] <= height + 1.0)
        return JSONResponse({"on_page": bool(on_page),
                             "mm": [round(millimetres[0], 1),
                                    round(millimetres[1], 1)]})

    @app.get("/config")
    async def get_config():
        return JSONResponse(detector.settings())

    @app.post("/config")
    async def set_config(min_area: float = None, stable_frames: int = None,
                         tolerance: float = None):
        return JSONResponse(detector.update(min_area=min_area,
                                            stable_frames=stable_frames,
                                            tolerance=tolerance))

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", choices=sorted(PAPER_SIZES_MM),
                        default="letter")
    parser.add_argument("--paper-mm", type=float, nargs=2,
                        metavar=("SHORT", "LONG"),
                        help="measured paper size in mm, overrides --paper")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--min-area", type=float, default=MIN_AREA_FRAC)
    parser.add_argument("--stable-frames", type=int, default=STABLE_FRAMES)
    parser.add_argument("--tolerance", type=float, default=STABLE_TOL_PX)
    parser.add_argument("--scale", type=float, default=1.0,
                        help="detect on a downscaled frame; below 1.0 a small "
                             "page breaks up and the detector latches onto "
                             "furniture instead, so raise it only if the page "
                             "fills much of the view")
    args = parser.parse_args()

    paper_mm = tuple(args.paper_mm) if args.paper_mm else PAPER_SIZES_MM[args.paper]
    detector = Detector(paper_mm, args.min_area, args.stable_frames,
                        args.tolerance, args.scale)
    threading.Thread(target=detector.run, daemon=True).start()

    host = socket.gethostname()
    print(f"[+] page detection test rig: http://{host}.local:{args.port}/",
          flush=True)
    print(f"    paper {paper_mm[0]} x {paper_mm[1]} mm", flush=True)
    uvicorn.run(build_app(detector), host="0.0.0.0", port=args.port,
                log_level="error", access_log=False,
                timeout_graceful_shutdown=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
