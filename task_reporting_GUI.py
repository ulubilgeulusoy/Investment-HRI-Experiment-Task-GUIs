"""
Simple task reporting GUI for pipe inspection experiments.

Participants can record leak and crack presence (0 or 1) and optionally
describe crack locations. Entries are appended to a CSV file for later
analysis.
"""

import csv
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox


RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
DATA_FILE = Path(__file__).with_name(f"experiment_responses_{RUN_TIMESTAMP}.csv")
MAX_LOCATION_PARTS = 8  # split space-separated entries into separate cells


class TaskReportingApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Pipe Inspection Task Reporting")
        self.geometry("520x420")
        self.resizable(False, False)

        self.participant_var = tk.StringVar()
        self.trial_var = tk.StringVar()
        self.leak_var = tk.IntVar(value=-1)
        self.crack_var = tk.IntVar(value=-1)

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
        tk.Entry(form, textvariable=self.participant_var, width=20).grid(row=0, column=1, sticky="w")

        # Trial identifier
        tk.Label(form, text="Trial ID").grid(row=1, column=0, sticky="w", pady=(8, 0))
        tk.Entry(form, textvariable=self.trial_var, width=20).grid(row=1, column=1, sticky="w", pady=(8, 0))

        # Leak detection (0 or 1)
        tk.Label(form, text="Leak present (0/1)").grid(row=2, column=0, sticky="w", pady=(12, 0))
        leak_frame = tk.Frame(form)
        leak_frame.grid(row=2, column=1, sticky="w", pady=(12, 0))
        tk.Radiobutton(leak_frame, text="0 = No leak", variable=self.leak_var, value=0).pack(
            side="left"
        )
        tk.Radiobutton(leak_frame, text="1 = Leak", variable=self.leak_var, value=1).pack(
            side="left", padx=(8, 0)
        )

        # Crack detection (0 or 1)
        tk.Label(form, text="Crack present (0/1)").grid(row=3, column=0, sticky="w", pady=(12, 0))
        crack_frame = tk.Frame(form)
        crack_frame.grid(row=3, column=1, sticky="w", pady=(12, 0))
        tk.Radiobutton(crack_frame, text="0 = No crack", variable=self.crack_var, value=0).pack(
            side="left"
        )
        tk.Radiobutton(crack_frame, text="1 = Crack", variable=self.crack_var, value=1).pack(
            side="left", padx=(8, 0)
        )

        # Crack location free text
        tk.Label(form, text="Crack location(s)").grid(row=4, column=0, sticky="nw", pady=(12, 0))
        self.location_text = tk.Text(form, height=5, width=40, wrap="word")
        self.location_text.grid(row=4, column=1, sticky="w", pady=(12, 0))

        # Buttons
        button_row = tk.Frame(self, pady=12)
        button_row.pack()
        tk.Button(button_row, text="Submit entry", command=self.submit).pack(side="left", padx=6)
        tk.Button(button_row, text="Clear form", command=self.clear_form).pack(side="left", padx=6)

        # Status
        self.status = tk.Label(self, text="", fg="#2b6a30")
        self.status.pack(pady=(4, 0))

    def clear_form(self) -> None:
        self.participant_var.set("")
        self.trial_var.set("")
        self.leak_var.set(-1)
        self.crack_var.set(-1)
        self.location_text.delete("1.0", tk.END)
        self.status.config(text="")

    def submit(self) -> None:
        participant = self.participant_var.get().strip() or "N/A"
        trial = self.trial_var.get().strip() or "N/A"
        leak = self.leak_var.get()
        crack = self.crack_var.get()
        location = self.location_text.get("1.0", tk.END).strip()

        # Basic validation: leak and crack must be 0 or 1.
        if leak not in (0, 1) or crack not in (0, 1):
            messagebox.showerror("Missing data", "Please select 0 or 1 for leak and crack.")
            return

        # If crack is present, encourage entering a location.
        if crack == 1 and not location:
            if not messagebox.askyesno(
                "No location provided",
                "Crack marked as present but no location was entered. Submit anyway?",
            ):
                return

        self._append_row(participant, trial, leak, crack, location)
        self.status.config(text="Saved entry to experiment_responses.csv")
        self.clear_form()

    def _append_row(self, participant: str, trial: str, leak: int, crack: int, location: str) -> None:
        new_file = not DATA_FILE.exists()
        location_parts = self._split_location(location)
        with DATA_FILE.open("a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            if new_file:
                writer.writerow(
                    [
                        "timestamp",
                        "participant_id",
                        "trial_id",
                        "leak_present",
                        "crack_present",
                        "crack_location_raw",
                        *[f"crack_location_part_{i+1}" for i in range(MAX_LOCATION_PARTS)],
                    ]
                )
            writer.writerow(
                [
                    datetime.now().isoformat(timespec="seconds"),
                    participant,
                    trial,
                    leak,
                    crack,
                    location,
                    *location_parts,
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


if __name__ == "__main__":
    app = TaskReportingApp()
    app.mainloop()
