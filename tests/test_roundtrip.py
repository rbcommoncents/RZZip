from __future__ import annotations

from pathlib import Path

from cli import build_parser, compress_file, decompress_file


def test_roundtrip_small_log(sample_log_file: Path, archive_file: Path, restored_file: Path) -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "compress",
            str(sample_log_file),
            str(archive_file),
            "--backend",
            "gzip",
            "--resource-profile",
            "fast",
        ]
    )
    metrics = compress_file(str(sample_log_file), str(archive_file), args)

    assert archive_file.exists()
    assert metrics.compressed_size > 0

    dec_metrics = decompress_file(str(archive_file), str(restored_file), verify_checksum=True)

    assert restored_file.read_text(encoding="utf-8") == sample_log_file.read_text(encoding="utf-8")
    assert dec_metrics.checksum_valid is True


def test_roundtrip_no_backend(sample_log_file: Path, archive_file: Path, restored_file: Path) -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "compress",
            str(sample_log_file),
            str(archive_file),
            "--backend",
            "none",
            "--resource-profile",
            "fast",
        ]
    )
    compress_file(str(sample_log_file), str(archive_file), args)
    decompress_file(str(archive_file), str(restored_file), verify_checksum=True)
    assert restored_file.read_text(encoding="utf-8") == sample_log_file.read_text(encoding="utf-8")


def test_roundtrip_raw_mode(sample_log_file: Path, archive_file: Path, restored_file: Path) -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "compress",
            str(sample_log_file),
            str(archive_file),
            "--mode",
            "raw",
            "--backend",
            "gzip",
            "--resource-profile",
            "fast",
        ]
    )
    compress_file(str(sample_log_file), str(archive_file), args)
    decompress_file(str(archive_file), str(restored_file), verify_checksum=True)
    assert restored_file.read_text(encoding="utf-8") == sample_log_file.read_text(encoding="utf-8")