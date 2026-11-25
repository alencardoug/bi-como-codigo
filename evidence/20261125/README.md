# Evidence — 25/11/2026

The live run of stage 2.4's exporter, step 5 of [`docs/exporter.md`](../../docs/exporter.md#15-the-order-of-the-work),
in a read window the Owner opened ([§16](../../docs/exporter.md#16-the-implementation)).

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
