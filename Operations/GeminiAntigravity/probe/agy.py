#!/usr/bin/env python3
"""Reusable headless Antigravity runner.

Usage: agy.py <cwd> <project_id> <model> <prompt-file>
Prints the conversation id and then the full readable transcript once complete.
"""
import json
import os
import re
import subprocess
import sys
import time

HOME = os.path.expanduser("~")
AGENTAPI = os.path.join(HOME, ".gemini", "antigravity", "bin", "agentapi")
BRAIN = os.path.join(HOME, ".gemini", "antigravity", "brain")


def ls_env():
    ps = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True)
    line = next(l for l in ps.stdout.splitlines()
                if "language_server" in l and "--csrf_token" in l)
    pid = line.split()[0]
    csrf = re.search(r"--csrf_token (\S+)", line).group(1)
    lsof = subprocess.run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN", "-a", "-p", pid],
                          capture_output=True, text=True)
    ports = sorted({int(m) for m in re.findall(r"127\.0\.0\.1:(\d+) \(LISTEN\)", lsof.stdout)})
    return csrf, ports


def run(cwd, project_id, model, prompt, title="agy-run", timeout=900):
    csrf, ports = ls_env()
    env = dict(os.environ)
    env["ANTIGRAVITY_CSRF_TOKEN"] = csrf
    env["ANTIGRAVITY_PROJECT_ID"] = project_id
    for port in reversed(ports):
        env["ANTIGRAVITY_LS_ADDRESS"] = f"127.0.0.1:{port}"
        r = subprocess.run([AGENTAPI, "new-conversation", f"--model={model}",
                            f"--title={title}", prompt],
                           cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "") + (r.stderr or "")
        m = re.search(r'"conversationId"\s*:\s*"([0-9a-f-]{36})"', out)
        if m:
            return m.group(1)
        last = out
    raise SystemExit("failed to start conversation:\n" + last[:2000])


def transcript(conv, skip_types=("USER_INPUT", "CHECKPOINT", "CONVERSATION_HISTORY")):
    p = os.path.join(BRAIN, conv, ".system_generated", "logs", "transcript.jsonl")
    if not os.path.exists(p):
        return None
    out = []
    for line in open(p):
        d = json.loads(line)
        if d.get("type") in skip_types:
            continue
        out.append((d.get("step_index"), d.get("source"), d.get("type"), d.get("content") or ""))
    return out


if __name__ == "__main__":
    cwd, project_id, model, prompt_file = sys.argv[1:5]
    prompt = open(prompt_file, encoding="utf-8").read()
    conv = run(cwd, project_id, model, prompt,
               title=os.path.basename(prompt_file).replace(".txt", ""))
    print("conversationId:", conv)
    for _ in range(60):
        t = transcript(conv)
        if t and any("COMPLETE" in c for *_, c in t):
            break
        time.sleep(3)
    for idx, src, typ, content in transcript(conv) or []:
        print(f"\n==== step {idx} {src} {typ} ====")
        print(content[:6000])
