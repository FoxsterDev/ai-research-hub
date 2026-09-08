"""One bounded CLI lifetime with file-backed evidence and process-group cleanup."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import records


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def terminate_group(process: subprocess.Popen) -> None:
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        # Popen retains the process handle on Windows; this cannot target a
        # reused PID. Descendant cleanup is unsupported and explicitly exposed.
        process.kill()
    process.wait(timeout=10)


def capture(
    command: list[str], *, cwd: Path, environment: dict[str, str], prompt: bytes,
    output_dir: Path, timeout_seconds: float, max_output_bytes: int = 32 * 1024 * 1024,
) -> dict[str, Any]:
    if not 0 < timeout_seconds <= 3600 or max_output_bytes < 1024:
        raise ValueError("invalid process limits")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    started = timestamp()
    start_clock = time.monotonic()
    process = None
    status = "failed"
    error = None
    interrupted = False
    previous_handlers = {}

    def interrupt(signum, frame):
        raise KeyboardInterrupt

    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[sig] = signal.signal(sig, interrupt)
        with (output_dir / "stdin.txt").open("xb") as stream:
            stream.write(prompt)
        with (output_dir / "stdin.txt").open("rb") as stdin, \
                (output_dir / "transcript.jsonl").open("xb") as stdout, \
                (output_dir / "stderr.txt").open("xb") as stderr:
            records.write(output_dir / "process-intent.json", {
                "owner_pid": os.getpid(), "started": started,
            }, exclusive=True)
            process = subprocess.Popen(
                command, cwd=cwd, env=environment, stdin=stdin,
                stdout=stdout, stderr=stderr, start_new_session=(os.name == "posix"),
                creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0),
            )
            records.write(output_dir / "process-start.json", {
                "pid": process.pid, "owner_pid": os.getpid(), "started": started,
                "process_group": process.pid if os.name == "posix" else None,
            }, exclusive=True)
            while True:
                elapsed = time.monotonic() - start_clock
                if elapsed >= timeout_seconds:
                    status = "timeout"
                    break
                size = sum((output_dir / name).stat().st_size
                           for name in ("transcript.jsonl", "stderr.txt"))
                if size > max_output_bytes:
                    status = "output_limit"
                    break
                try:
                    process.wait(timeout=min(0.2, timeout_seconds - elapsed))
                    status = "completed" if process.returncode == 0 else "failed"
                    if sum((output_dir / name).stat().st_size for name in
                           ("transcript.jsonl", "stderr.txt")) > max_output_bytes:
                        status = "output_limit"
                    break
                except subprocess.TimeoutExpired:
                    continue
    except KeyboardInterrupt:
        status = "interrupted"
        interrupted = True
    except OSError as exception:
        error = type(exception).__name__
    finally:
        if process is not None:
            terminate_group(process)
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)
    terminal = {
        "started": started, "ended": timestamp(), "status": status,
        "exit_code": process.returncode if process is not None else None,
        "timed_out": status == "timeout", "interrupted": interrupted,
        "output_limited": status == "output_limit", "launch_error": error,
        "duration_seconds": round(time.monotonic() - start_clock, 3),
        "pid": process.pid if process is not None else None,
        "process_tree_cleanup": "owned_process_group" if os.name == "posix" else "parent_only_unverified",
    }
    records.write(output_dir / "process-terminal.json", terminal, exclusive=True)
    return terminal
