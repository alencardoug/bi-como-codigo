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

## The chart's interactions, approved by the Owner (N104)

The same day, the Owner asked whether B could highlight a line as Evidence does, and then for a
vertical whose popup shows every series at the month. Both were built as a **demonstration** over
B's artifact of this draw, outside the prototype, which stays as it was measured. The Owner
approved them for the reports, and found B ahead of or equal to Evidence on every point once they
were added (N104). They are built for real at stage 2.5. `chart_interaction/` is their starting
point:

| File | What it is |
|---|---|
| `p01.report.json` | The declaration with the chart's layers: the line, with the legend's selection (`legenda`); the points of the month under the vertical; the vertical, one rule per month, nearest the pointer, over the whole plot; and `perto`, the series the page highlights |
| `page.mjs`, `page.css` | The page with the popup: every series at the month, from the rows the chart draws, by value; a series with no row reads "Sem vendas neste recorte."; the partial month carries its notice; the line within 8 px of the pointer is highlighted and in bold; a click near it acts as a click on its legend label; hovering a legend label highlights it; a double-click clears the selection |
| `demo.diff` | Those three files against the artifact's own |
| `apply_demo.py` | Copies an artifact of B, puts the three files in place and writes their new SHA-384 into `index.html` |
| `legend.mjs`, `vertical.mjs` | Headless Chrome through the DevTools protocol. They drive the legend and the vertical step by step, and record each line's opacity and the popup's text; they judge nothing |
| `shots/` | `legend.json` and `vertical.json`, the records, and screenshots of the steps |

```sh
python3 -I evidence/20261124/chart_interaction/apply_demo.py <B's artifact> <out>
uv run --group prototype python evidence/20261124/serve.py <out> 8103
node evidence/20261124/chart_interaction/legend.mjs http://127.0.0.1:8103/ <records> <password>
node evidence/20261124/chart_interaction/vertical.mjs http://127.0.0.1:8103/ <records> <password>
```

**What the records show** (`shots/*.json`): hovering a legend label or a line leaves only that series
at full opacity; a click isolates one, shift-click adds another and a double-click restores all
five. The popup at 2152-01 lists the five series. Its values equal the fixture's sums to the cent,
for the three months checked against `chart_oracle.py`'s fixture: 2152-01 and 2155-05 under
`todos`, and 2150-09 under `fixture_canal_c`. At 2155-05 it carries the partial month's notice. At
2150-09 under `fixture_canal_c` it reads "Sem vendas neste recorte." for `fixture_raiz_3`, the G
cell.

**What it does not do yet, for 2.5:**

- The line still crosses the G cell, and `fixture_canal_c` still loses 2155-05 from its axis (above),
  so the popup cannot show that month.
- The popup's values come from the chart's rows, cast to `DOUBLE` (§4 of the prototype). They
  matched to the cent here, but 2.5 must format them from the exact amounts, as the tables do.
- There is no hover on a touch screen, and no keyboard path to the popup.
- Light and dark themes are not covered yet.
