from __future__ import annotations

from pathlib import Path

import pytest

from errors import ValidationError
from validation import (
    ensure_archive_suffix,
    ensure_input_exists,
    ensure_input_suffix,
    validate_compress_paths,
    validate_decompress_paths,
)


def test_ensure_input_exists_ok(tmp_path: Path) -> None:
    p = tmp_path / "a.log"
    p.write_text("x", encoding="utf-8")
    assert ensure_input_exists(str(p)) == p


def test_ensure_input_exists_missing(tmp_path: Path) -> None:
    p = tmp_path / "missing.log"
    with pytest.raises(ValidationError):
        ensure_input_exists(str(p))


def test_ensure_input_suffix_ok(tmp_path: Path) -> None:
    p = tmp_path / "a.log"
    p.write_text("x", encoding="utf-8")
    assert ensure_input_suffix(str(p)) == p


def test_ensure_input_suffix_bad(tmp_path: Path) -> None:
    p = tmp_path / "a.exe"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(ValidationError):
        ensure_input_suffix(str(p))


def test_ensure_archive_suffix_ok(tmp_path: Path) -> None:
    p = tmp_path / "a.rzzip"
    assert ensure_archive_suffix(str(p)) == p


def test_ensure_archive_suffix_bad(tmp_path: Path) -> None:
    p = tmp_path / "a.zip"
    with pytest.raises(ValidationError):
        ensure_archive_suffix(str(p))


def test_validate_compress_paths_same_file(tmp_path: Path) -> None:
    p = tmp_path / "same.log"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(ValidationError):
        validate_compress_paths(str(p), str(p))


def test_validate_decompress_paths_same_file(tmp_path: Path) -> None:
    p = tmp_path / "same.rzzip"
    p.write_bytes(b"abc")
    with pytest.raises(ValidationError):
        validate_decompress_paths(str(p), str(p))


def test_validate_compress_paths_ok(tmp_path: Path) -> None:
    src = tmp_path / "in.log"
    dst = tmp_path / "out.rzzip"
    src.write_text("x", encoding="utf-8")
    in_path, out_path = validate_compress_paths(str(src), str(dst))
    assert in_path == src
    assert out_path == dst


def test_validate_decompress_paths_ok(tmp_path: Path) -> None:
    src = tmp_path / "in.rzzip"
    dst = tmp_path / "out.log"
    src.write_bytes(b"abc")
    in_path, out_path = validate_decompress_paths(str(src), str(dst))
    assert in_path == src
    assert out_path == dst