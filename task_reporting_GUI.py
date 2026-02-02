"""
Task reporting GUI that preloads visual inspection results and scores entries.
"""

import csv
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox


MAX_LOCATION_PARTS = 8  # kept for CSV shape (locations unused now)


def prompt_session_ids():
    """Ask participant and trial IDs together before the main window."""
    try:
        import tkinter as tk

        result = {"participant": "", "trial": ""}

        def on_submit():
            result["participant"] = participant_entry.get().strip()
            result["trial"] = trial_entry.get().strip()
            window.destroy()

        window = tk.Tk()
        window.title("Session Info")
        window.geometry("280x200")
        window.resizable(False, False)

        tk.Label(window, text="Participant ID:").pack(pady=(12, 2))
        participant_entry = tk.Entry(window)
        participant_entry.pack()
        participant_entry.focus()

        tk.Label(window, text="Trial number:").pack(pady=(10, 2))
        trial_entry = tk.Entry(window)
        trial_entry.pack()

        tk.Button(window, text="Start", command=on_submit).pack(pady=12)

        window.mainloop()
        return result["participant"] or "participant", result["trial"] or "trial"
    except Exception:
        return "participant", "trial"


def load_reference(participant_id: str, trial_id: str):
    """Load the visual output CSV and derive expected marker colors/crack info."""
    csv_dir = Path(__file__).with_name("CSV")
    csv_path = csv_dir / f"visual_{participant_id}_{trial_id}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Expected file not found: {csv_path.name}")

    red_markers = []
    marker_colors = {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                mid = int((row.get("marker_id") or "").strip())
            except ValueError:
                continue
            color = (row.get("color_name") or "").strip().lower()
            marker_colors[mid] = color
            if color == "red":
                red_markers.append(mid)

    return {
        "path": csv_path,
        "red_markers": red_markers,
        "marker_colors": marker_colors,
        "all_markers": sorted(marker_colors.keys()),
        "expected_crack": 1 if red_markers else 0,
    }


def load_leak_reference(participant_id: str, trial_id: str):
    """Load the leak reference CSV; file stores 1 or 0 indicating leak presence."""
    csv_dir = Path(__file__).with_name("CSV")
    csv_path = csv_dir / f"leak_{participant_id}_{trial_id}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Expected file not found: {csv_path.name}")

    expected_leak = 0
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Try keys that likely encode leak state; fall back to first numeric value.
            for key, val in row.items():
                if val is None:
                    continue
                v = val.strip()
                if v in ("0", "1"):
                    expected_leak = int(v)
                    break
            else:
                continue
            break

    return {"path": csv_path, "expected_leak": expected_leak}


class TaskReportingApp(tk.Tk):
    def __init__(self, participant_id: str, trial_id: str, reference, leak_reference, data_file: Path) -> None:
        super().__init__()
        self.title("Pipe Inspection Task Reporting")
        self.geometry("620x520")
        self.resizable(False, False)

        self.participant_var = tk.StringVar(value=participant_id)
        self.trial_var = tk.StringVar(value=trial_id)
        self.leak_var = tk.IntVar(value=-1)
        self.crack_var = tk.IntVar(value=-1)
        self.reference = reference  # dict with expected_crack, marker_colors
        self.leak_reference = leak_reference  # dict with expected_leak
        self.marker_vars = {mid: tk.StringVar(value="") for mid in reference["all_markers"]}
        self.data_file = data_file

        self._build_ui()

    def _build_ui(self) -> None:
        header = tk.Label(
            self,
            text="Record Inspection Outcome",
            font=("Segoe UI", 16, "bold"),
            pady=10,
        )
        header.pack()

        form = tk.Frame(self, padx=16, pady=8)
        form.pack(fill="both", expand=True)

        # Participant identifier
        tk.Label(form, text="Participant ID").grid(row=0, column=0, sticky="w")
        tk.Entry(form, textvariable=self.participant_var, width=20, state="readonly").grid(row=0, column=1, sticky="w")

        # Trial identifier
        tk.Label(form, text="Trial ID").grid(row=1, column=0, sticky="w", pady=(8, 0))
        tk.Entry(form, textvariable=self.trial_var, width=20, state="readonly").grid(row=1, column=1, sticky="w", pady=(8, 0))

        # Leak detection (0 or 1)
        tk.Label(form, text="Leak present (0/1)").grid(row=2, column=0, sticky="w", pady=(12, 0))
        leak_frame = tk.Frame(form)
        leak_frame.grid(row=2, column=1, sticky="w", pady=(12, 0))
        tk.Radiobutton(leak_frame, text="0 = No leak", variable=self.leak_var, value=0).pack(side="left")
        tk.Radiobutton(leak_frame, text="1 = Leak", variable=self.leak_var, value=1).pack(side="left", padx=(8, 0))

        # Crack presence (0 or 1)
        tk.Label(form, text="Crack present (0/1)").grid(row=3, column=0, sticky="w", pady=(12, 0))
        crack_frame = tk.Frame(form)
        crack_frame.grid(row=3, column=1, sticky="w", pady=(12, 0))
        tk.Radiobutton(crack_frame, text="0 = No crack", variable=self.crack_var, value=0).pack(side="left")
        tk.Radiobutton(crack_frame, text="1 = Crack", variable=self.crack_var, value=1).pack(side="left", padx=(8, 0))

        # Marker-by-marker color selection
        tk.Label(form, text="Select marker colors").grid(row=4, column=0, sticky="nw", pady=(12, 0))
        markers_frame = tk.Frame(form)
        markers_frame.grid(row=4, column=1, columnspan=3, sticky="w", pady=(12, 0))

        for idx, marker_id in enumerate(self.reference["all_markers"]):
            row = idx // 4
            col = idx % 4
            slot = tk.Frame(markers_frame, padx=4, pady=4, bd=1, relief="groove")
            slot.grid(row=row, column=col, padx=4, pady=4, sticky="w")
            tk.Label(slot, text=f"ID {marker_id}").pack(anchor="w")
            tk.Radiobutton(slot, text="Green", variable=self.marker_vars[marker_id], value="green").pack(anchor="w")
            tk.Radiobutton(slot, text="Red", variable=self.marker_vars[marker_id], value="red").pack(anchor="w")

    
        # Buttons
        button_row = tk.Frame(self, pady=12)
        button_row.pack()
        tk.Button(button_row, text="Submit entry", command=self.submit).pack(side="left", padx=6)
        tk.Button(button_row, text="Clear form", command=self.clear_form).pack(side="left", padx=6)

        # Status
        self.status = tk.Label(self, text="", fg="#2b6a30")
        self.status.pack(pady=(4, 0))

    def clear_form(self) -> None:
        self.leak_var.set(-1)
        self.crack_var.set(-1)
        for var in self.marker_vars.values():
            var.set("")
        self.status.config(text="")

    def submit(self) -> None:
        participant = self.participant_var.get().strip() or "N/A"
        trial = self.trial_var.get().strip() or "N/A"
        leak = self.leak_var.get()
        crack = self.crack_var.get()
        location = ""  # locations unused in marker-based flow

        # Validation
        if leak not in (0, 1):
            messagebox.showerror("Missing data", "Please select 0 or 1 for leak.")
            return
        if crack not in (0, 1):
            messagebox.showerror("Missing data", "Please select 0 or 1 for crack.")
            return
        if any(var.get() not in ("red", "green") for var in self.marker_vars.values()):
            messagebox.showerror("Missing data", "Please select red/green for every marker ID.")
            return

        score_pct = self._score(crack)
        self._append_row(participant, trial, leak, crack, location, score_pct)
        self.status.config(text=f"Saved. Performance: {score_pct:.0f}%")
        self.update_idletasks()
        self.destroy()

    def _append_row(self, participant: str, trial: str, leak: int, crack: int, location: str, score_pct: float) -> None:
        new_file = not self.data_file.exists()
        location_parts = self._split_location(location)
        with self.data_file.open("a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            if new_file:
                writer.writerow(
                    [
                        "timestamp",
                        "participant_id",
                        "trial_id",
                        "leak_present",
                        "crack_present",
                        "score_percent",
                        *[f"marker_{mid}" for mid in self.reference["all_markers"]],
                    ]
                )
            writer.writerow(
                [
                    datetime.now().isoformat(timespec="seconds"),
                    participant,
                    trial,
                    leak,
                    crack,
                    f"{score_pct:.0f}",
                    *[self.marker_vars[mid].get() for mid in self.reference["all_markers"]],
                ]
            )

    def _split_location(self, location: str) -> list[str]:
        """
        Split a space-separated location field into fixed columns.
        Extra tokens are discarded beyond MAX_LOCATION_PARTS.
        """
        tokens = location.split()
        trimmed = tokens[:MAX_LOCATION_PARTS]
        # Pad to fixed width for consistent CSV shape.
        return trimmed + [""] * (MAX_LOCATION_PARTS - len(trimmed))

    def _score(self, crack: int) -> float:
        """Score: leak 33.4%, crack-present 33.3%, all markers correct 33.3%."""
        expected_leak = self.leak_reference["expected_leak"]
        expected_crack = self.reference["expected_crack"]
        expected_colors = self.reference["marker_colors"]

        score = 0.0

        if self.leak_var.get() == expected_leak:
            score += 33.4

        if crack == expected_crack:
            score += 33.3

        markers_match = all(self.marker_vars[mid].get() == expected_colors[mid] for mid in expected_colors)
        if markers_match:
            score += 33.3

        return score


if __name__ == "__main__":
    pid, tid = prompt_session_ids()
    csv_dir = Path(__file__).with_name("CSV")
    csv_dir.mkdir(exist_ok=True)
    data_file = csv_dir / f"results_{pid}_{tid}.csv"
    try:
        reference = load_reference(pid, tid)
        leak_reference = load_leak_reference(pid, tid)
    except FileNotFoundError as exc:
        messagebox.showerror("Missing reference", str(exc))
        raise SystemExit(1)

    app = TaskReportingApp(pid, tid, reference, leak_reference, data_file)
    app.mainloop()
