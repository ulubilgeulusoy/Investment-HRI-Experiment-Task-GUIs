# Combined Investment Experiment GUI

This repository is centered on the combined two-stage experiment launcher:

- `combined_experiment_GUI.py`

The combined GUI brings the full workflow into one application:

1. Stage 1 handles Raspberry Pi SSH connection and Windows share mount setup.
2. Stage 2 collects participant/trial values once and provides launch controls for:
   - leak check
   - visual inspection
   - task reporting

## Main Files

- `combined_experiment_GUI.py`
- `combined_visual_inspection_GUI.py`
- `combined_task_reporting_GUI.py`
- `run_combined_experiment.bat`
- `requirements.txt`

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

### Stage 1: SSH + Mount Setup

This stage is used before running participant trials. It lets the operator:

- connect to the Raspberry Pi over SSH
- check whether the SMB mount is active
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

## Data Flow

The visual inspection and task reporting workflows use:

- `C:\CSV\participant_<participant_id>`

Typical files include:

- `visual_<participant>_<trial>.csv`
- `leak_<participant>_<trial>.csv`
- `results_<participant>_<trial>.csv`

The leak-check workflow writes its result through the Raspberry Pi to the mounted Windows share.

## Requirements

- Python 3.9+
- `tkinter`
- `opencv-contrib-python`
- `paramiko`
- access to the Raspberry Pi over SSH
- access to the Windows SMB share used for CSV storage
- a webcam for visual inspection

Install dependencies with:

```bash
python -m pip install -r requirements.txt
```

## Archive Folder

The `archive/` folder contains the older standalone version of the project, including:

- `leak_check_GUI.py`
- `visual_inspection_GUI.py`
- `task_reporting_GUI.py`
- the original standalone `.bat` launchers
- the previous README documenting that standalone layout

Those files are kept for reference and fallback use, while the root of the repo now reflects the combined application workflow.
