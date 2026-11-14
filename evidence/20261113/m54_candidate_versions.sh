#!/bin/sh
# M54: the versions on the npm registry that stage 2.3's plan pins, and when
# each package last changed. Reads the public registry only.
date -u +'%Y-%m-%dT%H:%M:%SZ'
for p in @evidence-dev/evidence @evidence-dev/core-components @duckdb/duckdb-wasm vega vega-lite vega-embed; do
  printf '%s latest=%s modified=%s\n' "$p" "$(npm view "$p" version)" "$(npm view "$p" time.modified)"
done
echo "@duckdb/duckdb-wasm dist-tags:"; npm view @duckdb/duckdb-wasm dist-tags --json
echo "@duckdb/duckdb-wasm last stable (no -dev):"
npm view @duckdb/duckdb-wasm versions --json | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>console.log(JSON.parse(s).filter(v=>!v.includes("-")).slice(-3).join(" ")))'
echo "@evidence-dev/evidence@40.1.8 dependencies on DuckDB, Svelte, ECharts:"
npm view @evidence-dev/evidence@40.1.8 dependencies --json | grep -i -E 'duckdb|sveltejs/kit|echarts'
echo "@evidence-dev/universal-sql (Evidence's browser engine) and its DuckDB-WASM range:"
npm view @evidence-dev/universal-sql version
npm view @evidence-dev/universal-sql dependencies --json | grep -i duckdb
echo "@duckdb/duckdb-wasm@1.32.0 published:"; npm view @duckdb/duckdb-wasm time --json | grep '"1.32.0"'
