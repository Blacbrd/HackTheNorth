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

Both recommendation endpoints accept `{"user_input":"I need a vegan vegetable"}` and return `{"shelf_number":1,"item":"peas","source":"app"}`. Gemini is instructed to return structured JSON, then its output is checked against `storage.json` before the robot integration is invoked.

For an Expo `expo-audio` recording, upload the recorded file as multipart form data under the `audio` field with its actual audio MIME type. Transcription uses the same configured `GEMINI_MODEL` and returns only plain transcript text. Unsupported media types return `415`, empty or oversized uploads return `422` or `413`, an unset Gemini key returns `503`, and a Gemini failure returns `502`.

`storage.json` is valid JSON (shelf keys are strings on disk) and changes are written through an atomic replacement.

## Real robot mode

By default the API is safe: it records the app job and prints the robot command, but it does not move hardware. To drive the BracketBot, run the backend where it can execute `/home/bracketbot/bbapps/hampy_demo/station_nav.py` and `replay_trajectory.py`, then set:

```dotenv
ROBOT_ENABLED=true
ROBOT_TRANSPORT=local
ROBOT_APP_DIR=/home/bracketbot/bbapps/hampy_demo
ROBOT_STATION_BY_SHELF=1:table_1,2:table_2,3:table_3
ROBOT_DROPOFF_STATION=table_2
ROBOT_PICKUP_MOTION_TEMPLATE=motions/{station}_pickup.json
ROBOT_DROP_MOTION=motions/drop.json
```

With that config, a request for an item on shelf 1 runs this robot workflow in the background:

1. Drive to `table_1` with `station_nav.py table_1 --direct --no-marker --execute --yes`.
2. Replay `motions/table_1_pickup.json`.
3. Drive to `table_2`.
4. Replay `motions/drop.json`.

The API writes robot output to `backend/robot-run.log`. The phone progress screen still advances by timer; it does not yet read live success/failure telemetry from the robot process.

If the backend runs on your Mac instead of the robot, use `ROBOT_TRANSPORT=ssh`; SSH key auth must already work because a web request cannot type the robot password interactively.

The JSON repository serializes writes within this API process. Run a single Uvicorn worker while using file storage; move the repository to a database or add a cross-process lock before running multiple workers or multiple backend instances.

## Tests

```powershell
python -m uv run pytest
```

Tests use a fake Gemini client and require no API key or network connection.
