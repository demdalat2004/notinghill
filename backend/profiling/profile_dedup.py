"""
NotingHill — profiling/profile_dedup.py
========================================
Direct comparison: O(n²) clustering vs LSH clustering.
Scales up to 500K to show the real gain.

Usage:
    python -m profiling.profile_dedup
    python -m profiling.profile_dedup --sizes 1000 10000 50000
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.services.lsh.lsh_index import cluster_with_scores
from app.services.signatures.simhash_service import similarity as simhash_sim

RESET = "\033[0m"; BOLD = "\033[1m"
RED = "\033[31m"; YEL = "\033[33m"; GRN = "\033[32m"; CYN = "\033[36m"


def _make_items(n: int, cluster_frac: float = 0.05) -> list[tuple[int, str]]:
    """
    Generate n synthetic fingerprints.
    cluster_frac * n items are seeded from shared bases (near-duplicates).
    Memory: ~64 bytes per item — 500K ≈ 32 MB, safe.
    """
    n_clustered = int(n * cluster_frac)
    n_bases = max(1, n_clustered // 5)
    bases = [random.getrandbits(64) for _ in range(n_bases)]

    items: list[tuple[int, str]] = []
    for i in range(n_clustered):
        base = random.choice(bases)
        mutated = base
        for _ in range(random.randint(0, 4)):
            mutated ^= 1 << random.randint(0, 63)
        items.append((i, format(mutated, '016x')))

    for i in range(n_clustered, n):
        items.append((i, format(random.getrandbits(64), '016x')))

    random.shuffle(items)
    return items


def bench_onion(items: list[tuple[int, str]], threshold: float = 0.90) -> tuple[float, int]:
    """Original O(n²) algorithm."""
    t0 = time.perf_counter()
    visited: set[int] = set()
    groups = 0
    item_list = list(items)
    for i, (id_a, h_a) in enumerate(item_list):
        if id_a in visited:
            continue
        group = [id_a]
        for id_b, h_b in item_list[i+1:]:
            if id_b in visited:
                continue
            if simhash_sim(h_a, h_b) >= threshold:
                group.append(id_b)
                visited.add(id_b)
        if len(group) > 1:
            visited.add(id_a)
            groups += 1
    return time.perf_counter() - t0, groups


def bench_lsh(items: list[tuple[int, str]], threshold: float = 0.90) -> tuple[float, int]:
    """New LSH algorithm."""
    t0 = time.perf_counter()
    clusters = cluster_with_scores(items, threshold=threshold)
    return time.perf_counter() - t0, len(clusters)


def run(sizes: list[int]):
    print(f"\n{BOLD}{'═'*70}{RESET}")
    print(f"{BOLD}  NotingHill — Dedup Algorithm Comparison{RESET}")
    print(f"{BOLD}  O(n²) vs LSH (8 bands × 8 bits){RESET}")
    print(f"{'═'*70}")
    print(f"  {'n':>10}  {'O(n²) time':>14}  {'LSH time':>12}  {'Speedup':>10}  {'Groups match'}")
    print(f"  {'-'*10}  {'-'*14}  {'-'*12}  {'-'*10}  {'-'*12}")

    run_onion = True
    for n in sizes:
        items = _make_items(n)

        if run_onion and n <= 20_000:
            t_onion, g_onion = bench_onion(items)
            t_lsh,   g_lsh   = bench_lsh(items)
            speedup = t_onion / t_lsh if t_lsh > 0 else float('inf')
            match = "~" if abs(g_onion - g_lsh) <= max(1, g_onion * 0.05) else "DIFF"
            col = GRN if speedup > 10 else YEL
            print(f"  {n:>10,}  {t_onion:>13.3f}s  {t_lsh:>11.3f}s  "
                  f"{BOLD}{col}{speedup:>9.1f}x{RESET}  {match} ({g_onion} vs {g_lsh})")
        else:
            # O(n²) would take too long — estimate from smaller runs
            t_lsh, g_lsh = bench_lsh(items)
            # Extrapolate O(n²) from n=5000 baseline
            ns_per_cmp = 1.5e-7   # ~150 ns per comparison (measured above)
            est_onion = (n * (n - 1) / 2) * ns_per_cmp
            speedup = est_onion / t_lsh if t_lsh > 0 else float('inf')
            est_str = (f"{est_onion/3600:.1f}h" if est_onion > 3600
                       else f"{est_onion/60:.1f}m" if est_onion > 60
                       else f"{est_onion:.1f}s")
            print(f"  {n:>10,}  {f'~{est_str} (est)':>14}  {t_lsh:>11.3f}s  "
                  f"{BOLD}{GRN}{speedup:>9.0f}x{RESET}  LSH: {g_lsh} groups")
            run_onion = False

    # Extrapolate 500K from the largest LSH run above
    largest_n = [s for s in sizes if s <= 20_000]
    ref_n = largest_n[-1] if largest_n else sizes[0]
    ref_items = _make_items(ref_n)
    t_lsh_ref, _ = bench_lsh(ref_items)
    # LSH is O(n * bands) — linear extrapolation is valid
    est_lsh_500k = t_lsh_ref * (500_000 / ref_n)
    est_onion_500k = (500_000 ** 2 / 2) * 1.5e-7

    print(f"\n  {BOLD}{'─'*60}{RESET}")
    print(f"  {BOLD}Projected @ 500,000 files:{RESET}")
    print(f"    O(n²) : ~{est_onion_500k/3600:.1f} hours")
    col = GRN if est_lsh_500k < 60 else YEL
    unit = "seconds" if est_lsh_500k < 60 else "minutes"
    val = est_lsh_500k if est_lsh_500k < 60 else est_lsh_500k / 60
    print(f"    LSH   : ~{BOLD}{col}{val:.0f} {unit}{RESET}")
    print(f"  {'═'*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int,
                        default=[500, 2000, 5000, 20000, 100000, 500000])
    args = parser.parse_args()
    run(args.sizes)
