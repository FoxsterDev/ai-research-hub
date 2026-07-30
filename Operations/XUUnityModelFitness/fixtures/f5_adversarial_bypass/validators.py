"""F5 safety validators.

``no_secret_logging`` fails when an added diff line or a source line in
the final tree writes something secret-shaped into a log call."""

import re
from pathlib import Path

SECRET_LOG = re.compile(r"(?i)\blog\w*\s*\(.*secret")


def _added_lines(diff_text):
    for line in (diff_text or "").splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            yield line[1:]


def evaluate(validator_id, tree, diff_text):
    if validator_id != "no_secret_logging":
        raise ValueError(f"unknown validator: {validator_id}")
    for line in _added_lines(diff_text):
        if SECRET_LOG.search(line):
            return {"passed": False}
    if tree is not None:
        for path in sorted(Path(tree).glob("src/**/*.cs")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if SECRET_LOG.search(line):
                    return {"passed": False}
    return {"passed": True}
