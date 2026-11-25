// The tables of a report page (docs/report_page.md §3.4): each in a region of
// its own that scrolls sideways on a narrow screen, so the page never does;
// the notice of the partial month on its rows; numbers aligned right. A
// crosstab's row keys are row headers, and its first column stays in place
// as the region scrolls.

export const el = (tag, attrs = {}, text) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text !== undefined) e.textContent = text;
  return e;
};

const NUMERIC = new Set(["brl", "int"]);

export function table(t, partialText) {
  const region = el("div", { class: "table-scroll", role: "region", tabindex: "0", "aria-label": t.title });
  const out = el("table", { "data-bice": t.bice });
  out.append(el("caption", {}, t.title));
  const head = el("tr");
  t.header.forEach((h, i) => head.append(el("th", { scope: "col", class: NUMERIC.has(t.formats[i]) ? "num" : "" }, h)));
  const thead = el("thead");
  thead.append(head);
  out.append(thead);
  const body = el("tbody");
  const note = () => {
    const tr = el("tr", { class: "note" });
    const td = el("td", { colspan: String(t.header.length), "data-bice": "partial" });
    td.append(el("span", { class: "pinned" }, partialText));  // stays in view as a wide table scrolls
    tr.append(td);
    return tr;
  };
  if (t.empty) {
    const tr = el("tr");
    tr.append(el("td", { colspan: String(t.header.length), "data-bice": "empty" }, t.empty));
    body.append(tr);
  }
  const partialAt = new Set(t.partialRows);
  t.cells.forEach((row, i) => {
    if (partialAt.has(i) && !partialAt.has(i - 1)) body.append(note());
    const tr = el("tr");
    row.forEach((c, j) => {
      if (c.head) { tr.append(el("th", { scope: "row" }, c.text)); return; }
      if (c.empty && c.mark) {  // a crosstab's empty cell: the mark is seen, the report's text is read
        const td = el("td", { "data-bice": "empty", class: "num" });
        td.append(el("span", { "aria-hidden": "true" }, c.mark), el("span", { class: "visually-hidden" }, c.text));
        tr.append(td);
        return;
      }
      const attrs = c.empty ? { "data-bice": "empty" } : NUMERIC.has(t.formats[j]) ? { class: "num" } : {};
      tr.append(el("td", attrs, c.text));
    });
    body.append(tr);
  });
  out.append(body);
  if (t.partial && t.partialRows.length === 0) {  // the detail of the partial month
    const foot = el("tfoot");
    foot.append(note());
    out.append(foot);
  }
  region.append(out);
  if (t.mark && t.cells.some((row) => row.some((c) => c.empty))) {  // what the mark means, once, under the table
    region.append(el("p", { class: "table-key", "data-bice": "key", "aria-hidden": "true" }, `${t.mark} ${t.cells.flat().find((c) => c.empty).text}`));
  }
  return region;
}
