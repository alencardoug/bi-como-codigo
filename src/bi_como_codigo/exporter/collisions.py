"""§10, N108: `export collisions`, an Owner-local diagnostic. `verify` stops at
the first clear value and prints only its code and file; this lists **every**
honest value of the sealed result found in the committed public bytes, with
the gate's own matching (`contract.needles` and its spellings).

The haystacks are the **committed** bytes of the included public files
(`git show HEAD:<path>`) and the profile labels of the committed
`release/profiles.json`, which `verify` searches in the manifest (N83) — never
the candidate's copy, nor the envelopes. A value is printed only when it is
found there, so nothing is shown that the site does not already show. The
output goes to the terminal, never to Git.
"""

from __future__ import annotations

import fnmatch
import json
import os
import pathlib
import subprocess

from .. import contract as c
from .. import release
from . import CANDIDATE_REFUSED, Refused


def _git(root: pathlib.Path, *args: str) -> bytes:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, env=env, check=False)
    if done.returncode != 0:
        raise Refused(CANDIDATE_REFUSED, check="git")
    return done.stdout


def haystacks(root: pathlib.Path) -> dict[str, bytes]:
    """The committed public bytes: every included file of `site/` at HEAD but
    the package, and the committed profile labels."""
    globs = release.inclusion(root)
    names = _git(root, "ls-tree", "-r", "--name-only", "HEAD", "site/").decode("utf-8").splitlines()
    out = {}
    for rel in names:
        if any(fnmatch.fnmatchcase(rel, g) for g in globs) and not rel.startswith("site/package/"):
            out[rel] = _git(root, "show", f"HEAD:{rel}")
    profiles = json.loads(_git(root, "show", "HEAD:release/profiles.json"))
    out["release/profiles.json (labels)"] = "\n".join(p["label"] for p in profiles["profiles"]).encode("utf-8")
    return out


def holders(contract: c.Contract, payloads: dict[str, tuple[bytes, bytes]], run_dir: pathlib.Path) -> dict[str, set[tuple[str, str]]]:
    """Each value the gate would search, with the reports and columns that hold it."""
    import duckdb

    found: dict[str, set[tuple[str, str]]] = {}
    con = duckdb.connect(":memory:", config={"autoinstall_known_extensions": False, "autoload_known_extensions": False})
    try:
        for report_id, (totals_raw, parquet) in sorted(payloads.items()):
            report = contract.reports[report_id]
            path = run_dir / f"{report_id}.collisions.parquet"
            path.write_bytes(parquet)
            totals = json.loads(totals_raw)
            found.setdefault(str(totals["rows"]), set()).add((report_id, "(rows)"))
            for name, value in totals["sums"].items():
                found.setdefault(value, set()).add((report_id, f"(sum of {name})"))
            for col in report.columns:
                if col.type == "BOOLEAN":
                    continue
                q = '"' + col.name + '"'
                sql = f"SELECT DISTINCT CAST({q} AS VARCHAR) FROM read_parquet(?) WHERE {q} IS NOT NULL"
                for (value,) in con.execute(sql, [str(path)]).fetchall():
                    if (col.numeric and c.eligible_number(value)) or (not col.numeric and len(value) >= 3):
                        found.setdefault(value, set()).add((report_id, col.name))
    finally:
        con.close()
    return found


def hits(root: pathlib.Path, contract: c.Contract, payloads, run_dir: pathlib.Path) -> list[str]:
    """Every honest value found in the committed public bytes, as terminal lines."""
    _contract, public = c.load(root)
    stacks = haystacks(root)
    values = holders(contract, payloads, run_dir)
    lines = []
    for value in sorted(values):
        numeric = c.eligible_number(value) if _is_number(value) else False
        spellings = c.spellings(value) if numeric else [value]
        for spelling in spellings:
            for rel, data in sorted(stacks.items()):
                if spelling.encode("utf-8") in data:
                    where = ", ".join(f"{r} {col}" for r, col in sorted(values[value]))
                    approved = " (approved in release/public_values.json)" if value in public else ""
                    lines.append(f"collision: {value!r} as {spelling!r} in {rel}; held by {where}{approved}")
    lines.append(f"{len(lines)} collision(s)")
    return lines


def _is_number(text: str) -> bool:
    return bool(c._CANONICAL.fullmatch(text))


def report(root: pathlib.Path, environ, **kwargs) -> list[str]:
    """The run up to the checked payloads, then the hits; nothing is sealed."""
    from . import run

    return run.export(root, environ, diagnose=lambda contract, payloads, run_dir: hits(root, contract, payloads, run_dir), **kwargs)
