// The report runner of Candidate B (docs/framework_prototype.md §4): it reads a
// report declaration — p01.report.json — and runs its queries through a
// `query(sql, params)` function the page gives it, over the table the page
// registered after login. It knows nothing of the DOM and nothing of the
// envelope: it turns the declaration and the inputs into rows and cells, which
// the page renders. Every value it formats is formatted here, in pt-BR.

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

// The options of each input, from its query, and its initial value.
export async function inputs(report, query) {
  const out = [];
  for (const input of report.inputs) {
    const values = (await run(report, input.options, {}, query)).map((r) => String(r.value));
    const options = input.all ? [input.all, ...values] : values;
    const initial = input.all ? input.all : input.default === "last" ? values[values.length - 1] : values[0];
    out.push({ ...input, options, initial, last: values[values.length - 1] });
  }
  return out;
}

// A table's cells: each declared column formatted, or the empty-cell text when
// the value is absent — a summary cell with no row under the filter. A cell
// whose rows sum to zero has a value, and is formatted as one.
export function cells(table, rows) {
  return rows.map((row) => table.columns.map((c) => {
    const text = format(row[c.field], c.format);
    return text === null ? { text: table.empty_cell, empty: true } : { text, empty: false };
  }));
}

// Everything the page shows for the current inputs: the chart's rows, and each
// table's header, cells and the rows the partial-month notice goes on.
export async function view(report, current, last, query) {
  const chart = (await run(report, report.chart.query, current, query)).map((r) => ({ ...r }));
  const tables = [];
  for (const t of report.tables) {
    const rows = await run(report, t.query, current, query);
    const partialRows = t.month_field ? rows.map((r, i) => (r[t.month_field] === last ? i : -1)).filter((i) => i >= 0) : [];
    const partial = t.month_input ? current[t.month_input] === last : partialRows.length > 0;
    tables.push({
      bice: t.bice, title: t.title, header: t.columns.map((c) => c.label), cells: cells(t, rows),
      empty: rows.length === 0 ? t.empty_table || null : null, partialRows, partial,
    });
  }
  return { chart, tables };
}
