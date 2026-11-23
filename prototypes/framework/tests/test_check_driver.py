"""The browser check through its real driver (`browser/check.mjs`), on a page of
the data-bice contract written here from the oracle itself (CMP-2-04): the page
that shows what the oracle says passes — with an empty footer cell, which shows
nothing —; one that writes a summed count beside the summary table, or whose
logout keeps the session's document, is refused for that reason."""

from __future__ import annotations

import json
import shutil

import pytest

import check
import fixture as fx_mod

pytestmark = pytest.mark.skipif(not (shutil.which("node") and shutil.which("google-chrome")), reason="needs node and Chrome")


@pytest.fixture(scope="module")
def oracle():
    return check.expected(fx_mod.generate(99)[0])


_SCRIPT = r"""
const D = __DATA__, V = __VARIANT__;
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
const table = (bice, head, rows, foot) => `<table data-bice="${bice}"><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>`
  + rows.map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`).join("")
  + (foot === null ? "" : `<tfoot><tr><td>${esc(foot)}</td></tr></tfoot>`) + "</table>";
let worker = null;
function login() {
  document.body.innerHTML = `<input data-bice="password" type="password"><button data-bice="submit">Entrar</button>
    <p data-bice="login-error" hidden>Senha incorreta: nada foi aberto.</p>`;
  $("[data-bice=submit]").onclick = () => {
    if ($("[data-bice=password]").value !== D.password) { $("[data-bice=login-error]").hidden = false; return; }
    worker = new Worker(URL.createObjectURL(new Blob(["onmessage = () => {}"], { type: "text/javascript" })));
    report();
  };
}
function report() {
  const filters = Object.keys(D.summary), months = D.months;
  document.body.innerHTML = `<select data-bice="filter">${filters.map((f) => `<option value="${esc(f)}">${esc(f)}</option>`).join("")}</select>
    <select data-bice="month">${months.map((m) => `<option value="${m}">${m}</option>`).join("")}</select>
    <div data-bice="summary"></div><div data-bice="detail"></div><button data-bice="logout">Sair</button>`;
  const show = () => {
    const f = $("[data-bice=filter]").value, m = $("[data-bice=month]").value;
    $("[data-bice=summary]").innerHTML = table("summary-table", D.summary_header, D.summary[f], V.blank_foot ? "" : D.notice)
      + (V.blank_foot ? `<p data-bice="partial">${esc(D.notice)}</p>` : "") + (V.sum_beside ? `<p>Total de pedidos: ${esc(V.sum_beside)}</p>` : "");
    const rows = D.detail[f][m], last = m === D.last;
    $("[data-bice=detail]").innerHTML = rows.length ? table("detail-table", D.detail_header, rows, last ? D.notice : null)
      : `<p data-bice="empty">${esc(D.empty)}</p>` + (last ? `<p data-bice="partial">${esc(D.notice)}</p>` : "");
  };
  $("[data-bice=filter]").onchange = show;
  $("[data-bice=month]").onchange = show;
  show();
  $("[data-bice=logout]").onclick = () => {
    worker.terminate();
    if (V.same_document) { window.kept = D; login(); } else { location.replace(location.href); }
  };
}
login();
"""


def _page(o: check.Oracle, folder, **variant) -> None:
    data = {"password": check.PASSWORD, "summary": o.summary, "detail": o.detail, "months": o.months, "last": o.last,
            "notice": check.NOTICE, "empty": check.EMPTY, "summary_header": check.SUMMARY_HEADER, "detail_header": check.DETAIL_HEADER}
    script = _SCRIPT.replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__VARIANT__", json.dumps(variant))
    folder.mkdir()
    (folder / "index.html").write_text(f'<!doctype html><meta charset="utf-8"><body></body><script>{script}</script>', encoding="utf-8")


def _reasons(o, tmp_path, name, **variant) -> set[str]:
    _page(o, tmp_path / name, **variant)
    seen = check.read(tmp_path / name, o.months, tmp_path / f"{name}.json", timeout=300)
    return {r["reason"] for r in check.compare(seen, o)}


def test_the_page_as_the_oracle_says_passes_even_with_an_empty_footer_cell(oracle, tmp_path):
    assert _reasons(oracle, tmp_path, "good", blank_foot=True) == set()


def test_a_summed_count_beside_the_summary_table_is_refused(oracle, tmp_path):
    a_sum = sorted(s for s in oracle.order_sums if "." in s)[0]
    assert _reasons(oracle, tmp_path, "sum", sum_beside=a_sum) == {"order_count summed"}


def test_a_logout_that_keeps_the_sessions_document_is_refused(oracle, tmp_path):
    assert _reasons(oracle, tmp_path, "kept", same_document=True) == {"logout"}
