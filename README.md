# Hampy

Hampy is a mobile food-bank assistant connected to a BracketBot. A user asks for food by voice or text, Gemini selects matching inventory, the backend dispatches one robot transfer, and the app shows live camera and movement status.

## Repository layout

- `frontend/` — Expo mobile app
- `backend/` — FastAPI API, Gemini integration, inventory, robot dispatch, and camera proxy
- `robot/` — robot-side transfer, route replay, lean-mode, audio, and live-camera programs

BBOS and its daemons are external robot dependencies and are intentionally not included. The robot programs reference the installed `/home/bracketbot/bbos` package and the installed `~/bbapps/quest_teleop` arm utilities.

## Robot setup

Copy `robot/` to `/home/bracketbot/bbapps/hampy_demo/`. Preserve the recorded route at `routes/table1_to_table2.json`; it is replayed exactly and should only be used from the physical starting pose where it was recorded.

Start the camera service on the robot:

```bash
cd ~/bbapps/hampy_demo
uv run camera_web.py --host 127.0.0.1 --port 8082 --fps 10
```

The backend dispatches this non-interactive workflow:

```bash
uv run transfer_both.py --execute --yes
```

The workflow enables lean mode for pickup, grasps with both arms, switches back to balance mode, replays `routes/table1_to_table2.json`, releases both items, and plays the completion audio. Keep the route and arm paths clear and keep the emergency stop ready whenever it runs.

## Backend

From `backend/`:

```bash
cp .env.example .env
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Set `GEMINI_API_KEY`, set `ROBOT_ENABLED=true`, and use `ROBOT_TRANSPORT=ssh` when the API runs on the laptop. SSH key authentication must work non-interactively for `bracketbot@bracketbot-0186.local`.

Forward the robot camera to the laptop in a separate terminal:

```bash
ssh -N -L 8082:127.0.0.1:8082 bracketbot@bracketbot-0186.local
```

Verify the connections with `GET /health`, `GET /api/robot/camera/status`, and `GET /api/robot/job`.

## Frontend

Set `EXPO_PUBLIC_API_URL` in `frontend/.env` to the laptop's LAN API address, such as `http://172.20.10.5:8000`, then run:

```bash
cd frontend
npm ci
npx expo start --clear
```

The phone and laptop must be on the same network. Pressing **Ask Hampy** sends the request to the backend; all accepted recommendations dispatch the same two-arm table-one-to-table-two robot workflow.

## Checks

```bash
cd backend && uv run pytest
cd ../frontend && npm run typecheck && npm run lint
```
