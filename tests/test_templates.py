from __future__ import annotations

from templates import (
    analyze_templates,
    build_template_records,
    build_value_dictionary,
    normalize_line,
    parse_records,
    rebuild_line,
    serialize_records,
    template_storage_bytes,
    value_dictionary_storage_bytes,
)


def test_normalize_line_extracts_values() -> None:
    template, values = normalize_line(
        "2026-01-01 10:00:00 service=auth user=alice code=200 path=/login 10.0.0.1 host-1"
    )
    assert "<TS>" in template
    assert "service=<SERVICE>" in template
    assert "user=<USER>" in template
    assert "code=<CODE>" in template
    assert "path=<PATH>" in template
    assert "<IP>" in template
    assert "<HOSTNUM>" in template
    assert len(values) >= 6


def test_rebuild_line_roundtrip() -> None:
    original = "2026-01-01 10:00:00 service=auth user=alice code=200 path=/login 10.0.0.1 host-1"
    template, values = normalize_line(original)
    rebuilt = rebuild_line(template, values)
    assert rebuilt == original


def test_analyze_templates_counts() -> None:
    lines = [
        "2026-01-01 10:00:00 service=auth user=alice code=200 path=/login\n",
        "2026-01-01 10:00:01 service=auth user=bob code=200 path=/login\n",
    ]
    parsed, counts = analyze_templates(lines)
    assert len(parsed) == 2
    assert sum(counts.values()) == 2


def test_build_value_dictionary() -> None:
    lines = [
        "2026-01-01 10:00:00 service=auth user=alice code=200 path=/login\n",
        "2026-01-01 10:00:01 service=auth user=alice code=200 path=/login\n",
    ]
    parsed, counts = analyze_templates(lines)
    values = build_value_dictionary(parsed, min_hits=2)
    assert "alice" in values or "/login" in values or "200" in values


def test_serialize_parse_records_roundtrip() -> None:
    lines = [
        "2026-01-01 10:00:00 service=auth user=alice code=200 path=/login\n",
        "2026-01-01 10:00:01 service=auth user=bob code=200 path=/login\n",
    ]
    parsed, counts = analyze_templates(lines)
    value_dict = build_value_dictionary(parsed, min_hits=2)
    templates, records = build_template_records(parsed, counts, min_template_hits=2, value_dict=value_dict)
    blob = serialize_records(records)
    parsed_records = parse_records(blob, value_dict)
    assert len(parsed_records) == len(records)
    assert len(templates) >= 1


def test_template_storage_bytes() -> None:
    assert template_storage_bytes(["abc", "defg"]) == (2 + 3) + (2 + 4)


def test_value_dictionary_storage_bytes() -> None:
    assert value_dictionary_storage_bytes(["abc", "defg"]) == (2 + 3) + (2 + 4)