from __future__ import annotations

import re
import struct

from errors import CorruptArchiveError


def pack_u16(n: int) -> bytes:
    return struct.pack(">H", n)


def pack_u32(n: int) -> bytes:
    return struct.pack(">I", n)


def pack_u64(n: int) -> bytes:
    return struct.pack(">Q", n)


def unpack_u16(blob: bytes, offset: int) -> tuple[int, int]:
    return struct.unpack_from(">H", blob, offset)[0], offset + 2


def unpack_u32(blob: bytes, offset: int) -> tuple[int, int]:
    return struct.unpack_from(">I", blob, offset)[0], offset + 4


def unpack_u64(blob: bytes, offset: int) -> tuple[int, int]:
    return struct.unpack_from(">Q", blob, offset)[0], offset + 8


def read_exact(f, n: int) -> bytes:
    data = f.read(n)
    if len(data) != n:
        raise CorruptArchiveError(f"Unexpected EOF while reading {n} bytes")
    return data


def pack_text(text: str) -> bytes:
    data = text.encode("utf-8")
    if len(data) > 65535:
        raise ValueError("Text field too large for u16 length")
    return pack_u16(len(data)) + data


def unpack_text_from_file(f) -> str:
    length = struct.unpack(">H", read_exact(f, 2))[0]
    return read_exact(f, length).decode("utf-8")


def safe_preview_bytes(data: bytes, max_len: int = 48) -> str:
    text = data.decode("utf-8", errors="replace")
    text = "".join(ch if 32 <= ord(ch) <= 126 else " " for ch in text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len] + ("..." if len(text) > max_len else "")


def safe_preview_text(text: str, max_len: int = 60) -> str:
    text = "".join(ch if 32 <= ord(ch) <= 126 else " " for ch in text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len] + ("..." if len(text) > max_len else "")