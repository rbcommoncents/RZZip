from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sample_log_text() -> str:
    return (
        "2026-01-01 10:00:00 service=auth user=alice code=200 path=/login ip=10.0.0.1 host-1\n"
        "2026-01-01 10:00:01 service=auth user=bob code=200 path=/login ip=10.0.0.2 host-2\n"
        "2026-01-01 10:00:02 service=auth user=alice code=500 path=/login ip=10.0.0.1 host-1\n"
        "2026-01-01 10:00:03 service=auth user=bob code=200 path=/logout ip=10.0.0.2 host-2\n"
    )


@pytest.fixture
def sample_log_file(tmp_path: Path, sample_log_text: str) -> Path:
    p = tmp_path / "sample.log"
    p.write_text(sample_log_text, encoding="utf-8")
    return p


@pytest.fixture
def archive_file(tmp_path: Path) -> Path:
    return tmp_path / "sample.rzzip"


@pytest.fixture
def restored_file(tmp_path: Path) -> Path:
    return tmp_path / "restored.log"