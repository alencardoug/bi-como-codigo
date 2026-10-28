#!/usr/bin/env bash
# P8's host-process check, as written and with a bracketed pgrep. Reads the
# process table only. A `ps | grep` matches its own grep, whose arguments hold
# the pattern; brackets keep a pattern from matching its own command line.
date -u +%Y-%m-%dT%H:%M:%SZ
echo "--- as written: ps -eo pid,pgid,args | grep -E 'mvp_ed1\.streaming|prism|beam'"
ps -eo pid,pgid,args | grep -E 'mvp_ed1\.streaming|prism|beam'
echo "[exit $?]"
echo "--- bracketed: pgrep -af 'mvp_ed1[.](streaming|airbyte)|[p]rism|[b]eam'"
pgrep -af 'mvp_ed1[.](streaming|airbyte)|[p]rism|[b]eam'
echo "[exit $?]"
