# Investment HRI Experiment Task GUIs

Two Python GUIs for running and logging investment HRI / pipe inspection experiments:

- `task_reporting_GUI.py`: a Tkinter form that records participant/trial IDs, binary leak/crack presence, and optional crack locations into a timestamped CSV.
- `visual_inspection_GUI.py`: an OpenCV window that detects ArUco markers (IDs 0–14), highlights them with random green/red colors, logs which markers go red to a CSV, and records marker visibility intervals.

## Requirements
- Python 3.9+ (tested with the built-in `tkinter` on standard Python installs)
- Packages: `opencv-python` (provides `cv2` and `cv2.aruco`)
- A webcam for the visual inspection tool (update the device index in `cv2.VideoCapture(1)` if needed)

Install dependencies:
```bash
python -m pip install opencv-python
```

## Usage

### Task reporting GUI
```bash
python task_reporting_GUI.py
```
- Choose 0/1 for leak and crack; optional free text for crack locations (space-separated parts are split into fixed CSV columns).
- Each run writes to `experiment_responses_YYYYMMDD_HHMMSS.csv` beside the script. A header row is added on first write.

### Visual inspection GUI
```bash
python visual_inspection_GUI.py
```
- Press `q` to quit.
- On startup, marker IDs 0–14 are randomly assigned green with a cap of 3 red markers; assignments are saved to `marker_color_assignments_YYYYMMDD_HHMMSS.csv`.
- The webcam feed draws detected markers with their assigned colors and labels. Marker visibility intervals are tracked in-memory; extend the script to persist them if needed.

## Notes
- Both scripts are standalone; no external config files are required.
- Data files are timestamped per run to avoid overwriting prior results.
