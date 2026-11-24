"""Serve the two artifacts of one draw of stage 2.3 with the prototype's own server
(prototypes/framework/serve.py), until interrupted: B on the first port, Evidence on
the second.

    uv run --group prototype python evidence/20261124/serve.py <draw folder> 8101 8102

With a folder and one port, it serves that folder alone — the chart demonstration
built by chart_interaction/apply_demo.py:

    uv run --group prototype python evidence/20261124/serve.py <folder> 8103
"""
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "prototypes" / "framework"))
from serve import Server  # noqa: E402

if len(sys.argv) == 3:
    with Server(pathlib.Path(sys.argv[1]), int(sys.argv[2])) as one:
        print("Serving:", one.url, flush=True)
        while True:
            time.sleep(3600)
draw, port_b, port_e = pathlib.Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
with Server(draw / "own" / "artifact", port_b) as b, Server(draw / "evidence" / "artifact", port_e) as e:
    print("B:", b.url, "Evidence:", e.url, flush=True)
    while True:
        time.sleep(3600)
