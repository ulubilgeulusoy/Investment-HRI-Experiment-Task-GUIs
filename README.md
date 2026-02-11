# Investment HRI Experiment Task GUIs

This repository contains two Python GUIs used in the pipe inspection HRI workflow:

- `visual_inspection_GUI.py` generates randomized marker color assignments and displays live ArUco detection from a webcam.
- `task_reporting_GUI.py` collects participant responses, compares them to reference files, and writes a scored result CSV.

## Repository Files

- `visual_inspection_GUI.py`
- `task_reporting_GUI.py`
- `requirements.txt`
- `GUIs/run_visual_inspection.bat`
- `GUIs/run_task_reporting.bat`

## Requirements

- Python 3.9+
- `tkinter` (included with standard Python on Windows)
- `opencv-contrib-python` (includes `cv2` and `cv2.aruco`)
- A webcam

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Output and Reference Folder

Both GUIs read/write data in:

- `C:\CSV\participant_<participant_id>`

Example for participant `12`:

- `C:\CSV\participant_12`

## GUI 1: Visual Inspection

Run:

```bash
python visual_inspection_GUI.py
```

### What it does

1. Prompts for `participant_id` and `trial_number` in a small Tk window.
2. Randomly assigns colors to marker IDs `0-7`:
- green by default
- red with probability bias, capped at 3 red markers
3. Writes assignments to:
- `C:\CSV\participant_<id>\visual_<id>_<trial>.csv`
4. Opens webcam feed (`cv2.VideoCapture(1)`) and detects ArUco markers.
5. Draws marker outlines and IDs using assigned colors.
6. Tracks marker visibility intervals in memory (not written to disk).
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

### Required reference files before running

The script expects these files in `C:\CSV\participant_<id>`:

- `visual_<id>_<trial>.csv` (from Visual Inspection GUI)
- `leak_<id>_<trial>.csv` (contains a leak ground-truth value `0` or `1`)

If either file is missing, the GUI exits with an error dialog.

### What it does

1. Prompts for `participant_id` and `trial_id`.
2. Loads expected crack ground truth from `visual_<id>_<trial>.csv`:
- expected crack = `1` if any marker is red, otherwise `0`
3. Loads expected leak ground truth from `leak_<id>_<trial>.csv`.
4. Shows a form with:
- read-only participant/trial
- leak present (`0/1`)
- crack present (`0/1`)
- red/green choice for each marker ID found in the visual CSV
5. Validates all required fields.
6. Computes score and saves one row to:
- `C:\CSV\participant_<id>\results_<id>_<trial>.csv`
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

## BAT Launchers (Conda)

The launchers in `GUIs/` activate a Conda env named `computer_vision` and run the scripts:

- `GUIs/run_visual_inspection.bat`
- `GUIs/run_task_reporting.bat`

Current activation path inside both BAT files:

```bat
call "C:\Users\investment\miniconda3\Scripts\activate.bat"
call conda activate computer_vision
```

If your Miniconda install path or environment name differs, edit both BAT files.

Example environment setup:

```powershell
conda create -n computer_vision python=3.10 -y
conda activate computer_vision
pip install -r requirements.txt
```

## Notes

- If ID fields are left blank, scripts fall back to default IDs (`participant` / `trial`).
- `visual_inspection_GUI.py` uses compatibility helpers for multiple OpenCV ArUco API versions.
- Camera index is currently `1`; change `cv2.VideoCapture(1)` if your webcam is on another index.
