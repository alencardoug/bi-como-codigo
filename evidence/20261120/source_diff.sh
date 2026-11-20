#!/usr/bin/env sh
# M61 — what changed in mvp_eng_dados_2 between v2.3.0 (2bceb47) and b0ef66e, from Git alone.
# Reads Git only, in the checkout ENG_DADOS_DIR names; runs nothing of that project.
set -eu
: "${ENG_DADOS_DIR:?set ENG_DADOS_DIR to a checkout of mvp_eng_dados_2}"
echo "# source_diff.sh — $(date -u +%Y-%m-%dT%H:%M:%SZ) — git only"
echo "## b0ef66e on origin/main"
git -C "$ENG_DADOS_DIR" branch -r --contains b0ef66e
echo "## files changed, whole tree"
git -C "$ENG_DADOS_DIR" diff --stat 2bceb47 b0ef66e
echo "## files changed under dbt/: $(git -C "$ENG_DADOS_DIR" diff --name-only 2bceb47 b0ef66e -- dbt | wc -l)"
