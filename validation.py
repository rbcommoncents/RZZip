from __future__ import annotations

from pathlib import Path

from constants import DEFAULT_ALLOWED_INPUT_SUFFIXES, DEFAULT_ARCHIVE_SUFFIX
from errors import ValidationError


def ensure_input_exists(path: str) -> Path:
    p = Path(path)
    if not p.exists():
        raise ValidationError(f"Input file does not exist: {path}")
    if not p.is_file():
        raise ValidationError(f"Input path is not a file: {path}")
    return p


def ensure_input_suffix(path: str, allowed_suffixes: set[str] | None = None) -> Path:
    p = Path(path)
    allowed = allowed_suffixes or DEFAULT_ALLOWED_INPUT_SUFFIXES
    if p.suffix and p.suffix.lower() not in allowed:
        raise ValidationError(
            f"Unsupported input file type: {p.suffix}. "
            f"Allowed types: {', '.join(sorted(allowed))}"
        )
    return p


def ensure_archive_suffix(path: str) -> Path:
    p = Path(path)
    if p.suffix.lower() != DEFAULT_ARCHIVE_SUFFIX:
        raise ValidationError(
            f"Archive output must use {DEFAULT_ARCHIVE_SUFFIX} extension: {path}"
        )
    return p


def ensure_parent_dir_writable(path: str) -> Path:
    p = Path(path)
    parent = p.parent if p.parent != Path("") else Path(".")
    if not parent.exists():
        raise ValidationError(f"Output directory does not exist: {parent}")
    if not parent.is_dir():
        raise ValidationError(f"Output parent is not a directory: {parent}")
    return p


def validate_compress_paths(input_path: str, output_path: str) -> tuple[Path, Path]:
    in_path = ensure_input_exists(input_path)
    ensure_input_suffix(input_path)
    out_path = ensure_archive_suffix(output_path)
    ensure_parent_dir_writable(output_path)
    if in_path.resolve() == out_path.resolve():
        raise ValidationError("Input and output paths must be different")
    return in_path, out_path


def validate_decompress_paths(input_path: str, output_path: str) -> tuple[Path, Path]:
    in_path = ensure_input_exists(input_path)
    if in_path.suffix.lower() != DEFAULT_ARCHIVE_SUFFIX:
        raise ValidationError(f"Input archive must be a {DEFAULT_ARCHIVE_SUFFIX} file")
    out_path = Path(output_path)
    ensure_parent_dir_writable(output_path)
    if in_path.resolve() == out_path.resolve():
        raise ValidationError("Input and output paths must be different")
    return in_path, out_path