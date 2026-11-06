#!/bin/sh
# M50: how firebase-tools' `hosting:clone` parses its source — read from the
# installed CLI's own code, since its --help shows only `<site>:<channel>`.
# Reads files only. Run: sh evidence/20261106/m50_hosting_clone_source.sh
date -u +%Y-%m-%dT%H:%M:%SZ
root=$(dirname "$(dirname "$(dirname "$(readlink -f "$(command -v firebase)")")")")
echo "firebase-tools $(firebase --version), $root/lib/commands/hosting-clone.js, lines 20-31:"
sed -n 20,31p "$root/lib/commands/hosting-clone.js"
