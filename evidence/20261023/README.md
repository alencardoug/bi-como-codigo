# Evidence — 23/10/2026

Claude Code's reproductions of the round-2 and round-3 reviews by Codex (REVIEW.md, "Round 2" and
"Round 3"), taken before applying their findings to the plan, against eng_dados at commit `26b58b3`;
and the probes behind the regeneration runbook of stage 1.4 (`k*`, M24–M26), against eng_dados at
`1e197ac`. Each `*.out.txt` is the literal output of the file with the same stem, with its UTC
timestamp in the first line.

| File | Reproduces | Finding |
|---|---|---|
| `r1_envelope_counterexample.sh` | E2 — the public Diretoria password opens every report, and its holder can produce valid ciphertext | RV2-01, RV2-02 |
| `r2_lineage_leaves.py` | E3, plus a type cast — copy, sum, rounding, multiplication and cast have the same lineage leaf | RV2-08 |
| `r3_p13_averages.sql` | E6 — P13's rounded averages, re-weighted by their counts, differ from the direct calculation | RV2-12 |
| `r4_label_swap.sql` | New — swapping two channel labels keeps the row count and every total, and only a row-level comparison with the view catches it | RV2-03 |
| `r5_aad_bytes.sh` | R3-E1 of round 3 — the same fields serialised in another order give other authenticated bytes, and decryption fails | RV3-01 |
| `k1_rollback_cut.sh` | M24 — the approved recovery package and its second copy verify, and what the warehouse gained after its cut | Runbook P6, P7, O5; N26 |
| `k2_category_and_price_dependencies.sh` | M25 — nothing outside the generator depends on the category names or on the single price range | PLAN §9 |
| `k3_make_variables.sh` | M26 — a variable given to `make medir` reaches the target the meter runs | Runbook S5 |

Re-running needs what `evidence/20261022/README.md` describes: the eng_dados databases up, read-only
sessions through `evidence/20261022/ro.sh`, and the eng_dados `.venv` for the Python probe. The
`k*` probes run with `ENG_DADOS_DIR` pointing at the eng_dados checkout: `k1` calls only its
read-only targets — `preflight ALVO=trabalho` and `recovery-verify`, which lists the dumps and, with
`CONTRA_O_BANCO=1`, counts and reads —; `k2` reads tracked files; `k3` runs in a temporary directory
and touches nothing of eng_dados.
