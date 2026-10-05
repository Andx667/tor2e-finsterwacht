#!/usr/bin/env python3
"""Zeichnet das Logo (Wachturm unter einem Stern) -> assets/logo.svg, logo.png (512), logo.webp (144), logo-print.png (512, rot).

Weiß auf transparent (plus logo-print.png in Titelrot für die PDFs), im Stil der Mod-Icons auf andx.eu. SVG und Raster stammen aus
denselben Koordinaten (64×64-Raster).
    python3 tools/logo.py
"""
import math, os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")

# Stern: 8 Strahlen, schlank
SX, SY, RO, RI, N = 32, 14.5, 7, 2.3, 8
star = [(SX + (RO if i % 2 == 0 else RI) * math.sin(math.pi * i / N),
         SY - (RO if i % 2 == 0 else RI) * math.cos(math.pi * i / N)) for i in range(2 * N)]
# Turm: Schaft, Zinnenkranz mit drei Zinnen
shaft = [(25.5, 54), (38.5, 54), (37.5, 33), (26.5, 33)]
crown = [(21, 33), (43, 33), (43, 28), (38.5, 28), (38.5, 23.5), (34, 23.5), (34, 28),
         (30, 28), (30, 23.5), (25.5, 23.5), (25.5, 28), (21, 28)]
door = (29, 45, 35, 54)          # Rechteck + Halbrund oben
slit = (31, 36, 33, 41)


def pts(p):
    return "M" + " L".join(f"{x:g} {y:g}" for x, y in p) + "Z"


svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <circle cx="32" cy="32" r="29" fill="none" stroke="#f5f3f2" stroke-width="3"/>
  <path fill="#f5f3f2" fill-rule="evenodd" d="{pts(star)} {pts(shaft)} {pts(crown)} M29 54V48a3 3 0 0 1 6 0V54Z M31 36h2v5h-2Z"/>
</svg>
'''
open(os.path.join(A, "logo.svg"), "w", encoding="utf-8").write(svg)

S = 8 * 64
k = S / 64
m = Image.new("L", (S, S), 0)
d = ImageDraw.Draw(m)
sc = lambda p: [(x * k, y * k) for x, y in p]
d.ellipse([3 * k, 3 * k, 61 * k, 61 * k], outline=255, width=int(3 * k))
for poly in (star, shaft, crown):
    d.polygon(sc(poly), fill=255)
x0, y0, x1, y1 = door
d.rectangle([x0 * k, (y0 + 3) * k, x1 * k, y1 * k], fill=0)
d.pieslice([x0 * k, y0 * k, x1 * k, (y0 + 6) * k], 180, 360, fill=0)
d.rectangle([slit[0] * k, slit[1] * k, slit[2] * k, slit[3] * k], fill=0)

img = Image.new("RGBA", (S, S), (245, 243, 242, 0))
img.putalpha(m)
img.resize((512, 512), Image.LANCZOS).save(os.path.join(A, "logo.png"), optimize=True)
img.resize((144, 144), Image.LANCZOS).save(os.path.join(A, "logo.webp"), quality=90, method=6)
ink = Image.new("RGBA", (S, S), (0x7A, 0x2A, 0x1F, 0))   # fwred aus finsterwacht.sty
ink.putalpha(m)
ink.resize((512, 512), Image.LANCZOS).save(os.path.join(A, "logo-print.png"), optimize=True)
print("assets/logo.svg, logo.png, logo.webp, logo-print.png")
