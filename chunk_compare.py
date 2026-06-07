"""
Stretch feature — Chunking-strategy comparison.

Compares the project's boundary-aware 600/80 chunker against a mechanical
fixed-character 300/50 split, on the same query set. For each query it reports
the best (lowest) cosine distance each strategy achieves and whether the
best-matching chunk is a complete thought or a mid-sentence fragment.

    python chunk_compare.py
"""

from __future__ import annotations

import numpy as np

from embed import get_model
from ingest import load_documents, clean_text, chunk_text, DOCS_DIR


def fixed_char_chunks(text: str, size: int = 300, overlap: int = 50) -> list[str]:
    """Strategy B: mechanical fixed-character split (no boundary awareness)."""
    step = max(1, size - overlap)
    return [text[i : i + size] for i in range(0, len(text), step) if text[i : i + size].strip()]


def build(strategy) -> list[str]:
    """Apply a chunking strategy to every cleaned document; return chunk texts."""
    chunks = []
    for doc in load_documents(DOCS_DIR):
        chunks.extend(strategy(clean_text(doc["raw_text"])))
    return chunks


def looks_complete(chunk: str) -> bool:
    """Heuristic: a 'complete' chunk ends on sentence punctuation."""
    return chunk.rstrip().endswith((".", "!", "?"))


QUERIES = [
    "Is parking a problem at Metro 112?",
    "Are the walls thin and can you hear the neighbors?",
    "How fast is maintenance at The Bravern?",
]


def evaluate(name: str, chunks: list[str], model) -> None:
    emb = model.encode(chunks, normalize_embeddings=True)
    lengths = [len(c) for c in chunks]
    print(f"\n### {name}")
    print(f"chunks={len(chunks)}  avg_len={sum(lengths)//len(lengths)}  "
          f"complete={sum(looks_complete(c) for c in chunks)}/{len(chunks)}")
    for q in QUERIES:
        qv = model.encode([q], normalize_embeddings=True)[0]
        sims = emb @ qv
        best = int(np.argmax(sims))
        dist = 1 - float(sims[best])  # cosine distance, lower = better
        flag = "complete" if looks_complete(chunks[best]) else "FRAGMENT"
        print(f"  dist={dist:.3f} [{flag:8}] {q}")
        print(f"         -> {chunks[best][:90].replace(chr(10),' ')}...")


def main() -> None:
    model = get_model()
    evaluate("Strategy A — boundary-aware 600/80 (project default)",
             build(chunk_text), model)
    evaluate("Strategy B — mechanical fixed 300/50",
             build(fixed_char_chunks), model)


if __name__ == "__main__":
    main()
