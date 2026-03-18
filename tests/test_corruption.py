from __future__ import annotations

from pathlib import Path

import pytest

from cli import build_parser, compress_file, decompress_file
from container import read_header
from errors import ChecksumMismatchError, CorruptArchiveError, FormatError, VersionError


def test_truncated_archive_raises(sample_log_file: Path, archive_file: Path, tmp_path: Path) -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "compress",
            str(sample_log_file),
            str(archive_file),
            "--backend",
            "gzip",
            "--resource-profile",
            "fast",
        ]
    )
    compress_file(str(sample_log_file), str(archive_file), args)

    bad = tmp_path / "truncated.rzlog"
    blob = archive_file.read_bytes()
    bad.write_bytes(blob[:-10])

    with pytest.raises(CorruptArchiveError):
        decompress_file(str(bad), str(tmp_path / "restored.log"), verify_checksum=False)


def test_bad_magic_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.rzlog"
    bad.write_bytes(b"BAD!" + b"\x00" * 52)
    with pytest.raises(FormatError):
        with bad.open("rb") as f:
            read_header(f)


def test_bad_version_raises(tmp_path: Path) -> None:
    bad = tmp_path / "badver.rzlog"
    blob = bytearray()
    blob.extend(b"RZLG")
    blob.append(99)
    blob.append(0)
    blob.extend(b"\x00" * (56 - 6))
    bad.write_bytes(bytes(blob))

    with pytest.raises(VersionError):
        with bad.open("rb") as f:
            read_header(f)


def test_checksum_mismatch_raises(sample_log_file: Path, archive_file: Path, tmp_path: Path) -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "compress",
            str(sample_log_file),
            str(archive_file),
            "--backend",
            "gzip",
            "--resource-profile",
            "fast",
        ]
    )
    compress_file(str(sample_log_file), str(archive_file), args)

    blob = bytearray(archive_file.read_bytes())
    blob[-1] ^= 0xFF  # flip last byte
    bad = tmp_path / "checksum_bad.rzlog"
    bad.write_bytes(bytes(blob))

    with pytest.raises((ChecksumMismatchError, CorruptArchiveError)):
        decompress_file(str(bad), str(tmp_path / "restored.log"), verify_checksum=True)