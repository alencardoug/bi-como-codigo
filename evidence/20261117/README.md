# Evidence — 17/11/2026

Claude Code's measurements after eng_dados closed its consumer-base phase with the tag `v2.1.0`
(`eb11709` of `mvp_eng_dados_2`): M55 to M58 of the plan. Each `*.out.txt` is the literal output of
the file with the same stem, with its UTC timestamp in the first line.

| File | Measures | Used by |
|---|---|---|
| `capture.sh`, with `capture_split.py` | The 16 views of `consumption` in one `REPEATABLE READ READ ONLY` transaction, through the exporter's own login (`consumption_reader`): the warehouse provenance, each view's columns and types, its row count and a fingerprint — the md5 of its rows as text, in text order. The rows themselves go to `CAPTURE_DIR`, outside Git | M55 |
| `compare.py` | The capture of M55 against every "before" that survives from the old pin `4da9e60` — the rows of four views that `mvp_eng_dados_2` measured on 2026-11-14, outside its Git, and the counts its Consumidores §5 publishes —, by the grain the package declares; each captured header against the package's relations at `eb11709`; and each view's repeated keys by its columns of role `grain`, alone and with those of role `identity` | M56; [UQ-18](../../docs/upstream_questions.md#the-questions) |
| `q_p08_november.sql` | What P08's cost of November 2026 is made of: the sale outflows of `analytics.fact_inventory_movement` by month, those of 2026-11 by origin, type and day, the last realised order day, and the orders behind them. Read-only session, superuser, through `evidence/20261022/ro.sh` | M58; [UQ-16](../../docs/upstream_questions.md#the-questions) |
| `views_sql_diff.sh` | What changed in the declaration of the views between `4da9e60` and `eb11709`, from Git alone: under `consumption`, only its YAML — no view's SQL | M56 |
| `package_check.py` | The metadata package at `eb11709` against `19c0e80`, the pin of the notice of 2026-11-15: format, keys added, `on_zero_denominator`, `open_items`, the warehouse provenance, the gateway code's meanings, the view audits and the run of their reference tests | M57 |

**What is not here.** No row of any view: the capture's rows are clear report data, and stay on this
machine (`/data/` is ignored; PLAN §6.2, stage 2.4). The fingerprints let the next capture say which
views changed without them.

**The "before" this repository does not have.** It never captured the views at `4da9e60`: the notices
that set that pin (`mvp_eng_dados_2`, 2026-11-14 and 2026-11-15) reached this repository only with the
one of 2026-11-17, and the shared warehouse no longer holds that state. So the before → after of
twelve views is not measured, here or there (its Q63). `mvp_eng_dados_2` offers to rebuild that state
from its pre-cycle recovery cut in an ephemeral database, if asked (its Consumidores §5) — a question
for the Owner (PLAN §7).

Re-running needs the databases up — asked of the Owner (`CLAUDE.md` §5) — and reads only:

```sh
ENG_DADOS_DIR=<checkout of mvp_eng_dados_2> CAPTURE_DIR=data/captures/<date>_<pin> sh evidence/20261117/capture.sh
```

`compare.py` reads files only — the "before" files under that checkout's `data/medicoes/`, the capture,
and the package as `git show eb11709:docs/pacote_de_metadados.json` writes it; `package_check.py`, the
package at both commits; `views_sql_diff.sh`, that checkout's Git:

```sh
python3 -I evidence/20261117/compare.py <checkout of mvp_eng_dados_2> data/captures/20261117_v2.1.0 <package at eb11709>
python3 -I evidence/20261117/package_check.py <package at eb11709> <package at 19c0e80>
ENG_DADOS_DIR=<checkout of mvp_eng_dados_2> sh evidence/20261117/views_sql_diff.sh
```

On 2026-11-17 the capture ran twice, at 14:49Z and 14:52Z, with the same 16 fingerprints, and the
provenance read again afterwards was the same row (`sequence` 71): no build ran in between.
