"""Atomic local records with optimistic concurrency and process locks."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path

from .errors import HarnessError, require

MAX_DOCUMENT_BYTES = 262144


def identifier(value: str) -> str:
    require(
        isinstance(value, str) and bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value)),
        "invalid_id",
        "Use a lowercase identifier with letters, digits, hyphens, or underscores.",
    )
    return value


def revision(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inside(root: Path, relative: str) -> Path:
    require(isinstance(relative, str), "invalid_path", "A record path must be a string.")
    path = Path(relative)
    require(
        not path.is_absolute() and ".." not in path.parts and path.parts and str(path) == relative,
        "invalid_path",
        "Use a canonical relative path without '..', './', or repeated separators.",
    )
    candidate = root / path
    cursor = candidate
    while cursor != root:
        require(
            not cursor.is_symlink(), "invalid_path", "Harness record paths cannot contain symlinks."
        )
        cursor = cursor.parent
    require(
        candidate.resolve().is_relative_to(root.resolve()),
        "invalid_path",
        "The path leaves the Harness root.",
    )
    return candidate


@contextlib.contextmanager
def locked(root: Path, key: str):
    directory = root / ".locks"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Filesystems may alias case or Unicode normalization. Serialize those aliases too.
    lock_key = unicodedata.normalize("NFC", key).casefold()
    path = directory / hashlib.sha256(lock_key.encode()).hexdigest()
    with path.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def atomic_write(path: Path, data: bytes, mode: int = 0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            os.fchmod(handle.fileno(), mode)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (ValueError, UnicodeError) as exc:
        raise HarnessError("invalid_json", f"Invalid JSON: {path.name}", str(exc)) from exc


def write_json(path: Path, value):
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def markdown(content: str) -> bytes:
    content = content.replace("\r\n", "\n").strip() + "\n"
    require(
        content.startswith("# ") and len(content.splitlines()[0]) > 2,
        "invalid_document",
        "A Markdown record must begin with a meaningful level-one title.",
    )
    data = content.encode()
    require(
        b"\x00" not in data and len(data) <= MAX_DOCUMENT_BYTES,
        "invalid_document",
        "A Markdown record must be UTF-8 text no larger than 256 KiB.",
    )
    return data


def put_document(root: Path, relative: str, content: str, expected: str | None):
    path = inside(root, relative)
    data = markdown(content)
    with locked(root, relative):
        current = revision(path.read_bytes()) if path.exists() else None
        require(
            current == expected,
            "conflict",
            "The record changed or already exists.",
            "Read its current revision before writing. Use --revision for an existing record.",
        )
        atomic_write(path, data)
    return {"path": relative, "revision": revision(data)}
