#!/usr/bin/env bash
# RR-19: `cp -a <copy>/candidato data/recovery/` over an existing candidate merges
# the two directories — a file the copy does not have stays. A model in a
# temporary directory: nothing of eng_dados is read or written.
set -euo pipefail
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/copy/candidato" "$tmp/data/recovery/candidato"
echo manifest > "$tmp/copy/candidato/manifest.json"
echo stray > "$tmp/data/recovery/candidato/unexpected.txt"
cp -a "$tmp/copy/candidato" "$tmp/data/recovery/"
echo "after cp -a over an existing candidate:"; (cd "$tmp/data/recovery/candidato" && ls -1)
rm -rf "$tmp/data/recovery/candidato"
cp -a "$tmp/copy/candidato" "$tmp/data/recovery/"
echo "after cp -a into an absent candidate path:"; (cd "$tmp/data/recovery/candidato" && ls -1)
