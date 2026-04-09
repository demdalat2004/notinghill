"""
NotingHill — services/dedup_service.py
Exact + near-duplicate detection.

Optimizations vs original:
  • run_text_dedup / run_image_dedup: O(n²) → LSH  (see lsh/lsh_index.py)
    With 500K files the old approach would take ~69 hours.
    LSH completes in seconds/minutes.
  • upsert_duplicate_group: already uses batch size lookup (kept).
  • _cluster_and_save: replaced entirely with LSH-based version.
"""
from __future__ import annotations

import time

from ..db.connection import get_db
from ..db import repo_duplicates
from ..services.lsh.lsh_index import cluster_with_scores


# ── Exact dedup (SHA-256) — unchanged, already fast ──────────────────────

def run_exact_dedup() -> int:
    """Group files with identical sha256. Returns number of groups found."""
    with get_db() as con:
        rows = con.execute("""
            SELECT sha256, GROUP_CONCAT(item_id) as ids
            FROM items WHERE sha256 IS NOT NULL AND is_deleted=0
            GROUP BY sha256 HAVING COUNT(*)>1
        """).fetchall()

    count = 0
    for row in rows:
        sha = row["sha256"]
        ids = [int(i) for i in row["ids"].split(",")]
        repo_duplicates.upsert_duplicate_group("exact", sha, ids)
        count += 1
    return count


# ── Near-duplicate dedup — O(n²) → LSH ───────────────────────────────────

def run_text_dedup(threshold: float = 0.90) -> int:
    """
    Group files with similar simhash (hamming distance within threshold).
    Uses LSH banding: O(n * bands) instead of O(n²).
    """
    with get_db() as con:
        rows = con.execute("""
            SELECT item_id, simhash64 FROM items
            WHERE simhash64 IS NOT NULL AND is_deleted=0
        """).fetchall()

    items = [(r["item_id"], r["simhash64"]) for r in rows]
    return _lsh_cluster_and_save("similar_text", items, threshold)


def run_image_dedup(threshold: float = 0.90) -> int:
    """
    Group images with similar perceptual hash.
    Uses LSH banding: O(n * bands) instead of O(n²).
    """
    with get_db() as con:
        rows = con.execute("""
            SELECT item_id, phash FROM items
            WHERE phash IS NOT NULL AND is_deleted=0 AND file_type_group='image'
        """).fetchall()

    items = [(r["item_id"], r["phash"]) for r in rows]
    return _lsh_cluster_and_save("similar_image", items, threshold)


def _lsh_cluster_and_save(
    group_type: str,
    items: list[tuple[int, str]],
    threshold: float,
) -> int:
    """
    LSH clustering + persist groups.
    Returns number of groups written.
    """
    if not items:
        return 0

    clusters = cluster_with_scores(items, threshold=threshold)

    count = 0
    for cluster_ids, score_map in clusters:
        # Use a stable key: sorted item_ids joined
        group_key = "_".join(str(i) for i in sorted(cluster_ids))
        repo_duplicates.upsert_duplicate_group(
            group_type,
            group_key,
            cluster_ids,
            scores=score_map,
        )
        count += 1
    return count
