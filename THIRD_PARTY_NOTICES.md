# Third-Party Notices

This repository uses or interfaces with third-party packages and tools. Each dependency is governed by its own license terms.

## Dependencies in `requirements.txt`

| Component | License | Notes |
|---|---|---|
| opencv-contrib-python / OpenCV | See upstream project license terms | Used for webcam-based ArUco marker detection and visualization. |
| paramiko | See upstream project license terms | Used for SSH communication with the Raspberry Pi. |

## Raspberry Pi script dependencies documented in README

The README includes a Raspberry Pi script example (`code_investment.py`) that references additional packages and hardware libraries not listed in the root `requirements.txt`.

| Component | License | Notes |
|---|---|---|
| Adafruit MPR121 examples/library | MIT | The README script block preserves SPDX attribution and license lines from Adafruit/Tony DiCola example code context. |
| pygame | See upstream project license terms | Used in the Pi-side script for audio playback. |
| pydub | See upstream project license terms | Used in the Pi-side script for audio processing/playback. |
| Python / tkinter | See upstream project license terms | `tkinter` is typically part of standard Python installations. |

This notice is provided for source-repository documentation. If distributing a bundled executable, Python environment, Raspberry Pi image, or installer, review and include the full license texts for bundled third-party components.
