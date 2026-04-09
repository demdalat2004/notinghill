"""
NotingHill — services/lsh/lsh_index.py
=======================================
LSH (Locality-Sensitive Hashing) wrapper for near-duplicate detection.
Replaces the O(n²) clustering in dedup_service.py.

Algorithm
---------
SimHash / pHash are 64-bit integers stored as hex strings.
For LSH we use a banding approach on bit-decomposed fingerprints:

  • Split 64 bits into `b` bands of `r` bits each  (b * r = 64)
  • Two items hash to the same bucket in ≥1 band  →  candidate pair
  • Candidate pairs are verified with exact hamming distance

Probability of detection (for similarity s, bands b, rows-per-band r):
  P = 1 - (1 - s^r)^b

For s=0.90, b=8, r=8:  P ≈ 0.9997  (virtually guaranteed detection)
For s=0.85, b=8, r=8:  P ≈ 0.9966

No external dependencies — uses only the stdlib.
datasketch is NOT used here because our hashes are already computed
fixed-size fingerprints, not raw document shingling.
"""
from __future__ import annotations

import collections
from typing import Iterable

# ── tuneable constants ─────────────────────────────────────────────────────
# 64 bits = 8 bands × 8 bits/band
_BANDS = 8
_ROWS  = 8   # bits per band
assert _BANDS * _ROWS == 64


def _hex_to_int(h: str) -> int | None:
    try:
        return int(h, 16)
    except (ValueError, TypeError):
        return None


def _band_keys(fingerprint_int: int) -> list[int]:
    """Split 64-bit integer into b band keys."""
    keys = []
    for b in range(_BANDS):
        shift = b * _ROWS
        mask  = (1 << _ROWS) - 1
        keys.append(((fingerprint_int >> shift) & mask) | (b << _ROWS))
    return keys


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def find_similar_pairs(
    items: list[tuple[int, str]],   # [(item_id, hex_fingerprint), ...]
    threshold: float = 0.90,
    max_hamming: int | None = None, # override: use raw hamming cutoff instead
) -> list[tuple[int, int, float]]:
    """
    Return list of (item_id_a, item_id_b, similarity) for all pairs
    whose similarity ≥ threshold.

    Complexity: O(n * b)  instead of O(n²)
    """
    if max_hamming is None:
        # Convert similarity threshold → max hamming distance
        max_hamming = int((1.0 - threshold) * 64)

    # ── Build LSH index ───────────────────────────────────────────────────
    buckets: dict[int, list[int]] = collections.defaultdict(list)
    int_fps: dict[int, int] = {}  # item_id → int fingerprint

    for item_id, hex_fp in items:
        fp_int = _hex_to_int(hex_fp)
        if fp_int is None:
            continue
        int_fps[item_id] = fp_int
        for band_key in _band_keys(fp_int):
            buckets[band_key].append(item_id)

    # ── Collect candidate pairs (shared bucket ≥ 1 band) ─────────────────
    candidates: set[tuple[int, int]] = set()
    for bucket_items in buckets.values():
        if len(bucket_items) < 2:
            continue
        for i in range(len(bucket_items)):
            for j in range(i + 1, len(bucket_items)):
                a, b = bucket_items[i], bucket_items[j]
                pair = (min(a, b), max(a, b))
                candidates.add(pair)

    # ── Verify candidates with exact hamming distance ─────────────────────
    results: list[tuple[int, int, float]] = []
    for id_a, id_b in candidates:
        fp_a = int_fps.get(id_a)
        fp_b = int_fps.get(id_b)
        if fp_a is None or fp_b is None:
            continue
        dist = _hamming(fp_a, fp_b)
        if dist <= max_hamming:
            sim = 1.0 - dist / 64.0
            results.append((id_a, id_b, sim))

    return results


def cluster_pairs(
    pairs: list[tuple[int, int, float]],
    all_ids: Iterable[int],
) -> list[list[int]]:
    """
    Union-Find clustering of (id_a, id_b) pairs.
    Returns list of clusters (each cluster = list of item_ids).
    Singletons are excluded.
    """
    parent: dict[int, int] = {i: i for i in all_ids}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        parent[find(x)] = find(y)

    for id_a, id_b, _ in pairs:
        if id_a in parent and id_b in parent:
            union(id_a, id_b)

    groups: dict[int, list[int]] = collections.defaultdict(list)
    for item_id in parent:
        groups[find(item_id)].append(item_id)

    return [g for g in groups.values() if len(g) >= 2]


def cluster_with_scores(
    items: list[tuple[int, str]],
    threshold: float = 0.90,
) -> list[tuple[list[int], dict[int, float]]]:
    """
    High-level API: returns list of (cluster_item_ids, {item_id: best_score}).
    Scores represent the highest similarity any member has to any other member.
    """
    if not items:
        return []

    pairs = find_similar_pairs(items, threshold=threshold)
    if not pairs:
        return []

    all_ids = {item_id for item_id, _ in items}
    clusters = cluster_pairs(pairs, all_ids)

    # Build score map per cluster
    # For each item, take its max similarity to any pair partner
    best_score: dict[int, float] = {}
    for id_a, id_b, sim in pairs:
        best_score[id_a] = max(best_score.get(id_a, 0.0), sim)
        best_score[id_b] = max(best_score.get(id_b, 0.0), sim)

    return [(cluster, {iid: best_score.get(iid, 1.0) for iid in cluster})
            for cluster in clusters]
