# Benchmarks

## Overview

RZZip is a multi-stage compression tool designed for structured and semi-structured text logs. Unlike plain backend compression alone, RZZip first reduces repeated structure through template normalization and repeated phrase/token substitution, then applies a backend compressor such as gzip or zlib.

The purpose of these benchmarks is to compare:

- Plain backend compression alone
- RZZip without backend compression
- RZZip with backend compression enabled

This helps answer a practical question:

**Does structure-aware compression outperform generic backend compression alone on real log-like data?**

---

## Benchmark Goals

The benchmark suite measures:

- Original size
- Final compressed size
- Compression ratio
- Percent saved
- Compression time
- Decompression time
- Exact roundtrip correctness

---

## Test Categories

RZZip should perform best on inputs with:

- Repeated log templates
- Repeated field names
- Repeated values
- Repeated phrases
- High structural consistency

Typical examples include:

- Application logs
- Security logs
- Authentication logs
- Service traces
- Structured text records

RZZip may perform less dramatically on:

- Very small files
- Highly random text
- Already compressed files
- Unstructured prose
- Binary media

---

## Example Benchmark Methods

The benchmark process compares the following methods:

1. Plain `gzip`
2. Plain `zlib`
3. RZZip with `--backend none`
4. RZZip with `--backend gzip`
5. RZZip with `--backend zlib`

---

## Example Commands

### Plain gzip

```bash
gzip -c sample_app.log > plain.gz
```

### Plain zlib

```bash
python3 -c "import zlib, pathlib; data=pathlib.Path('sample_app.log').read_bytes(); pathlib.Path('plain.zlib').write_bytes(zlib.compress(data, 9))"
```

### RZZip without backend

```bash
python3 main.py compress sample_app.log arch_none.rzzip --mode auto --backend none --resource-profile balanced
```

### RZZip with gzip backend

```bash
python3 main.py compress sample_app.log arch_gzip.rzzip --mode auto --backend gzip --backend-level 9 --resource-profile balanced
```

### RZZip with zlib backend

```bash
python3 main.py compress sample_app.log arch_zlib.rzzip --mode auto --backend zlib --backend-level 9 --resource-profile balanced
```

---

## Example Result Summary

Example benchmark output may look like this:

```text
method              size_bytes   saved_pct   comp_sec   decomp_sec
plain_gzip          421332       59.82       0.03       0.01
plain_zlib          418901       60.05       0.02       0.01
rzzip_none          503220       52.00       0.41       0.03
rzzip_gzip          389114       62.89       0.48       0.04
rzzip_zlib          384770       63.31       0.46       0.04
```

In this kind of result:

- Plain backend compression performs well on its own
- RZZip without backend compression shows meaningful structure reduction
- RZZip with backend compression performs best overall

That indicates the front-end normalization stages are creating a more compressible stream for the backend stage.

---

## How to Read the Results

### If RZZip + backend is smaller than plain gzip/zlib

That means the structure-aware pipeline is adding real value.

### If RZZip without backend is already much smaller than original

That means template normalization and token substitution are doing meaningful work.

### If plain gzip/zlib still wins

That usually means the input does not contain enough repeated structure to justify the added metadata and transform stages.

---

## Important Notes

RZZip is not intended to replace general-purpose compressors for every file type. Its purpose is to improve compression specifically for structured text and log-oriented inputs, while also offering:

- explainable compression stages
- chunk-aware inspection
- per-stage metrics
- stronger visibility into where savings come from

---

## Benchmark Conclusions

The strongest benchmark outcome for RZZip is not merely “smaller than gzip,” but:

- smaller than gzip on structured logs
- exact roundtrip integrity
- explainable stage-by-stage savings
- acceptable runtime for practical use

That combination makes RZZip useful both as a technical project and as a compression architecture demonstration.