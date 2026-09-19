# Page detection (BracketBot)

Finds a sheet of paper in the head camera and maps its surface to millimetres,
origin at the paper's top-left, x along the top edge, y down the left edge —
the frame the phone sends drawing coordinates in.

This code runs **on the robot**, not in the app bundle. It lives here so it is
version controlled (`~/bbapps` on the robot is *not* a git repo), and deploys
over SSH. Everything in the detection path opens the camera as a **Reader**,
which bbos never makes exclusive, so it runs safely alongside teleop and the
arm work.

## Deploy

```bash
scp -r robot/draw bracketbot@172.20.10.3:~/bbapps/
```

`uv` is not on the PATH for non-interactive SSH, so prefix remote commands with
`export PATH=$HOME/.local/bin:$PATH`. Each script carries its own dependency
header, so `uv run <script>` builds its environment on first use.

---

# Verifying it yourself

Do not take my word for any of this. Each step below produces evidence you can
check with your own eyes, in increasing order of what it proves. **Step 5 is the
only one that proves the millimetres are real**, and only you can run it.

SSH in first:

```bash
ssh bracketbot@172.20.10.3
export PATH=$HOME/.local/bin:$PATH
cd ~/bbapps/draw
```

### 1. The geometry math — no robot involved

```bash
uv run test_detect.py
```

Draws a page at corners it chooses, detects it, and compares. Expect:

```
corner error px: [0.0, 0.0, 1.41, 0.0]
mm->px round trip err: [0.0, 0.0, 0.0, 0.0]
centre 139.7,108.0mm -> px [673.7, 507.2] -> mm [139.7, 107.95]
```

Corner error is the polygon simplifier rounding; anything under ~2 px is fine.
This proves the homography math, nothing about the camera.

### 2. A real frame from your camera

```bash
uv run grab_frame.py                      # saves /tmp/head.jpg
uv run detect_page.py --source /tmp/head.jpg --debug-image /tmp/overlay.png
```

Then copy it to your laptop and **look at it**:

```bash
scp bracketbot@172.20.10.3:/tmp/overlay.png .
```

You should see a green outline on the paper, TL/TR/BR/BL labels on its corners,
a red x-axis arrow and blue y-axis arrow from the top-left, and a 25 mm grid.
If the green outline is around a laptop or a table instead, detection failed —
that is what this step is for.

### 3. The server's logic, and the full-resolution claim

```bash
uv run test_server.py
```

Feeds `/tmp/head.jpg` through the same code path the live server uses and
checks the API. Expect `worst corner round-trip error: 0.00 mm` and
`ALL SERVER CHECKS PASSED`.

Then check the claim that detection has to run at full resolution:

```bash
uv run test_scale.py
```

On your own frame, on your own robot. What it printed here:

```
scale 1.0       78 ms  found  area=0.0140  aspect_err=0.015  looks like paper
scale 0.75      44 ms  found  area=0.4684  aspect_err=0.208  WRONG OBJECT
scale 0.5       21 ms  NOT FOUND
```

Half scale loses a small page entirely, and three-quarter scale is worse than
useless: it confidently reports something that is not the paper. 78 ms is 13
detections a second, which is plenty. If your numbers disagree with mine, trust
yours and change the default.

### 4. Live, in a browser — the useful one

```bash
uv run page_server.py --paper-mm 215.9 279.4
```

Then open **http://bracketbot-0186.local:8005/** on your laptop or phone (same
network as the robot). You get the annotated feed, live numbers, sliders to
retune without restarting, and click-to-measure.

Put a sheet on the table, point the robot at it, and watch:

| Readout | What it should say |
| --- | --- |
| page | `found` |
| stable | `yes` (`settling n/4` while it locks on) |
| area | above ~1.5 %; if lower, move the robot closer |
| aspect err | under ~0.05 — this is the strongest signal it is a real page |
| corners | all four near 90° |

Move the paper around. The outline should track it and the axes should stay
pinned to the same physical corner. If it jumps to furniture, raise **Min area**
until it stops.

### 5. Do the millimetres match reality? — the real test

Steps 1–4 prove the code is *internally consistent* and that the outline lands
on the paper. They cannot tell you whether "100 mm" means 100 real millimetres.
Only this can:

1. With a ruler, mark a cross on the sheet **50 mm from the left edge and
   50 mm from the top**. Mark a second at **150, 200**.
2. In the browser, click exactly on each cross.
3. The readout should say close to `50.0, 50.0` and `150.0, 200.0`.

How close is good enough is your call, but for drawing you want a few mm at
worst. Also click all four corners — they should read `0,0`, `215.9,0`,
`215.9,279.4` and `0,279.4`.

**Then test the lens.** Click the **midpoint of the top edge**. It should read
`108, 0`. Whatever the second number comes out as is your barrel distortion in
millimetres, measured directly. That number is the single most useful thing you
can learn today, because it sets the floor on how accurate the drawing can be.

---

## What I verified, and what I did not

| Claim | Evidence |
| --- | --- |
| Homography math is correct | `test_detect.py`: ≤1.4 px corner error, exact round-trip |
| It finds a real page | Found the notepad on your table; corners 83.7–96.3°, aspect error 0.015 |
| API and click-to-measure work | `test_server.py`: 0.00 mm corner error, off-sheet clicks rejected |
| Full resolution is the right default | Timed on the robot: 1.0 → 77 ms and correct; 0.75 → locks onto the wrong object; 0.5 → finds nothing |
| **mm match physical reality** | **Not verified — needs step 5 and a ruler** |
| **Holds steady live on a positioned page** | **Not verified — a live run on the current scene was intermittent** |

I never started the server myself; a permission guard blocked opening a network
port, so step 4 is genuinely unrun. That is also why step 5 is yours.

## Known limits

1. **Live detection was intermittent at desk distance.** In the real frame the
   notepad filled 1.4 % of the image, out at the edge of the lens. It detects in
   a still but did not hold still for several frames running. Get closer, or
   relax with `--min-area 0.008 --stable-frames 4 --tolerance 12`.
2. **The head camera is a fisheye.** Straight lines visibly bow, so a real
   rectangle does not project to a straight-edged quad. Accuracy degrades away
   from the image centre — keep the page near the middle. Step 5 measures the
   damage. Fixing it properly needs a checkerboard calibration.
3. **`--scale` below 1.0 is a trap.** Measured, not guessed: see the table above.
4. **"Top-left" is the image's top-left,** not a marked corner of the sheet.
   Rotate the paper 180° and the origin moves with it. Mark one corner and check
   it, or the drawing comes out rotated.
5. **Camera frame is not arm frame.** Detection says where the page is relative
   to the camera. Nothing here maps that to arm coordinates.

## Files

| File | Purpose |
| --- | --- |
| `detect_page.py` | The detector. One-shot CLI, prints the page frame as JSON |
| `page_server.py` | Live browser test rig on port 8005 |
| `grab_frame.py` | Saves one head-camera frame to `/tmp/head.jpg` |
| `test_detect.py` | Synthetic regression test for the geometry |
| `test_server.py` | Regression test for the server logic and API |
| `test_scale.py` | Reproduces why `--scale` must stay at 1.0 |
| `pen_grip.py` | Gripper clamp — **untested on hardware**, belongs to the arm workstream |

### `detect_page.py` output

| Field | Meaning |
| --- | --- |
| `corners_px` | `tl`/`tr`/`br`/`bl` in left-eye pixels |
| `homography_px_to_mm` | pixel → paper mm |
| `homography_mm_to_px` | paper mm → pixel, for checking a stroke before drawing |
| `page_mm`, `orientation` | which way round the sheet is |
| `quality.aspect_error` | how close the shape is to your paper's real ratio |
| `pose_camera_approx` | 3D pose — **approximate**, assumes a focal length |

The homography needs **no camera calibration**: four corners plus the real
paper size determine it exactly. The 3D pose does not — it guesses a focal
length, exactly as `hampy_demo/marker_alignment.py` does, because this robot has
no saved intrinsics. Do not trust its distances.
