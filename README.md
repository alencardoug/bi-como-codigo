# bi-como-codigo

A showcase of **BI as code** over the synthetic retail warehouse built in
[mvp_eng_dados_1](https://github.com/alencardoug/mvp_eng_dados_1): reports for its sixteen business
questions, a reading portal for its data governance, the governance of the project itself, and
least-privilege access by profile — with no BI licence and no database server.

**Status: planning.** Nothing is implemented yet. The plan, with every decision the Owner has taken,
is under review by a second agent before any code is written.

| File | What it is |
|---|---|
| [`PLAN.md`](PLAN.md) | The development plan: what gets built, the architecture, the stages with the effort of each, and the decisions |
| [`REVIEW.md`](REVIEW.md) | The original proposal by Codex and the review by Claude Code that led to the plan |
| [`evidence/20261022/`](evidence/20261022/) | The read-only probes behind every measurement in the plan, with their literal outputs |

The data is synthetic end to end. The warehouse, its pipeline and its governance live in
mvp_eng_dados_1; this repository only reads what that project publishes.
