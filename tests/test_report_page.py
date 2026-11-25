"""The report page's checks (docs/report_page.md §4, N119), P01 first.

- The declaration: its pins are the ones `site/app/cdn.json` writes; its queries
  sum only what the pinned metadata calls additive; its question is the
  metadata's.
- Checks 1 to 3, in headless Chrome over the committed site and its invented
  package: tables, chart and popup against the package; the legend, the
  keyboard and touch; tab order, focus, 360 px and both colour schemes. The
  browser side, `tests/browser/report_page.mjs`, only reads; every expectation
  here comes from the invented rows (`site_fixture.p01_rows`) with Python's
  `decimal`, never from the page's SQL.

They need Chrome and Node: in `make check` a missing one fails (N119); on a CI
runner without them the browser checks are skipped.

**On the real package** (N119, before each PR that brings it and against its
preview): `BICE_REPORT_PACKAGE` names a sealed package's folder — the
exporter's result —, which the page is served with and the oracle opens with
the profile's public password (N22), through the Python reader. Its Parquet is
read in a private temporary folder, removed at once. A failure's detail would
print values, so the command prints names only:

    BICE_REPORT_PACKAGE=<folder> uv run --frozen pytest -q --tb=no -rN -p no:cacheprovider tests/test_report_page.py The pinned third-party
bodies are cached by their sha256 in `BICE_CDN_CACHE` — by default
`$XDG_CACHE_HOME/bi-como-codigo/cdn` —, fetched once and checked.
"""

from __future__ import annotations

import functools
import hashlib
import http.server
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import urllib.request
from decimal import Decimal

import pytest

from bi_como_codigo import release as r
from bi_como_codigo.exporter import metadata as m

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
import report_pins  # noqa: E402
import site_fixture as sf  # noqa: E402

PAGE = ROOT / "site" / "relatorios" / "p01.report.json"
DECLARATION = json.loads(PAGE.read_text(encoding="utf-8"))
CDN = ROOT / "site" / "app" / "cdn.json"
DRIVER = ROOT / "tests" / "browser" / "report_page.mjs"
NBSP = " "


# --- the declaration --------------------------------------------------------------------------


def test_the_pins_are_written_from_cdn_json():
    """C1: no build, so the committed import map, scripts and pins.mjs are
    exactly what tests/report_pins.py writes from cdn.json."""
    assert report_pins.main(["--check"]) == 0


def _metadata() -> dict:
    checkout = os.environ.get("ENG_DADOS_2_DIR")
    if not checkout:
        pytest.skip("needs ENG_DADOS_2_DIR, a checkout of mvp_eng_dados_2, as make check sets it")
    pin = json.loads((ROOT / "release" / "views.json").read_text(encoding="utf-8"))["pin"]
    shown = subprocess.run(["git", "-C", checkout, "show", f"{pin}:{m.PATH}"], capture_output=True, check=True)
    return json.loads(shown.stdout)


def _view() -> str:
    views = json.loads((ROOT / "release" / "views.json").read_text(encoding="utf-8"))["views"]
    return next(v["view"] for v in views if v["report"] == DECLARATION["id"])


def test_only_additive_columns_are_summed():
    """No metric is redefined here (CLAUDE.md §6, rule 3): a query sums only a
    column the pinned metadata calls additive — never order_count, which counts
    an order in each of its categories."""
    columns = _metadata()["view_rules"][f"consumption.{_view()}"]["columns"]
    summed = {name for q in DECLARATION["queries"].values() for name in re.findall(r"\bsum\(\s*([a-z_]+)\s*\)", q["sql"])}
    assert summed, "the declaration sums nothing: the check would prove nothing"
    assert {name: columns[name]["additivity"] for name in summed} == {name: "additive" for name in summed}
    assert columns["order_count"]["additivity"] == "non_additive"


def test_the_question_is_the_metadata_s():
    assert DECLARATION["question"] == _metadata()["questions"][DECLARATION["id"]]["title"]


# --- what the package holds, computed here ----------------------------------------------------

REAL = os.environ.get("BICE_REPORT_PACKAGE")


def _real_rows(folder: pathlib.Path) -> list[tuple]:
    """P01 of a sealed package, opened as the browser opens it, as typed rows."""
    import tempfile

    import duckdb

    from bi_como_codigo import envelope as e

    manifest = e.validate_manifest((folder / "manifest.json").read_bytes())
    password = next(p.password for p in r.profiles(ROOT) if p.id == DECLARATION["profile"])
    key = e.login(manifest, DECLARATION["profile"], password)
    entry = manifest.reports[DECLARATION["id"]]
    _totals, parquet = e.open_report(manifest, (folder / entry.file).read_bytes(), DECLARATION["id"], key)
    with tempfile.TemporaryDirectory() as private:
        path = pathlib.Path(private) / "p01.parquet"
        path.write_bytes(parquet)
        return [tuple(row) for row in duckdb.connect(":memory:").execute("SELECT * FROM read_parquet(?)", [str(path)]).fetchall()]


NAMES = [col for col in ("year_month", "year_number", "month_number", "sales_channel_name", "channel_type", "root_category_name",
                         "category_name", "order_count", "unit_count", "gross_revenue_amount", "discount_amount", "net_revenue_amount")]
ROWS = [dict(zip(NAMES, row)) for row in (_real_rows(pathlib.Path(REAL)) if REAL else sf.ROWS["P01"])]
MONTHS = sorted({row["year_month"] for row in ROWS})
CHANNELS = sorted({row["sales_channel_name"] for row in ROWS})
ROOTS = sorted({row["root_category_name"] for row in ROWS})
LAST = MONTHS[-1]
EMPTY = DECLARATION["empty"]
PARTIAL = DECLARATION["partial"]["text"]
SUMMARY = next(t for t in DECLARATION["tables"] if t["bice"] == "summary")


def brl(amount: Decimal) -> str:
    whole, cents = f"{amount:,.2f}".split(".")
    sign = "-" if whole.startswith("-") else ""
    return f"{sign}R${NBSP}{whole.lstrip('-').replace(',', '.')},{cents}"


def integer(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def cell(filter_: str, month: str, root: str) -> tuple[Decimal | None, int | None]:
    """A summary cell: the net revenue and the units of its rows, or none — G."""
    rows = [x for x in ROWS if x["year_month"] == month and x["root_category_name"] == root
            and filter_ in ("todos", x["sales_channel_name"])]
    if not rows:
        return None, None
    return sum((x["net_revenue_amount"] for x in rows), Decimal(0)), sum(x["unit_count"] for x in rows)


@pytest.mark.skipif(bool(REAL), reason="the invented grid's cases, not the real package's")
def test_the_fixture_holds_every_case():
    """The invented grid has what the checks must see: a G under every
    filter, a G under one channel only, a Z, a channel with no row in the last
    month."""
    assert all(cell(f, "2150-06", "fixture_raiz_4")[0] is None for f in ["todos", *CHANNELS])
    assert cell("fixture_canal_c", "2150-03", "fixture_raiz_3")[0] is None and cell("todos", "2150-03", "fixture_raiz_3")[0] is not None
    assert cell("fixture_canal_b", "2150-05", "fixture_raiz_2")[0] == 0
    assert all(cell("fixture_canal_c", LAST, root)[0] is None for root in ROOTS)


# --- the browser -----------------------------------------------------------------------------


#: Where stage 2.3 kept the same pinned bodies, by sha256, on a machine that ran it.
PROTOTYPE_BODIES = ROOT / "prototypes" / "framework" / "runs" / "cdn_bodies"


def _cdn_cache() -> pathlib.Path:
    """The pinned bodies, each checked against its sha256: from the cache, else
    from stage 2.3's copies, else fetched from its URL as it is."""
    base = os.environ.get("BICE_CDN_CACHE") or os.path.join(
        os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache"), "bi-como-codigo", "cdn")
    cache = pathlib.Path(base)
    cache.mkdir(parents=True, exist_ok=True)
    for pin in json.loads(CDN.read_text(encoding="utf-8"))["files"]:
        path = cache / pin["sha256"]
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == pin["sha256"]:
            continue
        local = PROTOTYPE_BODIES / pin["sha256"]
        if local.exists():
            body = local.read_bytes()
        else:
            try:
                with urllib.request.urlopen(pin["url"], timeout=120) as response:
                    body = response.read()
            except OSError as error:
                pytest.fail(f"the pinned body {pin['url']} is not in {cache} and could not be fetched ({error}): "
                            f"place it there, named by its sha256 {pin['sha256']}")
        if hashlib.sha256(body).hexdigest() != pin["sha256"]:
            pytest.fail(f"{pin['url']}: the body found does not match its pin")
        path.write_bytes(body)
    return cache


class _Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".mjs": "text/javascript", ".bice": "application/octet-stream"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, *_args):
        pass


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    chrome = os.environ.get("BICE_CHROME") or shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome or not shutil.which("node"):
        if os.environ.get("CI"):
            pytest.skip("no Chrome or Node on this runner")
        pytest.fail("the report page's checks 1 to 3 need Chrome and Node (N119); BICE_CHROME names Chrome")
    cache = _cdn_cache()
    deploy = tmp_path_factory.mktemp("report") / "deploy"
    r.build(ROOT, deploy)
    if REAL:  # the page served with the real package in place of the invented one
        shutil.rmtree(deploy / "package")
        shutil.copytree(REAL, deploy / "package")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Handler, directory=str(deploy)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    password = next(p.password for p in r.profiles(ROOT) if p.id == DECLARATION["profile"])
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/relatorios/p01.html"
        run = subprocess.run(["node", str(DRIVER), url, password, str(cache), str(CDN)], capture_output=True, text=True,
                             timeout=240, env={**os.environ, "BICE_CHROME": chrome})
    finally:
        server.shutdown()
    assert run.returncode == 0, run.stderr[-3000:]
    return json.loads(run.stdout)


def test_the_page_runs_without_an_error(seen):
    assert seen["errors"] == []


def test_a_wrong_password_opens_nothing(seen):
    assert seen["wrongPassword"] == {"error": True, "report": False}


def test_the_inputs(seen):
    assert seen["inputs"] == {"filter": {"options": ["todos", *CHANNELS], "value": "todos"}, "month": {"options": MONTHS, "value": LAST}}
    assert seen["question"] == DECLARATION["question"]


@pytest.mark.parametrize("filter_", ["todos", *CHANNELS])
def test_the_summary_agrees_with_the_package(seen, filter_):
    """The summary is a crosstab: a month per row, its row header, and a root
    category per column, each cell the net revenue of its rows, or a G — the
    mark seen, the report's text said —; the notice before the partial month."""
    pivot = SUMMARY["pivot"]
    expected = []
    for month in MONTHS:
        if month == LAST:
            expected.append({"note": PARTIAL})
        row = [{"row": month}]
        for root in ROOTS:
            net, _units = cell(filter_, month, root)
            row.append(brl(net) if net is not None else {"mark": pivot["empty_mark"], "said": EMPTY})
        expected.append(row)
    view = seen["views"][filter_]
    assert view["heads"]["summary"] == [pivot["row_label"], *ROOTS]
    assert view["tables"]["summary"] == expected
    has_g = any(cell(filter_, m, root)[0] is None for m in MONTHS for root in ROOTS)
    assert view["keys"]["summary"] == (f"{pivot['empty_mark']} {EMPTY}" if has_g else None)


@pytest.mark.parametrize("filter_", ["todos", *CHANNELS])
def test_the_detail_of_the_last_month_agrees_with_the_package(seen, filter_):
    rows = sorted((x for x in ROWS if x["year_month"] == LAST and filter_ in ("todos", x["sales_channel_name"])),
                  key=lambda x: (x["sales_channel_name"], x["category_name"]))
    expected = [[x["sales_channel_name"], x["category_name"], integer(x["order_count"]), integer(x["unit_count"]), brl(x["net_revenue_amount"])]
                for x in rows] or [[EMPTY]]
    assert seen["views"][filter_]["tables"]["detail"] == expected + [{"note": PARTIAL}]


def _hex(colour: str) -> tuple[int, int, int]:
    if colour.startswith("#"):
        return tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))
    return tuple(int(v) for v in re.findall(r"\d+", colour)[:3])


def _series(view) -> dict[str, str]:
    """Each series' stroke, by the legend's key colour."""
    by_rgb = {_hex(colour): name for name, colour, _pressed in view["legend"]}
    strokes = {}
    for line in view["lines"]:
        strokes.setdefault(by_rgb[_hex(line["stroke"])], line["stroke"])
    return strokes


@pytest.mark.parametrize("filter_", ["todos", *CHANNELS])
def test_every_month_stays_on_the_axis(seen, filter_):
    assert [month for month, _x in seen["views"][filter_]["xLabels"]] == MONTHS


@pytest.mark.parametrize("filter_", ["todos", *CHANNELS])
def test_the_chart_agrees_with_the_package(seen, filter_):
    """Each series read back from the SVG through the axes: every point at its
    month to a pixel and its value to under a pixel, a gap at each G, the
    partial month dashed from the month before."""
    view = seen["views"][filter_]
    x_of = {popup["month"]: popup["ruleX"] for popup in view["popups"]}  # where the vertical stands at each month
    # A label stands at its tick's exact height plus a constant baseline offset; the
    # grid lines stand at the same ticks rounded to a whole pixel. Their mean
    # difference is the offset, so the labels give the axis exactly.
    labels = sorted(view["yLabels"], key=lambda label: label[1])  # top first: the largest value
    assert len(labels) == len(view["yGrid"]) >= 2, (labels, view["yGrid"])
    offset = sum(anchor - y for (_text, anchor), y in zip(labels, sorted(view["yGrid"]))) / len(labels)
    ticks = [(int(text.replace(".", "")), anchor - offset) for text, anchor in labels]
    (v0, y0), (v1, y1) = min(ticks), max(ticks)
    per_px = (v1 - v0) / (y0 - y1)
    by_rgb = {_hex(colour): name for name, colour, _pressed in view["legend"]}

    def read(run):
        out = []
        for x, y in run:
            month = min(MONTHS, key=lambda mo: abs(x_of[mo] - x))
            assert abs(x_of[month] - x) < 1, (x, month)
            out.append((month, v0 + (y0 - y) * per_px))
        return out

    def runs(months):
        found, current = [], []
        for month in months:
            if cell(filter_, month, root)[0] is None:
                if current:
                    found.append(current)
                current = []
            else:
                current.append(month)
        return found + ([current] if current else [])

    for root in ROOTS:
        layers = {"solid": [], "dashed": []}
        for line in view["lines"]:
            if by_rgb[_hex(line["stroke"])] == root:
                layers["dashed" if "layer_1" in line["layer"] else "solid"].extend(read(run) for run in line["runs"])
        for drawn, months in ((layers["solid"], MONTHS[:-1]), (layers["dashed"], MONTHS[-2:])):
            assert [[mo for mo, _v in run] for run in drawn] == runs(months), (root, filter_)
            for run in drawn:
                for month, value in run:
                    assert abs(value - float(cell(filter_, month, root)[0])) <= 0.75 * per_px, (root, filter_, month)


def test_a_category_keeps_its_colour_under_every_filter(seen):
    strokes = {f: _series(seen["views"][f]) for f in ["todos", *CHANNELS]}
    assert all(s == strokes["todos"] for s in strokes.values())
    assert sorted(strokes["todos"]) == ROOTS and len(set(strokes["todos"].values())) == len(ROOTS)


@pytest.mark.parametrize("filter_", ["todos", *CHANNELS])
def test_the_popup_lists_every_series_at_every_month(seen, filter_):
    popups = seen["views"][filter_]["popups"]
    assert [p["month"] for p in popups] == MONTHS
    for popup in popups:
        month = popup["month"]
        value = {root: cell(filter_, month, root)[0] for root in ROOTS}
        order = sorted(ROOTS, key=lambda root: (value[root] is None, -(value[root] or 0), root))
        assert [row[:2] for row in popup["rows"]] == [[root, brl(value[root]) if value[root] is not None else EMPTY] for root in order]
        assert popup["notice"] == (PARTIAL if month == LAST else None)


def test_the_partial_month_is_marked_on_the_chart(seen):
    assert all(seen["views"][f]["partialMark"] == ["mês incompleto"] for f in ["todos", *CHANNELS])


def _opacities(state, view):
    names = _series(view)
    return {root: state["strokes"][names[root]] for root in ROOTS}


def test_the_legend_highlights_and_isolates(seen):
    """N104: a click isolates, Shift adds, a double click restores; hovering a
    label highlights it."""
    it, view = seen["interactions"], seen["views"]["todos"]
    dim = DECLARATION["chart"]["vega_lite"]["layer"][0]["encoding"]["opacity"]["value"]
    order = it["shiftEnter"]["order"]
    assert order == ROOTS

    def only(*names):
        return {root: 1 if root in names else dim for root in ROOTS}

    assert _opacities(it["isolateSecond"], view) == only(order[1])
    assert it["isolateSecond"]["pressed"] == ["false", "true", "false", "false"] and it["isolateSecond"]["all"]
    assert _opacities(it["addThird"], view) == only(order[1], order[2])
    assert _opacities(it["doubleClickPlot"], view) == only(*ROOTS) and not it["doubleClickPlot"]["all"]
    assert _opacities(it["hoverFirst"], view) == only(order[0]) and it["hoverFirst"]["pressed"] == ["false"] * 4
    assert _opacities(it["hoverAway"], view) == only(*ROOTS)
    assert it["shiftEnter"]["pressed"] == ["false", "true", "false", "false"]
    assert it["restored"]["pressed"] == ["false"] * 4 and not it["restored"]["all"]


def test_a_click_on_a_line_isolates_it(seen):
    it = seen["interactions"]
    assert it.get("clickLine"), "no point of the chart stood apart from the other lines"
    names = {stroke: name for name, stroke in _series(seen["views"]["todos"]).items()}
    pressed = dict(zip(it["shiftEnter"]["order"], it["clickLine"]["pressed"]))
    assert pressed == {root: "true" if root == names[it["clickLine"]["stroke"]] else "false" for root in ROOTS}


def test_the_keyboard_moves_the_vertical(seen):
    it = seen["interactions"]
    assert it["keyEnd"]["tip"]["month"] == LAST and it["keyEnd"]["tip"]["notice"] == PARTIAL
    assert it["keyEnd"]["announce"].startswith(f"{LAST}. {PARTIAL.rstrip('.')};")
    assert it["keyLeft"]["month"] == MONTHS[-2]
    assert it["keyEscape"] is None


def test_the_tab_order_and_focus(seen):
    """Skip link, site link, the two filters, logout, the legend, the chart,
    then each table's region; every stop shows its focus."""
    tabs = seen["interactions"]["tabs"]
    expected = [("a", "skip", "Pular para o relatório"), ("a", None, "bi-como-codigo"), ("select", "filter", None), ("select", "month", None),
                ("button", "logout", "Sair"), *[("button", "legend-item", root) for root in ROOTS], ("div", "chart", None),
                ("div", "table-scroll", DECLARATION["tables"][0]["title"]), ("div", "table-scroll", DECLARATION["tables"][1]["title"])]
    got = [(t["tag"], t["bice"] or t["cls"], t["text"] if text is not None else None) for t, (_tag, _kind, text) in zip(tabs, expected)]
    assert len(tabs) == len(expected) and got == expected, [(t["tag"], t["bice"] or t["cls"], t["text"]) for t in tabs]
    assert all(t["outline"] for t in tabs), [t for t in tabs if not t["outline"]]


def test_a_narrow_screen_does_not_scroll_sideways(seen):
    assert seen["loginOverflow"] <= 0 and seen["narrow"]["overflow"] <= 0


def test_a_tap_places_the_vertical_and_isolates_nothing(seen):
    """The vertical stands at the month nearest the tap: within half the step
    between two months — the labels' spacing, as their rotated anchors sit a
    constant distance off their months —; nothing is isolated."""
    tap = seen["narrow"]["tap"]
    xs = sorted(x for _month, x in tap["labels"])
    step = (xs[-1] - xs[0]) / (len(xs) - 1)
    assert tap["tip"] is not None and tap["tip"]["month"] in MONTHS
    assert abs(tap["tip"]["ruleX"] - tap["x"]) <= step / 2 + 0.5
    assert tap["pressed"] == ["false"] * len(ROOTS)


def _luminance(rgb):
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r_, g, b = (channel(c) for c in rgb)
    return 0.2126 * r_ + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    la, lb = sorted((_luminance(_hex(a)), _luminance(_hex(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_both_schemes_are_legible(seen, scheme):
    """Text at 4.5:1 against its surface in both schemes; each series at 3:1 in
    the dark, and in the light, where three of the validated slots fall below
    it, the summary table is the relief; the chart wears the scheme's series."""
    s = seen["schemes"][scheme]
    assert contrast(s["text"], s["surface"]) >= 4.5 and contrast(s["muted"], s["surface"]) >= 4.5
    if scheme == "dark":
        assert all(contrast(colour, s["surface"]) >= 3 for colour in s["tokens"][:len(ROOTS)])
    else:
        assert seen["views"]["todos"]["tables"]["summary"]
    assert {_hex(c) for c in s["strokes"]} == {_hex(c) for c in s["tokens"][:len(ROOTS)]}
    assert _hex(s["body"][0]) == _hex(s["surface"])


def test_logout_leaves_nothing_of_the_report(seen):
    assert seen["afterLogout"] == {"tables": 0, "svg": 0}
