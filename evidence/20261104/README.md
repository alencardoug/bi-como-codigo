# Evidence — 04/11/2026

Claude Code's answer to the regeneration runbook's H4 for the part of stage 1.5 delivered so far,
against eng_dados at `c272104`, clean but for two files of another tool at its root. Each `*.out.txt`
is the literal output of the file with the same stem, with its UTC timestamp in the first line. The
runbook puts H4's answer in the diary of stage 1.6, which opens at P10; this is what P10 quotes.

| File | Reproduces | Item |
|---|---|---|
| `q22_h4_stage_1_5_checks.sql` | Every check stage 1.5 has added so far that runs on the warehouse, on today's data: each dbt test's own SQL with its `ref()` resolved from eng_dados' manifest, P09's new view inlined in place of the deployed one | Runbook H4 |

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

Re-running needs what [`evidence/20261022/README.md`](../20261022/README.md) describes: the
eng_dados databases up and read-only sessions through `evidence/20261022/ro.sh`. `q22` runs no dbt
command: `dbt test` would run eng_dados' `on-run-end` hook, which applies grants.
