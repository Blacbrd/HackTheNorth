# Shelf Robot API

FastAPI backend for managing shelf inventory and selecting a robot pickup target with Gemini.

## Setup

```powershell
cd backend
Copy-Item .env.example .env
# Add your Gemini API key to .env
python -m uv sync
python -m uv run uvicorn app.main:app --host 0.0.0.0 --reload
```

The API is available locally at `http://127.0.0.1:8000`; `--host 0.0.0.0` also makes it reachable from an Expo Go phone on the same network. Interactive docs are at `/docs`.

The default `GEMINI_MODEL` is `gemini-3.5-flash-lite`, Google's stable fast, free-tier-eligible model. You can override it in `.env` without changing application code.

## API

- `GET /api/shelves` and `GET /api/shelves/{shelf_number}` read inventory.
- `POST /api/shelves/{shelf_number}/items` with `{"item":"banana"}` adds an item. Repeated items are allowed and represent separate inventory quantities.
- `DELETE /api/shelves/{shelf_number}/items/{item}` removes one matching item occurrence per request.
- `POST /api/recommendations/app` asks Gemini and sends the validated selection to the dummy robot client.
- `POST /api/recommendations/robot` is the equivalent robot-originated route and uses the same service.
- `POST /api/transcriptions` accepts multipart form data with an `audio` file and returns `{"text":"..."}`. It accepts AAC, M4A/MP4, MP3, OGG, WAV, WebM, and 3GP audio up to `MAX_AUDIO_UPLOAD_BYTES` (10 MiB by default). MIME parameters such as `audio/webm; codecs=opus` are supported.

Both recommendation endpoints accept `{"user_input":"I need a vegan vegetable"}` and return `{"items":[{"shelf_number":1,"item":"peas"}],"source":"app","shelf_number":1,"item":"peas"}`. `shelf_number`/`item` mirror `items[0]` for older clients. With `ROBOT_TWO_ITEM_MODE=true`, `items` has two entries and the robot job runs the four-stage two-item workflow instead of the three-stage single-item one. Gemini is instructed to return structured JSON, then every returned item is checked against `storage.json` before the robot integration is invoked.

For an Expo `expo-audio` recording, upload the recorded file as multipart form data under the `audio` field with its actual audio MIME type. Transcription uses the same configured `GEMINI_MODEL` and returns only plain transcript text. Unsupported media types return `415`, empty or oversized uploads return `422` or `413`, an unset Gemini key returns `503`, and a Gemini failure returns `502`.

`storage.json` is valid JSON (shelf keys are strings on disk) and changes are written through an atomic replacement.

## Real robot mode

By default the API is safe: it records the app job and prints the robot command, but it does not move hardware. To drive the BracketBot, run the backend where it can execute the workflow script in `ROBOT_APP_DIR`, then set:

```dotenv
ROBOT_ENABLED=true
ROBOT_TRANSPORT=local
ROBOT_APP_DIR=/home/bracketbot/bbapps/hampy_demo
ROBOT_COMMAND="uv run transfer_both.py --execute --yes"
```

With that config, a request runs `ROBOT_COMMAND` in the background (`transfer_both.py` wraps `drop_both.py`'s transfer mode: pick up the item, drive to `table_2` holding it, drop it, back away, then play completion audio).

Progress is driven by that process's own stdout, not a timer. `RobotClient` reads the command's output line by line, writes every line to `backend/robot-run.log`, and maps it to a job stage: a `HAMPY_STAGE:<name>` (or `HAMPY_FAIL:<name>`) marker line is used if present, and a fallback prose match (`"PICKUP COMPLETE"`, `"TRANSFER COMPLETE"`, `"NAVIGATION FAILED (exit code N)"`, etc.) is used for a robot script that predates the markers. A stage never moves backwards. The robot side can also push its stage directly with `POST /api/robot/job/stage/{stage}` instead of relying on stdout parsing. If the script exits non-zero without either path having already recorded a failure or completion, the job is marked `fault`.

Set `ROBOT_TWO_ITEM_MODE=true` to have Gemini pick two items per request and run the four-stage job (`queued`, `dropping_first`, `dropping_second`, `arrived`) instead of the default three-stage one (`picking`, `driving`, `arrived`).

The phone's camera view is served from this API too, not the robot directly: `GET /api/robot/camera.jpg` proxies the robot's snapshot server (`ROBOT_CAMERA_URL`/`ROBOT_CAMERA_TOPIC`), returning `503` if the camera is unreachable, and `GET /api/robot/camera/status` reports `{"available": bool, "url": str}` without raising.

If the backend runs on your Mac instead of the robot, use `ROBOT_TRANSPORT=ssh`; SSH key auth must already work because a web request cannot type the robot password interactively.

The JSON repository serializes writes within this API process. Run a single Uvicorn worker while using file storage; move the repository to a database or add a cross-process lock before running multiple workers or multiple backend instances.

## Tests

```powershell
python -m uv run pytest
```

Tests use a fake Gemini client and require no API key or network connection.
