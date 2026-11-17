"""Split the stream of capture.sh: sections to standard output, rows to CAPTURE_DIR.

Each section opens with a line `### <name>`. A `### rows <view>` section is the
view's rows as CSV and goes to `<CAPTURE_DIR>/<view>.csv`, outside Git; every
other section is printed as it came, and is what enters Git.
"""

import datetime
import pathlib
import sys

out_dir = pathlib.Path(sys.argv[1])
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
print(f"# capture.sh — {now} — one REPEATABLE READ READ ONLY transaction, login consumption_reader")
out_dir.mkdir(parents=True, exist_ok=True)
sink = None
written = []
for line in sys.stdin:
    if line.startswith("### "):
        if sink is not None:
            sink.close()
            sink = None
        name = line[4:].strip()
        if name.startswith("rows "):
            view = name[5:]
            path = out_dir / f"{view}.csv"
            sink = path.open("w", encoding="utf-8", newline="")
            written.append(path.name)
            continue
        print(f"\n## {name}")
        continue
    if sink is not None:
        sink.write(line)
    else:
        sys.stdout.write(line)
if sink is not None:
    sink.close()
print(f"\n## rows\n{len(written)} files written outside Git, one per view")
