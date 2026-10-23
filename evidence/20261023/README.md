# Evidence — 23/10/2026

Claude Code's reproductions of the round-2 review by Codex (REVIEW.md, "Round 2"), taken before
applying its findings to the plan, against eng_dados at commit `26b58b3`. Each `*.out.txt` is the
literal output of the file with the same stem, with its UTC timestamp in the first line.

| File | Reproduces | Finding |
|---|---|---|
| `r1_envelope_counterexample.sh` | E2 — the public Diretoria password opens every report, and its holder can produce valid ciphertext | RV2-01, RV2-02 |
| `r2_lineage_leaves.py` | E3, plus a type cast — copy, sum, rounding, multiplication and cast have the same lineage leaf | RV2-08 |
| `r3_p13_averages.sql` | E6 — P13's rounded averages, re-weighted by their counts, differ from the direct calculation | RV2-12 |
| `r4_label_swap.sql` | New — swapping two channel labels keeps the row count and every total, and only a row-level comparison with the view catches it | RV2-03 |

Re-running needs what `evidence/20261022/README.md` describes: the eng_dados databases up, read-only
sessions through `evidence/20261022/ro.sh`, and the eng_dados `.venv` for the Python probe.
