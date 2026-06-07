"""
Milestone 5 + stretch features — Query interface (Gradio).

Two tabs:
  • Ask        — single-shot grounded Q&A, with a complex metadata filter and a
                 semantic/hybrid retrieval toggle, plus a panel showing the
                 retrieved chunks and their scores.
  • Chat       — multi-turn conversation with memory (follow-ups like
                 "what about noise there?" resolve against earlier turns).

    python app.py
    # then open http://localhost:7860
"""

from __future__ import annotations

import base64
from pathlib import Path

import gradio as gr

from query import ask, Conversation

# Embed the favicon directly in <head> as a data URI so it shows in the browser
# tab regardless of how the Gradio version serves favicon_path.
_FAV = Path(__file__).parent / "favicon.png"
HEAD = ""
if _FAV.exists():
    _b64 = base64.b64encode(_FAV.read_bytes()).decode()
    HEAD = f'<link rel="icon" type="image/png" href="data:image/png;base64,{_b64}">'

COMPLEXES = ["All complexes", "The Bravern", "Metro 112",
             "Surrey on the Main", "Avalon Meydenbauer"]
PLATFORMS = ["All platforms", "Yelp", "ApartmentRatings"]

MIN_YEAR, MAX_YEAR = 2008, 2026  # span of review dates in the corpus

EXAMPLE_QS = [
    "Is parking a problem at Metro 112?",
    "Which complex has thin walls or noise from neighbors?",
    "How responsive is maintenance at The Bravern?",
    "What do reviewers say about pricing and rent increases?",
    "Which apartments in Kirkland do reviewers recommend?",
]

# Toggle light/dark by reloading with Gradio's ?__theme query param.
THEME_TOGGLE_JS = """() => {
  const u = new URL(window.location.href);
  const cur = u.searchParams.get('__theme');
  u.searchParams.set('__theme', cur === 'dark' ? 'light' : 'dark');
  window.location.href = u.href;
}"""


def _year_bounds(from_year: int, to_year: int):
    """Convert UI year sliders to YYYYMMDD date_min/date_max (None if full span)."""
    lo, hi = int(min(from_year, to_year)), int(max(from_year, to_year))
    date_min = None if lo <= MIN_YEAR else lo * 10000 + 101
    date_max = None if hi >= MAX_YEAR else hi * 10000 + 1231
    return date_min, date_max


def _format_chunks(chunks: list[dict]) -> str:
    """Render retrieved chunks with their score for the transparency panel."""
    lines = []
    for i, c in enumerate(chunks, 1):
        if "distance" in c:          # semantic retrieval
            metric = f"distance={c['distance']:.3f}"
        else:                         # hybrid retrieval
            metric = f"score={c['score']:.3f} (sem={c['sem']:.2f} bm25={c['bm25']:.2f})"
        date = c.get("date", "?")
        lines.append(f"{i}. [{c['complex']} · {date}] {metric}\n   {c['text'][:160]}...")
    return "\n\n".join(lines) if lines else "(no chunks retrieved)"


# --- Tab 1: Ask -------------------------------------------------------------
def handle_query(question: str, complex_choice: str, method: str,
                 from_year: int, to_year: int, platform_choice: str):
    question = (question or "").strip()
    if not question:
        return "Please enter a question.", "", ""

    cflt = None if complex_choice == "All complexes" else complex_choice
    pflt = None if platform_choice == "All platforms" else platform_choice
    date_min, date_max = _year_bounds(from_year, to_year)
    result = ask(question, complex_filter=cflt, method=method,
                 date_min=date_min, date_max=date_max, platform_filter=pflt)

    answer = result["answer"]
    sources = ("\n".join(f"• {s}" for s in result["sources"])
               if result["sources"]
               else "(No sources — no reviews match your filters / question.)")
    return answer, sources, _format_chunks(result["chunks"])


# --- Tab 2: Chat (conversational memory) ------------------------------------
def chat_respond(message: str, history: list, convo: Conversation | None):
    message = (message or "").strip()
    if not message:
        return history, convo, ""
    if convo is None:
        convo = Conversation()

    result = convo.ask(message)
    reply = result["answer"]
    if result["standalone_question"] != message:
        reply = f"*(resolved to: “{result['standalone_question']}”)*\n\n{reply}"
    if result["sources"]:
        reply += "\n\n**Retrieved from:**\n" + "\n".join(
            f"• {s}" for s in result["sources"])

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]
    return history, convo, ""


def reset_chat():
    return [], None, ""


# --- Look & feel ------------------------------------------------------------
THEME = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="blue",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
).set(
    body_background_fill="*neutral_50",
    block_border_width="1px",
    block_shadow="0 1px 3px rgba(0,0,0,0.06)",
    block_radius="14px",
)

CSS = """
.gradio-container {max-width: 980px !important; margin: 0 auto !important;}
#hero {
    background: linear-gradient(120deg, #4f46e5 0%, #2563eb 60%, #0ea5e9 100%);
    color: #fff; border-radius: 18px; padding: 26px 30px; margin-bottom: 14px;
    box-shadow: 0 8px 24px rgba(79,70,229,0.25);
}
#hero h1 {margin: 0 0 6px 0; font-size: 1.7rem; font-weight: 800; color:#fff;}
#hero p {margin: 0; opacity: 0.92; font-size: 0.98rem; color:#eef;}
#hero .pills {margin-top: 12px;}
#hero .pill {
    display:inline-block; background: rgba(255,255,255,0.18); color:#fff;
    border-radius: 999px; padding: 3px 12px; margin: 3px 6px 0 0; font-size: 0.8rem;
}
.answer-box textarea {font-size: 1.02rem !important; line-height: 1.5 !important;}
#toolbar {justify-content: flex-end; gap: 6px; margin-bottom: 4px;}
"""

HERO = """
<div id="hero">
  <h1>🏢 The Unofficial Guide — Bellevue Apartments</h1>
  <p>Honest renter experiences, answered <b>only</b> from resident reviews — with the source reviewer cited every time.</p>
  <div class="pills">
    <span class="pill">The Bravern</span>
    <span class="pill">Metro 112</span>
    <span class="pill">Surrey on the Main</span>
    <span class="pill">Avalon Meydenbauer</span>
  </div>
</div>
"""

with gr.Blocks(title="The Unofficial Guide — Bellevue Apartments",
               theme=THEME, css=CSS, head=HEAD) as demo:
    with gr.Row(elem_id="toolbar"):
        theme_btn = gr.Button("🌗 Light / Dark", size="sm", scale=0)
    gr.HTML(HERO)

    with gr.Tab("🔎  Ask"):
        with gr.Group():
            with gr.Row():
                inp = gr.Textbox(label="Your question", show_label=False,
                                 placeholder="Ask about parking, noise, maintenance, pricing…",
                                 scale=5, container=False)
                btn = gr.Button("Ask  ↵", variant="primary", scale=1)
            example_dd = gr.Dropdown(EXAMPLE_QS, label="💡  Try an example",
                                     value=None, interactive=True)
            with gr.Row():
                complex_dd = gr.Dropdown(COMPLEXES, value="All complexes",
                                         label="🏷️  Filter by complex")
                platform_dd = gr.Dropdown(PLATFORMS, value="All platforms",
                                          label="🌐  Filter by source")
                method_radio = gr.Radio(["semantic", "hybrid"], value="semantic",
                                        label="⚙️  Retrieval method")
            with gr.Row():
                from_year = gr.Slider(MIN_YEAR, MAX_YEAR, value=MIN_YEAR, step=1,
                                      label="📅  Reviews from year")
                to_year = gr.Slider(MIN_YEAR, MAX_YEAR, value=MAX_YEAR, step=1,
                                    label="📅  Reviews to year")

        answer = gr.Textbox(label="💬  Answer", lines=7, elem_classes="answer-box")
        sources = gr.Textbox(label="📎  Retrieved from", lines=2)
        with gr.Accordion("🔍  Retrieved chunks (with scores + date)", open=False):
            chunks_box = gr.Textbox(show_label=False, lines=8, container=False)

        ask_inputs = [inp, complex_dd, method_radio, from_year, to_year, platform_dd]
        outs = [answer, sources, chunks_box]
        btn.click(handle_query, ask_inputs, outs)
        inp.submit(handle_query, ask_inputs, outs)
        # Selecting an example fills the question box.
        example_dd.change(lambda q: q or "", example_dd, inp)

    with gr.Tab("💬  Chat (with memory)"):
        gr.Markdown(
            "Multi-turn chat — ask a follow-up like *“what about noise there?”* and "
            "it resolves against the previous turn (the resolved query is shown in the reply)."
        )
        convo_state = gr.State(None)
        chatbot = gr.Chatbot(height=420, label="Conversation",
                             avatar_images=(None, "🏢"),
                             placeholder="Ask about a complex, then ask a follow-up…")
        with gr.Group():
            with gr.Row():
                chat_in = gr.Textbox(show_label=False, container=False, scale=5,
                                     placeholder="e.g. Is parking a problem at Metro 112?")
                send = gr.Button("Send", variant="primary", scale=1)
        clear = gr.Button("🗑  Clear conversation", size="sm")

        send.click(chat_respond, [chat_in, chatbot, convo_state],
                   [chatbot, convo_state, chat_in])
        chat_in.submit(chat_respond, [chat_in, chatbot, convo_state],
                       [chatbot, convo_state, chat_in])
        clear.click(reset_chat, outputs=[chatbot, convo_state, chat_in])

    theme_btn.click(fn=None, inputs=None, outputs=None, js=THEME_TOGGLE_JS)


if __name__ == "__main__":
    demo.launch(favicon_path=str(_FAV) if _FAV.exists() else None)
