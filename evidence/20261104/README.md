# Evidence — 04/11/2026

Claude Code's answers to the regeneration runbook's H4, for the part of stage 1.5 delivered so far,
and H5, against eng_dados at `c272104`, clean but for two files of another tool at its root. Each `*.out.txt`
is the literal output of the file with the same stem, with its UTC timestamp in the first line. The
runbook puts H4's answer in the diary of stage 1.6, which opens at P10; this is what P10 quotes.

| File | Reproduces | Item |
|---|---|---|
| `q22_h4_stage_1_5_checks.sql` | Every check stage 1.5 has added so far that runs on the warehouse, on today's data: each dbt test's own SQL with its `ref()` resolved from eng_dados' manifest, P09's new view inlined in place of the deployed one | Runbook H4 |
| `q23_h5_m3_order_count.sql` | D5's M3 probe: the order count of P01, P02, P05 and P06 recounted from the fact at each view's grain with `(source_system, order_id)`, compared with the view both ways | Runbook H5 |
| `p24_h5_realism.py` | D5's M7, M8 and M9 probes, retail and legacy: the declared tree and ranges read from eng_dados' `geracao.yml`, the legacy findings from its current manifest | Runbook H5 |

## H4, so far

**The checks.** Two, both singular dbt tests of severity `error`, so both run in `dbt build` — in
`make check` and in step 8 of `make recovery-restore` (`dbt-rebuild`, then `check`):

| Test | Commit | On today's data |
|---|---|---|
| `invariante_14_lancamento_antes_da_venda` | `0b8a33c` | **Fails: 3,130 rows, 240 products** — M9's count. By design: the guard against the return of D65 |
| `p09_capturado_reconcilia_com_a_fato` | `94e0d09` | Passes once the view is rebuilt with stage 1.5's code: 0 rows, R$ 36,719,765.95 on both sides. Against the view deployed today, built before `94e0d09`, it fails (0 against the fact's total) — but a restore rebuilds the view before it tests |

What stage 1.5 has added that does **not** run on the warehouse: T2 (`make source-oracle`, read-only
on the two sources, on demand), the addition to `test_carga` (an isolated load) and H3 with
`test_realism` (memory).

**Which code can still restore a v1.0.0 package.** Any commit before `0b8a33c`, the last one being
`c7be31c`: up to it stage 1.5 changed only the generator, which a restore does not run, and
read-only tools. From `0b8a33c` on, a v1.0.0 package's restore would stop at step 8: `dbt build`
exits non-zero on invariant 14, and the nodes downstream of `trusted.order_items`, `trusted.orders`
and `trusted.product_skus` are skipped. This is derived from the recipe and dbt's semantics, **not
exercised**: no restore was run. The way back (runbook §6) runs `PRE`'s code — `33d6451`, the last
commit before stage 1.5 (N26) — so it changes no step.

**Still to come.** H6 to H8 — the gates, the recovery phase and the epochs — read
`governance.legacy_captures`, `raw_legacy` and the ledger, and by H8 they fail with no current
epoch. They join this answer when they land, before stage 1.6.

## H5 — the probes of D5

D5 runs `q23` through `$RO` and `p24` from the eng_dados root with its `.venv`; each prints its
expected values, and `p24` exits 1 when one is not met.

| Probe | Expected at D5 | Today, v1.0.0 data |
|---|---|---|
| M3, `q23` | `differing_rows` 0 and as many groups in the view as recounted, in P01, P02, P05 and P06 | **Met** — fixed by stage 1.1. Not vacuous: a count without the source would miss 1 group in P05 and 1 in P06, M3's two |
| M7, `p24` | Every leaf of `dim_category` on the root and middle the tree declares, both sources | Fails: 11 of 12 retail leaves and 7 of 8 legacy ones elsewhere |
| M8, `p24` | 0 fact items outside the declared range of their leaf, both sources | Fails: 4,794 of 7,500 retail items, 106 of 231 legacy ones, none with a finding on its price |
| M9 retail, `p24` | 0 items sold before launch, read as invariant 14 reads them | Fails: 3,130 of 7,500 — M9's count |
| M9 legacy, `p24` | 0 unexplained: each item with a finding on its order's `placed_at` or its product's `launched_at` whose cleaned value is another instant than the original | Fails: 55 of 231, none explained |

The probes fail today on the defects stage 1.6 must close, and M3 passes as it has since stage 1.1:
neither side is vacuous. The legacy link to the manifest is not empty either — all 231 legacy items
and 23 products reach their physical row in staging, the only path a finding has to an item.

**What D5 should find in the legacy source, predicted in memory.** The fixed generator, run with
the legacy catalogue's seed and factor, gives 0 on M7 (10 leaves), M8 (375 items) and M9, with 14
items of unknown launch. Its injector puts the new batch's findings (`060c3fc9…`, 108, as today's)
where none moves a fact item's date or price: the `unit_price` and `placed_at` findings are
rejections, and the `launched_at` one, a missing time zone, cleans back to the same instant. So
legacy M8 and M9 are expected at 0, not only "none unexplained". A prediction, not a measurement:
D5 measures.

Re-running needs what [`evidence/20261022/README.md`](../20261022/README.md) describes: the
eng_dados databases up and read-only sessions through `evidence/20261022/ro.sh`. `q22` runs no dbt
command: `dbt test` would run eng_dados' `on-run-end` hook, which applies grants.
