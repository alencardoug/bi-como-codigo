# Evidence — 06/11/2026

Claude Code's measurements for stage 2.2a, the encryption envelope, once both readers existed. They
are M48 to M50 of the plan. Each `*.out.txt` is the literal output of the file with the same stem,
with its UTC timestamp in the first line.

| File | Measures | Used by |
|---|---|---|
| `m48_counter_proof.py`, with `m48_worker.py` and `m48_worker.mjs` | The counter-proof of [envelope §6.5](../../docs/encryption_envelope.md#65-the-counter-proof-of-each-predicate): for every `predicate_id` of `src/bi_como_codigo/envelope.py` and of `web/envelope.mjs`, a copy of the module with that one condition taken as true, and its dedicated cases run against the copy — each must no longer end in its original code and predicate | M48 |
| `m50_hosting_clone_source.sh` | How the installed `firebase-tools` parses the source of `hosting:clone` — `<site>:<channel>`, or `<site>@<version>` —, read from its own code, since its `--help` shows only the first | M50; [the pipeline §4.4](../../docs/publishing_pipeline.md#44-the-promotion-workflow-push-to-main) |
| `m49_browser_latency.mjs` | PBKDF2-HMAC-SHA-256 deriving an AES-KW key in Chrome, headless, through the DevTools protocol, five runs each of 100,000, 600,000, 1,000,000 and 2,000,000 iterations | N67, M49; [envelope §7](../../docs/encryption_envelope.md#7-where-it-is-implemented) |

Re-running `m48` needs the locked environment and Node 20 or later:
`uv run --frozen python evidence/20261106/m48_counter_proof.py`. It writes the mutant copies under a
temporary directory, removed at the end, and exits 1 if any case survives. `m49` needs Chrome
(`CHROME`, or `google-chrome` on the PATH) and Node 20 or later:
`node evidence/20261106/m49_browser_latency.mjs`; it uses a throwaway Chrome profile under the
system's temporary directory and removes it.
`m50` reads files only: `sh evidence/20261106/m50_hosting_clone_source.sh`.
