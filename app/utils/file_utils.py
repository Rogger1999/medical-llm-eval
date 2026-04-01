"""File system utility helpers."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator, Optional


def ensure_dir(path: str | Path) -> Path:
    """Create directory (and parents) if it does not exist. Return Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_write(path: str | Path, content: str | bytes) -> Path:
    """Write content to path, creating parent dirs as needed."""
    p = Path(path)
    ensure_dir(p.parent)
    mode = "wb" if isinstance(content, bytes) else "w"
    encoding = None if isinstance(content, bytes) else "utf-8"
    with open(p, mode, encoding=encoding) as f:
        f.write(content)
    return p


def safe_read(path: str | Path, binary: bool = False) -> Optional[str | bytes]:
    """Read and return file content, or None if file does not exist."""
    p = Path(path)
    if not p.exists():
        return None
    mode = "rb" if binary else "r"
    encoding = None if binary else "utf-8"
    with open(p, mode, encoding=encoding) as f:
        return f.read()


def list_files(directory: str | Path, extension: Optional[str] = None) -> list[Path]:
    """List files in directory, optionally filtered by extension."""
    d = Path(directory)
    if not d.exists():
        return []
    files: list[Path] = []
    for entry in d.iterdir():
        if entry.is_file():
            if extension is None or entry.suffix.lower() == extension.lower():
                files.append(entry)
    return sorted(files)


def file_size_bytes(path: str | Path) -> int:
    """Return file size in bytes, or 0 if not found."""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0
