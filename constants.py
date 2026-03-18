from __future__ import annotations

MAGIC = b"RZLG"
VERSION_MAJOR = 10
VERSION_MINOR = 0

FLAG_CHECKSUM = 0x01

MODE_RAW = 0
MODE_TEMPLATE = 1
MODE_NAMES = {
    MODE_RAW: "raw",
    MODE_TEMPLATE: "template",
}

BACKEND_NONE = 0
BACKEND_GZIP = 1
BACKEND_ZLIB = 2

BACKEND_NAMES = {
    BACKEND_NONE: "none",
    BACKEND_GZIP: "gzip",
    BACKEND_ZLIB: "zlib",
}

RAW_RECORD = 0
TEMPLATE_RECORD = 1
RAW_VALUE = 0
REF_VALUE = 1

TEXT_MIN_TOKEN_LEN = 4
TEXT_MIN_PHRASE_CHARS = 8

HEADER_SIZE = 56
CHUNK_HEADER_SIZE = 26

DEFAULT_ALLOWED_INPUT_SUFFIXES = {
    ".log",
    ".txt",
    ".jsonl",
    ".csv",
}

DEFAULT_ARCHIVE_SUFFIX = ".rzzip"

PROFILE_DEFAULTS = {
    "fast": {
        "chunk_bytes": 32 * 1024,
        "min_len": 6,
        "max_len": 16,
        "top_patterns": 16,
        "rescore_limit": 75,
        "min_template_hits": 3,
        "min_value_hits": 3,
    },
    "balanced": {
        "chunk_bytes": 128 * 1024,
        "min_len": 6,
        "max_len": 24,
        "top_patterns": 32,
        "rescore_limit": 200,
        "min_template_hits": 2,
        "min_value_hits": 2,
    },
    "deep": {
        "chunk_bytes": 512 * 1024,
        "min_len": 6,
        "max_len": 32,
        "top_patterns": 64,
        "rescore_limit": 400,
        "min_template_hits": 2,
        "min_value_hits": 2,
    },
}