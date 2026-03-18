# Investment HRI Experiment Task GUIs

This repository contains three Python GUIs used in the pipe inspection HRI workflow:

- `visual_inspection_GUI.py` generates randomized marker color assignments and displays live ArUco detection from a webcam.
- `task_reporting_GUI.py` collects participant responses, compares them to reference files, and writes a scored result CSV.
- `leak_check_GUI.py` connects to a Raspberry Pi over SSH, mounts a Windows SMB share on the Pi, launches the leak-check script remotely, and monitors its status/logs.

## Repository Files

- `visual_inspection_GUI.py`
- `task_reporting_GUI.py`
- `leak_check_GUI.py`
- `requirements.txt`
- `GUIs/run_visual_inspection.bat`
- `GUIs/run_task_reporting.bat`
- `GUIs/run_leak_check_GUI.bat`

## Requirements

- Python 3.9+
- `tkinter` (included with standard Python on Windows)
- `opencv-contrib-python` (includes `cv2` and `cv2.aruco`)
- `paramiko`
- A webcam for `visual_inspection_GUI.py`
- Network access from the Windows laptop to the Raspberry Pi for `leak_check_GUI.py`

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Output and Reference Folder

The visual inspection and task reporting GUIs read/write participant data in:

- `C:\CSV\participant_<participant_id>`

Example for participant `12`:

- `C:\CSV\participant_12`

The leak-check workflow writes its leak CSV from the Raspberry Pi into a Windows SMB share mounted on the Pi at `/mnt/csv`. In the current setup, that Windows share is:

- `\\192.168.0.51\CSV`

When mounted on the Pi, leak result files are written under:

- `/mnt/csv/participant_<participant_id>/leak_<participant_id>_<trial_number>.csv`

## GUI 1: Visual Inspection

Run:

```bash
python visual_inspection_GUI.py
```

Or double-click:

- `GUIs/run_visual_inspection.bat`

### What it does

1. Prompts for `participant_id` and `trial_number` in a small Tk window.
2. Randomly assigns colors to marker IDs `0-7`.
3. Writes assignments to:
   `C:\CSV\participant_<id>\visual_<id>_<trial>.csv`
4. Opens webcam feed (`cv2.VideoCapture(1)`) and detects ArUco markers.
5. Draws marker outlines and IDs using assigned colors.
6. Tracks marker visibility intervals in memory.
7. Exit with `q`.

### Visual CSV format

`visual_<id>_<trial>.csv`:

```csv
marker_id,color_name
0,green
1,red
...
```

## GUI 2: Task Reporting

Run:

```bash
python task_reporting_GUI.py
```

Or double-click:

- `GUIs/run_task_reporting.bat`

### Required reference files before running

The script expects these files in `C:\CSV\participant_<id>`:

- `visual_<id>_<trial>.csv` from Visual Inspection
- `leak_<id>_<trial>.csv` containing a leak ground-truth value `0` or `1`

If either file is missing, the GUI exits with an error dialog.

### What it does

1. Prompts for `participant_id` and `trial_id`.
2. Loads expected crack ground truth from `visual_<id>_<trial>.csv`.
3. Loads expected leak ground truth from `leak_<id>_<trial>.csv`.
4. Shows a form for leak/crack presence and marker color choices.
5. Validates all required fields.
6. Computes score and saves one row to:
   `C:\CSV\participant_<id>\results_<id>_<trial>.csv`
7. Closes automatically after successful submit.

### Scoring logic

Total score is 100%:

- Leak correct: `33.4%`
- Crack-present value correct: `33.3%`
- All marker colors correct: `33.3%`

### Results CSV format

`results_<id>_<trial>.csv` includes headers like:

```csv
timestamp,participant_id,trial_id,leak_present,crack_present,score_percent,marker_0,marker_1,...
```

## GUI 3: Leak Check

Run:

```bash
python leak_check_GUI.py
```

Or double-click:

- `GUIs/run_leak_check_GUI.bat`

### What it does

1. Connects from the Windows laptop to the Raspberry Pi over SSH using password authentication.
2. Optionally mounts the Windows SMB share on the Pi at `/mnt/csv`.
3. Runs preflight checks for:
   the Pi conda init script, target folder, leak-check script, `python3`, `setsid`, and the mount point.
4. Launches the Raspberry Pi leak-check script inside the configured conda environment.
5. Supplies `Participant ID` and `Trial` automatically to the remote script.
6. Shows remote stdout/stderr snippets in the built-in log view.
7. Lets the operator start, stop, kill, and check the remote process.

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
8. Waits for button/touch interaction during the experiment.

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

This file is later consumed by `task_reporting_GUI.py` as:

- `leak_<participant_id>_<trial_number>.csv`

### Current default Raspberry Pi settings

- SSH host: `192.168.0.148`
- SSH port: `22`
- SSH username: `homemicro`
- Pi conda init: `/home/homemicro/miniconda3/etc/profile.d/conda.sh`
- Pi conda env: `chrps`
- Remote folder:
  `/home/homemicro/Investment Experiment/Investment Buzz Wire (old chrps folder)`
- Remote script: `code_investment.py`
- PID file: `/tmp/raspi_investment.pid`
- Log file: `/tmp/raspi_investment.log`

These settings are for the Windows-side launcher GUI. The actual experiment execution happens on the Raspberry Pi after SSH connection and remote launch.

### Current default Windows share mount settings

- Windows host: `192.168.0.51`
- Share name: `CSV`
- Windows username: `Investment`
- Mount point on Pi: `/mnt/csv`
- SMB version: `3.0`

### Leak Check setup

#### On the Windows laptop

1. Make sure the folder you want to receive leak CSV files is shared over SMB.
2. Confirm the Windows share is reachable as:
   `\\192.168.0.51\CSV`
3. Confirm the Windows username and password used by the Pi for mounting.

#### On the Raspberry Pi

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

### Leak Check operator flow

1. Launch `leak_check_GUI.py` or double-click `GUIs/run_leak_check_GUI.bat`.
2. Enter the Raspberry Pi SSH password.
3. Enter the Windows share password and Pi sudo password if needed.
4. Click `Test Connection`.
5. Click `Mount Share`.
6. Enter `Participant ID` and `Trial`.
7. Click `Start Experiment`.
8. Use `Show Last Log`, `Check Status`, `Stop Experiment`, or `Kill Experiment` as needed.

### Notes for Leak Check

- `Mount Share` uses `sudo mount -t cifs` on the Raspberry Pi.
- If `Pi sudo Password` is left blank, the GUI falls back to the SSH password.
- If the share is already mounted, the GUI reports `ALREADY_MOUNTED /mnt/csv`.
- The remote process is tracked with `/tmp/raspi_investment.pid`.
- The GUI log shows the SSH command output, not a full live terminal stream.

## BAT Launchers (Conda)

The launchers in `GUIs/` activate a Conda env named `computer_vision` and run the scripts:

- `GUIs/run_visual_inspection.bat`
- `GUIs/run_task_reporting.bat`
- `GUIs/run_leak_check_GUI.bat`

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

## Notes

- `visual_inspection_GUI.py` uses compatibility helpers for multiple OpenCV ArUco API versions.
- Camera index in `visual_inspection_GUI.py` is currently `1`; change `cv2.VideoCapture(1)` if needed.
- `leak_check_GUI.py` relies on password-based SSH through `paramiko`.
