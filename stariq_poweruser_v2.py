"""
StarIQ Power User Guide — 3-page PDF (v2)
Each cell's height is calculated from its actual content; no overflow.

Page 1 — Model Mastery & Prompting
Page 2 — Knowledge Bases, RAG & Workspace
Page 3 — RBAC, Docs, Governance, Roadmap & Troubleshooting
"""

import math, os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

# ── Palette ───────────────────────────────────────────────────────────────
GOLD      = HexColor("#FFB81C")
ORANGE    = HexColor("#FF6200")
BLACK     = HexColor("#0D0D0D")
WHITE     = HexColor("#FFFFFF")
CREAM     = HexColor("#FFFDF7")
GOLD_TINT = HexColor("#FFF5D6")
MID       = HexColor("#4A4A4A")
SOFT      = HexColor("#888888")
DARK_BG   = HexColor("#1A1A1A")
RULE      = HexColor("#E0D0A0")
BLUE      = HexColor("#1565C0")
GREEN     = HexColor("#1D6B3E")
RED       = HexColor("#A52A2A")
AMBER     = HexColor("#CC6600")

# ── 8pt grid constants ────────────────────────────────────────────────────
U        = 8
W, H     = letter          # 612 × 792
MARGIN   = 5 * U           # 40 pt
GUTTER   = 2 * U           # 16 pt
PAD      = 2 * U           # 16 pt  (inside cells)
CW       = W - 2 * MARGIN  # 532 pt  usable content width
SC       = (CW - GUTTER) // 2   # 258 pt  each half-column

HEADER_H = 10 * U   # 80 pt
STRIPE_H =  1 * U   #  8 pt
FOOTER_H =  6 * U   # 48 pt
# Usable body height per page
BODY_H   = H - HEADER_H - STRIPE_H - FOOTER_H   # 656 pt


# ── Drawing primitives ────────────────────────────────────────────────────
def rr(cv, x, y, w, h, r=6, fill=WHITE, stroke=None, sw=0.5):
    """Rounded rectangle."""
    p = cv.beginPath()
    p.moveTo(x+r, y); p.lineTo(x+w-r, y)
    p.arcTo(x+w-r, y, x+w, y+r, -90, 90); p.lineTo(x+w, y+h-r)
    p.arcTo(x+w-r, y+h-r, x+w, y+h, 0, 90); p.lineTo(x+r, y+h)
    p.arcTo(x, y+h-r, x+r, y+h, 90, 90); p.lineTo(x, y+r)
    p.arcTo(x, y, x+r, y+r, 180, 90); p.close()
    cv.setFillColor(fill)
    if stroke:
        cv.setStrokeColor(stroke); cv.setLineWidth(sw)
    cv.drawPath(p, fill=1, stroke=bool(stroke))


def wrap_text(cv, text, x, y, max_w, font="Helvetica", size=8.5,
              color=MID, lh=None):
    """Draw wrapped paragraph; return y after last line."""
    if lh is None:
        lh = round(size * 1.4)
    cv.setFont(font, size)
    cv.setFillColor(color)
    for raw in text.split("\n"):
        words = raw.split()
        if not words:
            y -= lh * 0.5
            continue
        buf = []
        for word in words:
            if cv.stringWidth(" ".join(buf + [word]), font, size) <= max_w:
                buf.append(word)
            else:
                if buf:
                    cv.drawString(x, y, " ".join(buf))
                    y -= lh
                buf = [word]
        if buf:
            cv.drawString(x, y, " ".join(buf))
            y -= lh
    return y


def divider(cv, x, y, w, color=RULE):
    cv.setStrokeColor(color); cv.setLineWidth(0.5)
    cv.line(x, y, x + w, y)


def section_label(cv, text, x, y, w, bg=GOLD, fg=BLACK):
    """Gold label bar; returns y below it."""
    rr(cv, x, y, w, 16, r=3, fill=bg)
    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(fg)
    cv.drawString(x + 6, y + 4, text.upper())
    return y - 10


def pill(cv, text, x, y, bg=GOLD, fg=BLACK, font_size=7.5):
    """Inline pill badge; returns width of pill."""
    tw = cv.stringWidth(text, "Helvetica-Bold", font_size)
    pw = tw + 10
    rr(cv, x, y - 2, pw, 14, r=3, fill=bg)
    cv.setFont("Helvetica-Bold", font_size); cv.setFillColor(fg)
    cv.drawString(x + 5, y + 2, text)
    return pw


def circle_badge(cv, label, cx, cy, r=9, bg=GOLD, fg=BLACK):
    cv.setFillColor(bg); cv.circle(cx, cy, r, fill=1, stroke=0)
    cv.setFillColor(fg); cv.setFont("Helvetica-Bold", 8)
    cv.drawCentredString(cx, cy - 3, label)


def flagstar_logo(cv, x, y, star_col=GOLD, text_col=WHITE):
    cx, cy = x + 9, y + 7
    cv.setFillColor(star_col)
    ro, ri = 8, 2.5
    p = cv.beginPath()
    for i in range(8):
        ang = math.pi / 4 * i - math.pi / 2
        r_ = ro if i % 2 == 0 else ri
        px_, py_ = cx + r_ * math.cos(ang), cy + r_ * math.sin(ang)
        p.moveTo(px_, py_) if i == 0 else p.lineTo(px_, py_)
    p.close(); cv.drawPath(p, fill=1, stroke=0)
    cv.setFillColor(text_col); cv.setFont("Helvetica-Bold", 12)
    cv.drawString(cx + 12, y + 1, "flagstar")


# ── Page chrome (shared header + footer) ─────────────────────────────────
def draw_header(cv, page_num, total_pages, subtitle):
    cv.setFillColor(BLACK)
    cv.rect(0, H - HEADER_H, W, HEADER_H, fill=1, stroke=0)
    # "StarIQ" gold, rest white
    cv.setFillColor(GOLD); cv.setFont("Helvetica-Bold", 22)
    sw = cv.stringWidth("StarIQ", "Helvetica-Bold", 22)
    cv.drawString(MARGIN, H - HEADER_H + 46, "StarIQ")
    cv.setFillColor(WHITE); cv.setFont("Helvetica-Bold", 22)
    cv.drawString(MARGIN + sw + 4, H - HEADER_H + 46, " Power User Guide")
    # Subtitle
    cv.setFillColor(SOFT); cv.setFont("Helvetica-Oblique", 8)
    cv.drawString(MARGIN, H - HEADER_H + 28, subtitle)
    # Page badge
    badge_w = 80
    rr(cv, W - MARGIN - badge_w, H - HEADER_H + 26, badge_w, 20, r=4, fill=GOLD)
    cv.setFillColor(BLACK); cv.setFont("Helvetica-Bold", 8)
    cv.drawCentredString(W - MARGIN - badge_w / 2,
                         H - HEADER_H + 34, f"PAGE {page_num} OF {total_pages}")
    # Logo
    flagstar_logo(cv, W - MARGIN - badge_w - 110, H - HEADER_H + 42)
    # Gold stripe
    cv.setFillColor(GOLD)
    cv.rect(0, H - HEADER_H - STRIPE_H, W, STRIPE_H, fill=1, stroke=0)


def draw_footer(cv):
    cv.setFillColor(DARK_BG)
    cv.rect(0, 0, W, FOOTER_H, fill=1, stroke=0)
    cv.setFillColor(GOLD)
    cv.rect(0, FOOTER_H - 3, W, 3, fill=1, stroke=0)
    items = [
        ("Login", "myapps.microsoft.com", "https://myapps.microsoft.com"),
        ("Resources", "flagstar.sharepoint.com/sites/AI",
         "https://flagstar.sharepoint.com/sites/AI/SitePages/Home.aspx"),
        ("Teams Support", "Join code: g2w1hjy", None),
        ("Exec Guide", "StarIQ at a Glance  →", None),
    ]
    seg = W / len(items)
    for i, (lbl, txt, url) in enumerate(items):
        cx_ = i * seg + seg / 2
        cv.setFont("Helvetica-Bold", 7.5); cv.setFillColor(GOLD)
        cv.drawCentredString(cx_, FOOTER_H - 14, lbl)
        fc = HexColor("#7BBFFF") if url else SOFT
        cv.setFont("Helvetica", 7); cv.setFillColor(fc)
        uw = cv.stringWidth(txt, "Helvetica", 7)
        cv.drawCentredString(cx_, FOOTER_H - 25, txt)
        if url:
            cv.linkURL(url,
                       (cx_ - uw / 2, FOOTER_H - 30, cx_ + uw / 2, FOOTER_H - 18),
                       relative=0)
        if i < len(items) - 1:
            cv.setStrokeColor(HexColor("#333333")); cv.setLineWidth(0.5)
            cv.line((i + 1) * seg, 6, (i + 1) * seg, FOOTER_H - 6)


# ─────────────────────────────────────────────────────────────────────────
#  PAGE 1  —  Model Mastery & Prompting
# ─────────────────────────────────────────────────────────────────────────
def page1(cv):
    draw_header(cv, 1, 4,
        "Model mastery · Token economics · CRAFT prompt framework · "
        "Power techniques · Anti-patterns")

    # Layout: 2 rows, 2 cols
    # Row A (top): Model deep dive (left) | CRAFT Framework (right)  — 328pt
    # Row B (bot): Power Techniques (left) | Anti-patterns + Quick Wins (right) — 304pt
    # Gaps: 2×GUTTER + top/bottom margin within body

    top = H - HEADER_H - STRIPE_H        # 704
    gap_top = GUTTER                      # 16
    ROW_A_H = 328
    ROW_B_H = BODY_H - ROW_A_H - 3 * GUTTER   # 656 - 328 - 48 = 280

    ra_y = top - gap_top - ROW_A_H       # y of bottom of row A
    rb_y = ra_y - GUTTER - ROW_B_H       # y of bottom of row B

    cl = MARGIN          # left col x
    cr = MARGIN + SC + GUTTER  # right col x

    # Cell backgrounds
    rr(cv, cl, ra_y, SC, ROW_A_H, r=8, fill=GOLD_TINT, stroke=RULE, sw=0.8)
    rr(cv, cr, ra_y, SC, ROW_A_H, r=8, fill=WHITE,     stroke=RULE, sw=0.8)
    rr(cv, cl, rb_y, SC, ROW_B_H, r=8, fill=WHITE,     stroke=RULE, sw=0.8)
    rr(cv, cr, rb_y, SC, ROW_B_H, r=8, fill=DARK_BG)

    IW = SC - 2 * PAD   # inner cell width

    # ── A-LEFT: Model deep dive ───────────────────────────────────────────
    iy = ra_y + ROW_A_H - PAD - 2
    iy = section_label(cv, "Model Selection & Token Economics", cl + PAD, iy, IW)
    iy -= 4

    models = [
        ("Haiku",   "Claude 3.5 Haiku", "200K", "Lowest",
         False, False,
         "Fastest. Best for high-volume, simple work: summaries, "
         "classification, extraction, quick Q&A. Use it like an intern "
         "— great throughput, not your deepest thinker."),
        ("Lite",    "Amazon Nova Lite",  "128K", "Very Low",
         False, False,
         "Cheapest option. Ideal for repetitive batch tasks, basic "
         "reformatting, and simple lookups where quality tolerance is high."),
        ("Sonnet",  "Claude 4 Sonnet",  "200K", "Moderate",
         True, False,
         "The default for all knowledge work. Strong reasoning, detailed "
         "writing, code review, policy interpretation. Best value "
         "across quality, speed, and cost."),
        ("Pro",     "Amazon Nova Pro",  "128K", "Moderate",
         False, False,
         "Multimodal strength: text + images + video. Use when your "
         "documents contain charts or images that need interpretation."),
        ("Opus",    "Claude 4 Opus",    "200K", "Highest",
         False, True,
         "Maximum accuracy. Reserve for regulatory interpretation, "
         "multi-step agentic workflows, and decisions where a single "
         "error has real cost. Overkill and expensive for simple tasks."),
    ]

    for name, base, ctx, cost, is_rec, is_top, desc in models:
        # Name pill
        bg_pill = GOLD if is_rec else (ORANGE if is_top else HexColor("#DDDDDD"))
        fg_pill = BLACK
        pw = pill(cv, name, cl + PAD, iy, bg=bg_pill, fg=fg_pill)
        # Metadata
        cv.setFont("Helvetica", 7); cv.setFillColor(SOFT)
        meta = f"{base}  ·  {ctx}  ·  {cost} cost"
        cv.drawString(cl + PAD + pw + 6, iy + 2, meta)
        if is_rec:
            cv.setFont("Helvetica-Bold", 7); cv.setFillColor(ORANGE)
            mw = cv.stringWidth(meta, "Helvetica", 7)
            cv.drawString(cl + PAD + pw + 8 + mw, iy + 2, "  ★ Start here")
        iy -= 14
        iy = wrap_text(cv, desc, cl + PAD + 4, iy, IW - 4,
                       size=8, color=MID, lh=11)
        iy -= 6

    divider(cv, cl + PAD, iy + 2, IW)
    iy -= 10

    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(GOLD)
    cv.drawString(cl + PAD, iy, "TOKEN CHEAT SHEET")
    iy -= 12

    rows = [
        ("1 token",                   "≈ ¾ of a word"),
        ("200-word email",            "≈ 270 tokens"),
        ("10-page report",            "≈ 6,700 tokens"),
        ("RAG injection (5 chunks)",  "≈ 2,500 tokens"),
        ("Max output / response",     "≈ 48,000 words"),
        ("Switch model mid-chat",     "@ModelName in chat"),
        ("Cost tip",                  "Use Haiku/Lite for bulk; Sonnet for analysis; Opus for critical"),
    ]
    for lbl, val in rows:
        cv.setFont("Helvetica-Bold", 7.5); cv.setFillColor(MID)
        cv.drawString(cl + PAD, iy, lbl)
        cv.setFont("Helvetica", 7.5); cv.setFillColor(SOFT)
        cv.drawRightString(cl + PAD + IW, iy, val)
        iy -= 10

    # ── A-RIGHT: CRAFT Framework ──────────────────────────────────────────
    iy = ra_y + ROW_A_H - PAD - 2
    iy = section_label(cv, "The CRAFT Prompt Framework", cr + PAD, iy, IW)
    iy -= 2

    cv.setFont("Helvetica", 8); cv.setFillColor(MID)
    iy = wrap_text(cv,
        "Structure every prompt with these five elements. "
        "A complete CRAFT prompt reduces back-and-forth by 60–80% "
        "and consistently produces output you can use immediately.",
        cr + PAD, iy, IW, size=8, color=MID, lh=11)
    iy -= 8

    craft_items = [
        ("C", "Context",
         "Who you are, the purpose, constraints, and background. "
         "\"I am preparing a board presentation on Q2 credit risk. "
         "My audience is non-technical executives. The tone must be calm and factual.\""),
        ("R", "Role",
         "Assign a specific persona with domain expertise. "
         "\"You are a senior Treasury analyst at Flagstar with 15 years "
         "of ALM experience.\" Role primes the model's perspective and vocabulary."),
        ("A", "Action",
         "A precise, active verb: analyze / draft / compare / extract / "
         "evaluate / rewrite / translate. Avoid: 'help me with' or 'tell me about' "
         "— these are vague and produce generic responses."),
        ("F", "Format",
         "Specify structure explicitly: \"Return a markdown table with four columns: "
         "Risk Factor, Likelihood, Impact (1–5), Mitigation.\" "
         "Or: \"Three bullet points, max 20 words each, no jargon.\""),
        ("T", "Tone & Target",
         "Define audience and reading level. "
         "\"Plain English for a non-finance VP\" produces a completely "
         "different response than \"technical language for the ALCO committee.\""),
    ]
    for letter_, name, desc in craft_items:
        # Letter badge
        cv.setFillColor(GOLD)
        cv.roundRect(cr + PAD, iy - 2, 16, 16, 3, fill=1, stroke=0)
        cv.setFillColor(BLACK); cv.setFont("Helvetica-Bold", 10)
        cv.drawCentredString(cr + PAD + 8, iy + 3, letter_)
        cv.setFont("Helvetica-Bold", 9); cv.setFillColor(BLACK)
        cv.drawString(cr + PAD + 22, iy, name)
        iy -= 13
        iy = wrap_text(cv, desc, cr + PAD + 22, iy, IW - 22,
                       size=8, color=MID, lh=11)
        iy -= 5

    # ── B-LEFT: Power Techniques ──────────────────────────────────────────
    iy = rb_y + ROW_B_H - PAD - 2
    iy = section_label(cv, "Power Prompting Techniques", cl + PAD, iy, IW)
    iy -= 4

    techniques = [
        ("Chain-of-thought",
         "Append \"think step by step\" or \"show your reasoning before answering\" "
         "to any analytical prompt. Accuracy on multi-step problems improves "
         "significantly — the model surfaces its logic, which you can also verify."),
        ("Few-shot examples",
         "Show 1–2 examples of the exact output you want before requesting yours. "
         "\"Here is a good example of the format I need: [X]. "
         "Now produce the same for [Y].\" Examples outperform instructions alone."),
        ("Negative constraints",
         "State what NOT to do explicitly — models process negatives reliably. "
         "\"Do NOT include generic advice. Do NOT exceed 250 words. "
         "Do NOT use bullet points. Do NOT reference competitors.\""),
        ("Structured output",
         "\"Return JSON with keys: risk, likelihood (1–5), impact (1–5), "
         "mitigation.\" Structured output is machine-readable, "
         "copy-paste ready, and eliminates interpretation errors."),
        ("Iterative refinement",
         "Treat one conversation as one working session. Build on responses: "
         "\"Strengthen the opening\" → \"Cut to half the length\" → "
         "\"Add a concrete Flagstar example.\" Never start over — iterate."),
        ("Persona persistence via Memory",
         "In the left sidebar, open Memory and add permanent context: "
         "your role, department, preferred writing style, recurring acronyms. "
         "This personalizes every future conversation automatically."),
    ]
    for title_, body_ in techniques:
        cv.setFont("Helvetica-Bold", 8.5); cv.setFillColor(BLUE)
        cv.drawString(cl + PAD, iy, title_)
        iy -= 12
        iy = wrap_text(cv, body_, cl + PAD + 6, iy, IW - 6,
                       size=8, color=MID, lh=11)
        iy -= 7

    # ── B-RIGHT: Anti-patterns + Quick Wins (dark bg) ─────────────────────
    iy = rb_y + ROW_B_H - PAD - 2
    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(GOLD)
    cv.drawString(cr + PAD, iy, "ANTI-PATTERNS — WHAT NOT TO DO")
    iy -= 13

    antis = [
        ("Vague ask",
         "\"Help me with this\" → Be explicit about task, format, and audience"),
        ("Using Opus for simple work",
         "Reserve Opus for high-stakes analysis. Haiku costs ~50× less"),
        ("Restarting instead of refining",
         "\"Make it more concise\" beats starting a new chat from scratch"),
        ("No context provided",
         "The model cannot tailor output if it doesn't know who will read it"),
        ("One giant prompt",
         "Break complex work into steps — each step gets a focused, quality response"),
        ("Accepting the first draft",
         "AI first drafts are starting points. Always refine at least once"),
        ("Uploading without a question",
         "\"Here is a file\" alone gives the model nothing to retrieve against"),
        ("Ignoring stale context",
         "Long chats drift. Start fresh and summarize key context from the prior one"),
    ]
    for title_, fix in antis:
        cv.setFillColor(RED); cv.setFont("Helvetica-Bold", 8)
        cv.drawString(cr + PAD, iy, "✘  " + title_)
        iy -= 11
        iy = wrap_text(cv, fix, cr + PAD + 10, iy, IW - 10,
                       size=7.5, color=HexColor("#CCCCCC"), lh=10)
        iy -= 5

    divider(cv, cr + PAD, iy + 2, IW, color=HexColor("#444444"))
    iy -= 10

    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(GOLD)
    cv.drawString(cr + PAD, iy, "KEYBOARD SHORTCUTS & CHAT COMMANDS")
    iy -= 12

    shortcuts = [
        ("/command",  "Invoke a saved prompt template with an interactive form"),
        ("#kb-name",  "Reference a knowledge base in the current chat"),
        ("@Model",    "Switch AI model mid-conversation without starting over"),
        ("$skill",    "Activate a Skill instruction set for the current session"),
        ("↑ arrow",   "Edit your last message in the chat input"),
        ("Ctrl+Enter","Send message (configurable in profile settings)"),
    ]
    for key, desc in shortcuts:
        cv.setFont("Courier-Bold", 7.5); cv.setFillColor(GOLD)
        kw = cv.stringWidth(key, "Courier-Bold", 7.5)
        cv.drawString(cr + PAD, iy, key)
        cv.setFont("Helvetica", 7.5); cv.setFillColor(HexColor("#CCCCCC"))
        cv.drawString(cr + PAD + kw + 6, iy, desc)
        iy -= 11

    draw_footer(cv)


# ─────────────────────────────────────────────────────────────────────────
#  PAGE 2  —  Knowledge Bases, RAG & Workspace
# ─────────────────────────────────────────────────────────────────────────
def page2(cv):
    cv.showPage()
    cv.setFillColor(CREAM)
    cv.rect(0, 0, W, H, fill=1, stroke=0)

    draw_header(cv, 2, 4,
        "Knowledge bases · RAG internals · Retrieval modes · "
        "Custom agents · Skills, tools & prompt libraries")

    top = H - HEADER_H - STRIPE_H
    ROW_A_H = 316
    ROW_B_H = BODY_H - ROW_A_H - 3 * GUTTER  # 656 - 316 - 48 = 292

    ra_y = top - GUTTER - ROW_A_H
    rb_y = ra_y - GUTTER - ROW_B_H

    cl = MARGIN; cr = MARGIN + SC + GUTTER
    IW = SC - 2 * PAD

    rr(cv, cl, ra_y, SC, ROW_A_H, r=8, fill=WHITE,     stroke=RULE, sw=0.8)
    rr(cv, cr, ra_y, SC, ROW_A_H, r=8, fill=GOLD_TINT, stroke=RULE, sw=0.8)
    rr(cv, cl, rb_y, SC, ROW_B_H, r=8, fill=GOLD_TINT, stroke=RULE, sw=0.8)
    rr(cv, cr, rb_y, SC, ROW_B_H, r=8, fill=WHITE,     stroke=RULE, sw=0.8)

    # ── A-LEFT: RAG Internals ─────────────────────────────────────────────
    iy = ra_y + ROW_A_H - PAD - 2
    iy = section_label(cv, "How RAG Works — Under the Hood", cl + PAD, iy, IW)
    iy -= 2

    cv.setFont("Helvetica", 8); cv.setFillColor(MID)
    iy = wrap_text(cv,
        "When you upload a document, StarIQ doesn't \"read\" it the way a human does. "
        "Here is the exact pipeline from upload to cited answer:",
        cl + PAD, iy, IW, size=8, color=MID, lh=11)
    iy -= 8

    rag_steps = [
        ("Extract",
         "Apache Tika 3.2 extracts text from 1,000+ formats: PDF, Word, "
         "Excel (all sheets), PowerPoint, HTML, email (.eml/.msg), ZIP archives, images (OCR). "
         "Formulas extract as computed values. Charts and embedded images are NOT extracted."),
        ("Chunk",
         "Text is split into ~1,500-character segments with configurable overlap. "
         "Overlap preserves meaning across section boundaries — critical for legal "
         "contracts, policy documents, and any content where context flows across paragraphs."),
        ("Embed",
         "Each chunk is converted to a vector — a mathematical fingerprint of its semantic "
         "meaning — using Cohere Embed v4. Similar meaning = similar vector, "
         "regardless of exact wording."),
        ("Store",
         "Vectors are stored in PGVector (PostgreSQL) inside Flagstar's private AWS. "
         "Fully encrypted at rest (AWS KMS). Never sent externally. "
         "Full audit trail for all access."),
        ("Retrieve",
         "Your question is also embedded. The system finds the top 5 chunks whose "
         "vectors are most semantically similar to your query — "
         "not keyword matching, but meaning matching."),
        ("Answer",
         "The 5 chunks (~2,500 tokens) are injected into the model's context window "
         "alongside your question. The model generates a response grounded in those "
         "chunks, with citations showing the exact source document and section."),
    ]
    for i, (step, desc) in enumerate(rag_steps):
        circle_badge(cv, str(i + 1), cl + PAD + 9, iy - 2, r=9, bg=GOLD, fg=BLACK)
        cv.setFont("Helvetica-Bold", 9); cv.setFillColor(BLACK)
        cv.drawString(cl + PAD + 24, iy, step)
        iy -= 13
        iy = wrap_text(cv, desc, cl + PAD + 24, iy, IW - 24,
                       size=8, color=MID, lh=11)
        iy -= 6

    divider(cv, cl + PAD, iy + 2, IW)
    iy -= 10

    # Retrieval modes
    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(GOLD)
    cv.drawString(cl + PAD, iy, "TWO RETRIEVAL MODES")
    iy -= 12

    modes = [
        (GOLD, "Focused Retrieval (default)",
         "Sends only the top 5 most relevant chunks per query (~2,500 tokens). "
         "Best for large collections. Efficient, fast, and cost-effective."),
        (ORANGE, "Full Context",
         "Injects the complete file every message — bypasses RAG entirely. "
         "Use ONLY for short reference material that is always relevant "
         "(style guides, brand templates). Impractical and expensive for anything over ~3,000 words."),
    ]
    for mc, mname, mdesc in modes:
        pw = pill(cv, mname, cl + PAD, iy, bg=mc, fg=BLACK)
        iy -= 14
        iy = wrap_text(cv, mdesc, cl + PAD + 6, iy, IW - 6,
                       size=8, color=MID, lh=11)
        iy -= 8

    # File limits table
    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(GOLD)
    cv.drawString(cl + PAD, iy, "FILE LIMITS & TECHNICAL SPECS")
    iy -= 12
    specs = [
        ("Max file size",       "50 MB"),
        ("Max files per KB",    "90 files"),
        ("Supported formats",   "1,000+ (Apache Tika 3.2)"),
        ("Embedding model",     "Cohere Embed v4"),
        ("Chunks returned",     "Top 5 per query"),
        ("Chunk size",          "~1,500 characters"),
        ("Vector DB",           "PostgreSQL + PGVector"),
    ]
    for lbl, val in specs:
        cv.setFont("Helvetica-Bold", 7.5); cv.setFillColor(MID)
        cv.drawString(cl + PAD, iy, lbl)
        cv.setFont("Helvetica", 7.5); cv.setFillColor(SOFT)
        cv.drawRightString(cl + PAD + IW, iy, val)
        iy -= 10

    # ── A-RIGHT: KB Best Practices ────────────────────────────────────────
    iy = ra_y + ROW_A_H - PAD - 2
    iy = section_label(cv, "Knowledge Base Best Practices", cr + PAD, iy, IW)
    iy -= 4

    bps = [
        ("Organize by domain",
         "Separate KBs by topic: \"Compliance Policies\", \"ALM Procedures\", "
         "\"ALCO Minutes\". Focused scope = higher retrieval precision and "
         "less risk of pulling from irrelevant documents."),
        ("Write precise KB descriptions",
         "The description trains AI discovery. Write it like a search query: "
         "\"Flagstar FTP methodology, ALM policies, interest rate risk procedures "
         "updated 2024–2025.\" Vague names produce vague retrievals."),
        ("Keep documents current",
         "Outdated documents produce outdated answers. Assign a KB owner "
         "per department. Run a quarterly review: remove stale files, "
         "add updated versions, re-test retrieval quality."),
        ("Test before deploying to a team",
         "Ask 5–10 representative questions and verify that citations pull "
         "from the correct sections. If retrieval is weak, improve document "
         "structure — use clear headings and avoid large table-only files."),
        ("Scope custom agents tightly",
         "When building a custom model, attach only the KBs it actually needs. "
         "An unscoped agent can retrieve from ANY KB the user has access to, "
         "which increases the risk of hallucination from irrelevant sources."),
        ("Prefer text-rich documents",
         "Charts, images, and complex table formatting are NOT extracted. "
         "Excel formulas show only computed values. "
         "Scanned PDFs require Tesseract OCR — currently disabled for "
         "embedded images. Convert to text-heavy formats where possible."),
        ("Private by default",
         "Every KB starts as private. Explicitly grant access to RBAC groups "
         "or individuals. For KBs containing confidential content, "
         "use private visibility and audit access grants quarterly."),
    ]
    for title_, body_ in bps:
        cv.setFillColor(GOLD); cv.setFont("Helvetica-Bold", 10)
        cv.drawString(cr + PAD, iy, "·")
        cv.setFont("Helvetica-Bold", 8.5); cv.setFillColor(BLACK)
        cv.drawString(cr + PAD + 10, iy, title_)
        iy -= 12
        iy = wrap_text(cv, body_, cr + PAD + 10, iy, IW - 10,
                       size=8, color=MID, lh=11)
        iy -= 7

    # ── B-LEFT: Building Custom AI Agents ────────────────────────────────
    iy = rb_y + ROW_B_H - PAD - 2
    iy = section_label(cv, "Building Custom AI Agents (Workspace → Models)", cl + PAD, iy, IW)
    iy -= 4

    cv.setFont("Helvetica", 8); cv.setFillColor(MID)
    iy = wrap_text(cv,
        "A Custom Model is not a new AI — it is a configuration preset that binds "
        "a system prompt, knowledge bases, tools, skills, and capability toggles "
        "to a base model. The result: a purpose-built team member "
        "with a defined job, scope, and personality.",
        cl + PAD, iy, IW, size=8, color=MID, lh=11)
    iy -= 8

    cv.setFont("Helvetica-Bold", 8.5); cv.setFillColor(GOLD)
    cv.drawString(cl + PAD, iy, "Example build — Treasury Policy Assistant")
    iy -= 13

    agent_config = [
        ("Base Model",
         "Sonnet — strong reasoning, cost-effective for daily department queries"),
        ("System Prompt",
         "\"You are a Treasury policy expert at Flagstar. Answer only using "
         "attached knowledge bases. Always cite exact sources. "
         "If you are not certain, say so explicitly. "
         "Today is {{CURRENT_DATE}}, user is {{USER_NAME}}.\""),
        ("Knowledge bases",
         "Attach: 'FTP Procedures', 'ALM Policy', 'ALCO Minutes'. "
         "Leave others unattached to prevent off-topic retrievals."),
        ("Capabilities",
         "Enable: Citations (required for trust). "
         "Disable: Image Generation, Code Interpreter (out of scope)."),
        ("Prompt starter chips",
         "Add clickable suggestions: 'Summarize FTP methodology', "
         "'What is our policy on duration gap limits?', "
         "'Explain ALCO reporting requirements'."),
        ("Access control",
         "Share with 'Treasury Team' RBAC group — Read access. "
         "Assign Write access only to the KB owner."),
    ]
    for step, desc in agent_config:
        cv.setFillColor(ORANGE); cv.setFont("Helvetica-Bold", 8.5)
        cv.drawString(cl + PAD, iy, f"› {step}")
        iy -= 12
        iy = wrap_text(cv, desc, cl + PAD + 10, iy, IW - 10,
                       size=8, color=MID, lh=11)
        iy -= 6

    divider(cv, cl + PAD, iy + 2, IW)
    iy -= 10

    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(GOLD)
    cv.drawString(cl + PAD, iy, "SKILLS vs TOOLS vs FUNCTIONS")
    iy -= 12

    svt = [
        ("Skills", BLUE,
         "Markdown instruction sets. Teach the model HOW to approach a task. "
         "Lazy-loaded on demand — efficient on context window. Invoke with $ in chat. "
         "Examples: code review checklist, writing style guide, analysis framework."),
        ("Tools", ORANGE,
         "Executable Python scripts. Give the model access to real-world data, "
         "APIs, and external calculations. Must pass a security code review "
         "before deployment. Invoke automatically when the model needs them."),
        ("Functions", SOFT,
         "Admin-only platform extensions: new AI providers, custom UI buttons, "
         "data pipeline filters. Not accessible to end users or team leads."),
    ]
    for svt_name, svt_col, svt_desc in svt:
        pw = pill(cv, svt_name, cl + PAD, iy, bg=svt_col, fg=WHITE if svt_col != SOFT else BLACK)
        iy -= 14
        iy = wrap_text(cv, svt_desc, cl + PAD + 6, iy, IW - 6,
                       size=8, color=MID, lh=11)
        iy -= 7

    # ── B-RIGHT: Prompt Libraries & Variables ────────────────────────────
    iy = rb_y + ROW_B_H - PAD - 2
    iy = section_label(cv, "Prompt Libraries & Slash Commands", cr + PAD, iy, IW)
    iy -= 4

    cv.setFont("Helvetica", 8); cv.setFillColor(MID)
    iy = wrap_text(cv,
        "Prompts are reusable templates with interactive form variables. "
        "Users type / in chat to browse and invoke them. "
        "When triggered, a form appears — users fill in the fields "
        "and receive structured, consistent output every time.",
        cr + PAD, iy, IW, size=8, color=MID, lh=11)
    iy -= 10

    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(BLACK)
    cv.drawString(cr + PAD, iy, "Variable types:")
    iy -= 13

    vars_ = [
        ("{{field_name}}",              "Plain text input"),
        ("{{name | textarea:...}}",     "Multi-line text area"),
        ("{{n | select:options=[...]}}","Dropdown (\"High\",\"Med\",\"Low\")"),
        ("{{due | date:required}}",     "Date picker — required field"),
        ("{{urgent | checkbox}}",       "Boolean toggle"),
        ("{{amount | number:min=0}}",   "Numeric input with min/max"),
        ("{{CURRENT_DATE}}",            "Auto-injected: today's date"),
        ("{{USER_NAME}}",               "Auto-injected: the requestor's name"),
        ("{{CLIPBOARD}}",               "Auto-injected: user's clipboard content"),
    ]
    for var, desc in vars_:
        cv.setFont("Courier-Bold", 7.5); cv.setFillColor(BLUE)
        vw = cv.stringWidth(var, "Courier-Bold", 7.5)
        cv.drawString(cr + PAD, iy, var)
        cv.setFont("Helvetica", 7.5); cv.setFillColor(SOFT)
        cv.drawString(cr + PAD + vw + 6, iy, desc)
        iy -= 11

    divider(cv, cr + PAD, iy + 2, IW)
    iy -= 10

    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(GOLD)
    cv.drawString(cr + PAD, iy, "MULTI-MODEL WORKFLOW")
    iy -= 12

    cv.setFont("Helvetica", 8); cv.setFillColor(MID)
    iy = wrap_text(cv,
        "Switch models mid-conversation with @ModelName to run "
        "different phases at the optimal cost-quality point:",
        cr + PAD, iy, IW, size=8, color=MID, lh=11)
    iy -= 8

    workflow = [
        ("@Haiku",  "Extract all dates, amounts, and party names from the contract (fast, cheap)"),
        ("@Sonnet", "Analyze extracted terms for risk, ambiguity, and missing clauses (balanced)"),
        ("@Opus",   "Draft a legal memo with full reasoning and actionable recommendations (highest quality)"),
    ]
    for model, desc in workflow:
        cv.setFillColor(ORANGE); cv.setFont("Courier-Bold", 8.5)
        mw = cv.stringWidth(model, "Courier-Bold", 8.5)
        cv.drawString(cr + PAD, iy, model)
        iy -= 12
        iy = wrap_text(cv, desc, cr + PAD + 10, iy, IW - 10,
                       size=8, color=MID, lh=11)
        iy -= 7

    cv.setFont("Helvetica-Oblique", 7.5); cv.setFillColor(SOFT)
    cv.drawString(cr + PAD, iy,
        "Generated documents (Word, PPT, Excel) available to download for 30 days.")

    draw_footer(cv)


# ─────────────────────────────────────────────────────────────────────────
#  PAGE 3  —  RBAC, Doc Gen, Governance, Roadmap, Troubleshooting
# ─────────────────────────────────────────────────────────────────────────
def page3(cv):
    cv.showPage()
    cv.setFillColor(CREAM)
    cv.rect(0, 0, W, H, fill=1, stroke=0)

    draw_header(cv, 3, 4,
        "RBAC & sharing · Document generation · Data governance · AI intake process")

    top = H - HEADER_H - STRIPE_H

    # 2 rows — roadmap & troubleshooting moved to page 4
    ROW_A_H = 252
    ROW_B_H = BODY_H - ROW_A_H - 3 * GUTTER  # 656-252-48=356

    ra_y = top - GUTTER - ROW_A_H
    rb_y = ra_y - GUTTER - ROW_B_H

    cl = MARGIN; cr = MARGIN + SC + GUTTER
    IW = SC - 2 * PAD

    rr(cv, cl, ra_y, SC, ROW_A_H, r=8, fill=GOLD_TINT, stroke=RULE, sw=0.8)
    rr(cv, cr, ra_y, SC, ROW_A_H, r=8, fill=WHITE,     stroke=RULE, sw=0.8)
    rr(cv, cl, rb_y, SC, ROW_B_H, r=8, fill=WHITE,     stroke=RULE, sw=0.8)
    rr(cv, cr, rb_y, SC, ROW_B_H, r=8, fill=GOLD_TINT, stroke=RULE, sw=0.8)

    # ── A-LEFT: RBAC & Sharing ────────────────────────────────────────────
    iy = ra_y + ROW_A_H - PAD - 2
    iy = section_label(cv, "RBAC & Sharing Strategy", cl + PAD, iy, IW)
    iy -= 4

    cv.setFont("Helvetica", 8); cv.setFillColor(MID)
    iy = wrap_text(cv,
        "All Workspace resources share an additive permission model. "
        "Permissions NEVER deny — if ANY group a user belongs to grants a permission, they have it. "
        "Design accordingly: minimize Global Defaults, grant specifics via groups.",
        cl + PAD, iy, IW, size=8, color=MID, lh=11)
    iy -= 8

    group_types = [
        (GOLD, "Permission Groups  (for feature rights)",
         "Grant specific capabilities: image generation, code interpreter, web search. "
         "Set 'Who can share' = Nobody so they stay invisible in sharing menus. "
         "Examples: 'Power Users', 'Developers', 'Data Scientists'."),
        (ORANGE, "Sharing Groups  (for resource access)",
         "Organize users by team or project for sharing models, KBs, and prompts. "
         "Set 'Who can share' = Members (private) or Anyone (open). "
         "Examples: 'Treasury Team', 'HR Leadership', 'Risk Committee'."),
    ]
    for gc, gname, gdesc in group_types:
        pw = pill(cv, gname, cl + PAD, iy, bg=gc, fg=BLACK)
        iy -= 15
        iy = wrap_text(cv, gdesc, cl + PAD + 6, iy, IW - 6,
                       size=8, color=MID, lh=11)
        iy -= 8

    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(GOLD)
    cv.drawString(cl + PAD, iy, "PRINCIPLE OF LEAST PRIVILEGE")
    iy -= 12

    rules = [
        "Minimize Global Defaults — grant rights through groups, not globally",
        "Attach only the KBs an agent needs — unscoped models pull from all accessible KBs",
        "Read access for team sharing; Write access only for designated owners",
        "Confidential KBs → Private visibility + explicit named access grants",
        "Group memberships auto-sync from Microsoft Entra ID on every login",
        "User Roles: Admin (full) · User (standard) · Pending (new SSO accounts)",
    ]
    for r_ in rules:
        cv.setFillColor(GOLD); cv.setFont("Helvetica-Bold", 10)
        cv.drawString(cl + PAD, iy, "·")
        iy = wrap_text(cv, r_, cl + PAD + 10, iy, IW - 10,
                       size=8, color=MID, lh=11)
        iy -= 5

    # ── A-RIGHT: Document Generation & In-Chat Rendering ─────────────────
    iy = ra_y + ROW_A_H - PAD - 2
    iy = section_label(cv, "Document Generation & In-Chat Rendering", cr + PAD, iy, IW)
    iy -= 4

    cv.setFont("Helvetica-Bold", 8.5); cv.setFillColor(BLACK)
    cv.drawString(cr + PAD, iy, "Generate downloadable Office files in chat:")
    iy -= 13

    office = [
        ("Word (.docx)",       BLUE,  "Reports, summaries, proposals, meeting notes, policy drafts"),
        ("PowerPoint (.pptx)", ORANGE,"Presentations with speaker notes, layouts, themes"),
        ("Excel (.xlsx)",      GREEN, "Data exports, financial tables, tracking sheets, models"),
    ]
    for fmt, fc, use in office:
        cv.setFont("Helvetica-Bold", 8.5); cv.setFillColor(fc)
        fw = cv.stringWidth(fmt, "Helvetica-Bold", 8.5)
        cv.drawString(cr + PAD, iy, fmt)
        cv.setFont("Helvetica", 8); cv.setFillColor(MID)
        cv.drawString(cr + PAD + fw + 5, iy, f"— {use}")
        iy -= 13

    cv.setFont("Helvetica-Oblique", 7.5); cv.setFillColor(SOFT)
    cv.drawString(cr + PAD, iy, "Files available to download for 30 days after generation.")
    iy -= 14

    cv.setFont("Helvetica-Bold", 8.5); cv.setFillColor(BLACK)
    cv.drawString(cr + PAD, iy, "In-chat Artifacts (no download, rendered in panel):")
    iy -= 13

    artifacts = [
        ("Mermaid", GOLD,
         "Flowcharts, org charts, Gantt, sequence diagrams, ERDs, pie charts"),
        ("HTML", BLUE,
         "Interactive dashboards, calculators, styled reports"),
        ("SVG", ORANGE,
         "Infographics, logos, technical drawings"),
        ("CSV / JSON", GREEN,
         "Quick data tables and syntax-highlighted structured data"),
        ("LaTeX", HexColor("#6A0DAD"),
         "Mathematical equations and scientific notation"),
    ]
    for art, ac, desc in artifacts:
        pw = pill(cv, art, cr + PAD, iy, bg=ac, fg=BLACK if ac == GOLD else WHITE, font_size=7.5)
        cv.setFont("Helvetica", 8); cv.setFillColor(MID)
        cv.drawString(cr + PAD + pw + 5, iy + 2, desc)
        iy -= 14

    divider(cv, cr + PAD, iy + 2, IW)
    iy -= 10

    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(GOLD)
    cv.drawString(cr + PAD, iy, "BEST PROMPTS FOR DOCUMENT GENERATION")
    iy -= 12

    gen_tips = [
        "Specify sections explicitly: \"Include headings: Executive Summary, Key Risks, Recommendations\"",
        "Provide your data directly rather than asking the AI to invent numbers",
        "Request speaker notes for PowerPoint: \"Add 2-sentence speaker notes per slide\"",
        "Name column headers for Excel: \"Columns: Date, Category, Amount, Owner, Status\"",
        "Break large documents into parts — max output is ~48,000 words per response",
    ]
    for tip in gen_tips:
        cv.setFillColor(ORANGE); cv.setFont("Helvetica-Bold", 9)
        cv.drawString(cr + PAD, iy, "›")
        iy = wrap_text(cv, tip, cr + PAD + 12, iy, IW - 12,
                       size=8, color=MID, lh=11)
        iy -= 5

    # ── B-LEFT: Data Governance ───────────────────────────────────────────
    iy = rb_y + ROW_B_H - PAD - 2
    iy = section_label(cv, "Data Classification & Governance", cl + PAD, iy, IW)
    iy -= 4

    cv.setFont("Helvetica", 8); cv.setFillColor(MID)
    iy = wrap_text(cv,
        "Before uploading any document to StarIQ, apply Flagstar's "
        "Enterprise Data Governance (EDG) Policy classification:",
        cl + PAD, iy, IW, size=8, color=MID, lh=11)
    iy -= 8

    classes = [
        (GREEN, "✅  Public",
         "Freely uploadable. Annual reports, press releases, regulatory guidance, "
         "published industry research."),
        (BLUE, "✅  Internal",
         "Generally appropriate. Internal procedures, meeting notes, project plans, "
         "team presentations. Standard StarIQ use."),
        (AMBER, "⚠   Confidential",
         "Proceed with caution. Non-public financials, strategy documents. "
         "Configure KB access controls before uploading. Consult the AI Team for guidance."),
        (RED, "❌  Restricted / Sensitive",
         "DO NOT upload without explicit written authorization. "
         "Customer PII, Social Security numbers, account numbers, authentication credentials, "
         "material non-public information (MNPI), or GLBA-protected data."),
    ]
    for cc, label, desc in classes:
        cv.setFont("Helvetica-Bold", 9); cv.setFillColor(cc)
        cv.drawString(cl + PAD, iy, label)
        iy -= 12
        iy = wrap_text(cv, desc, cl + PAD + 10, iy, IW - 10,
                       size=8, color=MID, lh=11)
        iy -= 8

    # ── B-RIGHT: Intake Process + Key Policies ───────────────────────────
    iy = rb_y + ROW_B_H - PAD - 2
    iy = section_label(cv, "AI Use Case Intake Process", cr + PAD, iy, IW)
    iy -= 4

    cv.setFont("Helvetica", 8); cv.setFillColor(MID)
    iy = wrap_text(cv,
        "Everyday use — summarizing, drafting, analyzing — does NOT require intake. "
        "Submit an intake form when your use case goes beyond standard chat:",
        cr + PAD, iy, IW, size=8, color=MID, lh=11)
    iy -= 8

    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(ORANGE)
    cv.drawString(cr + PAD, iy, "SUBMIT AN INTAKE FORM WHEN:")
    iy -= 12

    triggers = [
        "Building a custom agent that accesses sensitive or regulated data",
        "Integrating StarIQ with other Flagstar systems, APIs, or databases",
        "Deploying AI for any customer-facing process or workflow",
        "Your initiative involves GLBA, SOX, HMDA, or other regulated data",
        "Evaluating or procuring any third-party AI service or vendor",
        "Deploying Python-based Tools — must pass security code review first",
    ]
    for t_ in triggers:
        cv.setFillColor(ORANGE); cv.setFont("Helvetica-Bold", 10)
        cv.drawString(cr + PAD, iy, "·")
        iy = wrap_text(cv, t_, cr + PAD + 10, iy, IW - 10,
                       size=8, color=MID, lh=11)
        iy -= 5

    iy -= 6
    divider(cv, cr + PAD, iy + 2, IW)
    iy -= 10

    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(GOLD)
    cv.drawString(cr + PAD, iy, "KEY POLICIES TO KNOW")
    iy -= 12

    policies = [
        ("CIS Policy (Jan 2025)",
         "Customer Information Security — governs GLBA nonpublic personal information"),
        ("EDG Policy (Aug 2025)",
         "Enterprise Data Governance — data ownership and user responsibilities"),
        ("ECIM Policy (Aug 2025)",
         "Enterprise Corporate Information Management — data types and handling"),
        ("Master InfoSec Policy (Dec 2022)",
         "Access controls, data protection, and confidentiality requirements"),
    ]
    for pol_name, pol_desc in policies:
        cv.setFont("Helvetica-Bold", 8); cv.setFillColor(MID)
        cv.drawString(cr + PAD, iy, pol_name)
        iy -= 11
        iy = wrap_text(cv, pol_desc, cr + PAD + 8, iy, IW - 8,
                       size=7.5, color=SOFT, lh=10)
        iy -= 6

    iy -= 4
    cv.setFont("Helvetica-Oblique", 8); cv.setFillColor(SOFT)
    iy = wrap_text(cv,
        "Full admin visibility details and privacy commitments on page 4.",
        cr + PAD, iy, IW, size=8, color=SOFT, lh=11)

    draw_footer(cv)


# ─────────────────────────────────────────────────────────────────────────
def page4(cv):
    cv.showPage()
    cv.setFillColor(CREAM); cv.rect(0, 0, W, H, fill=1, stroke=0)

    draw_header(cv, 4, 4,
        "2026 roadmap · Troubleshooting · Admin visibility & privacy")

    top = H - HEADER_H - STRIPE_H

    ROW_A_H = 260  # dark roadmap strip (full width)
    ROW_B_H = BODY_H - ROW_A_H - 3 * GUTTER  # 656-260-48=348

    ra_y = top - GUTTER - ROW_A_H
    rb_y = ra_y - GUTTER - ROW_B_H

    cl = MARGIN; cr = MARGIN + SC + GUTTER
    IW = SC - 2 * PAD

    rr(cv, MARGIN, ra_y, CW, ROW_A_H, r=8, fill=DARK_BG)
    rr(cv, cl, rb_y, SC, ROW_B_H, r=8, fill=GOLD_TINT, stroke=RULE, sw=0.8)
    rr(cv, cr, rb_y, SC, ROW_B_H, r=8, fill=WHITE,     stroke=RULE, sw=0.8)

    # ── ROW A: 2026 Roadmap (dark, 2×2 quarter grid) ─────────────────────
    iy = ra_y + ROW_A_H - PAD - 2
    cv.setFont("Helvetica-Bold", 9); cv.setFillColor(GOLD)
    cv.drawString(MARGIN + PAD, iy, "2026 ROADMAP")
    iy -= 14

    # Left half: Q1 + Q2   |   Right half: Q3 + Q4
    lx = MARGIN + PAD;     lw = SC - PAD
    rx_ = MARGIN + SC + GUTTER; rw = SC - PAD
    iy_l = iy; iy_r = iy

    quarters = [
        ("✅  Q1 — Launched Feb 2026", GREEN,
         "Core platform · All 5 models via Amazon Bedrock · Knowledge bases & RAG "
         "· Prompt libraries with slash commands · Voice dictation & voice mode · "
         "Full accessibility compliance"),
        ("⏳  Q2 — Apr–Jun 2026", GOLD,
         "OneDrive & SharePoint RAG with auto permission enforcement · "
         "Mobile PWA (offline + push notifications) · "
         "AI Web Search via Palo Alto Prisma AI firewalls"),
        ("Q3 — Jul–Sep 2026", ORANGE,
         "Model Context Protocol (MCP) — connect AI to external tools & APIs · "
         "Python AI Tool Framework with internal marketplace · "
         "Code Interpreter enhancements · Advanced multi-step agent chains"),
        ("Q4 — Oct–Dec 2026", RED,
         "Custom Agents for IT Support, HR & Finance · "
         "Agent Policy Controls (natural language guardrails) · "
         "Agent Evaluation Pipeline (accuracy tracking & A/B testing) · "
         "Enterprise agent versioning & rollback"),
    ]
    for i, (q_label, qc, q_desc) in enumerate(quarters):
        if i < 2:
            x_, w_ = lx, lw; iy_ptr = "l"
        else:
            x_, w_ = rx_, rw; iy_ptr = "r"

        cur_y = iy_l if iy_ptr == "l" else iy_r
        cv.setFont("Helvetica-Bold", 8); cv.setFillColor(qc)
        cv.drawString(x_, cur_y, q_label)
        cur_y -= 11
        cur_y = wrap_text(cv, q_desc, x_ + 6, cur_y, w_ - 6,
                          size=7.5, color=HexColor("#CCCCCC"), lh=10)
        cur_y -= 10
        if iy_ptr == "l":
            iy_l = cur_y
        else:
            iy_r = cur_y

    # vertical rule between left/right quarters
    mid_x = MARGIN + SC + GUTTER / 2
    cv.setStrokeColor(HexColor("#333333")); cv.setLineWidth(0.5)
    cv.line(mid_x, ra_y + 8, mid_x, ra_y + ROW_A_H - 8)

    # ── ROW B LEFT: Admin Visibility & Privacy ────────────────────────────
    iy = rb_y + ROW_B_H - PAD - 2
    iy = section_label(cv, "What Administrators Can See", cl + PAD, iy, IW)
    iy -= 4

    cv.setFont("Helvetica", 8); cv.setFillColor(MID)
    iy = wrap_text(cv,
        "Flagstar's AI team has visibility into platform activity for "
        "regulatory compliance, security auditing, and cost management. "
        "All access is governed by Flagstar's information security policies.",
        cl + PAD, iy, IW, size=8, color=MID, lh=11)
    iy -= 10

    admin_vis = [
        (GOLD,   "Conversation logs",
         "All chat sessions are retained for regulatory audit. Accessible to AI Team admins only."),
        (GOLD,   "Model & token usage",
         "Model selected, token consumption per session, cost patterns by team."),
        (GOLD,   "Knowledge base access",
         "Which KB was accessed, which documents retrieved, and by whom."),
        (GOLD,   "User activity",
         "Login times, feature usage, document uploads, voice sessions."),
        (GOLD,   "Tool executions",
         "All Python tool calls, their inputs, outputs, and execution times."),
    ]
    for ac, item, detail in admin_vis:
        cv.setFont("Helvetica-Bold", 8); cv.setFillColor(DARK_BG if ac == GOLD else ac)
        cv.setFont("Helvetica-Bold", 8); cv.setFillColor(MID)
        cv.drawString(cl + PAD, iy, item)
        iy -= 11
        iy = wrap_text(cv, detail, cl + PAD + 8, iy, IW - 8,
                       size=7.5, color=SOFT, lh=10)
        iy -= 6

    divider(cv, cl + PAD, iy + 4, IW)
    iy -= 10

    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(GOLD)
    cv.drawString(cl + PAD, iy, "PRIVACY COMMITMENTS")
    iy -= 12

    privacy = [
        "StarIQ does NOT train AI models on your conversations or uploads",
        "Data is used only to generate your response — never shared externally",
        "Conversations are encrypted at rest (AES-256) and in transit (TLS 1.3)",
        "Runs entirely within Flagstar's private AWS VPC — zero data leaves our perimeter",
        "Retention periods follow Flagstar's records management schedule",
    ]
    for p_ in privacy:
        cv.setFillColor(GREEN); cv.setFont("Helvetica-Bold", 9)
        cv.drawString(cl + PAD, iy, "✓")
        iy = wrap_text(cv, p_, cl + PAD + 12, iy, IW - 12,
                       size=8, color=MID, lh=11)
        iy -= 5

    # ── ROW B RIGHT: Troubleshooting Quick Reference ──────────────────────
    iy = rb_y + ROW_B_H - PAD - 2
    iy = section_label(cv, "Troubleshooting Quick Reference", cr + PAD, iy, IW)
    iy -= 4

    trouble = [
        ("SSO login fails",
         "Go to myapps.microsoft.com directly. If the StarIQ tile is missing, "
         "contact your manager — access requires group assignment in Entra ID."),
        ("Document missing from KB",
         "Check the Documents tab for processing status (green = indexed). "
         "In chat, type # then the KB name to reference it explicitly."),
        ("AI gives outdated answers",
         "Upload current documents to a KB and reference it with #. "
         "Web Search (Q2 2026) will add live internet access."),
        ("Slow or hanging responses",
         "Switch to Haiku (fastest) or Lite. Start a fresh chat to clear context. "
         "Large file uploads slow initial processing — wait for green status."),
        ("Token / context limit hit",
         "Start a new chat. Paste a short summary of the prior conversation. "
         "Use concise, specific prompts — avoid pasting full documents into chat."),
        ("Account stuck on Pending",
         "New SSO accounts need role elevation. Message the AI Team on Teams "
         "(join code: g2w1hjy) and they'll promote you to User within 1 business day."),
        ("KB citations seem wrong",
         "Test your KB with 3–5 representative questions. "
         "Check document recency, header structure, and ensure no scanned-image PDFs "
         "(Tika cannot OCR images — use searchable PDFs or Word docs)."),
        ("Model ignoring instructions",
         "Move key rules to the top of your prompt. Use Memory for persistent preferences. "
         "Opus handles complex multi-constraint tasks better than Sonnet or Haiku."),
    ]
    for issue, fix in trouble:
        cv.setFont("Helvetica-Bold", 8); cv.setFillColor(ORANGE)
        cv.drawString(cr + PAD, iy, issue)
        iy -= 11
        iy = wrap_text(cv, fix, cr + PAD + 8, iy, IW - 8,
                       size=7.5, color=MID, lh=10)
        iy -= 8

    draw_footer(cv)


# ─────────────────────────────────────────────────────────────────────────
def build(out_path):
    cv = canvas.Canvas(out_path, pagesize=letter)
    # Page 1 background
    cv.setFillColor(CREAM); cv.rect(0, 0, W, H, fill=1, stroke=0)
    page1(cv)
    page2(cv)
    page3(cv)
    page4(cv)
    cv.save()
    print(f"✅  {out_path}  ({os.path.getsize(out_path) // 1024} KB)")


if __name__ == "__main__":
    build("/home/user/Test1/StarIQ_PowerUser_Guide_v2.pdf")
