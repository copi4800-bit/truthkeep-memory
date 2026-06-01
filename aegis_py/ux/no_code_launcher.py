"""TruthKeep No-Code Launcher.

A zero-extra-dependency desktop launcher built with tkinter.  It does not open
HTTP ports and does not change the memory core.  It simply runs the safe CLI
commands behind friendly buttons for non-technical users.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class LauncherCommand:
    label: str
    description: str
    args: list[str]


COMMANDS = [
    LauncherCommand("1. Install / Repair Easy Mode", "Create DB, check backend, and install OpenClaw Easy Mode.", ["easy", "install"]),
    LauncherCommand("2. Check OpenClaw", "Verify the OpenClaw manifest and TruthKeep backend readiness.", ["openclaw", "doctor"]),
    LauncherCommand("3. Show Dashboard", "Open the local text dashboard in the log panel.", ["dashboard"]),
    LauncherCommand("4. Safe Repair", "Create a backup and compact local storage.", ["repair"]),
    LauncherCommand("5. Print MCP Config", "Show copy-paste MCP config for manual setup.", ["openclaw", "config"]),
]


def _run_cli(args: list[str], db_path: str) -> tuple[int, str]:
    cmd = [sys.executable, "-m", "truthkeep.cli", "--db-path", db_path, *args]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=90)
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired:
        return 1, "Command timed out. TruthKeep did not finish within 90 seconds.\n"
    except Exception as exc:
        return 1, f"Failed to run command: {exc}\n"


def launch_no_code_gui(db_path: str = "memory_aegis.db") -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
    except Exception as exc:
        print("TruthKeep No-Code Launcher needs tkinter, which is not available in this Python install.")
        print(f"Details: {exc}")
        print("Use CLI instead: python -m truthkeep.cli easy install")
        return 1

    root = tk.Tk()
    root.title("TruthKeep — Easy Mode")
    root.geometry("980x680")
    root.minsize(860, 560)
    root.configure(bg="#08080a")

    fg = "#f8fafc"
    muted = "#94a3b8"
    accent = "#8b5cf6"
    panel = "#111118"
    border = "#27272f"

    header = tk.Frame(root, bg="#08080a")
    header.pack(fill="x", padx=22, pady=(18, 8))
    tk.Label(header, text="TruthKeep Easy Mode", bg="#08080a", fg=fg, font=("Segoe UI", 24, "bold")).pack(anchor="w")
    tk.Label(
        header,
        text="Nhớ đúng, nhớ lâu — local-only, MCP stdio, zero open ports.",
        bg="#08080a", fg=muted, font=("Segoe UI", 11),
    ).pack(anchor="w", pady=(4, 0))

    db_frame = tk.Frame(root, bg=panel, highlightbackground=border, highlightthickness=1)
    db_frame.pack(fill="x", padx=22, pady=10)
    tk.Label(db_frame, text="Database", bg=panel, fg=fg, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
    db_var = tk.StringVar(value=os.path.abspath(db_path))
    db_row = tk.Frame(db_frame, bg=panel)
    db_row.pack(fill="x", padx=14, pady=(0, 12))
    tk.Entry(db_row, textvariable=db_var, bg="#0b0b10", fg=fg, insertbackground=fg, relief="flat", font=("Consolas", 10)).pack(side="left", fill="x", expand=True, ipady=8)

    def choose_db() -> None:
        path = filedialog.asksaveasfilename(title="Choose TruthKeep database", defaultextension=".db", initialfile="memory_aegis.db")
        if path:
            db_var.set(path)

    tk.Button(db_row, text="Choose…", command=choose_db, bg=accent, fg="white", relief="flat", padx=14, pady=7).pack(side="left", padx=(10, 0))

    main = tk.Frame(root, bg="#08080a")
    main.pack(fill="both", expand=True, padx=22, pady=(0, 18))
    left = tk.Frame(main, bg="#08080a")
    left.pack(side="left", fill="y", padx=(0, 12))
    right = tk.Frame(main, bg=panel, highlightbackground=border, highlightthickness=1)
    right.pack(side="left", fill="both", expand=True)

    output = tk.Text(right, bg="#09090d", fg=fg, insertbackground=fg, relief="flat", wrap="word", font=("Consolas", 10))
    output.pack(fill="both", expand=True, padx=12, pady=12)
    output.insert("end", "Welcome. Click ‘Install / Repair Easy Mode’ first.\n\n")

    status_var = tk.StringVar(value="Ready")
    tk.Label(root, textvariable=status_var, bg="#08080a", fg=muted, anchor="w").pack(fill="x", padx=22, pady=(0, 12))

    def append(text: str) -> None:
        output.insert("end", text)
        output.see("end")

    def run_command(command: LauncherCommand) -> None:
        def worker() -> None:
            status_var.set(f"Running: {command.label}")
            append(f"\n>>> {command.label}\n")
            code, text = _run_cli(command.args, db_var.get())
            append(text)
            append(f"\n[exit code: {code}]\n")
            status_var.set("Ready" if code == 0 else "Needs attention")
            if code != 0:
                messagebox.showwarning("TruthKeep", "A check needs attention. See the log panel for details.")
        threading.Thread(target=worker, daemon=True).start()

    for command in COMMANDS:
        box = tk.Frame(left, bg=panel, highlightbackground=border, highlightthickness=1)
        box.pack(fill="x", pady=(0, 10))
        tk.Label(box, text=command.label, bg=panel, fg=fg, font=("Segoe UI", 10, "bold"), wraplength=260, justify="left").pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(box, text=command.description, bg=panel, fg=muted, wraplength=260, justify="left").pack(anchor="w", padx=12, pady=(0, 8))
        tk.Button(box, text="Run", command=lambda c=command: run_command(c), bg="#1f2937", fg=fg, relief="flat", padx=12, pady=6).pack(anchor="e", padx=12, pady=(0, 10))

    tk.Button(left, text="Clear Log", command=lambda: output.delete("1.0", "end"), bg="#27272a", fg=fg, relief="flat", padx=12, pady=8).pack(fill="x")

    root.mainloop()
    return 0
