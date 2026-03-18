import threading
import tkinter as tk
from tkinter import ttk, messagebox
import shlex

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


class RaspberryPiInvestmentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Raspberry Pi Investment Launcher")
        self.root.geometry("1180x820")
        self.root.minsize(1000, 720)

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
        self.sudo_password = tk.StringVar(value="")
        self.mount_version = tk.StringVar(value="3.0")

        self.participant_id = tk.StringVar(value="")
        self.trial_number = tk.StringVar(value="1")

        self.pid_file = tk.StringVar(value="/tmp/raspi_investment.pid")
        self.log_file = tk.StringVar(value="/tmp/raspi_investment.log")

        self.status_text = tk.StringVar(value="Not connected")
        self.auto_refresh_job = None

        self.main_frame = ttk.Frame(self.root, padding=15)
        self.main_frame.pack(fill="both", expand=True)
        self.paned = ttk.Panedwindow(self.main_frame, orient="horizontal")
        self.controls_frame = ttk.Frame(self.paned, padding=(0, 0, 12, 0))
        self.log_frame = ttk.LabelFrame(self.paned, text="Log", padding=10)
        self.log_controls_frame = ttk.Frame(self.log_frame)

        self._build_ui()
        self.root.after(100, self._set_initial_pane_sizes)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        self.paned.pack(fill="both", expand=True)
        self.paned.add(self.controls_frame, weight=5)
        self.paned.add(self.log_frame, weight=3)

        title_row = ttk.Frame(self.controls_frame)
        title_row.pack(fill="x", pady=(0, 12))

        ttk.Label(
            title_row,
            text="Raspberry Pi Investment Control",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")
        ttk.Label(title_row, textvariable=self.status_text).pack(side="right")

        ssh_frame = ttk.LabelFrame(self.controls_frame, text="SSH Connection", padding=12)
        ssh_frame.pack(fill="x", pady=(0, 10))

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

        ssh_frame.columnconfigure(1, weight=1)

        remote_frame = ttk.LabelFrame(self.controls_frame, text="Remote Script Setup", padding=12)
        remote_frame.pack(fill="x", pady=(0, 10))

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

        mount_frame = ttk.LabelFrame(self.controls_frame, text="Windows Share Mount", padding=12)
        mount_frame.pack(fill="x", pady=(0, 10))

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

        ttk.Label(mount_frame, text="Pi sudo Password").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(mount_frame, textvariable=self.sudo_password, width=24, show="*").grid(
            row=3, column=1, sticky="ew", padx=8, pady=5
        )

        ttk.Button(mount_frame, text="Mount Share", command=self.mount_share).grid(
            row=3, column=3, sticky="e", padx=8, pady=5
        )

        for column in (1, 3):
            mount_frame.columnconfigure(column, weight=1)

        help_text = (
            "The start action SSHes into the Raspberry Pi, activates the selected conda environment, "
            "feeds participant ID and trial number to the script, and runs it in the background. "
            "You can also mount the Windows SMB share here before launching."
        )
        ttk.Label(self.controls_frame, text=help_text, wraplength=640, justify="left").pack(anchor="w", pady=(0, 8))

        self.log_frame.configure(width=360)

        self.log_controls_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ttk.Label(self.log_controls_frame, text="Participant ID").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Entry(self.log_controls_frame, textvariable=self.participant_id, width=10).grid(row=0, column=1, sticky="w")
        ttk.Label(self.log_controls_frame, text="Trial").grid(row=0, column=2, sticky="w", padx=(12, 6))
        ttk.Entry(self.log_controls_frame, textvariable=self.trial_number, width=8).grid(row=0, column=3, sticky="w")

        ttk.Button(self.log_controls_frame, text="Start Experiment", command=self.start_experiment).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0), padx=(0, 6)
        )
        ttk.Button(self.log_controls_frame, text="Stop Experiment", command=self.stop_experiment).grid(
            row=1, column=2, columnspan=2, sticky="ew", pady=(8, 0), padx=(0, 6)
        )
        ttk.Button(self.log_controls_frame, text="Kill Experiment", command=self.kill_experiment).grid(
            row=1, column=4, sticky="ew", pady=(8, 0), padx=(0, 6)
        )
        ttk.Button(self.log_controls_frame, text="Check Status", command=self.check_remote_status).grid(
            row=1, column=5, sticky="ew", pady=(8, 0), padx=(0, 6)
        )
        ttk.Button(self.log_controls_frame, text="Show Last Log", command=self.show_last_log).grid(
            row=1, column=6, sticky="ew", pady=(8, 0), padx=(0, 6)
        )
        ttk.Button(self.log_controls_frame, text="Clear Log", command=self.clear_log).grid(
            row=1, column=7, sticky="ew", pady=(8, 0)
        )

        self.log_text = tk.Text(self.log_frame, wrap="none", height=22, font=("Consolas", 10))
        self.log_text.grid(row=1, column=0, sticky="nsew")

        y_scroll = ttk.Scrollbar(self.log_frame, orient="vertical", command=self.log_text.yview)
        y_scroll.grid(row=1, column=1, sticky="ns")

        x_scroll = ttk.Scrollbar(self.log_frame, orient="horizontal", command=self.log_text.xview)
        x_scroll.grid(row=2, column=0, sticky="ew")

        self.log_text.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.log_frame.columnconfigure(0, weight=1)
        self.log_frame.rowconfigure(1, weight=1)

    def _set_initial_pane_sizes(self):
        try:
            total_width = self.paned.winfo_width()
            if total_width > 200:
                self.paned.sashpos(0, int(total_width * 0.58))
        except Exception:
            pass

    def append_log(self, text):
        self.log_text.insert("end", text)
        self.log_text.see("end")

    def clear_log(self):
        self.log_text.delete("1.0", "end")

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

    def _validate_launch_inputs(self):
        participant = self.participant_id.get().strip()
        trial = self.trial_number.get().strip()

        if not participant or not trial:
            messagebox.showerror("Missing info", "Participant ID and trial number are required.")
            return None

        if not participant.isdigit():
            messagebox.showerror("Invalid participant", "Participant ID must be numeric.")
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
        script_name = shlex.quote(script_name_raw)
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
        sudo_password = self.sudo_password.get() or self.ssh_password.get()
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
            except Exception as exc:
                self.root.after(0, lambda: self.status_text.set("Connection failed"))
                self.root.after(0, lambda: self.append_log(f"[SSH Error] {exc}\n"))
                self.root.after(0, lambda: messagebox.showerror("SSH Error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def disconnect_ssh(self):
        self._cancel_log_refresh()
        self.ssh.disconnect()
        self.status_text.set("Disconnected")
        self.append_log("[INFO] SSH disconnected.\n")

    def start_experiment(self):
        if not self._ensure_connected():
            return

        launch_values = self._validate_launch_inputs()
        if launch_values is None:
            return

        participant, trial = launch_values
        self.append_log(f"[INFO] Launching participant {participant}, trial {trial}.\n")
        self.append_log("[INFO] Mounting Windows share before preflight.\n")

        def after_mount(code, out, err):
            if code != 0:
                self.status_text.set("Mount failed")
                messagebox.showerror(
                    "Mount failed",
                    "The Windows share mount command failed. Check the log for sudo, share name, or credential issues.",
                )
                return

            self.append_log(
                "[INFO] Running remote preflight checks for conda init, target folder, script file, python3, and setsid.\n"
            )

            def after_preflight(code, out, err):
                if code != 0:
                    self.status_text.set("Preflight failed")
                    messagebox.showerror(
                        "Preflight failed",
                        "The Raspberry Pi setup check failed. See the log panel for the exact missing path or command.",
                    )
                    return

                command = self._build_remote_start_command(participant, trial)
                self.append_log("[INFO] Preflight passed. Starting remote experiment process.\n")

                def after_start(start_code, start_out, start_err):
                    if start_code == 0 and "STARTED PID=" in start_out:
                        self.status_text.set(f"Running participant {participant}, trial {trial}")
                        self._schedule_log_refresh(1200)
                    elif "PROCESS_ALREADY_RUNNING" in start_out:
                        self.status_text.set("Experiment already running")
                        messagebox.showwarning(
                            "Already running",
                            "A process from the current PID file is already active on the Raspberry Pi.",
                        )
                    else:
                        self.status_text.set("Start failed")
                        messagebox.showerror(
                            "Start failed",
                            "The remote start command did not report a successful launch. See the log panel for stdout/stderr.",
                        )

                self.run_ssh_command_async(command, "Start Experiment", on_success=after_start)

            self.run_ssh_command_async(self._build_preflight_command(), "Preflight", on_success=after_preflight)

        try:
            mount_command = self._build_mount_command()
        except ValueError as exc:
            messagebox.showerror("Missing mount info", str(exc))
            return

        self.run_ssh_command_async(mount_command, "Mount Share", on_success=after_mount)

    def mount_share(self):
        if not self._ensure_connected():
            return

        try:
            mount_command = self._build_mount_command()
        except ValueError as exc:
            messagebox.showerror("Missing mount info", str(exc))
            return

        def after_mount(code, out, err):
            if code == 0:
                self.status_text.set("Windows share mounted")
            else:
                self.status_text.set("Mount failed")

        self.run_ssh_command_async(mount_command, "Mount Share", on_success=after_mount)

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
            if code == 0 and ("STOPPED PID=" in out or "PID_NOT_RUNNING" in out):
                self.status_text.set("Stopped")
                self._cancel_log_refresh()

        self.run_ssh_command_async(command, "Stop Experiment", on_success=after_stop)

    def kill_experiment(self):
        if not self._ensure_connected():
            return

        pid_file = shlex.quote(self.pid_file.get().strip())
        command = (
            "bash -lc "
            + shlex.quote(
                f"if [ -f {pid_file} ]; then "
                f"PID=$(cat {pid_file}); "
                "if kill -0 \"$PID\" 2>/dev/null; then "
                "if kill -KILL -- -\"$PID\" 2>/dev/null; then "
                'echo "KILLED PGID=$PID"; '
                "elif kill -KILL \"$PID\" 2>/dev/null; then "
                'echo "KILLED PID=$PID"; '
                "else "
                'echo "FAILED_TO_KILL PID=$PID"; '
                "exit 1; "
                "fi; "
                "sleep 1; "
                f"rm -f {pid_file}; "
                'echo "PID_FILE_REMOVED"; '
                "else "
                f"rm -f {pid_file}; "
                'echo "PID_NOT_RUNNING PID=$PID"; '
                "fi; "
                "else "
                'echo "PID_FILE_NOT_FOUND"; '
                "fi"
            )
        )

        def after_kill(code, out, err):
            if code == 0 and ("KILLED PID=" in out or "PID_NOT_RUNNING" in out):
                self.status_text.set("Killed")
                self._cancel_log_refresh()

        self.run_ssh_command_async(command, "Kill Experiment", on_success=after_kill)

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
        self.run_ssh_command_async(command, "Remote Status")

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

        self.run_ssh_command_async(command, "Last Log", on_success=after_log)

    def on_close(self):
        self._cancel_log_refresh()
        self.ssh.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = RaspberryPiInvestmentApp(root)
    root.mainloop()
