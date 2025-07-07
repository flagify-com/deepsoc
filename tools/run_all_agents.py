#!/usr/bin/env python3
"""Launch DeepSOC web server and all agent roles.

This script starts ``main.py`` along with the five agent roles as
independent subprocesses. It also handles graceful shutdown when
receiving ``SIGINT`` or ``SIGTERM``.
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Resolve project root and load environment variables from `.env`
ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

# Define commands for the main service and each agent role
AGENT_COMMANDS = [
    [sys.executable, "main.py"],
    [sys.executable, "main.py", "-role", "_captain"],
    [sys.executable, "main.py", "-role", "_manager"],
    [sys.executable, "main.py", "-role", "_operator"],
    [sys.executable, "main.py", "-role", "_executor"],
    [sys.executable, "main.py", "-role", "_expert"],
]

processes = []
_running = True


def _start_process(cmd):
    """Start a subprocess in the project root."""
    return subprocess.Popen(cmd, cwd=ROOT_DIR)


def _shutdown(*_):
    """Terminate all running subprocesses."""
    global _running
    _running = False
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
    # Give processes time to exit gracefully
    end = time.time() + 10
    for proc in processes:
        if proc.poll() is None:
            try:
                proc.wait(timeout=max(0, end - time.time()))
            except subprocess.TimeoutExpired:
                proc.kill()


def main() -> None:
    """Entry point."""
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _shutdown)

    # Start all agents
    for cmd in AGENT_COMMANDS:
        processes.append(_start_process(cmd))

    # Keep the script alive until interrupted
    try:
        while _running:
            # If any child process exits, initiate shutdown
            for proc in processes:
                if proc.poll() is not None:
                    _shutdown()
                    break
            time.sleep(1)
    finally:
        _shutdown()


if __name__ == "__main__":
    main()
