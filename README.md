# Combined Investment Experiment GUI

This repository contains the Linux two-stage experiment launcher.

The main entry point is:

- `combined_experiment_GUI.py`

The workflow is:

- the Raspberry Pi runs the leak-check script remotely over SSH
- the Raspberry Pi writes the leak CSV into a mounted network share at `/mnt/csv`
- the Ubuntu machine runs visual inspection and task reporting locally
- all participant CSVs are stored in one shared folder on Ubuntu

## Active Files

- `combined_experiment_GUI.py`
- `combined_visual_inspection_GUI.py`
- `combined_task_reporting_GUI.py`
- `shared_paths.py`
- `run_experiment.sh`
- `requirements.txt`

The `archive/` folder contains older standalone scripts kept for reference.

## Requirements

- Ubuntu or another Linux desktop with Python 3.9+
- `python3-tk`
- `opencv-contrib-python`
- `paramiko`
- a webcam for visual inspection
- network access from the Ubuntu machine to the Raspberry Pi
- a shared CSV folder exported from Ubuntu and mountable on the Raspberry Pi

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

On Debian/Ubuntu, install Tkinter if needed:

```bash
sudo apt-get install python3-tk
```

## Launch

Run:

```bash
./run_experiment.sh
```

Or:

```bash
python3 combined_experiment_GUI.py
```

## Data Layout

The local Ubuntu GUIs read and write participant data under:

- `/home/parc/csv`

By default this means:

- `/home/parc/csv/participant_<participant_id>`

Examples:

- `/home/parc/csv/participant_12/visual_12_1.csv`
- `/home/parc/csv/participant_12/leak_12_1.csv`
- `/home/parc/csv/participant_12/results_12_1.csv`

If you want a different local folder, set:

- `INVESTMENT_HRI_DATA_ROOT`

Example:

```bash
export INVESTMENT_HRI_DATA_ROOT=/srv/csv
```

The active code that controls this is in:

- `shared_paths.py`

## Recommended Ubuntu Share Model

1. Export a folder from Ubuntu, for example `/home/parc/csv` or `/srv/csv`, using Samba.
2. Mount that share on the Raspberry Pi at `/mnt/csv`.
3. Let the Pi write leak CSVs into `/mnt/csv/participant_<id>/...`.
4. Let the Ubuntu GUIs read and write the same participant folders locally.

This keeps all trial data in one place and matches the current controller GUI design.

## Combined GUI Overview

The combined GUI still works in two stages.

### Stage 1: SSH + Share Mount

This stage is used before trials begin. It lets the operator:

- connect to the Raspberry Pi over SSH
- verify whether the share mount is active on the Pi
- mount the Ubuntu CSV share on the Pi
- dismount the share if needed
- review setup logs in the GUI

`Continue to Session Controls` stays disabled until both SSH and the Pi-side mount are active.

### Stage 2: Session Controls

This stage is used during the experiment session. It lets the operator:

- enter participant number
- enter trial number
- start and kill the leak check on the Raspberry Pi
- choose the visual inspection camera in the Visual Inspection panel
- refresh the detected local camera list if needed
- launch visual inspection locally on Ubuntu
- launch task reporting locally on Ubuntu

## Visual Inspection

`combined_visual_inspection_GUI.py`:

1. uses the participant and trial values passed from the combined GUI
2. accepts the selected camera device from the combined GUI
3. randomly assigns colors to marker IDs `0-7`
4. writes `visual_<participant>_<trial>.csv` into the participant folder
5. opens the webcam feed and detects ArUco markers
6. draws marker outlines and IDs using the assigned colors

Camera note:

- the camera dropdown is inside the `Visual Inspection` section of stage 2, not in `Session Setup`
- the dropdown currently shows friendly names `Camera A` and `Camera B`
- those friendly names map to fixed USB-port aliases in `combined_visual_inspection_GUI.py`
- internally the app still resolves the real `/dev/video*` device from Linux camera discovery, so the selection remains stable even if camera indexes change
- the `Refresh Cameras` button repopulates the available local camera list before launch
- if `combined_visual_inspection_GUI.py` is run directly without a `--camera` argument, it falls back to its own camera picker dialog

## Task Reporting

`combined_task_reporting_GUI.py` expects these files in the participant folder:

- `visual_<id>_<trial>.csv`
- `leak_<id>_<trial>.csv`

It then:

1. loads the expected crack result from the visual CSV
2. loads the expected leak result from the leak CSV
3. shows the reporting form
4. scores the entry
5. writes `results_<id>_<trial>.csv`

## Leak Check and Raspberry Pi Mount

`combined_experiment_GUI.py` does not run the leak-check logic locally. It SSHes into the Raspberry Pi and launches the configured remote script there.

- the Pi should write to `/mnt/csv`
- `/mnt/csv` should be the mounted Ubuntu share

The GUI still uses SMB/CIFS mount commands on the Pi, so the simplest setup is:

- Ubuntu exports the CSV directory over Samba
- Raspberry Pi mounts `//ubuntu-host/share-name` at `/mnt/csv`

### Full Raspberry Pi script (`code_investment.py`)

```python
# SPDX-FileCopyrightText: 2017 Tony DiCola for Adafruit Industries
# SPDX-License-Identifier: MIT

# Simple test of the MPR121 capacitive touch sensor library.
# Will print out a message when any of the 12 capacitive touch inputs of the
# board are touched.  Open the serial REPL after running to see the output.
# Author: Tony DiCola
import os
import time
import csv
import re
import board
import busio
import time

from pydub import AudioSegment
from pydub.playback import play
import random

from tkinter import *

import RPi.GPIO as GPIO

import pygame

# --- Windows share target (mounted SMB share) ---
WINDOWS_MOUNT = "/mnt/csv"

def _windows_share_ready(path=WINDOWS_MOUNT):
    """
    Returns True only if the mount exists AND is actually mounted.
    This prevents silently writing to local /mnt/csv when mount is down.
    """
    try:
        if not os.path.isdir(path):
            return False
        # Linux: check if it's a mount point (works well for SMB mounts)
        return os.path.ismount(path)
    except Exception:
        return False



pygame.mixer.init()
sound = pygame.mixer.Sound("/home/homemicro/Documents/chrps/chrps/noti_beep.wav")
sound2 = pygame.mixer.Sound("/home/homemicro/Documents/chrps/chrps/system-noti.wav")
sound3 = pygame.mixer.Sound("/home/homemicro/Documents/chrps/chrps/recalibrated.wav")
leak_sound = AudioSegment.from_file(
    "/home/homemicro/Investment Experiment/Investment Buzz Wire (old chrps folder)/leak.m4a"
)+15
no_leak_sound = AudioSegment.from_file(
    "/home/homemicro/Investment Experiment/Investment Buzz Wire (old chrps folder)/no_leak.m4a"
)+15

# import required module
# from playsound import playsound


# Import MPR121 module.
import adafruit_mpr121

""" # Create I2C bus.
i2c = busio.I2C(board.SCL, board.SDA)

# Create MPR121 object.
mpr121 = adafruit_mpr121.MPR121(i2c) """

def configure_mpr121(running=False):
    global mpr121
    # Create I2C bus.
    i2c = busio.I2C(board.SCL, board.SDA)

    # Create MPR121 object.
    mpr121 = adafruit_mpr121.MPR121(i2c)

    touch_threshold = 16
    release_threshold = 6

    for i in range(12):
        mpr121[i].threshold = touch_threshold
        mpr121[i].release_threshold = release_threshold
    time.sleep(0.1)
    for i in range(12):
         print(f"Electrode {i}, Baseline = {mpr121.baseline_data(i)}, Filtered = {mpr121.filtered_data(i)}")

    # for i in range(1):
    #     sound2.play()
    #     time.sleep(.5)
    if running:
        sound3.play()


# Note you can optionally change the address of the device:
# mpr121 = adafruit_mpr121.MPR121(i2c, address=0x91)

# Write latest leak/no-leak decision to a CSV (1 = leak, 0 = no leak).
RESULTS_CSV = None


def _sanitize_token(token):
    token = token.strip()
    token = re.sub(r"\s+", "_", token)
    return re.sub(r"[^A-Za-z0-9_-]", "", token)


def export_leak_result(value):
    if RESULTS_CSV is None:
        raise RuntimeError("RESULTS_CSV not set. Provide participant ID and trial number.")
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([value])


# Loop forever testing each input and printing when they're touched.
count = 0
# song = AudioSegment.from_wav("/home/homemicro/Documents/chrps/chrps/ping.wav")
# song2 = AudioSegment.from_wav("/home/homemicro/Documents/chrps/chrps/system-noti.wav")

# playsound('/home/homemicro/Documents/chrps/nope.wav')
print('playing sound using  playsound')

GPIO.setmode(GPIO.BCM)
button_pin = 17
reset_button_pin = 27
GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(reset_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

try:
    participant_id = _sanitize_token(input("Participant ID: "))
    trial_number = _sanitize_token(input("Trial number: "))
    if not participant_id or not trial_number:
        raise ValueError("Participant ID and trial number are required.")
        # Decide output directory:
    # Prefer Windows-mounted share, otherwise fall back to local script folder
    if _windows_share_ready(WINDOWS_MOUNT):
        base_out_dir = WINDOWS_MOUNT
    else:
        base_out_dir = os.path.dirname(__file__)
        print(f"[WARN] Windows share not mounted at {WINDOWS_MOUNT}. Writing CSV locally to: {base_out_dir}")

    # Optional: keep data organized in a participant folder
    participant_folder = os.path.join(base_out_dir, f"participant_{participant_id}")
    os.makedirs(participant_folder, exist_ok=True)

    RESULTS_CSV = os.path.join(
        participant_folder,
        f"leak_{participant_id}_{trial_number}.csv",
    )


    playing = False
    sensor_enabled = False
    initialized_once = False
    last_button_state = GPIO.HIGH
    button_press_start = None

    while True:

        if sensor_enabled:
            for i in range(12):
                if mpr121[i].value and not playing:
                    print(f"Playing sound on touch {i}")
                    print(f"Electrode {i}: {mpr121.baseline_data(i)} (Baseline), {mpr121.filtered_data(i)} Filtered")
                    sound.play(loops=-1)
                    playing = True

        button_state = GPIO.input(button_pin)
        if button_state == GPIO.LOW and last_button_state == GPIO.HIGH:
            button_press_start = time.time()
        if button_state == GPIO.HIGH and last_button_state == GPIO.LOW:
            press_duration = 0
            if button_press_start is not None:
                press_duration = time.time() - button_press_start
            button_press_start = None

            if not initialized_once:
                print("Button pressed! Init sensor")
                configure_mpr121(True)
                sensor_enabled = True
                initialized_once = True
            else:
                if playing:
                    print("Button pressed! Stopping sound")
                    sound.stop()
                    playing = False
                elif press_duration >= 2:
                    print("Button held! Playing leak/no-leak sound")
                    leak_value = random.choice([1, 0])
                    export_leak_result(leak_value)
                    play(leak_sound if leak_value == 1 else no_leak_sound)
                    sensor_enabled = False
                    initialized_once = False
                    playing = False
        last_button_state = button_state

        if GPIO.input(reset_button_pin) == GPIO.LOW:
            print("Init sensor")
            configure_mpr121(True)

        time.sleep(0.01)

        """ # Loop through all 12 inputs (0-11).
        for i in range(12):
            # Call is_touched and pass it then number of the input.  If it's touched
            # it will return True, otherwise it will return False.
            if mpr121[i].value:
                print("Input {} touched!".format(i))
                print(count)
                if i == 0:
                    while True:
                        print("if")
                        #play(song)
                        sound.play()
                        time.sleep(2)
                        button_state = GPIO.input(button_pin)
                        if button_state == GPIO.LOW:
                            print('Button Pressed!')
                            break
                    # snd.play(blocking=1)
                    # playsound('/home/homemicro/Documents/chrps/chrps/nope.wav')

                else:

                    print("Else")
                    sound.play()
                    #play(song2)
                    # snd1.play(blocking=1)
                    # playsound('/home/homemicro/Documents/chrps/chrps/nope.wav')

                count = count + 1 """

except KeyboardInterrupt:
    print('Exiting program...')
    GPIO.cleanup()
```

## Current Defaults in the GUI

The controller currently defaults to these values:

- SSH host: `192.168.0.148`
- SSH port: `22`
- SSH username: `homemicro`
- remote conda init: `/home/homemicro/miniconda3/etc/profile.d/conda.sh`
- remote conda env: `chrps`
- remote folder: `/home/homemicro/Investment Experiment/Investment Buzz Wire (old chrps folder)`
- remote script: `code_investment.py`
- share host: `192.168.0.121`
- share user: `parc`
- Pi mount point: `/mnt/csv`
- share name: `CSV`

You should update the share host, username, and password fields in the GUI to match the Ubuntu machine exporting the CSV folder.

## Notes

- the shared local data root is configurable through `shared_paths.py`
- `run_experiment.sh` is the provided launcher for this branch

