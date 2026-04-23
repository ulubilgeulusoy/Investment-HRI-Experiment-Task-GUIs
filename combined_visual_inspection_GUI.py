import argparse
import ctypes
from pathlib import Path
import random
import re
import subprocess
import sys
import time
import tkinter as tk
from tkinter import messagebox
from typing import Optional

import cv2
import cv2.aruco as aruco

from shared_paths import get_participant_dir

CAMERA_PORT_ALIASES = {
    "usb-0000:00:14.0-6.1": "Camera A",
    "usb-0000:00:14.0-6.2": "Camera B",
}

# OpenCV renamed a few ArUco helpers; keep compatibility with both APIs.
def _get_predefined_dict(dict_id):
    """Return ArUco dictionary across OpenCV versions."""
    if hasattr(aruco, "Dictionary_get"):
        return aruco.Dictionary_get(dict_id)
    return aruco.getPredefinedDictionary(dict_id)

def _create_detector_params():
    """Return detector parameters across OpenCV versions."""
    if hasattr(aruco, "DetectorParameters_create"):
        return aruco.DetectorParameters_create()
    return aruco.DetectorParameters()

def _detect_markers(gray_frame, aruco_dictionary, detector_parameters):
    """Detect markers across old and new OpenCV ArUco APIs."""
    if hasattr(aruco, "detectMarkers"):
        return aruco.detectMarkers(gray_frame, aruco_dictionary, parameters=detector_parameters)

    detector = aruco.ArucoDetector(aruco_dictionary, detector_parameters)
    return detector.detectMarkers(gray_frame)


def _bring_window_to_front(window_name: str) -> None:
    """Best-effort attempt to foreground the OpenCV window."""
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, window_name)
        if hwnd:
            user32.ShowWindow(hwnd, 5)  # SW_SHOW
            user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def _position_window_on_right(window_name: str, width: int, height: int) -> None:
    """Place the window near the top-right of the primary display."""
    if sys.platform != "win32":
        try:
            cv2.resizeWindow(window_name, width, height)
        except Exception:
            pass
        return
    try:
        user32 = ctypes.windll.user32
        screen_width = user32.GetSystemMetrics(0)
        x = max(0, screen_width - width - 60)
        y = 60
        cv2.resizeWindow(window_name, width, height)
        cv2.moveWindow(window_name, x, y)
    except Exception:
        try:
            cv2.resizeWindow(window_name, width, height)
        except Exception:
            pass


def _build_waiting_frame(window_name: str):
    frame = 255 * (cv2.UMat(540, 960, cv2.CV_8UC3).get() * 0)
    frame[:] = (245, 245, 245)
    cv2.putText(frame, "Visual Inspection", (260, 210), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (40, 40, 40), 2, cv2.LINE_AA)
    cv2.putText(frame, "Opening camera, please wait...", (250, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (80, 80, 80), 2, cv2.LINE_AA)
    cv2.putText(frame, "Use the window X button to close.", (255, 335), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (110, 110, 110), 2, cv2.LINE_AA)
    return frame


def _format_camera_label(camera_name: str, usb_id: str, device_ref) -> str:
    alias = CAMERA_PORT_ALIASES.get(usb_id, camera_name)
    detail = usb_id or str(device_ref)
    return f"{alias} [{detail}] -> {device_ref}"


def _get_camera_menu_label(camera_name: str, usb_id: str) -> str:
    return CAMERA_PORT_ALIASES.get(usb_id, camera_name)


def _parse_camera_index(device_ref) -> Optional[int]:
    if isinstance(device_ref, int):
        return device_ref
    match = re.fullmatch(r"/dev/video(\d+)", str(device_ref).strip())
    if match:
        return int(match.group(1))
    return None


def _list_cameras_from_v4l2() -> list[dict]:
    try:
        result = subprocess.run(
            ["v4l2-ctl", "--list-devices"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return []

    cameras = []
    current_name = None
    current_usb_id = ""
    current_devices = []

    def flush_current():
        if not current_name or not current_devices:
            return
        video_nodes = sorted(
            (device for device in current_devices if device.startswith("/dev/video")),
            key=lambda device: _parse_camera_index(device) if _parse_camera_index(device) is not None else 10**9,
        )
        if not video_nodes:
            return
        preferred_device = video_nodes[0]
        cameras.append(
            {
                "device": preferred_device,
                "index": _parse_camera_index(preferred_device),
                "name": current_name,
                "usb_id": current_usb_id,
                "menu_label": _get_camera_menu_label(current_name, current_usb_id),
                "label": _format_camera_label(current_name, current_usb_id, preferred_device),
            }
        )

    for raw_line in result.stdout.splitlines():
        line = raw_line.rstrip()
        if not line:
            flush_current()
            current_name = None
            current_usb_id = ""
            current_devices = []
            continue

        if not line.startswith("\t"):
            flush_current()
            header = line.rstrip(":")
            usb_match = re.search(r"\(([^()]*)\)$", header)
            current_usb_id = usb_match.group(1) if usb_match else ""
            current_name = re.sub(r"\s*\([^()]*\)$", "", header).strip()
            current_devices = []
            continue

        current_devices.append(line.strip())

    flush_current()
    return cameras


def _build_linux_camera_label(video_device: Path) -> Optional[dict]:
    try:
        resolved = video_device.resolve(strict=True)
    except Exception:
        return None

    name_path = Path("/sys/class/video4linux") / video_device.name / "name"
    try:
        camera_name = name_path.read_text(encoding="utf-8").strip()
    except Exception:
        camera_name = video_device.name

    usb_match = re.search(r"(usb-[^/]+)", str(resolved))
    usb_id = usb_match.group(1) if usb_match else ""
    return {
        "device": str(video_device),
        "index": _parse_camera_index(str(video_device)),
        "name": camera_name,
        "usb_id": usb_id,
        "menu_label": _get_camera_menu_label(camera_name, usb_id),
        "label": _format_camera_label(camera_name, usb_id, video_device),
    }


def list_available_cameras() -> list[dict]:
    cameras = _list_cameras_from_v4l2()
    if cameras:
        return cameras

    discovered = []
    if sys.platform.startswith("linux"):
        for video_device in sorted(Path("/dev").glob("video*")):
            camera = _build_linux_camera_label(video_device)
            if camera is not None:
                discovered.append(camera)

    if discovered:
        return discovered

    return [
        {
            "device": index,
            "index": index,
            "name": f"Camera {index}",
            "usb_id": "",
            "menu_label": f"Camera {index}",
            "label": f"Camera index {index}",
        }
        for index in range(8)
    ]


def _select_camera(cameras: list[dict]):
    if len(cameras) == 1:
        return cameras[0]

    root = tk.Tk()
    root.withdraw()
    dialog = tk.Toplevel(root)
    dialog.title("Select Camera")
    dialog.attributes("-topmost", True)
    dialog.resizable(False, False)
    dialog.grab_set()

    selected_device = tk.StringVar(value=str(cameras[0]["device"]))
    result = {"camera": None}

    container = tk.Frame(dialog, padx=14, pady=12)
    container.pack(fill="both", expand=True)

    tk.Label(
        container,
        text="Choose the webcam for visual inspection.",
        font=("Segoe UI", 11, "bold"),
        anchor="w",
        justify="left",
    ).pack(anchor="w")
    tk.Label(
        container,
        text="Each option shows the camera name, USB port ID, and selected /dev/video node.",
        anchor="w",
        justify="left",
        wraplength=560,
    ).pack(anchor="w", pady=(6, 10))

    for camera in cameras:
        tk.Radiobutton(
            container,
            text=camera["label"],
            variable=selected_device,
            value=str(camera["device"]),
            anchor="w",
            justify="left",
            padx=4,
        ).pack(anchor="w", fill="x", pady=2)

    button_row = tk.Frame(container)
    button_row.pack(fill="x", pady=(12, 0))

    def on_confirm():
        for camera in cameras:
            if str(camera["device"]) == selected_device.get():
                result["camera"] = camera
                break
        dialog.destroy()

    def on_cancel():
        dialog.destroy()

    tk.Button(button_row, text="Open Camera", command=on_confirm).pack(side="left")
    tk.Button(button_row, text="Cancel", command=on_cancel).pack(side="left", padx=(8, 0))
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    dialog.update_idletasks()
    dialog.geometry(f"+{max(60, dialog.winfo_screenwidth() // 4)}+{max(60, dialog.winfo_screenheight() // 5)}")
    root.wait_window(dialog)
    root.destroy()
    return result["camera"]


def _open_camera(device_ref):
    """Open the camera with a small backend preference list per platform."""
    backends = []
    device_index = _parse_camera_index(device_ref)

    if sys.platform == "win32" and hasattr(cv2, "CAP_DSHOW"):
        backends.append(("DirectShow", cv2.CAP_DSHOW))
    if sys.platform == "win32" and hasattr(cv2, "CAP_MSMF"):
        backends.append(("Media Foundation", cv2.CAP_MSMF))
    if sys.platform.startswith("linux") and hasattr(cv2, "CAP_V4L2"):
        backends.append(("V4L2", cv2.CAP_V4L2))
    backends.append(("Default backend", cv2.CAP_ANY))

    last_error = None
    for backend_name, backend in backends:
        try:
            source = device_ref if isinstance(device_ref, str) else device_index
            cap = cv2.VideoCapture(source, backend)
        except Exception as exc:
            last_error = exc
            continue

        if not cap or not cap.isOpened():
            if cap:
                cap.release()
            continue

        # Ask the camera for MJPG first; many USB webcams negotiate this faster.
        try:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        except Exception:
            pass

        # A tiny warm-up read confirms the backend really works before we commit.
        ok, _ = cap.read()
        if ok:
            return cap, backend_name

        cap.release()

    if last_error is not None:
        raise RuntimeError(f"Unable to open camera {device_ref}: {last_error}") from last_error
    raise RuntimeError(f"Unable to open camera {device_ref}.")


def _confirm_close_visual_inspection() -> bool:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        return messagebox.askyesno(
            "Confirm Exit",
            "Are you sure you want to close the visual inspection window?",
            parent=root,
        )
    finally:
        root.destroy()

# Define the dictionary of markers you are using.
aruco_dict = _get_predefined_dict(aruco.DICT_ARUCO_ORIGINAL)

# Define the parameters for the ArUco marker detection.
parameters = _create_detector_params()

def run_visual_inspection(participant_id: str, trial_number: str, camera_device=None) -> None:
    participant_id = participant_id or "participant"
    trial_number = trial_number or "trial"
    window_name = "Visual Inspection"
    initial_width = 620
    initial_height = 430

    # Assign each of 8 markers (ID 0-7) a stable random color with a bias toward green
    # and a hard cap of 3 red markers. We iterate in random order so IDs that go red
    # change run to run, but stop once three reds are chosen.
    marker_ids = list(range(8))
    random.shuffle(marker_ids)
    marker_colors = {}
    max_red = 3
    red_count = 0
    red_bias = 0.3  # probability threshold for picking red until the cap is reached

    for marker_id in marker_ids:
        if red_count < max_red and random.random() < red_bias:
            marker_colors[marker_id] = (0, 0, 255)  # red
            red_count += 1
        else:
            marker_colors[marker_id] = (0, 255, 0)  # green

    # Export the random assignments for later reference into a participant subfolder.
    csv_dir = get_participant_dir(participant_id)
    csv_dir.mkdir(parents=True, exist_ok=True)
    color_csv = csv_dir / f"visual_{participant_id}_{trial_number}.csv"
    with color_csv.open("w", encoding="utf-8", newline="") as color_file:
        color_file.write("marker_id,color_name\n")
        for marker_id, (b, g, r) in sorted(marker_colors.items()):
            color_name = "red" if (b, g, r) == (0, 0, 255) else "green"
            color_file.write(f"{marker_id},{color_name}\n")

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.imshow(window_name, _build_waiting_frame(window_name))
    _position_window_on_right(window_name, initial_width, initial_height)
    _bring_window_to_front(window_name)
    cv2.waitKey(1)

    if camera_device:
        selected_camera = None
        for camera in list_available_cameras():
            if str(camera["device"]) == str(camera_device):
                selected_camera = camera
                break
        if selected_camera is None:
            selected_camera = {
                "device": camera_device,
                "index": _parse_camera_index(camera_device),
                "name": "Selected Camera",
                "usb_id": "",
            }
    else:
        cameras = list_available_cameras()
        selected_camera = _select_camera(cameras)
        if selected_camera is None:
            cv2.destroyAllWindows()
            raise SystemExit("Visual inspection cancelled before opening a camera.")

    # Start the webcam feed using the selected device path or fallback index.
    try:
        cap, backend_name = _open_camera(selected_camera["device"])
    except RuntimeError as exc:
        cv2.destroyAllWindows()
        raise SystemExit(str(exc)) from exc

    # Variables to keep track of marker visibility times and the current marker ID
    marker_detected_at = None
    visibility_intervals = []
    current_marker_id = None  # Variable to store the marker ID when detected
    window_brought_forward = False
    pending_close_confirmation = False
    last_frame = _build_waiting_frame(window_name)
    try:
        camera_label = selected_camera["usb_id"] or str(selected_camera["device"])
        cv2.displayOverlay(window_name, f"{selected_camera['name']} via {backend_name} ({camera_label})", 2000)
    except Exception:
        pass

    while True:
        # Capture frame-by-frame
        ret, frame = cap.read()
        if not ret:
            break

        # Our operations on the frame come here
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect the markers in the image
        corners, ids, rejectedImgPoints = _detect_markers(gray, aruco_dict, parameters)

        # If any markers were found, draw them on the frame with assigned colors
        if ids is not None:
            for marker_corners, marker_id in zip(corners, ids.flatten()):
                color = marker_colors.get(marker_id, (255, 255, 255))  # default white if out of range
                pts = marker_corners.reshape((4, 2)).astype(int)
                cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=3, lineType=cv2.LINE_AA)
                # Place ID label near the top-left corner of the marker
                cv2.putText(frame, f"ID {marker_id}", tuple(pts[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
            if marker_detected_at is None:  # If the marker was not detected before
                marker_detected_at = time.time()
                current_marker_id = ids[0][0]  # Store the marker ID when detected
        else:
            if marker_detected_at is not None:  # If the marker was detected earlier, but not now
                marker_end_time = time.time()
                visibility_intervals.append((marker_detected_at, marker_end_time, current_marker_id))
                marker_detected_at = None
                current_marker_id = None

        # Display the resulting frame
        last_frame = frame
        cv2.imshow(window_name, frame)
        if not window_brought_forward:
            _bring_window_to_front(window_name)
            window_brought_forward = True

        cv2.waitKey(1)
        try:
            window_visible = cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) >= 1
        except Exception:
            window_visible = False

        if not window_visible and not pending_close_confirmation:
            pending_close_confirmation = True
            if _confirm_close_visual_inspection():
                break
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            _position_window_on_right(window_name, initial_width, initial_height)
            cv2.imshow(window_name, last_frame)
            _bring_window_to_front(window_name)
            cv2.waitKey(1)
            pending_close_confirmation = False

    # Handle the case when the marker is still visible when the video feed ends
    if marker_detected_at is not None:
        marker_end_time = time.time()
        visibility_intervals.append((marker_detected_at, marker_end_time, current_marker_id))

    # When everything done, release the capture
    cap.release()
    cv2.destroyAllWindows()


def _parse_args():
    parser = argparse.ArgumentParser(description="Visual inspection GUI")
    parser.add_argument("--participant", default="", help="Participant ID")
    parser.add_argument("--trial", default="", help="Trial number")
    parser.add_argument("--camera", default="", help="Camera device path or index")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    participant_id = args.participant
    trial_number = args.trial

    if not participant_id or not trial_number:
        raise SystemExit("Participant ID and trial number must be provided by the combined GUI.")

    camera_device = args.camera.strip() or None
    run_visual_inspection(participant_id, trial_number, camera_device)
