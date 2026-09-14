#!/usr/bin/env python3
"""Generate 12 G-Sign exploration SVGs + 3 refined + comparison sheet."""

from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent / "G_SIGN_CONCEPTS"
EXP = ROOT / "explore"
REF = ROOT / "refined"
EXP.mkdir(exist_ok=True)
REF.mkdir(exist_ok=True)

GOLD = "#D99A22"
DEEP = "#A96F08"
LITE = "#F4C15D"
DARK = "#111827"

# Each concept: name, description, svg body (paths only, 1024 canvas)
CONCEPTS = {
    "e01-one-stroke": (
        "One-stroke G — same path = bowl + bar + signing flick",
        f"""
  <path d="M700 260
           C520 200 300 320 300 512
           C300 720 480 820 640 780
           C700 760 720 700 720 640
           L560 640
           L720 640
           C780 640 820 560 830 430"
        fill="none" stroke="{GOLD}" stroke-width="92"
        stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M760 500 L830 360 L890 470" fill="none" stroke="{LITE}"
        stroke-width="40" stroke-linecap="round" stroke-linejoin="round"/>
""",
    ),
    "e02-signature-cut": (
        "Signature-cut G — the cut IS the G opening",
        f"""
  <!-- solid G ring -->
  <path d="M700 300 A280 280 0 1 0 700 724"
        fill="none" stroke="{GOLD}" stroke-width="110" stroke-linecap="butt"/>
  <!-- bar -->
  <rect x="540" y="460" width="170" height="90" fill="{GOLD}"/>
  <!-- signature slash replaces/apertures the G — cuts through right side -->
  <path d="M420 760 C560 700 700 620 860 360"
        fill="none" stroke="{DEEP}" stroke-width="64"
        stroke-linecap="round" stroke-linejoin="round"/>
  <!-- verify tip continues slash -->
  <path d="M780 480 L860 340 L910 450" fill="none" stroke="{LITE}"
        stroke-width="44" stroke-linecap="round" stroke-linejoin="round"/>
""",
    ),
    "e03-cursive-g": (
        "Cursive g — loop is G; descender = signing gesture",
        f"""
  <!-- uppercase G gesture as cursive: entry, bowl, exit-up -->
  <path d="M280 380
           C320 240 520 200 620 280
           C720 360 700 520 560 560
           C480 580 420 560 400 520
           C380 480 420 440 500 440
           L700 440
           C780 440 820 380 820 300"
        fill="none" stroke="{GOLD}" stroke-width="78"
        stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M820 300 C840 240 880 220 920 250"
        fill="none" stroke="{LITE}" stroke-width="36" stroke-linecap="round"/>
""",
    ),
    "e04-brush-weight": (
        "Brush one-stroke — thick bowl, thin flourish (calligraphic)",
        f"""
  <!-- simulated brush: overlapping strokes for weight -->
  <path d="M680 250 C480 200 300 340 300 520 C300 720 500 820 660 770
           C720 750 740 700 740 640 L560 640 L740 640
           C800 640 830 560 835 420"
        fill="none" stroke="{GOLD}" stroke-width="100" stroke-linecap="round"/>
  <path d="M680 250 C480 200 300 340 300 520 C300 720 500 820 660 770
           C720 750 740 700 740 640 L560 640 L740 640
           C800 640 830 560 835 420"
        fill="none" stroke="{DEEP}" stroke-width="48" stroke-linecap="round"/>
  <path d="M835 420 C850 360 870 300 900 250"
        fill="none" stroke="{LITE}" stroke-width="28" stroke-linecap="round"/>
""",
    ),
    "e05-twin-moment": (
        "Twin-moment — first stroke = G, second = signing (motion)",
        f"""
  <path d="M660 240 A300 300 0 1 0 660 780"
        fill="none" stroke="{GOLD}" stroke-width="88" stroke-linecap="butt" opacity="1"/>
  <path d="M520 560 H700"
        fill="none" stroke="{GOLD}" stroke-width="80" stroke-linecap="round"/>
  <!-- second, lighter/faster stroke = the act of signing -->
  <path d="M480 640 C620 700 760 620 820 420"
        fill="none" stroke="{DEEP}" stroke-width="36" stroke-linecap="round" opacity="0.95"/>
  <path d="M780 460 L830 360 L880 430" fill="none" stroke="{LITE}" stroke-width="28"
        stroke-linecap="round" stroke-linejoin="round"/>
""",
    ),
    "e06-seal-slash": (
        "Seal-slash — G as stamp; slash cracks open the seal",
        f"""
  <circle cx="512" cy="512" r="360" fill="none" stroke="{DARK}" stroke-width="28"/>
  <path d="M680 300 A240 240 0 1 0 680 724"
        fill="none" stroke="{GOLD}" stroke-width="96" stroke-linecap="butt"/>
  <rect x="540" y="460" width="150" height="84" fill="{GOLD}"/>
  <path d="M300 780 L820 280" fill="none" stroke="{DEEP}" stroke-width="52"
        stroke-linecap="round"/>
""",
    ),
    "e07-diamond-carve": (
        "Diamond-carve — Golden Logistics DNA; G + slash in negative",
        f"""
  <!-- diamond / rotated square like logistics mark family -->
  <rect x="512" y="80" width="610" height="610" rx="24"
        transform="rotate(45 512 512)" fill="{GOLD}"/>
  <!-- G carved dark -->
  <path d="M640 320 A170 170 0 1 0 640 700"
        fill="none" stroke="{DARK}" stroke-width="78" stroke-linecap="butt"/>
  <rect x="520" y="470" width="140" height="70" fill="{DARK}"/>
  <!-- signature slash through diamond -->
  <path d="M280 700 C480 760 680 640 820 380"
        fill="none" stroke="{LITE}" stroke-width="48" stroke-linecap="round"/>
""",
    ),
    "e08-bar-is-signature": (
        "Bar-is-signature — G underline IS the signing line + flick",
        f"""
  <!-- only the bowl -->
  <path d="M700 280 A260 260 0 1 0 700 700"
        fill="none" stroke="{GOLD}" stroke-width="100" stroke-linecap="butt"/>
  <!-- signature line replaces G bar, exits with energy -->
  <path d="M420 620 L680 620 C780 620 820 520 830 400"
        fill="none" stroke="{DEEP}" stroke-width="66" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M770 470 L830 340 L890 430" fill="none" stroke="{LITE}" stroke-width="40"
        stroke-linecap="round" stroke-linejoin="round"/>
""",
    ),
    "e09-loop-merge": (
        "Loop-merge — single loop reads as G; lower swing = sign",
        f"""
  <path d="M560 300
           C760 280 820 480 700 560
           C620 610 480 600 420 520
           C360 440 400 320 520 300
           C700 280 860 400 860 560
           C860 720 700 820 520 780"
        fill="none" stroke="{GOLD}" stroke-width="84"
        stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M520 780 C600 800 700 780 780 700"
        fill="none" stroke="{DEEP}" stroke-width="40" stroke-linecap="round"/>
""",
    ),
    "e10-angular-gesture": (
        "Angular gesture — technical hex-G + diagonal verify cut",
        f"""
  <path d="M620 220 L780 320 L780 520 L620 620 L420 520 L420 320 Z"
        fill="none" stroke="{GOLD}" stroke-width="88" stroke-linejoin="round"/>
  <path d="M620 420 L780 420" fill="none" stroke="{GOLD}" stroke-width="72" stroke-linecap="round"/>
  <path d="M360 760 L700 300 L820 200" fill="none" stroke="{DEEP}" stroke-width="56"
        stroke-linecap="round" stroke-linejoin="round"/>
""",
    ),
    "e11-ink-node": (
        "Ink-node — continuous stroke ends inside G counter as seal dot",
        f"""
  <path d="M720 280 C500 220 300 360 300 540 C300 740 500 840 680 780
           L680 620 L540 620 L680 620
           C760 620 800 540 800 430"
        fill="none" stroke="{GOLD}" stroke-width="90" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="800" cy="380" r="36" fill="{LITE}"/>
""",
    ),
    "e12-lattice-slash": (
        "Lattice-slash — cargo grid DNA; freeform sign = only organic line",
        f"""
  <rect x="140" y="140" width="744" height="744" rx="40" fill="{DARK}"/>
  <!-- grid -->
  <g stroke="{GOLD}" stroke-width="14" opacity="0.35">
    <path d="M280 180 V844 M420 180 V844 M560 180 V844 M700 180 V844"/>
    <path d="M180 280 H844 M180 420 H844 M180 560 H844 M180 700 H844"/>
  </g>
  <!-- G -->
  <path d="M640 300 A200 200 0 1 0 640 700" fill="none" stroke="{LITE}" stroke-width="72" stroke-linecap="butt"/>
  <rect x="520" y="460" width="140" height="68" fill="{LITE}"/>
  <!-- organic signature -->
  <path d="M260 720 C420 800 620 760 780 480"
        fill="none" stroke="{GOLD}" stroke-width="44" stroke-linecap="round"/>
""",
    ),
}

REFINED = {
    "r1-one-stroke-master": (
        "REFINE 1 — One-stroke G-Sign (master)",
        f"""
  <!-- Master geometry: one continuous gesture G -->
  <path d="M720 250
           C500 190 280 330 280 540
           C280 760 500 870 680 810
           C740 790 760 730 760 660
           L580 660
           L760 660
           C840 660 880 560 890 400"
        fill="none" stroke="{GOLD}" stroke-width="108"
        stroke-linecap="round" stroke-linejoin="round"/>
  <!-- verification terminal (thick, integrated — not UI check) -->
  <path d="M820 500 L890 340 L950 460" fill="none" stroke="{DEEP}"
        stroke-width="52" stroke-linecap="round" stroke-linejoin="round"/>
""",
    ),
    "r2-signature-cut-master": (
        "REFINE 2 — Signature-cut G (the cut = signing)",
        f"""
  <path d="M700 290 A290 290 0 1 0 700 734"
        fill="none" stroke="{GOLD}" stroke-width="120" stroke-linecap="square"/>
  <rect x="530" y="455" width="180" height="96" fill="{GOLD}"/>
  <!-- slash that IS the aperture / act of signing -->
  <path d="M380 780 C540 700 700 600 880 320"
        fill="none" stroke="{DARK}" stroke-width="70"
        stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M790 470 L880 300 L940 420" fill="none" stroke="{LITE}"
        stroke-width="48" stroke-linecap="round" stroke-linejoin="round"/>
""",
    ),
    "r3-diamond-g-master": (
        "REFINE 3 — Diamond G (Golden Logistics DNA + signing slash)",
        f"""
  <rect x="512" y="70" width="620" height="620" rx="28"
        transform="rotate(45 512 512)" fill="{GOLD}"/>
  <path d="M650 310 A175 175 0 1 0 650 710"
        fill="none" stroke="{DARK}" stroke-width="82" stroke-linecap="butt"/>
  <rect x="520" y="465" width="150" height="74" fill="{DARK}"/>
  <path d="M270 690 C500 780 720 620 850 340"
        fill="none" stroke="{LITE}" stroke-width="52" stroke-linecap="round"/>
  <path d="M780 430 L850 300 L900 400" fill="none" stroke="{DEEP}"
        stroke-width="36" stroke-linecap="round" stroke-linejoin="round"/>
""",
    ),
}


def write_svg(path: Path, title: str, body: str) -> None:
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">\n'
        f"  <title>{title}</title>\n{body}\n</svg>\n",
        encoding="utf-8",
    )


for key, (title, body) in CONCEPTS.items():
    write_svg(EXP / f"{key}.svg", title, body)
for key, (title, body) in REFINED.items():
    write_svg(REF / f"{key}.svg", title, body)


def render(png: Path, svg: Path, size: int) -> None:
    cairosvg.svg2png(url=str(svg), write_to=str(png), output_width=size, output_height=size)


# Contact sheet for explore (3 cols x 4 rows) + refined row
def sheet(items: list[tuple[str, Path]], out: Path, cols: int = 3) -> None:
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
    cell = 280
    pad = 20
    rows = (len(items) + cols - 1) // cols
    W = cols * cell + (cols + 1) * pad
    H = rows * (cell + 48) + pad
    img = Image.new("RGB", (W, H), (248, 250, 252))
    d = ImageDraw.Draw(img)
    for i, (label, svg) in enumerate(items):
        r, c = divmod(i, cols)
        x = pad + c * (cell + pad)
        y = pad + r * (cell + 48)
        tmp = ROOT / f"_t_{i}.png"
        render(tmp, svg, 256)
        tile = Image.open(tmp).convert("RGBA")
        # white bg card
        d.rounded_rectangle([x, y, x + cell, y + cell], radius=12, fill=(255, 255, 255), outline=(203, 213, 225))
        img.paste(tile.resize((240, 240), Image.Resampling.LANCZOS), (x + 20, y + 20), tile.resize((240, 240), Image.Resampling.LANCZOS))
        d.text((x + 8, y + cell + 12), label, fill=(15, 23, 42), font=font)
        tmp.unlink(missing_ok=True)
    img.save(out)
    print("wrote", out, img.size)


explore_items = [(k.replace("e0", "E0").replace("e1", "E1").replace("e12", "E12"), EXP / f"{k}.svg") for k in CONCEPTS]
sheet(explore_items, ROOT / "explore-sheet.png", cols=3)

ref_items = [(k[:2].upper() + " " + k.split("-")[1], REF / f"{k}.svg") for k in REFINED]
# simpler labels
ref_items = [
    ("R1 One-stroke", REF / "r1-one-stroke-master.svg"),
    ("R2 Signature-cut", REF / "r2-signature-cut-master.svg"),
    ("R3 Diamond G", REF / "r3-diamond-g-master.svg"),
]
sheet(ref_items, ROOT / "refined-sheet.png", cols=3)

# small sizes for refined
for name in REFINED:
    for s in (16, 24, 32, 48, 128, 256):
        render(REF / f"{name}-{s}.png", REF / f"{name}.svg", s)

print("concepts", len(CONCEPTS), "refined", len(REFINED))
