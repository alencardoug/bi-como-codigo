"""The draw against both builder outputs (docs/framework_prototype.md §2.1,
steps 2 to 4).

For each candidate fixture the payload is computed as the gate computes it
(`contract.check_payload`), and both builder outputs are searched with both
inspections: the gate's own substring search, every hit (`gate_hits`), and
the carrier inspection's full dispatch (`inspect_items`). Each hit becomes a
rejection that names its class, its inspection and its file — never the
value — and what the draw moves.
"""

from __future__ import annotations

import pathlib

import fixture as fx_mod
import inspect_output as io_
import trees
from bi_como_codigo import contract as c, envelope as e, release

GATE = "contract.inspect"
CARRIER = "carrier inspection"


def _items(root: pathlib.Path) -> list[io_.Item]:
    """Every regular file of a builder output, read without following a link;
    a missing or linked root refuses the draw (PROTO-1-07)."""
    real = trees.real_root(root)
    return [io_.Item(rel, data) for rel, data in sorted(trees.files(real).items())]


def _opened(fx: fx_mod.Fixture) -> c.Values:
    """§2.1, step 2: the fixture sealed, opened with the reader, and checked as
    the gate checks it."""
    totals, parquet = fx_mod.payload(fx)
    manifest_raw, files = fx_mod.seal(totals, parquet)
    manifest = e.validate_manifest(manifest_raw)
    declared = {p.id: p.password for p in release.profiles(fx_mod.HERE)}
    key = e.login(manifest, "diretoria", declared["diretoria"])
    entry = manifest.reports[fx_mod.REPORT]
    opened_totals, opened_parquet = e.open_report(manifest, files[entry.file], fx_mod.REPORT, key)
    contract = fx_mod.contract()
    return c.check_payload(contract, contract.reports[fx_mod.REPORT], opened_totals, opened_parquet)


def collision_search(builders: dict[str, pathlib.Path], *, dependencies: dict[str, frozenset[str]] | None = None,
                     public: set[str] | None = None):
    """`collides(fx)` for `fixture.draw`, over the named builder outputs."""
    if not builders:
        raise ValueError("the draw needs the builder outputs it is drawn against")
    loaded = {name: _items(root) for name, root in builders.items()}
    if public is None:
        public = c.load_public_values((fx_mod.HERE / "release" / "public_values.json").read_bytes())

    def collides(fx: fx_mod.Fixture) -> list[fx_mod.Rejection]:
        values = _opened(fx)
        needles = c.needles([values], public)
        spelled = {s.encode(): n for n in values.numbers if c.eligible_number(n) for s in c.spellings(n)}
        spelled |= {t.encode(): t for t in values.texts}
        known = fx_mod.provenance(fx)
        carrier_needles = io_.Needles.from_fixture(fx, gate=False)
        out: list[fx_mod.Rejection] = []
        stopped: list[dict] = []

        def reject(value: str | None, inspection: str, file: str) -> None:
            if value is None:
                out.append(fx_mod.Rejection("value", inspection, file, tuple(sorted(fx.cells))))  # the totals object
                return
            for cls, keys in known.get(value, [("label", ())]):
                out.append(fx_mod.Rejection(cls, inspection, file, keys))

        for name, items in loaded.items():
            for code, needle, rel in io_.gate_hits({i.name: i.data for i in items}, needles):
                reject(None if code == c.CLEAR_TOTALS else spelled.get(needle), GATE, f"{name}:{rel}")
            report = io_.inspect_items(items, carrier_needles, dependencies=(dependencies or {}).get(name, frozenset()))
            stopped += [{"file": f"{name}:{x.file}", "path": x.path, "reason": x.reason} for x in report.inconclusive]
            for finding in report.findings:
                reject(str(finding.value), CARRIER, f"{name}:{finding.file}")
        if stopped:  # an output the inspection cannot read calibrates nothing
            raise fx_mod.DrawStopped(sorted(stopped, key=lambda x: (x["file"], x["path"])))
        return out

    return collides


def draw_against(seed: int, builders: dict[str, pathlib.Path], *, limit: int = fx_mod.DRAWS_MAX,
                 **kwargs) -> tuple[fx_mod.Fixture, dict]:
    """The measured fixture: drawn once, after both builder outputs are final."""
    return fx_mod.draw(seed, collision_search(builders, **kwargs), limit=limit)
