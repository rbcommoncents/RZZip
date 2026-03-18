# Usage

## Overview

RZZip is a modular command-line tool for compressing structured text and log files into a custom `.rzzip` archive format.

It supports:

- multi-stage compression
- chunked storage
- template-aware log normalization
- backend compression with gzip or zlib
- decompression
- archive inspection
- metrics and reporting

---

## Basic Commands

### Compress a file

```bash
python3 main.py compress sample_app.log sample.rzzip
```

### Decompress an archive

```bash
python3 main.py decompress sample.rzzip restored.log
```

### Inspect an archive

```bash
python3 main.py inspect sample.rzzip
```

---

## Compression Examples

### Auto mode with gzip backend

```bash
python3 main.py compress sample_app.log sample.rzzip --mode auto --backend gzip
```

### Auto mode with zlib backend

```bash
python3 main.py compress sample_app.log sample.rzzip --mode auto --backend zlib
```

### Raw-only mode

```bash
python3 main.py compress sample_app.log sample.rzzip --mode raw
```

### Template-only mode

```bash
python3 main.py compress sample_app.log sample.rzzip --mode template
```

### No backend compression

```bash
python3 main.py compress sample_app.log sample.rzzip --backend none
```

---

## Resource Profiles

RZZip supports multiple resource profiles.

### Fast

```bash
python3 main.py compress sample_app.log sample.rzzip --resource-profile fast
```

Use when you want:

- quicker runs
- lower CPU cost
- simpler testing

### Balanced

```bash
python3 main.py compress sample_app.log sample.rzzip --resource-profile balanced
```

Use when you want:

- good compression
- reasonable runtime
- normal day-to-day use

### Deep

```bash
python3 main.py compress sample_app.log sample.rzzip --resource-profile deep
```

Use when you want:

- more aggressive analysis
- best results on highly repetitive structured logs
- benchmarking or deeper experiments

Note: deep mode may take significantly longer on larger inputs.

---

## Progress Output

Use `--progress` to show live status during compression or decompression.

### Compress with progress

```bash
python3 main.py compress sample_app.log sample.rzzip --progress
```

### Decompress with progress

```bash
python3 main.py decompress sample.rzzip restored.log --progress
```

---

## Detailed Chunk Reporting

Use `--report-chunks` to print chunk-level metrics after compression.

```bash
python3 main.py compress sample_app.log sample.rzzip --report-chunks
```

---

## Backend Compression Levels

You can tune backend compression level.

### gzip level 9

```bash
python3 main.py compress sample_app.log sample.rzzip --backend gzip --backend-level 9
```

### zlib level 6

```bash
python3 main.py compress sample_app.log sample.rzzip --backend zlib --backend-level 6
```

Higher levels usually reduce size more but increase runtime.

---

## Tuning Options

### Chunk size

```bash
python3 main.py compress sample_app.log sample.rzzip --chunk-bytes 65536
```

### Pattern length controls

```bash
python3 main.py compress sample_app.log sample.rzzip --min-len 4 --max-len 16
```

### Top pattern count

```bash
python3 main.py compress sample_app.log sample.rzzip --top-patterns 32
```

### Rescore limit

```bash
python3 main.py compress sample_app.log sample.rzzip --rescore-limit 200
```

Use `0` to request full rescoring, though this may be expensive on larger files.

---

## Checksum Behavior

By default, compression can store a checksum and decompression can verify it.

### Disable checksum during compression

```bash
python3 main.py compress sample_app.log sample.rzzip --no-checksum
```

### Skip checksum verification during decompression

```bash
python3 main.py decompress sample.rzzip restored.log --no-verify
```

---

## Typical Workflow

### Step 1: Compress

```bash
python3 main.py compress sample_app.log sample.rzzip --backend gzip --resource-profile balanced --progress
```

### Step 2: Inspect

```bash
python3 main.py inspect sample.rzzip --top 20
```

### Step 3: Decompress

```bash
python3 main.py decompress sample.rzzip restored.log --progress
```

### Step 4: Verify exact match

```bash
diff sample_app.log restored.log
```

If `diff` produces no output, the restored file matches exactly.

---

## Comparing Against Plain gzip or zlib

To compare RZZip against standard backend compression alone:

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

Then compare file sizes:

```bash
wc -c sample_app.log sample.rzzip plain.gz plain.zlib
```

---

## Common Errors

### Unsupported input file type

Your input file extension may not be supported by validation rules.

### Wrong archive suffix

Compression output should use the `.rzzip` extension.

### Checksum mismatch

The archive may be corrupted, partially written, or modified after creation.

### Unsupported version

The archive may have been produced by a different major format version than the current decoder supports.

### Slower-than-expected compression

Try:

- `--resource-profile balanced`
- lower `--backend-level`
- smaller `--chunk-bytes`
- lower `--rescore-limit`

---

## Recommended Starting Command

```bash
python3 main.py compress sample_app.log sample.rzzip --mode auto --backend gzip --resource-profile balanced --progress
```

This is the best general-purpose starting point for most structured log files.