# Evidence — 24/11/2026

Screenshots of the two P01 pages of stage 2.3, taken by Claude Code on the day the Owner chose
Candidate B (ADR-0004), and the oracle of what their charts should show. Both pages are the
artifacts of the last full run of the comparison, draw `draw-20261123T191327Z-4fb760ca` at
`a4f333f` ([`docs/framework_prototype.md` §10](../../docs/framework_prototype.md#10-results)). The
fixture is invented, with P01's columns, seed 853985153: no warehouse data. `chart_oracle.out.txt`
is the literal output of `chart_oracle.py`, with its UTC timestamp in the first line.

| File | Measures | Used by |
|---|---|---|
| `serve.py` | Serves both artifacts of a draw with the prototype's own server (`prototypes/framework/serve.py`), B and Evidence on two ports of `127.0.0.1` | The screenshots |
| `shots.mjs` | Headless Chrome through the DevTools protocol: the login box, then, after the public password (N22), the chart under each filter, named by the filter's label; it records what the page shows and judges nothing | `shots/` |
| `shots/` | `b_*` and `evidence_*`: `01_login` and `03` to `06`, the chart under `todos` and each of the three channels; `*_shots.json`, the filters each page offered | §10, ADR-0004 |
| `chart_oracle.py` | From the drawn fixture's cells: per filter, the cells with no row (G), the cells summed to zero (Z) and the months with a row; for `todos`, the first months of `fixture_raiz_1`, its largest month, and the order months take when sorted by value, descending | §10, ADR-0004 |

The whole page after login, tables included, was captured too (`*_02_page.png`, 2.2 MB and 1.6 MB).
It stays on this machine, under the ignored `prototypes/framework/runs/screenshots-20261124/`.

```sh
uv run --group prototype python evidence/20261124/serve.py <draw folder> 8101 8102
node evidence/20261124/shots.mjs http://127.0.0.1:8101/ <out> b <password>
SETTLE_MS=6000 CHART='div:has(> div[_echarts_instance_])' node evidence/20261124/shots.mjs http://127.0.0.1:8102/ <out> evidence <password>
python3 -I evidence/20261124/chart_oracle.py <cells.json of the draw>
```

**What the screenshots show, against the oracle:**

| | B | Evidence |
|---|---|---|
| Month axis | In order of time, 2150-05 to 2155-05, labelled every fourth month; `fixture_raiz_1` starts at 482M and peaks at 2153-01, 721M, as the oracle has it | In descending order of value: the first point is 2153-01's 721M, the order the oracle gives for a sort by value; every label reads "2" |
| Colours and legend | One colour per category under every filter, legend in alphabetical order | The legend follows the sort, so the same category takes another colour under another filter |
| Z, a zero (`fixture_canal_b`, 2150-11, `fixture_raiz_2`) | Drawn at 0 | Drawn at 0 |
| G, no row (`fixture_canal_c`, 2150-09, `fixture_raiz_3`) | The line is drawn straight across it: the query has no row there and the specification imputes nothing | The line breaks |
| The last month with no row in a channel (`fixture_canal_c`, 2155-05) | The axis ends at 2155-04: the partial month is not shown | Not distinguishable: the axis has no readable labels |
| Number format | pt-BR, `800.000.000` | English short form, `800M` |

The browser check of stage 2.3 compared the tables, which passed in both. It did not compare the
charts. These defects are for stage 2.5, whose criterion is that filter, chart and table agree with
the package.
