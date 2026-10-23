"""Oracles of the `adr` skill's verifier: the record is one transaction.

Each way of leaving the record half-written has its counter-proof: a consistent
record passes, the break is introduced, and the problem is required.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("adr_verify", ROOT / ".claude" / "skills" / "adr" / "verify.py")
verify = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify)

INDEX = """\
# Decision record

## 2. Accepted

| ADR | Title | Date | Resolves |
|---|---|---|---|
{accepted}

## 3. Pending

| Pending | Decision in the plan | Written at |
|---|---|---|
{pending}
"""

ADR = """\
# ADR-{n} — Host the showcase

| Field | Information |
|---|---|
| Status | {status} |
| Resolves | {resolves} |
"""


def _record(
    root: pathlib.Path,
    *,
    adrs: dict[str, tuple[str, str]] | None = None,
    accepted: str = "None yet.",
    pending: str = "| **Hosting** | N2 | Stage 2.2 |\n| **CI pipeline** | N2 | Stage 2.2 |",
    count: str = "0 accepted, 2 pending",
) -> pathlib.Path:
    record = root / "docs" / "adr"
    record.mkdir(parents=True)
    (record / "README.md").write_text(INDEX.format(accepted=accepted, pending=pending), encoding="utf-8")
    (record / "0000-template.md").write_text("# ADR-NNNN\n", encoding="utf-8")
    for name, (status, resolves) in (adrs or {}).items():
        (record / name).write_text(ADR.format(n=name[:4], status=status, resolves=resolves), encoding="utf-8")
    (root / "README.md").write_text(
        f"| [`docs/adr/`](docs/adr/README.md) | The decision record: {count} |\n", encoding="utf-8"
    )
    return root


def test_empty_record_with_pending_rows_passes(tmp_path):
    assert verify.problems(_record(tmp_path)) == ([], 0, 2)


def test_closed_transaction_passes(tmp_path):
    root = _record(
        tmp_path,
        adrs={"0001-host-the-showcase.md": ("Accepted", "The pending row Hosting (N2)")},
        accepted="| [ADR-0001](0001-host-the-showcase.md) | Host the showcase | 2026-10-24 | Hosting |",
        pending="| **CI pipeline** | N2 | Stage 2.2 |",
        count="1 accepted, 1 pending",
    )
    assert verify.problems(root) == ([], 1, 1)


@pytest.mark.parametrize(
    "case, expected",
    [
        (
            dict(adrs={"0001-host-the-showcase.md": ("Accepted", "CI pipeline")}),
            "ADR-0001 exists but is not listed in §2",
        ),
        (
            dict(accepted="| [ADR-0001](0001-host-the-showcase.md) | Host | 2026-10-24 | Hosting |"),
            "§2 lists ADR-0001, and docs/adr/ has no such file",
        ),
        (
            dict(
                adrs={"0001-host-the-showcase.md": ("Accepted", "The pending row Hosting")},
                accepted="| [ADR-0001](0001-host-the-showcase.md) | Host | 2026-10-24 | Hosting |",
                count="1 accepted, 2 pending",
            ),
            "ADR-0001 resolves 'Hosting', which is still pending in §3",
        ),
        (
            dict(
                adrs={"0001-host-the-showcase.md": ("Proposed", "nothing")},
                accepted="| [ADR-0001](0001-host-the-showcase.md) | Host | 2026-10-24 | — |",
                count="1 accepted, 2 pending",
            ),
            "ADR-0001: status must be Accepted or Superseded",
        ),
        (
            dict(
                adrs={"0002-host-the-showcase.md": ("Accepted", "nothing")},
                accepted="| [ADR-0002](0002-host-the-showcase.md) | Host | 2026-10-24 | — |",
                count="1 accepted, 2 pending",
            ),
            "ADR numbers must run from 0001 with no gap",
        ),
        (
            dict(count="0 accepted, 3 pending"),
            "README out of date — its line for docs/adr/ should say '0 accepted, 2 pending'",
        ),
    ],
    ids=["not-indexed", "indexed-without-file", "resolved-still-pending", "proposal", "gap", "count"],
)
def test_half_written_record_is_flagged(tmp_path, case, expected):
    found, _, _ = verify.problems(_record(tmp_path, **case))
    assert any(expected in problem for problem in found), found


def test_the_record_of_this_repository_is_consistent():
    found, _, _ = verify.problems(ROOT)
    assert found == []
