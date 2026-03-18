from __future__ import annotations

from binaryio import pack_u32, pack_u64, read_exact, unpack_u32, unpack_u64
from constants import HEADER_SIZE, MAGIC, VERSION_MAJOR, VERSION_MINOR
from errors import FormatError, VersionError


def write_header(f, *, flags: int, chunk_bytes: int, chunk_count: int, orig_size: int, checksum: bytes) -> None:
    header = bytearray()
    header.extend(MAGIC)
    header.append(VERSION_MAJOR)
    header.append(VERSION_MINOR)
    header.append(flags)
    header.append(0)
    header.extend(pack_u32(chunk_bytes))
    header.extend(pack_u32(chunk_count))
    header.extend(pack_u64(orig_size))
    checksum = checksum if checksum else (b"\x00" * 32)
    if len(checksum) != 32:
        raise ValueError("Checksum must be 32 bytes")
    header.extend(checksum)
    f.seek(0)
    f.write(header)


def read_header(f) -> dict:
    blob = read_exact(f, HEADER_SIZE)
    offset = 0
    magic = blob[offset:offset + 4]
    offset += 4
    if magic != MAGIC:
        raise FormatError("Bad container magic")

    major = blob[offset]
    offset += 1
    minor = blob[offset]
    offset += 1

    if major != VERSION_MAJOR:
        raise VersionError(
            f"Unsupported archive major version: {major}.{minor}. "
            f"Expected {VERSION_MAJOR}.x"
        )

    flags = blob[offset]
    offset += 1
    _reserved = blob[offset]
    offset += 1
    chunk_bytes, offset = unpack_u32(blob, offset)
    chunk_count, offset = unpack_u32(blob, offset)
    orig_size, offset = unpack_u64(blob, offset)
    checksum = blob[offset:offset + 32]

    return {
        "flags": flags,
        "chunk_bytes": chunk_bytes,
        "chunk_count": chunk_count,
        "orig_size": orig_size,
        "checksum": checksum,
        "version": (major, minor),
    }


def iter_line_chunks(path: str, target_bytes: int):
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        lines: list[str] = []
        size = 0

        for line in f:
            line_bytes = line.encode("utf-8")
            line_size = len(line_bytes)

            if lines and size + line_size > target_bytes:
                chunk_text = "".join(lines)
                yield chunk_text.encode("utf-8")
                lines = [line]
                size = line_size
            else:
                lines.append(line)
                size += line_size

        if lines:
            chunk_text = "".join(lines)
            yield chunk_text.encode("utf-8")