// The bodies the report pages fetch themselves, each with its integrity: written by
// tests/report_pins.py from site/app/cdn.json, never by hand.
export default {
 "duckdb_parquet": {
  "extension": "parquet",
  "integrity": "sha384-BOQzRRlWIlBsguRiM4lH3NvA+Gl1aCfYJ1IjOjyaUD0566SD7N6Jo4TnT0LmKVvs",
  "url": "https://extensions.duckdb.org/v1.4.3/wasm_eh/parquet.duckdb_extension.wasm"
 },
 "duckdb_wasm": {
  "integrity": "sha384-hw3GjeJZY5QapQ8mwqMHXBPVmTLO+jKm5dlDwkGsEfjyu/HcXx1d0Rwlr/ZAShjq",
  "url": "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.32.0/dist/duckdb-eh.wasm"
 },
 "duckdb_worker": {
  "integrity": "sha384-a2Q5wPfMJHriw96D3xhtkym83ST11xUIm6e27q9d3v4ykPqSzeY7WCXK6CTlJFwb",
  "url": "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.32.0/dist/duckdb-browser-eh.worker.js"
 }
};
