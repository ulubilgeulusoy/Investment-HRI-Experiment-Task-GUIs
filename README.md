# Combined Investment Experiment GUI

This repository is now centered on the combined two-stage experiment launcher:

- `combined_experiment_GUI.py`

The combined GUI brings the full workflow into one application while still using the same underlying experiment pieces:

- leak check on the Raspberry Pi
- visual inspection on the Windows machine
- task reporting on the Windows machine

## Repository Layout

### Main Combined Application

- `combined_experiment_GUI.py`
- `combined_visual_inspection_GUI.py`
- `combined_task_reporting_GUI.py`
- `run_combined_experiment.bat`
- `requirements.txt`

### Archive Folder

The `archive/` folder contains the older standalone version of the project, including:

- `archive/leak_check_GUI.py`
- `archive/visual_inspection_GUI.py`
- `archive/task_reporting_GUI.py`
- `archive/run_leak_check.bat`
- `archive/run_visual_inspection.bat`
- `archive/run_task_reporting.bat`
- `archive/README.md`

Those files are kept for reference and fallback use. The root of the repo reflects the newer combined application workflow.

## Requirements

- Python 3.9+
- `tkinter` (included with standard Python on Windows)
- `opencv-contrib-python` (includes `cv2` and `cv2.aruco`)
- `paramiko`
- a webcam for visual inspection
- network access from the Windows laptop to the Raspberry Pi
- access to the Windows SMB share used for CSV storage

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## How To Launch

Double-click:

- `run_combined_experiment.bat`

Or run directly:

```bash
python combined_experiment_GUI.py
```

Note:

- the batch launchers in this repo use relative script paths
- if the folder structure changes again, update the `.bat` files so they point to the new script locations

## Combined GUI Overview

The combined GUI works in two stages.

### Stage 1: SSH + Mount Setup

This stage is used before participant trials begin. It lets the operator:

- connect to the Raspberry Pi over SSH
- verify whether the SMB mount is active
- mount the Windows CSV share
- dismount the share if needed
- review setup logs in the GUI

The GUI also shows clear active/inactive indicators for:

- SSH connection state
- mount state

`Continue to Session Controls` stays disabled until both SSH and mount are active.

### Stage 2: Session Controls

This stage is used during the experiment session. It lets the operator:

- enter participant number
- enter trial number
- start and kill the leak check on the Raspberry Pi
- launch visual inspection
- launch task reporting
- review the shared log panel

The combined GUI is designed so participant/trial values are entered once and then reused by the combined task GUIs.

## Data Output and Reference Folder

The visual inspection and task reporting workflows read and write participant data in:

- `C:\CSV\participant_<participant_id>`

Example for participant `12`:

- `C:\CSV\participant_12`

Typical files include:

- `visual_<participant_id>_<trial_number>.csv`
- `leak_<participant_id>_<trial_number>.csv`
- `results_<participant_id>_<trial_number>.csv`

The leak-check workflow writes its leak CSV from the Raspberry Pi into a Windows SMB share mounted on the Pi at `/mnt/csv`. In the current setup, that Windows share is:

- `\\192.168.0.51\CSV`

When mounted on the Pi, leak result files are written under:

- `/mnt/csv/participant_<participant_id>/leak_<participant_id>_<trial_number>.csv`

## Visual Inspection Details

In the combined workflow, visual inspection is launched from stage 2 and receives participant/trial values from the combined GUI.

### What it does

1. Uses the participant number and trial number already entered in the combined GUI.
2. Randomly assigns colors to marker IDs `0-7`.
3. Writes assignments to:
   `C:\CSV\participant_<id>\visual_<id>_<trial>.csv`
4. Opens webcam feed (`cv2.VideoCapture(1)`) and detects ArUco markers.
5. Draws marker outlines and IDs using the assigned colors.
6. Tracks marker visibility intervals in memory.
7. Exits when the user presses `q` in the OpenCV window.

### Visual CSV format

`visual_<id>_<trial>.csv`:

```csv
marker_id,color_name
0,green
1,red
...
```

### Notes

- the combined version removes the old participant/trial prompt window
- camera index is currently `1`; change `cv2.VideoCapture(1)` if another camera index is correct on your machine
- the script includes compatibility helpers for multiple OpenCV ArUco API versions

## Task Reporting Details

In the combined workflow, task reporting is launched from stage 2 and receives participant/trial values from the combined GUI.

### Required reference files before running

The script expects these files in `C:\CSV\participant_<id>`:

- `visual_<id>_<trial>.csv` from visual inspection
- `leak_<id>_<trial>.csv` containing a leak ground-truth value `0` or `1`

If either file is missing, the GUI exits with an error dialog.

### What it does

1. Uses the participant number and trial number already entered in the combined GUI.
2. Loads expected crack ground truth from `visual_<id>_<trial>.csv`.
3. Loads expected leak ground truth from `leak_<id>_<trial>.csv`.
4. Shows a form for leak/crack presence and marker color choices.
5. Validates all required fields.
6. Computes score and saves one row to:
   `C:\CSV\participant_<id>\results_<id>_<trial>.csv`
7. Closes automatically after successful submit.

### Scoring logic

Total score is 100%:

- leak correct: `33.4%`
- crack-present value correct: `33.3%`
- all marker colors correct: `33.3%`

### Results CSV format

`results_<id>_<trial>.csv` includes headers like:

```csv
timestamp,participant_id,trial_id,leak_present,crack_present,score_percent,marker_0,marker_1,...
```

### Notes

- the combined version removes the old participant/trial prompt window
- task reporting depends on both visual inspection output and leak-check output already existing

## Leak Check Details

In the combined workflow, leak check is launched from stage 2 after stage 1 has already established SSH and mount readiness.

### What it does

1. Connects from the Windows laptop to the Raspberry Pi over SSH using password authentication.
2. Mounts or verifies the Windows SMB share on the Pi at `/mnt/csv`.
3. Runs preflight checks for:
   - the Pi conda init script
   - target folder
   - leak-check script
   - `python3`
   - `setsid`
   - mount availability
4. Launches the Raspberry Pi leak-check script inside the configured conda environment.
5. Supplies `Participant ID` and `Trial` automatically to the remote script.
6. Shows remote stdout/stderr snippets in the built-in log view.
7. Lets the operator start and kill the remote process from the combined GUI.

### Raspberry Pi script

The GUI does not perform the leak-check logic itself. It starts a separate Python script on the Raspberry Pi, currently configured as:

- `code_investment.py`

This Raspberry Pi script is the hardware-facing experiment script. It runs on the Pi, talks to the GPIO and MPR121 touch sensor, plays the audio cues, and writes the leak ground-truth CSV used later by the task-reporting workflow.

### How the Raspberry Pi script works

At a high level, the Pi-side script does the following:

1. Prompts for `Participant ID` and `Trial number`.
2. Checks whether the Windows SMB share is actually mounted at `/mnt/csv`.
3. Chooses the CSV output directory:
   - `/mnt/csv` if the Windows share is mounted
   - otherwise the local script folder on the Pi
4. Creates:
   - `participant_<participant_id>/leak_<participant_id>_<trial_number>.csv`
5. Initializes Raspberry Pi GPIO inputs:
   - main button on BCM pin `17`
   - reset button on BCM pin `27`
6. Uses the MPR121 capacitive touch sensor over I2C.
7. Loads audio assets for:
   - touch notification
   - system notification
   - recalibration
   - leak / no-leak outcome audio
8. Waits for button and touch interaction during the experiment.

### Raspberry Pi interaction logic

The script behavior is roughly:

1. On first button press, it initializes and calibrates the MPR121 sensor.
2. Once sensor monitoring is enabled, a touch on an electrode starts a looping notification sound.
3. A short button press while sound is playing stops that sound.
4. A long button hold (`>= 2` seconds) triggers the leak/no-leak outcome:
   - randomly chooses `1` for leak or `0` for no leak
   - writes that single value to the leak CSV
   - plays the corresponding audio clip
5. The reset button can reinitialize the sensor again.

### Raspberry Pi script output

The CSV written by the Pi-side leak script contains a single row with the leak ground-truth value:

```csv
1
```

or

```csv
0
```

This file is later consumed by task reporting as:

- `leak_<participant_id>_<trial_number>.csv`

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

### Current default Raspberry Pi settings

- SSH host: `192.168.0.148`
- SSH port: `22`
- SSH username: `homemicro`
- Pi conda init: `/home/homemicro/miniconda3/etc/profile.d/conda.sh`
- Pi conda env: `chrps`
- remote folder:
  `/home/homemicro/Investment Experiment/Investment Buzz Wire (old chrps folder)`
- remote script: `code_investment.py`
- PID file: `/tmp/raspi_investment.pid`
- log file: `/tmp/raspi_investment.log`

These settings are for the Windows-side launcher GUI. The actual experiment execution happens on the Raspberry Pi after SSH connection and remote launch.

### IP address note

The IP addresses shown in this README are example values from the current setup and may be different in another lab, router, or session.

In particular, check these before running:

- Raspberry Pi SSH host, currently `192.168.0.148`
- Windows SMB host, currently `192.168.0.51`

If your network assigns different addresses, update the GUI fields to match your current environment.

### Current default Windows share mount settings

- Windows host: `192.168.0.51`
- share name: `CSV`
- Windows username: `Investment`
- mount point on Pi: `/mnt/csv`
- SMB version: `3.0`

## Leak Check Setup

### On the Windows laptop

1. Make sure the folder you want to receive leak CSV files is shared over SMB.
2. Confirm the Windows share is reachable as:
   `\\192.168.0.51\CSV`
3. Confirm the Windows username and password used by the Pi for mounting.

### On the Raspberry Pi

1. Confirm SSH access works from the laptop.
2. Confirm the experiment script runs manually from the Pi in the `chrps` conda environment.
3. Install CIFS tools if needed:

```bash
sudo apt update
sudo apt install cifs-utils -y
```

4. Confirm the mount point exists:

```bash
sudo mkdir -p /mnt/csv
```

5. Confirm the Pi can reach the Windows laptop:

```bash
ping -c 1 192.168.0.51
```

## Operator Flow

1. Launch `run_combined_experiment.bat` or run `combined_experiment_GUI.py`.
2. In stage 1, enter Raspberry Pi SSH credentials.
3. Enter the Windows share password and Pi sudo password if needed.
4. Click `Test Connection`.
5. Confirm the mount is active, or click `Mount Share`.
6. Continue to stage 2.
7. Enter `Participant Number` and `Trial Number`.
8. Start leak check, visual inspection, and task reporting as needed for the session.

## Batch Launchers

The launchers in this repo activate a Conda env named `computer_vision`.

Current activation path inside the BAT files:

```bat
call "C:\Users\investment\miniconda3\Scripts\activate.bat"
call conda activate computer_vision
```

If your Miniconda install path or environment name differs, edit the BAT files.

Example environment setup:

```powershell
conda create -n computer_vision python=3.10 -y
conda activate computer_vision
pip install -r requirements.txt
```

## Archive Summary

The standalone archived GUIs cover the same three experiment areas:

- `archive/visual_inspection_GUI.py`
  Creates randomized marker assignments and shows the webcam-based ArUco overlay as a standalone tool.
- `archive/task_reporting_GUI.py`
  Collects leak/crack and marker-color responses and writes scored CSV output as a standalone tool.
- `archive/leak_check_GUI.py`
  Connects to the Raspberry Pi, mounts the share, and starts the leak-check script as a standalone tool.

The archive also includes:

- standalone `.bat` launchers adjusted for the archived file locations
- the previous detailed standalone README at `archive/README.md`

## Notes

- `combined_visual_inspection_GUI.py` uses compatibility helpers for multiple OpenCV ArUco API versions.
- camera index in `combined_visual_inspection_GUI.py` is currently `1`; change `cv2.VideoCapture(1)` if needed.
- `combined_experiment_GUI.py` relies on password-based SSH through `paramiko`.
- the combined task GUIs remove the old participant/trial prompt windows because those values are now entered once in the combined launcher.
