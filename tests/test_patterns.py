from __future__ import annotations

from patterns import (
    choose_escape_byte,
    compress_payload,
    decode_bytes,
    dictionary_storage_bytes,
    encode_bytes,
)


def test_choose_escape_byte_returns_unused_byte() -> None:
    data = b"abc"
    escape = choose_escape_byte(data)
    assert escape not in data


def test_encode_decode_bytes_roundtrip() -> None:
    payload = b"alpha beta alpha beta alpha beta"
    token_to_pattern = {1: b"alpha beta"}
    escape = 0
    encoded = encode_bytes(payload, token_to_pattern, escape)
    decoded = decode_bytes(encoded, token_to_pattern, escape)
    assert decoded == payload


def test_dictionary_storage_bytes() -> None:
    token_to_pattern = {1: b"abc", 2: b"defg"}
    assert dictionary_storage_bytes(token_to_pattern) == (1 + 2 + 3) + (1 + 2 + 4)


def test_compress_payload_returns_expected_keys() -> None:
    payload = b"repeat repeat repeat repeat"
    out = compress_payload(
        payload,
        min_len=3,
        max_len=8,
        top_patterns=8,
        rescore_limit=50,
        text_aware=True,
        progress=False,
        label="test",
    )
    assert "escape" in out
    assert "token_to_pattern" in out
    assert "compressed_payload" in out
    assert "token_stage_saved" in out
    assert "dictionary_bytes" in out


def test_compress_payload_roundtrip() -> None:
    payload = b"error error error user=alice user=alice"
    out = compress_payload(
        payload,
        min_len=3,
        max_len=12,
        top_patterns=8,
        rescore_limit=50,
        text_aware=True,
        progress=False,
        label="test",
    )
    if out["token_to_pattern"]:
        restored = decode_bytes(out["compressed_payload"], out["token_to_pattern"], out["escape"])
    else:
        restored = out["compressed_payload"]
    assert restored == payload