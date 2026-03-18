from __future__ import annotations

import io
import struct

from backend import apply_backend_compression, apply_backend_decompression
from binaryio import pack_u16, pack_u32, read_exact, unpack_text_from_file, unpack_u16, unpack_u32
from constants import CHUNK_HEADER_SIZE, MODE_NAMES
from errors import CorruptArchiveError, UnsupportedModeError


def serialize_chunk_body(bundle: dict) -> bytes:
    templates = bundle["templates"]
    value_dict = bundle["value_dict"]
    token_to_pattern = bundle["token_to_pattern"]
    payload = bundle["payload"]

    out = bytearray()

    for template in templates:
        encoded = template.encode("utf-8")
        out.extend(pack_u16(len(encoded)))
        out.extend(encoded)

    for value in value_dict:
        encoded = value.encode("utf-8")
        out.extend(pack_u16(len(encoded)))
        out.extend(encoded)

    for token, pattern in token_to_pattern.items():
        out.append(token)
        out.extend(pack_u16(len(pattern)))
        out.extend(pattern)

    out.extend(payload)
    return bytes(out)


def serialize_chunk(bundle: dict, chunk_orig_size: int, backend: int, backend_level: int) -> tuple[bytes, dict]:
    raw_body = serialize_chunk_body(bundle)
    comp_body = apply_backend_compression(raw_body, backend, backend_level)

    out = bytearray()
    out.append(bundle["mode"])
    out.append(backend)
    out.extend(pack_u16(0))
    out.extend(pack_u32(chunk_orig_size))
    out.extend(pack_u32(bundle["logical_size"]))
    out.extend(pack_u16(len(bundle["templates"])))
    out.extend(pack_u16(len(bundle["value_dict"])))
    out.extend(pack_u16(len(bundle["token_to_pattern"])))
    out.extend(pack_u32(bundle["record_count"]))
    out.extend(pack_u32(len(comp_body)))
    out.extend(comp_body)

    stats = {
        "chunk_body_size": len(raw_body),
        "final_chunk_size": len(out),
        "backend_stage_saved": max(0, len(raw_body) - len(comp_body)),
    }
    return bytes(out), stats


def parse_chunk_from_file(f) -> dict:
    head = read_exact(f, CHUNK_HEADER_SIZE)
    offset = 0

    mode = head[offset]
    offset += 1
    backend = head[offset]
    offset += 1
    _reserved, offset = unpack_u16(head, offset)
    orig_size, offset = unpack_u32(head, offset)
    logical_size, offset = unpack_u32(head, offset)
    template_count, offset = unpack_u16(head, offset)
    value_dict_count, offset = unpack_u16(head, offset)
    dict_count, offset = unpack_u16(head, offset)
    record_count, offset = unpack_u32(head, offset)
    body_len, offset = unpack_u32(head, offset)

    if orig_size < 0 or logical_size < 0 or body_len < 0:
        raise CorruptArchiveError("Negative sizes encountered in chunk header")

    comp_body = read_exact(f, body_len)
    body = apply_backend_decompression(comp_body, backend)
    bio = io.BytesIO(body)

    templates = [unpack_text_from_file(bio) for _ in range(template_count)]
    value_dict = [unpack_text_from_file(bio) for _ in range(value_dict_count)]

    token_to_pattern: dict[int, bytes] = {}
    for _ in range(dict_count):
        token_blob = read_exact(bio, 1)
        if len(token_blob) != 1:
            raise CorruptArchiveError("Failed to read token byte")
        token = token_blob[0]

        plen_blob = read_exact(bio, 2)
        plen = struct.unpack(">H", plen_blob)[0]
        pattern = read_exact(bio, plen)
        token_to_pattern[token] = pattern

    payload = bio.read()

    if mode not in MODE_NAMES:
        raise UnsupportedModeError(f"Unknown chunk mode: {mode}")

    return {
        "mode": mode,
        "backend": backend,
        "orig_size": orig_size,
        "logical_size": logical_size,
        "templates": templates,
        "value_dict": value_dict,
        "token_to_pattern": token_to_pattern,
        "record_count": record_count,
        "payload": payload,
        "body_len": body_len,
        "decompressed_body_len": len(body),
    }