"""The sandbox of stage 2.3 (docs/framework_prototype.md §5).

Every phase that runs package code — the offline install, a script found
necessary, the build — runs through `run`, in bubblewrap: a work folder bound
read-write and the only host-backed thing writable, the system's `/usr` and
the TLS and DNS files read-only, the sandbox's own root remounted read-only,
an empty `HOME` and `/tmp` on tmpfs that vanish with it, a named
environment, its own PID namespace, no network, and no file descriptor
beyond 0, 1 and 2. The real home folder, the checkout, the clear mode and
the Docker socket are not bound at all.

`prove` runs the probe of §5 through the same wrapper; `variant` removes one
option, so that each check is shown to fail where its option is missing.
"""

from __future__ import annotations

import dataclasses
import json
import os
import pathlib
import secrets
import shutil
import socket
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROBE = HERE / "sandbox_probe.py"
WORK = "/work"
HOME = "/home/sandbox"
PATH = "/usr/local/bin:/usr/bin"
READ_ONLY = ("/usr", "/etc/ssl", "/etc/ca-certificates", "/etc/resolv.conf", "/etc/hosts", "/etc/nsswitch.conf")


@dataclasses.dataclass(frozen=True)
class Options:
    """The wrapper's options; each is removed by one variant of the proof."""

    clearenv: bool = True
    unshare_pid: bool = True
    unshare_net: bool = True
    extra_binds: tuple[str, ...] = ()  # host paths bound read-write: only a variant has any


def command(work: pathlib.Path, argv: list[str], *, env: dict[str, str] | None = None,
            options: Options = Options()) -> list[str]:
    cmd = ["bwrap", "--die-with-parent", "--new-session", "--unshare-ipc", "--unshare-uts"]
    if options.unshare_pid:
        cmd.append("--unshare-pid")
    if options.unshare_net:
        cmd.append("--unshare-net")
    if options.clearenv:
        cmd.append("--clearenv")
    named = {"PATH": PATH, "HOME": HOME, "LANG": "C.UTF-8", "TZ": "UTC", "npm_config_cache": f"{WORK}/.npm-cache"} | (env or {})
    for key, value in named.items():
        cmd += ["--setenv", key, value]
    for path in READ_ONLY:
        if os.path.lexists(path):
            cmd += ["--ro-bind", os.path.realpath(path), path]
    cmd += ["--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
            "--symlink", "usr/sbin", "/sbin", "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--tmpfs", "/home",
            "--dir", HOME, "--bind", str(work.resolve()), WORK, "--chdir", WORK]
    for path in options.extra_binds:
        cmd += ["--bind", path, path]
    cmd += ["--remount-ro", "/"]  # the sandbox's own root too: only the work folder, /tmp and HOME are writable
    return cmd + ["--", *argv]


def run(work: pathlib.Path, argv: list[str], *, env: dict[str, str] | None = None, options: Options = Options(),
        timeout: float | None = None, pass_fds: tuple[int, ...] = ()) -> subprocess.CompletedProcess:
    """Started with every descriptor beyond 0, 1 and 2 closed."""
    return subprocess.run(command(work, argv, env=env, options=options), capture_output=True, timeout=timeout,
                          close_fds=True, pass_fds=pass_fds, stdin=subprocess.DEVNULL)


@dataclasses.dataclass(frozen=True)
class Proof:
    passed: bool
    checks: dict[str, bool]
    detail: dict


def prove(work: pathlib.Path, *, absent: list[str], options: Options = Options(), pass_fds: tuple[int, ...] = ()) -> Proof:
    """The probe of §5 through the wrapper: `absent` are the host paths it must
    not see — stated, never read. The harness puts a synthetic token in its own
    environment, opens a listener on its loopback, and gives the probe its own
    PID and its parent's; no real credential is read."""
    token_name = "BICE_PROBE_TOKEN"
    token = secrets.token_hex(16)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    config = {"absent": absent, "token_name": token_name, "host_pids": [os.getpid(), os.getppid()], "port": port,
              "write": ["/usr/bice-probe", "/etc/bice-probe", "/bice-probe", *[os.path.join(p, "bice-probe") for p in absent if os.path.isdir(p)]],
              "registry": "registry.npmjs.org"}
    shutil.copyfile(PROBE, work / "sandbox_probe.py")
    (work / "probe.json").write_text(json.dumps(config))
    saved = os.environ.get(token_name)
    os.environ[token_name] = token
    try:
        result = run(work, ["/usr/bin/python3", f"{WORK}/sandbox_probe.py", f"{WORK}/probe.json"], options=options,
                     timeout=60, pass_fds=pass_fds)
    finally:
        listener.close()
        if saved is None:
            os.environ.pop(token_name, None)
        else:
            os.environ[token_name] = saved
        for name in ("sandbox_probe.py", "probe.json"):
            (work / name).unlink(missing_ok=True)
    try:
        detail = json.loads(result.stdout)
    except ValueError:
        return Proof(False, {}, {"exit": result.returncode, "stderr": result.stderr.decode(errors="replace")[-2000:]})
    checks = detail["checks"]
    return Proof(result.returncode == 0 and all(checks.values()), checks, detail)


def host_absent(checkout: pathlib.Path, scratch_sentinel: pathlib.Path, clear_sentinel: pathlib.Path) -> list[str]:
    """The paths of §5's probe, by their absolute host paths."""
    home = pathlib.Path.home()
    return [str(p) for p in (home, home / ".config" / "gcloud", home / ".config" / "configstore", home / ".ssh",
                             checkout / ".git", checkout / "prototypes" / "framework" / "clear",
                             pathlib.Path("/var/run/docker.sock"), pathlib.Path("/run/docker.sock"),
                             scratch_sentinel, clear_sentinel)]


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory(prefix="bice-sandbox-") as tmp:
        sentinel = pathlib.Path(tmp) / "sentinel"
        sentinel.write_text("sentinel")
        work = pathlib.Path(tmp) / "work"
        work.mkdir()
        proof = prove(work, absent=host_absent(HERE.parents[1], sentinel, HERE / "clear" / "planted"))
        print(json.dumps({"passed": proof.passed, "checks": proof.checks}, indent=2))
        sys.exit(0 if proof.passed else 1)
