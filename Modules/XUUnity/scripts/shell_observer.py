#!/usr/bin/env python3
"""Bounded, descriptor-aware shell observation for the fitness scorer.

Implements the P0 observer grammar from
``AIRoot/Design/XUUNITY_MODEL_FITNESS_AND_REDUCED_STACK_GATE_DESIGN.md``:

- quote-aware control-operator splitting (``&&``, ``||``, ``;``, ``|``,
  newline) with heredoc stripping;
- redirects parsed per file descriptor, so ``2>/dev/null`` is never a
  workspace mutation while ``> file`` always is;
- read verification against the required-file manifest by exact content
  hash (``cat``, ``tail -n +1`` incl. the multi-file header format) or by
  verified line intervals (``sed -n``, ``head -n``);
- multi-file output partitioned per operand — an extra non-manifest operand
  makes only the unverifiable remainder unsupported, never the already
  proven files;
- everything outside the grammar is classified ``ambiguous`` or
  ``unsupported`` explicitly and fails closed downstream instead of being
  silently dropped or converted to absence.
"""

from __future__ import annotations

import hashlib
import os
import re
import shlex
from dataclasses import dataclass, field
from typing import Any, Callable

NULL_SINKS = {"/dev/null"}
INERT_REDIRECT_TARGETS = {"/dev/null", "/dev/stdout", "/dev/stderr", "/dev/tty"}

READ_CREDIT_PROGRAMS = {"cat", "tail", "head", "sed"}

READ_ONLY_PROGRAMS = {
    "cat", "tail", "head", "sed", "rg", "grep", "egrep", "fgrep", "zgrep",
    "ls", "wc", "sort", "uniq", "cut", "tr", "echo", "printf", "pwd",
    "true", "false", ":", "test", "[", "jq", "basename", "dirname", "stat",
    "file", "which", "nl", "comm", "diff", "od", "xxd", "strings", "column",
    "date", "uname", "readlink", "realpath", "du", "df", "whoami",
    "hostname", "type", "command", "hexdump", "md5", "md5sum", "shasum",
    "sha256sum", "find", "git", "env", "wc", "expr", "seq", "yes",
}

MUTATOR_PROGRAMS = {
    "apply_patch", "patch", "tee", "cp", "mv", "rm", "mkdir", "rmdir",
    "touch", "truncate", "dd", "ln", "install", "rsync", "chmod", "chown",
    "unzip",
}

GIT_READ_ONLY_SUBCOMMANDS = {
    "status", "log", "show", "diff", "grep", "rev-parse", "ls-files",
    "blame", "describe", "cat-file", "ls-tree", "rev-list", "shortlog",
    "branch", "tag", "remote", "config", "count-objects", "var", "help",
    "add", "commit", "reflog", "merge-base", "show-ref", "for-each-ref",
    "name-rev", "diff-tree", "diff-index", "whatchanged", "cherry",
    "check-ignore", "check-attr", "ls-remote", "verify-commit",
    "verify-tag", "fetch",
}

GIT_MUTATING_SUBCOMMANDS = {
    "apply", "am", "checkout", "restore", "revert", "merge", "rebase",
    "cherry-pick", "mv", "rm", "clean", "reset", "stash", "pull", "switch",
    "worktree", "submodule",
}

SHELL_WRAPPERS = {"bash", "zsh", "sh"}

PARTIAL_READ_MARKERS = re.compile(
    r"(?:output truncated|content truncated|lines? omitted|"
    r"file has more than|use offset to read|…\s*\+\d+\s*lines?)",
    re.IGNORECASE,
)

_TAIL_HEADER = re.compile(r"(?:^|\n)==> (.*?) <==\n")


@dataclass(frozen=True)
class Redirect:
    fd: str
    op: str
    target: str | None


@dataclass(frozen=True)
class SimpleCommand:
    argv: tuple[str, ...]
    redirects: tuple[Redirect, ...]
    raw: str
    ambiguous_reason: str | None = None


@dataclass
class ShellRead:
    path: str
    proof: str  # proven | partial | unsupported | failed
    intervals: tuple[tuple[int, int], ...] = ()


@dataclass
class ShellEvaluation:
    reads: list[ShellRead] = field(default_factory=list)
    mutation_targets: list[str] = field(default_factory=list)
    parser_result: str = "recognized"  # recognized | unsupported | ambiguous
    programs: tuple[str, ...] = ()
    required_paths_mentioned: tuple[str, ...] = ()


def _strip_heredocs(command: str) -> tuple[str, bool]:
    result: list[str] = []
    index = 0
    quote: str | None = None
    escaped = False
    length = len(command)
    while index < length:
        character = command[index]
        if escaped:
            result.append(character)
            escaped = False
            index += 1
            continue
        if character == "\\" and quote != "'":
            result.append(character)
            escaped = True
            index += 1
            continue
        if quote:
            result.append(character)
            if character == quote:
                quote = None
            index += 1
            continue
        if character in {"'", '"'}:
            quote = character
            result.append(character)
            index += 1
            continue
        if command.startswith("<<", index) and not command.startswith("<<<", index):
            cursor = index + 2
            if cursor < length and command[cursor] == "-":
                cursor += 1
            while cursor < length and command[cursor] in " \t":
                cursor += 1
            delimiter_quote = ""
            if cursor < length and command[cursor] in {"'", '"'}:
                delimiter_quote = command[cursor]
                cursor += 1
            start = cursor
            while cursor < length and (
                command[cursor].isalnum() or command[cursor] in "_-"
            ):
                cursor += 1
            delimiter = command[start:cursor]
            if delimiter_quote:
                if cursor >= length or command[cursor] != delimiter_quote:
                    return command, False
                cursor += 1
            if not delimiter:
                return command, False
            newline = command.find("\n", cursor)
            if newline == -1:
                return command, False
            body_start = newline + 1
            terminator = None
            offset = body_start
            while offset <= length:
                line_end = command.find("\n", offset)
                if line_end == -1:
                    line = command[offset:]
                    line_end = length
                else:
                    line = command[offset:line_end]
                if line.lstrip("\t") == delimiter:
                    terminator = line_end
                    break
                offset = line_end + 1
                if line_end == length:
                    break
            if terminator is None:
                return command, False
            result.append(command[index:newline])
            index = terminator
            continue
        result.append(character)
        index += 1
    if quote:
        return command, False
    return "".join(result), True


def _split_control(command: str) -> tuple[list[str], list[str], bool]:
    segments: list[str] = []
    operators: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    index = 0
    ok = True
    while index < len(command):
        character = command[index]
        if escaped:
            current.append(character)
            escaped = False
            index += 1
            continue
        if character == "\\" and quote != "'":
            current.append(character)
            escaped = True
            index += 1
            continue
        if quote:
            current.append(character)
            if character == quote:
                quote = None
            index += 1
            continue
        if character in {"'", '"'}:
            quote = character
            current.append(character)
            index += 1
            continue
        operator = ""
        if command.startswith("&&", index) or command.startswith("||", index):
            operator = command[index : index + 2]
        elif command.startswith("|&", index):
            operator = "|"
            index += 1
        elif character in {";", "|", "\n"}:
            operator = character
        elif character == "&":
            duplication = (index > 0 and command[index - 1] in "<>") or (
                index + 1 < len(command) and command[index + 1] == ">"
            )
            if not duplication:
                ok = False
        elif character in {"(", ")"}:
            ok = False
        if operator:
            segment = "".join(current).strip()
            if segment:
                segments.append(segment)
                operators.append(operator)
            elif operators:
                pass
            current = []
            index += len(operator)
            continue
        current.append(character)
        index += 1
    segment = "".join(current).strip()
    if segment:
        segments.append(segment)
    else:
        if operators:
            operators.pop()
    if quote:
        ok = False
    return segments, operators, ok


def _has_active_substitution(segment: str) -> bool:
    quote: str | None = None
    escaped = False
    index = 0
    while index < len(segment):
        character = segment[index]
        if escaped:
            escaped = False
            index += 1
            continue
        if character == "\\" and quote != "'":
            escaped = True
            index += 1
            continue
        if quote == "'":
            if character == "'":
                quote = None
            index += 1
            continue
        if quote == '"':
            if character == '"':
                quote = None
            elif character == "`" or segment.startswith("$(", index):
                return True
            index += 1
            continue
        if character in {"'", '"'}:
            quote = character
            index += 1
            continue
        if character == "`" or segment.startswith("$(", index):
            return True
        if segment.startswith("<(", index) or segment.startswith(">(", index):
            return True
        index += 1
    return False


def _extract_redirects(segment: str) -> tuple[str, list[Redirect], bool]:
    remainder: list[str] = []
    redirects: list[Redirect] = []
    quote: str | None = None
    escaped = False
    index = 0
    length = len(segment)
    while index < length:
        character = segment[index]
        if escaped:
            remainder.append(character)
            escaped = False
            index += 1
            continue
        if character == "\\" and quote != "'":
            remainder.append(character)
            escaped = True
            index += 1
            continue
        if quote:
            remainder.append(character)
            if character == quote:
                quote = None
            index += 1
            continue
        if character in {"'", '"'}:
            quote = character
            remainder.append(character)
            index += 1
            continue
        if character in {">", "<"} or (
            character in "0123456789&"
            and index + 1 < length
            and segment[index + 1] in {">", "<"}
            and (index == 0 or segment[index - 1] in " \t")
        ):
            fd = ""
            if character in "0123456789&":
                fd = character
                index += 1
            op_char = segment[index]
            op = op_char
            index += 1
            if index < length and segment[index] == op_char:
                op += op_char
                index += 1
            elif op == ">" and index < length and segment[index] == "|":
                op += "|"
                index += 1
            if op == "<<":
                # Bodies were already stripped by _strip_heredocs; consume
                # the remaining marker and delimiter word without recording.
                if index < length and segment[index] == "-":
                    index += 1
                while index < length and segment[index] in " \t":
                    index += 1
                delimiter_quote = ""
                if index < length and segment[index] in {"'", '"'}:
                    delimiter_quote = segment[index]
                    index += 1
                while index < length and (
                    segment[index].isalnum() or segment[index] in "_-"
                ):
                    index += 1
                if delimiter_quote and index < length and segment[index] == delimiter_quote:
                    index += 1
                continue
            if index < length and segment[index] == "&":
                index += 1
                while index < length and segment[index].isdigit():
                    index += 1
                redirects.append(Redirect(fd or ("1" if ">" in op else "0"), op, None))
                continue
            while index < length and segment[index] in " \t":
                index += 1
            target_chars: list[str] = []
            target_quote: str | None = None
            while index < length:
                target_character = segment[index]
                if target_quote:
                    if target_character == target_quote:
                        target_quote = None
                    else:
                        target_chars.append(target_character)
                    index += 1
                    continue
                if target_character in {"'", '"'}:
                    target_quote = target_character
                    index += 1
                    continue
                if target_character in " \t\n;|&<>":
                    break
                target_chars.append(target_character)
                index += 1
            target = "".join(target_chars)
            if not target:
                return segment, [], False
            default_fd = "0" if op == "<" else "1"
            redirects.append(Redirect(fd or default_fd, op, target))
            continue
        remainder.append(character)
        index += 1
    if quote:
        return segment, [], False
    return "".join(remainder), redirects, True


def _parse_simple(segment: str) -> SimpleCommand:
    if _has_active_substitution(segment):
        return SimpleCommand((), (), segment, "command_substitution")
    remainder, redirects, ok = _extract_redirects(segment)
    if not ok:
        return SimpleCommand((), (), segment, "redirect_parse")
    try:
        tokens = shlex.split(remainder)
    except ValueError:
        return SimpleCommand((), (), segment, "token_parse")
    while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
        tokens.pop(0)
    if tokens and os.path.basename(tokens[0]) == "env":
        tokens.pop(0)
        while tokens and (
            re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0])
            or tokens[0].startswith("-")
        ):
            tokens.pop(0)
    return SimpleCommand(tuple(tokens), tuple(redirects), segment)


def _program(command: SimpleCommand) -> str:
    if not command.argv:
        return ""
    return os.path.basename(command.argv[0])


def _mutating_redirect_targets(command: SimpleCommand) -> list[str]:
    targets: list[str] = []
    for redirect in command.redirects:
        if redirect.op in {">", ">>", ">|"} and redirect.target is not None:
            if redirect.target not in INERT_REDIRECT_TARGETS:
                targets.append(redirect.target)
    return targets


def _stdout_redirected(command: SimpleCommand) -> bool:
    return any(
        redirect.fd in {"1", "&"} and redirect.op in {">", ">>", ">|"}
        for redirect in command.redirects
    )


def _classify_simple(command: SimpleCommand) -> tuple[str, list[str]]:
    """Return (classification, mutation_targets).

    classification: read_credit | inert | mutation | ambiguous
    """
    if command.ambiguous_reason:
        return "ambiguous", []
    if not command.argv:
        return "inert", []
    program = _program(command)
    targets = _mutating_redirect_targets(command)
    argv = command.argv

    if program == "git":
        subcommand = next(
            (token for token in argv[1:] if not token.startswith("-")), ""
        )
        if subcommand in GIT_READ_ONLY_SUBCOMMANDS:
            return ("mutation", targets) if targets else ("inert", [])
        if subcommand in GIT_MUTATING_SUBCOMMANDS:
            operands = [
                token
                for token in argv[1:]
                if not token.startswith("-") and token != subcommand
            ]
            return "mutation", targets + (operands or ["<shell-mutation>"])
        return "ambiguous", []
    if program == "find":
        unsafe = {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fls"}
        if any(token in unsafe for token in argv[1:]):
            return "ambiguous", []
        return ("mutation", targets) if targets else ("inert", [])
    if program == "sed" and any(
        token == "-i" or token.startswith("-i") and len(token) > 2 and token[2] != "n"
        or token == "--in-place"
        for token in argv[1:]
        if token.startswith("-")
    ):
        operands = [token for token in argv[1:] if not token.startswith("-")]
        return "mutation", targets + (operands[1:] or ["<shell-mutation>"])
    if program == "sort" and "-o" in argv:
        output_index = argv.index("-o")
        if output_index + 1 < len(argv):
            return "mutation", targets + [argv[output_index + 1]]
        return "ambiguous", []
    if program in MUTATOR_PROGRAMS:
        operands = [token for token in argv[1:] if not token.startswith("-")]
        if program == "tee":
            return "mutation", targets + (operands or ["<shell-mutation>"])
        if program in {"cp", "mv", "ln", "install"}:
            return "mutation", targets + (operands[-1:] or ["<shell-mutation>"])
        if program in {"rm", "mkdir", "rmdir", "touch", "truncate"}:
            return "mutation", targets + (operands or ["<shell-mutation>"])
        return "mutation", targets + ["<shell-mutation>"]
    if program in READ_ONLY_PROGRAMS:
        if targets:
            return "mutation", targets
        if program in READ_CREDIT_PROGRAMS:
            return "read_credit", []
        return "inert", []
    return "ambiguous", []


def _sed_interval(expression: str) -> tuple[int, int | None] | None:
    expression = expression.strip()
    match = re.fullmatch(r"(\d+),(\d+|\$)p", expression)
    if match:
        start = int(match.group(1))
        end = None if match.group(2) == "$" else int(match.group(2))
        return (start, end)
    match = re.fullmatch(r"(\d+)p", expression)
    if match:
        value = int(match.group(1))
        return (value, value)
    return None


def _head_count(argv: tuple[str, ...]) -> int | None:
    tokens = list(argv[1:])
    index = 0
    count: int | None = None
    while index < len(tokens):
        token = tokens[index]
        if token == "-n" and index + 1 < len(tokens):
            raw = tokens[index + 1]
            index += 2
        elif token.startswith("-n") and len(token) > 2:
            raw = token[2:]
            index += 1
        elif re.fullmatch(r"-\d+", token):
            raw = token[1:]
            index += 1
        else:
            if token.startswith("-"):
                return None
            index += 1
            continue
        try:
            count = int(raw)
        except ValueError:
            return None
    return count


def _operands(argv: tuple[str, ...]) -> list[str]:
    operands = []
    skip_next = False
    for token in argv[1:]:
        if skip_next:
            skip_next = False
            continue
        if token in {"-n", "-e", "-c"}:
            skip_next = True
            continue
        if token.startswith("-") and token != "-":
            continue
        operands.append(token)
    return operands


class _ByteWalker:
    def __init__(self, content: bytes):
        self.content = content
        self.offset = 0

    def slice(self, count: int) -> bytes | None:
        if self.offset + count > len(self.content):
            return None
        value = self.content[self.offset : self.offset + count]
        self.offset += count
        return value

    def remainder(self) -> bytes:
        value = self.content[self.offset :]
        self.offset = len(self.content)
        return value

    @property
    def exhausted(self) -> bool:
        return self.offset >= len(self.content)


def _verify_reads(
    read_segments: list[SimpleCommand],
    output: str,
    normalize: Callable[[str], str],
    manifest_entry: Callable[[str], dict[str, Any] | None],
) -> list[ShellRead] | None:
    """Verify ordered read-credit segments against the full command output.

    Returns None when the combination is outside the supported verification
    grammar; the caller downgrades the reads to unsupported.
    """
    reads: list[ShellRead] = []
    walker = _ByteWalker(output.encode("utf-8"))
    for position, segment in enumerate(read_segments):
        program = _program(segment)
        is_last = position == len(read_segments) - 1
        if _stdout_redirected(segment):
            return None
        if program == "cat":
            operands = _operands(segment.argv)
            if not operands or any(operand == "-" for operand in operands):
                return None
            for operand_index, operand in enumerate(operands):
                path = normalize(operand)
                entry = manifest_entry(path)
                expected_bytes = int((entry or {}).get("bytes") or -1)
                expected_hash = str((entry or {}).get("sha256") or "")
                if expected_bytes < 0 or not expected_hash:
                    for remaining in operands[operand_index:]:
                        reads.append(ShellRead(normalize(remaining), "unsupported"))
                    if not is_last:
                        for later in read_segments[position + 1 :]:
                            for later_operand in _operands(later.argv):
                                reads.append(
                                    ShellRead(normalize(later_operand), "unsupported")
                                )
                    return reads
                observed = walker.slice(expected_bytes)
                if observed is None:
                    reads.append(ShellRead(path, "partial"))
                    continue
                digest = hashlib.sha256(observed).hexdigest()
                reads.append(
                    ShellRead(path, "proven" if digest == expected_hash else "partial")
                )
        elif program == "tail":
            argv = segment.argv
            tokens = list(argv[1:])
            full_form = False
            if "-n" in tokens:
                flag_index = tokens.index("-n")
                full_form = (
                    flag_index + 1 < len(tokens)
                    and tokens[flag_index + 1] == "+1"
                )
            elif any(token == "-n+1" for token in tokens):
                full_form = True
            operands = [
                token
                for token in tokens
                if not token.startswith("-") and token != "+1"
            ]
            if not full_form or not operands:
                return None
            if len(operands) == 1:
                path = normalize(operands[0])
                entry = manifest_entry(path)
                expected_bytes = int((entry or {}).get("bytes") or -1)
                expected_hash = str((entry or {}).get("sha256") or "")
                if expected_bytes < 0 or not expected_hash:
                    reads.append(ShellRead(path, "unsupported"))
                    return reads if is_last else None
                observed = walker.slice(expected_bytes)
                if observed is None:
                    reads.append(ShellRead(path, "partial"))
                    continue
                digest = hashlib.sha256(observed).hexdigest()
                reads.append(
                    ShellRead(path, "proven" if digest == expected_hash else "partial")
                )
            else:
                if not is_last:
                    return None
                remainder = walker.remainder().decode("utf-8", errors="replace")
                sections: dict[str, str] = {}
                parts = _TAIL_HEADER.split(remainder)
                if len(parts) < 3 or parts[0].strip():
                    for operand in operands:
                        reads.append(ShellRead(normalize(operand), "unsupported"))
                    return reads
                names = parts[1::2]
                bodies = parts[2::2]
                for name, body in zip(names, bodies):
                    sections[normalize(name)] = body
                for operand in operands:
                    path = normalize(operand)
                    entry = manifest_entry(path)
                    expected_hash = str((entry or {}).get("sha256") or "")
                    body = sections.get(path)
                    if body is None:
                        reads.append(ShellRead(path, "partial"))
                        continue
                    if not expected_hash:
                        reads.append(ShellRead(path, "unsupported"))
                        continue
                    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                    reads.append(
                        ShellRead(
                            path,
                            "proven" if digest == expected_hash else "partial",
                        )
                    )
        elif program in {"sed", "head"}:
            if not is_last:
                return None
            if program == "sed":
                tokens = list(segment.argv[1:])
                if "-n" not in tokens:
                    return None
                expression_index = tokens.index("-n") + 1
                expression = (
                    tokens[expression_index]
                    if expression_index < len(tokens)
                    else ""
                )
                operand_tokens = [
                    token
                    for token_index, token in enumerate(tokens)
                    if not token.startswith("-")
                    and token_index != expression_index
                ]
                requested = _sed_interval(expression)
            else:
                count = _head_count(segment.argv)
                requested = (1, count) if count else None
                operand_tokens = _operands(segment.argv)
            if len(operand_tokens) != 1 or requested is None:
                return None
            path = normalize(operand_tokens[0])
            entry = manifest_entry(path)
            expected_lines = int((entry or {}).get("lines") or 0)
            if expected_lines <= 0:
                reads.append(ShellRead(path, "unsupported"))
                return reads
            start, requested_end = requested
            end = min(requested_end or expected_lines, expected_lines)
            if start > end:
                reads.append(ShellRead(path, "partial"))
                return reads
            remainder = walker.remainder().decode("utf-8", errors="replace")
            observed_lines = len(remainder.splitlines())
            if observed_lines == end - start + 1:
                reads.append(ShellRead(path, "proven", ((start, end),)))
            else:
                reads.append(ShellRead(path, "partial"))
        else:
            return None
    if not walker.exhausted:
        trailing = walker.remainder()
        if trailing.strip():
            return [
                ShellRead(read.path, "partial", ())
                if read.proof == "proven" and not read.intervals
                else read
                for read in reads
            ]
    return reads


def evaluate_shell_command(
    command: str,
    cwd: str | None,
    manifest: dict[str, Any],
    result_content: str,
    succeeded: bool,
    normalize: Callable[[str, str | None], str],
    depth: int = 0,
) -> ShellEvaluation:
    evaluation = ShellEvaluation()
    if depth > 4:
        evaluation.parser_result = "ambiguous"
        return evaluation

    def normalize_path(value: str) -> str:
        return normalize(value, cwd)

    def manifest_entry(path: str) -> dict[str, Any] | None:
        entry = manifest.get(path)
        return entry if isinstance(entry, dict) else None

    stripped, heredoc_ok = _strip_heredocs(command)
    if not heredoc_ok:
        evaluation.parser_result = "ambiguous"
        return evaluation
    segments, operators, split_ok = _split_control(stripped)
    if not split_ok:
        evaluation.parser_result = "ambiguous"
        return evaluation

    pipelines: list[list[SimpleCommand]] = []
    current: list[SimpleCommand] = []
    for index, segment in enumerate(segments):
        current.append(_parse_simple(segment))
        joined_by_pipe = index < len(operators) and operators[index] == "|"
        if not joined_by_pipe:
            pipelines.append(current)
            current = []
    if current:
        pipelines.append(current)

    single_wrapper = (
        len(pipelines) == 1
        and len(pipelines[0]) == 1
        and pipelines[0][0].argv
        and _program(pipelines[0][0]) in SHELL_WRAPPERS
        and len(pipelines[0][0].argv) >= 3
        and pipelines[0][0].argv[1] in {"-c", "-lc", "-lic"}
    )
    if single_wrapper:
        return evaluate_shell_command(
            pipelines[0][0].argv[2],
            cwd,
            manifest,
            result_content,
            succeeded,
            normalize,
            depth + 1,
        )

    programs: list[str] = []
    classifications: list[str] = []
    read_segments: list[SimpleCommand] = []
    output_poisoned = False
    mentioned: set[str] = set()

    for pipeline in pipelines:
        stage_classes: list[str] = []
        for stage in pipeline:
            program = _program(stage)
            if program:
                programs.append(program)
            if program in SHELL_WRAPPERS and len(stage.argv) >= 3:
                stage_classes.append("ambiguous")
                continue
            classification, targets = _classify_simple(stage)
            stage_classes.append(classification)
            for target in targets:
                evaluation.mutation_targets.append(normalize_path(target))
            for token in stage.argv[1:]:
                if token.startswith("-"):
                    continue
                normalized = normalize_path(token)
                if normalized in manifest:
                    mentioned.add(normalized)
        if "mutation" in stage_classes:
            classifications.append("mutation")
        elif "ambiguous" in stage_classes:
            classifications.append("ambiguous")
        elif len(pipeline) == 1 and stage_classes == ["read_credit"]:
            classifications.append("read_credit")
            read_segments.append(pipeline[0])
        else:
            classifications.append("inert")
            head = pipeline[0]
            program = _program(head)
            produces_output = program not in {
                "true", "false", ":", "test", "[",
            } and not _stdout_redirected(pipeline[-1])
            if produces_output:
                output_poisoned = True
            for stage, stage_class in zip(pipeline, stage_classes):
                if stage_class != "read_credit":
                    continue
                for operand in _operands(stage.argv):
                    normalized = normalize_path(operand)
                    if normalized in manifest:
                        evaluation.reads.append(
                            ShellRead(normalized, "unsupported")
                        )

    if "ambiguous" in classifications:
        evaluation.parser_result = "ambiguous"
        for path in sorted(mentioned):
            if not any(read.path == path for read in evaluation.reads):
                evaluation.reads.append(ShellRead(path, "unsupported"))
    evaluation.programs = tuple(dict.fromkeys(programs))
    evaluation.required_paths_mentioned = tuple(sorted(mentioned))

    if not read_segments:
        return evaluation

    if not succeeded:
        for segment in read_segments:
            for operand in _operands(segment.argv):
                path = normalize_path(operand)
                if manifest_entry(path):
                    evaluation.reads.append(ShellRead(path, "failed"))
        return evaluation

    verified: list[ShellRead] | None = None
    if (
        not output_poisoned
        and evaluation.parser_result == "recognized"
        and not PARTIAL_READ_MARKERS.search(result_content)
    ):
        verified = _verify_reads(
            read_segments, result_content, normalize_path, manifest_entry
        )
    if verified is None:
        for segment in read_segments:
            for operand in _operands(segment.argv):
                path = normalize_path(operand)
                if manifest_entry(path):
                    evaluation.reads.append(ShellRead(path, "unsupported"))
    else:
        evaluation.reads.extend(
            read for read in verified if manifest_entry(read.path)
        )
    return evaluation
