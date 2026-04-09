"""
NotingHill — core/time_utils.py
"""
import os
import stat
from pathlib import Path


def get_file_times(path: Path) -> dict:
    try:
        s = path.stat()
        ctime = int(s.st_ctime)
        mtime = int(s.st_mtime)
        atime = int(s.st_atime)
    except OSError:
        return {}

    # Best time heuristic:
    # Prefer ctime on Linux (inode change), mtime otherwise
    # If mtime < ctime, ctime might be copy time — trust mtime
    candidates = {}
    if ctime:
        candidates["ctime"] = ctime
    if mtime:
        candidates["mtime"] = mtime

    # Pick earliest reasonable timestamp as "original" time
    # Filter out obvious wrong timestamps (before 1990)
    MIN_TS = 631152000  # 1990-01-01
    valid = {k: v for k, v in candidates.items() if v > MIN_TS}

    if valid:
        best_key = min(valid, key=lambda k: valid[k])
        best_ts = valid[best_key]
    else:
        best_ts = mtime
        best_key = "mtime"

    return {
        "created_ts": ctime,
        "modified_ts": mtime,
        "accessed_ts": atime,
        "best_time_ts": best_ts,
        "best_time_source": best_key,
        "best_time_confidence": 0.7,
    }


def inject_metadata_time(times: dict, meta: dict) -> dict:
    """Override best_time with metadata-embedded time if available (e.g. EXIF taken_ts)."""
    taken = meta.get("taken_ts")
    MIN_TS = 631152000
    if taken and isinstance(taken, int) and taken > MIN_TS:
        times["best_time_ts"] = taken
        times["best_time_source"] = "exif"
        times["best_time_confidence"] = 0.95
    return times
