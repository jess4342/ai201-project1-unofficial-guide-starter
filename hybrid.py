"""
Stretch feature — Hybrid search (BM25 + semantic).

Combines lexical BM25 scoring with the dense semantic embeddings used in the
core pipeline. Both methods score every chunk; the two score sets are each
min-max normalized to [0, 1] and fused as:

    hybrid = alpha * semantic_norm + (1 - alpha) * bm25_norm      (alpha = 0.5)

Lexical BM25 nails exact terms (a complex name, "parking", a staff name);
semantic embeddings catch paraphrase. Fusing them is meant to get both.

Run a side-by-side comparison (semantic-only vs BM25-only vs hybrid):
    python hybrid.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from embed import get_model

ROOT = Path(__file__).parent
CHUNKS = json.loads((ROOT / "chunks.json").read_text(encoding="utf-8"))
ALPHA = 0.5  # weight on the semantic score; (1 - ALPHA) on BM25


# Common English words removed before BM25 scoring, so generic terms like
# "is/at/the/problem" don't inflate lexical matches for off-topic chunks.
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "do", "does", "for",
    "from", "had", "has", "have", "i", "in", "is", "it", "its", "of", "on", "or",
    "our", "that", "the", "their", "them", "they", "this", "to", "very", "was",
    "we", "were", "what", "when", "which", "with", "you", "your", "any", "about",
    "there", "here", "would", "could", "been", "than", "then", "so", "if",
    "problem", "problems", "issue", "issues",  # too generic in a review corpus
}


def _tokenize(text: str) -> list[str]:
    toks = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in toks if t not in _STOPWORDS]


# Build both indexes once at import.
_bm25 = BM25Okapi([_tokenize(c["text"]) for c in CHUNKS])
_doc_embeddings = get_model().encode(
    [c["text"] for c in CHUNKS], normalize_embeddings=True
)


def _minmax(scores: np.ndarray) -> np.ndarray:
    lo, hi = scores.min(), scores.max()
    if hi - lo < 1e-9:
        return np.zeros_like(scores)
    return (scores - lo) / (hi - lo)


def _semantic_scores(query: str) -> np.ndarray:
    """Cosine similarity (higher = better) between query and every chunk."""
    q = get_model().encode([query], normalize_embeddings=True)[0]
    return _doc_embeddings @ q  # normalized vectors -> dot product = cosine sim


def search(query: str, method: str = "hybrid", k: int = 4,
           complex_filter: str | None = None,
           date_min: int | None = None, date_max: int | None = None,
           platform_filter: str | None = None) -> list[dict]:
    """Return top-k chunks for `query` using 'semantic', 'bm25', or 'hybrid'.

    complex_filter / platform_filter / date_min / date_max apply the same
    metadata filtering the core pipeline uses, so hybrid composes with them.
    """
    sem = _minmax(_semantic_scores(query))
    bm = _minmax(np.array(_bm25.get_scores(_tokenize(query))))

    if method == "semantic":
        scores = sem
    elif method == "bm25":
        scores = bm
    elif method == "hybrid":
        scores = ALPHA * sem + (1 - ALPHA) * bm
    else:
        raise ValueError(f"unknown method: {method}")

    def _ok(i: int) -> bool:
        c = CHUNKS[i]
        if complex_filter and c["complex"] != complex_filter:
            return False
        if platform_filter and c["source_platform"] != platform_filter:
            return False
        if date_min is not None and c.get("date_int", 0) < date_min:
            return False
        if date_max is not None and c.get("date_int", 0) > date_max:
            return False
        return True

    order = [i for i in np.argsort(scores)[::-1] if _ok(i)]
    top = list(order)[:k]
    return [
        {
            "text": CHUNKS[i]["text"],
            "complex": CHUNKS[i]["complex"],
            "source_platform": CHUNKS[i]["source_platform"],
            "source_file": CHUNKS[i]["source_file"],
            "date": CHUNKS[i].get("date", "unknown"),
            "date_int": CHUNKS[i].get("date_int", 0),
            "score": float(scores[i]),
            "sem": float(sem[i]),
            "bm25": float(bm[i]),
        }
        for i in top
    ]


# ---------------------------------------------------------------------------
# Comparison harness
# ---------------------------------------------------------------------------
COMPARE_QUERIES = [
    "Mariano in maintenance",                          # exact names -> BM25 favored
    "Is it hard to hear neighbors through the walls?",  # paraphrase -> semantic favored
    "Brittany at the Metro 112 office",                 # exact name + complex
]


def _row(hit: dict) -> str:
    return (f"{hit['complex'][:18]:<18} score={hit['score']:.3f} "
            f"(sem={hit['sem']:.2f} bm25={hit['bm25']:.2f})  "
            f"{hit['text'][:70].replace(chr(10), ' ')}...")


def compare() -> None:
    for q in COMPARE_QUERIES:
        print("\n" + "=" * 78)
        print("QUERY:", q)
        for method in ("semantic", "bm25", "hybrid"):
            print(f"\n  -- {method.upper()} --")
            for hit in search(q, method=method, k=2):
                print("   ", _row(hit))


if __name__ == "__main__":
    compare()
