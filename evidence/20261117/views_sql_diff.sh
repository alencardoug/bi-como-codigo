#!/usr/bin/env sh
# M56 — what changed in the declaration of the 16 views between the old pin (4da9e60) and v2.1.0 (eb11709).
# Reads Git only, in the checkout ENG_DADOS_DIR names; runs nothing of that project.
set -eu
: "${ENG_DADOS_DIR:?set ENG_DADOS_DIR to a checkout of mvp_eng_dados_2}"
echo "# views_sql_diff.sh — $(date -u +%Y-%m-%dT%H:%M:%SZ) — git only"
echo "## files changed under dbt/models/consumption"
git -C "$ENG_DADOS_DIR" diff --stat 4da9e60 eb11709 -- dbt/models/consumption
echo "## .sql files changed under dbt/models/consumption: $(git -C "$ENG_DADOS_DIR" diff --name-only 4da9e60 eb11709 -- 'dbt/models/consumption/*.sql' | wc -l)"
echo "## models changed under dbt/models (any layer)"
git -C "$ENG_DADOS_DIR" diff --stat 4da9e60 eb11709 -- dbt/models
