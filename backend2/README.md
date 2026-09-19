# Robot Sketch backend

FastAPI accepts a photo, asks Gemini for a simplified black-and-white subject drawing, stores the
latest input and result under fixed names, and returns the PNG to the caller.

## Setup

```powershell
cd backend2
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` in `.env`, then run:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs` for the interactive API documentation.

The default model is `gemini-3.1-flash-image`, Google's image-generation variant intended for
image editing. Regular `gemini-3.5-flash` and `gemini-3.6-flash` models do not return generated
images for this workflow.

`ALLOWED_ORIGINS` is a comma-separated list. Add the URL of any Expo web development server that
needs to call the API. Native iOS and Android requests are not governed by browser CORS.

## Endpoints

- `POST /api/simplify`: multipart form field `image`; returns an `image/png` response.
- `GET /api/result`: returns the most recently generated image.
- `GET /health`: lightweight health check.

Every successful request overwrites `generated/current-input.png` and
`generated/current-drawing.png`. The API serializes generation in a single process so those two
files stay paired.

This storage model and the unauthenticated latest-result endpoint are intended for a local demo.
Add authentication and per-user storage before exposing the service publicly.

## App connection

Set `EXPO_PUBLIC_API_URL` in the Expo app to a URL the device can reach. A physical phone cannot
use the computer's `localhost`; use the computer's LAN address, such as
`http://192.168.1.25:8000`.

## Checks

```powershell
ruff check .
pytest
```
