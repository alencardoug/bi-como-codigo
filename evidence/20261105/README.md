# Evidence — 05/11/2026

Claude Code's measurement for stage 2.2a, the encryption envelope. It is M47 of the plan. Each
`*.out.txt` is the literal output of the file with the same stem, with its UTC timestamp in the
first line.

| File | Measures | Used by |
|---|---|---|
| `m47_pbkdf2_latency.mjs` | PBKDF2-HMAC-SHA-256 deriving an AES-KW key through Node's WebCrypto — the browser's API —, five runs each of 100,000, 600,000 and 1,000,000 iterations, with the Node version and the CPU | N67; [envelope §7](../../docs/encryption_envelope.md#7-where-it-is-implemented) |

Re-running needs Node 20 or later and nothing else: `node evidence/20261105/m47_pbkdf2_latency.mjs`.
It derives keys from a fixed throwaway string and a random salt, in memory, and writes nothing.
