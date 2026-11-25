// The report runner (docs/report_page.md §3.2): it reads a report's declaration
// and runs its queries through a `query(sql, params)` function the page gives
// it, over the table the page registered after login. It knows nothing of the
// DOM and nothing of the envelope: it turns the declaration and the inputs into
// rows and cells, which the page renders. Every value it formats is formatted
// here, in pt-BR, from the exact text DuckDB gives.

const BRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const INT = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

// An amount arrives as the exact decimal text DuckDB cast it to ("1234.50");
// Intl formats a decimal string exactly, never through a binary double.
export function format(value, kind) {
  if (value === null || value === undefined) return null;
  if (kind === "brl") return BRL.format(String(value));
  if (kind === "int") return INT.format(typeof value === "bigint" ? value : BigInt(value));
  return String(value);
}

// The value of each input, in the order a query's params name them.
export function params(query, inputs) {
  return (query.params || []).map((id) => {
    if (!(id in inputs)) throw new TypeError(`the input ${id} has no value`);
    return inputs[id];
  });
}

export async function run(report, name, inputs, query) {
  const q = report.queries[name];
  if (!q) throw new TypeError(`the report has no query ${name}`);
  return query(q.sql, params(q, inputs));
}

// A query's single column `value`, as text: the options of an input, or the
// series of the chart, in the order the query gives.
export async function values(report, name, query) {
  return (await run(report, name, {}, query)).map((r) => String(r.value));
}

// The options of each input, from its query, and its initial value.
export async function inputs(report, query) {
  const out = [];
  for (const input of report.inputs) {
    const found = await values(report, input.options, query);
    const options = input.all ? [input.all, ...found] : found;
    const initial = input.all ? input.all : input.default === "last" ? found[found.length - 1] : found[0];
    out.push({ ...input, options, initial, last: found[found.length - 1] });
  }
  return out;
}

// A table's cells: each declared column formatted, or the report's text for a
// cell with no row under the filter. A cell whose rows sum to zero has a
// value, and is formatted as one.
export function cells(report, table, rows) {
  return rows.map((row) => table.columns.map((c) => {
    const text = format(row[c.field], c.format);
    return text === null ? { text: report.empty, empty: true } : { text, empty: false };
  }));
}

// A crosstab (`pivot`): the query gives the grid as long rows, one per row
// key and column key, and this only lays them out — the row keys down, the
// column keys across, each in the order the query first gives it — and
// formats each value. It sums nothing: a key pair given twice is refused. A
// cell with no row under the filter is the report's empty text, shown as the
// table's mark.
export function pivot(report, table, rows) {
  const p = table.pivot;
  const across = [...new Set(rows.map((r) => String(r[p.column])))];
  const down = [...new Set(rows.map((r) => String(r[p.row])))];
  const at = new Map();
  for (const r of rows) {
    const key = `${r[p.row]}\u0000${r[p.column]}`;
    if (at.has(key)) throw new TypeError(`the crosstab ${table.bice} has two rows for one cell`);
    at.set(key, r[p.value]);
  }
  const cells = down.map((d) => [{ text: d, empty: false, head: true }, ...across.map((a) => {
    const text = format(at.get(`${d}\u0000${a}`), p.format);
    return text === null ? { text: report.empty, mark: p.empty_mark, empty: true } : { text, empty: false };
  })]);
  return { header: [p.row_label, ...across], formats: ["text", ...across.map(() => p.format)], cells, keys: down, mark: p.empty_mark };
}

// Everything the page shows for the current inputs: the chart's rows, as the
// query gives them, and each table's header, cells and the rows the
// partial-month notice goes on.
export async function view(report, current, last, query) {
  const chart = await run(report, report.chart.query, current, query);
  const tables = [];
  for (const t of report.tables) {
    const rows = await run(report, t.query, current, query);
    const laid = t.pivot ? pivot(report, t, rows)
      : { header: t.columns.map((c) => c.label), formats: t.columns.map((c) => c.format), cells: cells(report, t, rows), keys: rows.map((r) => r[t.month_field]) };
    const partialRows = t.month_field ? laid.keys.map((k, i) => (k === last ? i : -1)).filter((i) => i >= 0) : [];
    const partial = t.month_input ? current[t.month_input] === last : partialRows.length > 0;
    tables.push({
      bice: t.bice, title: t.title, header: laid.header, formats: laid.formats, cells: laid.cells, mark: laid.mark ?? null,
      empty: rows.length === 0 ? report.empty : null, partialRows, partial,
    });
  }
  return { chart, tables };
}
