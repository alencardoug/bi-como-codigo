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
from bi_como_codigo import contract as c

GATE = "contract.inspect"
CARRIER = "carrier inspection"


def _items(root: pathlib.Path) -> list[io_.Item]:
    return [io_.Item(p.relative_to(root).as_posix(), p.read_bytes()) for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()]


def collision_search(builders: dict[str, pathlib.Path], *, dependencies: dict[str, frozenset[str]] | None = None,
                     public: set[str] | None = None):
    """`collides(fx)` for `fixture.draw`, over the named builder outputs."""
    loaded = {name: _items(root) for name, root in builders.items()}
    public = public or set()
    contract = fx_mod.contract()

    def collides(fx: fx_mod.Fixture) -> list[fx_mod.Rejection]:
        totals, parquet = fx_mod.payload(fx)
        values = c.check_payload(contract, contract.reports[fx_mod.REPORT], totals, parquet)
        needles = c.needles([values], public)
        spelled = {s.encode(): n for n in values.numbers if c.eligible_number(n) for s in c.spellings(n)}
        spelled |= {t.encode(): t for t in values.texts}
        known = fx_mod.provenance(fx)
        carrier_needles = io_.Needles.from_fixture(fx)
        out: list[fx_mod.Rejection] = []

        def reject(value: str | None, inspection: str, file: str) -> None:
            if value is None:
                out.append(fx_mod.Rejection("value", inspection, file, tuple(fx.cells)))  # the totals object
                return
            cls, keys = known.get(value, ("label", ()))
            out.append(fx_mod.Rejection(cls, inspection, file, keys))

        for name, items in loaded.items():
            for code, needle, rel in io_.gate_hits({i.name: i.data for i in items}, needles):
                reject(None if code == c.CLEAR_TOTALS else spelled.get(needle), GATE, f"{name}:{rel}")
            report = io_.inspect_items(items, carrier_needles, dependencies=(dependencies or {}).get(name, frozenset()))
            for finding in report.findings:
                value = finding.value
                if finding.code == io_.INSPECT_CALENDAR:
                    value = str(value)  # a year of the window: the calendar moves
                reject(value, CARRIER, f"{name}:{finding.file}")
        return out

    return collides


def draw_against(seed: int, builders: dict[str, pathlib.Path], *, limit: int = fx_mod.DRAWS_MAX,
                 **kwargs) -> tuple[fx_mod.Fixture, dict]:
    """The measured fixture: drawn once, after both builder outputs are final."""
    return fx_mod.draw(seed, collision_search(builders, **kwargs), limit=limit)
