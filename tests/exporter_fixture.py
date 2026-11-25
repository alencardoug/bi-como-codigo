"""Writes the exporter's test fixture (docs/exporter.md §12): invented values
with the 16 views' real columns, and the facts a fake warehouse answers with.

The structure is `release/views.json`, the view contract the Owner reviewed,
drafted by `export propose` from the catalogue read in the first read window
(`evidence/20261124/catalogue.json`). A test, with `ENG_DADOS_2_DIR`, proves
that propose over that catalogue still drafts it byte for byte.

The fixture, `tests/exporter/fixture.json`, holds invented rows for every
view of that structure — no figure of eng_dados —, a catalogue and a
provenance row for the fake, an invented metadata package with the real
names, and the view contract with the fixture's own build, whose witness is
computed from the fixture's rows by the fake's fingerprint:

    uv run --frozen python tests/exporter_fixture.py

Everything is drawn from a seeded generator, so the bytes are the same on
every run.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import random
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.append(str(ROOT / "src"))

from bi_como_codigo.exporter import propose as P, views as V  # noqa: E402

HERE = ROOT / "tests" / "exporter"
STRUCTURE = ROOT / "release" / "views.json"
CATALOGUE = ROOT / "evidence" / "20261124" / "catalogue.json"
FIXTURE = HERE / "fixture.json"
CAPTURE = ROOT / "evidence" / "20261119" / "capture.out.txt"
PROFILE = ROOT / "evidence" / "20261124" / "m59_profile.out.txt"
PIN = "b0ef66e3ab42ce83c447c875c832f10f04db0d19"  # N91
SEED = 20261124

#: The fixture's build: invented, so it never matches a real warehouse.
FIXTURE_PROVENANCE = {
    "built_from_commit": "f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1",
    "invocation_id": "00000000-0000-4000-8000-000000000001",
    "sequence": 1,
}
POLICY = {"TimeZone": "UTC", "DateStyle": "ISO, MDY", "IntervalStyle": "postgres", "extra_float_digits": "1"}
COLLATION = {"datlocprovider": "c", "datcollate": "C.UTF-8", "datctype": "C.UTF-8", "daticulocale": None,
             "daticurules": None, "datcollversion": None}


def proposed(eng_dados_2: pathlib.Path) -> bytes:
    """What `export propose` drafts over the committed catalogue: release/views.json."""
    git = ["git", "-C", str(eng_dados_2)]
    path = f"{PIN}:docs/pacote_de_metadados.json"
    raw = subprocess.run([*git, "cat-file", "blob", path], capture_output=True, check=True).stdout
    blob = subprocess.run([*git, "rev-parse", path], capture_output=True, check=True, text=True).stdout.strip()
    draft = P.propose(
        P.parse_capture(CAPTURE.read_text(encoding="utf-8")),
        P.parse_profile(PROFILE.read_text(encoding="utf-8")),
        json.loads(raw),
        P.parse_catalogue(CATALOGUE.read_bytes()),
        PIN,
        blob,
    )
    return P.dump(draft)


# --- the fixture -------------------------------------------------------------------------------

LETTERS = "bcdfghjkmnpqrstvwxz"


def _text(rng: random.Random, limit: int, unique: int | None) -> str:
    """Invented text, never a word of the site: consonants and a digit."""
    size = min(limit, rng.randint(3, 9))
    body = "".join(rng.choice(LETTERS) for _ in range(size))
    if unique is not None:
        tag = f"{unique}"
        body = (body[: max(0, size - len(tag))] + tag)[:limit]
    return body


def _decimal(rng: random.Random, precision: int, scale: int) -> str:
    whole_digits = max(0, precision - scale - 3)  # the measured width, under N106's headroom
    whole = rng.randint(0, 10**whole_digits - 1) if whole_digits else 0
    fraction = rng.randint(0, 10**scale - 1) if scale else 0
    text = str(whole) + (f".{fraction:0{scale}d}" if scale else "")
    return text


def _instant(rng: random.Random) -> str:
    offset = dt.timezone(dt.timedelta(hours=rng.choice([-3, 0, 2])))
    base = dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc) + dt.timedelta(seconds=rng.randint(0, 3 * 10**7), microseconds=rng.randint(0, 999_999))
    return base.astimezone(offset).isoformat()


def rows_for(view: V.View, rng: random.Random) -> list[list]:
    count = rng.randint(3, 6)
    out = []
    for i in range(count):
        row = []
        for col in view.columns:
            grain = col.name in view.grain
            if col.nullable and i == 1:
                row.append(None)  # one null in every nullable column
            elif col.is_text:
                row.append(_text(rng, col.max_length, i if grain else None))
            elif col.is_integer:
                row.append(i + 1 if grain else rng.randint(0, 5000))
            elif col.is_decimal:
                row.append(_decimal(rng, col.precision, col.scale))
            elif col.source_type == "boolean":
                row.append(i % 2 == 0)
            elif col.is_instant:
                row.append(_instant(rng))
        out.append(row)
    return out


def invented_metadata(views: V.ViewContract) -> dict:
    """The metadata package's paths §5 reads, with the real names and nothing
    else of it: questions, view_rules with each column's role, relations."""
    return {
        "format": 1,
        "provenance": {"fixture": True},
        "questions": {v.report: {"view": f"consumption.{v.view}"} for v in views.views},
        "view_rules": {f"consumption.{v.view}": {"columns": {
            col.name: {"role": "grain" if col.name in v.grain else "measure"} for col in v.columns}} for v in views.views},
        "relations": {f"consumption.{v.view}": {"columns": {col.name: {} for col in v.columns}} for v in views.views},
    }


def fixture(structure_bytes: bytes) -> bytes:
    from fake_warehouse import fingerprint, typed_rows  # tests/fake_warehouse.py

    base = V.load(structure_bytes)
    rng = random.Random(SEED)
    rows = {v.view: rows_for(v, rng) for v in base.views}
    metadata = (json.dumps(invented_metadata(base), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    blob = hashlib.sha1(b"blob %d\0" % len(metadata) + metadata).hexdigest()
    draft = json.loads(structure_bytes)
    draft["metadata_blob"] = blob
    draft["accepted_builds"] = [{
        "provenance": FIXTURE_PROVENANCE,
        "policy": POLICY,
        "collation": COLLATION,
        "witness": [
            {"view": v.view, "rows": len(rows[v.view]), "md5": fingerprint(v, typed_rows(v, rows[v.view]))}
            for v in sorted(base.views, key=lambda x: x.view)
        ],
    }]
    contract = V.load(P.dump(draft))
    oids = {v.view: 70_000 + i for i, v in enumerate(sorted(contract.views, key=lambda x: x.view))}
    out = {
        "about": "Invented values with the 16 views' real columns (docs/exporter.md §12); generated by tests/exporter_fixture.py.",
        "views_json": json.loads(P.dump(draft)),
        "metadata": metadata.decode("utf-8"),
        "provenance": {**FIXTURE_PROVENANCE, "status": "verified"},
        "inventory": [{"oid": oids[name], "relname": name, "relkind": "v"} for name in sorted(oids)],
        "rows": rows,
    }
    return (json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8")


def main(argv: list[str]) -> int:
    sys.path.insert(0, str(ROOT / "tests"))
    if argv[1:]:
        print(__doc__)
        return 2
    FIXTURE.write_bytes(fixture(STRUCTURE.read_bytes()))
    print(f"wrote {FIXTURE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
