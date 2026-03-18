from __future__ import annotations

import re
from collections import Counter

from binaryio import pack_text, pack_u16, pack_u32, unpack_u16, unpack_u32
from constants import RAW_RECORD, RAW_VALUE, REF_VALUE, TEMPLATE_RECORD
from errors import CorruptArchiveError

PLACEHOLDER_PATTERN = re.compile(r"<TS>|<USER>|<PATH>|<CODE>|<SERVICE>|<IP>|<HOSTNUM>")
MASTER_PATTERN = re.compile(
    r"(?P<TS>\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}\b)"
    r"|(?P<USER>user=\S+)"
    r"|(?P<PATH>path=\S+)"
    r"|(?P<CODE>code=\d+)"
    r"|(?P<SERVICE>service=\S+)"
    r"|(?P<IP>\b(?:\d{1,3}\.){3}\d{1,3}\b)"
    r"|(?P<HOSTNUM>\b[a-zA-Z][a-zA-Z0-9_-]*-\d+\b)"
)


def split_line_ending(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n") or line.endswith("\r"):
        return line[:-1], line[-1]
    return line, ""


def match_to_template_part(match: re.Match[str]) -> tuple[str, str]:
    kind = match.lastgroup
    full = match.group(0)
    if kind == "TS":
        return "<TS>", full
    if kind == "USER":
        return "user=<USER>", full.split("=", 1)[1]
    if kind == "PATH":
        return "path=<PATH>", full.split("=", 1)[1]
    if kind == "CODE":
        return "code=<CODE>", full.split("=", 1)[1]
    if kind == "SERVICE":
        return "service=<SERVICE>", full.split("=", 1)[1]
    if kind == "IP":
        return "<IP>", full
    if kind == "HOSTNUM":
        return "<HOSTNUM>", full
    return full, full


def normalize_line(line_body: str) -> tuple[str, list[str]]:
    out_parts: list[str] = []
    values: list[str] = []
    cursor = 0
    for match in MASTER_PATTERN.finditer(line_body):
        start, end = match.span()
        out_parts.append(line_body[cursor:start])
        template_part, value = match_to_template_part(match)
        out_parts.append(template_part)
        values.append(value)
        cursor = end
    out_parts.append(line_body[cursor:])
    return "".join(out_parts), values


def rebuild_line(template: str, values: list[str]) -> str:
    value_iter = iter(values)

    def repl(_: re.Match[str]) -> str:
        try:
            return next(value_iter)
        except StopIteration as exc:
            raise CorruptArchiveError("Not enough values to rebuild template line") from exc

    rebuilt = PLACEHOLDER_PATTERN.sub(repl, template)

    try:
        next(value_iter)
        raise CorruptArchiveError("Too many values provided while rebuilding template line")
    except StopIteration:
        pass

    return rebuilt


def analyze_templates(lines: list[str]) -> tuple[list[dict], Counter[str]]:
    parsed_lines: list[dict] = []
    template_counts: Counter[str] = Counter()

    for line in lines:
        body, newline = split_line_ending(line)
        template, values = normalize_line(body)
        parsed_lines.append(
            {
                "body": body,
                "newline": newline,
                "template": template,
                "values": values,
            }
        )
        template_counts[template] += 1

    return parsed_lines, template_counts


def estimate_value_dict_savings(value: str, hits: int) -> int:
    data_len = len(value.encode("utf-8"))
    raw_cost = hits * (1 + 2 + data_len)
    ref_cost = hits * (1 + 2)
    dict_cost = 2 + data_len
    return raw_cost - (ref_cost + dict_cost)


def build_value_dictionary(parsed_lines: list[dict], min_hits: int) -> list[str]:
    counts = Counter()
    for item in parsed_lines:
        counts.update(item["values"])

    kept = []
    for value, hits in counts.most_common():
        if hits < min_hits:
            continue
        if estimate_value_dict_savings(value, hits) > 0:
            kept.append(value)
    return kept


def build_template_records(
    parsed_lines: list[dict],
    template_counts: Counter[str],
    min_template_hits: int,
    value_dict: list[str],
) -> tuple[list[str], list[dict]]:
    templates = [template for template, hits in template_counts.most_common() if hits >= min_template_hits]
    template_to_id = {template: idx for idx, template in enumerate(templates)}
    value_to_id = {value: idx for idx, value in enumerate(value_dict)}

    records: list[dict] = []
    for item in parsed_lines:
        template = item["template"]
        if template_counts[template] < min_template_hits:
            records.append({"type": RAW_RECORD, "raw": item["body"] + item["newline"]})
            continue

        encoded_values = []
        for value in item["values"]:
            if value in value_to_id:
                encoded_values.append((REF_VALUE, value_to_id[value]))
            else:
                encoded_values.append((RAW_VALUE, value))

        records.append(
            {
                "type": TEMPLATE_RECORD,
                "template_id": template_to_id[template],
                "newline": item["newline"],
                "values": encoded_values,
            }
        )

    return templates, records


def template_storage_bytes(templates: list[str]) -> int:
    return sum(2 + len(t.encode("utf-8")) for t in templates)


def value_dictionary_storage_bytes(values: list[str]) -> int:
    return sum(2 + len(v.encode("utf-8")) for v in values)


def serialize_records(records: list[dict]) -> bytes:
    out = bytearray()

    for record in records:
        out.append(record["type"])

        if record["type"] == RAW_RECORD:
            raw = record["raw"].encode("utf-8")
            out.extend(pack_u32(len(raw)))
            out.extend(raw)
            continue

        if record["type"] != TEMPLATE_RECORD:
            raise ValueError(f"Unknown record type: {record['type']}")

        out.extend(pack_u16(record["template_id"]))
        out.extend(pack_text(record["newline"]))
        out.extend(pack_u16(len(record["values"])))

        for kind, value in record["values"]:
            out.append(kind)
            if kind == REF_VALUE:
                out.extend(pack_u16(value))
            elif kind == RAW_VALUE:
                out.extend(pack_text(value))
            else:
                raise ValueError(f"Unknown value kind: {kind}")

    return bytes(out)


def parse_records(payload: bytes, value_dict: list[str]) -> list[dict]:
    records = []
    offset = 0

    while offset < len(payload):
        record_type = payload[offset]
        offset += 1

        if record_type == RAW_RECORD:
            raw_len, offset = unpack_u32(payload, offset)
            raw = payload[offset:offset + raw_len]
            if len(raw) != raw_len:
                raise CorruptArchiveError("Payload truncated while reading raw record")
            offset += raw_len
            records.append({"type": RAW_RECORD, "raw": raw.decode("utf-8")})
            continue

        if record_type != TEMPLATE_RECORD:
            raise CorruptArchiveError(f"Unknown record type in payload: {record_type}")

        template_id, offset = unpack_u16(payload, offset)
        newline_len, offset = unpack_u16(payload, offset)
        newline = payload[offset:offset + newline_len].decode("utf-8")
        if len(payload[offset:offset + newline_len]) != newline_len:
            raise CorruptArchiveError("Payload truncated while reading template newline")
        offset += newline_len

        value_count, offset = unpack_u16(payload, offset)
        values: list[str] = []

        for _ in range(value_count):
            if offset >= len(payload):
                raise CorruptArchiveError("Payload truncated while reading value kind")
            kind = payload[offset]
            offset += 1

            if kind == REF_VALUE:
                value_id, offset = unpack_u16(payload, offset)
                if value_id >= len(value_dict):
                    raise CorruptArchiveError(f"Value dictionary id out of range: {value_id}")
                values.append(value_dict[value_id])
            elif kind == RAW_VALUE:
                value_len, offset = unpack_u16(payload, offset)
                value = payload[offset:offset + value_len]
                if len(value) != value_len:
                    raise CorruptArchiveError("Payload truncated while reading raw value")
                offset += value_len
                values.append(value.decode("utf-8"))
            else:
                raise CorruptArchiveError(f"Unknown value kind: {kind}")

        records.append(
            {
                "type": TEMPLATE_RECORD,
                "template_id": template_id,
                "newline": newline,
                "values": values,
            }
        )

    return records