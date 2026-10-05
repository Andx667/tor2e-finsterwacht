#!/usr/bin/env python3
"""Zeichnet das GitHub-Social-Preview (1280×640) -> assets/social-preview.png.

Nutzt die Spielerkarte (ohne Spielleiter-Geheimnisse) und die Pagella aus TeX Gyre.
    python3 tools/social.py
"""
import glob, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1280, 640
INK, RED, GOLD, PARCH = (29, 23, 20), (122, 42, 31), (184, 156, 108), (247, 241, 230)


def font(style, size):
    pats = [f"**/texgyrepagella-{style}.otf"]
    for base in (os.path.expandvars(r"%LOCALAPPDATA%\Programs\MiKTeX\fonts"),
                 "/usr/share/texlive/texmf-dist/fonts", "/usr/share/texmf/fonts"):
        for p in pats:
            hit = glob.glob(os.path.join(base, p), recursive=True)
            if hit:
                return ImageFont.truetype(hit[0], size)
    return ImageFont.load_default()


# Hintergrund: Karte, innerhalb des Pergamentrands zugeschnitten (kein Rand sichtbar)
bg = Image.open(os.path.join(ROOT, "assets", "maps", "map-finsterwacht-players-de.jpg")).convert("RGB")
bg = bg.crop((60, 60, bg.width - 60, bg.height - 60))
s = max(W / bg.width, H / bg.height) * 1.15
bg = bg.resize((int(bg.width * s), int(bg.height * s)), Image.LANCZOS)
ox, oy = bg.width - W - 30, (bg.height - H) // 2 + 40
bg = bg.crop((ox, oy, ox + W, oy + H))

# dunkler Verlauf von links: unter dem Text ganz dunkel, ab ~60 % die Karte
grad = Image.new("L", (W, 1))
for x in range(W):
    t = max(0.0, min(1.0, (x - 640) / 380))
    grad.putpixel((x, 0), int(250 * (1 - t) ** 1.2))
mask = grad.resize((W, H))
img = Image.composite(Image.new("RGB", (W, H), INK), bg, mask)

d = ImageDraw.Draw(img)
d.rectangle([28, 28, W - 29, H - 29], outline=GOLD, width=3)
d.rectangle([40, 40, W - 41, H - 41], outline=GOLD, width=1)

x = 90
d.text((x, 150), "THE ONE RING · 2. EDITION", font=font("bold", 26), fill=GOLD)
d.text((x, 200), "Die Finsterwacht", font=font("bolditalic", 92), fill=PARCH)
d.line([x, 345, x + 380, 335], fill=GOLD, width=2)
d.text((x, 360), "Ein Abenteuer für Eriador, TA 2965", font=font("italic", 38), fill=(226, 212, 184))
d.text((x, 430), "Deutsche Druckfassung mit Karten und Gegenstandskarten", font=font("regular", 24), fill=(190, 176, 150))

out = os.path.join(ROOT, "assets", "social-preview.png")
img.save(out, optimize=True)
print(out)
