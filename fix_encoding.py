#!/usr/bin/env python3
"""Repair UTF-8 text that was previously decoded as Windows-1251.

Targets the active  source files observed in the repository:
  agent/main.py, agent/tools.py, agent/prompts.py

Originals are copied to a timestamped sibling directory before any write.
"""

from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGETS = (
    Path("agent/main.py"),
    Path("agent/tools.py"),
    Path("agent/prompts.py"),
)

# Typical fingerprints of UTF-8 bytes misread as Windows-1251, plus C1
# control characters left behind for undefined Windows-1251 byte values.
MOJIBAKE_RE = re.compile(
    r"(?:Р[\u0400-\u04FF]|С[\u0400-\u04FF]|вЂ|[\u0080-\u009F])"
)


def mojibake_score(value: str) -> int:
    return len(MOJIBAKE_RE.findall(value))


def reverse_cp1251_mojibake(value: str) -> str:
    """Reverse UTF-8 -> Windows-1251 mojibake, including undefined bytes."""
    raw = bytearray()
    for char in value:
        codepoint = ord(char)
        # Undefined CP1251 bytes can appear as C1 controls (e.g. U+0098).
        if 0x80 <= codepoint <= 0x9F:
            raw.append(codepoint)
        else:
            raw.extend(char.encode("cp1251", errors="strict"))
    return bytes(raw).decode("utf-8", errors="strict")


def repair_line(line: str) -> tuple[str, bool]:
    current = line
    changed = False

    # One pass fixes the usual case; a second handles accidental double
    # conversion without repeatedly rewriting already-correct text.
    for _ in range(2):
        before = mojibake_score(current)
        if before == 0:
            break
        try:
            candidate = reverse_cp1251_mojibake(current)
        except (UnicodeEncodeError, UnicodeDecodeError):
            break

        after = mojibake_score(candidate)
        if after >= before:
            break

        current = candidate
        changed = True

    return current, changed


def main() -> int:
    root = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    if not root.is_dir():
        print(f"ERROR: project directory not found: {root}")
        return 2

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = root.parent / f"{root.name}_encoding_backup_{timestamp}"

    changed_files = 0
    changed_lines_total = 0
    missing_files: list[str] = []

    for relative_path in TARGETS:
        path = root / relative_path
        if not path.is_file():
            missing_files.append(str(relative_path))
            continue

        original_bytes = path.read_bytes()
        has_bom = original_bytes.startswith(b"\xef\xbb\xbf")

        try:
            original_text = original_bytes.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            print(f"SKIP (not valid UTF-8): {relative_path}: {exc}")
            continue

        repaired_lines: list[str] = []
        changed_lines = 0
        for line in original_text.splitlines(keepends=True):
            repaired, changed = repair_line(line)
            repaired_lines.append(repaired)
            if changed:
                changed_lines += 1

        if changed_lines == 0:
            print(f"OK / no mojibake detected: {relative_path}")
            continue

        repaired_text = "".join(repaired_lines)
        backup_path = backup_root / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)

        output = repaired_text.encode("utf-8")
        if has_bom:
            output = b"\xef\xbb\xbf" + output
        path.write_bytes(output)

        changed_files += 1
        changed_lines_total += changed_lines
        print(f"FIXED: {relative_path} ({changed_lines} lines)")

    print()
    print(f"Changed files: {changed_files}")
    print(f"Changed lines: {changed_lines_total}")
    if changed_files:
        print(f"Original files backed up to: {backup_root}")
    else:
        print("No changes were necessary.")
    if missing_files:
        print("Files not found (skipped): " + ", ".join(missing_files))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
