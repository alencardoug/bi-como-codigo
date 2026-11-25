// The query engine of the report pages (docs/report_page.md §3.1): DuckDB-WASM
// and its Parquet extension, pinned (site/app/cdn.json; N94, N98), started on
// load — they carry no data — and ended with their worker at logout. Nothing
// is written to any store.
import * as duckdb from "@duckdb/duckdb-wasm";
import pins from "./pins.mjs";

// A pinned body, fetched with its integrity: the browser refuses other bytes.
async function pinned(name, type) {
  const pin = pins[name];
  const response = await fetch(pin.url, { integrity: pin.integrity, credentials: "omit", mode: "cors" });
  if (!response.ok) throw new Error(`${pin.url} answered ${response.status}`);
  return URL.createObjectURL(new Blob([await response.arrayBuffer()], { type }));
}

export async function start() {
  const [workerUrl, wasmUrl] = await Promise.all([pinned("duckdb_worker", "text/javascript"), pinned("duckdb_wasm", "application/wasm")]);
  const worker = new Worker(workerUrl);
  const db = new duckdb.AsyncDuckDB(new duckdb.VoidLogger(), worker);
  await db.instantiate(wasmUrl);
  URL.revokeObjectURL(workerUrl);
  URL.revokeObjectURL(wasmUrl);
  // The Parquet extension, pinned, in place of the engine's own unpinned fetch
  // of it: autoloading off, then LOAD of the checked bytes. The fragment names
  // the file, from which DuckDB takes the extension's entry point.
  const setup = await db.connect();
  await setup.query("SET GLOBAL autoinstall_known_extensions = false");
  await setup.query("SET GLOBAL autoload_known_extensions = false");
  for (const [name, pin] of Object.entries(pins).filter(([, p]) => p.extension)) {
    const url = await pinned(name, "application/wasm");
    await setup.query(`LOAD '${url}#/${pin.extension}.duckdb_extension.wasm'`);
    URL.revokeObjectURL(url);
  }
  await setup.close();
  return { db, worker };
}

// The table the page queries: the report's Parquet, registered, copied into a
// table and dropped as a file.
export async function load(engine, table, parquet) {
  await engine.db.registerFileBuffer(`${table}.parquet`, parquet);
  const conn = await engine.db.connect();
  await conn.query(`create table ${table} as select * from read_parquet('${table}.parquet')`);
  await engine.db.dropFile(`${table}.parquet`);
  return async function query(sql, params) {
    const statement = await conn.prepare(sql);
    try {
      return (await statement.query(...params)).toArray().map((row) => row.toJSON());
    } finally {
      await statement.close();
    }
  };
}
