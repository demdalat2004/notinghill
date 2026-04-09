"""
NotingHill — profiling/profile_pipeline.py
==========================================
Standalone profiling harness. Measures every stage of the pipeline
with realistic synthetic data scaled to 500K-file scenarios.

Usage (from backend/ directory):
    python -m profiling.profile_pipeline
    python -m profiling.profile_pipeline --real-dir "C:/Users/you/Documents"
"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
import re
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

# ── colour helpers ─────────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD  = "\033[1m"
RED   = "\033[31m"
YEL   = "\033[33m"
GRN   = "\033[32m"
CYN   = "\033[36m"


def _col(c, s): return f"{c}{s}{RESET}"
def _bar(frac, width=30):
    filled = int(frac * width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def _rating(ms_per_item):
    if ms_per_item < 1:   return _col(GRN, "FAST  ✓")
    if ms_per_item < 10:  return _col(YEL, "OK    ~")
    return                       _col(RED, "SLOW  ✗")


# ── timing helper ──────────────────────────────────────────────────────────
class Timer:
    def __init__(self):
        self._t = time.perf_counter()

    def elapsed(self) -> float:
        return time.perf_counter() - self._t

    def reset(self):
        self._t = time.perf_counter()


# ══════════════════════════════════════════════════════════════════════════
# 1. HASH BENCHMARKS
# ══════════════════════════════════════════════════════════════════════════

def bench_sha256(n: int = 1000, size_kb: int = 512) -> dict:
    """Benchmark SHA-256 on in-memory data (simulates file reads)."""
    data = os.urandom(size_kb * 1024)
    t = Timer()
    for _ in range(n):
        hashlib.sha256(data).hexdigest()
    elapsed = t.elapsed()
    return {"n": n, "size_kb": size_kb, "total_s": elapsed,
            "ms_per_item": elapsed / n * 1000, "items_per_s": n / elapsed}


def bench_simhash(n: int = 1000) -> dict:
    """Benchmark 64-bit simhash on synthetic text."""
    import random, string
    words = ["".join(random.choices(string.ascii_lowercase, k=random.randint(3,10)))
             for _ in range(200)]
    texts = [" ".join(random.choices(words, k=random.randint(50, 500))) for _ in range(n)]

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app.services.signatures.simhash_service import compute_simhash

    t = Timer()
    for txt in texts:
        compute_simhash(txt)
    elapsed = t.elapsed()
    return {"n": n, "total_s": elapsed,
            "ms_per_item": elapsed / n * 1000, "items_per_s": n / elapsed}


def bench_phash_pure(n: int = 100) -> dict:
    """Benchmark the pure-Python DCT phash (worst case: no numpy)."""
    try:
        from PIL import Image
    except ImportError:
        return {"error": "Pillow not installed"}

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app.services.signatures.phash_service import compute_phash

    # Create synthetic images
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for i in range(n):
            img = Image.new("RGB", (200, 200), color=(i % 255, (i * 3) % 255, 50))
            p = Path(d) / f"img_{i}.jpg"
            img.save(str(p))
            paths.append(p)

        t = Timer()
        for p in paths:
            compute_phash(p)
        elapsed = t.elapsed()

    return {"n": n, "total_s": elapsed,
            "ms_per_item": elapsed / n * 1000, "items_per_s": n / elapsed}


# ══════════════════════════════════════════════════════════════════════════
# 2. SIMHASH CLUSTERING (O(n²)) — extrapolation
# ══════════════════════════════════════════════════════════════════════════

def bench_simhash_cluster_onion(sizes=(500, 2000, 5000)) -> dict:
    """
    Measure actual O(n²) dedup clustering at several sizes,
    then extrapolate to 500K.
    """
    import random
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app.services.signatures.simhash_service import similarity

    results = {}
    for n in sizes:
        hashes = [format(random.getrandbits(64), '016x') for _ in range(n)]
        items  = list(enumerate(hashes))

        t = Timer()
        visited = set()
        for i, (id_a, h_a) in enumerate(items):
            if id_a in visited:
                continue
            group = [id_a]
            for id_b, h_b in items[i+1:]:
                if id_b in visited:
                    continue
                if similarity(h_a, h_b) >= 0.90:
                    group.append(id_b)
                    visited.add(id_b)
            if len(group) > 1:
                visited.add(id_a)
        elapsed = t.elapsed()

        ops = n * (n - 1) / 2
        results[n] = {"elapsed_s": elapsed, "comparisons": ops,
                      "ns_per_cmp": elapsed / ops * 1e9}

    # Extrapolate to 500K
    if len(sizes) >= 2:
        n1, n2 = sizes[-2], sizes[-1]
        r1, r2 = results[n1]["elapsed_s"], results[n2]["elapsed_s"]
        # O(n²) → time ∝ n²
        predicted_500k = r2 * (500_000 / n2) ** 2
    else:
        ns_per = results[sizes[-1]]["ns_per_cmp"]
        predicted_500k = (500_000 ** 2 / 2) * ns_per / 1e9

    results["predicted_500k_hours"] = predicted_500k / 3600
    return results


# ══════════════════════════════════════════════════════════════════════════
# 3. SQLITE WRITE BENCHMARKS
# ══════════════════════════════════════════════════════════════════════════

_ITEM_SQL = """
INSERT INTO items (
    root_id, full_path, parent_path, file_name, extension, mime_type,
    size_bytes, created_ts, modified_ts, accessed_ts,
    best_time_ts, best_time_source, best_time_confidence,
    sha256, simhash64, phash,
    file_type_group, content_status, metadata_status, indexing_status,
    is_deleted, is_hidden, is_system,
    first_seen_ts, last_seen_ts, last_indexed_ts, change_token
) VALUES (
    ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
) ON CONFLICT(full_path) DO UPDATE SET
    size_bytes=excluded.size_bytes,
    modified_ts=excluded.modified_ts,
    last_seen_ts=excluded.last_seen_ts,
    change_token=excluded.change_token,
    is_deleted=0
"""


def _make_row(i: int):
    now = int(time.time())
    return (
        1, f"/fake/path/file_{i}.txt", "/fake/path", f"file_{i}.txt", ".txt", "text/plain",
        1024 * i, now, now, now, now, "mtime", 0.8,
        format(i, '064x'), format(i % (2**64), '016x'), None,
        "text", "done", "done", "done",
        0, 0, 0, now, now, now, f"{1024*i}:{now}",
    )


def bench_sqlite_writes(n: int = 2000) -> dict:
    """Compare: one-by-one commit vs batch (executemany, one commit)."""
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "bench.db"

        def _init(con):
            con.executescript("""
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=NORMAL;
                PRAGMA cache_size=-65536;
                PRAGMA mmap_size=268435456;
                PRAGMA temp_store=MEMORY;
                CREATE TABLE IF NOT EXISTS items (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    root_id INTEGER, full_path TEXT UNIQUE, parent_path TEXT,
                    file_name TEXT, extension TEXT, mime_type TEXT,
                    size_bytes INTEGER, created_ts INTEGER, modified_ts INTEGER,
                    accessed_ts INTEGER, best_time_ts INTEGER, best_time_source TEXT,
                    best_time_confidence REAL, sha256 TEXT, simhash64 TEXT, phash TEXT,
                    file_type_group TEXT, content_status TEXT, metadata_status TEXT,
                    indexing_status TEXT, is_deleted INTEGER DEFAULT 0,
                    is_hidden INTEGER DEFAULT 0, is_system INTEGER DEFAULT 0,
                    first_seen_ts INTEGER, last_seen_ts INTEGER, last_indexed_ts INTEGER,
                    change_token TEXT
                );
            """)
            con.commit()

        # Mode A: one commit per row (current approach when using get_db() per call)
        con_a = sqlite3.connect(str(db_path))
        _init(con_a)
        t = Timer()
        for i in range(n):
            con_a.execute(_ITEM_SQL, _make_row(i))
            con_a.commit()
        time_single = t.elapsed()
        con_a.close()

        # Mode B: one transaction, executemany
        db_path2 = Path(d) / "bench2.db"
        con_b = sqlite3.connect(str(db_path2))
        _init(con_b)
        rows = [_make_row(n + i) for i in range(n)]
        t.reset()
        con_b.executemany(_ITEM_SQL, rows)
        con_b.commit()
        time_batch = t.elapsed()
        con_b.close()

    speedup = time_single / time_batch if time_batch > 0 else 0
    return {
        "n": n,
        "single_commit_s": time_single,
        "batch_commit_s": time_batch,
        "speedup_x": speedup,
        "single_ms_per_row": time_single / n * 1000,
        "batch_ms_per_row": time_batch / n * 1000,
    }


# ══════════════════════════════════════════════════════════════════════════
# 4. REAL FILE SCAN (optional)
# ══════════════════════════════════════════════════════════════════════════

def bench_real_scan(root: str, sample_n: int = 100) -> dict:
    """Walk directory and time stat() calls on first sample_n files."""
    root_path = Path(root)
    if not root_path.exists():
        return {"error": f"Path not found: {root}"}

    files_found = []
    t = Timer()
    for dirpath, dirnames, filenames in os.walk(root_path):
        # skip hidden/system dirs
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in
                       {"node_modules", "__pycache__", ".git", "$RECYCLE.BIN"}]
        for fname in filenames:
            fp = Path(dirpath) / fname
            try:
                s = fp.stat()
                files_found.append((str(fp), s.st_size, int(s.st_mtime)))
            except OSError:
                pass
            if len(files_found) >= sample_n:
                break
        if len(files_found) >= sample_n:
            break
    scan_elapsed = t.elapsed()

    # Estimate full-walk time for 500K files
    if files_found:
        ms_per_file = scan_elapsed / len(files_found) * 1000
        est_500k_min = ms_per_file * 500_000 / 1000 / 60
    else:
        ms_per_file = est_500k_min = 0

    return {
        "sampled": len(files_found),
        "scan_elapsed_s": scan_elapsed,
        "ms_per_file": ms_per_file,
        "est_500k_minutes": est_500k_min,
    }


# ══════════════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════════════

def _section(title: str):
    print(f"\n{BOLD}{CYN}{'─'*60}{RESET}")
    print(f"{BOLD}{CYN}  {title}{RESET}")
    print(f"{BOLD}{CYN}{'─'*60}{RESET}")


def _row(label, value, rating=None):
    r = f"  {rating}" if rating else ""
    print(f"  {label:<38} {BOLD}{value}{RESET}{r}")


def run(real_dir: str | None = None):
    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  NotingHill — Pipeline Profiler{RESET}")
    print(f"{BOLD}  Target scale: 500K files, mixed types{RESET}")
    print(f"{BOLD}{'═'*60}{RESET}")

    # ── 1. SHA-256 ────────────────────────────────────────────────────────
    _section("1. SHA-256 hashing  (512 KB files)")
    print("  Running...", end="\r")
    r = bench_sha256(n=500, size_kb=512)
    _row("Speed",     f"{r['items_per_s']:.0f} files/s", _rating(r['ms_per_item']))
    _row("ms / file", f"{r['ms_per_item']:.2f} ms")
    _row("Est. 500K files", f"{500_000 / r['items_per_s'] / 60:.1f} minutes")

    # ── 2. Simhash ────────────────────────────────────────────────────────
    _section("2. SimHash computation  (text files)")
    print("  Running...", end="\r")
    r = bench_simhash(n=500)
    _row("Speed",     f"{r['items_per_s']:.0f} files/s", _rating(r['ms_per_item']))
    _row("ms / file", f"{r['ms_per_item']:.2f} ms")
    _row("Est. 500K text files", f"{500_000 / r['items_per_s'] / 60:.1f} minutes")

    # ── 3. pHash ─────────────────────────────────────────────────────────
    _section("3. pHash  (pure-Python DCT — worst case)")
    print("  Running 100 images...", end="\r")
    r = bench_phash_pure(n=100)
    if "error" in r:
        print(f"  {_col(RED, r['error'])}")
    else:
        _row("Speed",       f"{r['items_per_s']:.1f} images/s", _rating(r['ms_per_item']))
        _row("ms / image",  f"{r['ms_per_item']:.1f} ms")
        _row("Est. 100K images", f"{100_000 / r['items_per_s'] / 60:.1f} minutes")
        if r['ms_per_item'] > 50:
            print(f"  {_col(RED, '⚠  Pure-Python DCT is very slow → prime PyO3 candidate')}")

    # ── 4. Dedup clustering ───────────────────────────────────────────────
    _section("4. Dedup clustering  (current O(n²) simhash)")
    print("  Running n=500, 2000, 5000 ... (may take a moment)", end="\r")
    r = bench_simhash_cluster_onion(sizes=(500, 2000, 5000))
    for n, data in r.items():
        if n == "predicted_500k_hours":
            continue
        print(f"  n={n:<6}  {data['elapsed_s']:.3f}s   "
              f"({data['ns_per_cmp']:.1f} ns/cmp)")
    pred = r["predicted_500k_hours"]
    colour = RED if pred > 1 else YEL if pred > 0.1 else GRN
    _row("★ Predicted time @ 500K",
         f"{pred:.1f} hours" if pred > 1 else f"{pred*60:.1f} minutes",
         _col(colour, "← CRITICAL BOTTLENECK" if pred > 1 else "manageable"))

    # ── 5. SQLite write modes ─────────────────────────────────────────────
    _section("5. SQLite write modes  (items table upsert)")
    print("  Running 2000 rows each mode...", end="\r")
    r = bench_sqlite_writes(n=2000)
    _row("Single-commit (current)",
         f"{r['single_ms_per_row']:.2f} ms/row  ({r['single_commit_s']:.2f}s total)",
         _rating(r['single_ms_per_row']))
    _row("Batch executemany",
         f"{r['batch_ms_per_row']:.2f} ms/row  ({r['batch_commit_s']:.2f}s total)",
         _rating(r['batch_ms_per_row']))
    _row("Speedup", f"{r['speedup_x']:.1f}x faster with batch")

    # ── 6. Real dir scan ──────────────────────────────────────────────────
    if real_dir:
        _section(f"6. Real filesystem scan  ({real_dir})")
        r = bench_real_scan(real_dir, sample_n=200)
        if "error" in r:
            print(f"  {_col(RED, r['error'])}")
        else:
            _row("Files sampled",   str(r['sampled']))
            _row("ms / stat()",     f"{r['ms_per_file']:.3f} ms",
                 _rating(r['ms_per_file']))
            _row("Est. 500K files", f"{r['est_500k_minutes']:.1f} minutes")

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  SUMMARY — Priority order for optimization{RESET}")
    print(f"{'═'*60}")
    print(f"  {_col(RED,  '1. [CRITICAL] Dedup O(n²) → must replace with LSH')}")
    print(f"  {_col(RED,  '2. [HIGH]     pHash pure-Python DCT → PyO3 Rust ext')}")
    print(f"  {_col(YEL,  '3. [MED]      SimHash pure-Python → PyO3 or numpy')}")
    print(f"  {_col(YEL,  '4. [MED]      SQLite single-commits → batch writes')}")
    print(f"  {_col(GRN,  '5. [LOW]      SHA-256 (already fast enough)')}")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-dir", default=None,
                        help="Real directory to scan for filesystem bench")
    args = parser.parse_args()
    run(real_dir=args.real_dir)
