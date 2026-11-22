// The report runner of Candidate B (prototypes/framework/own/report.mjs), with
// a query function that answers from fixed rows: formatting in pt-BR, the
// empty cell apart from the zero, the inputs, and the partial-month notice.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as runner from "../own/report.mjs";

const report = JSON.parse(readFileSync(new URL("../own/p01.report.json", import.meta.url)));
const nbsp = (s) => s.replace(/ /g, " ");

test("amounts are formatted exactly from their decimal text, counts from BigInt", () => {
  assert.equal(nbsp(runner.format("1234567890123.50", "brl")), "R$ 1.234.567.890.123,50");
  assert.equal(nbsp(runner.format("0.00", "brl")), "R$ 0,00");
  assert.equal(runner.format(9007199254740993n, "int"), "9.007.199.254.740.993");
  assert.equal(runner.format(null, "brl"), null);
  assert.equal(runner.format("fixture_canal_a", "text"), "fixture_canal_a");
});

test("a cell with no row says so, and a zero is a value", () => {
  const summary = report.tables.find((t) => t.bice === "summary");
  const rows = [
    { year_month: "2134-07", root_category_name: "r3", net_revenue_amount: null, unit_count: null },
    { year_month: "2134-09", root_category_name: "r2", net_revenue_amount: "0.00", unit_count: 788273n },
  ];
  const cells = runner.cells(summary, rows);
  assert.deepEqual(cells[0].slice(2), [{ text: "Sem vendas neste recorte.", empty: true }, { text: "Sem vendas neste recorte.", empty: true }]);
  assert.equal(nbsp(cells[1][2].text), "R$ 0,00");
  assert.equal(cells[1][2].empty, false);
});

test("order_count is shown only in the detail, never summed", () => {
  const where = report.tables.filter((t) => t.columns.some((c) => c.field === "order_count")).map((t) => t.bice);
  assert.deepEqual(where, ["detail"]);
  for (const q of Object.values(report.queries)) assert.doesNotMatch(q.sql, /sum\(\s*order_count/i);
});

function fake(answers) {
  const calls = [];
  const query = async (sql, params) => {
    calls.push({ sql, params });
    const name = Object.keys(report.queries).find((k) => report.queries[k].sql === sql);
    return answers[name](params);
  };
  return { query, calls };
}

test("the inputs come from the data, with todos first and the last month selected", async () => {
  const { query } = fake({ canais: () => [{ value: "a" }, { value: "b" }], meses: () => [{ value: "2134-03" }, { value: "2139-03" }] });
  const inputs = await runner.inputs(report, query);
  assert.deepEqual(inputs.map((i) => [i.bice, i.options, i.initial]), [["filter", ["todos", "a", "b"], "todos"], ["month", ["2134-03", "2139-03"], "2139-03"]]);
});

test("params follow each query's declaration, and the partial notice marks the last month", async () => {
  const { query, calls } = fake({
    por_mes: () => [{ year_month: "2139-03", root_category_name: "r1", net_revenue_amount: 1.5 }],
    resumo: () => [
      { year_month: "2139-02", root_category_name: "r1", net_revenue_amount: "1.00", unit_count: 10000n },
      { year_month: "2139-03", root_category_name: "r1", net_revenue_amount: "2.00", unit_count: 20000n },
    ],
    detalhe: () => [],
  });
  const shown = await runner.view(report, { canal: "b", mes: "2139-03" }, "2139-03", query);
  assert.deepEqual(calls.map((c) => c.params), [["b"], ["b"], ["b", "2139-03"]]);
  const [summary, detail] = shown.tables;
  assert.deepEqual(summary.partialRows, [1]);
  assert.equal(detail.partial, true);
  assert.equal(detail.empty, "Sem vendas neste recorte.");
  assert.equal(report.partial.text, "Mês em curso: os números ainda vão mudar.");
  await assert.rejects(runner.view(report, { canal: "b" }, "2139-03", query), /the input mes has no value/);
});
