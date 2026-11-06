# Evidence — 06/11/2026

Claude Code's measurements for stage 2.2a, the encryption envelope, once both readers existed. They
are M48 to M51 of the plan. Each `*.out.txt` is the literal output of the file with the same stem,
with its UTC timestamp in the first line.

| File | Measures | Used by |
|---|---|---|
| `m48_counter_proof.py`, with `m48_worker.py` and `m48_worker.mjs` | The counter-proof of [envelope §6.5](../../docs/encryption_envelope.md#65-the-counter-proof-of-each-predicate): for every `predicate_id` of `src/bi_como_codigo/envelope.py` and of `web/envelope.mjs`, a copy of the module with that one condition taken as true, and its dedicated cases run against the copy — each must no longer end in its original code and predicate | M48 |
| `m51_first_preview.out.txt` | Excerpts of GitHub's log of the first publishing run (PR #1): the jobs' conclusions, the channel and version the federated deploy produced, and the exact check's refusal on Hosting's reserved files. The access token is masked by GitHub; the reserved `init.json`, which holds the project's public web configuration, is not copied | M51 |
| `m50_hosting_clone_source.sh` | How the installed `firebase-tools` parses the source of `hosting:clone` — `<site>:<channel>`, or `<site>@<version>` —, read from its own code, since its `--help` shows only the first | M50; [the pipeline §4.4](../../docs/publishing_pipeline.md#44-the-promotion-workflow-push-to-main) |
| `m49_browser_latency.mjs` | PBKDF2-HMAC-SHA-256 deriving an AES-KW key in Chrome, headless, through the DevTools protocol, five runs each of 100,000, 600,000, 1,000,000 and 2,000,000 iterations | N67, M49; [envelope §7](../../docs/encryption_envelope.md#7-where-it-is-implemented) |

Re-running `m48` needs the locked environment and Node 20 or later:
`uv run --frozen python evidence/20261106/m48_counter_proof.py`. It writes the mutant copies under a
temporary directory, removed at the end, and exits 1 if any case survives. `m49` needs Chrome
(`CHROME`, or `google-chrome` on the PATH) and Node 20 or later:
`node evidence/20261106/m49_browser_latency.mjs`; it uses a throwaway Chrome profile under the
system's temporary directory and removes it.
`m50` reads files only: `sh evidence/20261106/m50_hosting_clone_source.sh`.

The `r_*.txt` files are not measurements: they are the literal outputs of creating stage 2.2's
resources on 2026-11-06, 05:23–05:26Z, under N70 — `r_01` the project's state and its APIs before,
`r_02` the APIs enabled, `r_03` the workload identity pool and provider with the provider read back,
`r_04` the two service accounts, their role and their bindings read back with no user-managed key,
`r_05` the GitHub environments, their branch policies, the repository variables, the empty list of
secrets and the default workflow permissions; `r_06`, written at 13:44Z at the Owner's answer of that
afternoon, the ruleset on `main` and the rules GitHub reports in force there. How each is removed is
[the pipeline's §8](../../docs/publishing_pipeline.md#8-removing-it).

The `t*.out.txt` files are the tests of [the pipeline's §7](../../docs/publishing_pipeline.md#7-the-tests-of-the-stage),
run on GitHub and Firebase from 06:39Z: excerpts of GitHub's logs of each run, with every step's
environment block left out (paths and the masked token), and what was read independently
afterwards with the Owner's credentials. `t1_first_release` is T1 — and with it T7, the federation
accepting `publish.yml` and `promote.yml` on `main` in their environments —, approved under N75;
`t9_no_stored_key` is T9; `t3_t6_t11_refusals` are T3, T6 and T11; `t4_t5_t10_promotions` are T4, T5 in PIPE-1-04's schedule and T10(b) with its recovery, approved under N75 as the Owner extended it to the morning.
