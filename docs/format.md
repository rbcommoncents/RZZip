# RZZip Format

## Overview

RZZip is a chunked, multi-stage archive format for structured text and log data.

The format is designed to preserve exact content while improving compression by combining:

1. structural normalization
2. repeated phrase/token substitution
3. compact binary chunk storage
4. final backend compression

The archive extension used by the project is:

```text
.rzzip
```

---

## Design Goals

The RZZip format was built to support:

- exact decompression
- structured log awareness
- chunk-based storage
- versioned containers
- explainable compression stages
- backend compression as a final layer

---

## High-Level Compression Pipeline

The compression pipeline works in stages:

1. Read text input in chunks
2. Detect repeated structure
3. Convert repeated lines into templates when beneficial
4. Build token dictionaries for repeated patterns
5. Serialize chunk metadata and payload into a compact binary body
6. Apply backend compression to the chunk body
7. Store all chunks inside a versioned container

---

## Container Header

Each archive begins with a fixed-size container header.

### Header fields

- magic bytes
- major version
- minor version
- flags
- chunk target size
- chunk count
- original input size
- checksum

### Purpose

The container header allows the decoder to verify:

- this is an RZZip archive
- the archive version is supported
- the expected original size is known
- the checksum can be validated after decompression

---

## Chunk Model

The archive stores data as a sequence of chunks.

Each chunk contains:

- chunk mode
- backend type
- original chunk size
- logical size
- template count
- value dictionary count
- token dictionary count
- record count
- compressed body length
- compressed body bytes

---

## Chunk Modes

### Raw Mode

Raw mode stores the chunk payload directly as text-oriented bytes, then applies token substitution if beneficial.

Use case:

- chunks that do not benefit enough from template normalization
- less structured or more irregular input

### Template Mode

Template mode converts repeated line structures into templates with extracted values.

Use case:

- repeated application log lines
- repeated service messages
- repeated structured text patterns

---

## Template Records

In template mode, each line becomes either:

- a raw record
- or a template record

### Raw Record

A raw record stores the full line directly.

### Template Record

A template record stores:

- template id
- newline marker
- value count
- values or dictionary references

This allows repeated line structures to be stored once while variable fields are stored separately.

---

## Value Dictionary

If certain extracted values repeat often enough, they may be placed into a value dictionary for the chunk.

Instead of storing the same value repeatedly, records can reference the dictionary entry by id.

This reduces repeated cost for common values such as:

- usernames
- service names
- response codes
- paths
- repeated identifiers

---

## Token Dictionary

After raw or template payload generation, RZZip performs repeated pattern analysis and may build a token dictionary.

The token dictionary maps:

- one-byte token id
- to repeated byte pattern

The payload is then rewritten so repeated byte sequences are replaced by token references.

This is the second major structural reduction stage.

---

## Backend Compression

Once the chunk body has been serialized, RZZip applies an optional backend compressor.

Supported backends include:

- none
- gzip
- zlib

The backend stage is deliberately applied last so it can exploit repetition created by earlier normalization steps.

---

## Checksums

RZZip supports optional checksum validation.

If enabled, the archive stores a SHA-256 checksum of the original input stream.

During decompression, the restored content is hashed and compared against the stored checksum.

This provides strong confidence that the archive:

- was not corrupted
- was fully restored
- roundtripped correctly

---

## Versioning

RZZip uses explicit major and minor version fields.

### Major Version

Major version changes indicate format compatibility boundaries.

### Minor Version

Minor version changes indicate smaller format or behavior evolution within the same major generation.

A decoder should reject unsupported major versions rather than attempting unsafe recovery.

---

## Why This Format Exists

RZZip is not just a generic compression wrapper.

It exists to make compression of structured logs:

- more explainable
- more measurable
- more inspectable
- often more efficient than plain backend compression alone

The format is especially useful when the input contains strong repetition in structure and wording.