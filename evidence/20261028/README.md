# Evidence — 28/10/2026

Claude Code's reproductions of round 4 of the regeneration runbook's review by Codex (runbook §10,
RR-27 to RR-31), taken before applying its findings, against eng_dados at `1e197ac`, clean. They
are M36 of the plan. `q17` is M37, P8's host-process check, taken after round 9 of the review was
interrupted. Each `*.out.txt` is the literal output of the file with the same stem, with its
UTC timestamp in the first line.

| File | Reproduces | Finding |
|---|---|---|
| `q14_p13_reconciliation.sql` | The P13 check of runbook lines E1 and E11, superseding `q11` of [`evidence/20261023/`](../20261023/README.md): `q11` plus each raw identity once in the capture and one classification row per full classification identity | RR-30 |
| `q15_p13_multiplicity.sql` | `q14`'s section 4 on CTE scenarios: a classification repeated, as Codex's model did, and a raw row repeated. Every loss counter stays 0 in both, as in `q11`; each is flagged by its own multiplicity counter | RR-30 |
| `q16_container_state.sh` | The project's containers by `docker inspect`, and whether the warehouse saw a capture after M30 | Runbook O9 |
| `q17_p8_process_check.sh` | P8's check as written, a `ps \| grep` that matches its own `grep`, against a bracketed `pgrep -af` that finds nothing and exits 1 | Runbook P8, §4 |

Re-running needs what [`evidence/20261022/README.md`](../20261022/README.md) describes: the eng_dados
databases up and read-only sessions through `evidence/20261022/ro.sh`. `q14` and `q15` go through
`ro.sh`; `q16` reads `docker inspect` — it starts, stops and changes nothing —, then the warehouse
through `ro.sh`. `q17` reads the process table only; run it on its own, since a shell whose
arguments hold the pattern would match too.
