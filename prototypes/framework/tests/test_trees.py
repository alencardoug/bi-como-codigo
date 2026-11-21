"""The host-side tree reads of trees.py, on their own (PROTO-3-02)."""

from __future__ import annotations

import os
import pathlib
import tarfile
import gzip
import io

import pytest

import trees


def _aliased(tmp_path: pathlib.Path) -> pathlib.Path:
    """`lexical/via/../dist`, where `via` is a link to `physical/assets`: the
    kernel resolves it to `physical/dist` (two files); a normalized spelling
    reads `lexical/dist` (one file)."""
    (tmp_path / "physical/assets").mkdir(parents=True)
    (tmp_path / "physical/dist").mkdir()
    (tmp_path / "physical/dist/index.html").write_text("<p>a</p>")
    (tmp_path / "physical/dist/rows.json").write_text("[1]")
    (tmp_path / "lexical/dist").mkdir(parents=True)
    (tmp_path / "lexical/dist/index.html").write_text("<p>a</p>")
    os.symlink(tmp_path / "physical/assets", tmp_path / "lexical/via")
    return tmp_path / "lexical/via/../dist"


def test_a_link_hidden_behind_a_dot_dot_is_refused_before_normalizing(tmp_path):
    source = _aliased(tmp_path)
    with pytest.raises(trees.Refused):
        trees.real_root(source)
    with pytest.raises(trees.Refused):
        trees.archive(source, tmp_path / "out.tar.gz")
    with pytest.raises(trees.Refused):
        trees.files(source)
    with pytest.raises(trees.Refused):
        trees.copy(source, tmp_path / "copy")
    assert not (tmp_path / "out.tar.gz").exists()


def test_a_relative_root_is_checked_from_the_working_folder(tmp_path, monkeypatch):
    (tmp_path / "real/dist").mkdir(parents=True)
    (tmp_path / "real/dist/a.txt").write_text("a")
    monkeypatch.chdir(tmp_path)
    assert trees.real_root(pathlib.Path("real/dist")) == tmp_path / "real/dist"
    digest = trees.archive(pathlib.Path("real/dist"), tmp_path / "a.tar.gz")
    with tarfile.open(fileobj=io.BytesIO(gzip.decompress((tmp_path / "a.tar.gz").read_bytes()))) as tar:
        assert tar.getnames() == ["a.txt"]
    assert len(digest) == 64


@pytest.mark.parametrize("form", ["//", "/", "../"])
def test_a_relative_part_that_is_absolute_or_leaves_is_refused(tmp_path, form):
    """PROTO-4-09: `//x` is an absolute path, not a folder under the base —
    refused even when the folder it names exists."""
    (tmp_path / "work").mkdir()
    (tmp_path / "sibling").mkdir()
    (tmp_path / "sibling" / "marker").write_text("x")
    rel = {"//": "/" + str(tmp_path / "sibling"), "/": str(tmp_path / "sibling"), "../": "../sibling"}[form]
    with pytest.raises(trees.Refused):
        trees.real_root(tmp_path / "work", rel)
