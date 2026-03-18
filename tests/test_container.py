from __future__ import annotations

import io

import pytest

from container import read_header, write_header
from constants import FLAG_CHECKSUM
from errors import FormatError, VersionError


def test_header_roundtrip() -> None:
    bio = io.BytesIO()
    checksum = b"\x11" * 32
    write_header(
        bio,
        flags=FLAG_CHECKSUM,
        chunk_bytes=4096,
        chunk_count=3,
        orig_size=12345,
        checksum=checksum,
    )
    bio.seek(0)
    header = read_header(bio)
    assert header["flags"] == FLAG_CHECKSUM
    assert header["chunk_bytes"] == 4096
    assert header["chunk_count"] == 3
    assert header["orig_size"] == 12345
    assert header["checksum"] == checksum


def test_bad_magic_raises() -> None:
    bio = io.BytesIO(b"BAD!" + b"\x00" * 52)
    with pytest.raises(FormatError):
        read_header(bio)


def test_bad_version_raises() -> None:
    bio = io.BytesIO()
    # magic + intentionally bad major version
    bio.write(b"RZLG")
    bio.write(bytes([99, 0]))  # bad major/minor
    bio.write(b"\x00" * (56 - 6))
    bio.seek(0)
    with pytest.raises(VersionError):
        read_header(bio)