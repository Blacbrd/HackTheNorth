# Running the Hampy demo

Three processes, started in this order. Two on the laptop, one on the robot.

The robot is `bracketbot@bracketbot-0186.local`, currently `172.20.10.3`.
The laptop is `172.20.10.2`. Both are on the same hotspot; the phone must join
it too.

---

## 1. Robot — the camera server

This is the **only** thing you start by hand on the robot.

```bash
ssh bracketbot@bracketbot-0186.local
export PATH="$HOME/.local/bin:$PATH"
cd ~/bbapps/hampy_demo
nohup uv run camera_web.py --port 8082 --fps 6 > ~/camera_web.log 2>&1 &
```

`nohup ... &` keeps it alive when the SSH session drops. Without the
`export PATH` line you get `nohup: failed to run command 'uv'`.

Check it:

```bash
ss -tln | grep 8082        # expect a LISTEN line
```

**You do not start the pick-up script.** The backend launches that itself over
SSH, once per request. If you run it manually as well, the two fight over
`drive.ctrl` and both fail.

---

## 2. Laptop — the backend

```bash
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --reload
```

`--host 0.0.0.0` is required — on `127.0.0.1` the phone cannot reach it.

Check it, from the laptop:

```bash
curl -s http://127.0.0.1:8000/api/robot/camera/status
# {"available":true,"url":"http://172.20.10.3:8082/snapshot/camera.head.jpeg.jpg"}
```

`"available":false` means step 1 is not running, or the robot's IP moved.

---

## 3. Laptop — the app

```bash
cd frontend
npx expo start
```

Scan the QR code with the phone. The app works out the API address from
whichever host served the bundle, so if Expo and the backend are on the same
laptop there is nothing to configure. If it cannot reach the API, set
`EXPO_PUBLIC_API_URL=http://172.20.10.2:8000` in `frontend/.env`.

---

## How a run goes

1. **Shelves screen.** Inventory lives in `backend/storage.json`. Add or remove
   items here so the thing you are about to ask for is actually in stock.
2. **Ask Hampy.** Hold the mic and speak, or type. Gemini transcribes and picks
   an item that is genuinely on a shelf — it is checked against the inventory,
   not trusted.
3. The live camera is visible on this screen before you even submit. That is
   the robot's head camera, cropped to one eye by the backend.
4. **Submit.** The backend asks Gemini, validates the pick, creates the job,
   then opens an SSH connection and starts the workflow script on the robot.
5. **Progress screen.** Three steps, each one moving only when the robot says
   it has got there:

   | Step | What the robot is doing |
   | --- | --- |
   | Initial pick up | Gripping the item off the shelf |
   | Driving to shelf | Carrying it to the drop-off table |
   | Ready to collect | Grippers open, item released |

6. The robot plays its completion audio and stops where it is. It does not
   drive back to its start position — that is deliberate, for the demo.
7. **"Return back to shelves"** clears the job and returns to the inventory.

If something goes wrong the run stops on the step it failed at, in red, with
the reason. It does not pretend to finish.

---

## Two-item mode

Off by default. One switch, in `backend/.env`:

```dotenv
ROBOT_TWO_ITEM_MODE=true
ROBOT_COMMAND="uv run transfer_two.py --execute --yes --no-retreat"
```

Gemini then picks two items and the progress screen shows four steps instead of
three: Request received, Dropping off first item, Dropping off second item,
Ready to collect. Restart the backend after changing it. Set it back to `false`
to return to the single-item demo — nothing else changes either side.

Leave it `false` unless `transfer_two.py` actually exists on the robot.

---

## Before you demo

```bash
# robot camera serving
ssh bracketbot@bracketbot-0186.local 'ss -tln | grep 8082'

# the workflow script the backend will launch actually exists
ssh bracketbot@bracketbot-0186.local 'ls ~/bbapps/hampy_demo/transfer_both.py'

# nothing else is holding the drive controller
ssh bracketbot@bracketbot-0186.local \
  'ps aux | grep -E "quest_teleop|station_nav" | grep -v grep'

# the backend can see the camera
curl -s http://127.0.0.1:8000/api/robot/camera/status
```

Then run one full job end to end, with someone next to the emergency stop,
before you run it in front of anyone.

---

## When it breaks

**Camera says offline.** Step 1 is not running, or the robot's IP changed.
Check `hostname -I` on the robot and update `ROBOT_HOST` and
`ROBOT_CAMERA_URL` in `backend/.env`.

**Camera is frozen — "SIGNAL STALLED".** The last frame is still on screen but
nothing new arrived. Usually the hotspot. The robot may well still be working.

**"The robot faulted" immediately.** The workflow script died on startup. Look
at `backend/robot-run.log` — the last few lines are the robot's own stdout.
Most often `transfer_both.py` does not exist yet, or `uv` was not on the PATH.

**"The robot is stuck".** Navigation could not take control:

```
ERROR: Navigation could not take control: drive.ctrl is still owned by another app.
```

Something else is driving. Kill Quest teleop, Manual Drive, or a leftover
`station_nav.py`. `camera_web.py` is **not** the culprit — it only reads.

**`AUTO-UNDOCK REFUSED: heading differs by ...`.** The robot thinks it is parked
at a table but facing the wrong way. Turn it to face away from the table before
starting, or re-save the station with
`uv run calibrate_station.py table_1`.

**Everything looks right but nothing moves.** Check `ROBOT_ENABLED=true` in
`backend/.env`. With it `false` the backend only prints the command, and the
app marks the run as a rehearsal.
