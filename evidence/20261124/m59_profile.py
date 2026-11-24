"""The profile of M59's capture that stage 2.4's view contract needs (docs/exporter.md §4), from
the rows outside Git and printing no value: per view, its rows and whether its grain is unique; per
column, its nulls, and for each `numeric` the most integer digits and fractional digits written,
with any NaN or infinity; for `integer` and `bigint`, the most digits; for text, the longest value
in characters, and whether any holds a NUL.

The grain is the metadata package's: the columns of role `grain`, with those of role `identity`
(`view_rules.<view>.columns`, UQ-18), read with `git show <pin>:docs/pacote_de_metadados.json`.

    python3 -I evidence/20261124/m59_profile.py <capture dir> evidence/20261119/capture.out.txt <metadata package>
"""
import csv
import datetime
import json
import pathlib
import sys

capture, header_file, package_file = (pathlib.Path(a) for a in sys.argv[1:4])
csv.field_size_limit(1 << 30)
text = header_file.read_text(encoding="utf-8")
cols_section = text.split("## columns\n")[1].split("\n## ")[0].strip().splitlines()[1:]
types: dict[str, list[tuple[str, str]]] = {}
for line in cols_section:
    view, _pos, name, typ, _p, _s = line.split(",")
    types.setdefault(view, []).append((name, typ))
rules = json.loads(package_file.read_text(encoding="utf-8"))["view_rules"]

print(datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
print(f"capture: {capture.name}; {len(types)} views, {sum(len(c) for c in types.values())} columns")
widest = {"numeric_integer_digits": 0, "numeric_fraction_digits": 0, "numeric_total": 0}
for view, columns in sorted(types.items()):
    names = [n for n, _ in columns]
    grain = [c for c, r in rules[f"consumption.{view}"]["columns"].items() if r["role"] in ("grain", "identity")]
    with (capture / f"{view}.csv").open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        head = next(reader)
        assert head == names, (view, "header differs from the capture's columns")
        rows = list(reader)
    idx = [names.index(g) for g in grain]
    keys = [tuple(r[i] for i in idx) for r in rows]
    null_in_grain = sum(1 for k in keys if "" in k)
    dupes = len(keys) - len(set(keys))
    print(f"\n{view}: {len(rows)} rows; grain {'+'.join(grain)}: {dupes} repeated keys, {null_in_grain} with an empty grain cell")
    for i, (name, typ) in enumerate(columns):
        values = [r[i] for r in rows]
        nulls = sum(1 for v in values if v == "")
        present = [v for v in values if v != ""]
        detail = ""
        if typ == "numeric":
            special = sum(1 for v in present if v.lower() in ("nan", "infinity", "-infinity"))
            finite = [v.lstrip("-") for v in present if v.lower() not in ("nan", "infinity", "-infinity")]
            whole = max((len(v.split(".")[0].lstrip("0")) for v in finite), default=0)
            frac = max((len(v.split(".")[1]) if "." in v else 0 for v in finite), default=0)
            total = max((len(v.split(".")[0].lstrip("0")) + (len(v.split(".")[1]) if "." in v else 0) for v in finite), default=0)
            negative = sum(1 for v in present if v.startswith("-"))
            widest["numeric_integer_digits"] = max(widest["numeric_integer_digits"], whole)
            widest["numeric_fraction_digits"] = max(widest["numeric_fraction_digits"], frac)
            widest["numeric_total"] = max(widest["numeric_total"], total)
            detail = f"integer digits ≤ {whole}, fraction digits ≤ {frac}, both ≤ {total}; {negative} negative; NaN or infinity {special}"
        elif typ in ("integer", "bigint"):
            detail = f"digits ≤ {max((len(v.lstrip('-')) for v in present), default=0)}; {sum(1 for v in present if v.startswith('-'))} negative"
        elif typ in ("text", "character varying"):
            detail = f"longest {max((len(v) for v in present), default=0)} characters; NUL {sum(1 for v in present if chr(0) in v)}"
        else:
            detail = typ
        print(f"  {name} ({typ}): {nulls} null; {detail}")
print(f"\nwidest numeric: {widest}")
