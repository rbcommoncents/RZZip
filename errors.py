from __future__ import annotations


class RZLogError(Exception):
    """Base exception for the rzlog tool."""


class FormatError(RZLogError):
    """Raised when the archive/container format is invalid."""


class VersionError(RZLogError):
    """Raised when archive version is unsupported."""


class ValidationError(RZLogError):
    """Raised when input validation fails."""


class CorruptArchiveError(RZLogError):
    """Raised when an archive is truncated or corrupted."""


class ChecksumMismatchError(RZLogError):
    """Raised when checksum verification fails."""


class UnsupportedModeError(RZLogError):
    """Raised when an unknown chunk or compression mode is encountered."""