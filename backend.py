from __future__ import annotations

import gzip
import zlib

from constants import BACKEND_NONE, BACKEND_GZIP, BACKEND_ZLIB


def resolve_backend(name: str) -> int:
    mapping = {
        "none": BACKEND_NONE,
        "gzip": BACKEND_GZIP,
        "zlib": BACKEND_ZLIB,
    }
    return mapping[name]


def apply_backend_compression(data: bytes, backend: int, level: int = 9) -> bytes:
    if backend == BACKEND_NONE:
        return data
    if backend == BACKEND_GZIP:
        return gzip.compress(data, compresslevel=level)
    if backend == BACKEND_ZLIB:
        return zlib.compress(data, level)
    raise ValueError(f"Unknown backend: {backend}")


def apply_backend_decompression(data: bytes, backend: int) -> bytes:
    if backend == BACKEND_NONE:
        return data
    if backend == BACKEND_GZIP:
        return gzip.decompress(data)
    if backend == BACKEND_ZLIB:
        return zlib.decompress(data)
    raise ValueError(f"Unknown backend: {backend}")