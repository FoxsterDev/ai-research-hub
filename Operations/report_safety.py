#!/usr/bin/env python3
"""Shared safety primitives for operational report generators.

This module deliberately has no third-party dependencies so Python engines and
launchd wrappers can use the same redaction and atomic-write boundary.
"""

import argparse
import json
import os
import re
import sys
import tempfile


_REDACTIONS = (
    (re.compile(r"(\bbearer\s+)([A-Za-z0-9._\-]{8,})", re.I), r"\1[REDACTED]"),
    (re.compile(r"(://[^:/\s]+:)([^@/\s]+)(@)"), r"\1[REDACTED]\3"),
    (re.compile(r"(\b(?:authorization|proxy-authorization)\s*[:=]\s*(?:bearer|basic)?\s*)([^\s,;]+)", re.I),
     r"\1[REDACTED]"),
    (re.compile(r"(\b(?:password|passwd|pwd|api[_-]?key|apikey|access[_-]?token|auth[_-]?token|"
                r"client[_-]?secret|secret|signature|sig|x-amz-signature|x-goog-signature|token)"
                r"\s*[:=]\s*)([^\s,;&]+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"([?&](?:token|access_token|api_key|key|secret|signature|sig|x-amz-signature|"
                r"x-goog-signature|x-amz-credential|x-goog-credential)=)([^&#\s]+)", re.I),
     r"\1[REDACTED]"),
    (re.compile(r"-----BEGIN [^-\r\n]*(?:PRIVATE KEY|CERTIFICATE)-----.*?"
                r"(?:-----END [^-\r\n]*(?:PRIVATE KEY|CERTIFICATE)-----|\Z)", re.I | re.S),
     "[REDACTED PEM BLOCK]"),
)


def redact(value):
    """Return text with credential-bearing forms removed."""
    text = str(value or "")
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def safe_error(error, limit=400):
    return redact(f"{type(error).__name__}: {error}").replace("\n", " ")[:limit]


def redact_tree(value):
    """Redact string leaves without risking corruption of serialized JSON syntax."""
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {key: redact_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_tree(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_tree(item) for item in value)
    return value


def atomic_write_text(path, text, encoding="utf-8"):
    """Durably replace *path* from a same-directory temporary file."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{os.path.basename(path)}.", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        try:
            dir_fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def atomic_write_json(path, value, **kwargs):
    atomic_write_text(path, json.dumps(redact_tree(value), **kwargs) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Redact operational text from stdin.")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    output = redact(sys.stdin.read()).replace("\r", " ").replace("\n", " ").strip()
    if args.limit > 0:
        output = output[:args.limit]
    sys.stdout.write(output)


if __name__ == "__main__":
    main()
