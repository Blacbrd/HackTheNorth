# BracketBot ring control

## Setup

Clone the HID helper beside this repository folder and create its Python
environment:

```bash
git clone https://github.com/integralbyte/AQual.git ../AQual
python3 -m venv ../AQual/.venv
../AQual/.venv/bin/python -m pip install hidapi httpx
```

Deploy the persistent bridge and audio to the robot. The robot directory must
also contain the existing `six_seven.py` and `play_robot_audio.py` programs.

```bash
scp ring_robot_bridge.py thank_you.wav \
  bracketbot@bracketbot-0186.local:/home/bracketbot/bbapps/hampy_demo/
```

The Yiser-J6 ring is mapped as follows:

- Up: move backward one short step
- Down: move forward one short step
- Left: turn right one short step
- Right: turn left one short step
- Center: run the six-seven arm gesture
- Home/secondary button: say “Thank you for listening!”

The movement commands are intentionally short: 0.30 seconds at 0.12 m/s forward,
0.10 m/s backward, or 0.40 rad/s while turning. Each command finishes by sending
a zero-velocity command.

Before starting, stop dashboard Manual Drive, navigation, Quest teleop, and any
other program that owns `drive.ctrl` or either arm controller. Clear the robot's
path and keep the emergency stop ready.

Start the controller on the Mac:

```bash
cd /Users/ace/Documents/ChatGPT/bracketbot/ring-to-keyboard
./start_ring_robot.command
```

Press `Ctrl-C` to stop. The Mac maintains one SSH connection to the robot, so
directional presses do not incur a new SSH connection delay.
