from __future__ import annotations

import io

import pytest

from binaryio import (
    pack_text,
    pack_u16,
    pack_u32,
    pack_u64,
    read_exact,
    unpack_text_from_file,
    unpack_u16,
    unpack_u32,
    unpack_u64,
)
from errors import CorruptArchiveError


def test_pack_unpack_u16() -> None:
    blob = pack_u16(65535)
    value, offset = unpack_u16(blob, 0)
    assert value == 65535
    assert offset == 2


def test_pack_unpack_u32() -> None:
    blob = pack_u32(123456789)
    value, offset = unpack_u32(blob, 0)
    assert value == 123456789
    assert offset == 4


def test_pack_unpack_u64() -> None:
    blob = pack_u64(1234567890123)
    value, offset = unpack_u64(blob, 0)
    assert value == 1234567890123
    assert offset == 8


def test_pack_unpack_text() -> None:
    bio = io.BytesIO(pack_text("hello world"))
    assert unpack_text_from_file(bio) == "hello world"


def test_read_exact_success() -> None:
    bio = io.BytesIO(b"abcdef")
    assert read_exact(bio, 3) == b"abc"


def test_read_exact_raises_on_short_read() -> None:
    bio = io.BytesIO(b"abc")
    with pytest.raises(CorruptArchiveError):
        read_exact(bio, 4)