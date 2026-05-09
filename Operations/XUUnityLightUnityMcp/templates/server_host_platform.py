import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class HostPlatformAdapter:
    platform_kind: str

    def pid_is_alive(self, pid: int) -> bool:
        if pid <= 0:
            return False

        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def list_process_commands(self) -> list[tuple[int, str]]:
        if os.name == "nt":
            shell_path = shutil.which("powershell") or shutil.which("powershell.exe") or shutil.which("pwsh")
            if not shell_path:
                return []

            script = (
                "Get-CimInstance Win32_Process | "
                "Where-Object { $_.CommandLine } | "
                "Select-Object ProcessId,CommandLine | "
                "ConvertTo-Json -Compress"
            )
            try:
                completed = subprocess.run(
                    [shell_path, "-NoProfile", "-Command", script],
                    check=False,
                    capture_output=True,
                    text=True,
                )
            except OSError:
                return []

            raw = completed.stdout.strip()
            if not raw:
                return []

            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                return []

            if isinstance(payload, dict):
                payload = [payload]

            commands: list[tuple[int, str]] = []
            for entry in payload if isinstance(payload, list) else []:
                if not isinstance(entry, dict):
                    continue
                try:
                    pid = int(entry.get("ProcessId") or 0)
                except (TypeError, ValueError):
                    continue
                command = str(entry.get("CommandLine") or "").strip()
                if pid > 0 and command:
                    commands.append((pid, command))
            return commands

        try:
            completed = subprocess.run(
                ["ps", "-axo", "pid=,command="],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            return []

        commands: list[tuple[int, str]] = []
        for line in completed.stdout.splitlines():
            line = line.rstrip()
            if not line:
                continue
            parts = line.lstrip().split(None, 1)
            if len(parts) != 2:
                continue
            raw_pid, command = parts
            try:
                pid = int(raw_pid)
            except ValueError:
                continue
            command = command.strip()
            if pid > 0 and command:
                commands.append((pid, command))
        return commands


def host_platform_kind() -> str:
    if sys.platform == "darwin":
        return "macos"
    if os.name == "nt":
        return "windows"
    return "linux"


def current_host_platform_adapter() -> HostPlatformAdapter:
    return HostPlatformAdapter(platform_kind=host_platform_kind())
