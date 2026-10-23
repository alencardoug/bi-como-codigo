#!/usr/bin/env bash
# k1 — the rollback cut as it stands before stage 1.6: the approved package, its second copy,
# and what the warehouse has gained since the cut. Read-only: `recovery-verify` lists the dumps
# inside the warehouse container and, with CONTRA_O_BANCO=1, only counts and reads.
# The eng_dados checkout comes from ENG_DADOS_DIR (default: ~/Projetos/mvp_eng_dados_1).
set -uo pipefail
cd "${ENG_DADOS_DIR:-$HOME/Projetos/mvp_eng_dados_1}"
copy="${RECOVERY_COPY:-$HOME/mvp_ed1-recovery-20260925T123221Z/candidato}"
step() { printf '\n$ %s\n' "$*"; "$@"; printf '[exit %s]\n' "$?"; }

echo "# k1_rollback_cut.sh — $(date -u +%Y-%m-%dT%H:%M:%SZ) — eng_dados at $(git rev-parse --short HEAD)"
step ls data/recovery
step make --no-print-directory preflight ALVO=trabalho
step make --no-print-directory recovery-verify
step make --no-print-directory recovery-verify CONTRA_O_BANCO=1
step sh -c "cd '$copy' && sha256sum -c checksums.sha256"
step grep MemAvailable /proc/meminfo
