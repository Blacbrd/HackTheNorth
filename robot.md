# Robot-side setup for the Hampy app

Written for: the agent working inside the SSH session on the BracketBot.

Everything below happens on the robot, in `~/bbapps/hampy_demo`. Nothing in this
file touches the laptop.

---

## The short version

The phone app talks to a FastAPI backend on the laptop. That backend already
SSHes into this robot and runs a script. Two things are missing:

1. **The camera server is not running.** Nothing is listening on port 8082, so
   the app shows "camera offline".
2. **The robot never tells the backend where it has got to.** The app fakes the
   progress steps on a timer. It needs real ones.

There are four jobs. Jobs 1 and 2 are required for the demo. Job 3 is a small
quality fix. Job 4 is only if someone finishes the two-item feature.

---

## How the two sides talk to each other

There is no new network service to build. The laptop already opens an SSH
connection and runs a command here. **Anything this robot prints to stdout goes
straight back to the laptop over that same connection, line by line, as it
happens.** The backend reads those lines live and moves the progress bar.

So "pinging the backend" just means: **print a line.**

The backend looks for lines in this exact shape:

```
HAMPY_STAGE: <stage_name>
```

and, if something goes wrong:

```
HAMPY_FAIL: <failure_name>
```

That is the whole protocol. Print the line, flush it, and the app updates.

> **Why not a WebSocket or an HTTP callback?**
> Because the robot would have to know the laptop's IP address, and that
> address changes every time someone rejoins the hotspot. The SSH pipe is
> already open and already points the right way. If you later want a push
> channel anyway, the backend does expose `POST /api/robot/job/stage/{stage}`
> — but the printed line is the path that works today with no configuration.

### The stage names

**Single-item mode** (what the demo uses now) — print these three, in order:

| Print this                  | What the app shows   | When to print it                          |
| --------------------------- | -------------------- | ----------------------------------------- |
| `HAMPY_STAGE: picking`      | Initial pick up      | As soon as the run starts                 |
| `HAMPY_STAGE: driving`      | Driving to shelf     | Once the item is gripped and nav begins   |
| `HAMPY_STAGE: arrived`      | Ready to collect     | The moment the grippers open and let go   |

**Two-item mode** (only if job 4 gets done) — print these four:

| Print this                       | What the app shows        |
| -------------------------------- | ------------------------- |
| `HAMPY_STAGE: queued`            | Request received          |
| `HAMPY_STAGE: dropping_first`    | Dropping off first item   |
| `HAMPY_STAGE: dropping_second`   | Dropping off second item  |
| `HAMPY_STAGE: arrived`           | Ready to collect          |

### The failure names

| Print this             | What the app shows                |
| ---------------------- | --------------------------------- |
| `HAMPY_FAIL: missing`  | The item was not where we thought |
| `HAMPY_FAIL: blocked`  | Something is in the robot's way   |
| `HAMPY_FAIL: fault`    | The robot stopped mid-run         |

### Rules

- Always pass `flush=True` to `print`, or the line sits in a buffer and the app
  freezes on the previous step.
- Stages only move forwards. The backend ignores a stage that is earlier than
  the one it already has, so a duplicate print is harmless.
- Print the stage line **before** the slow thing it describes, not after.
- `arrived` is the last stage. Print it when the grippers open, not later.

---

## Job 1 — Start the camera server (required)

Nothing is serving camera frames. Start it:

```bash
cd ~/bbapps/hampy_demo
uv run camera_web.py --port 8082 --fps 6
```

Leave it running. It should print something like:

```
Streaming 3 cameras:
  camera.head.jpeg
  ...
Low-latency mode: newest frame only, 6 FPS per camera
```

**This is safe to run at the same time as a pickup.** `camera_web.py` only
*reads* the camera topics. It never touches `drive.ctrl` or the arms, so it
will not fight with navigation.

Make it survive a dropped SSH session, or it dies the moment the terminal
closes. **The `export PATH` line is not optional** — without it you get
`nohup: failed to run command 'uv': No such file or directory`:

```bash
export PATH="$HOME/.local/bin:$PATH"
cd ~/bbapps/hampy_demo
nohup uv run camera_web.py --port 8082 --fps 6 > ~/camera_web.log 2>&1 &
```

This has already been done once and it worked — the server came up and served
frames. If it is still running you do not need to start it again; check with
`ss -tln | grep 8082`.

### Check it works

From the robot itself:

```bash
curl -s -o /dev/null -w '%{http_code} %{size_download}\n' \
  http://127.0.0.1:8082/snapshot/camera.head.jpeg.jpg
```

You want `200` and a size of a few hundred thousand bytes. A `503` means the
camera daemon has no frames yet — wait a few seconds and retry.

Then, **from the laptop**, check it is reachable across the network:

```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  http://172.20.10.3:8082/snapshot/camera.head.jpeg.jpg
```

This has been checked already: the laptop (`172.20.10.2`) can open TCP
connections to the robot on ports other than 22, so **no SSH tunnel should be
needed**. The only reason the camera is dark is that nothing is serving it.

- If that returns `200`, you are done. The laptop backend proxies frames to the
  phone from there.
- If it hangs or refuses, something changed about the network. Open a tunnel
  from the laptop instead and tell the backend to use it:

  ```bash
  # on the laptop, in its own terminal, left running
  ssh -N -L 8082:127.0.0.1:8082 bracketbot@bracketbot-0186.local
  ```

  then set `ROBOT_CAMERA_URL=http://127.0.0.1:8082` in `backend/.env`.

### Which camera topic to use — do not change this

The robot publishes three JPEG topics. They are not what their names suggest:

| Topic               | Size     | What it actually shows                     |
| ------------------- | -------- | ------------------------------------------ |
| `camera.head.jpeg`  | 2560x960 | Forward view — **a stereo pair, side by side** |
| `camera.left.jpeg`  | 640x480  | Left **wrist** camera, pointed at the gripper |
| `camera.right.jpeg` | 640x480  | Right **wrist** camera, pointed at the gripper |

`camera.head.jpeg` is the only one that shows the room, so it is the one the
app uses. It is two 1280x960 images joined side by side. **The laptop backend
crops it down to the left eye** before the phone ever sees it, which also halves
what crosses the network — a measured 401KB per frame down to 193KB. Do not try
to "fix" the stereo on this end; leave the topic publishing the full pair.

The small 640x480 topics look tempting because they are 13x smaller, but they
point at the robot's own hands and are useless as a "what the robot sees" view.

### If the robot's IP has changed

`172.20.10.3` is a hotspot address and it moves. Check it with:

```bash
hostname -I
```

and put the current one in `backend/.env` as `ROBOT_HOST` and `ROBOT_CAMERA_URL`.

---

## Job 2 — Create `transfer_both.py` (required)

The backend runs this command:

```bash
uv run transfer_both.py --execute --yes
```

That file does not exist yet. `drop_both.py` already has a `transfer` mode that
does the whole job — pick the item up, drive to `table_2` holding it, drop it —
but nothing calls it. `pickup_both.py` is the same idea for `pickup` mode, so
copy its shape exactly.

Create `~/bbapps/hampy_demo/transfer_both.py`:

```python
# /// script
# requires-python = ">=3.10,<3.11"
# dependencies = ["bbos", "numpy<2"]
# [tool.uv.sources]
# bbos = { path = "/home/bracketbot/bbos", editable = true }
# ///
"""Pick the item up, carry it to table_2, and drop it there."""

from drop_both import main


if __name__ == "__main__":
    raise SystemExit(main("transfer"))
```

Make sure the `# /// script` header block is copied character for character
from `pickup_both.py`. `uv` reads it to work out the dependencies, and the run
fails without it.

### Then add the stage prints

Open `drop_both.py` and add the three lines below. Line numbers are from the
current file and will drift as you edit, so match on the surrounding text.

1. **`picking`** — right after `args = parser.parse_args()` (around line 119),
   but only when the run is actually a transfer:

   ```python
   if mode == "transfer":
       print("HAMPY_STAGE: picking", flush=True)
   ```

2. **`driving`** — next to the existing line that prints
   `"PICKUP COMPLETE: navigating to table_2 while holding the item..."`
   (around line 454). Put it immediately **before** that print:

   ```python
   print("HAMPY_STAGE: driving", flush=True)
   ```

3. **`arrived`** — next to the existing line that prints
   `"Dropping: opening both grippers..."` (around line 504). Put it immediately
   **before** that print, so the app says "Ready to collect" at the same moment
   the grippers actually open:

   ```python
   print("HAMPY_STAGE: arrived", flush=True)
   ```

4. **`blocked`** — inside the existing `NAVIGATION FAILED` branch (around line
   478), add:

   ```python
   print("HAMPY_FAIL: blocked", flush=True)
   ```

Do not delete or reword any of the existing prints. The backend also matches
the old wording as a fallback, and keeping both means nothing breaks if one
half of this work lands without the other.

---

## Job 3 — Stop after the drop, and speak straight away

Right now, after the robot lets go of the item, it reverses away from
`table_2` and only *then* plays the completion sound. For the demo we want the
opposite: **drop, speak immediately, stop moving.** No reversing, no driving
back to where it started.

Add a flag rather than deleting the code, so the old behaviour is one argument
away.

**Step 1.** In `drop_both.py`, next to the other `parser.add_argument` calls
(the block ending around line 118), add:

```python
parser.add_argument(
    "--no-retreat",
    action="store_true",
    help="stay put after the drop instead of reversing away from the table",
)
```

**Step 2.** Find the block that currently runs between the arm retract and the
completion audio — it starts at `document = load_station_document(DEFAULT_CONFIG)`
(around line 516) and ends with the `WARNING: post-drop retreat timed out`
print (around line 538). That whole block is the reversing. Wrap it:

```python
if not args.no_retreat:
    document = load_station_document(DEFAULT_CONFIG)
    ...                                   # everything already there
    if not backed_away and not stopped:
        print(
            "WARNING: post-drop retreat timed out; the base is stopped. "
            "Continuing to completion audio.",
            flush=True,
        )
```

Leave the `print("Playing completion audio...")` block that follows it exactly
where it is and **outside** the new `if`. That way the sound plays either way,
and with `--no-retreat` it plays the instant the arms are clear.

**Step 3.** Because the backend passes `--no-retreat` on every run, put it in
the default command. Nothing on the robot needs to change for that — it is set
on the laptop in `backend/.env`:

```dotenv
ROBOT_COMMAND="uv run transfer_both.py --execute --yes --no-retreat"
```

Mention this to whoever owns the laptop config; the flag is useless until the
backend actually sends it.

### What the robot says when it finishes

It plays `~/bbapps/hampy_demo/completion_audio.wav` through
`play_robot_audio.py` at volume `0.95`. If you want different words, replace
that `.wav` file — it must be **16-bit PCM WAV**, any sample rate. Nothing else
needs changing.

After the audio, the script parks the arms and turns torque off on its own.
That is the idle state, and it is already correct — do not add anything to
drive the robot back to a start position.

---

## Job 4 — Two-item mode (only if someone builds it)

This is the feature where the robot carries two items and drops them at two
different tables. **It is off by default and the demo works without it.** The
laptop side is already written and waiting behind a flag.

If and when it works:

1. Write `transfer_two.py` on this robot that picks up both items, drives to
   the first table, drops item one, drives to the second table, drops item two.
2. Print these four lines at the right moments:

   ```
   HAMPY_STAGE: queued             # at the very start
   HAMPY_STAGE: dropping_first     # before driving to the first table
   HAMPY_STAGE: dropping_second    # after the first item is released
   HAMPY_STAGE: arrived            # when the second item is released
   ```

3. Tell whoever owns the laptop to set, in `backend/.env`:

   ```dotenv
   ROBOT_TWO_ITEM_MODE=true
   ROBOT_COMMAND="uv run transfer_two.py --execute --yes --no-retreat"
   ```

That flag also makes Gemini pick two items instead of one, and switches the
app's progress list to the four steps above. Setting it back to `false` returns
everything to the single-item demo. No code changes either side.

---

## Things that will bite you

### "drive.ctrl is still owned by another app"

This has already killed two runs. It means something else is holding the drive
controller. Before any run, check nothing else is driving:

```bash
ps aux | grep -E "quest_teleop|teleop|station_nav|nav_dashboard|drop_both" | grep -v grep
```

Kill anything that shows up. Quest teleop and Manual Drive are the usual
culprits. `camera_web.py` is **not** — leave it running.

### "AUTO-UNDOCK REFUSED: near table_1, but heading differs by -150.8deg"

The robot thinks it is parked at `table_1` but facing the wrong way, so it
refuses to reverse out. Physically turn the robot to roughly face away from the
table before starting, or re-save the station pose:

```bash
cd ~/bbapps/hampy_demo
uv run calibrate_station.py table_1
```

### `uv: command not found`

A non-interactive `ssh host "command"` skips the login shell, so `~/.local/bin`
is missing from `PATH`. The backend already prepends it. If you hit this in a
script you wrote yourself, start it with:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

---

## Checklist before the demo

Run these in order. Every one should pass.

```bash
# 1. camera server up
curl -s -o /dev/null -w '%{http_code}\n' \
  http://127.0.0.1:8082/snapshot/camera.head.jpeg.jpg      # expect 200

# 2. the wrapper exists and imports cleanly
cd ~/bbapps/hampy_demo && uv run transfer_both.py --help   # expect the help text

# 3. nothing else is holding the drive
ps aux | grep -E "quest_teleop|station_nav" | grep -v grep # expect nothing

# 4. the stage prints are in place
grep -n "HAMPY_STAGE" drop_both.py                         # expect 3 lines

# 5. the retreat flag exists
grep -n "no-retreat" drop_both.py                          # expect 2 lines
```

Then, with a spotter next to the emergency stop, run one full job from the
phone. The app should show **Initial pick up → Driving to shelf → Ready to
collect**, with live camera the whole way, and the robot should speak and stop
where it is.
