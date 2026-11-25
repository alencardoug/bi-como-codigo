# Evidence — 25/11/2026

Two subjects on the same day: the live run of stage 2.4's exporter, and the measures behind the
short plan of stage 2.5. Each `*.out.txt` is the literal output of the file with the same stem, with
its UTC timestamp in the first line — for `vega_invalid.html`, the text of its `<pre>` in Chrome's
`--dump-dom`. The path of B's artifact is shortened to `<B artifact>`.

## Stage 2.4 — the live run

Step 5 of [`docs/exporter.md`](../../docs/exporter.md#15-the-order-of-the-work), in a read window the
Owner opened ([§16](../../docs/exporter.md#16-the-implementation)).

| File | What it is | Used by |
|---|---|---|
| `export_run.json` | The run's receipt, written by `export evidence` after its strict reading against `release/views.json` ([§9](../../docs/exporter.md#9-the-package)): the pin and the metadata's digests; the read's time, provenance, text-form policy, collation and TLS mode; the eight facts of §3; per view, its rows, fingerprint, whether both equal the witness, the reference's digest and the Parquet's SHA-256; each envelope's SHA-256; the private candidate's commit, files, `verify` results and exemptions; the phases' durations. No value of any row | [`docs/exporter.md`](../../docs/exporter.md) §16 |

```sh
uv run --frozen python -m bi_como_codigo.exporter collisions
uv run --frozen python -m bi_como_codigo.exporter run
uv run --frozen python -m bi_como_codigo.exporter evidence <BICE_EXPORT_DIR>/run.json evidence/20261125
```

The first two need the environment of [`docs/exporter.md` §3](../../docs/exporter.md#3-the-read) and a read
window; the clear data stays in `BICE_EXPORT_STAGING`, removed when the run ends.

## Stage 2.5 — M62 and M63

How the package gate's value inspection meets a report page's own code, M62, and how the pinned
Vega-Lite draws a null, M63.

| File | Measures | Used by |
|---|---|---|
| `collision_surface.py` | The gate's needles (`bi_como_codigo.contract`, unchanged) built from M59's capture of the 16 views, outside Git, and searched by substring, as `verify` searches, in Candidate B's artifact of the last full run of 2.3 (`draw-20261123T191327Z-4fb760ca`, at `a4f333f`), in `site/index.html` and `site/releases.md`, and in N104's demonstration. Per hit: its kind, length, occurrences, how many stand as a token, whether all sit inside integrity hashes, and the view columns holding it. It prints no value | [`docs/report_page.md`](../../docs/report_page.md) §2 |
| `vega_invalid.html` | The Vega 6.4.0 and Vega-Lite 6.5.0 the page pins — the bodies of `prototypes/framework/own/cdn.json`, by digest — drawing invented points under each of Vega-Lite's `invalid` modes: a series null in the middle (G) and one null in the last month. Per mode, each line's subpaths and the x axis's months | [`docs/report_page.md`](../../docs/report_page.md) §3.2, §8 |

No database was read: the values are M59's capture, under the ignored `data/captures/`.

```sh
uv run --frozen python evidence/20261125/collision_surface.py data/captures/20261119_v2.3.0 <B artifact>/*.mjs <B artifact>/*.json <B artifact>/*.css <B artifact>/index.html site/index.html site/releases.md evidence/20261124/chart_interaction/p01.report.json evidence/20261124/chart_interaction/page.mjs evidence/20261124/chart_interaction/page.css
cp prototypes/framework/runs/cdn_bodies/<vega's sha256> <folder>/vega.js
cp prototypes/framework/runs/cdn_bodies/<vega-lite's sha256> <folder>/vega-lite.js
cp evidence/20261125/vega_invalid.html <folder>/
google-chrome --headless=new --user-data-dir=<folder>/profile --allow-file-access-from-files --virtual-time-budget=5000 --dump-dom file://<folder>/vega_invalid.html
```
