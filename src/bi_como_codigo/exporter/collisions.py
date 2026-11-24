"""§10, N108: `export collisions`, an Owner-local diagnostic. `verify` stops at
the first clear value and prints only its code and file; this lists **every**
honest value of the run found in the committed public bytes.

It is the gate's own matching, unchanged (XIMPL-1-01): the values are what
`contract.check_payload` collects from each report — instants rendered in UTC,
numbers classified by the contract's types, the row count and the sums, and
the whole totals object —, and the needles are `contract.needles` over them,
with their spellings and eligibility. The haystacks are pinned to **one
commit**: the inclusion list, the profile labels and every included public
file are read at the same `HEAD`, never from the working tree, and the
package's envelopes are not searched. A value is printed only when it is found
in those committed bytes, so nothing is shown that the site does not already
show. The output goes to the terminal, never to Git.
"""

from __future__ import annotations

import fnmatch
import json
import os
import pathlib
import subprocess

from .. import contract as c
from . import CANDIDATE_REFUSED, Refused

INCLUDE = "release/include.txt"
PROFILES = "release/profiles.json"
PUBLIC = "release/public_values.json"


class Snapshot:
    """The committed public bytes at one commit."""

    def __init__(self, root: pathlib.Path):
        self.root = root
        self.commit = self._git("rev-parse", "--verify", "HEAD^{commit}").decode("ascii").strip()

    def _git(self, *args: str) -> bytes:
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        done = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, env=env, check=False)
        if done.returncode != 0:
            raise Refused(CANDIDATE_REFUSED, check="git")
        return done.stdout

    def show(self, rel: str) -> bytes:
        return self._git("show", f"{self.commit}:{rel}")

    def globs(self) -> list[str]:
        out = []
        for raw in self.show(INCLUDE).decode("utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#"):
                out.append(line)
        return out

    def regular_files(self) -> list[str]:
        """The regular files of `site/` at the commit: a symbolic link's blob is
        its target's name, not public content, and `release.build` refuses it
        (XIMPL-2-09)."""
        out = []
        for line in self._git("ls-tree", "-r", self.commit, "site/").decode("utf-8").splitlines():
            meta, _, rel = line.partition("\t")
            if meta.split()[0] in ("100644", "100755"):
                out.append(rel)
        return out

    def haystacks(self) -> dict[str, bytes]:
        globs = self.globs()
        out = {rel: self.show(rel) for rel in self.regular_files()
               if any(fnmatch.fnmatchcase(rel, g) for g in globs) and not rel.startswith("site/package/")}
        labels = [p["label"] for p in json.loads(self.show(PROFILES))["profiles"]]
        out[f"{PROFILES} (labels)"] = "\n".join(labels).encode("utf-8")
        return out

    def public(self) -> set[str]:
        return c.load_public_values(self.show(PUBLIC))


def holders(contract: c.Contract, payloads: dict[str, tuple[bytes, bytes]], run_dir: pathlib.Path) -> dict[str, set[str]]:
    """Each value the gate searches, with where it is held: `<report> <column>`,
    `<report> (rows)` or `<report> (sum of <column>)`. Read as the gate reads:
    its own connection, in UTC, the same cast."""
    found: dict[str, set[str]] = {}
    con = c._connect()
    try:
        for report_id, (totals_raw, parquet) in sorted(payloads.items()):
            report = contract.reports[report_id]
            path = run_dir / f"{report_id}.collisions.parquet"
            path.write_bytes(parquet)
            totals = json.loads(totals_raw)
            found.setdefault(str(totals["rows"]), set()).add(f"{report_id} (rows)")
            for name, value in totals["sums"].items():
                found.setdefault(value, set()).add(f"{report_id} (sum of {name})")
            for col in report.columns:
                if col.type == "BOOLEAN":
                    continue
                q = '"' + col.name + '"'
                sql = f"SELECT DISTINCT CAST({q} AS VARCHAR) FROM read_parquet(?) WHERE {q} IS NOT NULL"
                for (value,) in con.execute(sql, [str(path)]).fetchall():
                    found.setdefault(value, set()).add(f"{report_id} {col.name}")
    finally:
        con.close()
    return found


def hits(root: pathlib.Path, contract: c.Contract, payloads, run_dir: pathlib.Path) -> list[str]:
    """Every needle of the gate found in the committed public bytes, as lines."""
    snapshot = Snapshot(root)
    stacks = snapshot.haystacks()
    approved = snapshot.public()
    values = [c.check_payload(contract, contract.reports[rid], totals, parquet) for rid, (totals, parquet) in sorted(payloads.items())]
    where = holders(contract, payloads, run_dir)
    canonical: dict[bytes, set[str]] = {}
    for v in values:  # every canonical value behind a needle, as `contract.needles` derives them (XIMPL-2-06)
        for text in v.texts:
            if len(text) >= 3:
                canonical.setdefault(text.encode("utf-8"), set()).add(text)
        for number in v.numbers:
            if c.eligible_number(number):
                for spelling in c.spellings(number):
                    canonical.setdefault(spelling.encode("utf-8"), set()).add(number)
    lines = []
    for code, needle in c.needles(values, set()):  # every needle, the approved ones included and marked
        for rel, data in sorted(stacks.items()):
            if needle not in data:
                continue
            if code == c.CLEAR_TOTALS:
                report = next(v.report for v in values if v.totals_raw == needle)
                lines.append(f"collision: the whole totals object of {report} in {rel}")
                continue
            for value in sorted(canonical[needle]):  # each needs its own approval
                mark = " (approved in release/public_values.json)" if value in approved else ""
                held = ", ".join(sorted(where.get(value, ())))
                lines.append(f"collision: {value!r} as {needle.decode('utf-8')!r} in {rel}; held by {held}{mark}")
    lines.append(f"{len(lines)} collision(s) at {snapshot.commit[:12]}")
    return lines


def report(root: pathlib.Path, environ, **kwargs) -> list[str]:
    """The run up to the checked payloads, then the hits; nothing is sealed."""
    from . import run

    return run.export(root, environ, diagnose=lambda contract, payloads, run_dir: hits(root, contract, payloads, run_dir), **kwargs)
