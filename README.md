# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Demo Video

**[▶️ Watch the demo (unofficialguide_demo.mp4)](unofficialguide_demo.mp4)** 
---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->

Renter-submitted reviews of apartment complexes in Bellevue, WA. This is valuable because it's scattered across multiple review platforms and hard to consolidate — a prospective renter can't easily compare complexes side by side or weigh pros and cons against their own priorities (noise, parking, management responsiveness, pricing). Official property listings advertise amenities but never surface the lived-in tradeoffs (thin walls, unreliable pricing systems, slow elevators) that residents actually report.

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

All sources are `.txt` review files in `documents/`; the review date is encoded in each filename (e.g. `… - Feb 22, 2018.txt`) and parsed into chunk metadata for the date filter.

| # | Source | Reviewer | Reviewed | File |
|---|--------|----------|----------|------|
| 1 | Yelp — The Bravern | Will M. | 2025-12-19 | `The Bravern - Will M. Kirkland, WA - Dec 19, 2025.txt` |
| 2 | Yelp — The Bravern | Emily W. | 2025-06-24 | `The Bravern - Emily W. Portland, OR - Jun 24, 2025.txt` |
| 3 | Yelp — Metro 112 | Vivian H. | 2018-02-22 | `Metro 112 -  Vivian H. Bellevue, WA - Feb 22, 2018.txt` |
| 4 | Yelp — Metro 112 | Summer C. | 2019-09-28 | `Metro 112 - Summer C. Bellevue, WA - Sep 28, 2019.txt` |
| 5 | Yelp — Surrey on the Main | Utopi D. | 2026-04-13 | `Surrey on the Main - Utopi D. San Francisco, CA - Apr 13, 2026.txt` |
| 6 | Yelp — Avalon Meydenbauer | Lorraine I. | 2021-09-04 | `Meydenbauer Avalon Lorraine I. Los Angeles, CA - Sep 4, 2021.txt` |
| 7 | Yelp — Avalon Meydenbauer | Pratik W. | 2017-12-27 | `Meydenbauer Avalon, Pratik W. Seattle, WA - Dec 27, 2017.txt` |
| 8 | ApartmentRatings — Avalon Meydenbauer | Resident 154444 | 2013-06-13 | `Meydenbauer Avalon, Current Resident 154444 Resident • 2013 - Jun 13, 2013.txt` |
| 9 | ApartmentRatings — Avalon Meydenbauer | Resident 392713 | 2011-01-22 | `Meydenbauer Avalon, Current Resident 392713 Resident • 2008 - 2011 - Jan 22, 2011.txt` |
| 10 | ApartmentRatings — Avalon Meydenbauer | livinginrent | 2010-12-22 | `Meydenbauer Avalon, livinginrent Resident • 2009-2010 - Dec, 22, 2010.txt` |

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:** ~600 characters (~130–150 tokens), target/budget per chunk.

**Overlap:** ~80 characters (~20 tokens) of sentence-level overlap carried from the end of one chunk into the start of the next.

**Why these choices fit your documents:** The corpus is short, opinionated reviews that vary widely in length — some are a single paragraph, others run several paragraphs covering distinct topics (parking, management, noise, pricing). A 600-char budget keeps one coherent opinion intact so its embedding stays semantically tight, while splitting a long multi-topic review into a few focused chunks instead of one diluted vector. The 80-char overlap (~13% of chunk size) keeps a claim and its supporting detail from being stranded across a boundary (e.g. "Management is responsive. They fixed my heater the same day.") without inflating the index with near-duplicate chunks.

**Preprocessing before chunking:** The `.txt` files were copied by hand, so they contain no HTML/nav. Cleaning is light and structure-preserving (`clean_text` in `ingest.py`): decode stray HTML entities, normalize line endings, trim trailing spaces, collapse blank-line runs — but keep paragraph breaks, which the chunker uses as boundaries. Chunking is **boundary-aware** (`chunk_text`): it packs whole *sentences* up to the 600-char budget rather than slicing mid-word, with a digit-guard so numbered lists (`1.`, `2.`) don't fragment into "1." pieces, and a hard-split fallback for any single sentence over 600 chars. Each chunk carries metadata (`complex`, `source_platform`, `source_file`); the complex is detected by keyword, not by parsing the inconsistent filenames.

**Final chunk count:** 28 chunks across the 10 review files (lengths 119–592 chars, avg ~479; 0 empty, 0 HTML leftovers). The count is below the 50+ rule-of-thumb because the corpus is small (~13 KB of text); it scales up automatically as more reviews are added, with no change to chunk size.

**Sample chunks** (5 representative chunks, each labeled with its source document):

1. **Source:** `The Bravern - Will M. Kirkland, WA - Dec 19, 2025.txt` (complex: The Bravern, 568 chars)
   > I've waited to make this review until we've lived her a while. This is our first apartment ... but the Bravern has exceeded all my expectations ... it's a fabulous property. Everything ... staff, apartment finishes, appliances, security, parking, the gym, etc. ... they're all absolutely top notch. The staff really makes the difference ... Thea (concierge) and Alon (resident services manager) are great ... Mariano, Gene, and Shawn in maintenance are awesome ...

2. **Source:** `Metro 112 -  Vivian H. Bellevue, WA - Feb 22, 2018.txt` (complex: Metro 112, 588 chars)
   > I started with things I really like: 1. Fantastic location 2. Friendly staff and responsive maintenance team 3. Helped receiving packages ... Things I don't like: 1. The walls in between are incredibly thin (no insulation) and not sound proof at all.

3. **Source:** `Meydenbauer Avalon, Current Resident 154444 Resident • 2013 - Jun 13, 2013.txt` (complex: Avalon Meydenbauer, 553 chars)
   > As others have said, Noisy building. I can hear my neighbors TV, people in the hall way, keys rattling.. etc.. On the bright side I can always find a parking spot and it feels very safe to walk around. Great location next to the mall ... Inside the apartment the paint is chipped, the materials used is cheap, the walls are thin ... I don't think there is AC in this building..

4. **Source:** `Surrey on the Main - Utopi D. San Francisco, CA - Apr 13, 2026.txt` (complex: Surrey on the Main, 563 chars)
   > Beyond the initial move-in period, ~20 days for full residency, the front office once their commission and online reviews have been collected, do not make the best effort to reply to residents for potentially problematic, non-maintenance issues often citing prioritization as the reasoning for delays or non-response. ...

5. **Source:** `Metro 112 - Summer C. Bellevue, WA - Sep 28, 2019.txt` (complex: Metro 112, 463 chars)
   > You spend a lot of time week to week interacting with the Metro 112 staff, and you used to feel like you're part of this big family, but it's feeling less and less so. I tend to avoid visiting the office if Brittany's the only one there ... If Brittany's the one that lead you on your apartment tour, I would recommend doing another tour with Kim or Julia! This is an otherwise nice place to live.

Each chunk is a complete, standalone thought — readable on its own, with no fragments or HTML artifacts.

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` (384-dim), with embeddings normalized and stored in a persistent **ChromaDB** collection (`chroma_db/`) using **cosine** distance. Retrieval is top-k = 4 (`retrieve()` in `embed.py`), with an optional `complex_filter` that restricts results to a single complex via Chroma metadata — used for single-complex questions to prevent cross-property bleed. Chosen because it runs locally with no API key or rate limits, is fast, and is a strong general-purpose encoder for short, opinionated review text.

**Production tradeoff reflection:** If cost weren't a constraint and this served real renters, I'd weigh: **accuracy on domain-specific text** — a larger model like `all-mpnet-base-v2` (768-dim) or a hosted API (OpenAI `text-embedding-3-large`, Voyage, Cohere) would better capture nuance in mixed praise/complaint reviews and sarcasm; **context length** — MiniLM truncates ~256 tokens, fine for 600-char chunks but limiting if I ingested long-form posts; **multilingual support** — a multilingual model (`paraphrase-multilingual-MiniLM-L12-v2`) would handle non-English reviews without a translation step; and **latency** — MiniLM embeds the query in a few ms locally, whereas a hosted API adds a network round-trip per query, which matters for an interactive UI. I'd likely keep a small local model for query embedding and reserve a heavier model only if retrieval quality demanded it.

### Retrieval test examples

Three queries run through `retrieve()`, showing the top returned chunks and their cosine distances (lower = closer match):

**Example 1 — Query: "Do reviewers report parking as a problem at Metro 112?"** *(filtered to Metro 112)*
| # | Distance | Source | Chunk (excerpt) |
|---|----------|--------|-----------------|
| 1 | **0.392** | Metro 112 – Vivian H. | "...they had to open the door and let all the cars get in and out. The problems is many cars don't pay parking are still parking inside. They didn't tow them away..." |
| 2 | 0.545 | Metro 112 – Vivian H. | "We reported this issue to Metro 112 more than 4 times but never get resolved..." |

*Why these are relevant:* The top chunk is directly on-topic — it describes the specific parking problem (a broken garage door letting non-paying cars in) the query asks about, from the correct complex. It's not a keyword coincidence: the chunk never uses the word "problem," yet the embedding matched the *meaning* of "parking issue," which is exactly the semantic match we want.

**Example 2 — Query: "Which apartments have thin walls or noise problems from neighbors?"** *(open, no filter)*
| # | Distance | Source | Chunk (excerpt) |
|---|----------|--------|-----------------|
| 1 | **0.382** | Avalon Meydenbauer (2013) | "As others have said, Noisy building. I can hear my neighbors TV, people in the hall way, keys rattling..." |
| 2 | **0.406** | Metro 112 – Vivian H. | "Our bedroom is next to our neighbor's living room and I can hear very clearly what they are watching when I was on my bed..." |

*Why these are relevant:* Both top hits describe hearing neighbors through walls — the exact concept queried — and they correctly come from **two different complexes**, which is what a cross-complex question needs. The query word "thin walls" semantically matches "I can hear my neighbors" even though the wording differs, showing the embedding captures meaning over surface tokens.

**Example 3 — Query: "How reliable is the pricing and rent at Metro 112?"** *(filtered to Metro 112)*
| # | Distance | Source | Chunk (excerpt) |
|---|----------|--------|-----------------|
| 1 | **0.328** | Metro 112 – Vivian H. | "They refused to give any promotion to loyal customers who paid all the rent on time... the rent was given by system." |
| 2 | 0.359 | Metro 112 – Vivian H. | "We reported this issue to Metro 112 more than 4 times but never get resolved..." |

This was the strongest match of the three (0.328) — the retrieved chunk is squarely about Metro 112's pricing/rent reliability, the subject of the query.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:** Generation runs on Groq's `llama-3.3-70b-versatile` at `temperature=0` (`query.py`). The system prompt enforces grounding with explicit, numbered rules rather than a suggestion: (1) *"Use only the information in the CONTEXT below. Do not use any outside or prior knowledge about these apartments, the city, or apartments in general."* (2) *"If the context does not contain enough information to answer the question, reply with exactly: 'I don't have enough information on that.' Do not guess or fill gaps from general knowledge."* (3) attribute every claim to the complex it came from and never blend complaints across complexes; (4) say so when only one review supports a claim. The retrieved chunks are passed in a numbered CONTEXT block, each labeled with its complex, source file, and platform, so the model has the attribution data inline.

**How source attribution is surfaced in the response:** Two layers. (a) The model is instructed to attribute claims to the named complex in its prose ("Metro 112 reviewers say…"). (b) More importantly, the **source list is built programmatically** from the retrieved chunks' metadata (`source_list()` in `query.py`) — one deduplicated entry per source file naming the reviewer (`Complex — reviewer`, e.g. "Metro 112 — Vivian H.") — so attribution does not depend on the model remembering to cite. When the model declines (out-of-corpus question), the source list is suppressed so unused reviews aren't misleadingly cited. The Gradio UI shows the answer and this "Retrieved from" list in separate fields. *Known tradeoff:* the list reflects what was **retrieved** (top-k), which can include a chunk the answer didn't ultimately draw on.

### Example responses with source attribution

**Example A — Query: "Is parking a problem at Metro 112?"**
> **Answer:** Metro 112 reviewer Vivian H. says that many cars don't pay for parking but are still allowed to park inside, and that Metro 112 didn't tow them away despite claiming to do so. Vivian H. also mentions parking fees were waived at one point but charged again on renewal. One reviewer, Vivian H., notes that parking is a problem at Metro 112.
>
> **Retrieved from:**
> • Metro 112 — Vivian H. Bellevue, WA

Every claim is attributed to the named reviewer (Vivian H.) and traces to the cited Metro 112 review; nothing comes from general knowledge.

**Example B — Query: "What do reviewers say about pricing at Metro 112?"**
> **Answer:** Metro 112 reviewer Vivian H. says the pricing system is not reliable and makes them doubt the prices. They note that a room they wanted was "rented out," but an identical floor plan was offered for $100 more, which they found unacceptable; staff said the price was "given by their system." Vivian H. also describes a later rent increase of over $200 and parking fees no longer being waived. These pricing issues are noted by one reviewer, Vivian H.
>
> **Retrieved from:**
> • Metro 112 — Vivian H. Bellevue, WA

### Out-of-scope query (refusal)

**Query: "Are there any pet-friendly apartments in Seattle?"** (the corpus only covers Bellevue complexes)
> **Answer:** I don't have enough information on that.
>
> **Retrieved from:** *(none — the reviews didn't cover this question)*

The system declines instead of fabricating a plausible answer from the model's training knowledge — the grounding rules force a refusal when the retrieved context doesn't support an answer.

---

## Query Interface

The interface is a **Gradio web app** (`app.py`), launched with `python app.py` and opened at `http://localhost:7860`.

**Input / control fields (Ask tab):**
- *Your question* (text box) — a free-text question; submit with the **Ask** button or Enter.
- *Try an example* (dropdown) — picks a ready-made question (incl. an out-of-corpus one) and fills the box.
- *Filter by complex* (dropdown) — metadata filter; scope retrieval to one complex or "All complexes".
- *Filter by source* (dropdown) — metadata filter; scope to Yelp, ApartmentRatings, or all.
- *Retrieval method* (radio) — `semantic` (dense) or `hybrid` (semantic + BM25); stretch feature.
- *Reviews from year / to year* (sliders) — metadata date filter on the review date.
- A **🌗 Light / Dark** toggle (top-right) and Gradio's footer **Settings** both switch theme.
- A second **Chat (with memory)** tab provides the multi-turn conversational mode.

**Output fields:**
- *Answer* (text box) — the grounded, generated answer.
- *Retrieved from* (text box) — the deduplicated list of sources, naming the reviewer (`Complex — reviewer`), or a "no sources" note when the system declines.
- *Retrieved chunks* (collapsible) — the raw retrieved chunks with their distance/score and review date, for transparency.

**Sample interaction transcript:**
```
Your question:  How responsive is maintenance at The Bravern?

[Ask]

Answer:
The Bravern reviewer Will M. says that maintenance staff — specifically
Mariano, Gene, and Shawn — are "awesome" and when issues arise they arrive
within 30 minutes and resolve the problem. This is noted by one reviewer,
Will M.

Retrieved from:
• The Bravern — Will M. Kirkland, WA
• The Bravern — Emily W. Portland, OR
```

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | Which review platforms have reviews for Avalon Meydenbauer, and how many total? | Yelp (2) + ApartmentRatings (3) = **5** | Named both platforms correctly, but counted only **3** total (top distances 0.58–0.70) | Off-target | **Inaccurate** (undercounted) |
| 2 | Do reviewers report parking as a problem at Metro 112? | Yes — garage door breaks, unpaid cars not towed | "Yes" — many cars don't pay yet park inside and aren't towed; parking-fee waiver later dropped. Cited Metro 112 only (top dist 0.392) | Relevant | **Accurate** |
| 3 | Which complex has noise issues — The Bravern or Metro 112? | Metro 112 (thin walls; Vivian H. hears neighbors) | Reported **The Bravern** has noise and "no information about Metro 112" — missed Metro 112's documented thin-wall complaints | Partially relevant | **Partially accurate** (honest about its context, but missed the in-corpus Metro 112 noise chunk; see Failure Case) |
| 4 | Surrey on the Main — what specific issue does the reviewer name? | Miscommunication on maintenance timing between staff/front office/residents | "I don't have enough information on that." | Off-target | **Inaccurate** (declined though the info exists; see Failure Case) |
| 5 | Which complex(es) are credited with fast/same-day maintenance? | The Bravern (issues fixed within 30 min) | The Bravern — maintenance resolves issues "within 30 minutes" (named staff); noted Metro 112 calls its team "responsive" without specifics | Relevant | **Accurate** |

**Out-of-corpus control (bonus):** *"Which apartments in Kirkland do reviewers recommend?"* → "I don't have enough information on that." (no sources). **Accurate** — correctly declines rather than fabricating.

**Summary:** 2 accurate (Q2, Q5) + correct refusal on the control; 1 partially accurate (Q3); 2 inaccurate (Q1, Q4). The two clean wins are grounded, attributed, and hedge appropriately; the three misses are all explained below and trace to known limits of top-k semantic retrieval on a small corpus, not to ungrounded hallucination — in every case the system either answered from real review text or declined, and never invented facts.

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:** Q3 — *"Which complex do reviewers describe as having noise issues, The Bravern or Metro 112?"*

**What the system returned (confidently wrong):** It answered about **Avalon Meydenbauer** (which the question never mentioned) and stated that **Metro 112 does not mention noise** — which is false. Metro 112's Vivian H. review explicitly says the walls are *"incredibly thin (no insulation) and not sound proof,"* and that *"I can hear very clearly what they are watching."* The answer sounds authoritative but is wrong about the corpus.

**Root cause (tied to a specific pipeline stage): the retrieval stage, not generation.** Two compounding effects:

1. **Comparison queries break single-vector retrieval.** The question is relational — "compare A vs B on X." A dense retriever embeds the *whole* query into one vector dominated by the two complex names + "noise," and that vector lands far from a narrow first-person anecdote like *"Our bedroom is next to our neighbor's living room…"* That Metro 112 noise chunk sits at cosine distance **0.655 — rank #7**, below the `k=4` cutoff, so it never reaches the LLM. **Proof it's the phrasing, not the data:** rephrasing to the bare concept *"thin walls, can hear neighbors TV and noise"* pulls the exact same chunk to **rank #1 (0.446)**.
2. **Cross-property bleed.** Retrieval matches the "noise" concept across *all* complexes, so Avalon's emphatic *"Noisy building. I can hear my neighbors TV"* — the strongest literal noise statement in the whole corpus — outranks Metro 112's, even though the question named only Bravern and Metro 112.

The net effect: the LLM's top-4 context was two Bravern chunks and two Avalon chunks (including Avalon's emphatic *"Noisy building. I can hear my neighbors TV"*) — and **not a single Metro 112 chunk**. The two nearest Metro 112 chunks, a *garage/parking* one (rank #6, no noise) and the thin-walls noise chunk (rank #7), both fell just below the `k=4` cutoff. Grounded faithfully in *that* context, the model described Avalon's noise and concluded nothing supported a Metro 112 noise complaint — a faithful reading of a mis-retrieved context. **Generation behaved correctly; retrieval served the wrong chunks.**

**What you would change to fix it:** (1) **Per-complex retrieval for comparison questions** — detect the named complexes and run a separate top-k for each, then merge, so each side is represented (the right architecture for "compare A vs B"). (2) **Query decomposition** — split "compare A and B on X" into "A on X" + "B on X" before retrieving. (3) **Use the `complex_filter`** already built into `retrieve()` to scope each side. (4) **Retrieve more then threshold** (k=8–10) and/or a **stronger embedding model** (`all-mpnet-base-v2`) to lift narrow anecdotes above the cutoff.

*Second instance (a refusal rather than a wrong answer):* Q4 — *"In the Surrey on the Main review, what specific building feature or issue does the reviewer name?"* — returns *"I don't have enough information,"* although the Surrey review names front-office non-responsiveness. Same family of cause: Surrey has only 2 chunks (thin representation) and the abstract phrase "building feature or issue" embeds far from the review's concrete wording, so both Surrey chunks (~0.73–0.79) fall below the `k=4` cutoff and never reach the model.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:** Because planning.md pinned down concrete numbers and tools up front — 600-char chunks with 80-char overlap, `all-MiniLM-L6-v2`, top-k = 4, ChromaDB with cosine distance — the implementation was a direct translation of the spec rather than a series of guesses. `chunk_text()` and `retrieve()` were written straight to those parameters, and the Evaluation Plan questions doubled as acceptance tests: I knew retrieval was working when the parking and pricing queries returned the right Metro 112 chunks at low distances. The Anticipated Challenges section also paid off — "cross-property bleed" was called out in planning, so I built a `complex_filter` into retrieval before I'd even seen the problem occur.

**One way your implementation diverged from the spec, and why:** The spec described chunking as a fixed 600-character split, but the implementation does **boundary-aware** chunking — it packs whole *sentences* up to a 600-char budget with sentence-level overlap, instead of slicing at exactly 600 characters. I changed this after inspecting early output: a raw character split cut words in half and, worse, fragmented the numbered lists in the Metro 112 review (e.g. turning "1. Fantastic location" into a "1." fragment), which would have produced meaningless embeddings. A second, smaller divergence: the generation model moved from "Claude" in early planning drafts to Groq's `llama-3.3-70b-versatile`, to match the starter repo's free-tier, no-credit-card stack.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1 — Tightening the evaluation questions**

- *What I gave the AI:* My draft Evaluation Plan from planning.md, with questions like "What do reviewers say about management at Avalon Meydenbauer?" and "What is the overall sentiment toward Surrey on the Main?"
- *What it produced:* Claude flagged that three of my questions had **subjective** expected answers (sentiment/recommendations) that couldn't be graded right-or-wrong, and rewrote them into fact-typed questions with objective answers — a yes/no on parking, a named complex for noise, a specific named issue for Surrey, a count for Avalon.
- *What I changed or overrode:* I kept the rewrites but added a sixth **out-of-corpus control** question (Kirkland apartments) specifically to test that the system declines instead of hallucinating. The AI initially left placeholders for the exact answers (Yelp/ApartmentRatings blocked automated fetching), so I filled in the verifiable answers myself from the source reviews after the pipeline was running — e.g. confirming Metro 112's garage door is "always broken" and the Surrey issue is front-office non-responsiveness.

**Instance 2 — Ingestion, the PDF, and the chunker**

- *What I gave the AI:* My `documents/` folder (10 hand-copied `.txt` reviews plus an experimental `thebravern.pdf`) and the Chunking Strategy section, and asked it to build the loader and chunker.
- *What it produced:* Claude inspected the PDF, found all 12 pages were **image-only with zero extractable text**, and recommended excluding it rather than adding OCR; it then wrote a boundary-aware chunker with keyword-based complex detection (instead of parsing my inconsistent filenames).
- *What I changed or overrode:* I accepted excluding the PDF and keeping the corpus to the 10 `.txt` reviews. When the chunk count came out at 28 — below the milestone's 50+ guideline — I directed that we keep the 600-char size rather than shrink it to game the count, since the corpus is genuinely small (~13 KB) and the size fits the content; I noted the reasoning in planning.md and the README instead.

---

## Stretch Features

### 1. Hybrid search (BM25 + semantic) — `hybrid.py`

**Approach:** Lexical **BM25** (`rank_bm25`) and dense **semantic** (cosine over `all-MiniLM-L6-v2`) each score all 28 chunks. Each score set is **min-max normalized to [0, 1]**, then fused as `hybrid = 0.5·semantic + 0.5·bm25`. BM25 rewards exact term overlap (complex names, "parking", staff names); semantic rewards paraphrase. Run `python hybrid.py` to reproduce the comparison; the UI's **Ask** tab also has a semantic/hybrid toggle.

**Comparison on 3 queries** (top-1 shown; scores normalized):

| Query | Semantic top-1 | BM25 top-1 | Hybrid top-2 | Winner |
|-------|----------------|------------|--------------|--------|
| "Mariano in maintenance" | Bravern maintenance chunk | Same | Same | tie — exact name, all agree |
| "Is it hard to hear neighbors through the walls?" | Metro 112 "bedroom next to neighbor's living room" (sem 1.00) | Avalon "Noisy building... hear my neighbors TV" (bm25 1.00) | **Both** of those chunks | **Hybrid** — surfaces the concept match *and* the keyword match |
| "Brittany at the Metro 112 office" | Metro 112 Brittany chunk | Same | Same | tie — proper noun, all agree |

**Which performed better:** On the noise query the methods **disagreed**, and that's the informative case: semantic alone missed Avalon's literal "hear my neighbors" chunk, and BM25 alone ranked the keyword-heavy Avalon chunk above Metro 112's more descriptive one. **Hybrid returned both** in its top-2, combining each method's strength. On the two proper-noun queries all three agreed, because exact names are where lexical and semantic signals coincide — so hybrid costs nothing there and helps when wording diverges.

### 2. Chunking-strategy comparison — `chunk_compare.py`

Compared the project's **boundary-aware 600/80** chunker against a **mechanical fixed-character 300/50** split on the same queries (`python chunk_compare.py`):

| | Strategy A: boundary-aware 600/80 | Strategy B: fixed 300/50 |
|---|-----------------------------------|--------------------------|
| Chunks | 28 | 56 |
| Complete (end on sentence punctuation) | **28 / 28** | **12 / 56** |
| "parking problem at Metro 112" | dist **0.321**, *complete* chunk | dist 0.368, **fragment** ("e door and let all the cars...") |
| "thin walls / hear neighbors" | dist 0.436, *complete* | dist 0.437, **fragment** ("ation) and not sound proof...") |
| "fast maintenance at The Bravern" | dist 0.609, *complete* | dist 0.556, **fragment** (matched an off-topic move-out chunk) |

**Which is better and why:** **Strategy A.** The mechanical 300/50 split produces mostly fragments (only 12/56 chunks are complete thoughts) — chunks start mid-word, which makes them unreadable as context for the LLM. Even where Strategy B posts a marginally lower distance (the maintenance query, 0.556 vs 0.609), it does so by matching an **off-topic fragment** about moving out, *not* the "within 30 minutes" maintenance content — so the lower distance is misleading and would produce worse grounding. Strategy A keeps every chunk a complete, citable thought, which is what grounded generation needs.

### 3. Metadata filtering — `retrieve(query, complex_filter=..., platform_filter=..., date_min=..., date_max=...)`

Retrieval supports ChromaDB `where` filters on three metadata fields — **`complex`** (equality), **`source_platform`** (Yelp / ApartmentRatings), and **`date_int`** (a sortable YYYYMMDD review date, range-filtered with `$gte`/`$lte`). The **Ask** tab exposes all three: a complex dropdown, a source dropdown, and a "from year / to year" pair of sliders. Multiple constraints are combined with `$and` (`build_where()` in `embed.py`).

**Complex filter** — visible effect for query *"Where can I always find a parking spot?"*:

| Filter | Top results (complex) |
|--------|-----------------------|
| **None** | Avalon Meydenbauer (0.692), Avalon (0.692), Avalon (0.704), Metro 112 (0.718) |
| **complex = "Metro 112"** | Metro 112 ×4 — Avalon chunks excluded |
| **complex = "The Bravern"** | The Bravern ×4 — only Bravern chunks |

**Date filter** — the review date is parsed from each filename (e.g. `… - Feb 22, 2018.txt`) into metadata. Visible effect for query *"What do reviewers say about staff and maintenance?"*:

| Filter | Top results (date · complex) |
|--------|------------------------------|
| **from 2020** (`date_min=20200101`) | 2026-04-13 Surrey, 2025-12-19 The Bravern — only recent reviews |
| **before 2015** (`date_max=20141231`) | 2010-12-22 Avalon, 2011-01-22 Avalon — only older reviews |

The date filter directly addresses planning.md's "stale reviews" risk: a user can now scope answers to recent reviews only, instead of blending a 2010 review with a 2026 one.

**Source filter** — `source_platform = "ApartmentRatings"` returns only the three Avalon ApartmentRatings reviews; `"Yelp"` returns only Yelp reviews. Useful for comparing how the two platforms' reviews differ.

> **Note on hybrid + filters:** the BM25 tokenizer removes English stopwords (and ultra-generic review words like "problem/issue") so a chunk can't rank highly just for sharing common words. This fixed a case where *"Is parking a problem at Metro 112?"* pulled an unrelated Avalon chunk that merely contained "problems" — after the fix, all top results are on-topic Metro 112 chunks.

### 4. Conversational memory — `Conversation` in `query.py`

Multi-turn chat (UI **Chat** tab). Before retrieval, a follow-up is rewritten into a standalone query using prior turns; if the rewrite names exactly one complex, retrieval is auto-scoped to it (reusing feature #3). Recorded 2-turn exchange:

```
USER:      Is parking a problem at Metro 112?
ASSISTANT: Metro 112 reviewers say parking is a problem — many cars don't pay yet
           park inside and aren't towed; a parking-fee waiver was later dropped.

USER:      What about noise there?
           (resolved to: "What about noise at the Metro 112 apartment complex?")
ASSISTANT: Metro 112 reviewers say there are noise issues — one can hear neighbors'
           TV, conversations, even the microwave "ding"; neighbors throw weekend
           parties. It improved after complaints but persists on quiet nights.
```

Turn 2 contains no complex name — "there" only resolves to Metro 112 by carrying context from turn 1. The rewrite (shown in the transcript) is the visible proof the memory was used, not topic coincidence, and the answer is correctly grounded in Metro 112's reviews.
