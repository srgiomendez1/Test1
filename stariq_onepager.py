"""
StarIQ Executive One-Pager — Flagstar Brand
Infographic-style single page, matching the numbered-grid format.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
import os, zipfile, io
from PIL import Image

# ── Flagstar brand colors ──────────────────────────────────────────────────
GOLD    = HexColor("#FFB81C")
ORANGE  = HexColor("#FF6200")
BLACK   = HexColor("#000000")
WHITE   = HexColor("#FFFFFF")
CREAM   = HexColor("#FFF8EC")   # warm off-white background
DARK    = HexColor("#1A1A1A")   # near-black for body text
MID     = HexColor("#4A4A4A")   # mid-gray for body copy
GOLD_LT = HexColor("#FFF0C2")   # light gold tint for alternating cells

# ── Page setup ────────────────────────────────────────────────────────────
W, H = letter          # 612 x 792 pts  (8.5" x 11")
MARGIN = 0.45 * inch

# ── Extract Flagstar logo from uploaded PPTX ──────────────────────────────
LOGO_SRC = "/root/.claude/uploads/fcee979a-6e1a-4650-b28b-1cb028b281e0/cd5a7b7f-flagstartemplate.pptx"
LOGO_OUT = "/tmp/flagstar_logo.png"

def extract_logo():
    with zipfile.ZipFile(LOGO_SRC) as z:
        # image1.jpg is the clean logo on white background
        with z.open("ppt/media/image1.jpg") as f:
            img = Image.open(io.BytesIO(f.read())).convert("RGBA")
    # Make white background transparent so it works on any bg
    data = img.getdata()
    new_data = []
    for r, g, b, a in data:
        if r > 240 and g > 240 and b > 240:
            new_data.append((r, g, b, 0))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    img.save(LOGO_OUT, "PNG")
    return LOGO_OUT

# ── Helper: draw rounded rect ─────────────────────────────────────────────
def round_rect(c, x, y, w, h, r, fill=None, stroke=None):
    p = c.beginPath()
    p.moveTo(x + r, y)
    p.lineTo(x + w - r, y)
    p.arcTo(x + w - r, y, x + w, y + r, -90, 90)
    p.lineTo(x + w, y + h - r)
    p.arcTo(x + w - r, y + h - r, x + w, y + h, 0, 90)
    p.lineTo(x + r, y + h)
    p.arcTo(x, y + h - r, x + r, y + h, 90, 90)
    p.lineTo(x, y + r)
    p.arcTo(x, y, x + r, y + r, 180, 90)
    p.close()
    if fill:
        c.setFillColor(fill)
    if stroke:
        c.setStrokeColor(stroke)
        c.setLineWidth(0.5)
    c.drawPath(p, fill=bool(fill), stroke=bool(stroke))

# ── Helper: wrapped text in a box ─────────────────────────────────────────
def draw_text_block(c, text, x, y, width, font, size, color, line_height=None):
    if line_height is None:
        line_height = size * 1.3
    c.setFont(font, size)
    c.setFillColor(color)
    words = text.split()
    lines, line = [], []
    for w in words:
        test = " ".join(line + [w])
        if c.stringWidth(test, font, size) <= width:
            line.append(w)
        else:
            if line:
                lines.append(" ".join(line))
            line = [w]
    if line:
        lines.append(" ".join(line))
    for ln in lines:
        c.drawString(x, y, ln)
        y -= line_height
    return y  # returns y after last line

# ── Grid cell content ─────────────────────────────────────────────────────
CELLS = [
    {
        "num": "1",
        "title": "Access StarIQ",
        "body": "Go to myapps.microsoft.com, click the StarIQ icon, and sign in with your Flagstar credentials. SSO — no new password needed.",
        "link": None,
    },
    {
        "num": "2",
        "title": "Summarize Anything",
        "body": "Upload a 50-page report and ask: \"Summarize in 5 bullets with key decisions.\" Done in seconds.",
        "link": None,
    },
    {
        "num": "3",
        "title": "Draft in Seconds",
        "body": "\"Write a professional email about our Q2 deadline change — positive tone.\" Get a polished draft instantly.",
        "link": None,
    },
    {
        "num": "4",
        "title": "Analyze Data",
        "body": "Upload Excel → \"What are the top trends and outliers?\" AI reads values and surfaces insights fast.",
        "link": None,
    },
    {
        "num": "5",
        "title": "Pick Your Model",
        "body": "⚡ Haiku — quick tasks\n🚀 Sonnet — most work  ★ start here\n🎯 Opus — critical decisions\nSwitch with @ModelName mid-chat.",
        "link": None,
    },
    {
        "num": "6",
        "title": "Knowledge Base",
        "body": "Upload your team's docs (PDF, Word, Excel, PPT). Type # in chat to reference them. Answers come with exact citations. Private by default.",
        "link": None,
    },
    {
        "num": "7",
        "title": "Ground Rules",
        "body": "✅ Upload internal docs & reports\n✅ Review AI output before sharing\n❌ No customer PII or SSNs\n❌ No passwords or credentials",
        "link": None,
    },
    {
        "num": "8",
        "title": "Your Data Is Safe",
        "body": "Runs inside Flagstar's private AWS. Never leaves our environment. Conversations never used to train AI. GLBA & SOX compliant.",
        "link": None,
    },
]

# ── Main draw function ────────────────────────────────────────────────────
def build_pdf(out_path):
    logo_path = extract_logo()
    c = canvas.Canvas(out_path, pagesize=letter)

    # ── BACKGROUND ───────────────────────────────────────────────────────
    c.setFillColor(CREAM)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ── HEADER BAR ───────────────────────────────────────────────────────
    HEADER_H = 1.65 * inch
    c.setFillColor(BLACK)
    c.rect(0, H - HEADER_H, W, HEADER_H, fill=1, stroke=0)

    # Programmatic Flagstar logo (4-pointed star + wordmark)
    import math
    logo_x = W - MARGIN - 1.55 * inch
    logo_y = H - HEADER_H + 0.42 * inch
    # Draw 4-pointed star (Flagstar style)
    c.setFillColor(GOLD)
    star_cx = logo_x + 0.13 * inch
    star_cy = logo_y + 0.06 * inch
    r_outer, r_inner = 0.115 * inch, 0.038 * inch
    pts = 4
    star_path = c.beginPath()
    for i in range(pts * 2):
        angle = math.pi / pts * i - math.pi / 2
        r = r_outer if i % 2 == 0 else r_inner
        px = star_cx + r * math.cos(angle)
        py = star_cy + r * math.sin(angle)
        if i == 0:
            star_path.moveTo(px, py)
        else:
            star_path.lineTo(px, py)
    star_path.close()
    c.drawPath(star_path, fill=1, stroke=0)
    # Wordmark
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(logo_x + 0.29 * inch, logo_y, "flagstar")

    # Title — "StarIQ" in gold, rest in white
    title_y = H - HEADER_H + 0.92 * inch
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 30)
    stariq_w = c.stringWidth("StarIQ ", "Helvetica-Bold", 30)
    c.drawString(MARGIN, title_y, "StarIQ ")

    c.setFillColor(WHITE)
    c.drawString(MARGIN + stariq_w, title_y, "at a Glance")

    # Subtitle
    c.setFillColor(HexColor("#AAAAAA"))
    c.setFont("Helvetica", 9)
    c.drawString(MARGIN, H - HEADER_H + 0.62 * inch,
                 "Your AI Assistant at Flagstar  ·  Powered by Amazon Bedrock  ·  Runs 100% inside Flagstar's private AWS")

    # Tagline pill (below subtitle, left-aligned)
    pill_x = MARGIN
    pill_y = H - HEADER_H + 0.22 * inch
    round_rect(c, pill_x, pill_y, 1.65 * inch, 0.28 * inch, 5,
               fill=ORANGE, stroke=None)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(pill_x + 0.1 * inch, pill_y + 0.08 * inch,
                 "No tech skills needed  ✓")

    # ── GOLD ACCENT STRIPE ───────────────────────────────────────────────
    c.setFillColor(GOLD)
    c.rect(0, H - HEADER_H - 0.055 * inch, W, 0.055 * inch, fill=1, stroke=0)

    # ── GRID LAYOUT ──────────────────────────────────────────────────────
    COLS = 4
    ROWS = 2
    PAD = 0.18 * inch
    GUTTER = 0.14 * inch
    GRID_TOP = H - HEADER_H - 0.055 * inch - 0.15 * inch
    FOOTER_H = 0.58 * inch
    GRID_BOT = FOOTER_H + 0.08 * inch
    GRID_H = GRID_TOP - GRID_BOT
    CELL_H = (GRID_H - GUTTER * (ROWS - 1)) / ROWS
    GRID_W = W - 2 * MARGIN
    CELL_W = (GRID_W - GUTTER * (COLS - 1)) / COLS

    for idx, cell in enumerate(CELLS):
        row = idx // COLS
        col = idx % COLS
        cx = MARGIN + col * (CELL_W + GUTTER)
        cy = GRID_TOP - (row + 1) * CELL_H - row * GUTTER

        # Cell background — alternate light gold vs white
        bg = GOLD_LT if (row + col) % 2 == 0 else WHITE
        round_rect(c, cx, cy, CELL_W, CELL_H, 7, fill=bg, stroke=HexColor("#E8D89A"))

        # Large number
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 28)
        c.drawString(cx + PAD, cy + CELL_H - PAD - 0.02 * inch, cell["num"])

        # Divider line under number
        num_w = c.stringWidth(cell["num"], "Helvetica-Bold", 28)
        line_y = cy + CELL_H - PAD - 0.28 * inch
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.5)
        c.line(cx + PAD, line_y, cx + CELL_W - PAD, line_y)

        # Title
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 9.5)
        title_y = line_y - 0.16 * inch
        draw_text_block(c, cell["title"], cx + PAD, title_y,
                        CELL_W - 2 * PAD, "Helvetica-Bold", 9.5, DARK, 12)

        # Body text — handle \n manually
        body_y = title_y - 0.20 * inch
        lines_raw = cell["body"].split("\n")
        for raw_line in lines_raw:
            body_y = draw_text_block(c, raw_line, cx + PAD, body_y,
                                     CELL_W - 2 * PAD, "Helvetica", 8.2, MID, 11)
            body_y -= 1  # small extra gap between manual lines

    # ── FOOTER ───────────────────────────────────────────────────────────
    c.setFillColor(BLACK)
    c.rect(0, 0, W, FOOTER_H, fill=1, stroke=0)

    # Footer gold line at top
    c.setFillColor(GOLD)
    c.rect(0, FOOTER_H - 0.04 * inch, W, 0.04 * inch, fill=1, stroke=0)

    footer_y = FOOTER_H * 0.52

    # Three link blocks
    links = [
        ("🔑  Login", "myapps.microsoft.com", "https://myapps.microsoft.com"),
        ("🌐  Resources", "flagstar.sharepoint.com/sites/AI", "https://flagstar.sharepoint.com/sites/AI/SitePages/Home.aspx"),
        ("💬  Teams Support", "Join code: g2w1hjy", None),
    ]

    third = W / 3
    for i, (label, url_text, url) in enumerate(links):
        cx = i * third + third / 2

        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(cx, footer_y + 0.11 * inch, label)

        c.setFillColor(HexColor("#BBBBBB"))
        c.setFont("Helvetica", 7.5)
        if url:
            c.setFillColorRGB(0.7, 0.85, 1.0)
        c.drawCentredString(cx, footer_y - 0.06 * inch, url_text)
        if url:
            link_w = c.stringWidth(url_text, "Helvetica", 7.5)
            c.linkURL(url,
                      (cx - link_w / 2, footer_y - 0.14 * inch,
                       cx + link_w / 2, footer_y + 0.02 * inch),
                      relative=0)

    # Vertical dividers in footer
    c.setStrokeColor(HexColor("#444444"))
    c.setLineWidth(0.5)
    for i in [1, 2]:
        c.line(i * third, 0.08 * inch, i * third, FOOTER_H - 0.1 * inch)

    # ── SAVE ─────────────────────────────────────────────────────────────
    c.save()
    print(f"✅ Saved: {out_path}")


if __name__ == "__main__":
    out = "/home/user/Test1/StarIQ_Exec_OnePager.pdf"
    build_pdf(out)
