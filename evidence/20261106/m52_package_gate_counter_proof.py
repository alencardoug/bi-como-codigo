"""M52: the counter-proof of every check of the package gate (docs/package_gate.md §9.2).

For each check of stage 2.2b, a copy of the package `bi_como_codigo` is
written to a temporary directory with that one check made to pass, and the
tests of its mutation are run against the copy. A mutant is *killed* when at
least one of its tests fails — the mutation no longer stops at its check.
Every mutant must be killed; the unmodified copy must pass the same tests.

Run from the repository root, with the locked environment:

    uv run --frozen python evidence/20261106/m52_package_gate_counter_proof.py

It writes only under a temporary directory, prints one line per mutant and a
summary, and exits 1 if any mutant survives or the control fails.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
GATE = "tests/test_package_gate.py"
ENVELOPE = "tests/test_envelope.py"

#: (check, file, exact text, its replacement, tests: (file, -k expression)); a
#: mutant of several files gives a list of (file, text, replacement) and None.
MUTANTS = [
    ("declarations_agree", "contract.py", "        raise Refused(DECLARATIONS_AGREE)", "        pass", (GATE, "declarations_agree")),
    ("inventory_exact", "contract.py", "        raise Refused(INVENTORY_EXACT)", "        pass", (GATE, "mut08 or mut09")),
    ("entitlements_exact", "contract.py", "        raise Refused(ENTITLEMENTS_EXACT)", "        pass", (GATE, "mut10")),
    ("schema_exact", "contract.py", "        raise Refused(SCHEMA_EXACT, report.id)", "        pass", (GATE, "mut11 or mut12")),
    ("not_null", "contract.py", "            raise Refused(NOT_NULL, report.id, c.name)", "            pass", (GATE, "mut14")),
    ("grain_unique", "contract.py", "        raise Refused(GRAIN_UNIQUE, report.id)", "        pass", (GATE, "mut13")),
    ("totals_rows", "contract.py", "        raise Refused(TOTALS_ROWS, report.id)", "        pass", (GATE, "mut15 and rows")),
    ("totals_sums", "contract.py", "        if totals[\"sums\"][name] != got:\n            raise Refused(TOTALS_SUMS, report.id, name)",
     "        if False:\n            raise Refused(TOTALS_SUMS, report.id, name)", (GATE, "mut15 and sum")),
    ("totals_shape (keys)", "contract.py",
     "    if not ok or not isinstance(data, dict) or set(data) != {\"contract_version\", \"report_version\", \"rows\", \"sums\"}:\n        raise Refused(TOTALS_SHAPE, report.id)",
     "    if not ok or not isinstance(data, dict):\n        raise Refused(TOTALS_SHAPE, report.id)", (GATE, "mut16 and extra_key")),
    ("totals_shape (types)", "contract.py", "    if any(not isinstance(v, str) for v in sums.values()):\n        raise Refused(TOTALS_SHAPE, report.id)",
     "    if False:\n        raise Refused(TOTALS_SHAPE, report.id)", (GATE, "mut16 and number")),
    ("totals_version", "contract.py", "        raise Refused(TOTALS_VERSION, report.id)", "        pass", (GATE, "mut17")),
    ("content_bound", "contract.py", "        raise Refused(CONTENT_BOUND, report.id)", "        pass", (GATE, "mut19")),
    # Two layers keep DuckDB's message out of the log — the contract's, and
    # verify's own catch-all —, so the mutant removes both.
    ("parquet_unreadable, no value in the log",
     [("contract.py", "            raise Refused(PARQUET_UNREADABLE, report.id) from None", "            raise"),
      ("release.py", "    except Exception:  # never a value in the log (package_gate §7)\n        raise Refused(f\"{c.PARQUET_UNREADABLE}: a report could not be checked\") from None",
       "    except Exception as error:\n        raise Refused(f\"{c.PARQUET_UNREADABLE}: {error}\") from None")],
     None, None, (GATE, "prints_no_value")),
    ("clear_value and clear_totals", "contract.py", "            if needle in data:", "            if False:", (GATE, "mut05 or mut06 or mut07")),
    ("clear_totals first", "contract.py", "    found: list[tuple[str, bytes]] = [(CLEAR_TOTALS, v.totals_raw) for v in values]",
     "    found: list[tuple[str, bytes]] = []", (GATE, "mut07 and not mut07b and not mut07c and not mut07d")),
    ("the row count searched", "contract.py", "    values.numbers.add(str(rows))", "    pass", (GATE, "mut07b")),
    ("the Brazilian spellings", "contract.py", "    out = [canonical, sign + grouped + tail, sign + canonical.lstrip(\"-\").replace(\".\", \",\")]",
     "    out = [canonical]", (GATE, "mut06")),
    ("the manifest's labels only (N83)", "release.py", "            haystacks[rel] = c.manifest_labels(manifest) if rel == manifest_rel else data",
     "            haystacks[rel] = data", (GATE, "typed_fields_are_not_searched")),
    ("live_unchanged_identical", "envelope.py", "        require(same, PACKAGE_ID_REUSED, \"live_unchanged_identical\")", "        pass",
     (GATE, "mut20")),
    ("live_dek_fresh", "envelope.py", "    require(not (deks & live_deks), DEK_REUSED, \"live_dek_fresh\")", "    pass", (GATE, "mut21 and deks")),
    ("live_iv_fresh", "envelope.py", "    require(not (ivs & live_ivs), IV_REUSED, \"live_iv_fresh\")", "    pass", (GATE, "mut21 and ivs")),
    ("live_salt_fresh", "envelope.py", "    require(not (salts & live_salts), SALT_REUSED, \"live_salt_fresh\")", "    pass", (GATE, "mut21 and salts")),
    ("live_opens", "envelope.py", "        require(dek is not None, LIVE_UNREADABLE, \"live_opens\")", "        pass", (ENVELOPE, "unopenable")),
    ("bind-live: the paths", "release.py", "    if held != expected:\n        raise changed", "    if False:\n        raise changed", (GATE, "mut23 or other_paths")),
    ("bind-live: the margin", "release.py", "    if released > _when(checked_at) - LIVE_SETTLED:\n        raise changed",
     "    if False:\n        raise changed", (GATE, "mut25")),
    ("promote: the predecessor", "release.py", "    if (before or \"none\") != live_version:", "    if False:", (GATE, "mut22_mut24")),
    ("the record's live_version", "release.py",
     "        if not isinstance(live_version, str) or not live_version or any(ch in live_version for ch in \":/@ \"):",
     "        if False:", (GATE, "without_live_version")),
]


def run(src: pathlib.Path, tests: tuple[str, str]) -> int:
    env = dict(os.environ, PYTHONPATH=str(src), PYTHONDONTWRITEBYTECODE="1")
    path, expr = tests
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", path, "-k", expr],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode


def main() -> int:
    survivors = 0
    with tempfile.TemporaryDirectory(prefix="m52-") as tmp:
        src = pathlib.Path(tmp) / "src"
        shutil.copytree(ROOT / "src" / "bi_como_codigo", src / "bi_como_codigo")
        control = all(run(src, tests) == 0 for *_, tests in MUTANTS)
        print(f"control (unmodified copy, every mutant's tests): {'passed' if control else 'FAILED'}")
        for check, name, old, new, tests in MUTANTS:
            edits = name if isinstance(name, list) else [(name, old, new)]
            originals = {src / "bi_como_codigo" / f: (src / "bi_como_codigo" / f).read_text(encoding="utf-8") for f, _, _ in edits}
            applied = True
            for file, text, replacement in edits:
                module = src / "bi_como_codigo" / file
                current = module.read_text(encoding="utf-8")
                if current.count(text) != 1:
                    applied = False
                    break
                module.write_text(current.replace(text, replacement), encoding="utf-8")
            code = run(src, tests) if applied else None
            for module, original in originals.items():
                module.write_text(original, encoding="utf-8")
            if code is None:
                print(f"{check}: a text to mutate is not found exactly once — not run")
                survivors += 1
                continue
            killed = code != 0
            survivors += not killed
            print(f"{check}: {'killed' if killed else 'SURVIVED'} ({tests[0]} -k {tests[1]!r})")
    print(f"{len(MUTANTS)} mutants, {len(MUTANTS) - survivors} killed, {survivors} not")
    return 0 if control and not survivors else 1


if __name__ == "__main__":
    sys.exit(main())
