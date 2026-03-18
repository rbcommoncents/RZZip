from __future__ import annotations

import argparse
import csv
import gzip
import sys
import time
import zlib
from pathlib import Path

# Allow running from the bench/ folder without packaging the project.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cli import build_parser, compress_file, decompress_file  # noqa: E402


def plain_gzip_compress(data: bytes, level: int) -> bytes:
    return gzip.compress(data, compresslevel=level)


def plain_gzip_decompress(data: bytes) -> bytes:
    return gzip.decompress(data)


def plain_zlib_compress(data: bytes, level: int) -> bytes:
    return zlib.compress(data, level)


def plain_zlib_decompress(data: bytes) -> bytes:
    return zlib.decompress(data)


def pct_saved(original_size: int, compressed_size: int) -> float:
    if original_size == 0:
        return 0.0
    return 100.0 * (original_size - compressed_size) / original_size


def bench_plain(
    method: str,
    input_path: Path,
    output_dir: Path,
    level: int,
) -> dict:
    data = input_path.read_bytes()
    original_size = len(data)

    if method == "plain_gzip":
        out_path = output_dir / f"{input_path.stem}.plain.gz"
        t0 = time.perf_counter()
        comp = plain_gzip_compress(data, level)
        comp_sec = time.perf_counter() - t0

        out_path.write_bytes(comp)

        t1 = time.perf_counter()
        restored = plain_gzip_decompress(comp)
        decomp_sec = time.perf_counter() - t1
    elif method == "plain_zlib":
        out_path = output_dir / f"{input_path.stem}.plain.zlib"
        t0 = time.perf_counter()
        comp = plain_zlib_compress(data, level)
        comp_sec = time.perf_counter() - t0

        out_path.write_bytes(comp)

        t1 = time.perf_counter()
        restored = plain_zlib_decompress(comp)
        decomp_sec = time.perf_counter() - t1
    else:
        raise ValueError(f"Unknown plain benchmark method: {method}")

    if restored != data:
        raise RuntimeError(f"Roundtrip mismatch for {method} on {input_path.name}")

    compressed_size = len(comp)

    return {
        "file": input_path.name,
        "method": method,
        "profile": "-",
        "backend": "-",
        "backend_level": level,
        "input_bytes": original_size,
        "output_bytes": compressed_size,
        "saved_pct": round(pct_saved(original_size, compressed_size), 2),
        "comp_sec": round(comp_sec, 6),
        "decomp_sec": round(decomp_sec, 6),
        "roundtrip_ok": True,
        "output_file": str(out_path),
    }


def bench_rzlog(
    input_path: Path,
    output_dir: Path,
    profile: str,
    backend: str,
    backend_level: int,
    mode: str,
) -> dict:
    archive_path = output_dir / f"{input_path.stem}.{profile}.{backend}.rzzip"
    restored_path = output_dir / f"{input_path.stem}.{profile}.{backend}.restored.log"

    parser = build_parser()
    compress_args = parser.parse_args(
        [
            "compress",
            str(input_path),
            str(archive_path),
            "--mode",
            mode,
            "--resource-profile",
            profile,
            "--backend",
            backend,
            "--backend-level",
            str(backend_level),
        ]
    )

    compress_metrics = compress_file(str(input_path), str(archive_path), compress_args)

    t0 = time.perf_counter()
    decompress_metrics = decompress_file(
        str(archive_path),
        str(restored_path),
        verify_checksum=True,
        progress=False,
    )
    decomp_sec = time.perf_counter() - t0

    original = input_path.read_bytes()
    restored = restored_path.read_bytes()
    roundtrip_ok = original == restored and (decompress_metrics.checksum_valid is True)

    if not roundtrip_ok:
        raise RuntimeError(
            f"Roundtrip mismatch for rzlog ({profile}, {backend}) on {input_path.name}"
        )

    return {
        "file": input_path.name,
        "method": f"rzlog_{backend}",
        "profile": profile,
        "backend": backend,
        "backend_level": backend_level,
        "input_bytes": compress_metrics.original_size,
        "output_bytes": compress_metrics.compressed_size,
        "saved_pct": round(compress_metrics.percent_saved, 2),
        "comp_sec": round(compress_metrics.elapsed_seconds, 6),
        "decomp_sec": round(decomp_sec, 6),
        "roundtrip_ok": roundtrip_ok,
        "output_file": str(archive_path),
    }


def print_results_table(rows: list[dict]) -> None:
    headers = [
        "file",
        "method",
        "profile",
        "backend_level",
        "input_bytes",
        "output_bytes",
        "saved_pct",
        "comp_sec",
        "decomp_sec",
        "roundtrip_ok",
    ]

    widths = {h: len(h) for h in headers}
    for row in rows:
        for h in headers:
            widths[h] = max(widths[h], len(str(row[h])))

    header_line = " | ".join(f"{h:<{widths[h]}}" for h in headers)
    sep_line = "-+-".join("-" * widths[h] for h in headers)

    print(header_line)
    print(sep_line)
    for row in rows:
        print(" | ".join(f"{str(row[h]):<{widths[h]}}" for h in headers))


def write_csv(rows: list[dict], csv_path: Path) -> None:
    if not rows:
        return
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark RZLog against plain gzip and zlib."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="One or more input files to benchmark.",
    )
    parser.add_argument(
        "--output-dir",
        default="bench/out",
        help="Directory for benchmark artifacts.",
    )
    parser.add_argument(
        "--profiles",
        nargs="+",
        default=["fast", "balanced", "deep"],
        choices=["fast", "balanced", "deep"],
        help="RZLog resource profiles to benchmark.",
    )
    parser.add_argument(
        "--backends",
        nargs="+",
        default=["none", "gzip", "zlib"],
        choices=["none", "gzip", "zlib"],
        help="RZLog backends to benchmark.",
    )
    parser.add_argument(
        "--backend-level",
        type=int,
        default=9,
        help="Backend compression level for gzip/zlib.",
    )
    parser.add_argument(
        "--plain-level",
        type=int,
        default=9,
        help="Compression level for plain gzip/zlib comparison.",
    )
    parser.add_argument(
        "--mode",
        default="auto",
        choices=["auto", "raw", "template"],
        help="RZLog mode to benchmark.",
    )
    parser.add_argument(
        "--csv",
        default="bench/out/benchmark_results.csv",
        help="CSV output path.",
    )
    parser.add_argument(
        "--skip-plain",
        action="store_true",
        help="Skip plain gzip/zlib comparisons.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []

    for input_name in args.inputs:
        input_path = Path(input_name)
        if not input_path.exists() or not input_path.is_file():
            print(f"Skipping invalid input: {input_name}", file=sys.stderr)
            continue

        print(f"\n=== Benchmarking {input_path.name} ===")

        if not args.skip_plain:
            for method in ("plain_gzip", "plain_zlib"):
                row = bench_plain(
                    method=method,
                    input_path=input_path,
                    output_dir=output_dir,
                    level=args.plain_level,
                )
                rows.append(row)

        for profile in args.profiles:
            for backend in args.backends:
                row = bench_rzlog(
                    input_path=input_path,
                    output_dir=output_dir,
                    profile=profile,
                    backend=backend,
                    backend_level=args.backend_level,
                    mode=args.mode,
                )
                rows.append(row)

    if not rows:
        print("No benchmark results generated.", file=sys.stderr)
        return 1

    print("\n=== Results ===")
    print_results_table(rows)

    csv_path = Path(args.csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(rows, csv_path)
    print(f"\nCSV written to: {csv_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())