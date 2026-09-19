# Hampy frontend

Expo Router + TypeScript mobile app for managing food-bank shelves and asking the robot to choose an item. It runs in stock Expo Go on iOS and Android, plus Expo web.

Use Node.js 22.13 or newer for Expo SDK 57.

## Run it

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npx expo start
```

Run the FastAPI backend separately from `backend/`. Scan the QR code in the Expo terminal using Expo Go (iOS Camera / Expo Go on Android). Devices and the API host must be on the same network.

`localhost` works only in the browser on the same computer. For a physical phone, set `EXPO_PUBLIC_API_URL` to your computer’s LAN address, for example `http://192.168.1.42:8000`. If the LAN is restricted, run `npx expo start --tunnel` for the Expo bundle; the API still needs an address your phone can reach.

## Commands

```powershell
npm run typecheck
npm run lint
npm run web
```

Voice input records audio using Expo Audio and sends it to `POST /api/transcriptions`; the backend returns text that populates the request box. It is not on-device speech recognition. The black robot-camera panel is an intentionally swappable placeholder until the robot camera adapter is available.

Set `EXPO_PUBLIC_ROBOT_CAMERA_URL` to an optional still-image or browser-compatible camera endpoint to show it in the result card; leave it blank to retain the accessible black placeholder.
