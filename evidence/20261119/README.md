# Evidence — 19/11/2026

Claude Code's measurements after eng_dados closed two more phases since the pin `v2.1.0`: the base
reopening, tag `v2.2.0` (`f5a5173`), and the reorder point per pair, tag `v2.3.0` (`2bceb47` of
`mvp_eng_dados_2`): M59 and M60 of the plan. Each `*.out.txt` is the literal output of the file with
the same stem, with its UTC timestamp in the first line.

| File | Measures | Used by |
|---|---|---|
| `capture.out.txt` | The 16 views of `consumption` at `v2.3.0`, by [`../20261117/capture.sh`](../20261117/capture.sh) unchanged: one `REPEATABLE READ READ ONLY` transaction through the exporter's own login (`consumption_reader`), the warehouse provenance, each view's columns and types, its row count and fingerprint. The rows go to `CAPTURE_DIR`, outside Git | M59 |
| `compare.py` | That capture against M55's (`../20261117/capture.out.txt`, at `v2.1.0`): provenance, fingerprint per view, columns; and, from the rows outside Git, P12's reorder point against its available quantity, and P08's sums and P11's turnover against what `mvp_eng_dados_2`'s Consumidores §5 publishes for them on 2026-11-18 | M59 |
| `package_check.py` | The metadata package at `2bceb47` against `eb11709`: format, relations added, keys and foreign keys, the view audits and the run of their checks, the open items, the provenance | M60 |

**What is not here.** No row of any view: they stay on this machine (`/data/` is ignored; PLAN §6.2,
stage 2.4).

**The read window.** The Owner said on 2026-11-19 that `mvp_eng_dados_2` was not running, only
`gdados` building its layout. The capture ran twice, at 22:44:51Z and 22:46:26Z, with the same 16
fingerprints and the same provenance row (`sequence` 125): no build ran in between.

Re-running needs the databases up — asked of the Owner (`CLAUDE.md` §5) — and reads only:

```sh
ENG_DADOS_DIR=<checkout of mvp_eng_dados_2> CAPTURE_DIR=data/captures/20261119_v2.3.0 bash evidence/20261117/capture.sh
```

`compare.py` and `package_check.py` read files only — the two captures, the rows of P08, P11 and P12
outside Git, and the package as `git show <commit>:docs/pacote_de_metadados.json` writes it:

```sh
python3 -I evidence/20261119/compare.py evidence/20261117/capture.out.txt evidence/20261119/capture.out.txt data/captures/20261119_v2.3.0
python3 -I evidence/20261119/package_check.py <package at 2bceb47> <package at eb11709>
```
