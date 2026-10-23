# Evidence — 22/10/2026

Read-only probes behind the measurements M1–M18 of the plan. They were taken on the
[eng_dados](https://github.com/alencardoug/mvp_eng_dados_1) warehouse at commit `26b58b3`, between
23/10/2026 00:12Z and 01:22Z, and moved here from `data/medicoes/caminho_dos_dados_20261022/` in the
eng_dados checkout, where they were first written.

Every `*.saida.txt` is the literal output of the probe with the same stem, recorded with its UTC
timestamp in the first line. Probes and outputs are kept in Portuguese, exactly as recorded: they
are evidence, and translating them would change the record.

## Re-running

The eng_dados databases must be up (`make up` in that checkout); nothing else is needed.

| Probe | How |
|---|---|
| `s1_*.sql` … `s9_*.sql` | `evidence/20261022/ro.sh evidence/20261022/s1_view.sql` — always a read-only session. The eng_dados checkout comes from `ENG_DADOS_DIR` (default `~/Projetos/mvp_eng_dados_1`) |
| `linhagem_p01.py`, `catalogo_cobertura.py`, `descricao_herdavel.py` | From the eng_dados root, with its `.venv` and a complete `dbt/target/manifest.json`; the lineage scripts also need its `.env` loaded |
| `exportar.py` | `uv run --no-project --with pyarrow --with "psycopg[binary]" python -I exportar.py <eng_dados root> <output dir>` |
| `duckdb_wasm.saida.txt` | `curl` against jsDelivr, as written in the file |

`commit.txt` holds the eng_dados commit the probes ran against.
