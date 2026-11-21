"""The sandbox of §5, proved through the same wrapper the phases use, and each
check shown to fail on a wrapper with its option removed. No real credential
is read: the probe only stats the host paths."""

from __future__ import annotations

import os
import pathlib
import shutil

import pytest

import sandbox as sb

pytestmark = pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is not installed")


@pytest.fixture
def setting(tmp_path):
    sentinel_dir = tmp_path / "scratch"
    sentinel_dir.mkdir()
    sentinel = sentinel_dir / "sentinel"
    sentinel.write_text("planted by the harness")
    work = tmp_path / "work"
    work.mkdir()
    checkout = pathlib.Path(__file__).resolve().parents[3]
    absent = sb.host_absent(checkout, sentinel, checkout / "prototypes" / "framework" / "clear" / "planted")
    return work, absent, sentinel_dir


def test_the_wrapper_passes_its_probe(setting):
    work, absent, _ = setting
    proof = sb.prove(work, absent=absent)
    assert proof.passed, {k: v for k, v in proof.checks.items() if not v}
    assert proof.detail["seen"]["environment"] == ["HOME", "LANG", "PATH", "PWD", "TZ", "npm_config_cache"]  # PWD is bubblewrap's --chdir


@pytest.mark.parametrize("options, failing", [
    (sb.Options(clearenv=False), "token not inherited"),
    (sb.Options(unshare_pid=False), "no host pid"),
    (sb.Options(unshare_net=False), "host loopback unreachable"),
])
def test_each_check_fails_without_its_option(setting, options, failing):
    work, absent, _ = setting
    proof = sb.prove(work, absent=absent, options=options)
    assert not proof.passed and not proof.checks[failing]


def test_a_bound_host_folder_is_seen_and_written(setting):
    work, absent, scratch = setting
    proof = sb.prove(work, absent=[*absent, str(scratch)], options=sb.Options(extra_binds=(str(scratch),)))
    assert not proof.checks[f"absent {scratch / 'sentinel'}"]
    assert not proof.checks[f"no write {scratch / 'bice-probe'}"]


def test_an_inherited_descriptor_is_seen(setting):
    work, absent, _ = setting
    read, write = os.pipe()
    try:
        proof = sb.prove(work, absent=absent, pass_fds=(read,))
    finally:
        os.close(read)
        os.close(write)
    assert not proof.checks["only fds 0, 1, 2"]


def test_only_the_work_folder_is_written_on_the_host(setting):
    work, _, _ = setting
    result = sb.run(work, ["/usr/bin/sh", "-c", "echo built > out.txt; echo x > /bice 2>/dev/null; echo y > /usr/x 2>/dev/null; true"])
    assert result.returncode == 0
    assert (work / "out.txt").read_text() == "built\n"
