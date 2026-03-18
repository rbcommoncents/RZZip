from __future__ import annotations

import io

import pytest

from chunks import parse_chunk_from_file, serialize_chunk
from constants import BACKEND_NONE, MODE_RAW
from errors import UnsupportedModeError


def test_chunk_serialize_parse_roundtrip() -> None:
    bundle = {
        "mode": MODE_RAW,
        "templates": [],
        "value_dict": [],
        "token_to_pattern": {},
        "payload": b"hello world",
        "logical_size": 11,
        "record_count": 0,
    }
    blob, stats = serialize_chunk(bundle, chunk_orig_size=11, backend=BACKEND_NONE, backend_level=0)
    parsed = parse_chunk_from_file(io.BytesIO(blob))
    assert parsed["mode"] == MODE_RAW
    assert parsed["orig_size"] == 11
    assert parsed["payload"] == b"hello world"
    assert stats["final_chunk_size"] == len(blob)


def test_chunk_unknown_mode_raises() -> None:
    bundle = {
        "mode": 255,
        "templates": [],
        "value_dict": [],
        "token_to_pattern": {},
        "payload": b"hello",
        "logical_size": 5,
        "record_count": 0,
    }
    blob, _ = serialize_chunk(bundle, chunk_orig_size=5, backend=BACKEND_NONE, backend_level=0)
    with pytest.raises(UnsupportedModeError):
        parse_chunk_from_file(io.BytesIO(blob))