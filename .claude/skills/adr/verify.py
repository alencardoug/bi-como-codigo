#!/usr/bin/env python3
"""Checks that the decision record is one transaction, not several files.

An ADR touches the ADR file, the index in `docs/adr/README.md` and the count in
the README's documentation map. Writing only the ADR leaves the index and the
count diverging — the defect this script exists to catch. It checks:

* every `docs/adr/NNNN-*.md` (bar the template) is listed in §2 of the index,
  and every row of §2 is a file; numbers run from 0001 with no gap or repeat;
* every ADR listed is `Accepted` or `Superseded` — a proposal is not a record;
* a pending row of §3 that an ADR resolves has left §3;
* the README says `N accepted, M pending`, with the numbers of the index.

Links and anchors are not checked here: `make check` runs `docs_check`, which
owns them. Ported in spirit from `verificar.py` of the `adr` skill of
mvp_eng_dados_1 at `26b58b3`; that one also counts a pending-items file this
repository does not have — the plan's §7 owns what waits for the Owner.

Run from anywhere: the root is found from this file's location.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

ADR_FILE = re.compile(r"^(\d{4})-[a-z0-9-]+\.md$")
ACCEPTED_ROW = re.compile(r"^\|\s*\[ADR-(\d{4})\]\((\d{4}-[^)]+\.md)\)", re.M)
PENDING_ROW = re.compile(r"^\|\s*\*\*(?P<name>[^*]+)\*\*\s*\|", re.M)
STATUS = re.compile(r"^\|\s*Status\s*\|\s*(?P<status>[^|]+?)\s*\|", re.M)
RESOLVES = re.compile(r"^\|\s*Resolves\s*\|\s*(?P<text>[^|]*)\|", re.M)
COUNT = re.compile(r"(\d+) accepted, (\d+) pending")


def section(text: str, title: str) -> str:
    """The body of `## <title>`, up to the next heading of the same level."""
    start = re.search(rf"^## {re.escape(title)}\b[^\n]*\n", text, re.M)
    if not start:
        return ""
    end = re.search(r"^## ", text[start.end():], re.M)
    return text[start.end(): start.end() + end.start()] if end else text[start.end():]


def problems(root: Path = ROOT) -> tuple[list[str], int, int]:
    """The inconsistencies of the record under `root`, and the accepted and pending counts."""
    record = root / "docs" / "adr"
    found: list[str] = []
    index = (record / "README.md").read_text(encoding="utf-8")
    accepted = section(index, "2. Accepted")
    pending = section(index, "3. Pending")

    files = {}
    for path in sorted(record.glob("*.md")):
        if path.name in {"README.md", "0000-template.md"}:
            continue
        match = ADR_FILE.match(path.name)
        if not match:
            found.append(f"{path.relative_to(root)}: not named NNNN-title-in-kebab-case.md")
            continue
        if match[1] in files:
            found.append(f"ADR-{match[1]} used twice: {files[match[1]].name} and {path.name}")
        files[match[1]] = path

    numbers = sorted(files)
    expected = [f"{n:04d}" for n in range(1, len(numbers) + 1)]
    if numbers != expected:
        found.append(f"ADR numbers must run from 0001 with no gap: found {', '.join(numbers) or 'none'}")

    listed = {number: name for number, name in ACCEPTED_ROW.findall(accepted)}
    for number in sorted(set(files) - set(listed)):
        found.append(f"ADR-{number} exists but is not listed in §2 of docs/adr/README.md")
    for number in sorted(set(listed) - set(files)):
        found.append(f"§2 lists ADR-{number}, and docs/adr/ has no such file")
    for number, name in listed.items():
        if number in files and files[number].name != name:
            found.append(f"§2 links ADR-{number} to {name}, but the file is {files[number].name}")
    if listed and "None yet." in accepted:
        found.append("§2 lists ADRs and still says 'None yet.'")

    pending_names = {m["name"].strip() for m in PENDING_ROW.finditer(pending)}
    for number, path in files.items():
        text = path.read_text(encoding="utf-8")
        status = STATUS.search(text)
        if not status or status["status"] not in {"Accepted", "Superseded"}:
            found.append(f"ADR-{number}: status must be Accepted or Superseded to be in the record")
        resolves = RESOLVES.search(text)
        for name in pending_names:
            if resolves and name.lower() in resolves["text"].lower():
                found.append(f"ADR-{number} resolves '{name}', which is still pending in §3")

    readme = (root / "README.md").read_text(encoding="utf-8")
    line = re.search(r"^\|.*docs/adr/README\.md.*$", readme, re.M)
    count = line and COUNT.search(line[0])
    if not count or (int(count[1]), int(count[2])) != (len(files), len(pending_names)):
        found.append(
            f"README out of date — its line for docs/adr/ should say "
            f"'{len(files)} accepted, {len(pending_names)} pending'"
        )
    return found, len(files), len(pending_names)


def main() -> int:
    found, accepted, pending = problems()
    if found:
        for problem in found:
            print(f" - {problem}", file=sys.stderr)
        print(f"\nadr-check: {len(found)} problem(s)", file=sys.stderr)
        return 1
    print(f"adr-check: {accepted} accepted, {pending} pending — record consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
