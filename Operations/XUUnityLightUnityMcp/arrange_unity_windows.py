#!/usr/bin/env python3
import argparse
import fcntl
import json
import math
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path


LOCK_PATH = Path(os.environ.get("TMPDIR", "/tmp")) / "xuunity_arrange_unity_windows.lock"
DEFAULT_MARGIN = 18
DEFAULT_GUTTER = 14
TARGET_CELL_ASPECT = 1.55
APPLE_SCRIPT_TIMEOUT_SECONDS = 2.0
WINDOW_FIT_TOLERANCE = 8


def host_platform_kind() -> str:
    if sys.platform == "darwin":
        return "macos"
    if os.name == "nt":
        return "windows"
    return "linux"


def list_process_commands() -> list[tuple[int, str]]:
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
        parts = line.lstrip().split(None, 1)
        if len(parts) != 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        command = parts[1].strip()
        if pid > 0 and command:
            commands.append((pid, command))
    return commands


def looks_like_unity_editor(command: str) -> bool:
    if "Unity Hub" in command:
        return False
    if "Unity.app/Contents/MacOS/Unity" in command:
        return True
    return " -projectPath " in command and "/Unity" in command


def discover_running_unity_editor_pids() -> list[int]:
    return sorted({pid for pid, command in list_process_commands() if looks_like_unity_editor(command)})


def parse_bounds(raw: str) -> tuple[int, int, int, int]:
    values = [part.strip() for part in raw.replace("{", "").replace("}", "").split(",")]
    if len(values) != 4:
        raise ValueError(f"Unexpected bounds payload: {raw!r}")
    left, top, right, bottom = [int(float(value)) for value in values]
    return left, top, right, bottom


def read_main_screen_bounds() -> tuple[int, int, int, int]:
    script = 'tell application "Finder" to get bounds of window of desktop'
    try:
        completed = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=APPLE_SCRIPT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Timed out while querying macOS desktop bounds via AppleScript") from exc
    raw = (completed.stdout or "").strip()
    if completed.returncode != 0 or not raw:
        raise RuntimeError((completed.stderr or completed.stdout or "Failed to read macOS desktop bounds").strip())
    return parse_bounds(raw)


def choose_grid(count: int, width: int, height: int) -> tuple[int, int]:
    best_cols = 1
    best_rows = count
    best_score = float("inf")
    for cols in range(1, count + 1):
        rows = math.ceil(count / cols)
        cell_width = width / cols
        cell_height = height / rows
        cell_aspect = cell_width / max(1.0, cell_height)
        unused_slots = (rows * cols) - count
        score = abs(math.log(max(0.01, cell_aspect / TARGET_CELL_ASPECT))) + (unused_slots * 0.12)
        if score < best_score:
            best_score = score
            best_cols = cols
            best_rows = rows
    return best_cols, best_rows


def build_layout(
    pids: list[int],
    *,
    left: int,
    top: int,
    right: int,
    bottom: int,
    margin: int,
    gutter: int,
) -> list[dict[str, int]]:
    usable_width = max(320, (right - left) - (margin * 2))
    usable_height = max(240, (bottom - top) - (margin * 2))
    cols, rows = choose_grid(len(pids), usable_width, usable_height)
    cell_width = max(320, int((usable_width - gutter * (cols - 1)) / cols))
    cell_height = max(240, int((usable_height - gutter * (rows - 1)) / rows))

    layout: list[dict[str, int]] = []
    for index, pid in enumerate(pids):
        row = index // cols
        col = index % cols
        x = left + margin + col * (cell_width + gutter)
        y = top + margin + row * (cell_height + gutter)
        layout.append(
            {
                "pid": pid,
                "x": x,
                "y": y,
                "width": cell_width,
                "height": cell_height,
                "row": row,
                "col": col,
            }
        )
    return layout


def build_visible_fan_layout(
    pids: list[int],
    *,
    left: int,
    top: int,
    right: int,
    bottom: int,
    margin: int,
    max_window_width: int,
    max_window_height: int,
) -> list[dict[str, int]]:
    min_x = left + margin
    max_x = max(min_x, right - margin - max_window_width)
    min_y = top + margin
    max_y = max(min_y, bottom - margin - max_window_height)
    center_x = int((min_x + max_x) / 2)
    center_y = int((min_y + max_y) / 2)

    if len(pids) == 1:
        anchors = [(center_x, center_y)]
    elif len(pids) == 2:
        anchors = [(min_x, min_y), (max_x, max_y)]
    elif len(pids) == 3:
        anchors = [(min_x, min_y), (max_x, min_y), (center_x, max_y)]
    else:
        anchors = []
        spread = max(1, len(pids) - 1)
        for index in range(len(pids)):
            progress = index / spread
            y = int(min_y + (max_y - min_y) * progress)
            x = min_x if index % 2 == 0 else max_x
            if max_x > min_x and index % 4 in (2, 3):
                x = center_x
            anchors.append((x, y))

    return [
        {
            "pid": pid,
            "x": anchors[index][0],
            "y": anchors[index][1],
            "width": max_window_width,
            "height": max_window_height,
            "row": index,
            "col": index,
        }
        for index, pid in enumerate(pids)
    ]


def should_use_visible_fan_layout(
    results: list[dict[str, object]],
    *,
    right: int,
    bottom: int,
    margin: int,
) -> bool:
    if len(results) < 2 or not all(bool(item.get("applied")) for item in results):
        return False
    for item in results:
        width = int(item.get("width") or 0)
        height = int(item.get("height") or 0)
        requested_width = int(item.get("requested_width") or width)
        requested_height = int(item.get("requested_height") or height)
        x = int(item.get("x") or 0)
        y = int(item.get("y") or 0)
        if width > requested_width + WINDOW_FIT_TOLERANCE:
            return True
        if height > requested_height + WINDOW_FIT_TOLERANCE:
            return True
        if x + width > right - margin + WINDOW_FIT_TOLERANCE:
            return True
        if y + height > bottom - margin + WINDOW_FIT_TOLERANCE:
            return True
    return False


def set_window_bounds(pid: int, x: int, y: int, width: int, height: int, focus: bool) -> dict[str, object]:
    focus_clause = "set frontmost to true" if focus else ""
    script = f'''
tell application "System Events"
  set targetProcess to missing value
  repeat with candidateProcess in application processes
    try
      if (unix id of candidateProcess as integer) is {pid} then
        set targetProcess to candidateProcess
        exit repeat
      end if
    end try
  end repeat
  if targetProcess is missing value then error "Unity process not found for pid {pid}"
  if (count of windows of targetProcess) is 0 then error "Unity process has no windows"
  tell targetProcess
    set position of window 1 to {{{x}, {y}}}
    set size of window 1 to {{{width}, {height}}}
    {focus_clause}
    set finalPosition to position of window 1
    set finalSize to size of window 1
  end tell
end tell
return (item 1 of finalPosition as string) & "," & (item 2 of finalPosition as string) & "," & (item 1 of finalSize as string) & "," & (item 2 of finalSize as string)
'''
    try:
        completed = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=APPLE_SCRIPT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {
            "pid": pid,
            "applied": False,
            "error": "timed_out_waiting_for_macos_window_control",
        }
    if completed.returncode != 0:
        return {
            "pid": pid,
            "applied": False,
            "error": (completed.stderr or completed.stdout or "window_update_failed").strip(),
        }
    raw = (completed.stdout or "").strip()
    final_x, final_y, final_w, final_h = parse_bounds(raw)
    return {
        "pid": pid,
        "applied": True,
        "x": final_x,
        "y": final_y,
        "width": final_w,
        "height": final_h,
    }


@contextmanager
def exclusive_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def main() -> int:
    parser = argparse.ArgumentParser(description="Tile running Unity editor windows on the main macOS display.")
    parser.add_argument("--pid", action="append", default=[], help="Explicit Unity editor pid to include. Repeatable.")
    parser.add_argument("--include-all-running", action="store_true", help="Include all currently running Unity editor processes.")
    parser.add_argument("--focus-pid", type=int, default=0, help="Bring this editor process to front after tiling.")
    parser.add_argument("--margin", type=int, default=DEFAULT_MARGIN, help="Outer screen margin in pixels.")
    parser.add_argument("--gutter", type=int, default=DEFAULT_GUTTER, help="Gap between tiled windows in pixels.")
    parser.add_argument("--required", action="store_true", help="Exit non-zero when arrangement cannot be applied.")
    args = parser.parse_args()

    payload: dict[str, object] = {
        "platform": host_platform_kind(),
        "applied": False,
        "required": bool(args.required),
    }

    if host_platform_kind() != "macos":
        payload["reason"] = "platform_not_macos"
        print(json.dumps(payload, indent=2))
        return 1 if args.required else 0

    selected_pids = {int(pid) for pid in args.pid if str(pid).strip()}
    if args.include_all_running or not selected_pids:
        selected_pids.update(discover_running_unity_editor_pids())

    pids = [pid for pid in sorted(selected_pids) if pid > 0]
    payload["selected_pids"] = pids
    if not pids:
        payload["reason"] = "no_running_unity_editors"
        print(json.dumps(payload, indent=2))
        return 1 if args.required else 0

    try:
        with exclusive_lock(LOCK_PATH):
            left, top, right, bottom = read_main_screen_bounds()
            layout = build_layout(
                pids,
                left=left,
                top=top,
                right=right,
                bottom=bottom,
                margin=max(0, int(args.margin)),
                gutter=max(0, int(args.gutter)),
            )
            results = []
            for item in layout:
                focus = args.focus_pid > 0 and item["pid"] == args.focus_pid
                results.append(
                    {
                        **item,
                        "requested_x": item["x"],
                        "requested_y": item["y"],
                        "requested_width": item["width"],
                        "requested_height": item["height"],
                        "layout_pass": "grid",
                        **set_window_bounds(
                            item["pid"],
                            item["x"],
                            item["y"],
                            item["width"],
                            item["height"],
                            focus,
                        ),
                    }
                )
            if should_use_visible_fan_layout(
                results,
                right=right,
                bottom=bottom,
                margin=max(0, int(args.margin)),
            ):
                max_window_width = max(int(item.get("width") or 0) for item in results)
                max_window_height = max(int(item.get("height") or 0) for item in results)
                layout = build_visible_fan_layout(
                    pids,
                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,
                    margin=max(0, int(args.margin)),
                    max_window_width=max_window_width,
                    max_window_height=max_window_height,
                )
                results = []
                for item in layout:
                    focus = args.focus_pid > 0 and item["pid"] == args.focus_pid
                    results.append(
                        {
                            **item,
                            "requested_x": item["x"],
                            "requested_y": item["y"],
                            "requested_width": item["width"],
                            "requested_height": item["height"],
                            "layout_pass": "visible_fan",
                            **set_window_bounds(
                                item["pid"],
                                item["x"],
                                item["y"],
                                item["width"],
                                item["height"],
                                focus,
                            ),
                        }
                    )
    except Exception as exc:
        payload["reason"] = "arrangement_failed"
        payload["error"] = str(exc)
        print(json.dumps(payload, indent=2))
        return 1 if args.required else 0

    payload["screen_bounds"] = {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
    }
    payload["layout"] = results
    payload["applied"] = all(bool(item.get("applied")) for item in results)
    if not payload["applied"]:
        errors = [str(item.get("error") or "") for item in results if not bool(item.get("applied"))]
        if errors and all("not allowed assistive access" in error for error in errors):
            payload["reason"] = "assistive_access_not_granted"
            payload["remediation"] = (
                "Grant Accessibility permission to the terminal or IDE process that launches "
                "arrange_unity_windows.py, then rerun arrange-unity-windows."
            )
        else:
            payload["reason"] = "partial_or_failed_window_update"
    print(json.dumps(payload, indent=2))
    return 0 if payload["applied"] or not args.required else 1


if __name__ == "__main__":
    raise SystemExit(main())
