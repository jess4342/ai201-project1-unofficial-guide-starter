"""
Milestone 5 — Grounded generation.

Ties retrieval (Milestone 4) to a Groq-hosted LLM. `ask()` retrieves the
top-k chunks for a question, builds a context block, and prompts the model to
answer using ONLY that context — declining when the context doesn't support an
answer. Source attribution is guaranteed programmatically (built from the
retrieved chunks' metadata), not left to the model to invent.

    from query import ask
    result = ask("Is parking a problem at Metro 112?")
    # -> {"answer": ..., "sources": [...], "chunks": [...]}

Run directly for an end-to-end smoke test:
    python query.py
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from groq import Groq

from embed import retrieve, TOP_K
from ingest import COMPLEX_KEYWORDS, DATE_RE

load_dotenv()


def complexes_mentioned(text: str) -> set[str]:
    """Return the set of known complexes named in `text` (keyword match)."""
    low = text.lower()
    return {name for kw, name in COMPLEX_KEYWORDS.items() if kw in low}


# Complex-name fragments to strip when deriving the reviewer from a filename.
_COMPLEX_FRAGMENTS = [
    "The Bravern", "Bravern", "Metro 112", "Surrey on the Main", "Surrey on Main",
    "Surrey", "Meydenbauer Avalon", "Avalon Meydenbauer", "Meydenbauer", "Avalon",
]


def reviewer_from_file(source_file: str) -> str:
    """Derive a human-readable reviewer/source label from the filename.

    The reviewer identity is only encoded in the filename (e.g.
    "Metro 112 -  Vivian H. Bellevue, WA.txt" -> "Vivian H. Bellevue, WA").
    We strip the complex-name prefix and the extension; what remains identifies
    the reviewer (a name + location, or an ApartmentRatings handle + year).
    """
    import re
    stem = source_file[:-4] if source_file.lower().endswith(".txt") else source_file
    stem = DATE_RE.sub("", stem)  # drop the trailing review date
    for frag in _COMPLEX_FRAGMENTS:
        stem = re.sub(re.escape(frag), "", stem, flags=re.IGNORECASE)
    return stem.strip(" -,") or source_file

MODEL = "llama-3.3-70b-versatile"  # Groq free-tier, per the milestone

SYSTEM_PROMPT = """You are an assistant that answers questions about Bellevue \
apartment complexes using ONLY the resident reviews provided in the context.

Rules — follow them exactly:
1. Use only the information in the CONTEXT below. Do not use any outside or \
prior knowledge about these apartments, the city, or apartments in general.
2. If the context does not contain enough information to answer the question, \
reply with exactly: "I don't have enough information on that." Do not guess or \
fill gaps from general knowledge.
3. Attribute every claim to the complex AND the reviewer shown in the source \
label, e.g. "Metro 112 reviewer Vivian H. says...". Do NOT cite bare numbers \
like [1] — always name the reviewer. Never blend complaints from one complex \
into another.
4. When only one review supports a claim, say so (e.g. "one reviewer, Vivian H., \
notes...") rather than implying a consensus.
5. Be concise and factual. Quote or paraphrase the reviews; do not editorialize."""

USER_TEMPLATE = """CONTEXT (resident reviews):
{context}

QUESTION: {question}

Answer using only the context above, following all the rules."""


def _client() -> Groq:
    key = os.getenv("GROQ_API_KEY")
    if not key or key == "your_key_here":
        raise SystemExit("GROQ_API_KEY is not set in .env — add your Groq key first.")
    return Groq(api_key=key)


def format_context(chunks: list[dict]) -> str:
    """Render retrieved chunks into a source-labeled context block.

    Each block leads with the complex and reviewer so the model can attribute
    by name rather than by a bare index.
    """
    blocks = []
    for c in chunks:
        reviewer = reviewer_from_file(c["source_file"])
        blocks.append(
            f"[Source: {c['complex']} — reviewer {reviewer} "
            f"({c['source_platform']})]\n{c['text']}"
        )
    return "\n\n".join(blocks)


def source_list(chunks: list[dict]) -> list[str]:
    """Unique source attributions, built programmatically from metadata.

    This is what guarantees attribution regardless of what the model writes —
    one entry per source file that actually fed the answer, naming the reviewer.
    """
    seen, sources = set(), []
    for c in chunks:
        if c["source_file"] not in seen:
            seen.add(c["source_file"])
            sources.append(f"{c['complex']} — {reviewer_from_file(c['source_file'])}")
    return sources


def ask(question: str, k: int = TOP_K, complex_filter: str | None = None,
        method: str = "semantic", date_min: int | None = None,
        date_max: int | None = None, platform_filter: str | None = None) -> dict:
    """Retrieve, generate a grounded answer, and return it with its sources.

    method: "semantic" uses the ChromaDB dense retriever (default); "hybrid" or
    "bm25" route through the hybrid retriever (stretch feature).
    date_min / date_max: optional YYYYMMDD bounds on the review date.
    platform_filter: optional source platform (Yelp / ApartmentRatings).
    """
    if method == "semantic":
        chunks = retrieve(question, k=k, complex_filter=complex_filter,
                          date_min=date_min, date_max=date_max,
                          platform_filter=platform_filter)
    else:
        from hybrid import search  # local import avoids loading BM25 unless used
        chunks = search(question, method=method, k=k, complex_filter=complex_filter,
                        date_min=date_min, date_max=date_max,
                        platform_filter=platform_filter)

    if not chunks:
        return {"answer": "I don't have enough information on that.",
                "sources": [], "chunks": []}

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(
            context=format_context(chunks), question=question)},
    ]
    completion = _client().chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0,  # deterministic, no creative drift away from the context
    )
    answer = completion.choices[0].message.content.strip()

    # Only surface sources when the model actually answered — if it declined,
    # citing reviews would be misleading.
    declined = answer.lower().startswith("i don't have enough information")
    return {
        "answer": answer,
        "sources": [] if declined else source_list(chunks),
        "chunks": chunks,
    }


# ---------------------------------------------------------------------------
# Stretch feature — Conversational memory
# ---------------------------------------------------------------------------
CONDENSE_PROMPT = """Given the conversation so far and a follow-up question, \
rewrite the follow-up as a STANDALONE question that includes any context the \
reader would otherwise have to infer — especially the apartment complex being \
discussed. If the follow-up is already standalone, return it unchanged. Output \
ONLY the rewritten question, nothing else.

Conversation so far:
{history}

Follow-up question: {question}
Standalone question:"""


class Conversation:
    """Multi-turn chat with memory.

    Before retrieving, a follow-up question is rewritten into a standalone query
    using the prior turns, so references like "there" or "what about noise?"
    resolve to the complex discussed earlier. Each turn is then answered with
    the same grounded `ask()` pipeline.
    """

    def __init__(self) -> None:
        self.history: list[tuple[str, str]] = []  # (question, answer)

    def _condense(self, question: str) -> str:
        if not self.history:
            return question  # first turn — nothing to resolve
        history_text = "\n".join(
            f"User: {q}\nAssistant: {a}" for q, a in self.history
        )
        resp = _client().chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": CONDENSE_PROMPT.format(
                history=history_text, question=question)}],
            temperature=0,
        )
        return resp.choices[0].message.content.strip()

    def ask(self, question: str) -> dict:
        standalone = self._condense(question)
        # If the resolved question names exactly one complex, scope retrieval to
        # it (reuses the metadata-filter feature) so follow-ups ground reliably.
        named = complexes_mentioned(standalone)
        cflt = next(iter(named)) if len(named) == 1 else None
        result = ask(standalone, complex_filter=cflt)
        result["original_question"] = question
        result["standalone_question"] = standalone
        self.history.append((question, result["answer"]))
        return result


def _memory_demo() -> None:
    print("\n" + "#" * 74)
    print("CONVERSATIONAL MEMORY DEMO (turn 2 depends on turn 1)")
    print("#" * 74)
    convo = Conversation()
    for turn in ["Is parking a problem at Metro 112?", "What about noise there?"]:
        r = convo.ask(turn)
        print(f"\nUSER: {turn}")
        if r["standalone_question"] != turn:
            print(f"  (rewritten for retrieval -> {r['standalone_question']})")
        print("ASSISTANT:", r["answer"])


# ---------------------------------------------------------------------------
# End-to-end smoke test
# ---------------------------------------------------------------------------
def _smoke() -> None:
    tests = [
        "Is parking a problem at Metro 112?",
        "Which complex has thin walls or noise issues from neighbors?",
        "How responsive is maintenance at The Bravern?",
        "Which apartments in Kirkland do reviewers recommend?",  # out-of-corpus control
    ]
    for q in tests:
        print("\n" + "=" * 74)
        print("Q:", q)
        print("-" * 74)
        r = ask(q)
        print(r["answer"])
        if r["sources"]:
            print("\nSources:")
            for s in r["sources"]:
                print("  •", s)
        else:
            print("\n(no sources — declined / out of corpus)")


if __name__ == "__main__":
    _smoke()
