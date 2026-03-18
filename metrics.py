from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter


@dataclass
class ChunkMetrics:
    index: int
    mode: str
    original_size: int

    template_input_size: int = 0
    logical_size: int = 0
    payload_size: int = 0
    chunk_body_size: int = 0
    final_chunk_size: int = 0

    template_count: int = 0
    value_dict_count: int = 0
    token_dict_count: int = 0
    record_count: int = 0

    template_bytes: int = 0
    value_dict_bytes: int = 0
    token_dict_bytes: int = 0

    template_stage_saved: int = 0
    token_stage_saved: int = 0
    backend_stage_saved: int = 0
    total_saved: int = 0


@dataclass
class RunMetrics:
    action: str

    start_time: float = field(default_factory=perf_counter)
    end_time: float = 0.0

    original_size: int = 0
    compressed_size: int = 0
    restored_size: int = 0

    chunk_count: int = 0
    chunk_mode_counts: dict[str, int] = field(default_factory=dict)

    template_count: int = 0
    value_dict_count: int = 0
    token_dict_count: int = 0

    template_bytes: int = 0
    value_dict_bytes: int = 0
    token_dict_bytes: int = 0

    template_stage_saved: int = 0
    token_stage_saved: int = 0
    backend_stage_saved: int = 0
    total_saved: int = 0

    checksum_valid: bool | None = None
    chunks: list[ChunkMetrics] = field(default_factory=list)

    def stop(self) -> None:
        self.end_time = perf_counter()

    @property
    def elapsed_seconds(self) -> float:
        if self.end_time == 0.0:
            return perf_counter() - self.start_time
        return self.end_time - self.start_time

    @property
    def compression_ratio(self) -> float:
        if self.original_size == 0:
            return 1.0
        if self.compressed_size:
            return self.compressed_size / self.original_size
        if self.restored_size:
            return self.restored_size / self.original_size
        return 1.0

    @property
    def percent_saved(self) -> float:
        if self.original_size == 0:
            return 0.0
        if self.compressed_size:
            return 100.0 * (self.original_size - self.compressed_size) / self.original_size
        return 0.0