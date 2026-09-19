# Picture to Path mobile client

An Expo TypeScript app for capturing or selecting an image, posting it to FastAPI, and presenting a simplified black-and-white drawing.

The app targets Expo SDK 57, the current stable SDK used by this project.

## Run

1. Copy `.env.example` to `.env` and set `EXPO_PUBLIC_API_URL` to a network address reachable from the phone or emulator.
2. Run `npm install`.
3. Run `npm start`.

For a browser build, run `npm run web`. Camera access still depends on browser and device support,
but choosing an existing image works without camera permission.

The app submits `multipart/form-data` to `POST /api/simplify` with the file field named `image`. The endpoint returns PNG bytes directly. The app writes them over the stable cached file `current-drawing.png` before rendering the result.

On web, the response is displayed through a temporary object URL because Expo FileSystem is a
native API.
