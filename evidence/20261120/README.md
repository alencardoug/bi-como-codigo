# Evidence — 20/11/2026

Claude Code's check of `mvp_eng_dados_2`'s answer to UQ-21 to UQ-23 — three commits on top of the
tag `v2.3.0` (`2bceb47`), the last `b0ef66e`, with no new tag: M61 of the plan. Each `*.out.txt` is
the literal output of the file with the same stem, with its UTC timestamp in the first line.

| File | Measures | Used by |
|---|---|---|
| `source_diff.sh` | What changed between `2bceb47` and `b0ef66e`, from Git alone: whether `b0ef66e` is on its `origin/main`, the files changed, and how many under `dbt/` | M61 |
| `package_diff.py` | The metadata package at `b0ef66e` against `2bceb47`, key by key: every difference outside `checks`, and for `checks` the ids added or removed, the results whose status changed and the dates of the runs | M61 |

No database was read: no file under `dbt/` changed, so the 16 views and their data are those M59
captured at `2bceb47`.

```sh
ENG_DADOS_DIR=<checkout of mvp_eng_dados_2> sh evidence/20261120/source_diff.sh
python3 -I evidence/20261120/package_diff.py <package at 2bceb47> <package at b0ef66e>
```
