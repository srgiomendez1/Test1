# Skill: Infographic & One-Pager Design Architecture

Use this skill when building PDF infographics, executive one-pagers, visual reference cards, or any single-page visual document in Python (reportlab, Pillow, etc.).

---

## CORE PRINCIPLES

### 1. Visual Flow — Guide the Eye Deliberately
The viewer's eye must have a clear path. Design for **30–90 second executive scan**.

**Z-Pattern** (most one-pagers): Top-left entry → top-right → diagonal → bottom-left → bottom-right.
**F-Pattern** (text-heavy): Eyes read across top, then scan down the left edge.

Rules:
- **Entry point lives in the top 20–25% of the page** — dominant headline, largest element
- Primary focal point must be ≥ 4× the size of secondary elements
- Use size, color contrast, and white space as directional cues — NOT arrows unless necessary
- Rhythm: spacing between sections should follow a consistent multiplier (e.g., internal gutter = 0.5× external margin)
- Never leave the eye with no "next step" — every section should flow visually into the next

### 2. Infographic Principles (Tufte + Gestalt)
**Data-ink ratio ≥ 85%** — every pixel either conveys information or creates necessary breathing room. Remove everything else.

**Gestalt grouping:**
- Proximity: related items closer together than unrelated ones
- Similarity: use consistent color/size for items of equal importance
- Max 7 ± 2 information chunks per page (cognitive limit)

**Typography — strict 3-level scale:**
| Level | Size | Weight | Use |
|-------|------|--------|-----|
| L1 — Hero | 36–40pt | Bold | Page title only |
| L2 — Section | 10–11pt | Bold | Cell/section headers |
| L3 — Body | 8–8.5pt | Regular | Supporting detail |
- Line height: **1.4× font size** for all levels
- Never use more than 2 font weights (Bold + Regular)
- Never go below 8pt for print, 9pt for screen

**Color as signal, not decoration — each color answers "why is this color here?"**
| Color role | Meaning | Max page coverage |
|-----------|---------|------------------|
| Dark (black/near-black) | Anchor, header background, critical text | 20–25% |
| Primary accent (brand gold/color) | Numbers, borders, CTAs | 10–12% |
| Alert (orange/red) | Warnings, "action required" — use ONCE per page max | 2–3% |
| Neutral (white/cream) | Default content background | 50–60% |
| Mid-gray | Body copy, secondary text | as needed |

**Contrast (WCAG AA minimum 4.5:1):**
- Gold #FFB81C on white: 3.2:1 — FAILS. Use gold only for large text, icons, fills — never body text
- Black on white: 21:1 ✓
- #4A4A4A on cream: 6.8:1 ✓ — use for body text

### 3. Grid Architecture — All Dimensions Are Math
**8pt baseline grid** — ALL dimensions must be multiples of 8pt (≈ 0.111"):

```
Letter page = 612pt × 792pt

Recommended starting layout:
  Margin (horizontal): 40pt (0.556")
  Gutter (between cells): 16pt (0.222")
  Cell padding (inside): 12–16pt

4-column base grid:
  Cell width = (612 − 2×40 − 3×16) / 4 = 484 / 4 = 121pt

2-column layout:
  Cell width = (612 − 2×40 − 16) / 2 = 516 / 2 = 258pt

3-column layout (unequal for hierarchy):
  Wide: 240pt, Med: 180pt, Narrow: 100pt (+ 2×16 gutter = 532pt = content width ✓)
```

**Vertical proportions (golden ratio approximation):**
- Header: 14% of page height (≈ 112pt / 1.56")
- Content: 71% (≈ 560pt)
- Footer: 10% (≈ 80pt)
- Gold/accent divider: ≤ 1% (8pt)

**Visual weight via cell size — NOT color alone:**
- Critical info: 2-column span (2× area = 2× perceived importance)
- Standard info: 1-column
- Supporting/tertiary: smaller height or narrower column
- All rows in the same section must be identical height

**Cell layout checklist:**
- [ ] All dimensions are multiples of 8pt
- [ ] COLS × CELL_W + (COLS−1) × GUTTER + 2×MARGIN = PAGE_W
- [ ] No cell content exceeds 75% of cell height (reserve 25% for white space)
- [ ] Internal padding ≤ gutter (padding < gutter is fine; padding > gutter confuses hierarchy)
- [ ] Line height = 1.4× font size consistently

---

## LAYOUT TEMPLATES (Letter, 8.5"×11")

### Executive One-Pager (recommended)
```
┌─────────────────────────────────────────────────────────┐  112pt header
│  HERO TITLE (38pt)   subtitle (10pt)      LOGO/badge   │
├─────────────────────────────────────────────────────────┤  8pt gold stripe
│                     │                   │               │
│  PRIMARY CONTENT    │  USE CASES /      │  QUICK REF   │  280pt
│  (240pt wide)       │  DETAILS          │  (100pt wide)│
│  What + How         │  (180pt wide)     │  e.g. model  │
│                     │                   │  picker      │
├────────────────────────────┬────────────────────────────┤  16pt gap
│  SUPPORTING A              │  SUPPORTING B              │  180pt
│  (258pt wide)              │  (258pt wide)              │
├─────────────────────────────────────────────────────────┤  16pt gap
│  FULL-WIDTH TRUST / DATA SAFETY STRIP (48pt)            │
└─────────────────────────────────────────────────────────┘  80pt footer
```

### Two-Page Power User Guide
- Page 1: Same structure as above
- Page 2: 2×3 or 3×2 equal grid (6 sections) + footer
- Consistent header/footer for brand unity

---

## ICON STRATEGY
Draw icons programmatically (reliable in PDF, no font dependency):
- Small colored circle (16–20pt diameter) as badge background
- Simple geometric shape inside: rectangle=doc, bars=chart, envelope=email, circle=idea
- Always pair icon with text label — never icon alone
- Icon color = same as section accent; background circle = lighter tint of same color

---

## COMMON MISTAKES TO AVOID
- All cells equal size → no hierarchy, no focal point
- Gold/accent > 12% of page → visually noisy, dilutes emphasis
- Equal gutter and padding → confuses grouping vs. internal spacing
- More than 3 font sizes → chaotic hierarchy
- Body text below 8pt → fails readability
- Centering everything → static, no flow
- Ignoring the bottom 20% of page → execs don't scroll, so put CTAs high
- Footer height < 0.65" → cramped, links unclickable
- No entry point → viewer doesn't know where to start

---

## PYTHON SNIPPET: 8pt Grid Setup (reportlab)

```python
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter

W, H = letter  # 612, 792

# 8pt baseline grid
UNIT = 8  # points

# Layout constants (all multiples of UNIT)
MARGIN = 5 * UNIT          # 40pt horizontal margin
GUTTER = 2 * UNIT          # 16pt between cells
PAD = 2 * UNIT             # 16pt internal padding
HEADER_H = 14 * UNIT       # 112pt
FOOTER_H = 10 * UNIT       # 80pt
STRIPE_H = 1 * UNIT        # 8pt accent stripe

# Content dimensions
CW = W - 2 * MARGIN        # 532pt usable width

# Column presets
COL4 = (CW - 3*GUTTER) / 4       # 4 equal cols: 121pt
COL2 = (CW - GUTTER) / 2         # 2 equal cols: 258pt
COL_WIDE = 240                    # custom wide col
COL_MED = 180                     # custom medium col
COL_NARROW = CW - COL_WIDE - COL_MED - 2*GUTTER  # remainder
```

---

## USAGE
Reference this skill when:
- Building any PDF one-pager or infographic in Python
- Reviewing a visual layout for hierarchy and flow issues
- Choosing column widths and cell sizes for a new design
- Selecting which information belongs in which visual zone
