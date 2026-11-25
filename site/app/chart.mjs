// The chart of a report page (docs/report_page.md §3.2, §3.3; N104): the
// declaration's Vega-Lite specification, its colours, domains and sizes taken
// from the page's theme, and the interactions the page owns —
// - a legend of buttons: hovering or focusing one highlights its series, a
//   click isolates it, Shift adds another, a double click or "Mostrar todas"
//   restores all;
// - a vertical on the month nearest the pointer, a tap, or the arrow keys,
//   with a popup of every series at that month, by value, from the exact
//   amounts; a series with no row there says so, and the partial month carries
//   its notice;
// - a line within NEAR px of the pointer highlighted, and a click on it acting
//   as a click on its legend button;
// - a direct label at each line's end, apart from the others, on a screen
//   wide enough for them.
// The vertical, the highlight and the isolation are Vega signals the page
// sets, so the pointer, the keyboard and touch take one path.

import { format } from "./report.mjs";
import { el } from "./tables.mjs";

const NEAR = 8;  // px: a line this close to the pointer is the one under it (N104)
const LINE = 16;  // px between two direct labels
const WIDE = "(min-width: 40rem)";  // room for direct labels beside the plot

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

export function theme() {
  const series = [];
  for (let i = 1; css(`--series-${i}`); i++) series.push(css(`--series-${i}`));
  return {
    surface: css("--surface"), text: css("--text"), muted: css("--text-2"), grid: css("--grid"), series,
    font: getComputedStyle(document.body).fontFamily,
  };
}

function specFor(chart, domain, th, room) {
  if (domain.length > th.series.length) {
    throw new Error(`${domain.length} series and ${th.series.length} colours: fold or facet, never cycle`);
  }
  const spec = structuredClone(chart.vega_lite);
  spec.height = "container";
  spec.autosize = { type: "fit", contains: "padding" };
  spec.padding = { top: NEAR, right: room, bottom: 4, left: 4 };
  spec.config = {
    locale: { number: { decimal: ",", thousands: ".", grouping: [3], currency: ["R$ ", ""] } },
    background: "transparent",
    font: th.font,
    view: { stroke: null },
    axis: {
      labelColor: th.muted, titleColor: th.muted, gridColor: th.grid, domainColor: th.grid,
      labelFontSize: 12, titleFontSize: 12, titleFontWeight: "normal", gridWidth: 1, ticks: false, labelPadding: 6,
    },
    axisX: { grid: false },
    axisY: { domain: false, tickCount: 5 },
    mark: { invalid: "break-paths-show-domains" },  // a null breaks the line and keeps its month (M63)
    rule: { color: th.muted },
    text: { color: th.muted },
    point: { stroke: th.surface },
  };
  const scale = { domain, range: th.series.slice(0, domain.length) };
  const visit = (node) => {
    if (node.encoding?.color?.field === chart.series) node.encoding.color.scale = scale;
    (node.layer || []).forEach(visit);
  };
  visit(spec);
  return spec;
}

function toSegment(px, py, a, b) {
  const dx = b.x - a.x, dy = b.y - a.y, len = dx * dx + dy * dy;
  const t = len ? Math.max(0, Math.min(1, ((px - a.x) * dx + (py - a.y) * dy) / len)) : 0;
  return Math.hypot(px - (a.x + t * dx), py - (a.y + t * dy));
}

export class Chart {
  // parts: the elements of the page — plot, labels, legend, tip, announce.
  constructor(parts, report, last) {
    this.p = parts;
    this.r = report;
    this.c = report.chart;
    this.last = last;
    this.rows = [];
    this.domain = [];
    this.months = [];
    this.isolated = [];
    this.month = null;
    this.near = null;
    this.nearLegend = null;
    this.view = null;
    this.frame = 0;
    this.bind();
    const redraw = () => this.view && this.draw(this.rows, this.domain);
    matchMedia("(prefers-color-scheme: dark)").addEventListener("change", redraw);
    matchMedia(WIDE).addEventListener("change", redraw);  // room for the direct labels, or none
  }

  async draw(rows, domain) {
    this.rows = rows;
    this.domain = domain;
    this.byMonth = new Map();
    for (const r of rows) {
      const x = r[this.c.x];
      if (!this.byMonth.has(x)) this.byMonth.set(x, new Map());
      this.byMonth.get(x).set(r[this.c.series], r);
    }
    this.months = [...this.byMonth.keys()];
    if (this.view) this.view.finalize();
    this.th = theme();
    this.wide = matchMedia(WIDE).matches;
    const spec = globalThis.vegaLite.compile(specFor(this.c, domain, this.th, this.wide ? this.labelRoom() : 4)).spec;
    this.view = new globalThis.vega.View(globalThis.vega.parse(spec), { renderer: "svg", container: this.p.plot, hover: false });
    this.view.data("rows", rows);
    this.view.signal("isolados", this.isolated);
    const at = this.months.indexOf(this.last);  // the partial month, drawn dashed from the one before
    if (at >= 0) this.view.signal("ultimo", this.last).signal("penultimo", at > 0 ? this.months[at - 1] : null);
    this.view.addResizeListener(() => { this.drawn = null; this.labels(); });
    await this.view.runAsync();
    this.drawn = null;
    this.month = null;
    this.near = null;
    this.p.tip.hidden = true;
    this.legend();
    this.labels();
  }

  finalize() {
    if (this.view) this.view.finalize();
    this.view = null;
  }

  colour(series) {
    return this.th.series[this.domain.indexOf(series)];
  }

  value(month, series) {
    const row = this.byMonth.get(month)?.get(series);
    const v = row?.[this.c.y];
    return v === null || v === undefined ? null : v;
  }

  // The plot's own coordinates, through the screen matrix of a drawn line.
  ctm() {
    return this.p.plot.querySelector(".mark-line path")?.getScreenCTM() || null;
  }

  x(month) {
    const xs = this.view.scale("x");
    return xs(month) + (xs.bandwidth ? xs.bandwidth() / 2 : 0);
  }

  // Each series as drawn: its runs of points, a month with no row breaking the run.
  segments() {
    if (this.drawn) return this.drawn;
    const ys = this.view.scale("y");
    const out = new Map();
    for (const s of this.domain) {
      const runs = [];
      let run = [];
      for (const m of this.months) {
        const v = this.value(m, s);
        if (v === null) {
          if (run.length) runs.push(run);
          run = [];
        } else {
          run.push({ x: this.x(m), y: ys(v) });
        }
      }
      if (run.length) runs.push(run);
      out.set(s, runs);
    }
    return (this.drawn = out);
  }

  nearest(px, py) {
    let best = NEAR, near = null;
    for (const [s, runs] of this.segments()) {
      if (this.isolated.length && !this.isolated.includes(s)) continue;
      for (const run of runs) {
        for (let i = 0; i < run.length; i++) {
          const d = i === 0 ? Math.hypot(px - run[0].x, py - run[0].y) : toSegment(px, py, run[i - 1], run[i]);
          if (d < best) { best = d; near = s; }
        }
      }
    }
    return near;
  }

  nearestMonth(px) {
    let best = Infinity, at = null;
    for (const m of this.months) {
      const d = Math.abs(this.x(m) - px);
      if (d < best) { best = d; at = m; }
    }
    return at;
  }

  bind() {
    const plot = this.p.plot;
    plot.addEventListener("pointermove", (e) => this.pointer(e));
    plot.addEventListener("pointerdown", (e) => { this.touch = e.pointerType === "touch"; if (e.pointerType !== "mouse") this.pointer(e); });
    // A tap's pointer leaves as the finger lifts: the popup stays until the next tap.
    plot.addEventListener("pointerleave", (e) => { if (e.pointerType !== "touch" && !plot.matches(":focus-visible")) this.clear(); });
    // A click near a line isolates it; a tap only places the vertical — the legend isolates on touch.
    plot.addEventListener("click", (e) => { if (this.near && !this.touch) this.toggle(this.near, e.shiftKey); });
    plot.addEventListener("dblclick", () => this.isolate([]));
    plot.addEventListener("keydown", (e) => this.key(e));
    plot.addEventListener("focus", () => {
      if (plot.matches(":focus-visible") && this.month === null && this.months.length) this.show(this.months[this.months.length - 1], null, true);
    });
    plot.addEventListener("blur", () => this.clear());
  }

  pointer(e) {
    const ctm = this.view && this.ctm();
    if (!ctm) return;
    const px = (e.clientX - ctm.e) / ctm.a, py = (e.clientY - ctm.f) / ctm.d;
    this.near = this.nearest(px, py);
    this.show(this.nearestMonth(px), { x: e.clientX, y: e.clientY }, false);
  }

  key(e) {
    const n = this.months.length;
    if (!n || !this.view) return;
    let i = this.month === null ? n - 1 : this.months.indexOf(this.month);
    if (e.key === "ArrowLeft") i = Math.max(0, i - 1);
    else if (e.key === "ArrowRight") i = Math.min(n - 1, i + 1);
    else if (e.key === "Home") i = 0;
    else if (e.key === "End") i = n - 1;
    else if (e.key === "Escape") { this.clear(); return; }
    else return;
    e.preventDefault();
    this.near = null;
    this.show(this.months[i], null, true);
  }

  // The signals, at most once a frame.
  signals() {
    if (this.frame) return;
    this.frame = requestAnimationFrame(() => {
      this.frame = 0;
      if (!this.view) return;
      this.view.signal("mes", this.month).signal("perto", this.nearLegend ?? this.near).runAsync();
    });
  }

  show(month, at, announce) {
    if (month === null) return this.clear();
    this.month = month;
    this.signals();
    const spoken = this.tip(month, at);
    if (announce) this.p.announce.textContent = spoken;
  }

  clear() {
    this.month = null;
    this.near = null;
    this.p.tip.hidden = true;
    this.signals();
  }

  // The popup: every series at the month, by value, exact; returns its text.
  tip(month, at) {
    const tip = this.p.tip;
    const highlighted = this.nearLegend ?? this.near;
    const order = [...this.domain].sort((a, b) => (this.value(month, b) ?? -Infinity) - (this.value(month, a) ?? -Infinity) || a.localeCompare(b));
    tip.replaceChildren(el("strong", {}, month));
    const spoken = [];
    if (month === this.last) {
      tip.append(el("em", {}, this.r.partial.text));
      spoken.push(this.r.partial.text.replace(/\.$/, ""));
    }
    const list = el("table");
    for (const s of order) {
      const row = this.byMonth.get(month)?.get(s);
      const text = row ? format(row[this.c.y_text], this.c.y_format) : null;
      const tr = el("tr", s === highlighted ? { class: "near" } : {});
      const key = el("td");
      key.append(el("span", { class: "key", style: `--key: ${this.colour(s)}` }));
      tr.append(key, el("td", {}, s), el("td", text === null ? { "data-bice": "empty" } : { class: "num" }, text ?? this.r.empty));
      list.append(tr);
      spoken.push(`${s}: ${text ?? this.r.empty}`);
    }
    tip.append(list);
    tip.hidden = false;
    this.place(month, at);
    return `${month}. ${spoken.join("; ")}.`;
  }

  // Beside the pointer, or, from the keyboard, beside the vertical; inside the figure.
  place(month, at) {
    const tip = this.p.tip, box = tip.offsetParent?.getBoundingClientRect();
    const ctm = this.ctm();
    if (!box || !ctm) return;
    const x = at ? at.x : ctm.a * this.x(month) + ctm.e;
    const y = at ? at.y : ctm.f + NEAR;
    const pad = 12, w = tip.offsetWidth, h = tip.offsetHeight;
    let left = x - box.left + pad;
    if (left + w > box.width) left = x - box.left - pad - w;
    tip.style.left = `${Math.max(0, left)}px`;
    tip.style.top = `${Math.max(0, Math.min(box.height - h, y - box.top - (at ? h / 2 : 0)))}px`;
  }

  legend() {
    const box = this.p.legend;
    box.replaceChildren();
    for (const s of this.domain) {
      const b = el("button", { type: "button", class: "legend-item", "aria-pressed": String(this.isolated.includes(s)) });
      b.append(el("span", { class: "key", style: `--key: ${this.colour(s)}`, "aria-hidden": "true" }), document.createTextNode(s));
      b.addEventListener("click", (e) => this.toggle(s, e.shiftKey));
      b.addEventListener("keydown", (e) => { if (e.key === "Enter" && e.shiftKey) { e.preventDefault(); this.toggle(s, true); } });
      b.addEventListener("dblclick", () => this.isolate([]));
      b.addEventListener("pointerenter", () => this.hover(s));
      b.addEventListener("pointerleave", () => this.hover(null));
      b.addEventListener("focus", () => this.hover(s));
      b.addEventListener("blur", () => this.hover(null));
      box.append(b);
    }
    const all = el("button", { type: "button", class: "legend-all quiet" }, "Mostrar todas");
    all.hidden = this.isolated.length === 0;
    all.addEventListener("click", () => this.isolate([]));
    box.append(all);
  }

  hover(series) {
    this.nearLegend = series;
    this.signals();
    if (this.month !== null) this.tip(this.month, null);
  }

  toggle(series, add) {
    const on = this.isolated.includes(series);
    if (add) this.isolate(on ? this.isolated.filter((s) => s !== series) : [...this.isolated, series]);
    else this.isolate(on && this.isolated.length === 1 ? [] : [series]);
  }

  isolate(list) {
    this.isolated = list;
    if (this.view) this.view.signal("isolados", list).runAsync();
    for (const b of this.p.legend.querySelectorAll(".legend-item")) {
      b.setAttribute("aria-pressed", String(list.includes(b.textContent)));
    }
    const all = this.p.legend.querySelector(".legend-all");
    if (all) all.hidden = list.length === 0;
    for (const l of this.p.labels.querySelectorAll(".end-label")) {
      l.classList.toggle("faded", list.length > 0 && !list.includes(l.dataset.series));
    }
  }

  labelRoom() {
    const ctx = document.createElement("canvas").getContext("2d");
    ctx.font = `12px ${this.th.font}`;
    const widest = Math.max(0, ...this.domain.map((s) => ctx.measureText(s).width));
    return Math.ceil(widest) + 4 * NEAR;
  }

  // A label at each line's last point, beside the plot, spread apart, with a
  // leader line when it had to move.
  labels() {
    const box = this.p.labels;
    box.replaceChildren();
    const ctm = this.view && this.wide && this.ctm();
    if (!ctm) return;
    const frame = box.getBoundingClientRect();
    const ys = this.view.scale("y");
    const right = ctm.a * this.view.scale("x").range()[1] + ctm.e - frame.left + 2 * NEAR;
    const ends = [];
    for (const s of this.domain) {
      const m = [...this.months].reverse().find((month) => this.value(month, s) !== null);
      if (m === undefined) continue;
      ends.push({ s, x: ctm.a * this.x(m) + ctm.e - frame.left, y: ctm.d * ys(this.value(m, s)) + ctm.f - frame.top });
    }
    ends.sort((a, b) => a.y - b.y);
    let previous = -Infinity;
    for (const end of ends) { end.at = Math.max(end.y, previous + LINE); previous = end.at; }
    const overflow = previous - (frame.height - LINE / 2);
    if (overflow > 0) for (const end of ends) end.at -= overflow;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "leaders");
    for (const end of ends) {
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      for (const [k, v] of Object.entries({ x1: end.x + 5, y1: end.y, x2: right - 4, y2: end.at })) line.setAttribute(k, String(v));
      svg.append(line);
      const label = el("span", { class: "end-label", style: `left: ${right}px; top: ${end.at}px` });
      label.dataset.series = end.s;
      if (this.isolated.length && !this.isolated.includes(end.s)) label.classList.add("faded");
      label.append(el("span", { class: "key", style: `--key: ${this.colour(end.s)}` }), document.createTextNode(end.s));
      box.append(label);
    }
    box.prepend(svg);
  }
}
