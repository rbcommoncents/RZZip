from __future__ import annotations

import re
from collections import Counter

from binaryio import safe_preview_bytes
from constants import TEXT_MIN_PHRASE_CHARS, TEXT_MIN_TOKEN_LEN


def choose_escape_byte(data: bytes) -> int:
    used = set(data)
    for b in range(256):
        if b not in used:
            return b
    counts = Counter(data)
    return min(range(256), key=lambda b: counts[b])


def estimate_pattern_savings(length: int, hits: int) -> int:
    if hits < 2:
        return 0
    per_hit_gain = length - 2
    registry_cost = length + 3
    return hits * per_hit_gain - registry_cost


def add_candidate(candidates: list[dict], seen: set[bytes], pattern: bytes, source: str) -> None:
    if pattern in seen or len(pattern) < 2:
        return
    seen.add(pattern)
    candidates.append(
        {
            "pattern": pattern,
            "length": len(pattern),
            "source": source,
            "preview": safe_preview_bytes(pattern),
        }
    )


def extract_byte_candidates(
    data: bytes,
    min_len: int,
    max_len: int,
    progress: bool = False,
    label: str = "payload",
) -> list[dict]:
    candidates = []
    seen: set[bytes] = set()

    total_lengths = max_len - min_len + 1
    for idx, length in enumerate(range(max_len, min_len - 1, -1), start=1):
        if progress:
            print(f"[{label}] scanning byte patterns len={length} ({idx}/{total_lengths})", flush=True)

        counts = Counter(data[i:i + length] for i in range(0, len(data) - length + 1))
        for pattern, hits in counts.items():
            if hits < 2:
                continue
            if estimate_pattern_savings(length, hits) <= 0:
                continue
            add_candidate(candidates, seen, pattern, source="byte")

    return candidates


def extract_word_candidates(text: str) -> list[dict]:
    candidates = []
    seen: set[bytes] = set()
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_./:-]{3,}\b", text)
    counts = Counter(words)
    for word, hits in counts.items():
        pattern = word.encode("utf-8")
        if hits < 3 or len(pattern) < TEXT_MIN_TOKEN_LEN:
            continue
        if estimate_pattern_savings(len(pattern), hits) <= 0:
            continue
        add_candidate(candidates, seen, pattern, source="word")
    return candidates


def extract_phrase_candidates(text: str) -> list[dict]:
    candidates = []
    seen: set[bytes] = set()
    tokens = re.findall(r"\b[a-zA-Z0-9_./:-]+\b", text)
    for n in range(2, 6):
        phrases = Counter(" ".join(tokens[i:i + n]) for i in range(0, len(tokens) - n + 1))
        for phrase, hits in phrases.items():
            pattern = phrase.encode("utf-8")
            if hits < 3 or len(pattern) < TEXT_MIN_PHRASE_CHARS:
                continue
            if estimate_pattern_savings(len(pattern), hits) <= 0:
                continue
            add_candidate(candidates, seen, pattern, source=f"phrase{n}")
    return candidates


def extract_candidates(
    data: bytes,
    min_len: int,
    max_len: int,
    text_aware: bool,
    progress: bool = False,
    label: str = "payload",
) -> list[dict]:
    raw_candidates = []

    # Production guard: brute-force byte scanning gets very expensive on large chunks.
    byte_max_len = max_len
    if len(data) > 65536:
        byte_max_len = min(byte_max_len, 16)
        if progress:
            print(
                f"[{label}] large chunk detected ({len(data)} bytes); capping byte-pattern max_len to {byte_max_len}",
                flush=True,
            )

    raw_candidates.extend(
        extract_byte_candidates(
            data,
            min_len=min_len,
            max_len=byte_max_len,
            progress=progress,
            label=label,
        )
    )

    if text_aware:
        text = data.decode("utf-8", errors="replace")
        raw_candidates.extend(extract_word_candidates(text))
        raw_candidates.extend(extract_phrase_candidates(text))

    dedup: dict[bytes, dict] = {}
    for cand in raw_candidates:
        existing = dedup.get(cand["pattern"])
        if existing is None or cand["length"] > existing["length"]:
            dedup[cand["pattern"]] = cand

    candidates = list(dedup.values())
    candidates.sort(key=lambda x: (x["length"], x["source"]), reverse=True)
    return candidates


def find_non_overlapping_positions(data: bytes, pattern: bytes, blocked: bytearray | None = None) -> list[int]:
    positions = []
    plen = len(pattern)
    i = 0
    limit = len(data) - plen
    while i <= limit:
        if data[i:i + plen] == pattern:
            if blocked is not None and any(blocked[i:i + plen]):
                i += 1
                continue
            positions.append(i)
            i += plen
        else:
            i += 1
    return positions


def mark_blocked(blocked: bytearray, positions: list[int], length: int) -> None:
    marker = bytes([1])
    for pos in positions:
        blocked[pos:pos + length] = marker * length


def evaluate_candidate(data: bytes, candidate: dict, blocked: bytearray | None = None) -> dict | None:
    pattern = candidate["pattern"]
    positions = find_non_overlapping_positions(data, pattern, blocked)
    hits = len(positions)
    length = len(pattern)
    savings = estimate_pattern_savings(length, hits)
    if hits < 2 or savings <= 0:
        return None
    out = dict(candidate)
    out.update({"hits": hits, "savings": savings, "positions": positions})
    return out


def select_non_overlapping_patterns(
    data: bytes,
    candidates: list[dict],
    max_patterns: int,
    progress: bool = False,
    rescore_limit: int | None = 200,
    label: str = "payload",
) -> list[dict]:
    selected = []
    blocked = bytearray(len(data))
    pool = candidates if rescore_limit is None else candidates[:rescore_limit]
    used: set[bytes] = set()
    round_no = 0
    max_rounds = min(max_patterns, len(pool))

    while len(selected) < max_patterns:
        round_no += 1
        best = None
        total = len(pool)
        checked = 0

        if progress:
            print(f"[{label}] round {round_no}/{max_rounds}: rescoring candidates...", flush=True)

        for candidate in pool:
            checked += 1
            pattern = candidate["pattern"]

            if progress and (checked % 50 == 0 or checked == total):
                print(
                    f"\r[{label}] round {round_no}/{max_rounds}: {checked}/{total} candidates checked",
                    end="",
                    flush=True,
                )

            if pattern in used:
                continue

            scored = evaluate_candidate(data, candidate, blocked)
            if scored is None:
                continue

            if best is None or (
                scored["savings"], scored["length"], scored["hits"]
            ) > (
                best["savings"], best["length"], best["hits"]
            ):
                best = scored

        if progress:
            print()

        if best is None:
            if progress:
                print(f"[{label}] stopping: no more beneficial candidates", flush=True)
            break

        selected.append(best)
        used.add(best["pattern"])
        mark_blocked(blocked, best["positions"], best["length"])

        if progress:
            print(
                f"[{label}] selected #{len(selected)} | "
                f"src={best['source']} len={best['length']} "
                f"hits={best['hits']} est_saved={best['savings']}",
                flush=True,
            )

    return selected


def encode_bytes(data: bytes, token_to_pattern: dict[int, bytes], escape: int) -> bytes:
    if not token_to_pattern:
        return data

    pattern_to_token = {pattern: token for token, pattern in token_to_pattern.items()}
    lengths = sorted({len(p) for p in pattern_to_token}, reverse=True)

    out = bytearray()
    i = 0
    while i < len(data):
        matched = False
        for length in lengths:
            if i + length > len(data):
                continue
            chunk = data[i:i + length]
            token = pattern_to_token.get(chunk)
            if token is not None:
                out.append(escape)
                out.append(token)
                i += length
                matched = True
                break
        if matched:
            continue

        b = data[i]
        if b == escape:
            out.append(escape)
            out.append(escape)
        else:
            out.append(b)
        i += 1

    return bytes(out)


def decode_bytes(comp: bytes, token_to_pattern: dict[int, bytes], escape: int) -> bytes:
    if not token_to_pattern:
        return comp

    out = bytearray()
    i = 0
    while i < len(comp):
        b = comp[i]
        if b != escape:
            out.append(b)
            i += 1
            continue

        if i + 1 >= len(comp):
            raise ValueError("Dangling escape byte at end of payload")

        nxt = comp[i + 1]
        if nxt == escape:
            out.append(escape)
        else:
            pattern = token_to_pattern.get(nxt)
            if pattern is None:
                raise ValueError(f"Unknown token 0x{nxt:02X}")
            out.extend(pattern)
        i += 2

    return bytes(out)


def dictionary_storage_bytes(token_to_pattern: dict[int, bytes]) -> int:
    total = 0
    for pattern in token_to_pattern.values():
        total += 1 + 2 + len(pattern)
    return total


def compress_payload(
    payload: bytes,
    *,
    min_len: int,
    max_len: int,
    top_patterns: int,
    rescore_limit: int | None,
    text_aware: bool,
    progress: bool,
    label: str,
) -> dict:
    escape = choose_escape_byte(payload)

    candidates = extract_candidates(
        payload,
        min_len=min_len,
        max_len=max_len,
        text_aware=text_aware,
        progress=progress,
        label=label,
    )

    if progress:
        print(f"[{label}] candidate count: {len(candidates)}", flush=True)
        if rescore_limit is None:
            print(f"[{label}] rescoring all candidates", flush=True)
        else:
            print(f"[{label}] rescoring top {min(rescore_limit, len(candidates))} candidates", flush=True)

    selected = select_non_overlapping_patterns(
        payload,
        candidates,
        max_patterns=min(top_patterns, 255),
        progress=progress,
        rescore_limit=rescore_limit,
        label=label,
    )

    available_tokens = [b for b in range(256) if b != escape]
    token_to_pattern = {token: item["pattern"] for token, item in zip(available_tokens, selected)}
    comp = encode_bytes(payload, token_to_pattern, escape)

    token_savings = max(0, len(payload) - len(comp) - dictionary_storage_bytes(token_to_pattern))

    return {
        "escape": escape,
        "token_to_pattern": token_to_pattern,
        "compressed_payload": comp,
        "token_stage_saved": token_savings,
        "dictionary_bytes": dictionary_storage_bytes(token_to_pattern),
    }


def encode_chunk_payload(payload: bytes, token_to_pattern: dict[int, bytes], escape: int) -> bytes:
    if not token_to_pattern:
        return payload
    return bytes([escape]) + payload


def decode_chunk_payload(chunk: dict) -> bytes:
    payload = chunk["payload"]
    token_to_pattern = chunk["token_to_pattern"]
    if not token_to_pattern:
        return payload
    if not payload:
        return b""
    escape = payload[0]
    return decode_bytes(payload[1:], token_to_pattern, escape)