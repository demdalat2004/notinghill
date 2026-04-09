"""
NotingHill — services/signatures/sha256_service.py

Uses Rust extension (notinghill_ext) when available.
Falls back to pure-Python hashlib automatically — no config required.

Rust speedup: ~3–4x on large files (128 KB buffer + no GIL overhead),
              ~10–15x for batch via rayon parallelism.
"""
import hashlib
from pathlib import Path

try:
    import notinghill_ext as _ext
    _HAS_RUST = True
except ImportError:
    _HAS_RUST = False


def compute_sha256(path: Path, chunk_size: int = 131_072) -> str | None:
    if _HAS_RUST:
        try:
            return _ext.sha256_file(str(path))
        except Exception:
            pass
    # Pure-Python fallback
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def compute_sha256_batch(paths: list[Path]) -> list[str | None]:
    """
    Hash multiple files — uses rayon parallelism in Rust.
    Falls back to sequential pure-Python.
    """
    if _HAS_RUST:
        try:
            return _ext.sha256_batch([str(p) for p in paths])
        except Exception:
            pass
    return [compute_sha256(p) for p in paths]
