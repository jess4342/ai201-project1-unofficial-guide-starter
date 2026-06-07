"""
Milestone 3 — Document ingestion and chunking.

Loads the apartment-review .txt files from documents/, cleans them, splits them
into boundary-aware chunks (~600 chars with ~80-char overlap, per planning.md),
attaches source metadata to every chunk, and writes the result to chunks.json
for Milestone 4 (embedding + retrieval) to consume.

Stdlib only — no ML dependencies needed at this stage. Run it with:
    python ingest.py
"""

from __future__ import annotations

import html
import json
import random
import re
from pathlib import Path

# --- Spec (from planning.md → Chunking Strategy) ---------------------------
CHUNK_SIZE = 600      # target characters per chunk
CHUNK_OVERLAP = 80    # characters carried from the end of one chunk into the next

DOCS_DIR = Path(__file__).parent / "documents"
OUTPUT_FILE = Path(__file__).parent / "chunks.json"

# Known complexes in the corpus. We detect the complex by keyword instead of
# parsing the filename, because the filenames use inconsistent separators
# ("Metro 112 - ..." vs "Meydenbauer Avalon ..." with no dash). Order matters
# only for readability; each keyword is matched case-insensitively.
COMPLEX_KEYWORDS = {
    "bravern": "The Bravern",
    "metro 112": "Metro 112",
    "surrey": "Surrey on the Main",
    "meydenbauer": "Avalon Meydenbauer",
    "avalon": "Avalon Meydenbauer",
}


# ---------------------------------------------------------------------------
# 1. LOAD
# ---------------------------------------------------------------------------
def detect_complex(filename: str) -> str:
    """Map a filename to its apartment complex via keyword match."""
    name = filename.lower()
    for keyword, complex_name in COMPLEX_KEYWORDS.items():
        if keyword in name:
            return complex_name
    return "UNKNOWN"  # surfaced as a warning so bad metadata never passes silently


def detect_platform(filename: str) -> str:
    """Infer the source platform from the filename.

    ApartmentRatings entries in this corpus carry a '•' bullet and/or the word
    'Resident' with a year range; everything else came from Yelp.
    """
    if "•" in filename or "resident" in filename.lower():
        return "ApartmentRatings"
    return "Yelp"


# Trailing review date in the filename, e.g. "... - Feb 22, 2018.txt"
# (tolerates the stray comma in "Dec, 22, 2010").
DATE_RE = re.compile(r"-\s*([A-Za-z]{3,9})\.?,?\s+(\d{1,2}),?\s*(\d{4})\s*$")
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def parse_date(filename: str) -> tuple[str, int]:
    """Extract the trailing review date from a filename.

    Returns (iso_date, date_int) where date_int is a sortable YYYYMMDD integer
    used for range filtering in ChromaDB. Falls back to ("unknown", 0) if no
    date is present.
    """
    stem = filename[:-4] if filename.lower().endswith(".txt") else filename
    m = DATE_RE.search(stem)
    if not m:
        return "unknown", 0
    mon = _MONTHS.get(m.group(1)[:3].lower())
    if not mon:
        return "unknown", 0
    day, year = int(m.group(2)), int(m.group(3))
    return f"{year:04d}-{mon:02d}-{day:02d}", year * 10000 + mon * 100 + day


def load_documents(docs_dir: Path) -> list[dict]:
    """Read every .txt file in docs_dir into a record with source metadata."""
    docs = []
    txt_files = sorted(docs_dir.glob("*.txt"))
    if not txt_files:
        raise SystemExit(f"No .txt files found in {docs_dir}")

    for path in txt_files:
        raw = path.read_text(encoding="utf-8")
        complex_name = detect_complex(path.name)
        if complex_name == "UNKNOWN":
            print(f"  [WARN] Could not detect complex for: {path.name}")
        iso_date, date_int = parse_date(path.name)
        if date_int == 0:
            print(f"  [WARN] Could not parse date for: {path.name}")
        docs.append(
            {
                "source_file": path.name,
                "complex": complex_name,
                "source_platform": detect_platform(path.name),
                "date": iso_date,
                "date_int": date_int,
                "raw_text": raw,
            }
        )
    return docs


# ---------------------------------------------------------------------------
# 2. CLEAN
# ---------------------------------------------------------------------------
def clean_text(text: str) -> str:
    """Light, structure-preserving clean.

    The .txt files were copied by hand and are already free of HTML/nav, so we
    only normalize: decode any stray HTML entities, unify line endings, trim
    trailing spaces, and collapse runs of blank lines. We deliberately KEEP
    paragraph breaks because the chunker uses them as boundaries.
    """
    text = html.unescape(text)                 # &amp; -> &, &#39; -> ', etc.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))  # trim line ends
    text = re.sub(r"\n{3,}", "\n\n", text)     # collapse 3+ newlines to one blank line
    return text.strip()


# ---------------------------------------------------------------------------
# 3. CHUNK
# ---------------------------------------------------------------------------
def split_sentences(text: str) -> list[str]:
    """Split text into sentences without breaking numbered list markers.

    We break after . ! ? followed by whitespace, but skip a period that is
    preceded by a digit (e.g. the "1." / "2." in "1. Friendly staff"), so list
    items stay attached to their content instead of becoming "1." fragments.
    """
    sentences = []
    start = 0
    for m in re.finditer(r"[.!?]+\s+", text):
        # char right before the punctuation run
        prev = text[m.start() - 1] if m.start() > 0 else ""
        if prev.isdigit():
            continue  # likely a list marker like "1." — not a sentence end
        sentences.append(text[start:m.end()].strip())
        start = m.end()
    tail = text[start:].strip()
    if tail:
        sentences.append(tail)
    return [s for s in sentences if s]


def _hard_split(sentence: str, size: int, overlap: int) -> list[str]:
    """Fallback for a single sentence longer than `size`: slice on char budget."""
    pieces, i = [], 0
    step = max(1, size - overlap)
    while i < len(sentence):
        pieces.append(sentence[i : i + size])
        i += step
    return pieces


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Boundary-aware chunking honoring the 600-char / 80-char-overlap spec.

    Greedily packs whole sentences up to `size` chars, then starts the next
    chunk with the trailing sentence(s) of the previous one totaling up to
    `overlap` chars — so a claim and its supporting detail are never stranded on
    opposite sides of a boundary. A short review stays a single chunk; a long
    one splits into a few focused chunks.
    """
    sentences = split_sentences(text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        # A lone sentence bigger than the budget: flush, then hard-split it.
        if len(sentence) > size:
            if current:
                chunks.append(" ".join(current))
                current, current_len = [], 0
            chunks.extend(_hard_split(sentence, size, overlap))
            continue

        # +1 accounts for the space we join sentences with.
        if current_len + len(sentence) + 1 > size and current:
            chunks.append(" ".join(current))
            # Build the overlap from the tail sentences of the chunk just emitted.
            carry, carry_len = [], 0
            for s in reversed(current):
                if carry_len + len(s) + 1 > overlap:
                    break
                carry.insert(0, s)
                carry_len += len(s) + 1
            current = carry
            current_len = carry_len

        current.append(sentence)
        current_len += len(sentence) + 1

    if current:
        chunks.append(" ".join(current))

    # Drop any empty/whitespace-only chunks (Checkpoint: no empty strings).
    return [c.strip() for c in chunks if c.strip()]


def chunk_documents(docs: list[dict]) -> list[dict]:
    """Clean and chunk every document, carrying metadata onto each chunk."""
    all_chunks = []
    for doc in docs:
        cleaned = clean_text(doc["raw_text"])
        for i, chunk in enumerate(chunk_text(cleaned)):
            all_chunks.append(
                {
                    "id": f"{doc['source_file']}::chunk-{i}",
                    "text": chunk,
                    "complex": doc["complex"],
                    "source_platform": doc["source_platform"],
                    "source_file": doc["source_file"],
                    "date": doc["date"],
                    "date_int": doc["date_int"],
                    "char_count": len(chunk),
                }
            )
    return all_chunks


# ---------------------------------------------------------------------------
# 4. INSPECT / VALIDATE
# ---------------------------------------------------------------------------
def report(docs: list[dict], chunks: list[dict]) -> None:
    print("\n" + "=" * 70)
    print("INGESTION SUMMARY")
    print("=" * 70)
    print(f"Documents loaded : {len(docs)}")
    print(f"Total chunks     : {len(chunks)}")

    lengths = [c["char_count"] for c in chunks]
    if lengths:
        print(f"Chunk length     : min={min(lengths)}  "
              f"avg={sum(lengths) // len(lengths)}  max={max(lengths)} chars")

    # Per-complex breakdown — confirms metadata is attached to the right doc.
    print("\nChunks per complex:")
    by_complex: dict[str, int] = {}
    for c in chunks:
        by_complex[c["complex"]] = by_complex.get(c["complex"], 0) + 1
    for name, n in sorted(by_complex.items()):
        print(f"  {name:<22} {n}")

    # Automated sanity checks for the failure modes called out in the milestone.
    print("\nSanity checks:")
    empties = [c for c in chunks if not c["text"].strip()]
    html_like = [c for c in chunks if re.search(r"<[a-z/][^>]*>|&[a-z]+;", c["text"])]
    print(f"  empty chunks         : {len(empties)}")
    print(f"  HTML/entity leftovers: {len(html_like)}")
    print(f"  UNKNOWN-complex docs : {sum(1 for d in docs if d['complex'] == 'UNKNOWN')}")


def print_samples(chunks: list[dict], n: int = 5, seed: int = 7) -> None:
    print("\n" + "=" * 70)
    print(f"{n} RANDOM CHUNKS (read these — each should stand on its own)")
    print("=" * 70)
    random.seed(seed)  # fixed seed so the inspection is reproducible
    for c in random.sample(chunks, min(n, len(chunks))):
        print(f"\n[{c['id']}]  complex={c['complex']}  "
              f"platform={c['source_platform']}  ({c['char_count']} chars)")
        print("-" * 70)
        print(c["text"])


# ---------------------------------------------------------------------------
def main() -> None:
    print(f"Loading documents from {DOCS_DIR} ...")
    docs = load_documents(DOCS_DIR)
    chunks = chunk_documents(docs)

    report(docs, chunks)
    print_samples(chunks, n=5)

    OUTPUT_FILE.write_text(json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {len(chunks)} chunks -> {OUTPUT_FILE.name}")


if __name__ == "__main__":
    main()
