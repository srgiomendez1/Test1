"""
StarIQ Executive One-Pager v2
Design Architecture: 8pt baseline grid, Z-pattern flow, 3-level typography,
hierarchical cell sizing, color as signal, ≥25% white space per cell.

Layout (letter, 612×792pt):
  Header (112pt, black)  →  Entry point, brand anchor
  Gold stripe (8pt)
  Hero row (280pt)       →  3 unequal cols: What+Access | Use Cases | Model Picker
  Gap (16pt)
  Support row (180pt)    →  2 equal cols: Knowledge Base | Ground Rules
  Gap (16pt)
  Safety strip (48pt)    →  Full-width trust band
  Footer (80pt, black)   →  3 clickable links
"""

import math, zipfile, io
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color
from PIL import Image

# ── Brand palette (color as signal) ───────────────────────────────────────
GOLD       = HexColor("#FFB81C")   # accent / numbers / borders — max 12% page
ORANGE     = HexColor("#FF6200")   # CTA / alert — use once max
BLACK      = HexColor("#0D0D0D")   # anchor / header / footer
WHITE      = HexColor("#FFFFFF")   # neutral content bg
CREAM      = HexColor("#FFFDF7")   # warm content bg (alternate)
GOLD_TINT  = HexColor("#FFF5D6")   # light gold for section highlight
MID        = HexColor("#4A4A4A")   # body text (6.8:1 contrast on cream ✓)
SOFT       = HexColor("#888888")   # secondary / labels
DO_GREEN   = HexColor("#1D6B3E")   # Do items
DONT_RED   = HexColor("#A52A2A")   # Don't items
RULE_LINE  = HexColor("#E0D0A0")   # subtle dividers

# ── 8pt baseline grid ─────────────────────────────────────────────────────
U = 8           # 1 grid unit = 8pt
W, H = letter   # 612 × 792

MARGIN   = 5*U  # 40pt  horizontal margin
GUTTER   = 2*U  # 16pt  between cells
PAD      = 2*U  # 16pt  inside cell
CW       = W - 2*MARGIN               # 532pt content width

# Row heights
HEADER_H = 14*U  # 112pt
STRIPE_H =  1*U  #   8pt
HERO_H   = 35*U  # 280pt  ← largest, most important row
GAP      =  2*U  #  16pt
MID_H    = 23*U  # 184pt
SAFETY_H =  6*U  #  48pt
FOOTER_H = 10*U  #  80pt

# Hero column widths (3-col, unequal = visual hierarchy)
HC_LEFT  = 232   # What is StarIQ + Access steps
HC_MID   = 184   # 5 Use Cases
HC_RIGHT = CW - HC_LEFT - HC_MID - 2*GUTTER   # 100pt Model Picker

# Support column widths (2-col, equal)
SC = (CW - GUTTER) // 2   # 258pt each

# Y positions (from bottom)
footer_bot  = 0
footer_top  = FOOTER_H            # 80
safety_bot  = footer_top
safety_top  = safety_bot + SAFETY_H + GAP  # 144
mid_bot     = safety_top
mid_top     = mid_bot + MID_H     # 328
hero_bot    = mid_top + GAP       # 344
hero_top    = hero_bot + HERO_H   # 624
stripe_bot  = hero_top
stripe_top  = stripe_bot + STRIPE_H   # 632
header_bot  = stripe_top
header_top  = header_bot + HEADER_H   # 744  (< 792, leaves 48pt top margin)

# Push header to true top of page
OFFSET = H - header_top   # shift everything up by this
def Y(y): return y + OFFSET   # apply offset to all y coords


# ── Helpers ───────────────────────────────────────────────────────────────
def rr(cv, x, y, w, h, r=6, fill=WHITE, stroke=None, sw=0.5):
    """Rounded rectangle."""
    p = cv.beginPath()
    p.moveTo(x+r, y); p.lineTo(x+w-r, y)
    p.arcTo(x+w-r, y, x+w, y+r, -90, 90)
    p.lineTo(x+w, y+h-r)
    p.arcTo(x+w-r, y+h-r, x+w, y+h, 0, 90)
    p.lineTo(x+r, y+h)
    p.arcTo(x, y+h-r, x+r, y+h, 90, 90)
    p.lineTo(x, y+r)
    p.arcTo(x, y, x+r, y+r, 180, 90)
    p.close()
    cv.setFillColor(fill)
    if stroke: cv.setStrokeColor(stroke); cv.setLineWidth(sw)
    cv.drawPath(p, fill=1, stroke=bool(stroke))

def text_block(cv, lines_or_str, x, y, max_w, font, size, color,
               lh_mult=1.4, max_lines=None):
    """Draw wrapped text; return y below last line."""
    if isinstance(lines_or_str, str):
        raw_lines = lines_or_str.split("\n")
    else:
        raw_lines = lines_or_str
    cv.setFont(font, size)
    cv.setFillColor(color)
    lh = size * lh_mult
    drawn = 0
    for raw in raw_lines:
        words = raw.split()
        if not words:
            y -= lh * 0.5; continue
        buf = []
        for w in words:
            test = " ".join(buf + [w])
            if cv.stringWidth(test, font, size) <= max_w:
                buf.append(w)
            else:
                if buf:
                    cv.drawString(x, y, " ".join(buf)); y -= lh; drawn += 1
                    if max_lines and drawn >= max_lines: return y
                buf = [w]
        if buf:
            cv.drawString(x, y, " ".join(buf)); y -= lh; drawn += 1
            if max_lines and drawn >= max_lines: return y
    return y

def section_header(cv, label, x, y, w, color=GOLD):
    """Colored label bar above a section."""
    BAR_H = 14
    rr(cv, x, y, w, BAR_H, r=4, fill=color)
    cv.setFont("Helvetica-Bold", 7.5)
    cv.setFillColor(BLACK)
    cv.drawString(x + 6, y + 3.5, label.upper())
    return y - 6   # returns y just below bar

def icon_badge(cv, x, cy, symbol, bg, fg=WHITE, r=10):
    """Filled circle with a character inside."""
    cv.setFillColor(bg)
    cv.circle(x + r, cy, r, fill=1, stroke=0)
    cv.setFillColor(fg)
    cv.setFont("Helvetica-Bold", 9)
    cv.drawCentredString(x + r, cy - 3, symbol)
    return x + r * 2 + 6  # x after badge

def flagstar_logo(cv, x, y):
    """Programmatic Flagstar 4-pointed star + wordmark."""
    cx, cy = x + 10, y + 7
    cv.setFillColor(GOLD)
    pts = 4; r_out = 9; r_in = 3
    p = cv.beginPath()
    for i in range(pts * 2):
        angle = math.pi / pts * i - math.pi / 2
        r = r_out if i % 2 == 0 else r_in
        px = cx + r * math.cos(angle)
        py = cy + r * math.sin(angle)
        p.moveTo(px, py) if i == 0 else p.lineTo(px, py)
    p.close(); cv.drawPath(p, fill=1, stroke=0)
    cv.setFillColor(WHITE)
    cv.setFont("Helvetica-Bold", 14)
    cv.drawString(cx + 13, y + 1, "flagstar")


# ── Main ──────────────────────────────────────────────────────────────────
def build(out_path):
    cv = canvas.Canvas(out_path, pagesize=letter)

    # ── PAGE BACKGROUND ──────────────────────────────────────────────────
    cv.setFillColor(CREAM)
    cv.rect(0, 0, W, H, fill=1, stroke=0)

    # ── HEADER (Z-flow entry point) ───────────────────────────────────────
    cv.setFillColor(BLACK)
    cv.rect(0, Y(header_bot), W, HEADER_H, fill=1, stroke=0)

    # Large title: "StarIQ" gold + " at a Glance" white  (L1: 38pt)
    tx = MARGIN
    ty = Y(header_bot) + HEADER_H - 38
    cv.setFillColor(GOLD)
    cv.setFont("Helvetica-Bold", 38)
    sw = cv.stringWidth("StarIQ", "Helvetica-Bold", 38)
    cv.drawString(tx, ty, "StarIQ")
    cv.setFillColor(WHITE)
    cv.drawString(tx + sw + 4, ty, " at a Glance")

    # Subtitle (L3: 9pt, gray)
    cv.setFont("Helvetica", 9)
    cv.setFillColor(HexColor("#999999"))
    cv.drawString(tx, ty - 16,
        "Your AI Assistant at Flagstar  ·  Powered by Amazon Bedrock  ·  "
        "Secure & Private by Design")

    # Orange pill: "No tech skills needed"
    pill_w, pill_h = 140, 20
    pill_x, pill_y = tx, Y(header_bot) + 14
    rr(cv, pill_x, pill_y, pill_w, pill_h, r=5, fill=ORANGE)
    cv.setFillColor(WHITE)
    cv.setFont("Helvetica-Bold", 8)
    cv.drawCentredString(pill_x + pill_w/2, pill_y + 6, "✦  No tech skills needed")

    # Flagstar logo (top-right of header)
    flagstar_logo(cv, W - MARGIN - 110, Y(header_bot) + HEADER_H - 30)

    # ── GOLD STRIPE ───────────────────────────────────────────────────────
    cv.setFillColor(GOLD)
    cv.rect(0, Y(stripe_bot), W, STRIPE_H, fill=1, stroke=0)

    # ── HERO ROW ──────────────────────────────────────────────────────────
    hero_y_base = Y(hero_bot)
    hero_x = [MARGIN,
               MARGIN + HC_LEFT + GUTTER,
               MARGIN + HC_LEFT + GUTTER + HC_MID + GUTTER]

    # Cell backgrounds
    rr(cv, hero_x[0], hero_y_base, HC_LEFT, HERO_H, r=8, fill=WHITE,
       stroke=RULE_LINE, sw=0.8)
    rr(cv, hero_x[1], hero_y_base, HC_MID, HERO_H, r=8, fill=GOLD_TINT,
       stroke=RULE_LINE, sw=0.8)
    rr(cv, hero_x[2], hero_y_base, HC_RIGHT, HERO_H, r=8, fill=BLACK,
       stroke=None)

    # ── HERO LEFT: What is StarIQ? + 3-step access ────────────────────────
    iy = Y(hero_bot) + HERO_H - PAD - 4
    iy = section_header(cv, "What is StarIQ?", hero_x[0]+PAD, iy,
                         HC_LEFT - 2*PAD, color=GOLD)
    iy -= 6
    iy = text_block(cv,
        "A secure, browser-based AI assistant — your brilliant analyst, "
        "writer, and researcher available 24/7 inside Flagstar's private AWS. "
        "No technical background required.",
        hero_x[0]+PAD, iy, HC_LEFT - 2*PAD,
        "Helvetica", 8.5, MID)
    iy -= 12

    # Divider
    cv.setStrokeColor(RULE_LINE); cv.setLineWidth(0.5)
    cv.line(hero_x[0]+PAD, iy+4, hero_x[0]+HC_LEFT-PAD, iy+4)
    iy -= 10

    iy = section_header(cv, "Access in 3 Steps", hero_x[0]+PAD, iy,
                         HC_LEFT - 2*PAD, color=GOLD)
    iy -= 8

    steps = [
        ("1", "Go to myapps.microsoft.com"),
        ("2", "Click the StarIQ icon in your app list"),
        ("3", "Sign in with Flagstar credentials (SSO — no new password)"),
    ]
    for num, step_text in steps:
        # Numbered badge
        badge_r = 9
        badge_x = hero_x[0] + PAD + badge_r
        badge_cy = iy - 1
        cv.setFillColor(GOLD)
        cv.circle(badge_x, badge_cy, badge_r, fill=1, stroke=0)
        cv.setFillColor(BLACK)
        cv.setFont("Helvetica-Bold", 9)
        cv.drawCentredString(badge_x, badge_cy - 3, num)
        # Step text
        text_x = hero_x[0] + PAD + badge_r*2 + 6
        iy = text_block(cv, step_text, text_x, iy,
                        HC_LEFT - 2*PAD - badge_r*2 - 6,
                        "Helvetica", 8.5, MID)
        iy -= 7

    # ── HERO CENTER: 5 Use Cases ──────────────────────────────────────────
    iy = Y(hero_bot) + HERO_H - PAD - 4
    iy = section_header(cv, "5 Things You Can Do Today", hero_x[1]+PAD, iy,
                         HC_MID - 2*PAD, color=GOLD)
    iy -= 8

    use_cases = [
        ("D", ORANGE, "Summarize Documents",
         "\"Summarize this report in 5 bullets with key decisions.\""),
        ("@", HexColor("#1976D2"), "Draft Emails & Memos",
         "\"Write a professional email about our Q2 deadline change.\""),
        ("≡", HexColor("#2E7D32"), "Analyze Data",
         "\"What are the top trends and outliers in this spreadsheet?\""),
        ("*", HexColor("#7B1FA2"), "Brainstorm Ideas",
         "\"Give me 10 ideas on efficiency to present to leadership.\""),
        ("?", HexColor("#00838F"), "Explain Complex Topics",
         "\"Explain Funds Transfer Pricing in plain English.\""),
    ]
    for sym, col, title, prompt in use_cases:
        # Icon circle
        badge_r = 9; badge_x_c = hero_x[1] + PAD + badge_r
        badge_cy = iy - 2
        cv.setFillColor(col)
        cv.circle(badge_x_c, badge_cy, badge_r, fill=1, stroke=0)
        cv.setFillColor(WHITE)
        cv.setFont("Helvetica-Bold", 9)
        cv.drawCentredString(badge_x_c, badge_cy - 3, sym)
        # Title + prompt
        tx2 = hero_x[1] + PAD + badge_r*2 + 6
        tw2 = HC_MID - 2*PAD - badge_r*2 - 6
        cv.setFont("Helvetica-Bold", 8.5); cv.setFillColor(DARK if False else MID)
        cv.setFillColor(BLACK)
        cv.drawString(tx2, iy, title)
        iy -= 11
        cv.setFont("Helvetica-Oblique", 7.5); cv.setFillColor(SOFT)
        iy = text_block(cv, prompt, tx2, iy, tw2,
                        "Helvetica-Oblique", 7.5, SOFT, lh_mult=1.35)
        iy -= 8

    # ── HERO RIGHT: Pick Your Model ───────────────────────────────────────
    iy = Y(hero_bot) + HERO_H - PAD - 4
    # Label
    cv.setFont("Helvetica-Bold", 7.5)
    cv.setFillColor(GOLD)
    cv.drawString(hero_x[2] + PAD, iy, "PICK YOUR MODEL")
    iy -= 18

    models = [
        ("⚡", GOLD, "Haiku / Lite",
         "Quick tasks,\nsummaries,\nsimple Q&A", False),
        ("★", ORANGE, "Sonnet",
         "Analysis,\nwriting, code,\nmost daily work", True),
        ("◆", WHITE, "Opus",
         "Critical decisions,\ncomplex reasoning,\nhigh stakes", False),
    ]
    for sym, col, name, desc, is_rec in models:
        # Highlight recommended
        if is_rec:
            rr(cv, hero_x[2]+PAD-4, iy-60, HC_RIGHT-PAD, 68, r=5,
               fill=HexColor("#2A2A2A"))
            cv.setFillColor(ORANGE)
            cv.setFont("Helvetica-Bold", 6.5)
            cv.drawString(hero_x[2]+PAD, iy, "★ START HERE")
            iy -= 10

        # Symbol
        cv.setFont("Helvetica-Bold", 16)
        cv.setFillColor(col)
        cv.drawString(hero_x[2] + PAD, iy - 4, sym)
        # Name
        cv.setFont("Helvetica-Bold", 9)
        cv.setFillColor(WHITE)
        cv.drawString(hero_x[2] + PAD + 18, iy, name)
        iy -= 13
        # Desc
        cv.setFont("Helvetica", 7.5)
        cv.setFillColor(HexColor("#BBBBBB"))
        for line in desc.split("\n"):
            cv.drawString(hero_x[2] + PAD + 18, iy, line)
            iy -= 10
        iy -= 8

    # Speed hint at bottom of model col
    cv.setFont("Helvetica-Oblique", 7)
    cv.setFillColor(SOFT)
    cv.drawString(hero_x[2]+PAD, Y(hero_bot) + PAD + 10,
                  "Type @Sonnet to switch mid-chat")

    # ── SUPPORT ROW ───────────────────────────────────────────────────────
    mid_y_base = Y(mid_bot)
    mid_x = [MARGIN, MARGIN + SC + GUTTER]

    rr(cv, mid_x[0], mid_y_base, SC, MID_H, r=8,
       fill=GOLD_TINT, stroke=RULE_LINE, sw=0.8)
    rr(cv, mid_x[1], mid_y_base, SC, MID_H, r=8,
       fill=WHITE, stroke=RULE_LINE, sw=0.8)

    # SUPPORT LEFT: Knowledge Base ─────────────────────────────────────────
    iy = mid_y_base + MID_H - PAD - 4
    iy = section_header(cv, "Knowledge Base — Your Private AI Library",
                         mid_x[0]+PAD, iy, SC - 2*PAD, color=GOLD)
    iy -= 8
    kb_points = [
        "Upload team docs (PDF, Word, Excel, PPT, CSV and 1,000+ formats)",
        "Ask questions → get answers with citations showing exact sources",
        "Type  #  in any chat to reference a saved knowledge base",
        "Private by default — you control who can access each collection",
        "Limits: 50 MB per file, up to 90 files per knowledge base",
    ]
    for pt in kb_points:
        cv.setFillColor(GOLD)
        cv.setFont("Helvetica-Bold", 10)
        cv.drawString(mid_x[0]+PAD, iy, "·")
        iy = text_block(cv, pt, mid_x[0]+PAD+10, iy,
                        SC - 2*PAD - 10, "Helvetica", 8.5, MID)
        iy -= 5

    # SUPPORT RIGHT: Ground Rules ──────────────────────────────────────────
    iy = mid_y_base + MID_H - PAD - 4
    col_half = (SC - 2*PAD - GUTTER) // 2

    # DO column
    do_x = mid_x[1] + PAD
    dont_x = do_x + col_half + GUTTER

    cv.setFont("Helvetica-Bold", 9.5)
    cv.setFillColor(DO_GREEN)
    cv.drawString(do_x, iy, "✔  DO")
    cv.setFillColor(DONT_RED)
    cv.drawString(dont_x, iy, "✘  DON'T")
    iy -= 6
    # Underlines
    cv.setStrokeColor(DO_GREEN); cv.setLineWidth(1)
    cv.line(do_x, iy, do_x + col_half, iy)
    cv.setStrokeColor(DONT_RED)
    cv.line(dont_x, iy, dont_x + col_half, iy)
    iy -= 10

    dos = [
        "Upload internal reports, policies & procedures",
        "Be specific — \"200-word exec summary\" beats \"write a summary\"",
        "Review all AI output before sharing or acting on it",
        "Use Memory to personalize every response",
    ]
    donts = [
        "Upload customer PII, SSNs, or account numbers",
        "Paste passwords, API keys, or credentials",
        "Treat AI output as guaranteed fact",
        "Use for autonomous decisions (loans, compliance calls)",
    ]
    for do, dont in zip(dos, donts):
        start_iy = iy
        # DO item
        cv.setFillColor(DO_GREEN)
        cv.setFont("Helvetica-Bold", 9)
        cv.drawString(do_x, iy, "·")
        next_iy = text_block(cv, do, do_x+10, iy, col_half-10,
                             "Helvetica", 8, MID)
        # DON'T item (align to same start)
        cv.setFillColor(DONT_RED)
        cv.drawString(dont_x, start_iy, "·")
        next_iy2 = text_block(cv, dont, dont_x+10, start_iy, col_half-10,
                              "Helvetica", 8, MID)
        iy = min(next_iy, next_iy2) - 6

    # ── SAFETY STRIP (full width, trust band) ─────────────────────────────
    rr(cv, MARGIN, Y(safety_bot) + GAP//2, CW, SAFETY_H, r=8, fill=BLACK)

    items = [
        ("⬛", GOLD, "Private AWS"),
        ("⬛", GOLD, "Data never leaves Flagstar"),
        ("⬛", GOLD, "Never trains AI models"),
        ("⬛", GOLD, "GLBA & SOX compliant"),
        ("⬛", GOLD, "Full audit trail"),
    ]
    total_items = len(items)
    item_w = CW / total_items
    for i, (_, col, label) in enumerate(items):
        ix = MARGIN + i * item_w + item_w / 2
        iy2 = Y(safety_bot) + GAP//2 + SAFETY_H/2

        # Gold dot
        cv.setFillColor(GOLD)
        cv.circle(ix - cv.stringWidth(label, "Helvetica-Bold", 8)/2 - 8,
                  iy2 - 2, 3, fill=1, stroke=0)
        cv.setFont("Helvetica-Bold", 8)
        cv.setFillColor(WHITE)
        cv.drawString(ix - cv.stringWidth(label, "Helvetica-Bold", 8)/2,
                      iy2 - 4, label)

    # ── FOOTER ────────────────────────────────────────────────────────────
    cv.setFillColor(BLACK)
    cv.rect(0, Y(footer_bot), W, FOOTER_H, fill=1, stroke=0)
    # Gold top accent line
    cv.setFillColor(GOLD)
    cv.rect(0, Y(footer_bot) + FOOTER_H - 4, W, 4, fill=1, stroke=0)

    links = [
        ("🔑  Login", "myapps.microsoft.com", "https://myapps.microsoft.com"),
        ("🌐  Resources",
         "flagstar.sharepoint.com/sites/AI",
         "https://flagstar.sharepoint.com/sites/AI/SitePages/Home.aspx"),
        ("💬  Teams Support", "Join code: g2w1hjy", None),
    ]
    third = W / 3
    for i, (label, url_text, url) in enumerate(links):
        cx_f = i * third + third / 2
        # Label
        cv.setFont("Helvetica-Bold", 9)
        cv.setFillColor(GOLD)
        lw = cv.stringWidth(label, "Helvetica-Bold", 9)
        cv.drawString(cx_f - lw/2, Y(footer_bot) + 50, label)
        # URL text
        cv.setFont("Helvetica", 8)
        fcolor = HexColor("#7BBFFF") if url else HexColor("#AAAAAA")
        cv.setFillColor(fcolor)
        uw = cv.stringWidth(url_text, "Helvetica", 8)
        cv.drawString(cx_f - uw/2, Y(footer_bot) + 35, url_text)
        if url:
            cv.linkURL(url,
                       (cx_f - uw/2, Y(footer_bot)+28,
                        cx_f + uw/2, Y(footer_bot)+45), relative=0)
        # Vertical dividers
        if i < 2:
            cv.setStrokeColor(HexColor("#333333")); cv.setLineWidth(0.5)
            cv.line((i+1)*third, Y(footer_bot)+15, (i+1)*third, Y(footer_bot)+65)

    # Tagline bottom center
    cv.setFont("Helvetica-Oblique", 7)
    cv.setFillColor(HexColor("#666666"))
    cv.drawCentredString(W/2, Y(footer_bot) + 12,
        "StarIQ · Flagstar's Enterprise AI Platform · Your data is always private & secure")

    cv.save()
    print(f"✅  {out_path}")


if __name__ == "__main__":
    build("/home/user/Test1/StarIQ_Exec_OnePager_v2.pdf")
