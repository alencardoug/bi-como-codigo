# ADR-0001 — Encrypt each report under the password of the profiles it belongs to

| Field | Information |
|---|---|
| Status | Accepted |
| Date | 2026-11-06 |
| Decider | The Owner |
| Resolves | The pending row "Per-profile encryption" of the [record](README.md#3-pending), and the plan's N23, with N64–N67 |
| Supersedes / superseded by | — |

## Context

The showcase gives two profiles different reports — Diretoria all sixteen, Logística only P13
([PLAN §3.2](../../PLAN.md#32-the-showcase), O7) — on a static site with no server. Hiding a report
in JavaScript is not access control: the file can still be fetched by URL, as an evaluator sees in
the network tab. Firebase Authentication was considered and left out: a signed-in visitor could
change the shared password or delete the account (PLAN §2), and Firestore rules would add a
component to protect data the site can serve as files. Both passwords are public by design (N22),
printed below the login box, so what the site can demonstrate is **access scoped to the key
supplied** — each password opens exactly its profile's reports —, not the authentication of a
person nor confidentiality from the public.

The plan's first proposal of the envelope (PLAN §3.6) listed fields and parameters but left the
bytes open; the review found that equal fields are not equal bytes (M23, RV3-01) and that
parameters must not come from library defaults (RV2-02). Stage 2.2a froze the format and built
it, reviewed by Codex in five rounds.

## Alternatives considered

| Alternative | For | Against |
|---|---|---|
| **The password becomes the key** — each report encrypted at export, its data key wrapped under a key derived from each entitled profile's password | No account, no server, no rule set; the browser can only open what the key supplied unwraps; proved by execution, like eng_dados' `test_acesso` | The passwords are public, so it protects nothing from the public; a changed password does not revoke what was downloaded; a format to specify, implement twice and keep |
| Firebase Authentication with Firestore or Storage rules | A standard product; access enforced by the server | A shared account's password can be changed or the account deleted by any visitor; one more component and its rules; still no confidentiality, since the credentials are public |
| Hide the reports in the interface | Nothing to build | Not access control: every file is still fetchable by URL |
| A JSON header canonicalised by RFC 8785 as the authenticated data (instead of the binary header, N66) | Readable in a diff | Two implementations must canonicalise identically — the risk of M23 |
| A lower PBKDF2 count — a 250 ms budget or 100,000 (instead of 600,000, N67) | A faster login | Below the OWASP reference, read as a weak parameter by an evaluator who does not read why |

## Decision

Each report is encrypted on the Owner's machine at export, in the envelope of format version 1 —
PBKDF2-HMAC-SHA-256 with 600,000 iterations and a salt per profile per package, AES-KW of a fresh
256-bit data key per file for every entitled profile, AES-256-GCM with a fresh IV and the binary
header, byte for byte, as authenticated data —, as specified in
[`docs/encryption_envelope.md`](../encryption_envelope.md), produced and read in Python and read in
the browser by a separate JavaScript reader on WebCrypto.

## Consequences

- **Positive:** access per profile with no account, server or rule set; the public repository and
  Hosting only ever hold ciphertext and a manifest with no clear figure; the same reader file runs
  in the tests and in the site; every refusal is a named predicate with a case that dies without it
  (M48); the browser's login costs about 380 ms on the desktop (M49).
- **Negative:** confidentiality from the public is not provided and must never be claimed — the
  credentials are on the login screen; a password changed in a later release does not revoke what
  was downloaded with the former one; the format is a third thing to keep in step with two readers,
  through the vectors, the 151 shared cases and the specification's predicate table; a phone's
  login latency is not measured; anyone who knows a password can produce ciphertext the site
  accepts, so authenticity comes from the trusted release path and the HTTPS origin, not from the
  envelope.
- **Continued operation on Google Cloud:** nothing in the envelope names a project, a site or an
  environment; sandbox, qa and prod would be separate packages, each with its own salts, published
  by the pipeline of stage 2.2 to their own sites. The passwords are public by design (N22) and
  live in the profile declaration, registered in [`docs/public_by_design.yml`](../public_by_design.yml).
- **Documents to update:** [PLAN §3.6](../../PLAN.md#36-the-encryption-envelope--a-proposal-to-review-before-stage-23),
  which points to this ADR; [`docs/encryption_envelope.md`](../encryption_envelope.md), which owns
  the format; the record's index and the README's count.
