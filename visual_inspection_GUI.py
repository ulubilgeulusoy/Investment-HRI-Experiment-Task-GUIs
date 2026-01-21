import cv2
import cv2.aruco as aruco
import time
import random
from datetime import datetime

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

# Define the dictionary of markers you are using.
aruco_dict = _get_predefined_dict(aruco.DICT_ARUCO_ORIGINAL)

# Define the parameters for the ArUco marker detection.
parameters = _create_detector_params()


# Assign each of 15 markers (ID 0-14) a stable random color with a bias toward green
# and a hard cap of 3 red markers. We iterate in random order so IDs that go red
# change run to run, but stop once three reds are chosen.
marker_ids = list(range(15))
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

# Export the random assignments for later reference.
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
color_csv = f"marker_color_assignments_{timestamp}.csv"
with open(color_csv, "w") as color_file:
    color_file.write("marker_id,color_name,b,g,r\n")
    for marker_id, (b, g, r) in sorted(marker_colors.items()):
        color_name = "red" if (b, g, r) == (0, 0, 255) else "green"
        color_file.write(f"{marker_id},{color_name}\n")

# Start the webcam feed
cap = cv2.VideoCapture(1)  

# Variables to keep track of marker visibility times and the current marker ID
marker_detected_at = None
visibility_intervals = []
current_marker_id = None  # Variable to store the marker ID when detected

while True:
    # Capture frame-by-frame
    ret, frame = cap.read()
    if not ret:
        break

    # Our operations on the frame come here
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Detect the markers in the image
    corners, ids, rejectedImgPoints = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

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
    cv2.imshow('frame', frame)
    cv2.moveWindow('frame', 100, 100)  # This moves the window to (100, 100) coordinates

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Handle the case when the marker is still visible when the video feed ends
if marker_detected_at is not None:
    marker_end_time = time.time()
    visibility_intervals.append((marker_detected_at, marker_end_time, current_marker_id))

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
