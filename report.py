from __future__ import annotations

from metrics import RunMetrics


def pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return 100.0 * part / whole


def print_warnings(metrics: RunMetrics) -> None:
    if metrics.action == "compress" and metrics.compressed_size > metrics.original_size:
        print("Warning: compressed output is larger than original input.")


def print_compress_report(metrics: RunMetrics) -> None:
    print("\n=== Compression Report ===")
    print(f"Original size:        {metrics.original_size} bytes")
    print(f"Compressed size:      {metrics.compressed_size} bytes")
    print(f"Total bytes saved:    {metrics.original_size - metrics.compressed_size} bytes")
    print(f"Compression ratio:    {metrics.compression_ratio:.4f}")
    print(f"Percent saved:        {metrics.percent_saved:.2f}%")
    print(f"Chunks:               {metrics.chunk_count}")
    print(f"Chunk modes:          {metrics.chunk_mode_counts}")
    print(f"Templates kept:       {metrics.template_count}")
    print(f"Value dict entries:   {metrics.value_dict_count}")
    print(f"Token dict entries:   {metrics.token_dict_count}")
    print(f"Template bytes:       {metrics.template_bytes}")
    print(f"Value dict bytes:     {metrics.value_dict_bytes}")
    print(f"Token dict bytes:     {metrics.token_dict_bytes}")
    print(f"Template stage saved: {metrics.template_stage_saved} bytes ({pct(metrics.template_stage_saved, metrics.original_size):.2f}%)")
    print(f"Token stage saved:    {metrics.token_stage_saved} bytes ({pct(metrics.token_stage_saved, metrics.original_size):.2f}%)")
    print(f"Backend stage saved:  {metrics.backend_stage_saved} bytes ({pct(metrics.backend_stage_saved, metrics.original_size):.2f}%)")
    print(f"Elapsed time:         {metrics.elapsed_seconds:.4f}s")
    print_warnings(metrics)


def print_decompress_report(metrics: RunMetrics) -> None:
    print("\n=== Decompression Report ===")
    print(f"Restored size:        {metrics.restored_size} bytes")
    print(f"Original target size: {metrics.original_size} bytes")
    print(f"Chunks:               {metrics.chunk_count}")
    print(f"Checksum valid:       {metrics.checksum_valid}")
    print(f"Elapsed time:         {metrics.elapsed_seconds:.4f}s")


def print_chunk_table(metrics: RunMetrics, top: int = 10) -> None:
    print("\nChunk summary:")
    print(
        f"{'idx':>3} | {'mode':<8} | {'orig':>8} | {'logical':>8} | {'payload':>8} | "
        f"{'final':>8} | {'tmpl':>4} | {'vals':>4} | {'dict':>4} | {'saved':>8}"
    )
    print("----+----------+----------+----------+----------+----------+------+------+------+----------")
    for item in metrics.chunks[:top]:
        print(
            f"{item.index:>3} | {item.mode:<8} | {item.original_size:>8} | {item.logical_size:>8} | "
            f"{item.payload_size:>8} | {item.final_chunk_size:>8} | {item.template_count:>4} | "
            f"{item.value_dict_count:>4} | {item.token_dict_count:>4} | {item.total_saved:>8}"
        )