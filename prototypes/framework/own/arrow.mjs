// apache-arrow as the module DuckDB-WASM's browser bundle imports by name. The
// pinned UMD build, loaded before any module by a classic script with its
// integrity, defines `Arrow`; this module re-exports what the bundle reads
// from its namespace — checked against the pinned bundle by the tests.
const A = globalThis.Arrow;
if (!A) throw new Error("apache-arrow did not load");
export const { RecordBatchReader, Table, Type, tableFromIPC, tableToIPC } = A;
