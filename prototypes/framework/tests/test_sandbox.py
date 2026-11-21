"""The sandbox of §5, proved through the same wrapper the phases use, and each
check shown to fail on a wrapper with its option removed. No real credential
is read: the probe only stats the host paths."""

from __future__ import annotations

import dataclasses
import os
import pathlib
import shutil

import pytest

import sandbox as sb

pytestmark = pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is not installed")


@pytest.fixture
def setting(tmp_path):
    """A sentinel in this test's scratch folder and one under
    `prototypes/framework/clear/`, both planted for the test and removed after."""
    sentinel_dir = tmp_path / "scratch"
    sentinel_dir.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    checkout = pathlib.Path(__file__).resolve().parents[3]
    clear = checkout / "prototypes" / "framework" / "clear" / f"planted-{tmp_path.name}"
    with sb.planted(sentinel_dir / "sentinel") as sentinel, sb.planted(clear) as clear_sentinel:
        yield work, sb.host_absent(checkout, sentinel, clear_sentinel), sentinel_dir


def test_the_wrapper_passes_its_probe(setting):
    work, absent, _ = setting
    assert all(pathlib.Path(p).exists() for p in absent[-2:])  # the sentinels are there, on the host
    proof = sb.prove(work, absent=absent)
    assert proof.passed, {k: v for k, v in proof.checks.items() if not v}
    assert proof.detail["seen"]["environment"] == ["HOME", "LANG", "PATH", "PWD", "TZ", "npm_config_cache"]  # PWD is bubblewrap's --chdir


@pytest.mark.parametrize("option, failing", sorted(sb.VARIANTS.items()))
def test_each_check_fails_without_its_option(setting, option, failing):
    work, absent, _ = setting
    proof = sb.prove(work, absent=absent, options=dataclasses.replace(sb.Options(), **{option: False}))
    assert not proof.passed and proof.checks[failing] is False


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
    script = "echo built > out.txt && ! (echo x > /bice) 2>/dev/null && ! (echo y > /usr/x) 2>/dev/null"
    assert sb.run(work, ["/usr/bin/sh", "-c", script]).returncode == 0
    assert (work / "out.txt").read_text() == "built\n"
    unprotected = sb.run(work, ["/usr/bin/sh", "-c", script], options=sb.Options(remount_ro=False))
    assert unprotected.returncode != 0  # without the remount the sandbox's own root takes the write
