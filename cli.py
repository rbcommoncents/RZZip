from __future__ import annotations

import argparse
import hashlib
from collections import Counter
from pathlib import Path

from backend import resolve_backend
from chunks import parse_chunk_from_file, serialize_chunk
from constants import FLAG_CHECKSUM, MODE_NAMES, MODE_RAW, MODE_TEMPLATE, PROFILE_DEFAULTS, RAW_RECORD
from container import HEADER_SIZE, iter_line_chunks, read_header, write_header
from errors import ChecksumMismatchError, ValidationError
from metrics import ChunkMetrics, RunMetrics
from patterns import compress_payload, decode_chunk_payload, encode_chunk_payload
from report import print_chunk_table, print_compress_report, print_decompress_report
from templates import (
    analyze_templates,
    build_template_records,
    build_value_dictionary,
    parse_records,
    rebuild_line,
    serialize_records,
    template_storage_bytes,
    value_dictionary_storage_bytes,
)
from validation import validate_compress_paths, validate_decompress_paths


def resolve_options(args: argparse.Namespace) -> dict:
    defaults = PROFILE_DEFAULTS[args.resource_profile].copy()
    if args.chunk_bytes is not None:
        defaults["chunk_bytes"] = args.chunk_bytes
    if args.min_len is not None:
        defaults["min_len"] = args.min_len
    if args.max_len is not None:
        defaults["max_len"] = args.max_len
    if args.top_patterns is not None:
        defaults["top_patterns"] = args.top_patterns
    if args.rescore_limit is not None:
        defaults["rescore_limit"] = None if args.rescore_limit == 0 else args.rescore_limit
    if args.min_template_hits is not None:
        defaults["min_template_hits"] = args.min_template_hits
    if args.min_value_hits is not None:
        defaults["min_value_hits"] = args.min_value_hits
    return defaults


def build_raw_bundle(chunk_bytes: bytes, *, opts: dict, progress: bool) -> tuple[dict, dict]:
    if progress:
        print("[raw] building raw-dictionary candidate", flush=True)

    payload_info = compress_payload(
        chunk_bytes,
        min_len=opts["min_len"],
        max_len=opts["max_len"],
        top_patterns=opts["top_patterns"],
        rescore_limit=opts["rescore_limit"],
        text_aware=True,
        progress=progress,
        label="raw",
    )

    payload = encode_chunk_payload(
        payload_info["compressed_payload"],
        payload_info["token_to_pattern"],
        payload_info["escape"],
    )

    bundle = {
        "mode": MODE_RAW,
        "templates": [],
        "value_dict": [],
        "token_to_pattern": payload_info["token_to_pattern"],
        "payload": payload,
        "logical_size": len(chunk_bytes),
        "record_count": 0,
    }

    stats = {
        "template_stage_saved": 0,
        "token_stage_saved": payload_info["token_stage_saved"],
        "template_bytes": 0,
        "value_dict_bytes": 0,
        "token_dict_bytes": payload_info["dictionary_bytes"],
    }

    return bundle, stats


def build_template_bundle(chunk_text: str, *, opts: dict, progress: bool) -> tuple[dict, dict]:
    if progress:
        print("[template] analyzing templates and repeated field values", flush=True)

    lines = chunk_text.splitlines(keepends=True)
    parsed_lines, template_counts = analyze_templates(lines)
    value_dict = build_value_dictionary(parsed_lines, min_hits=opts["min_value_hits"])
    templates, records = build_template_records(
        parsed_lines,
        template_counts,
        min_template_hits=opts["min_template_hits"],
        value_dict=value_dict,
    )
    logical_payload = serialize_records(records)

    if progress:
        print(f"[template] templates kept: {len(templates)}", flush=True)
        print(f"[template] value dictionary entries: {len(value_dict)}", flush=True)
        print(f"[template] record count: {len(records)}", flush=True)
        print(f"[template] serialized payload bytes: {len(logical_payload)}", flush=True)

    payload_info = compress_payload(
        logical_payload,
        min_len=opts["min_len"],
        max_len=opts["max_len"],
        top_patterns=opts["top_patterns"],
        rescore_limit=opts["rescore_limit"],
        text_aware=False,
        progress=progress,
        label="template",
    )

    payload = encode_chunk_payload(
        payload_info["compressed_payload"],
        payload_info["token_to_pattern"],
        payload_info["escape"],
    )

    bundle = {
        "mode": MODE_TEMPLATE,
        "templates": templates,
        "value_dict": value_dict,
        "token_to_pattern": payload_info["token_to_pattern"],
        "payload": payload,
        "logical_size": len(logical_payload),
        "record_count": len(records),
    }

    template_saved = max(0, len(chunk_text.encode("utf-8")) - len(logical_payload))

    stats = {
        "template_stage_saved": template_saved,
        "token_stage_saved": payload_info["token_stage_saved"],
        "template_bytes": template_storage_bytes(templates),
        "value_dict_bytes": value_dictionary_storage_bytes(value_dict),
        "token_dict_bytes": payload_info["dictionary_bytes"],
    }

    return bundle, stats


def compress_file(input_path: str, output_path: str, args: argparse.Namespace) -> RunMetrics:
    validate_compress_paths(input_path, output_path)

    opts = resolve_options(args)
    backend = resolve_backend(args.backend)
    use_checksum = not args.no_checksum
    run = RunMetrics(action="compress")

    if args.progress:
        print(f"[compress] input: {input_path}", flush=True)
        print(f"[compress] output: {output_path}", flush=True)
        print(f"[compress] mode request: {args.mode}", flush=True)
        print(
            f"[compress] profile={args.resource_profile} chunk_bytes={opts['chunk_bytes']} "
            f"min_len={opts['min_len']} max_len={opts['max_len']} "
            f"top_patterns={opts['top_patterns']} rescore_limit={opts['rescore_limit']} "
            f"backend={args.backend} backend_level={args.backend_level}",
            flush=True,
        )

    hasher = hashlib.sha256() if use_checksum else None
    chunk_count = 0
    mode_counts = Counter()

    with open(output_path, "wb") as out:
        write_header(
            out,
            flags=(FLAG_CHECKSUM if use_checksum else 0),
            chunk_bytes=opts["chunk_bytes"],
            chunk_count=0,
            orig_size=0,
            checksum=b"\x00" * 32,
        )
        out.seek(HEADER_SIZE)

        for chunk_index, chunk_bytes in enumerate(iter_line_chunks(input_path, opts["chunk_bytes"]), start=1):
            chunk_text = chunk_bytes.decode("utf-8", errors="replace")
            run.original_size += len(chunk_bytes)

            if hasher is not None:
                hasher.update(chunk_bytes)

            if args.progress:
                print(f"\n[stream] chunk #{chunk_index}: original={len(chunk_bytes)} bytes", flush=True)

            candidates: dict[str, tuple[dict, dict]] = {}
            if args.mode in {"auto", "raw"}:
                candidates["raw"] = build_raw_bundle(chunk_bytes, opts=opts, progress=args.progress)
            if args.mode in {"auto", "template"}:
                candidates["template"] = build_template_bundle(chunk_text, opts=opts, progress=args.progress)

            if not candidates:
                raise ValidationError("No candidate compression modes available")

            serialized: dict[str, tuple[bytes, dict, dict, dict]] = {}
            for name, (bundle, stage_stats) in candidates.items():
                blob, chunk_stats = serialize_chunk(
                    bundle,
                    len(chunk_bytes),
                    backend=backend,
                    backend_level=args.backend_level,
                )
                serialized[name] = (blob, bundle, stage_stats, chunk_stats)

            chosen_name = min(serialized.keys(), key=lambda name: len(serialized[name][0])) if args.mode == "auto" else args.mode
            if chosen_name not in serialized:
                raise ValidationError(f"Chosen mode not available for this chunk: {chosen_name}")

            blob, bundle, stage_stats, chunk_stats = serialized[chosen_name]
            out.write(blob)

            if args.progress:
                for name, (cand_blob, cand_bundle, cand_stage_stats, cand_chunk_stats) in serialized.items():
                    print(
                        f"[stream] candidate mode={name:<8} final={len(cand_blob):>8} "
                        f"logical={cand_bundle['logical_size']:>8} payload={len(cand_bundle['payload']):>8} "
                        f"templates={len(cand_bundle['templates']):>4} values={len(cand_bundle['value_dict']):>4} "
                        f"dict={len(cand_bundle['token_to_pattern']):>4} "
                        f"tmpl_saved={cand_stage_stats['template_stage_saved']:>8} "
                        f"tok_saved={cand_stage_stats['token_stage_saved']:>8} "
                        f"backend_saved={cand_chunk_stats['backend_stage_saved']:>8}",
                        flush=True,
                    )
                print(f"[stream] chosen mode={chosen_name} stored={len(blob)} bytes", flush=True)

            chunk_metric = ChunkMetrics(
                index=chunk_index,
                mode=chosen_name,
                original_size=len(chunk_bytes),
                template_input_size=len(chunk_bytes),
                logical_size=bundle["logical_size"],
                payload_size=len(bundle["payload"]),
                chunk_body_size=chunk_stats["chunk_body_size"],
                final_chunk_size=chunk_stats["final_chunk_size"],
                template_count=len(bundle["templates"]),
                value_dict_count=len(bundle["value_dict"]),
                token_dict_count=len(bundle["token_to_pattern"]),
                record_count=bundle["record_count"],
                template_bytes=stage_stats["template_bytes"],
                value_dict_bytes=stage_stats["value_dict_bytes"],
                token_dict_bytes=stage_stats["token_dict_bytes"],
                template_stage_saved=stage_stats["template_stage_saved"],
                token_stage_saved=stage_stats["token_stage_saved"],
                backend_stage_saved=chunk_stats["backend_stage_saved"],
            )
            chunk_metric.total_saved = max(0, chunk_metric.original_size - chunk_metric.final_chunk_size)
            run.chunks.append(chunk_metric)

            run.template_count += chunk_metric.template_count
            run.value_dict_count += chunk_metric.value_dict_count
            run.token_dict_count += chunk_metric.token_dict_count

            run.template_bytes += chunk_metric.template_bytes
            run.value_dict_bytes += chunk_metric.value_dict_bytes
            run.token_dict_bytes += chunk_metric.token_dict_bytes

            run.template_stage_saved += chunk_metric.template_stage_saved
            run.token_stage_saved += chunk_metric.token_stage_saved
            run.backend_stage_saved += chunk_metric.backend_stage_saved

            chunk_count += 1
            mode_counts[chosen_name] += 1

        checksum = hasher.digest() if hasher is not None else b"\x00" * 32
        write_header(
            out,
            flags=(FLAG_CHECKSUM if use_checksum else 0),
            chunk_bytes=opts["chunk_bytes"],
            chunk_count=chunk_count,
            orig_size=run.original_size,
            checksum=checksum,
        )

    run.stop()
    run.chunk_count = chunk_count
    run.chunk_mode_counts = dict(mode_counts)
    run.compressed_size = Path(output_path).stat().st_size
    run.total_saved = run.original_size - run.compressed_size

    if args.progress:
        print(
            f"\n[compress] done: original={run.original_size} compressed={run.compressed_size} "
            f"saved={run.total_saved} elapsed={run.elapsed_seconds:.4f}s",
            flush=True,
        )

    return run


def decompress_file(
    input_path: str,
    output_path: str,
    verify_checksum: bool = True,
    progress: bool = False,
) -> RunMetrics:
    validate_decompress_paths(input_path, output_path)

    run = RunMetrics(action="decompress")
    hasher = hashlib.sha256() if verify_checksum else None

    if progress:
        print(f"[decompress] input: {input_path}", flush=True)
        print(f"[decompress] output: {output_path}", flush=True)
        print(f"[decompress] verify_checksum: {verify_checksum}", flush=True)

    with open(input_path, "rb") as f, open(output_path, "wb") as out:
        header = read_header(f)
        run.original_size = header["orig_size"]

        if progress:
            print(
                f"[decompress] chunks={header['chunk_count']} "
                f"orig_size={header['orig_size']} chunk_bytes={header['chunk_bytes']}",
                flush=True,
            )

        for chunk_index in range(1, header["chunk_count"] + 1):
            chunk = parse_chunk_from_file(f)
            logical_payload = decode_chunk_payload(chunk)

            if chunk["mode"] == MODE_RAW:
                restored = logical_payload
                mode_name = MODE_NAMES[MODE_RAW]
            elif chunk["mode"] == MODE_TEMPLATE:
                records = parse_records(logical_payload, chunk["value_dict"])
                out_parts: list[str] = []
                for record in records:
                    if record["type"] == RAW_RECORD:
                        out_parts.append(record["raw"])
                    else:
                        if record["template_id"] >= len(chunk["templates"]):
                            raise ValidationError(f"Template id out of range: {record['template_id']}")
                        rebuilt = rebuild_line(chunk["templates"][record["template_id"]], record["values"])
                        out_parts.append(rebuilt + record["newline"])
                restored = "".join(out_parts).encode("utf-8")
                mode_name = MODE_NAMES[MODE_TEMPLATE]
            else:
                raise ValidationError(f"Unknown chunk mode: {chunk['mode']}")

            out.write(restored)
            run.restored_size += len(restored)
            run.chunk_count += 1
            run.chunk_mode_counts[mode_name] = run.chunk_mode_counts.get(mode_name, 0) + 1

            if hasher is not None:
                hasher.update(restored)

            run.chunks.append(
                ChunkMetrics(
                    index=chunk_index,
                    mode=mode_name,
                    original_size=chunk["orig_size"],
                    logical_size=chunk["logical_size"],
                    payload_size=len(chunk["payload"]),
                    chunk_body_size=chunk["decompressed_body_len"],
                    final_chunk_size=chunk["body_len"] + 26,
                    template_count=len(chunk["templates"]),
                    value_dict_count=len(chunk["value_dict"]),
                    token_dict_count=len(chunk["token_to_pattern"]),
                    record_count=chunk["record_count"],
                )
            )

            if progress:
                print(
                    f"[decompress] chunk #{chunk_index}: mode={mode_name} "
                    f"orig={chunk['orig_size']} written={len(restored)}",
                    flush=True,
                )

    run.stop()

    if verify_checksum and (header["flags"] & FLAG_CHECKSUM):
        actual = hasher.digest() if hasher is not None else b""
        run.checksum_valid = actual == header["checksum"]
        if not run.checksum_valid:
            raise ChecksumMismatchError("Checksum verification failed after decompression")
    else:
        run.checksum_valid = None

    if progress:
        print(
            f"[decompress] done: restored={run.restored_size} "
            f"checksum_valid={run.checksum_valid} elapsed={run.elapsed_seconds:.4f}s",
            flush=True,
        )

    return run


def inspect_file(input_path: str, top: int = 10) -> None:
    if not Path(input_path).exists():
        raise ValidationError(f"Input file does not exist: {input_path}")

    header_run = RunMetrics(action="inspect")

    with open(input_path, "rb") as f:
        header = read_header(f)
        header_run.original_size = header["orig_size"]

        for chunk_index in range(1, header["chunk_count"] + 1):
            chunk = parse_chunk_from_file(f)
            mode_name = MODE_NAMES.get(chunk["mode"], "unknown")
            header_run.chunk_mode_counts[mode_name] = header_run.chunk_mode_counts.get(mode_name, 0) + 1
            header_run.chunk_count += 1

            item = ChunkMetrics(
                index=chunk_index,
                mode=mode_name,
                original_size=chunk["orig_size"],
                logical_size=chunk["logical_size"],
                payload_size=len(chunk["payload"]),
                chunk_body_size=chunk["decompressed_body_len"],
                final_chunk_size=chunk["body_len"] + 26,
                template_count=len(chunk["templates"]),
                value_dict_count=len(chunk["value_dict"]),
                token_dict_count=len(chunk["token_to_pattern"]),
                record_count=chunk["record_count"],
            )
            item.total_saved = max(0, item.original_size - item.final_chunk_size)
            header_run.chunks.append(item)

    print(f"Container file:        {input_path}")
    print(f"Original size:         {header['orig_size']} bytes")
    print(f"Stored chunks:         {header_run.chunk_count}")
    print(f"Chunk bytes target:    {header['chunk_bytes']}")
    print(f"Mode counts:           {header_run.chunk_mode_counts}")
    print_chunk_table(header_run, top=top)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Version 10 hardened .rzzip compressor",
        epilog=(
            "Examples:\n"
            "  python3 main.py compress app.log archive.rzzip --backend gzip --progress\n"
            "  python3 main.py decompress archive.rzzip restored.log --progress\n"
            "  python3 main.py inspect archive.rzzip --top 20"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    c = sub.add_parser("compress", help="Compress a supported text/log file into an .rzzip archive")
    c.add_argument("input_file")
    c.add_argument("output_file")
    c.add_argument("--mode", choices=["auto", "raw", "template"], default="auto")
    c.add_argument("--resource-profile", choices=["fast", "balanced", "deep"], default="balanced")
    c.add_argument("--chunk-bytes", type=int)
    c.add_argument("--min-len", type=int)
    c.add_argument("--max-len", type=int)
    c.add_argument("--top-patterns", type=int)
    c.add_argument("--rescore-limit", type=int, help="Use 0 for all candidates")
    c.add_argument("--min-template-hits", type=int)
    c.add_argument("--min-value-hits", type=int)
    c.add_argument("--backend", choices=["none", "gzip", "zlib"], default="gzip")
    c.add_argument("--backend-level", type=int, default=9)
    c.add_argument("--progress", action="store_true")
    c.add_argument("--no-checksum", action="store_true")
    c.add_argument("--report-chunks", action="store_true")

    d = sub.add_parser("decompress", help="Decompress an .rzzip archive back to text")
    d.add_argument("input_file")
    d.add_argument("output_file")
    d.add_argument("--no-verify", action="store_true")
    d.add_argument("--progress", action="store_true")

    i = sub.add_parser("inspect", help="Inspect archive structure and chunk summary")
    i.add_argument("input_file")
    i.add_argument("--top", type=int, default=10)

    return parser


def run_from_args(args: argparse.Namespace) -> None:
    if args.command == "compress":
        metrics = compress_file(args.input_file, args.output_file, args)
        print_compress_report(metrics)
        if args.report_chunks:
            print_chunk_table(metrics, top=len(metrics.chunks))
    elif args.command == "decompress":
        metrics = decompress_file(
            args.input_file,
            args.output_file,
            verify_checksum=not args.no_verify,
            progress=args.progress,
        )
        print_decompress_report(metrics)
    elif args.command == "inspect":
        inspect_file(args.input_file, top=args.top)