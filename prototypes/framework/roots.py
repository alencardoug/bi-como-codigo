"""Where the harness reads and writes, apart from where its code is (CMP-3-03).

`make prototype` runs the harness from a snapshot of its commit — the
tracked files of every harness path, exported from Git and made read-only
(`route.pinned`) —, so no file of the working tree is read while it runs.
The snapshot's code lives there; the repository it is of, the runs' state
and the clear mode's files do not, and are named here: by the environment
the snapshot is started with, and otherwise beside this file.
"""

from __future__ import annotations

import os
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
#: The Git repository the harness is of — its objects are its identity.
CHECKOUT = pathlib.Path(os.environ.get("BICE_REPO") or HERE.parents[1])
RUNS = pathlib.Path(os.environ.get("BICE_RUNS") or HERE / "runs")
CLEAR = pathlib.Path(os.environ.get("BICE_CLEAR") or HERE / "clear")
#: Running from a snapshot of the commit: nothing of the working tree is read.
PINNED = os.environ.get("BICE_SNAPSHOT") == "1"


if __name__ == "__main__":  # what a snapshot resolves to, for its test
    import json

    print(json.dumps({"here": str(HERE), "checkout": str(CHECKOUT), "runs": str(RUNS), "clear": str(CLEAR), "pinned": PINNED}))
