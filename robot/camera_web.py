# /// script
# requires-python = ">=3.10,<3.11"
# dependencies = ["bbos"]
# [tool.uv.sources]
# bbos = { path = "/home/bracketbot/bbos", editable = true }
# ///
"""Small browser dashboard for every live BracketBot JPEG camera topic."""

from __future__ import annotations

import argparse
import html
import json
import re
import signal
import socket
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

from bbos import Reader


KNOWN_TOPICS = (
    "camera.head.jpeg",
    "camera.left.jpeg",
    "camera.right.jpeg",
    "camera.wrist_left.jpeg",
    "camera.wrist_right.jpeg",
    "camera.left_wrist.jpeg",
    "camera.right_wrist.jpeg",
)


def discover_camera_topics() -> list[str]:
    shared = Path("/dev/shm")
    discovered = [path.name for path in shared.iterdir() if path.name.endswith(".jpeg")]
    ordered = [topic for topic in KNOWN_TOPICS if topic in discovered]
    ordered.extend(sorted(topic for topic in discovered if topic not in ordered))
    return ordered


def safe_camera_name(topic: str) -> str:
    value = topic.removeprefix("camera.").removesuffix(".jpeg")
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_") or "camera"


class CameraFeed:
    def __init__(self, topic: str):
        self.topic = topic
        self.frame = b""
        self.sequence = 0
        self.updated_at = 0.0
        self.error: str | None = None
        self.condition = threading.Condition()
        self.thread = threading.Thread(target=self._run, daemon=True, name=f"feed-{topic}")

    def start(self) -> None:
        self.thread.start()

    def _run(self) -> None:
        try:
            with Reader(self.topic, keeptime=False, sync=True) as reader:
                while True:
                    if not reader.ready():
                        time.sleep(0.003)
                        continue
                    size = int(reader.data["jpeg_len"])
                    if size <= 0:
                        continue
                    frame = bytes(reader.data["jpeg"][:size])
                    with self.condition:
                        self.frame = frame
                        self.sequence += 1
                        self.updated_at = time.time()
                        self.error = None
                        self.condition.notify_all()
        except Exception as exc:
            with self.condition:
                self.error = str(exc)
                self.condition.notify_all()

    def wait_after(self, sequence: int, timeout: float = 5.0) -> tuple[int, bytes]:
        with self.condition:
            self.condition.wait_for(
                lambda: self.sequence > sequence or self.error is not None,
                timeout=timeout,
            )
            return self.sequence, self.frame


def dashboard_html(topics: list[str], fps: float) -> bytes:
    cards = []
    for topic in topics:
        label = safe_camera_name(topic).replace("_", " ").title()
        escaped_topic = html.escape(topic)
        url_topic = quote(topic, safe="")
        cards.append(
            f"""
            <article class="camera" data-topic="{escaped_topic}">
              <header>
                <div><h2>{html.escape(label)}</h2><code>{escaped_topic}</code></div>
                <span class="status waiting">waiting</span>
              </header>
              <div class="viewport">
                <img data-snapshot="/snapshot/{url_topic}.jpg" alt="Live {html.escape(label)} camera">
                <button class="fullscreen" type="button">Full screen</button>
              </div>
            </article>
            """
        )
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>BracketBot Cameras</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; min-height: 100vh; background: #090d12; color: #eef4fb; }}
    main {{ width: min(1500px, 96vw); margin: 0 auto; padding: 28px 0 44px; }}
    .top {{ display:flex; justify-content:space-between; align-items:end; gap:20px; margin-bottom:20px; }}
    h1 {{ margin:0; font-size:clamp(1.6rem,3vw,2.5rem); letter-spacing:-.04em; }}
    .top p {{ margin:7px 0 0; color:#8da0b6; }}
    .live {{ display:flex; align-items:center; gap:8px; color:#9fb0c1; white-space:nowrap; }}
    .dot {{ width:9px; height:9px; border-radius:50%; background:#39db87; box-shadow:0 0 14px #39db87; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(min(430px,100%),1fr)); gap:18px; }}
    .camera {{ overflow:hidden; border:1px solid #26313e; border-radius:18px; background:#111821; box-shadow:0 16px 40px #0006; }}
    header {{ display:flex; align-items:center; justify-content:space-between; gap:12px; padding:15px 17px; }}
    h2 {{ margin:0 0 4px; font-size:1rem; text-transform:capitalize; }}
    code {{ color:#8294a8; font-size:.75rem; }}
    .status {{ border-radius:999px; padding:5px 9px; font-size:.72rem; font-weight:700; text-transform:uppercase; letter-spacing:.06em; }}
    .status.waiting {{ background:#463914; color:#ffdc68; }}
    .status.live {{ background:#123b2a; color:#72efa9; }}
    .status.error {{ background:#4b1f25; color:#ff8996; }}
    .viewport {{ position:relative; min-height:260px; background:#050709; display:grid; place-items:center; }}
    img {{ display:block; width:100%; max-height:68vh; object-fit:contain; }}
    .fullscreen {{ position:absolute; right:12px; bottom:12px; border:1px solid #ffffff33; border-radius:10px; padding:8px 11px; color:white; background:#080b10cc; cursor:pointer; backdrop-filter:blur(8px); }}
    .fullscreen:hover {{ background:#263443; }}
    footer {{ margin-top:18px; color:#718398; font-size:.82rem; }}
    :fullscreen img {{ width:100vw; height:100vh; max-height:none; background:#000; object-fit:contain; }}
    :fullscreen .fullscreen {{ position:fixed; }}
  </style>
</head>
<body>
  <main>
    <section class="top">
      <div><h1>BracketBot camera monitor</h1><p>Live head and wrist camera feeds</p></div>
      <div class="live"><span class="dot"></span><span>robot connected</span></div>
    </section>
    <section class="grid">{''.join(cards)}</section>
    <footer>Keep this page on the robot's trusted local network. Press Ctrl-C in the server terminal to stop.</footer>
  </main>
  <script>
    const FRAME_INTERVAL = {1000.0 / fps:.3f};
    const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
    for (const card of document.querySelectorAll('.camera')) {{
      card.querySelector('.fullscreen').addEventListener('click', () => {{
        if (document.fullscreenElement) document.exitFullscreen();
        else card.querySelector('.viewport').requestFullscreen();
      }});
      const img = card.querySelector('img');
      let previousUrl = null;
      (async function newestFrameLoop() {{
        while (true) {{
          const began = performance.now();
          try {{
            const response = await fetch(img.dataset.snapshot, {{cache:'no-store'}});
            if (!response.ok) throw new Error('camera unavailable');
            const blob = await response.blob();
            const nextUrl = URL.createObjectURL(blob);
            await new Promise(resolve => {{
              img.onload = () => {{
                if (previousUrl) URL.revokeObjectURL(previousUrl);
                previousUrl = nextUrl;
                resolve();
              }};
              img.onerror = resolve;
              img.src = nextUrl;
            }});
          }} catch (_) {{
            await sleep(200);
          }}
          const remaining = FRAME_INTERVAL - (performance.now() - began);
          if (remaining > 0) await sleep(remaining);
        }}
      }})();
    }}
    async function refresh() {{
      try {{
        const result = await fetch('/api/status', {{cache:'no-store'}});
        const data = await result.json();
        for (const card of document.querySelectorAll('.camera')) {{
          const feed = data.cameras[card.dataset.topic];
          const badge = card.querySelector('.status');
          badge.className = 'status ' + (feed.error ? 'error' : feed.age_seconds < 2 ? 'live' : 'waiting');
          badge.textContent = feed.error ? 'error' : feed.age_seconds < 2 ? 'live' : 'waiting';
          badge.title = feed.error || '';
        }}
      }} catch (_) {{}}
    }}
    refresh(); setInterval(refresh, 1500);
  </script>
</body>
</html>"""
    return page.encode("utf-8")


class CameraHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler, feeds: dict[str, CameraFeed], fps: float):
        super().__init__(address, handler)
        self.feeds = feeds
        self.page = dashboard_html(list(feeds), fps)

    def get_request(self):
        request, address = super().get_request()
        request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return request, address


class Handler(BaseHTTPRequestHandler):
    server: CameraHTTPServer
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(self.server.page)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(self.server.page)
            return
        if path == "/api/status":
            now = time.time()
            payload = {
                "cameras": {
                    topic: {
                        "sequence": feed.sequence,
                        "age_seconds": round(max(now - feed.updated_at, 0.0), 3)
                        if feed.updated_at else 9999.0,
                        "error": feed.error,
                    }
                    for topic, feed in self.server.feeds.items()
                }
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if path.startswith("/snapshot/") and path.endswith(".jpg"):
            topic = unquote(path[len("/snapshot/"):-len(".jpg")])
            feed = self.server.feeds.get(topic)
            if feed is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            with feed.condition:
                frame = feed.frame
            if not frame:
                self.send_error(HTTPStatus.SERVICE_UNAVAILABLE)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(frame)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.end_headers()
            self.wfile.write(frame)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format_: str, *args) -> None:
        if args and str(args[0]).startswith("GET /api/status"):
            return
        super().log_message(format_, *args)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8082)
    parser.add_argument("--fps", type=float, default=6.0,
                        help="display refresh rate per camera; lower reduces latency")
    parser.add_argument("--topics", help="optional comma-separated camera topics")
    args = parser.parse_args()
    topics = (
        [value.strip() for value in args.topics.split(",") if value.strip()]
        if args.topics else discover_camera_topics()
    )
    if not topics:
        raise SystemExit("No camera JPEG topics found")
    if not 1.0 <= args.fps <= 20.0:
        raise SystemExit("--fps must be between 1 and 20")

    feeds = {topic: CameraFeed(topic) for topic in topics}
    for feed in feeds.values():
        feed.start()
    server = CameraHTTPServer((args.host, args.port), Handler, feeds, args.fps)

    def stop(*_args) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    print(f"Streaming {len(feeds)} cameras:")
    for topic in feeds:
        print(f"  {topic}")
    print(f"Low-latency mode: newest frame only, {args.fps:g} FPS per camera")
    print(f"Open http://127.0.0.1:{args.port} through the SSH tunnel", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
