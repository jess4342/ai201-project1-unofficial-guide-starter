"""
Milestone 4 — Embedding and retrieval.

Loads the chunks produced by ingest.py (chunks.json), embeds them with
all-MiniLM-L6-v2, stores them in a persistent ChromaDB collection along with
their source metadata, and exposes a retrieve() function that returns the
top-k most relevant chunks (with distance scores and source info) for a query.

Run it to (re)build the index and print a retrieval test against the
evaluation-plan questions:
    python embed.py

Import retrieve() / get_collection() from other modules (Milestone 5):
    from embed import retrieve
"""

from __future__ import annotations

import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

# --- Config (from planning.md → Retrieval Approach) ------------------------
MODEL_NAME = "all-MiniLM-L6-v2"   # local, no API key, 384-dim
TOP_K = 4
COLLECTION_NAME = "apartment_reviews"

ROOT = Path(__file__).parent
CHUNKS_FILE = ROOT / "chunks.json"
CHROMA_DIR = ROOT / "chroma_db"   # persisted to disk (gitignored)

# Cache the model + client so importing modules don't reload them per call.
_model: SentenceTransformer | None = None
_client: chromadb.ClientAPI | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"Loading embedding model: {MODEL_NAME} ...")
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _client


# ---------------------------------------------------------------------------
# Build the index
# ---------------------------------------------------------------------------
def build_index() -> chromadb.Collection:
    """Embed every chunk in chunks.json and (re)load it into ChromaDB.

    We drop and recreate the collection each run so re-running never produces
    duplicate entries. Cosine distance is used because MiniLM embeddings are
    direction-based — cosine puts relevant matches in the ~0.2-0.5 range the
    Milestone 4 checkpoint expects.
    """
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    if not chunks:
        raise SystemExit(f"No chunks found in {CHUNKS_FILE}. Run ingest.py first.")

    model = get_model()
    client = get_client()

    # Fresh collection every build (idempotent re-runs).
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # didn't exist yet
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    texts = [c["text"] for c in chunks]
    print(f"Embedding {len(texts)} chunks ...")
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)

    collection.add(
        ids=[c["id"] for c in chunks],
        embeddings=embeddings.tolist(),
        documents=texts,
        metadatas=[
            {
                "complex": c["complex"],
                "source_platform": c["source_platform"],
                "source_file": c["source_file"],
                "date": c["date"],
                "date_int": c["date_int"],
            }
            for c in chunks
        ],
    )
    print(f"Stored {collection.count()} chunks in collection '{COLLECTION_NAME}' "
          f"(persisted to {CHROMA_DIR.name}/).")
    return collection


def get_collection() -> chromadb.Collection:
    """Return the existing collection, building it if it isn't there yet."""
    client = get_client()
    try:
        return client.get_collection(COLLECTION_NAME)
    except Exception:
        return build_index()


# ---------------------------------------------------------------------------
# Retrieve
# ---------------------------------------------------------------------------
def build_where(complex_filter: str | None = None,
                date_min: int | None = None,
                date_max: int | None = None,
                platform_filter: str | None = None) -> dict | None:
    """Assemble a ChromaDB `where` filter from metadata constraints.

    Combines optional complex / platform equality with an optional date_int
    range (YYYYMMDD). Multiple constraints are wrapped in `$and`.
    """
    conds: list[dict] = []
    if complex_filter:
        conds.append({"complex": complex_filter})
    if platform_filter:
        conds.append({"source_platform": platform_filter})
    if date_min is not None:
        conds.append({"date_int": {"$gte": date_min}})
    if date_max is not None:
        conds.append({"date_int": {"$lte": date_max}})
    if not conds:
        return None
    return conds[0] if len(conds) == 1 else {"$and": conds}


def retrieve(query: str, k: int = TOP_K, complex_filter: str | None = None,
             date_min: int | None = None, date_max: int | None = None,
             platform_filter: str | None = None) -> list[dict]:
    """Return the top-k chunks most relevant to `query`.

    complex_filter: restrict to one complex (defends against cross-property bleed).
    platform_filter: restrict to one source platform (Yelp / ApartmentRatings).
    date_min / date_max: restrict to reviews in a YYYYMMDD date range. Any may be None.
    """
    model = get_model()
    collection = get_collection()
    query_emb = model.encode([query], normalize_embeddings=True).tolist()

    where = build_where(complex_filter, date_min, date_max, platform_filter)
    res = collection.query(
        query_embeddings=query_emb,
        n_results=k,
        where=where,
    )

    hits = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        hits.append({"text": doc, "distance": dist, **meta})
    return hits


# ---------------------------------------------------------------------------
# Retrieval test harness (Milestone 4 checkpoint)
# ---------------------------------------------------------------------------
TEST_QUERIES = [
    # (query, optional complex_filter) — drawn from planning.md Evaluation Plan
    ("Do reviewers report parking as a problem at Metro 112?", "Metro 112"),
    ("Which apartments have thin walls or noise problems from neighbors?", None),
    ("Is maintenance fast and responsive? Do they fix issues quickly?", None),
    ("How reliable is the pricing and rent at Metro 112?", "Metro 112"),
]


def run_tests() -> None:
    print("\n" + "=" * 74)
    print("RETRIEVAL TEST  (checkpoint: top results should be on-topic, distance < 0.5)")
    print("=" * 74)
    for query, cflt in TEST_QUERIES:
        tag = f"  [filtered to complex={cflt}]" if cflt else ""
        print(f"\nQUERY: {query}{tag}")
        print("-" * 74)
        for i, hit in enumerate(retrieve(query, complex_filter=cflt), 1):
            preview = hit["text"][:180].replace("\n", " ")
            flag = "" if hit["distance"] < 0.5 else "  <-- weak match (>=0.5)"
            print(f"{i}. dist={hit['distance']:.3f}  {hit['complex']} "
                  f"({hit['source_platform']}){flag}")
            print(f"   {preview}...")


def main() -> None:
    build_index()
    run_tests()


if __name__ == "__main__":
    main()
