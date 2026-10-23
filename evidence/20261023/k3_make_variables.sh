#!/usr/bin/env bash
# k3 — does a variable given on the command line of `make medir` reach the target that
# docker/medir.sh runs? medir.sh calls `make --no-print-directory "$@"` with the target only.
# Reproduced on a throwaway Makefile with the same shape — outer make, a script, an inner make —,
# in a temporary directory, so that nothing of eng_dados runs.
set -euo pipefail
d=$(mktemp -d)
trap 'rm -rf "$d"' EXIT
printf '#!/usr/bin/env bash\nmake --no-print-directory -f %s/Makefile "$@"\n' "$d" > "$d/inner.sh"
chmod +x "$d/inner.sh"
printf 'outer:\n\t@%s/inner.sh show\nshow:\n\t@echo "inner sees RESET=[$(RESET)] FORCE=[$(FORCE)]"\n' "$d" > "$d/Makefile"
echo "# k3_make_variables.sh — $(date -u +%Y-%m-%dT%H:%M:%SZ) — $(make --version | head -1)"
for args in "RESET=1" "FORCE=1" ""; do
  printf '$ make outer %s → ' "$args"
  # shellcheck disable=SC2086
  make --no-print-directory -f "$d/Makefile" outer $args
done
