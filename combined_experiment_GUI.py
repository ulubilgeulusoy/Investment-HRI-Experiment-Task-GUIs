import shlex
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import paramiko


class SSHManager:
    def __init__(self):
        self.client = None
        self.connected = False

    def connect(self, host, port, username, password):
        self.disconnect()

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=host,
            port=int(port),
            username=username,
            password=password,
            timeout=10,
            look_for_keys=False,
            allow_agent=False,
        )

        self.client = client
        self.connected = True

    def exec(self, command):
        if not self.connected or self.client is None:
            raise RuntimeError("SSH is not connected.")

        stdin, stdout, stderr = self.client.exec_command(command)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        exit_status = stdout.channel.recv_exit_status()
        return out, err, exit_status

    def disconnect(self):
        if self.client is not None:
            try:
                self.client.close()
            except Exception:
                pass
        self.client = None
        self.connected = False

    def __del__(self):
        self.disconnect()


class CombinedExperimentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HRI Task GUI")
        self.root.geometry("1200x840")
        self.root.minsize(1040, 760)

        self.base_dir = Path(__file__).resolve().parent
        self.visual_script = self.base_dir / "combined_visual_inspection_GUI.py"
        self.reporting_script = self.base_dir / "combined_task_reporting_GUI.py"

        self.ssh = SSHManager()

        self.ssh_host = tk.StringVar(value="192.168.0.148")
        self.ssh_port = tk.StringVar(value="22")
        self.ssh_user = tk.StringVar(value="homemicro")
        self.ssh_password = tk.StringVar(value="")

        self.conda_sh = tk.StringVar(value="/home/homemicro/miniconda3/etc/profile.d/conda.sh")
        self.conda_env = tk.StringVar(value="chrps")
        self.remote_dir = tk.StringVar(
            value="/home/homemicro/Investment Experiment/Investment Buzz Wire (old chrps folder)"
        )
        self.script_name = tk.StringVar(value="code_investment.py")
        self.windows_host = tk.StringVar(value="192.168.0.51")
        self.windows_share = tk.StringVar(value="CSV")
        self.windows_user = tk.StringVar(value="Investment")
        self.windows_password = tk.StringVar(value="")
        self.mount_point = tk.StringVar(value="/mnt/csv")
        self.mount_version = tk.StringVar(value="3.0")

        self.participant_id = tk.StringVar(value="")
        self.trial_number = tk.StringVar(value="1")

        self.pid_file = tk.StringVar(value="/tmp/raspi_investment.pid")
        self.log_file = tk.StringVar(value="/tmp/raspi_investment.log")

        self.status_text = tk.StringVar(value="Stage 1: connect to the Raspberry Pi and mount the share")
        self.stage_text = tk.StringVar(value="SSH + Mount Setup")
        self.ssh_state_text = tk.StringVar(value="Inactive")
        self.mount_state_text = tk.StringVar(value="Inactive")
        self.auto_refresh_job = None
        self.stage_two_ready = False
        self.mount_active = False
        self.ssh_status_label = None
        self.mount_status_label = None
        self.continue_button = None
        self.start_leak_button = None
        self.start_visual_button = None
        self.start_reporting_button = None
        self.leak_start_locked = False
        self.visual_process = None
        self.reporting_process = None

        self.main_frame = ttk.Frame(self.root, padding=15)
        self.main_frame.pack(fill="both", expand=True)

        title_row = ttk.Frame(self.main_frame)
        title_row.pack(fill="x", pady=(0, 12))
        ttk.Label(
            title_row,
            text="HRI Task GUI",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")
        ttk.Label(title_row, textvariable=self.stage_text, font=("Segoe UI", 11, "bold")).pack(side="left", padx=(16, 0))
        ttk.Label(title_row, textvariable=self.status_text).pack(side="right")

        self.stage_canvas = tk.Canvas(self.main_frame, highlightthickness=0)
        self.stage_scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.stage_canvas.yview)
        self.stage_canvas.configure(yscrollcommand=self.stage_scrollbar.set)
        self.stage_canvas.pack(side="left", fill="both", expand=True)
        self.stage_scrollbar.pack(side="right", fill="y")

        self.stage_container = ttk.Frame(self.stage_canvas)
        self.stage_canvas_window = self.stage_canvas.create_window((0, 0), window=self.stage_container, anchor="nw")
        self.stage_container.bind("<Configure>", self._on_stage_container_configure)
        self.stage_canvas.bind("<Configure>", self._on_stage_canvas_configure)
        self.stage_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.stage_one_frame = ttk.Frame(self.stage_container, padding=(0, 0, 6, 12))
        self.stage_two_frame = ttk.Frame(self.stage_container, padding=(0, 0, 6, 12))
        self.log_text_widgets = []

        self._build_stage_one()
        self._build_stage_two()
        self._show_stage_one()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_stage_one(self):
        frame = self.stage_one_frame

        intro = (
            "Stage 1 finishes the Raspberry Pi setup before any participant session starts. "
            "Use this page to connect over SSH and mount the Windows CSV share."
        )
        ttk.Label(frame, text=intro, wraplength=920, justify="left").pack(anchor="w", pady=(0, 8))

        ssh_frame = ttk.LabelFrame(frame, text="SSH Connection", padding=12)
        ssh_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(ssh_frame, text="Host").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(ssh_frame, textvariable=self.ssh_host, width=32).grid(row=0, column=1, sticky="ew", padx=8, pady=5)
        ttk.Label(ssh_frame, text="Port").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(ssh_frame, textvariable=self.ssh_port, width=32).grid(row=1, column=1, sticky="ew", padx=8, pady=5)
        ttk.Label(ssh_frame, text="Username").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(ssh_frame, textvariable=self.ssh_user, width=32).grid(row=2, column=1, sticky="ew", padx=8, pady=5)
        ttk.Label(ssh_frame, text="Password").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(ssh_frame, textvariable=self.ssh_password, width=32, show="*").grid(
            row=3, column=1, sticky="ew", padx=8, pady=5
        )

        ssh_buttons = ttk.Frame(ssh_frame)
        ssh_buttons.grid(row=0, column=2, rowspan=4, sticky="ns", padx=(12, 0))
        ttk.Button(ssh_buttons, text="Test Connection", command=self.test_connection).pack(fill="x", pady=(0, 8))
        ttk.Button(ssh_buttons, text="Disconnect", command=self.disconnect_ssh).pack(fill="x")
        self.ssh_status_label = tk.Label(ssh_buttons, textvariable=self.ssh_state_text, fg="#b00020")
        self.ssh_status_label.pack(anchor="center", pady=(10, 0))
        ssh_frame.columnconfigure(1, weight=1)

        remote_frame = ttk.LabelFrame(frame, text="Remote Script Setup", padding=12)
        remote_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(remote_frame, text="Conda Init").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(remote_frame, textvariable=self.conda_sh).grid(row=0, column=1, sticky="ew", padx=8, pady=5)
        ttk.Label(remote_frame, text="Conda Env").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(remote_frame, textvariable=self.conda_env).grid(row=1, column=1, sticky="ew", padx=8, pady=5)
        ttk.Label(remote_frame, text="Remote Folder").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(remote_frame, textvariable=self.remote_dir).grid(row=2, column=1, sticky="ew", padx=8, pady=5)
        ttk.Label(remote_frame, text="Script Name").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(remote_frame, textvariable=self.script_name).grid(row=3, column=1, sticky="ew", padx=8, pady=5)
        ttk.Label(remote_frame, text="PID File").grid(row=4, column=0, sticky="w", pady=5)
        ttk.Entry(remote_frame, textvariable=self.pid_file).grid(row=4, column=1, sticky="ew", padx=8, pady=5)
        ttk.Label(remote_frame, text="Log File").grid(row=5, column=0, sticky="w", pady=5)
        ttk.Entry(remote_frame, textvariable=self.log_file).grid(row=5, column=1, sticky="ew", padx=8, pady=5)
        remote_frame.columnconfigure(1, weight=1)

        mount_frame = ttk.LabelFrame(frame, text="Windows Share Mount", padding=12)
        mount_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(mount_frame, text="Windows Host").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(mount_frame, textvariable=self.windows_host, width=24).grid(row=0, column=1, sticky="ew", padx=8, pady=5)
        ttk.Label(mount_frame, text="Share Name").grid(row=0, column=2, sticky="w", pady=5)
        ttk.Entry(mount_frame, textvariable=self.windows_share, width=20).grid(row=0, column=3, sticky="ew", padx=8, pady=5)
        ttk.Label(mount_frame, text="Windows User").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(mount_frame, textvariable=self.windows_user, width=24).grid(row=1, column=1, sticky="ew", padx=8, pady=5)
        ttk.Label(mount_frame, text="Windows Password").grid(row=1, column=2, sticky="w", pady=5)
        ttk.Entry(mount_frame, textvariable=self.windows_password, width=20, show="*").grid(
            row=1, column=3, sticky="ew", padx=8, pady=5
        )
        ttk.Label(mount_frame, text="Mount Point").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(mount_frame, textvariable=self.mount_point, width=24).grid(row=2, column=1, sticky="ew", padx=8, pady=5)
        ttk.Label(mount_frame, text="SMB Version").grid(row=2, column=2, sticky="w", pady=5)
        ttk.Entry(mount_frame, textvariable=self.mount_version, width=20).grid(row=2, column=3, sticky="ew", padx=8, pady=5)
        mount_buttons = ttk.Frame(mount_frame)
        mount_buttons.grid(row=0, column=4, rowspan=3, sticky="ns", padx=(16, 0), pady=5)
        ttk.Button(mount_buttons, text="Mount Share", command=self.mount_share).pack(fill="x")
        ttk.Button(mount_buttons, text="Check Mount Status", command=self.refresh_mount_status).pack(fill="x", pady=(6, 0))
        ttk.Button(mount_buttons, text="Dismount", command=self.dismount_share).pack(fill="x", pady=(6, 0))
        self.mount_status_label = tk.Label(mount_buttons, textvariable=self.mount_state_text, fg="#b00020")
        self.mount_status_label.pack(anchor="center", pady=(8, 0))

        for column in (1, 3):
            mount_frame.columnconfigure(column, weight=1)

        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(6, 8))
        self.continue_button = ttk.Button(
            actions,
            text="Continue to Session Controls",
            command=self.complete_stage_one,
            state="disabled",
        )
        self.continue_button.pack(side="right")

        log_frame = ttk.LabelFrame(frame, text="Setup Log", padding=10)
        log_frame.pack(fill="both", expand=True)
        self._build_log_widget(log_frame, height=12)

    def _build_stage_two(self):
        frame = self.stage_two_frame

        session_frame = ttk.LabelFrame(frame, text="Session Setup", padding=12)
        session_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(session_frame, text="Participant ID").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(session_frame, textvariable=self.participant_id, width=18).grid(row=0, column=1, sticky="w", padx=8, pady=5)
        ttk.Label(session_frame, text="Trial Number").grid(row=0, column=2, sticky="w", pady=5)
        ttk.Entry(session_frame, textvariable=self.trial_number, width=12).grid(row=0, column=3, sticky="w", padx=8, pady=5)
        ttk.Button(session_frame, text="Back to SSH Setup", command=self._show_stage_one).grid(row=0, column=4, sticky="e", padx=(20, 0))
        session_frame.columnconfigure(4, weight=1)

        launch_frame = ttk.LabelFrame(frame, text="Task Launchers", padding=12)
        launch_frame.pack(fill="x", pady=(0, 10))

        leak_frame = ttk.LabelFrame(launch_frame, text="Leak Check", padding=10)
        leak_frame.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.start_leak_button = ttk.Button(leak_frame, text="Start Leak Check", command=self.start_experiment)
        self.start_leak_button.pack(fill="x", pady=(0, 8))
        ttk.Button(leak_frame, text="Quit Leak Check", command=self.kill_experiment).pack(fill="x")

        visual_frame = ttk.LabelFrame(launch_frame, text="Visual Inspection", padding=10)
        visual_frame.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        self.start_visual_button = ttk.Button(
            visual_frame,
            text="Start Visual Inspection",
            command=self.launch_visual_inspection,
        )
        self.start_visual_button.pack(fill="x")

        reporting_frame = ttk.LabelFrame(launch_frame, text="Task Reporting", padding=10)
        reporting_frame.grid(row=0, column=2, sticky="nsew", padx=6, pady=6)
        self.start_reporting_button = ttk.Button(
            reporting_frame,
            text="Start Task Reporting",
            command=self.launch_task_reporting,
        )
        self.start_reporting_button.pack(fill="x")

        for column in range(3):
            launch_frame.columnconfigure(column, weight=1)

        log_frame = ttk.LabelFrame(frame, text="Leak Check Log", padding=10)
        log_frame.pack(fill="both", expand=True)
        self._build_log_widget(log_frame, height=24)

    def _build_log_widget(self, parent, height):
        log_text = tk.Text(parent, wrap="none", height=height, font=("Consolas", 10))
        log_text.grid(row=0, column=0, sticky="nsew")

        y_scroll = ttk.Scrollbar(parent, orient="vertical", command=log_text.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")

        x_scroll = ttk.Scrollbar(parent, orient="horizontal", command=log_text.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")

        log_text.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        self.log_text_widgets.append(log_text)

    def _show_stage_one(self):
        self.stage_two_frame.pack_forget()
        self.stage_one_frame.pack(fill="both", expand=True)
        self.stage_text.set("SSH + Mount Setup")
        self.root.after(0, lambda: self.stage_canvas.yview_moveto(0))
        if self.stage_two_ready:
            self.status_text.set("Stage 1 ready to revisit; stage 2 data is preserved")

    def _show_stage_two(self):
        self.stage_one_frame.pack_forget()
        self.stage_two_frame.pack(fill="both", expand=True)
        self.stage_text.set("Session Controls")
        self.status_text.set("Stage 2: enter participant/trial values and launch tasks")
        self.stage_two_ready = True
        self.root.after(0, lambda: self.stage_canvas.yview_moveto(0))

    def _on_stage_container_configure(self, event):
        self.stage_canvas.configure(scrollregion=self.stage_canvas.bbox("all"))

    def _on_stage_canvas_configure(self, event):
        self.stage_canvas.itemconfigure(self.stage_canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        if self.stage_canvas.winfo_exists():
            self.stage_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def append_log(self, text):
        for widget in self.log_text_widgets:
            widget.insert("end", text)
            widget.see("end")

    def clear_log(self):
        for widget in self.log_text_widgets:
            widget.delete("1.0", "end")

    def run_ssh_command_async(self, command, label=None, on_success=None):
        def worker():
            try:
                out, err, code = self.ssh.exec(command)
                msg = f"[{label}] exit={code}\n" if label else f"[command] exit={code}\n"
                if out:
                    msg += "--- stdout ---\n"
                    msg += out if out.endswith("\n") else out + "\n"
                if err:
                    msg += "--- stderr ---\n"
                    msg += err if err.endswith("\n") else err + "\n"
                if not out and not err:
                    msg += "(no output)\n"

                self.root.after(0, lambda: self.append_log(msg + "\n"))
                if code != 0 and label:
                    self.root.after(0, lambda: self.status_text.set(f"{label} failed"))
                if on_success is not None:
                    self.root.after(0, lambda: on_success(code, out, err))
            except Exception as exc:
                self.root.after(0, lambda: self.append_log(f"[ERROR] {exc}\n"))
                if label:
                    self.root.after(0, lambda: self.status_text.set(f"{label} error"))

        threading.Thread(target=worker, daemon=True).start()

    def _ensure_connected(self):
        if not self.ssh.connected:
            messagebox.showwarning("Not connected", "Test and establish SSH connection first.")
            return False
        return True

    def _set_ssh_state(self, active):
        self.ssh_state_text.set("Active" if active else "Inactive")
        if self.ssh_status_label is not None:
            self.ssh_status_label.configure(fg="#1f7a1f" if active else "#b00020")
        if not active:
            self._set_mount_state(False)
        self._update_continue_button_state()

    def _set_mount_state(self, active):
        self.mount_active = active
        self.mount_state_text.set("Active" if active else "Inactive")
        if self.mount_status_label is not None:
            self.mount_status_label.configure(fg="#1f7a1f" if active else "#b00020")
        self._update_continue_button_state()

    def _update_continue_button_state(self):
        if self.continue_button is None:
            return
        state = "normal" if self.ssh.connected and self.mount_active else "disabled"
        self.continue_button.configure(state=state)

    def _set_start_leak_button_enabled(self, enabled):
        if self.start_leak_button is not None:
            self.start_leak_button.configure(state="normal" if enabled else "disabled")

    def _set_start_visual_button_enabled(self, enabled):
        if self.start_visual_button is not None:
            self.start_visual_button.configure(state="normal" if enabled else "disabled")

    def _set_start_reporting_button_enabled(self, enabled):
        if self.start_reporting_button is not None:
            self.start_reporting_button.configure(state="normal" if enabled else "disabled")

    def _validate_launch_inputs(self):
        participant = self.participant_id.get().strip()
        trial = self.trial_number.get().strip()

        if not participant or not trial:
            messagebox.showerror("Missing info", "Participant number and trial number are required.")
            return None

        if not participant.isdigit():
            messagebox.showerror("Invalid participant", "Participant number must be numeric.")
            return None

        if not trial.isdigit():
            messagebox.showerror("Invalid trial", "Trial number must be numeric.")
            return None

        return participant, trial

    def _build_remote_start_command(self, participant, trial):
        conda_sh = shlex.quote(self.conda_sh.get().strip())
        conda_env = shlex.quote(self.conda_env.get().strip())
        remote_dir = shlex.quote(self.remote_dir.get().strip())
        script_name_raw = self.script_name.get().strip()
        pid_file = shlex.quote(self.pid_file.get().strip())
        log_file = shlex.quote(self.log_file.get().strip())

        wrapper_script = "\n".join(
            [
                "import builtins",
                "import os",
                "import runpy",
                "responses = iter([os.environ['PARTICIPANT_ID'], os.environ['TRIAL_NUMBER']])",
                "real_input = builtins.input",
                "def scripted_input(prompt=''):",
                "    print(prompt, end='', flush=True)",
                "    try:",
                "        value = next(responses)",
                "    except StopIteration:",
                "        return real_input(prompt)",
                "    print(value, flush=True)",
                "    return value",
                "builtins.input = scripted_input",
                f"runpy.run_path({script_name_raw!r}, run_name='__main__')",
            ]
        )

        worker_script = (
            f"source {conda_sh} && "
            f"conda activate {conda_env} && "
            f"cd {remote_dir} && "
            "export PYTHONUNBUFFERED=1 && "
            f"export PARTICIPANT_ID={shlex.quote(participant)} && "
            f"export TRIAL_NUMBER={shlex.quote(trial)} && "
            f"python3 -c {shlex.quote(wrapper_script)}"
        )

        start_script = (
            f"if [ -f {pid_file} ]; then "
            f"OLD_PID=$(cat {pid_file}); "
            "if kill -0 \"$OLD_PID\" 2>/dev/null; then "
            'echo "PROCESS_ALREADY_RUNNING PID=$OLD_PID"; '
            "exit 1; "
            "fi; "
            "fi; "
            f"mkdir -p $(dirname {log_file}) && "
            f"setsid bash -lc {shlex.quote(worker_script)} > {log_file} 2>&1 < /dev/null & "
            "PID=$! && "
            f"echo $PID > {pid_file} && "
            'echo "STARTED PID=$PID"'
        )

        return f"bash -lc {shlex.quote(start_script)}"

    def _build_preflight_command(self):
        conda_sh = shlex.quote(self.conda_sh.get().strip())
        remote_dir = shlex.quote(self.remote_dir.get().strip())
        script_name = shlex.quote(self.script_name.get().strip())
        mount_point = shlex.quote(self.mount_point.get().strip())

        preflight = (
            "set -e; "
            f'test -f {conda_sh} && echo "OK conda init found"; '
            f'test -d {remote_dir} && echo "OK remote folder found"; '
            f'cd {remote_dir}; '
            f'test -f {script_name} && echo "OK script found"; '
            "command -v python3 >/dev/null && echo \"OK python3 found\"; "
            "command -v setsid >/dev/null && echo \"OK setsid found\"; "
            "command -v mount >/dev/null && echo \"OK mount found\"; "
            f'if mountpoint -q {mount_point}; then echo "OK mount point active"; else echo "WARN mount point not active"; fi'
        )
        return f"bash -lc {shlex.quote(preflight)}"

    def _build_mount_command(self):
        windows_host = self.windows_host.get().strip()
        windows_share = self.windows_share.get().strip()
        windows_user = self.windows_user.get().strip()
        windows_password = self.windows_password.get()
        mount_point = self.mount_point.get().strip()
        sudo_password = self.ssh_password.get()
        mount_version = self.mount_version.get().strip() or "3.0"

        if not windows_host or not windows_share or not windows_user or not windows_password or not mount_point:
            raise ValueError("Windows host, share, username, password, and mount point are required.")

        share_path = f"//{windows_host}/{windows_share}"
        mount_script = (
            "set -e; "
            "UID_VALUE=$(id -u); "
            "GID_VALUE=$(id -g); "
            f"WIN_USER={shlex.quote(windows_user)}; "
            f"WIN_PASS={shlex.quote(windows_password)}; "
            f"MOUNT_VER={shlex.quote(mount_version)}; "
            "MOUNT_OPTS=\"username=${WIN_USER},password=${WIN_PASS},uid=${UID_VALUE},gid=${GID_VALUE},iocharset=utf8,vers=${MOUNT_VER}\"; "
            f"sudo -S mkdir -p {shlex.quote(mount_point)}; "
            f"if mountpoint -q {shlex.quote(mount_point)}; then "
            f'echo "ALREADY_MOUNTED {mount_point}"; '
            "else "
            f"sudo -S mount -t cifs {shlex.quote(share_path)} {shlex.quote(mount_point)} -o \"$MOUNT_OPTS\"; "
            f'echo "MOUNTED {mount_point}"; '
            "fi"
        )
        return f"printf '%s\\n' {shlex.quote(sudo_password)} | bash -lc {shlex.quote(mount_script)}"

    def _schedule_log_refresh(self, delay_ms=2000):
        self._cancel_log_refresh()
        self.auto_refresh_job = self.root.after(delay_ms, self._refresh_log_if_connected)

    def _cancel_log_refresh(self):
        if self.auto_refresh_job is not None:
            self.root.after_cancel(self.auto_refresh_job)
            self.auto_refresh_job = None

    def _refresh_log_if_connected(self):
        self.auto_refresh_job = None
        if self.ssh.connected:
            self.show_last_log(schedule_next=True)

    def _build_mount_status_command(self):
        mount_point_raw = self.mount_point.get().strip()
        mount_point = shlex.quote(mount_point_raw)
        status_script = (
            f"if mountpoint -q {mount_point}; then "
            f'echo "MOUNT_ACTIVE {mount_point_raw}"; '
            "else "
            f'echo "MOUNT_INACTIVE {mount_point_raw}"; '
            "fi"
        )
        return f"bash -lc {shlex.quote(status_script)}"

    def refresh_mount_status(self, show_message=False, on_checked=None):
        if not self._ensure_connected():
            return

        def after_status(code, out, err):
            mount_active = "MOUNT_ACTIVE" in out
            self._set_mount_state(mount_active)
            self.status_text.set("Mount point is active" if mount_active else "Mount point is inactive")
            if show_message:
                if mount_active:
                    messagebox.showinfo("Mount Status", f"{self.mount_point.get().strip()} is mounted.")
                else:
                    messagebox.showwarning("Mount Status", f"{self.mount_point.get().strip()} is not mounted.")
            if on_checked is not None:
                on_checked(mount_active)

        self.run_ssh_command_async(self._build_mount_status_command(), "Check Mount Status", on_success=after_status)

    def _build_leak_running_status_command(self):
        script_name = self.script_name.get().strip()
        scanner = "\n".join(
            [
                "import os",
                "import subprocess",
                "script_name = os.environ['SCRIPT_NAME']",
                "self_pid = os.getpid()",
                "parent_pid = os.getppid()",
                "output = subprocess.check_output(['ps', '-eo', 'pid=,pgid=,args='], text=True)",
                "matches = []",
                "for line in output.splitlines():",
                "    parts = line.strip().split(None, 2)",
                "    if len(parts) < 3:",
                "        continue",
                "    pid = int(parts[0])",
                "    if pid in (self_pid, parent_pid):",
                "        continue",
                "    args = parts[2]",
                "    if script_name in args:",
                "        matches.append(line.strip())",
                "if matches:",
                "    print('LEAK_RUNNING')",
                "    print('\\n'.join(matches))",
                "else:",
                "    print('LEAK_NOT_RUNNING')",
            ]
        )
        status_script = (
            f"export SCRIPT_NAME={shlex.quote(script_name)} && "
            f"python3 -c {shlex.quote(scanner)}"
        )
        return f"bash -lc {shlex.quote(status_script)}"

    def refresh_leak_running_status(self):
        if not self.ssh.connected:
            self._set_start_leak_button_enabled(False)
            return

        def after_status(code, out, err):
            running = "LEAK_RUNNING" in out
            self._set_start_leak_button_enabled((not running) and (not self.leak_start_locked))

        self.run_ssh_command_async(
            self._build_leak_running_status_command(),
            "Leak Check Running Status",
            on_success=after_status,
        )

    def _mount_share_async(self, on_success=None):
        if not self._ensure_connected():
            return

        try:
            mount_command = self._build_mount_command()
        except ValueError as exc:
            messagebox.showerror("Missing mount info", str(exc))
            return

        def after_mount(code, out, err):
            if code == 0:
                self.status_text.set("Windows share mount command completed")
                self.refresh_mount_status(on_checked=lambda mount_active: on_success() if mount_active and on_success else None)
            else:
                self.status_text.set("Mount failed")
                self._set_mount_state(False)
                messagebox.showerror(
                    "Mount failed",
                    "The Windows share mount command failed. Check the log for sudo, share name, or credential issues.",
                )

        self.run_ssh_command_async(mount_command, "Mount Share", on_success=after_mount)

    def _watch_local_process(self, attr_name, enable_callback, label):
        process = getattr(self, attr_name)
        if process is None:
            enable_callback(True)
            return

        if process.poll() is None:
            self.root.after(1000, lambda: self._watch_local_process(attr_name, enable_callback, label))
            return

        setattr(self, attr_name, None)
        enable_callback(True)
        self.append_log(f"[INFO] {label} window closed.\n")
        self.status_text.set(f"{label} closed")

    def _launch_local_script(self, script_path: Path, label: str, attr_name: str, enable_callback):
        launch_values = self._validate_launch_inputs()
        if launch_values is None:
            return

        participant, trial = launch_values
        if not script_path.exists():
            messagebox.showerror("Missing script", f"Could not find {script_path.name}.")
            return

        try:
            enable_callback(False)
            process = subprocess.Popen(
                [sys.executable, str(script_path), "--participant", participant, "--trial", trial],
                cwd=str(self.base_dir),
            )
            setattr(self, attr_name, process)
            self.append_log(f"[INFO] Launched {label} for participant {participant}, trial {trial}.\n")
            self.status_text.set(f"Launched {label}")
            self.root.after(1000, lambda: self._watch_local_process(attr_name, enable_callback, label))
        except Exception as exc:
            enable_callback(True)
            messagebox.showerror("Launch failed", str(exc))

    def test_connection(self):
        host = self.ssh_host.get().strip()
        port = self.ssh_port.get().strip()
        user = self.ssh_user.get().strip()
        password = self.ssh_password.get()

        if not host or not port or not user:
            messagebox.showerror("Missing info", "Please fill host, port, username, and password.")
            return

        self.status_text.set("Connecting...")

        def worker():
            try:
                self.ssh.connect(host, port, user, password)
                out, err, code = self.ssh.exec("echo SSH_OK && hostname && pwd")
                msg = f"{out}{err}".strip() or "SSH connection successful."
                self.root.after(0, lambda: self.status_text.set(f"Connected to {host} as {user}"))
                self.root.after(0, lambda: messagebox.showinfo("Success", msg))
                self.root.after(0, lambda: self.append_log(f"[INFO] SSH connection verified. exit={code}\n{msg}\n"))
                self.root.after(0, lambda: self._set_ssh_state(True))
                self.root.after(0, self.refresh_mount_status)
                self.root.after(0, self.refresh_leak_running_status)
            except Exception as exc:
                self.root.after(0, lambda: self.status_text.set("Connection failed"))
                self.root.after(0, lambda: self.append_log(f"[SSH Error] {exc}\n"))
                self.root.after(0, lambda: self._set_ssh_state(False))
                self.root.after(0, lambda: self._set_start_leak_button_enabled(False))
                self.root.after(0, lambda: messagebox.showerror("SSH Error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def disconnect_ssh(self):
        self._cancel_log_refresh()
        self.ssh.disconnect()
        self.status_text.set("Disconnected")
        self._set_ssh_state(False)
        self._set_start_leak_button_enabled(False)
        self.append_log("[INFO] SSH disconnected.\n")

    def complete_stage_one(self):
        def move_to_stage_two():
            self._show_stage_two()

        self._mount_share_async(on_success=move_to_stage_two)

    def start_experiment(self):
        if not self._ensure_connected():
            return

        launch_values = self._validate_launch_inputs()
        if launch_values is None:
            return

        participant, trial = launch_values
        self.leak_start_locked = True
        self._set_start_leak_button_enabled(False)
        self.append_log(f"[INFO] Launching leak check for participant {participant}, trial {trial}.\n")
        self.append_log("[INFO] Mounting Windows share before preflight.\n")

        def after_mount():
            self.append_log(
                "[INFO] Running remote preflight checks for conda init, target folder, script file, python3, and setsid.\n"
            )

            def after_preflight(code, out, err):
                if code != 0:
                    self.status_text.set("Preflight failed")
                    self.leak_start_locked = False
                    self.refresh_leak_running_status()
                    messagebox.showerror(
                        "Preflight failed",
                        "The Raspberry Pi setup check failed. See the log panel for the exact missing path or command.",
                    )
                    return

                command = self._build_remote_start_command(participant, trial)
                self.append_log("[INFO] Preflight passed. Starting remote leak check process.\n")

                def after_start(start_code, start_out, start_err):
                    if start_code == 0 and "STARTED PID=" in start_out:
                        self.status_text.set(f"Leak check running for participant {participant}, trial {trial}")
                        self.leak_start_locked = True
                        self._set_start_leak_button_enabled(False)
                        self._schedule_log_refresh(1200)
                    elif "PROCESS_ALREADY_RUNNING" in start_out:
                        self.status_text.set("Leak check already running")
                        self.leak_start_locked = True
                        self._set_start_leak_button_enabled(False)
                        messagebox.showwarning(
                            "Already running",
                            "A process from the current PID file is already active on the Raspberry Pi.",
                        )
                    else:
                        self.status_text.set("Start failed")
                        self.leak_start_locked = False
                        self.refresh_leak_running_status()
                        messagebox.showerror(
                            "Start failed",
                            "The remote start command did not report a successful launch. See the log panel for stdout/stderr.",
                        )

                self.run_ssh_command_async(command, "Start Leak Check", on_success=after_start)

            self.run_ssh_command_async(self._build_preflight_command(), "Preflight", on_success=after_preflight)

        self._mount_share_async(on_success=after_mount)

    def launch_visual_inspection(self):
        self._launch_local_script(
            self.visual_script,
            "visual inspection",
            "visual_process",
            self._set_start_visual_button_enabled,
        )

    def launch_task_reporting(self):
        self._launch_local_script(
            self.reporting_script,
            "task reporting",
            "reporting_process",
            self._set_start_reporting_button_enabled,
        )

    def mount_share(self):
        self._mount_share_async()

    def _build_dismount_command(self):
        mount_point = self.mount_point.get().strip()
        sudo_password = self.ssh_password.get()
        if not mount_point:
            raise ValueError("Mount point is required.")

        dismount_script = (
            "set -e; "
            f"if mountpoint -q {shlex.quote(mount_point)}; then "
            f"sudo -S umount {shlex.quote(mount_point)}; "
            f'echo "UNMOUNTED {mount_point}"; '
            "else "
            f'echo "NOT_MOUNTED {mount_point}"; '
            "fi"
        )
        return f"printf '%s\\n' {shlex.quote(sudo_password)} | bash -lc {shlex.quote(dismount_script)}"

    def dismount_share(self):
        if not self._ensure_connected():
            return

        try:
            dismount_command = self._build_dismount_command()
        except ValueError as exc:
            messagebox.showerror("Missing mount info", str(exc))
            return

        def after_dismount(code, out, err):
            if code == 0:
                self.status_text.set("Dismount command completed")
                self.refresh_mount_status()
            else:
                self.status_text.set("Dismount failed")

        self.run_ssh_command_async(dismount_command, "Dismount Share", on_success=after_dismount)

    def stop_experiment(self):
        if not self._ensure_connected():
            return

        pid_file = shlex.quote(self.pid_file.get().strip())
        command = (
            "bash -lc "
            + shlex.quote(
                f"if [ -f {pid_file} ]; then "
                f"PID=$(cat {pid_file}); "
                "if kill -0 \"$PID\" 2>/dev/null; then "
                "if kill -INT -- -\"$PID\" 2>/dev/null; then "
                'echo "STOPPED PGID=$PID"; '
                "elif kill -INT \"$PID\" 2>/dev/null; then "
                'echo "STOPPED PID=$PID"; '
                "else "
                'echo "FAILED_TO_STOP PID=$PID"; '
                "exit 1; "
                "fi; "
                "sleep 1; "
                "if ! kill -0 \"$PID\" 2>/dev/null; then "
                f"rm -f {pid_file}; "
                'echo "PID_FILE_REMOVED"; '
                "fi; "
                "else "
                f"rm -f {pid_file}; "
                'echo "PID_NOT_RUNNING PID=$PID"; '
                "fi; "
                "else "
                'echo "PID_FILE_NOT_FOUND"; '
                "fi"
            )
        )

        def after_stop(code, out, err):
            if code == 0 and ("STOPPED PID=" in out or "PID_NOT_RUNNING" in out or "STOPPED PGID=" in out):
                self.status_text.set("Leak check stopped")
                self._cancel_log_refresh()

        self.run_ssh_command_async(command, "Stop Leak Check", on_success=after_stop)

    def kill_experiment(self):
        if not self._ensure_connected():
            return

        pid_file_raw = self.pid_file.get().strip()
        pid_file = shlex.quote(pid_file_raw)
        script_name = self.script_name.get().strip()
        killer = "\n".join(
            [
                "import os",
                "import signal",
                "import subprocess",
                "import time",
                "",
                "script_name = os.environ['SCRIPT_NAME']",
                "pid_file = os.environ['PID_FILE']",
                "self_pid = os.getpid()",
                "parent_pid = os.getppid()",
                "killed_any = False",
                "",
                "def scan_matches():",
                "    output = subprocess.check_output(['ps', '-eo', 'pid=,pgid=,args='], text=True)",
                "    found = []",
                "    for line in output.splitlines():",
                "        parts = line.strip().split(None, 2)",
                "        if len(parts) < 3:",
                "            continue",
                "        pid = int(parts[0])",
                "        pgid = int(parts[1])",
                "        args = parts[2]",
                "        if pid in (self_pid, parent_pid):",
                "            continue",
                "        if script_name in args:",
                "            found.append((pid, pgid, args))",
                "    return found",
                "",
                "def try_kill_pid(pid):",
                "    global killed_any",
                "    try:",
                "        os.kill(pid, signal.SIGKILL)",
                "        print(f'KILLED_PID PID={pid}')",
                "        killed_any = True",
                "    except ProcessLookupError:",
                "        pass",
                "    except PermissionError:",
                "        print(f'FAILED_TO_KILL_PID PID={pid}')",
                "",
                "def try_kill_pgid(pgid):",
                "    global killed_any",
                "    try:",
                "        os.killpg(pgid, signal.SIGKILL)",
                "        print(f'KILLED_PGID PGID={pgid}')",
                "        killed_any = True",
                "    except ProcessLookupError:",
                "        pass",
                "    except PermissionError:",
                "        print(f'FAILED_TO_KILL_PGID PGID={pgid}')",
                "",
                "if os.path.exists(pid_file):",
                "    try:",
                "        with open(pid_file, 'r', encoding='utf-8') as fh:",
                "            pid_text = fh.read().strip()",
                "        if pid_text:",
                "            pid = int(pid_text)",
                "            try:",
                "                pgid = os.getpgid(pid)",
                "            except ProcessLookupError:",
                "                pgid = None",
                "            if pgid is not None:",
                "                try_kill_pgid(pgid)",
                "            try_kill_pid(pid)",
                "    except Exception as exc:",
                "        print(f'PID_FILE_READ_ERROR {exc}')",
                "else:",
                "    print('PID_FILE_NOT_FOUND')",
                "",
                "for pid, pgid, args in scan_matches():",
                "    if pgid not in (self_pid, parent_pid):",
                "        try_kill_pgid(pgid)",
                "    try_kill_pid(pid)",
                "",
                "time.sleep(1.0)",
                "remaining = scan_matches()",
                "try:",
                "    if os.path.exists(pid_file):",
                "        os.remove(pid_file)",
                "        print('PID_FILE_REMOVED')",
                "except Exception as exc:",
                "    print(f'PID_FILE_REMOVE_ERROR {exc}')",
                "",
                "if remaining:",
                "    print('REMAINING_MATCHES')",
                "    for pid, pgid, args in remaining:",
                "        print(f'{pid} {pgid} {args}')",
                "    raise SystemExit(1)",
                "if killed_any:",
                "    print('KILL_SWEEP_COMPLETE')",
                "else:",
                "    print('NO_MATCHING_PROCESSES_FOUND')",
            ]
        )
        command = (
            "bash -lc "
            + shlex.quote(
                f"export SCRIPT_NAME={shlex.quote(script_name)} && "
                f"export PID_FILE={pid_file} && "
                f"python3 -c {shlex.quote(killer)}"
            )
        )

        def after_kill(code, out, err):
            if code == 0 and (
                "KILL_SWEEP_COMPLETE" in out
                or "NO_MATCHING_PROCESSES_FOUND" in out
                or "PID_NOT_RUNNING" in out
            ):
                self.status_text.set("Leak check killed")
                self._cancel_log_refresh()
                self.leak_start_locked = False
                self.refresh_leak_running_status()
            else:
                self.status_text.set("Kill sweep incomplete")
                messagebox.showwarning(
                    "Kill sweep incomplete",
                    "The Pi kill sweep ran, but one or more matching processes may still be alive. Check the log.",
                )

        self.run_ssh_command_async(command, "Kill Leak Check", on_success=after_kill)

    def check_remote_status(self):
        if not self._ensure_connected():
            return

        pid_file = shlex.quote(self.pid_file.get().strip())
        script_name = self.script_name.get().strip()
        command = (
            "bash -lc "
            + shlex.quote(
                f'echo "--- PID file ---"; '
                f'if [ -f {pid_file} ]; then cat {pid_file}; else echo "missing"; fi; '
                'echo "--- Process check ---"; '
                f'if [ -f {pid_file} ]; then PID=$(cat {pid_file}); ps -g "$PID" -o pid=,pgid=,ppid=,stat=,etime=,cmd=; fi; '
                'echo "--- Matching processes ---"; '
                f'ps -ef | grep -F {shlex.quote(script_name)} | grep -v grep || true'
            )
        )
        self.run_ssh_command_async(command, "Leak Check Status")

    def show_last_log(self, schedule_next=False):
        if not self._ensure_connected():
            return

        log_file = shlex.quote(self.log_file.get().strip())
        command = (
            "bash -lc "
            + shlex.quote(
                f'echo "--- Last log lines ---"; '
                f'tail -n 60 {log_file} 2>/dev/null || echo "No log file found."'
            )
        )

        def after_log(code, out, err):
            if schedule_next:
                self._schedule_log_refresh(2000)

        self.run_ssh_command_async(command, "Last Leak Log", on_success=after_log)

    def on_close(self):
        if not messagebox.askyesno(
            "Confirm Exit",
            "Are you sure you want to close the combined experiment control window?",
        ):
            return
        self._cancel_log_refresh()
        self.ssh.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = CombinedExperimentApp(root)
    root.mainloop()
