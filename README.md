# Combined Investment Experiment GUI

This repository is the Ubuntu/Linux version of the combined two-stage experiment launcher.

The main entry point is:

- `combined_experiment_GUI.py`

The workflow remains the same as the previous setup:

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

The `archive/` folder still contains the older standalone scripts and Windows batch launchers for reference only.

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

Use the same mount-based architecture that already worked well before.

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

The important part for Linux migration is unchanged:

- the Pi should write to `/mnt/csv`
- `/mnt/csv` should be the mounted Ubuntu share

The GUI still uses SMB/CIFS mount commands on the Pi, so the simplest setup is:

- Ubuntu exports the CSV directory over Samba
- Raspberry Pi mounts `//ubuntu-host/share-name` at `/mnt/csv`

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

## Migration Summary

The active code is now aligned with the Linux deployment model:

- local GUI CSV paths no longer use `C:\CSV`
- the shared local data root is configurable through `shared_paths.py`
- the controller GUI uses neutral share wording instead of Windows-only wording
- the repo includes a Linux shell launcher instead of relying on a `.bat` file
