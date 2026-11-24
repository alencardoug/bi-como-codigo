"""What each chart of stage 2.3's P01 page should show, from the drawn fixture's cells
(prototypes/framework/measured.py writes them as cells.json beside the draw): per filter,
the cells with no row (G) and the cells summed to zero (Z), the months the filter has,
and, for the chart of all channels, the first months chronologically and the order the
months take if a category axis is sorted by the value, descending, in order of first
appearance — Evidence's default for a category x.

    python3 -I evidence/20261124/chart_oracle.py <cells.json>
"""
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "prototypes" / "framework"))
import fixture as f  # noqa: E402

fx = f.Fixture.load(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")))
s = f.summary(fx)
print(datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
print("fixture:", fx.digest()[:8], "seed", fx.seed, "months", fx.year_month(0), "to", fx.year_month(f.PARTIAL))
months = sorted({i for (_, i, _) in s})
roots = sorted({r for (_, _, r) in s})
for flt in f.FILTERS:
    have = sorted({i for (fl, i, _) in s if fl == flt})
    gaps = [f"{fx.year_month(i)} {r}" for i in months for r in roots if (flt, i, r) not in s]
    zeros = [f"{fx.year_month(i)} {r}" for (fl, i, r), (n, _) in sorted(s.items()) if fl == flt and n == 0]
    print(f"\n{flt}: months with a row {fx.year_month(have[0])} to {fx.year_month(have[-1])} ({len(have)} of {len(months)})")
    print("  G, no row:", gaps or "none")
    print("  Z, zero:", zeros or "none")
series = sorted((i, n) for (fl, i, r), (n, _) in s.items() if fl == "todos" and r == roots[0])
print(f"\ntodos, {roots[0]}, the first four months:", [(fx.year_month(i), f"{float(n) / 1e6:.0f}M") for i, n in series[:4]])
top = max(series, key=lambda x: x[1])
print(f"todos, {roots[0]}, its largest month:", fx.year_month(top[0]), f"{float(top[1]) / 1e6:.0f}M")
order = []
for _n, i, _r in sorted(((n, i, r) for (fl, i, r), (n, _) in s.items() if fl == "todos"), reverse=True):
    if i not in order:
        order.append(i)
print("todos, months sorted by value descending:", [fx.year_month(i) for i in order[:6]], "...", fx.year_month(order[-1]))
