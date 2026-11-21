"""The probe of docs/framework_prototype.md §5, run inside the sandbox by the
system's Python. It stats — never reads — the host paths it is given, reads
its own environment, lists /proc and its descriptors, tries to write outside
the work folder and to reach the network, and prints what it found as JSON.
"""

import json
import os
import socket
import sys

config = json.load(open(sys.argv[1]))
checks = {}
seen = {}

for path in config["absent"]:
    try:
        os.stat(path)
        found = True
    except FileNotFoundError:
        found = False
    except OSError:
        found = True  # there, but not readable: still seen
    checks["absent " + path] = not found

checks["token not inherited"] = config["token_name"] not in os.environ
seen["environment"] = sorted(os.environ)

own = {kind: os.readlink("/proc/self/ns/" + kind) for kind in ("pid", "ipc", "uts", "net", "mnt")}
seen["namespaces"] = own
checks["own PID namespace"] = own["pid"] != config["host_ns"]["pid"]
checks["own IPC namespace"] = own["ipc"] != config["host_ns"]["ipc"]
checks["own UTS namespace"] = own["uts"] != config["host_ns"]["uts"]
checks["own network namespace"] = own["net"] != config["host_ns"]["net"]
checks["own mount namespace"] = own["mnt"] != config["host_ns"]["mnt"]
others = set()
for p in os.listdir("/proc"):
    if p.isdigit():
        try:
            others.add(os.readlink("/proc/" + p + "/ns/pid"))
        except OSError:
            others.add("unreadable")  # a process it cannot inspect is not shown to be its own
seen["pid_namespaces_visible"] = sorted(others)
checks["every visible process in its own PID namespace"] = others == {own["pid"]}
# bubblewrap's setsid: the session's leader is inside the sandbox's PID namespace.
# Seen from inside, a leader outside the namespace has SID 0; no number of the
# host's is compared, since namespaces may share numbers (PROTO-2-07).
seen["sid"] = os.getsid(0)
checks["a session of its own"] = os.getsid(0) != 0
checks["root not writable"] = not os.access("/", os.W_OK)

# Every live descriptor, a directory's included; only the one this listing
# opens is left out, by its own number (PROTO-2-07).
listing = os.open("/proc/self/fd", os.O_RDONLY | os.O_DIRECTORY)
try:
    listed = [int(fd) for fd in os.listdir(listing) if int(fd) != listing]
    fds = []
    for fd in listed:  # listdir's own duplicate is closed by now; an inherited one is not
        try:
            os.readlink("/proc/self/fd/%d" % fd)
            fds.append(fd)
        except OSError:
            pass
    fds.sort()
finally:
    os.close(listing)
seen["fds"] = fds
checks["only fds 0, 1, 2"] = fds == [0, 1, 2]

for path in config["write"]:
    wrote = False
    try:
        with open(path, "w") as handle:
            handle.write("x")
        wrote = True  # recorded before any cleanup, which may fail on its own
    except OSError:
        pass
    if wrote:
        try:
            os.unlink(path)
        except OSError:
            pass
    checks["no write " + path] = not wrote

try:
    socket.create_connection(("127.0.0.1", config["port"]), timeout=3).close()
    reached = True
except OSError:
    reached = False
checks["host loopback unreachable"] = not reached

try:
    socket.create_connection((config["registry"], 443), timeout=5).close()
    reached = True
except OSError:
    reached = False
checks["registry unreachable"] = not reached

print(json.dumps({"checks": checks, "seen": seen}))
