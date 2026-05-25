"""
StarIQ Power User Guide — Two-Page PDF
Design system: same as exec one-pager (8pt grid, Z-flow, 3-level type scale)
Content: StarIQ platform features + Claude/LLM best practices knowledge

Page 1: Advanced Prompting | Model Mastery | Knowledge Bases & RAG
Page 2: Custom Agents | Governance | Roadmap | Troubleshooting
"""

import math
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

# ── Brand palette (same as exec guide) ───────────────────────────────────
GOLD      = HexColor("#FFB81C")
ORANGE    = HexColor("#FF6200")
BLACK     = HexColor("#0D0D0D")
WHITE     = HexColor("#FFFFFF")
CREAM     = HexColor("#FFFDF7")
GOLD_TINT = HexColor("#FFF5D6")
MID       = HexColor("#4A4A4A")
SOFT      = HexColor("#888888")
DARK_BG   = HexColor("#1A1A1A")
DO_GREEN  = HexColor("#1D6B3E")
WARN_RED  = HexColor("#A52A2A")
RULE_LINE = HexColor("#E0D0A0")
BLUE_HL   = HexColor("#1565C0")

# ── 8pt baseline grid ─────────────────────────────────────────────────────
U      = 8
W, H   = letter  # 612 × 792
MARGIN = 5*U     # 40pt
GUTTER = 2*U     # 16pt
PAD    = 2*U     # 16pt
CW     = W - 2*MARGIN  # 532pt

HEADER_H = 10*U   # 80pt  (power user header is shorter — content is king)
FOOTER_H =  6*U   # 48pt
STRIPE_H =  1*U   #  8pt
CONTENT_H = H - HEADER_H - STRIPE_H - FOOTER_H  # 656pt per page


# ── Shared drawing helpers ────────────────────────────────────────────────
def rr(cv, x, y, w, h, r=6, fill=WHITE, stroke=None, sw=0.5):
    p = cv.beginPath()
    p.moveTo(x+r,y); p.lineTo(x+w-r,y)
    p.arcTo(x+w-r,y,x+w,y+r,-90,90); p.lineTo(x+w,y+h-r)
    p.arcTo(x+w-r,y+h-r,x+w,y+h,0,90); p.lineTo(x+r,y+h)
    p.arcTo(x,y+h-r,x+r,y+h,90,90); p.lineTo(x,y+r)
    p.arcTo(x,y,x+r,y+r,180,90); p.close()
    cv.setFillColor(fill)
    if stroke: cv.setStrokeColor(stroke); cv.setLineWidth(sw)
    cv.drawPath(p, fill=1, stroke=bool(stroke))

def wrap(cv, text, x, y, max_w, font, size, color, lh=None):
    """Wrap text; return y after last line."""
    if lh is None: lh = size * 1.4
    cv.setFont(font, size); cv.setFillColor(color)
    for raw in text.split("\n"):
        words = raw.split()
        if not words: y -= lh*0.5; continue
        buf = []
        for w_ in words:
            test = " ".join(buf+[w_])
            if cv.stringWidth(test, font, size) <= max_w:
                buf.append(w_)
            else:
                if buf: cv.drawString(x,y," ".join(buf)); y-=lh
                buf=[w_]
        if buf: cv.drawString(x,y," ".join(buf)); y-=lh
    return y

def sec_bar(cv, label, x, y, w, bg=GOLD, fg=BLACK):
    """Section header bar; returns y below it."""
    rr(cv, x, y, w, 16, r=4, fill=bg)
    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(fg)
    cv.drawString(x+6, y+4, label.upper())
    return y - 8

def bullet(cv, text, x, y, max_w, dot_color=GOLD, size=8.5):
    """Single bulleted line with wrap; returns y after."""
    cv.setFillColor(dot_color); cv.setFont("Helvetica-Bold", 10)
    cv.drawString(x, y, "·")
    y = wrap(cv, text, x+10, y, max_w-10, "Helvetica", size, MID)
    return y - 3

def numbered_item(cv, num, title, body, x, y, w, num_color=GOLD):
    """Numbered item: circle badge + bold title + body."""
    r = 9; cx_ = x+r; cy_ = y-2
    cv.setFillColor(num_color); cv.circle(cx_, cy_, r, fill=1, stroke=0)
    cv.setFillColor(BLACK); cv.setFont("Helvetica-Bold", 8)
    cv.drawCentredString(cx_, cy_-3, str(num))
    tx = x+r*2+5
    cv.setFont("Helvetica-Bold", 9); cv.setFillColor(BLACK)
    cv.drawString(tx, y, title)
    y -= 12
    y = wrap(cv, body, tx, y, w-r*2-5, "Helvetica", 8, MID)
    return y - 6

def flagstar_logo(cv, x, y, star_col=GOLD, text_col=WHITE):
    cx,cy = x+9,y+7
    cv.setFillColor(star_col)
    pts=4; ro=8; ri=2.5
    p=cv.beginPath()
    for i in range(pts*2):
        ang=math.pi/pts*i-math.pi/2
        r_=ro if i%2==0 else ri
        px_=cx+r_*math.cos(ang); py_=cy+r_*math.sin(ang)
        p.moveTo(px_,py_) if i==0 else p.lineTo(px_,py_)
    p.close(); cv.drawPath(p,fill=1,stroke=0)
    cv.setFillColor(text_col); cv.setFont("Helvetica-Bold",12)
    cv.drawString(cx+12, y+1, "flagstar")

def page_header(cv, page_num, subtitle):
    """Consistent header for both pages."""
    cv.setFillColor(BLACK)
    cv.rect(0, H-HEADER_H, W, HEADER_H, fill=1, stroke=0)
    # Title
    cv.setFillColor(GOLD); cv.setFont("Helvetica-Bold", 22)
    sw = cv.stringWidth("StarIQ", "Helvetica-Bold", 22)
    cv.drawString(MARGIN, H-HEADER_H+48, "StarIQ")
    cv.setFillColor(WHITE); cv.setFont("Helvetica-Bold", 22)
    cv.drawString(MARGIN+sw+3, H-HEADER_H+48, " Power User Guide")
    # Subtitle
    cv.setFillColor(SOFT); cv.setFont("Helvetica-Oblique", 8)
    cv.drawString(MARGIN, H-HEADER_H+30, subtitle)
    # Page badge
    rr(cv, W-MARGIN-72, H-HEADER_H+28, 72, 20, r=5, fill=GOLD)
    cv.setFillColor(BLACK); cv.setFont("Helvetica-Bold", 8)
    cv.drawCentredString(W-MARGIN-36, H-HEADER_H+36, f"PAGE {page_num} OF 2")
    # Logo
    flagstar_logo(cv, W-MARGIN-150, H-HEADER_H+42)
    # Gold stripe
    cv.setFillColor(GOLD)
    cv.rect(0, H-HEADER_H-STRIPE_H, W, STRIPE_H, fill=1, stroke=0)

def page_footer(cv, page_num):
    """Consistent footer for both pages."""
    cv.setFillColor(DARK_BG)
    cv.rect(0, 0, W, FOOTER_H, fill=1, stroke=0)
    cv.setFillColor(GOLD)
    cv.rect(0, FOOTER_H-3, W, 3, fill=1, stroke=0)
    links = [
        ("Login", "myapps.microsoft.com", "https://myapps.microsoft.com"),
        ("Resources", "flagstar.sharepoint.com/sites/AI",
         "https://flagstar.sharepoint.com/sites/AI/SitePages/Home.aspx"),
        ("Teams Support", "Join code: g2w1hjy", None),
        ("Exec Guide", "StarIQ at a Glance", None),
    ]
    seg = W / len(links)
    for i,(lbl,txt,url) in enumerate(links):
        cx_ = i*seg + seg/2
        cv.setFont("Helvetica-Bold",7.5); cv.setFillColor(GOLD)
        cv.drawCentredString(cx_, FOOTER_H-14, lbl)
        cv.setFont("Helvetica",7)
        fc = HexColor("#7BBFFF") if url else HexColor("#AAAAAA")
        cv.setFillColor(fc)
        uw = cv.stringWidth(txt,"Helvetica",7)
        cv.drawCentredString(cx_, FOOTER_H-26, txt)
        if url:
            cv.linkURL(url,(cx_-uw/2,FOOTER_H-31,cx_+uw/2,FOOTER_H-20),relative=0)
        if i<len(links)-1:
            cv.setStrokeColor(HexColor("#333333")); cv.setLineWidth(0.5)
            cv.line((i+1)*seg,6,(i+1)*seg,FOOTER_H-6)


# ═══════════════════════════════════════════════════════════════════════════
#  PAGE 1: Model Mastery | Advanced Prompting | Knowledge Bases & RAG
# ═══════════════════════════════════════════════════════════════════════════
def page1(cv):
    page_header(cv, 1,
        "Model mastery · Advanced prompting · Knowledge bases & RAG · "
        "For team leads, power users & builders")

    # Content starts here
    top = H - HEADER_H - STRIPE_H
    bot = FOOTER_H

    # ── ROW 1 (top half): 3 columns — Model Deep Dive | Prompt Architecture | Prompt Anti-Patterns
    # Heights
    ROW1_H = 296   # 37 × 8pt
    ROW2_H = top - bot - ROW1_H - 3*GUTTER  # remainder

    # Column widths for row 1 (3 cols, unequal)
    C1W = 204   # Model deep dive
    C2W = 196   # Prompt architecture
    C3W = CW - C1W - C2W - 2*GUTTER  # 116pt — anti-patterns / quick tips

    r1y = top - ROW1_H - GUTTER
    c1x = MARGIN
    c2x = MARGIN + C1W + GUTTER
    c3x = MARGIN + C1W + GUTTER + C2W + GUTTER

    rr(cv,c1x,r1y,C1W,ROW1_H,r=8,fill=GOLD_TINT,stroke=RULE_LINE,sw=0.8)
    rr(cv,c2x,r1y,C2W,ROW1_H,r=8,fill=WHITE,stroke=RULE_LINE,sw=0.8)
    rr(cv,c3x,r1y,C3W,ROW1_H,r=8,fill=DARK_BG,stroke=None)

    # ── CELL 1: Model Deep Dive & Token Economics ─────────────────────────
    iy = r1y+ROW1_H-PAD-4
    iy = sec_bar(cv,"Model Selection & Token Economics",c1x+PAD,iy,C1W-2*PAD)
    iy -= 4

    models = [
        ("Haiku",  "Claude 3.5","200K","Lowest",
         "Summaries, classification, extraction, high-volume Q&A. "
         "Fastest response. Use for anything you'd send to an intern."),
        ("Lite",   "Nova Lite",  "128K","Very Low",
         "Reformatting, basic lookups, repetitive batch tasks. "
         "Cheapest option when quality tolerance is high."),
        ("Sonnet", "Claude 4",   "200K","Moderate",
         "Complex analysis, policy interpretation, detailed writing, "
         "code review. Default for all knowledge work. Start here."),
        ("Pro",    "Nova Pro",   "128K","Moderate",
         "Multimodal (text + images/video). Good for decks with visuals "
         "or image-heavy documents."),
        ("Opus",   "Claude 4",   "200K","Highest",
         "Regulatory interpretation, multi-step reasoning, agentic "
         "workflows, anything where a single error is costly."),
    ]
    for m_name, base, ctx, cost, desc in models:
        is_sonnet = m_name == "Sonnet"
        is_opus = m_name == "Opus"
        bg = GOLD if is_sonnet else (HexColor("#2A0A0A") if False else None)
        # Model name pill
        pill_w = cv.stringWidth(m_name,"Helvetica-Bold",7.5)+10
        pill_col = GOLD if is_sonnet else (ORANGE if is_opus else HexColor("#DDDDDD"))
        rr(cv,c1x+PAD,iy-1,pill_w,13,r=3,fill=pill_col)
        cv.setFillColor(BLACK if is_sonnet or is_opus else MID)
        cv.setFont("Helvetica-Bold",7.5)
        cv.drawString(c1x+PAD+4,iy+2,m_name)
        # Base + cost inline
        cv.setFont("Helvetica",7)
        cv.setFillColor(SOFT)
        tag = f"{base}  ·  {ctx}  ·  ${cost}"
        cv.drawString(c1x+PAD+pill_w+6, iy+2, tag)
        if is_sonnet:
            cv.setFont("Helvetica-Bold",7); cv.setFillColor(ORANGE)
            cv.drawString(c1x+PAD+pill_w+cv.stringWidth(tag,"Helvetica",7)+10,iy+2,"★ START HERE")
        iy -= 14
        iy = wrap(cv,desc,c1x+PAD,iy,C1W-2*PAD,"Helvetica",7.5,MID,lh=10)
        iy -= 5

    # Token cheat-sheet
    iy -= 2
    cv.setStrokeColor(RULE_LINE); cv.setLineWidth(0.5)
    cv.line(c1x+PAD,iy+3,c1x+C1W-PAD,iy+3)
    iy -= 8
    cv.setFont("Helvetica-Bold",7.5); cv.setFillColor(GOLD)
    cv.drawString(c1x+PAD,iy,"TOKEN CHEAT SHEET")
    iy -= 10
    tokens = [
        ("1 token","≈ ¾ of a word"),
        ("200-word email","≈ 270 tokens"),
        ("10-page report","≈ 6,700 tokens"),
        ("RAG injection (5 chunks)","≈ 2,500 tokens"),
        ("Max output / response","≈ 48,000 words"),
        ("Switch models mid-chat","@ModelName in chat"),
    ]
    for label,val in tokens:
        cv.setFont("Helvetica-Bold",7); cv.setFillColor(MID)
        cv.drawString(c1x+PAD,iy,label)
        cv.setFont("Helvetica",7); cv.setFillColor(SOFT)
        cv.drawRightString(c1x+C1W-PAD,iy,val)
        iy -= 10

    # ── CELL 2: Advanced Prompt Architecture ──────────────────────────────
    iy = r1y+ROW1_H-PAD-4
    iy = sec_bar(cv,"Advanced Prompt Architecture",c2x+PAD,iy,C2W-2*PAD)
    iy -= 4

    # CRAFT framework (Claude's recommended prompt structure)
    cv.setFont("Helvetica-Bold",8.5); cv.setFillColor(GOLD)
    cv.drawString(c2x+PAD,iy,"The CRAFT Framework")
    iy -= 13
    craft = [
        ("C","Context",
         "Background, constraints, who you are, what this is for"),
        ("R","Role",
         "\"You are a senior Treasury analyst at Flagstar...\" "
         "— primes the model's perspective and expertise level"),
        ("A","Action",
         "Precise verb: analyze / draft / compare / extract / evaluate. "
         "Avoid: 'help me with' or 'tell me about'"),
        ("F","Format",
         "\"Return as a markdown table with columns X,Y,Z\" or "
         "\"3 bullet points, max 25 words each\" — be exact"),
        ("T","Tone & Target",
         "Audience, reading level, formality. "
         "\"Plain English for a non-finance VP\" changes everything"),
    ]
    for letter_,name,desc_ in craft:
        # Letter badge
        cv.setFillColor(GOLD)
        cv.roundRect(c2x+PAD,iy-2,14,14,3,fill=1,stroke=0)
        cv.setFillColor(BLACK); cv.setFont("Helvetica-Bold",9)
        cv.drawCentredString(c2x+PAD+7,iy+2,letter_)
        cv.setFont("Helvetica-Bold",8.5); cv.setFillColor(BLACK)
        cv.drawString(c2x+PAD+18,iy,name)
        iy -= 12
        iy = wrap(cv,desc_,c2x+PAD+18,iy,C2W-2*PAD-18,"Helvetica",7.5,MID,lh=10)
        iy -= 4

    iy -= 4
    cv.setStrokeColor(RULE_LINE); cv.setLineWidth(0.5)
    cv.line(c2x+PAD,iy+3,c2x+C2W-PAD,iy+3)
    iy -= 8

    cv.setFont("Helvetica-Bold",7.5); cv.setFillColor(GOLD)
    cv.drawString(c2x+PAD,iy,"POWER TECHNIQUES")
    iy -= 11

    techniques = [
        ("Chain-of-thought",
         "Add \"think step by step\" or \"show your reasoning\" to any "
         "analytical prompt. Dramatically improves accuracy on multi-step problems."),
        ("Few-shot examples",
         "Show the model 1–2 examples of the exact output you want before "
         "asking. \"Here's a good example: [X]. Now do the same for [Y].\""),
        ("Negative constraints",
         "\"Do NOT include generic advice. Do NOT exceed 300 words. "
         "Do NOT use bullet points.\" Negatives are processed reliably."),
        ("Structured output",
         "\"Return JSON with keys: risk, likelihood, impact, mitigation.\" "
         "or \"Markdown table with exactly 4 columns.\" Machines parse, humans skim."),
        ("Iterative refinement",
         "Build on responses: \"Make the opening stronger\" → "
         "\"Reduce to half the length\" → \"Add a concrete Flagstar example\". "
         "One conversation = one working session."),
        ("Persona persistence",
         "Use Memory (sidebar) to permanently store your role, preferred style, "
         "and recurring acronyms. The model remembers across every future chat."),
    ]
    for title_,body_ in techniques:
        cv.setFont("Helvetica-Bold",7.5); cv.setFillColor(BLUE_HL)
        cv.drawString(c2x+PAD,iy,title_)
        iy -= 11
        iy = wrap(cv,body_,c2x+PAD,iy,C2W-2*PAD,"Helvetica",7.5,MID,lh=10)
        iy -= 5

    # ── CELL 3: Anti-Patterns & Quick Wins (dark bg) ──────────────────────
    iy = r1y+ROW1_H-PAD-4
    cv.setFont("Helvetica-Bold",7.5); cv.setFillColor(GOLD)
    cv.drawString(c3x+PAD,iy,"ANTI-PATTERNS")
    iy -= 11
    antis = [
        "Vague ask: \"Help me with this\" → be explicit about task, format, and audience",
        "Using Opus for simple summaries → wasteful; switch to Haiku",
        "Ignoring the first response → iterate, don't restart from scratch",
        "No context → AI has no idea who will read this or why",
        "Uploading massive files with no specific question → scopes nothing",
        "Treating output as final → always review before any official use",
        "Long context without pruning → stale history confuses responses; start fresh",
        "Asking everything at once → break complex work into sequential steps",
    ]
    for a in antis:
        cv.setFillColor(WARN_RED); cv.setFont("Helvetica-Bold",9)
        cv.drawString(c3x+PAD,iy,"✘")
        iy = wrap(cv,a,c3x+PAD+12,iy,C3W-2*PAD-12,"Helvetica",7,HexColor("#CCCCCC"),lh=9.5)
        iy -= 5

    iy -= 4
    cv.setStrokeColor(HexColor("#333333")); cv.setLineWidth(0.5)
    cv.line(c3x+PAD,iy+2,c3x+C3W-PAD,iy+2)
    iy -= 8

    cv.setFont("Helvetica-Bold",7.5); cv.setFillColor(GOLD)
    cv.drawString(c3x+PAD,iy,"QUICK WINS")
    iy -= 11
    quick = [
        "Type / in chat to see all prompt templates",
        "Type # to reference a knowledge base",
        "Type @ to switch models mid-conversation",
        "Type $ to activate a Skill instruction set",
        "Dictate with the microphone icon",
        "Export chats as Word or PDF",
        "Favorite any response with the ★ icon",
        "Add to Notes for persistent reference",
    ]
    for q in quick:
        cv.setFillColor(GOLD); cv.setFont("Helvetica-Bold",9)
        cv.drawString(c3x+PAD,iy,"›")
        iy = wrap(cv,q,c3x+PAD+10,iy,C3W-2*PAD-10,"Helvetica",7,
                  HexColor("#CCCCCC"),lh=9.5)
        iy -= 4

    # ── ROW 2 (bottom half): 2 columns — Knowledge Base Mastery | RAG Deep Dive
    r2y = FOOTER_H + GUTTER
    rr(cv,MARGIN,r2y,(CW-GUTTER)//2,ROW2_H-GUTTER,r=8,fill=WHITE,stroke=RULE_LINE,sw=0.8)
    rr(cv,MARGIN+(CW-GUTTER)//2+GUTTER,r2y,(CW-GUTTER)//2,ROW2_H-GUTTER,
       r=8,fill=GOLD_TINT,stroke=RULE_LINE,sw=0.8)

    SC = (CW-GUTTER)//2
    c_kb = MARGIN
    c_rag = MARGIN + SC + GUTTER

    # LEFT: Knowledge Base Mastery
    iy = r2y + ROW2_H - GUTTER - PAD
    iy = sec_bar(cv,"Knowledge Base Mastery",c_kb+PAD,iy,SC-2*PAD)
    iy -= 6

    cv.setFont("Helvetica-Bold",8); cv.setFillColor(BLACK)
    cv.drawString(c_kb+PAD,iy,"How RAG works — what actually happens when you upload a file:")
    iy -= 13

    rag_steps = [
        ("Upload","Apache Tika extracts text from 1,000+ formats (PDF, Word, Excel, PPT, HTML, email, ZIP...)"),
        ("Chunk","Document split into ~1,500-character segments with configurable overlap to preserve context across boundaries"),
        ("Embed","Each chunk converted to a vector (Cohere Embed v4) — a mathematical fingerprint of its meaning"),
        ("Store","Vectors saved in PGVector (PostgreSQL) inside Flagstar's AWS — fully encrypted, never external"),
        ("Retrieve","Your question is also embedded; system finds top 5 most semantically similar chunks"),
        ("Answer","Those 5 chunks injected into the AI's context window with citations → grounded, cited response"),
    ]
    for i,(step,desc_) in enumerate(rag_steps):
        cv.setFillColor(GOLD); cv.setFont("Helvetica-Bold",8)
        cv.drawString(c_kb+PAD,iy,f"{i+1}. {step}")
        iy -= 11
        iy = wrap(cv,desc_,c_kb+PAD+8,iy,SC-2*PAD-8,"Helvetica",7.5,MID,lh=10)
        iy -= 4

    iy -= 4
    cv.setStrokeColor(RULE_LINE); cv.setLineWidth(0.5)
    cv.line(c_kb+PAD,iy+2,c_kb+SC-PAD,iy+2)
    iy -= 10

    cv.setFont("Helvetica-Bold",8); cv.setFillColor(GOLD)
    cv.drawString(c_kb+PAD,iy,"Retrieval Modes")
    iy -= 12

    modes = [
        ("Focused Retrieval (default)",GOLD,
         "Sends only the top 5 most relevant chunks (~2,500 tokens). "
         "Best for large document collections. Efficient and fast."),
        ("Full Context",ORANGE,
         "Injects the complete file every message. Only for short "
         "reference material that is always relevant (style guides, templates). "
         "WARNING: consumes tokens rapidly — impractical for large docs."),
    ]
    for mode_name, mc, mode_desc in modes:
        rr(cv,c_kb+PAD,iy-2,cv.stringWidth(mode_name,"Helvetica-Bold",7.5)+8,13,r=3,fill=mc)
        cv.setFillColor(BLACK); cv.setFont("Helvetica-Bold",7.5)
        cv.drawString(c_kb+PAD+4,iy+2,mode_name)
        iy -= 14
        iy = wrap(cv,mode_desc,c_kb+PAD+6,iy,SC-2*PAD-6,"Helvetica",7.5,MID,lh=10)
        iy -= 6

    # RIGHT: KB Best Practices + File Limits
    iy = r2y + ROW2_H - GUTTER - PAD
    iy = sec_bar(cv,"Knowledge Base Best Practices",c_rag+PAD,iy,SC-2*PAD)
    iy -= 6

    kb_bps = [
        ("Organize by domain",
         "Create separate KBs: \"Compliance Policies\", \"ALM Procedures\", "
         "\"ALCO Minutes\". Focused scope = higher retrieval precision."),
        ("Name & describe precisely",
         "The description trains the AI's discovery. Write it like a search "
         "query: \"Flagstar FTP methodology, ALM policies, interest rate risk "
         "procedures updated 2024–2025.\""),
        ("Keep documents current",
         "Outdated documents produce outdated answers. Assign a KB owner "
         "per department and run a quarterly review cycle."),
        ("Test before sharing",
         "Ask 5–10 representative questions and verify citations pull from "
         "the right chunks. Adjust document structure if retrieval is weak."),
        ("Scope your agents",
         "When building a custom model, attach only the KBs it needs. "
         "Unscoped models can retrieve from any KB — increases hallucination risk."),
        ("Prefer text-heavy files",
         "Charts, images, and complex table formatting are NOT extracted. "
         "Excel formulas show only computed values. Scanned PDFs require OCR."),
        ("Use overlap on flowing docs",
         "For documents where meaning spans section boundaries (legal contracts, "
         "multi-part analyses), chunk overlap preserves context continuity."),
    ]
    for title_,body_ in kb_bps:
        cv.setFillColor(GOLD); cv.setFont("Helvetica-Bold",8.5)
        cv.drawString(c_rag+PAD,iy,"·")
        cv.setFont("Helvetica-Bold",8); cv.setFillColor(BLACK)
        cv.drawString(c_rag+PAD+10,iy,title_)
        iy -= 12
        iy = wrap(cv,body_,c_rag+PAD+10,iy,SC-2*PAD-10,"Helvetica",7.5,MID,lh=10)
        iy -= 5

    # File limits inline
    iy -= 2
    cv.setStrokeColor(RULE_LINE); cv.setLineWidth(0.5)
    cv.line(c_rag+PAD,iy+2,c_rag+SC-PAD,iy+2)
    iy -= 10
    limits = [
        ("Max file size","50 MB per file"),
        ("Max files per KB","90 files"),
        ("Supported formats","1,000+ via Apache Tika"),
        ("Embedding model","Cohere Embed v4"),
        ("Chunks returned","Top 5 per query"),
        ("Chunk size","~1,500 characters"),
    ]
    cv.setFont("Helvetica-Bold",7.5); cv.setFillColor(GOLD)
    cv.drawString(c_rag+PAD,iy,"FILE LIMITS & CONFIG"); iy -= 11
    for lbl,val in limits:
        cv.setFont("Helvetica-Bold",7.5); cv.setFillColor(MID)
        cv.drawString(c_rag+PAD,iy,lbl)
        cv.setFont("Helvetica",7.5); cv.setFillColor(SOFT)
        cv.drawRightString(c_rag+SC-PAD,iy,val)
        iy -= 10

    page_footer(cv, 1)


# ═══════════════════════════════════════════════════════════════════════════
#  PAGE 2: Custom Agents | RBAC | Doc Gen | Governance | Roadmap | Troubleshoot
# ═══════════════════════════════════════════════════════════════════════════
def page2(cv):
    cv.showPage()  # start new PDF page
    page_header(cv, 2,
        "Custom agents · RBAC & sharing · Document generation · "
        "Data governance · 2026 roadmap · Troubleshooting")

    top = H - HEADER_H - STRIPE_H
    bot = FOOTER_H

    # Page 2 layout: 3 rows
    # Row A (top): Custom Agents + RBAC  (2 cols, 258pt each, 280pt tall)
    # Row B (mid): Doc Generation + Governance  (2 cols, 258pt each, 200pt tall)
    # Row C (bot): Roadmap strip (full width, 72pt) + Troubleshooting strip (full width, 72pt)

    ROW_A_H = 276
    ROW_B_H = 200
    ROW_C_H = top - bot - ROW_A_H - ROW_B_H - 4*GUTTER

    SC = (CW - GUTTER) // 2  # 258pt
    cA = MARGIN
    cB = MARGIN + SC + GUTTER

    ra_y = top - ROW_A_H - GUTTER
    rb_y = ra_y - ROW_B_H - GUTTER
    rc_y = bot + GUTTER

    rr(cv,cA,ra_y,SC,ROW_A_H,r=8,fill=GOLD_TINT,stroke=RULE_LINE,sw=0.8)
    rr(cv,cB,ra_y,SC,ROW_A_H,r=8,fill=WHITE,stroke=RULE_LINE,sw=0.8)
    rr(cv,cA,rb_y,SC,ROW_B_H,r=8,fill=WHITE,stroke=RULE_LINE,sw=0.8)
    rr(cv,cB,rb_y,SC,ROW_B_H,r=8,fill=GOLD_TINT,stroke=RULE_LINE,sw=0.8)
    rr(cv,MARGIN,rc_y,CW,ROW_C_H,r=8,fill=DARK_BG)

    # ── ROW A LEFT: Custom Agents (Workspace → Models) ─────────────────────
    iy = ra_y+ROW_A_H-PAD-4
    iy = sec_bar(cv,"Building Custom AI Agents",cA+PAD,iy,SC-2*PAD)
    iy -= 4

    cv.setFont("Helvetica",8); cv.setFillColor(MID)
    iy = wrap(cv,
        "A Custom Model in Workspace is not a new AI — it is a configuration "
        "preset that binds a system prompt, knowledge bases, tools, skills, "
        "and capability toggles to a base model. Think of it as a purpose-built "
        "team member with a defined job, scope, and personality.",
        cA+PAD,iy,SC-2*PAD,"Helvetica",8,MID)
    iy -= 10

    cv.setFont("Helvetica-Bold",8); cv.setFillColor(GOLD)
    cv.drawString(cA+PAD,iy,"Example: Treasury Policy Assistant"); iy -= 12

    agent_steps = [
        ("Base Model","StarIQ Sonnet — strong reasoning, cost-efficient for daily queries"),
        ("System Prompt",
         "\"You are a Treasury policy expert at Flagstar. Answer questions about "
         "FTP, ALM, and interest rate risk using ONLY attached knowledge bases. "
         "Always cite your sources. Say 'I don't know' rather than guessing. "
         "Today: {{CURRENT_DATE}}, user: {{USER_NAME}}.\""),
        ("Knowledge","Attach: 'FTP Procedures', 'ALM Policy', 'ALCO Minutes' KBs"),
        ("Capabilities","Enable: Citations. Disable: Image Generation, Code Interpreter"),
        ("Access","Share with Treasury RBAC group — Read permission"),
        ("Prompt chips","Add starter suggestions: 'Summarize FTP methodology', "
         "'What is our ALM policy on duration gaps?'"),
    ]
    for step,desc_ in agent_steps:
        cv.setFillColor(ORANGE); cv.setFont("Helvetica-Bold",8)
        cv.drawString(cA+PAD,iy,f"• {step}:")
        iy -= 11
        iy = wrap(cv,desc_,cA+PAD+10,iy,SC-2*PAD-10,"Helvetica",7.5,MID,lh=10)
        iy -= 4

    iy -= 4
    cv.setStrokeColor(RULE_LINE); cv.setLineWidth(0.5)
    cv.line(cA+PAD,iy+2,cA+SC-PAD,iy+2)
    iy -= 8

    cv.setFont("Helvetica-Bold",7.5); cv.setFillColor(GOLD)
    cv.drawString(cA+PAD,iy,"SKILLS vs TOOLS vs FUNCTIONS"); iy -= 11
    svt = [
        ("Skills","Markdown instructions — teach the model HOW to think. "
         "Loaded lazily (efficient on context). Invoke with $ in chat."),
        ("Tools","Python scripts — give the model access to real-world data, "
         "APIs, and calculations. Require security code review before deploy."),
        ("Functions","Admin-only — add new AI providers, UI buttons, data filters. "
         "Not available to end users."),
    ]
    for name_,desc_ in svt:
        cv.setFont("Helvetica-Bold",7.5); cv.setFillColor(BLUE_HL)
        cv.drawString(cA+PAD,iy,name_)
        iy -= 10
        iy = wrap(cv,desc_,cA+PAD+6,iy,SC-2*PAD-6,"Helvetica",7.5,MID,lh=10)
        iy -= 5

    # ── ROW A RIGHT: RBAC & Sharing ────────────────────────────────────────
    iy = ra_y+ROW_A_H-PAD-4
    iy = sec_bar(cv,"RBAC & Sharing Strategy",cB+PAD,iy,SC-2*PAD)
    iy -= 4

    cv.setFont("Helvetica",8); cv.setFillColor(MID)
    iy = wrap(cv,
        "All Workspace resources (Models, Knowledge, Prompts, Skills, Tools) share "
        "a unified, additive permission system. Permissions NEVER deny — if any "
        "group grants access, the user has it.",
        cB+PAD,iy,SC-2*PAD,"Helvetica",8,MID)
    iy -= 10

    cv.setFont("Helvetica-Bold",8); cv.setFillColor(GOLD)
    cv.drawString(cB+PAD,iy,"Two Group Types — Use Both"); iy -= 12

    groups = [
        ("Permission Groups","Grant feature rights (image gen, code interpreter, "
         "web search). Set 'Who can share' = Nobody. Example: 'Power Users', 'Developers'."),
        ("Sharing Groups","Organize teams for resource access. Set 'Who can share' = "
         "Members or Anyone. Example: 'Treasury Team', 'HR Leadership', 'Risk Management'."),
    ]
    for g_name,g_desc in groups:
        rr(cv,cB+PAD,iy-2,cv.stringWidth(g_name,"Helvetica-Bold",8)+10,14,r=4,fill=GOLD)
        cv.setFont("Helvetica-Bold",8); cv.setFillColor(BLACK)
        cv.drawString(cB+PAD+5,iy+2,g_name)
        iy -= 15
        iy = wrap(cv,g_desc,cB+PAD+6,iy,SC-2*PAD-6,"Helvetica",7.5,MID,lh=10)
        iy -= 8

    cv.setFont("Helvetica-Bold",7.5); cv.setFillColor(GOLD)
    cv.drawString(cB+PAD,iy,"PRINCIPLE OF LEAST PRIVILEGE"); iy -= 11
    rbac_rules = [
        "Minimize Global Default Permissions — grant rights via specific groups, not globally",
        "Attach only the KBs an agent needs — unscoped models can retrieve from all user KBs",
        "Use Read access for team sharing; Write access only for designated owners",
        "KBs with confidential content → Private visibility + explicit access grants only",
        "Sync is automatic — Entra ID group memberships update on each login",
        "User Roles: Admin → full access | User → standard | Pending → new SSO accounts",
    ]
    for rule in rbac_rules:
        iy = bullet(cv,rule,cB+PAD,iy,SC-2*PAD,dot_color=GOLD,size=7.5)

    iy -= 4
    cv.setStrokeColor(RULE_LINE); cv.setLineWidth(0.5)
    cv.line(cB+PAD,iy+2,cB+SC-PAD,iy+2)
    iy -= 10

    cv.setFont("Helvetica-Bold",7.5); cv.setFillColor(GOLD)
    cv.drawString(cB+PAD,iy,"PROMPT LIBRARY WITH SLASH COMMANDS"); iy -= 11
    cv.setFont("Helvetica",7.5); cv.setFillColor(MID)
    iy = wrap(cv,
        "Create reusable prompts with interactive form variables. Users type / in chat "
        "to trigger your template — a form appears, they fill it in, output is structured.",
        cB+PAD,iy,SC-2*PAD,"Helvetica",7.5,MID,lh=10)
    iy -= 8
    vars_ = [
        ("{{project_name}}","Text input field"),
        ("{{priority | select:...}}","Dropdown: High / Medium / Low"),
        ("{{deadline | date:required}}","Date picker, required"),
        ("{{urgent | checkbox}}","Boolean toggle"),
        ("{{CURRENT_DATE}}","Auto-injected — today's date"),
        ("{{USER_NAME}}","Auto-injected — requestor's name"),
    ]
    for var,desc_ in vars_:
        cv.setFont("Courier-Bold",7); cv.setFillColor(BLUE_HL)
        vw = cv.stringWidth(var,"Courier-Bold",7)
        cv.drawString(cB+PAD,iy,var)
        cv.setFont("Helvetica",7); cv.setFillColor(SOFT)
        cv.drawString(cB+PAD+vw+6,iy,desc_)
        iy -= 10

    # ── ROW B LEFT: Document Generation & In-Chat Rendering ────────────────
    iy = rb_y+ROW_B_H-PAD-4
    iy = sec_bar(cv,"Document Generation & In-Chat Rendering",cA+PAD,iy,SC-2*PAD)
    iy -= 6

    cv.setFont("Helvetica-Bold",8); cv.setFillColor(BLACK)
    cv.drawString(cA+PAD,iy,"Generate downloadable Office files directly in chat:"); iy -= 13
    office = [
        ("Word (.docx)","Reports, summaries, proposals, meeting notes"),
        ("PowerPoint (.pptx)","Presentations with speaker notes, layouts, themes"),
        ("Excel (.xlsx)","Data exports, financial models, tracking sheets"),
    ]
    for fmt,use in office:
        cv.setFont("Helvetica-Bold",8); cv.setFillColor(BLUE_HL)
        cv.drawString(cA+PAD,iy,fmt)
        cv.setFont("Helvetica",8); cv.setFillColor(MID)
        cv.drawString(cA+PAD+cv.stringWidth(fmt,"Helvetica-Bold",8)+6,iy,f"— {use}")
        iy -= 12

    iy -= 4
    cv.setFont("Helvetica-Bold",8); cv.setFillColor(BLACK)
    cv.drawString(cA+PAD,iy,"In-chat Artifacts (no download needed):"); iy -= 13
    artifacts = [
        ("Mermaid","Flowcharts, org charts, Gantt, sequence, ERD, pie charts"),
        ("HTML","Interactive dashboards, calculators, styled reports"),
        ("SVG","Infographics, logos, technical drawings"),
        ("CSV/JSON","Tables and structured data with syntax highlighting"),
        ("LaTeX","Mathematical equations and scientific notation"),
    ]
    for art,use in artifacts:
        cv.setFont("Helvetica-Bold",8); cv.setFillColor(GOLD)
        cv.drawString(cA+PAD,iy,art)
        aw = cv.stringWidth(art,"Helvetica-Bold",8)
        cv.setFont("Helvetica",8); cv.setFillColor(MID)
        cv.drawString(cA+PAD+aw+5,iy,f"— {use}")
        iy -= 12

    iy -= 4
    cv.setStrokeColor(RULE_LINE); cv.setLineWidth(0.5)
    cv.line(cA+PAD,iy+2,cA+SC-PAD,iy+2)
    iy -= 10
    cv.setFont("Helvetica-Bold",7.5); cv.setFillColor(GOLD)
    cv.drawString(cA+PAD,iy,"MULTI-MODEL WORKFLOW (example)"); iy -= 11
    workflow = [
        "@Haiku — extract all dates, amounts, party names from contract",
        "@Sonnet — analyze extracted terms for risk and ambiguity",
        "@Opus — draft legal memo with full reasoning and recommendations",
    ]
    for step in workflow:
        cv.setFillColor(ORANGE); cv.setFont("Helvetica-Bold",9)
        cv.drawString(cA+PAD,iy,"›")
        iy = wrap(cv,step,cA+PAD+12,iy,SC-2*PAD-12,"Helvetica",7.5,MID,lh=10)
        iy -= 5
    cv.setFont("Helvetica-Oblique",7); cv.setFillColor(SOFT)
    cv.drawString(cA+PAD,iy,"Documents available for download for 30 days after generation.")

    # ── ROW B RIGHT: Data Governance & Compliance ──────────────────────────
    iy = rb_y+ROW_B_H-PAD-4
    iy = sec_bar(cv,"Data Governance & Compliance",cB+PAD,iy,SC-2*PAD)
    iy -= 6

    classes = [
        ("Public","✅","Annual reports, regulatory guidance, press releases — freely uploadable"),
        ("Internal","✅","Procedures, meeting notes, project plans — appropriate for StarIQ"),
        ("Confidential","⚠","Strategy docs, non-public financials — configure KB access controls first"),
        ("Restricted","❌","Customer PII, SSNs, account numbers, credentials — DO NOT upload without explicit authorization"),
    ]
    for cls,icon,desc_ in classes:
        col = DO_GREEN if icon=="✅" else (HexColor("#CC6600") if icon=="⚠" else WARN_RED)
        cv.setFont("Helvetica-Bold",8); cv.setFillColor(col)
        cv.drawString(cB+PAD,iy,f"{icon}  {cls}")
        iy -= 11
        iy = wrap(cv,desc_,cB+PAD+10,iy,SC-2*PAD-10,"Helvetica",7.5,MID,lh=10)
        iy -= 5

    iy -= 4
    cv.setStrokeColor(RULE_LINE); cv.setLineWidth(0.5)
    cv.line(cB+PAD,iy+2,cB+SC-PAD,iy+2)
    iy -= 10

    cv.setFont("Helvetica-Bold",7.5); cv.setFillColor(GOLD)
    cv.drawString(cB+PAD,iy,"USE THE AI INTAKE PROCESS WHEN:"); iy -= 11
    intake = [
        "Building agents that access sensitive or regulated data",
        "Integrating StarIQ with other Flagstar systems or databases",
        "Deploying AI for customer-facing processes",
        "Any initiative involving GLBA, SOX, HMDA regulated data",
        "Using or evaluating third-party AI services or vendors",
    ]
    for item in intake:
        iy = bullet(cv,item,cB+PAD,iy,SC-2*PAD,dot_color=ORANGE,size=7.5)

    cv.setFont("Helvetica-Oblique",7.5); cv.setFillColor(SOFT)
    iy -= 4
    cv.drawString(cB+PAD,iy,
        "Everyday use (summarizing, drafting, analyzing) does NOT require intake.")

    # ── ROW C: Roadmap + Troubleshooting on dark bg ─────────────────────────
    total_rc = CW
    road_w = total_rc * 0.55
    trouble_w = total_rc - road_w - GUTTER

    road_x = MARGIN
    trouble_x = MARGIN + road_w + GUTTER

    iy_road = rc_y + ROW_C_H - PAD - 4
    iy_tbl = rc_y + ROW_C_H - PAD - 4

    cv.setFont("Helvetica-Bold",8); cv.setFillColor(GOLD)
    cv.drawString(road_x+PAD,iy_road,"2026 ROADMAP")
    cv.drawString(trouble_x+PAD,iy_tbl,"TROUBLESHOOTING QUICK REFERENCE")
    iy_road -= 12; iy_tbl -= 12

    quarters = [
        ("Q1 ✓","Launched Feb 2026",
         "Core platform, all models, KBs & RAG, prompt libraries, voice, accessibility"),
        ("Q2","Apr–Jun 2026",
         "OneDrive & SharePoint RAG integration · Mobile PWA · AI Web Search (Palo Alto Prisma)"),
        ("Q3","Jul–Sep 2026",
         "Model Context Protocol · Python AI Tool Framework · Code Interpreter enhancements"),
        ("Q4","Oct–Dec 2026",
         "Custom Agents (IT, HR, Finance) · Agent Policy Controls · Agent Evaluation Pipeline"),
    ]
    for q,when,desc_ in quarters:
        col = DO_GREEN if "✓" in q else GOLD
        cv.setFont("Helvetica-Bold",8); cv.setFillColor(col)
        cv.drawString(road_x+PAD,iy_road,q)
        cv.setFont("Helvetica-Oblique",7.5); cv.setFillColor(SOFT)
        qw = cv.stringWidth(q,"Helvetica-Bold",8)
        cv.drawString(road_x+PAD+qw+6,iy_road,when)
        iy_road -= 11
        iy_road = wrap(cv,desc_,road_x+PAD+6,iy_road,road_w-2*PAD-6,
                       "Helvetica",7.5,HexColor("#CCCCCC"),lh=10)
        iy_road -= 6

    troubles = [
        ("SSO login fails","Access via myapps.microsoft.com; check OAuth redirect URIs"),
        ("Doc not found in KB","Check Documents tab for processing status; verify # reference"),
        ("Outdated AI answers","Upload current docs; use web search when live (Q2 2026)"),
        ("Slow responses","Switch to Haiku/Lite; start a new chat; use Focused Retrieval"),
        ("Token limit hit","New chat + summarize prior context; use concise prompts"),
        ("Account 'Pending'","Contact AI Team on Teams (g2w1hjy) to elevate role"),
    ]
    for issue,fix in troubles:
        cv.setFont("Helvetica-Bold",7.5); cv.setFillColor(WARN_RED)
        cv.drawString(trouble_x+PAD,iy_tbl,issue)
        iy_tbl -= 11
        iy_tbl = wrap(cv,fix,trouble_x+PAD+6,iy_tbl,trouble_w-2*PAD-6,
                      "Helvetica",7.5,HexColor("#CCCCCC"),lh=10)
        iy_tbl -= 6

    page_footer(cv, 2)


# ── Run ───────────────────────────────────────────────────────────────────
def build(out_path):
    cv = canvas.Canvas(out_path, pagesize=letter)
    cv.setFillColor(CREAM)
    cv.rect(0, 0, W, H, fill=1, stroke=0)
    page1(cv)
    page2(cv)
    cv.save()
    print(f"✅  {out_path}")


if __name__ == "__main__":
    build("/home/user/Test1/StarIQ_PowerUser_Guide.pdf")
