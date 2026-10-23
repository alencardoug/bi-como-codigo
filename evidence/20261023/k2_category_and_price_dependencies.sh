#!/usr/bin/env bash
# k2 — does anything in eng_dados, besides the generator, depend on today's category names or on the
# single price range? Answers the item of PLAN §9 that stage 1.4 was to find out. Reads tracked files
# only (`git grep` at HEAD); the names come from the generator itself, never typed here.
# The eng_dados checkout comes from ENG_DADOS_DIR (default: ~/Projetos/mvp_eng_dados_1).
set -uo pipefail
cd "${ENG_DADOS_DIR:-$HOME/Projetos/mvp_eng_dados_1}"
echo "# k2_category_and_price_dependencies.sh — $(date -u +%Y-%m-%dT%H:%M:%SZ) — eng_dados at $(git rev-parse --short HEAD)"

names=$(.venv/bin/python -c "
from mvp_ed1.generator.providers import ARVORE_DE_CATEGORIAS
print('\n'.join(n for nivel in ARVORE_DE_CATEGORIAS for n in nivel))")
echo "category names, from generator/providers.py: $(echo "$names" | wc -l)"

# Whole words only: 'Moda' must not match 'Modalidade'.
patterns=()
while IFS= read -r n; do patterns+=(-e "$n"); done <<< "$names"
outside_generator=(-- . ':!src/mvp_ed1/generator' ':!CONVERSAS_COM_CHAT')

echo
echo "## category names outside the generator and the study trail"
git grep -n -I -w -F "${patterns[@]}" "${outside_generator[@]}" | cut -c1-200
echo "[matches: $(git grep -c -I -w -F "${patterns[@]}" "${outside_generator[@]}" | awk -F: '{s+=$NF} END {print s+0}')]"

echo
echo "## the price range and the margin, outside the generator"
git grep -n -I -E 'faixa_de_preco|margem_sobre_o_custo|4800(\.00)?\b|\b9\.90\b' "${outside_generator[@]}" ':!uv.lock' | cut -c1-200
echo "[matches: $(git grep -c -I -E 'faixa_de_preco|margem_sobre_o_custo|4800(\.00)?\b|\b9\.90\b' "${outside_generator[@]}" ':!uv.lock' | awk -F: '{s+=$NF} END {print s+0}')]"

echo
echo "## category names in the study trail (CONVERSAS_COM_CHAT) — files and matches"
git grep -c -I -w -F "${patterns[@]}" -- CONVERSAS_COM_CHAT
