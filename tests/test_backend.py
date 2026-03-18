from __future__ import annotations

from backend import (
    apply_backend_compression,
    apply_backend_decompression,
    resolve_backend,
)
from constants import BACKEND_GZIP, BACKEND_NONE, BACKEND_ZLIB


def test_backend_none_roundtrip() -> None:
    data = b"hello world" * 100
    comp = apply_backend_compression(data, BACKEND_NONE, 9)
    decomp = apply_backend_decompression(comp, BACKEND_NONE)
    assert decomp == data


def test_backend_gzip_roundtrip() -> None:
    data = b"hello world" * 100
    comp = apply_backend_compression(data, BACKEND_GZIP, 9)
    decomp = apply_backend_decompression(comp, BACKEND_GZIP)
    assert decomp == data


def test_backend_zlib_roundtrip() -> None:
    data = b"hello world" * 100
    comp = apply_backend_compression(data, BACKEND_ZLIB, 9)
    decomp = apply_backend_decompression(comp, BACKEND_ZLIB)
    assert decomp == data


def test_resolve_backend_names() -> None:
    assert resolve_backend("none") == BACKEND_NONE
    assert resolve_backend("gzip") == BACKEND_GZIP
    assert resolve_backend("zlib") == BACKEND_ZLIB