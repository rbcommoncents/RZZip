# RZZip

**RZZip** is a modular, multi-stage compression tool built for structured text and log data.

Instead of relying on backend compression alone, RZZip first analyzes repeated structure, repeated phrases, and repeated values, then emits a compact binary archive format and optionally applies a final backend compressor such as **gzip** or **zlib**.

The result is a project that is not only focused on compression ratio, but also on:

- explainability
- inspectability
- chunk-aware storage
- measurable stage-by-stage savings
- exact roundtrip recovery

---

## Why RZZip Exists

Generic compressors like `gzip` and `zlib` are strong general-purpose tools, but they do not understand log structure.

RZZip was built to test a different idea:

> If logs are repetitive in both **structure** and **content**, can a structure-aware front end produce a better stream for backend compression than generic compression alone?

On structured logs, the answer is often yes.

RZZip works especially well when the input contains:

- repeated log templates
- repeated field names
- repeated values
- repeated service messages
- repeated phrases and line patterns

---

## Core Architecture

RZZip uses a layered compression pipeline:

1. **Chunk input text**
2. **Normalize repeated structure**
3. **Convert repeated lines into templates when beneficial**
4. **Build token dictionaries for repeated phrases / byte patterns**
5. **Serialize compact chunk metadata and payload**
6. **Apply backend compression**
7. **Store as a versioned `.rzzip` archive**

This gives the project a strong balance between:

- custom compression logic
- modular design
- exact decompression
- measurable outcomes

---

## Features

- Lossless compression for structured text and log files
- Chunk-based archive format
- Template-aware normalization
- Token dictionary substitution
- Optional backend compression with:
  - `none`
  - `gzip`
  - `zlib`
- Archive inspection tools
- Compression / decompression timing
- Per-stage metrics and reporting
- Checksum validation
- Hardened input validation and corruption detection
- Modular testable codebase

---

## Project Layout

```text
rzzip/
├── main.py
├── constants.py
├── errors.py
├── binaryio.py
├── backend.py
├── validation.py
├── patterns.py
├── templates.py
├── chunks.py
├── container.py
├── metrics.py
├── report.py
├── cli.py
├── docs/
│   ├── usage.md
│   ├── format.md
│   └── benchmarks.md
├── tests/
│   ├── conftest.py
│   ├── test_binaryio.py
│   ├── test_backend.py
│   ├── test_validation.py
│   ├── test_patterns.py
│   ├── test_templates.py
│   ├── test_chunks.py
│   ├── test_container.py
│   ├── test_roundtrip.py
│   └── test_corruption.py
└── bench/
    └── benchmark.py
```

---

## Installation

RZZip is built in Python and uses the standard library only.

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/RZZip.git
cd RZZip
```

Check your Python version:

```bash
python3 --version
```

Recommended:

- Python 3.11+
- `pytest` for running tests

Install test dependency:

```bash
pip install pytest
```

---

## Quick Start

### Compress a log file

```bash
python3 main.py compress sample_app.log sample.rzzip --mode auto --backend gzip --resource-profile balanced --progress
```

### Inspect the archive

```bash
python3 main.py inspect sample.rzzip --top 20
```

### Decompress the archive

```bash
python3 main.py decompress sample.rzzip restored.log --progress
```

### Verify exact match

```bash
diff sample_app.log restored.log
```

If `diff` prints nothing, the roundtrip was exact.

---

## Compression Modes

### `auto`
Tries both raw and template modes per chunk and stores whichever is smaller.

### `raw`
Skips template normalization and applies token-pattern compression only.

### `template`
Attempts template normalization for repeated structured lines.

---

## Resource Profiles

### `fast`
Good for quick tests and lower CPU usage.

### `balanced`
Best default for normal use.

### `deep`
More aggressive analysis for highly repetitive logs, but slower.

---

## Backends

RZZip supports:

- `none`
- `gzip`
- `zlib`

Examples:

```bash
python3 main.py compress sample_app.log out.rzzip --backend none
python3 main.py compress sample_app.log out.rzzip --backend gzip
python3 main.py compress sample_app.log out.rzzip --backend zlib
```

---

## Example Metrics Output

A typical compression report looks like this:

```text
=== Compression Report ===
Original size:        1048576 bytes
Compressed size:      396288 bytes
Total bytes saved:    652288 bytes
Compression ratio:    0.3779
Percent saved:        62.21%
Chunks:               3
Chunk modes:          {'template': 3}
Templates kept:       97
Value dict entries:   241
Token dict entries:   119
Template bytes:       9122
Value dict bytes:     6033
Token dict bytes:     4817
Template stage saved: 246810 bytes (23.54%)
Token stage saved:    311405 bytes (29.70%)
Backend stage saved:  94176 bytes (8.98%)
Elapsed time:         0.4287s
```

This helps show **where compression wins actually come from**, not just the final size.

---

## Comparing Against Plain gzip / zlib

To test whether RZZip is actually improving over standard compression alone:

### Plain gzip

```bash
gzip -c sample_app.log > plain.gz
```

### Plain zlib

```bash
python3 -c "import zlib, pathlib; data=pathlib.Path('sample_app.log').read_bytes(); pathlib.Path('plain.zlib').write_bytes(zlib.compress(data, 9))"
```

### RZZip

```bash
python3 main.py compress sample_app.log sample.rzzip --backend gzip --resource-profile balanced
```

Then compare sizes:

```bash
wc -c sample_app.log sample.rzzip plain.gz plain.zlib
```

RZZip is most likely to outperform plain backend compression on:

- structured logs
- repeated service traces
- repeated auth events
- repeated system messages
- template-heavy text records

---

## Hardening / Production Readiness

Version 10 adds stronger reliability features, including:

- input file validation
- archive suffix checks
- custom exceptions
- version compatibility checks
- corruption detection
- checksum verification
- roundtrip tests
- backend tests
- validation tests
- chunk and container parsing tests

This makes the project stronger not only as a compression experiment, but as a portfolio-quality engineering project.

---

## Running Tests

Run the full test suite:

```bash
pytest -q
```

Run a single file:

```bash
pytest -q tests/test_roundtrip.py
```

Run a single test:

```bash
pytest -q tests/test_roundtrip.py::test_roundtrip_small_log
```

---

## Documentation

Additional documentation is available in the `docs/` directory:

- `docs/usage.md`
- `docs/format.md`
- `docs/benchmarks.md`

These cover:

- command usage
- format architecture
- benchmark interpretation
- comparison methodology

---

## What Makes This Project Interesting

RZZip is more than “yet another compression wrapper.”

It demonstrates:

- format design
- chunked container design
- multi-stage transformation pipelines
- backend integration
- metrics and observability
- defensive parsing
- exact roundtrip recovery
- modular Python architecture
- testability and benchmarking

It is a strong project for discussing:

- compression architecture
- systems design
- structured text optimization
- defensive engineering
- explainable tooling

---

## Future Ideas

Possible future directions include:

- JSON export for metrics
- CSV benchmark output
- side-by-side benchmark runner
- richer input format detection
- archive metadata subcommands
- lightweight UI for archive inspection
- additional backend compressors
- smarter candidate extraction strategies
- parallel chunk processing

---

## License

This project is licensed under the Apache License 2.0.
See the `LICENSE` file for details.

---

## Final Note

RZZip started as a compression experiment, but it grew into something more useful:

A modular, inspectable, explainable archive format for structured logs that can outperform plain backend compression in the right conditions.

That is the kind of engineering story worth shipping.

