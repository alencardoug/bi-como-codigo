# Evidence — 13/11/2026

Claude Code's measurement after eng_dados' stage 13 closed: M53 of the plan. The `*.out.txt` is the
literal output of the file with the same stem, with its UTC timestamp in the first line.

| File | Measures | Used by |
|---|---|---|
| `m53_billing_off.sh` | Whether the showcase's Google Cloud project is linked to a billing account — eng_dados' [plan for stage 13](https://github.com/alencardoug/mvp_eng_dados_1/blob/f86b9fb/PLANO_etapa_13.md) records that the end of the account's free trial reaches every project on it —, and that live still answers | M53 |

Re-running it needs `gcloud` authenticated and reads nothing but the billing info and the live page:
`BI_GCP_PROJECT=bi-como-codigo BI_LIVE_URL=https://bi-como-codigo.web.app/ sh evidence/20261113/m53_billing_off.sh`.
