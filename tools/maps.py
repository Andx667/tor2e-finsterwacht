"""Draws the hand-drawn maps (Loremaster and player versions).

Optional step: the rendered JPGs are committed in assets/maps, so the PDF build
never needs this. Run it only after changing a map:

    pip install playwright pillow && playwright install chromium
    python3 tools/maps.py
"""
import random, math
from playwright.sync_api import sync_playwright

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "assets", "maps") + os.sep
SVG = os.path.join(D, "svg") + os.sep
INK, RED = "#3a2716", "#8a2e1e"
W, H = 800, 600
GM = True


def rough(pts, closed=False, jit=2.2, seg=14, seed=1):
    """Hand-drawn polyline: subdivide each segment and jitter the points."""
    r = random.Random(seed)
    P = pts + ([pts[0]] if closed else [])
    out = []
    for (x1, y1), (x2, y2) in zip(P, P[1:]):
        n = max(1, int(math.hypot(x2 - x1, y2 - y1) / seg))
        for i in range(n):
            t = i / n
            out.append((x1 + (x2 - x1) * t + r.uniform(-jit, jit), y1 + (y2 - y1) * t + r.uniform(-jit, jit)))
    out.append(P[-1] if not closed else out[0])
    d = f"M{out[0][0]:.1f} {out[0][1]:.1f}"
    for (ax, ay), (bx, by) in zip(out, out[1:]):
        d += f" Q{ax:.1f} {ay:.1f} {(ax + bx) / 2:.1f} {(ay + by) / 2:.1f}"
    d += f" L{out[-1][0]:.1f} {out[-1][1]:.1f}"
    return d + (" Z" if closed else "")


def blob(cx, cy, rx, ry, irr=0.08, n=28, seed=1, a0=0, a1=360):
    r = random.Random(seed)
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        k = 1 + r.uniform(-irr, irr)
        pts.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    return pts


def path(d, w=1.6, col=INK, dash=None, fill="none", op=1):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="{d}" fill="{fill}" stroke="{col}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" opacity="{op}"{da}/>'


def label(x, y, txt, size=24, anchor="middle", rot=0, col=INK, style=""):
    tr = f' transform="rotate({rot} {x} {y})"' if rot else ""
    return f'<text x="{x}" y="{y}" font-family="TeX Gyre Chorus" font-size="{size}" fill="{col}" text-anchor="{anchor}"{tr} {style}>{txt}</text>'


def num(x, y, n):
    if not GM:
        return ""
    return (f'<circle cx="{x}" cy="{y}" r="13" fill="#efe2c4" stroke="{RED}" stroke-width="1.6"/>'
            f'<text x="{x}" y="{y + 5.5}" font-family="TeX Gyre Pagella" font-weight="700" font-size="16" fill="{RED}" text-anchor="middle">{n}</text>')


def hachures(pts, out=True, length=12, every=1, seed=3, w=1.1):
    """Short strokes pointing outward from a polygon edge (cliffs, earthworks)."""
    r = random.Random(seed)
    s = ""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    for i, (x1, y1) in enumerate(pts[:-1]):
        x2, y2 = pts[i + 1]
        n = int(math.hypot(x2 - x1, y2 - y1) / 9)
        for j in range(0, n, every):
            t = j / max(n, 1)
            x, y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
            dx, dy = x - cx, y - cy
            L = math.hypot(dx, dy) or 1
            k = length * r.uniform(0.6, 1.25) * (1 if out else -1)
            s += path(f"M{x:.1f} {y:.1f} L{x + dx / L * k:.1f} {y + dy / L * k:.1f}", w)
    return s


def trees(cx, cy, n, spread, seed):
    r = random.Random(seed)
    s = ""
    for _ in range(n):
        x, y = cx + r.uniform(-spread, spread), cy + r.uniform(-spread * 0.6, spread * 0.6)
        s += path(rough([(x - 5, y + 4), (x, y - 6), (x + 5, y + 4)], jit=0.6, seg=5, seed=r.randint(0, 999)), 1.2)
    return s


def compass(x, y):
    return (f'<g transform="translate({x} {y})">'
            + path(rough([(0, -38), (7, 0), (0, 38), (-7, 0)], closed=True, jit=0.7, seg=8, seed=5), 1.4)
            + path("M0 -38 L7 0 L0 0 Z", 0.5, fill=INK, op=0.85)
            + path(rough([(-30, 0), (30, 0)], jit=0.6, seed=6), 1)
            + f'<text x="0" y="-44" font-family="TeX Gyre Pagella" font-weight="700" font-size="16" fill="{INK}" text-anchor="middle">N</text></g>')


def cartouche(x, y, title, sub, w=250):
    return (path(rough([(x, y), (x + w, y), (x + w, y + 64), (x, y + 64)], closed=True, jit=1.2, seed=9), 1.5, fill="#efe2c4", op=0.95)
            + path(rough([(x + 6, y + 6), (x + w - 6, y + 6), (x + w - 6, y + 58), (x + 6, y + 58)], closed=True, jit=0.9, seed=10), 0.8)
            + label(x + w / 2, y + 33, title, 30, col=RED)
            + label(x + w / 2, y + 52, sub, 17))


def frame(content, seed):
    r = random.Random(seed)
    edge = []
    for (x1, y1), (x2, y2) in zip([(6, 6), (W - 6, 6), (W - 6, H - 6), (6, H - 6)], [(W - 6, 6), (W - 6, H - 6), (6, H - 6), (6, 6)]):
        n = 40
        for i in range(n):
            t = i / n
            edge.append((x1 + (x2 - x1) * t + r.uniform(-3.5, 3.5), y1 + (y2 - y1) * t + r.uniform(-3.5, 3.5)))
    clip = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in edge) + " Z"
    stains = "".join(
        f'<circle cx="{r.uniform(60, W - 60):.0f}" cy="{r.uniform(60, H - 60):.0f}" r="{r.uniform(30, 90):.0f}" fill="url(#stain)" opacity="{r.uniform(0.25, 0.55):.2f}"/>'
        for _ in range(6))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W * 2}" height="{H * 2}">
<defs>
 <clipPath id="torn"><path d="{clip}"/></clipPath>
 <filter id="grain" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" seed="{seed}"/>
  <feColorMatrix values="0 0 0 0 0.35  0 0 0 0 0.25  0 0 0 0 0.12  0 0 0 0.22 0"/>
 </filter>
 <filter id="blot" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="4" seed="{seed + 3}"/>
  <feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.32  0 0 0 0 0.15  0 0 0 0.55 -0.12"/>
 </filter>
 <filter id="ink" x="-5%" y="-5%" width="110%" height="110%">
  <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="2" seed="{seed + 7}" result="n"/>
  <feDisplacementMap in="SourceGraphic" in2="n" scale="3" xChannelSelector="R" yChannelSelector="G"/>
 </filter>
 <radialGradient id="vig" cx="50%" cy="50%" r="72%"><stop offset="55%" stop-color="#e8d8b3" stop-opacity="0"/><stop offset="100%" stop-color="#7a5528" stop-opacity="0.55"/></radialGradient>
 <radialGradient id="stain"><stop offset="0%" stop-color="#b08850" stop-opacity="0"/><stop offset="80%" stop-color="#a07840" stop-opacity="0.25"/><stop offset="100%" stop-color="#8a6230" stop-opacity="0"/></radialGradient>
 <radialGradient id="lamp"><stop offset="0%" stop-color="#e8a33a" stop-opacity="0.95"/><stop offset="100%" stop-color="#e8a33a" stop-opacity="0"/></radialGradient>
 <radialGradient id="pale"><stop offset="0%" stop-color="#cfe3e6" stop-opacity="1"/><stop offset="100%" stop-color="#9fc4cc" stop-opacity="0"/></radialGradient>
</defs>
<rect width="{W}" height="{H}" fill="#ffffff"/>
<g clip-path="url(#torn)">
 <rect width="{W}" height="{H}" fill="#e9dbb9"/>
 <rect width="{W}" height="{H}" filter="url(#blot)"/>
 {stains}
 <g filter="url(#ink)" opacity="0.92">{content}</g>
 <rect width="{W}" height="{H}" filter="url(#grain)"/>
 <rect width="{W}" height="{H}" fill="url(#vig)"/>
</g>
<path d="{clip}" fill="none" stroke="#6b4a24" stroke-width="1.2" opacity="0.5"/>
</svg>'''


# ---------------- Fornost Erain ----------------
def fornost():
    s = ""
    # hill contours
    for i, (rx, ry) in enumerate([(250, 175), (185, 130), (120, 85)]):
        s += path(rough(blob(430, 300, rx, ry, irr=0.07, seed=20 + i), closed=True, jit=1.5, seed=30 + i), 1.0, op=0.55)
    # Deadmen's Dike: double earthwork arc with ticks, south and west
    arc_o = blob(430, 300, 300, 225, irr=0.03, n=30, seed=40, a0=70, a1=250)
    arc_i = blob(430, 300, 286, 212, irr=0.03, n=30, seed=40, a0=70, a1=250)
    s += path(rough(arc_o, jit=1.4, seed=41), 1.6) + path(rough(arc_i, jit=1.4, seed=42), 1.2)
    s += hachures(arc_o, length=9, seed=43, w=0.9)
    s += label(118, 500, "Deadmen's Dike", 26, rot=-40)
    # outer walls, broken
    wall = blob(430, 300, 205, 148, irr=0.05, n=36, seed=50)
    r = random.Random(51)
    for i in range(0, len(wall) - 3, 3):
        if r.random() < 0.72:
            seg = wall[i:i + 3]
            s += path(rough(seg, jit=1.0, seed=60 + i), 3.2)
    for i in (2, 11, 20, 29):
        x, y = wall[i]
        s += path(rough([(x - 7, y - 7), (x + 7, y - 7), (x + 7, y + 7), (x - 7, y + 7)], closed=True, jit=0.8, seed=70 + i), 1.6, fill="#d9c69e")
    # lanterns of the scavengers + the pale light
    for (x, y) in ([(262, 352), (292, 392), (240, 318)] if GM else []):
        s += f'<circle cx="{x}" cy="{y}" r="11" fill="url(#lamp)"/><circle cx="{x}" cy="{y}" r="2.6" fill="#a8541a"/>'
    if GM:
        s += f'<circle cx="575" cy="412" r="15" fill="url(#pale)"/><circle cx="575" cy="412" r="2.6" fill="#6f9aa3"/>'
        s += label(590, 444, "ein bleiches Licht?", 18, anchor="start")
    s += num(220, 360, 1) + label(320, 476, "Außenmauern", 20)
    # Throne room of Arvedui (high side): long pillared hall, east end collapsed
    s += path(rough([(380, 165), (500, 165), (500, 222), (455, 222)], jit=1.2, seed=80), 2.4)
    s += path(rough([(430, 222), (380, 222), (380, 165)], jit=1.2, seed=81), 2.4)
    for px in range(402, 452, 13):
        for py in (180, 207):
            s += f'<circle cx="{px}" cy="{py}" r="2.6" fill="none" stroke="{INK}" stroke-width="1.1"/>'
    # the throne at the west end: small block with a many-rayed star
    s += path(rough([(385, 186), (393, 186), (393, 201), (385, 201)], closed=True, jit=0.4, seed=84), 1.4, fill="#2b2420")
    s += path(rough([(462, 176), (478, 196), (470, 208), (490, 214)], jit=1.5, seed=82), 0.9, dash="2 4")
    rr = random.Random(83)
    s += "".join(f'<circle cx="{rr.uniform(458, 496):.0f}" cy="{rr.uniform(196, 236):.0f}" r="{rr.uniform(1.2, 2.6):.1f}" fill="{INK}"/>' for _ in range(16))
    if GM:
        s += num(365, 150, 2) + label(440, 132, "Thronsaal Arveduis", 22)
    else:
        s += label(440, 116, "eine Halle mit schwarzem Thron", 21) + label(440, 137, "wo Ned das Schwert fand", 16, col="#6b4a24")
    # Dome of Sight: large dome on the crest, collapsed onto itself
    dome = blob(452, 318, 44, 38, irr=0.05, n=26, seed=150)
    s += path(rough(dome, closed=True, jit=1.1, seed=151), 2.2, fill="#d9c69e")
    s += path(rough(blob(452, 318, 28, 24, irr=0.12, n=18, seed=152, a0=20, a1=300), jit=1.2, seed=153), 1.1)
    rr = random.Random(154)
    for k in range(7):
        a = math.radians(k * 51 + rr.uniform(-12, 12))
        x1, y1 = 452 + 8 * math.cos(a), 318 + 7 * math.sin(a)
        x2, y2 = 452 + 40 * math.cos(a), 318 + 34 * math.sin(a)
        s += path(rough([(x1, y1), (x2, y2)], jit=1.4, seg=5, seed=155 + k), 0.9)
    s += "".join(f'<circle cx="{452 + rr.uniform(-14, 14):.0f}" cy="{318 + rr.uniform(-11, 11):.0f}" r="{rr.uniform(1.4, 3.0):.1f}" fill="{INK}"/>' for _ in range(12))
    s += label(452, 378, "Kuppel der Sicht" if GM else "eine eingestürzte Kuppel", 20)
    # Hall of Rolls
    s += path(rough([(545, 225), (612, 225), (612, 268), (545, 268)], closed=True, jit=1.0, seed=90), 2.2)
    for k in range(4):
        s += path(rough([(553, 235 + k * 8), (604, 235 + k * 8)], jit=0.5, seed=91 + k), 0.7)
    if GM:
        s += num(630, 222, 3) + label(628, 286, "Halle der Schriftrollen", 20, anchor="middle")
    # Tombs of the Kings (west)
    for k, (x, y) in enumerate([(285, 225), (318, 212), (300, 255)]):
        s += path(rough([(x - 11, y + 9), (x - 11, y - 3), (x, y - 11), (x + 11, y - 3), (x + 11, y + 9)], jit=0.7, seg=6, seed=100 + k), 1.6)
    s += (num(322, 282, 4) + label(342, 288, "Gräber der Könige", 20, anchor="start")) if GM else label(334, 256, "Gräber der Könige", 20, anchor="start")
    # orc-sign on north slope
    rr = random.Random(110)
    x, y = 520, 112
    for k in range(7 if GM else 0):
        s += f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="2.4" ry="3.6" fill="{INK}" transform="rotate(-50 {x:.0f} {y:.0f})"/>'
        s += f'<ellipse cx="{x + 8:.0f}" cy="{y + 6:.0f}" rx="2.4" ry="3.6" fill="{INK}" transform="rotate(-50 {x + 8:.0f} {y + 6:.0f})"/>'
        x, y = x + 15 + rr.uniform(-2, 2), y - 9 + rr.uniform(-2, 2)
    if GM:
        s += label(560, 125, "Orkspuren", 19, anchor="start", col=RED)
    # Greenway from the south
    s += path(rough([(360, 600), (372, 540), (395, 488), (412, 445)], jit=1.4, seed=120), 1.3)
    s += path(rough([(392, 600), (400, 540), (417, 490), (430, 447)], jit=1.4, seed=121), 1.3)
    s += label(330, 560, "der Greenway", 20, anchor="end") + label(330, 580, "nach Bree", 17, anchor="end")
    # beacon line to the NE
    if GM:
        s += path(rough([(640, 175), (700, 120), (760, 62)], jit=1, seed=130), 1.4, dash="7 6")
    for (bx, by) in ([(672, 147), (732, 90)] if GM else []):
        s += path(rough([(bx - 8, by + 7), (bx, by - 8), (bx + 8, by + 7)], closed=True, jit=0.5, seg=6, seed=int(bx)), 1.3, fill="#cdb78c")
    if GM:
        s += label(662, 196, "Signalfeuer-Linie", 19, anchor="start", rot=-42)
        s += label(745, 40, "zur Finsterwacht", 16, anchor="end", col=RED)
    # thorn and trees
    s += trees(120, 260, 14, 50, 140) + trees(690, 330, 12, 45, 141) + trees(560, 520, 9, 40, 142)
    s += compass(720, 510)
    s += cartouche(28, 24, "Fornost Erain", "die Ruinen auf Deadmen's Dike" if GM else "wie Ned Appledore sie zeichnete", 270)
    s += label(772, 588, "Skizze für den Loremaster · nicht maßstabsgetreu" if GM else "auf die Rückseite einer Zeche im Prancing Pony gekritzelt", 15, anchor="end", col="#6b4a24")
    return frame(s, 11)


# ---------------- The Finsterwacht ----------------
def finsterwacht():
    s = ""
    crag = [(250, 175), (330, 112), (450, 92), (565, 122), (625, 195), (612, 300), (560, 368), (470, 408),
            (382, 412), (300, 382), (238, 300), (250, 175)]
    # valley contours below
    for k in range(4):
        y0 = 470 + k * 30
        s += path(rough([(0, y0 + 20), (200, y0), (420, y0 + 25 - k * 3), (620, y0 - 5), (800, y0 + 12)], jit=2, seed=200 + k), 0.9, op=0.5)
    # cliffs: hachures on N, E, W (stop at the ramp side)
    cliff = crag[:8] + [crag[8]]
    s += path(rough(crag, closed=True, jit=1.6, seed=210), 1.8)
    s += hachures(crag[0:8], length=20, seed=211, w=1.0)
    s += hachures([crag[9], crag[10], crag[11]], length=20, seed=212, w=1.0)
    s += label(450, 48, "Steilhang", 20, col="#6b4a24") + label(640, 392, "Steilhang", 20, rot=-52, col="#6b4a24")
    s += label(180, 230, "Steilhang", 20, rot=-80, col="#6b4a24")
    # walls (double line, inset)
    wall = [(272, 185), (338, 135), (450, 116), (552, 142), (602, 202), (590, 292), (544, 350), (468, 386),
            (440, 389)]
    wall2 = [(408, 391), (386, 392), (358, 382)]
    wall3 = [(318, 368), (262, 300), (272, 185)]
    for w_ in (wall, wall2, wall3):
        s += path(rough(w_, jit=1.0, seed=len(w_) * 7), 4.2) + path(rough(w_, jit=1.0, seed=len(w_) * 7 + 1), 1, col="#e9dbb9")
    # breach (jagged gap between 440 and 408)
    s += path(rough([(440, 389), (432, 380), (424, 395), (416, 382), (408, 391)], jit=0.6, seg=4, seed=230), 1.2)
    rr = random.Random(231)
    s += "".join(f'<circle cx="{rr.uniform(408, 446):.0f}" cy="{rr.uniform(395, 412):.0f}" r="{rr.uniform(1.4, 3):.1f}" fill="{INK}"/>' for _ in range(16))
    s += label(452, 432, "die Bresche", 19, anchor="start")
    # gate towers between (358,382) and (318,368)
    for (gx, gy) in [(354, 383), (321, 368)]:
        s += path(rough([(gx - 9, gy - 9), (gx + 9, gy - 9), (gx + 9, gy + 9), (gx - 9, gy + 9)], closed=True, jit=0.8, seed=int(gx)), 1.8, fill="#d9c69e")
    s += num(338, 345, 1) + label(272, 414, "zerbrochenes Tor", 19, anchor="end")
    # ramp from the valley up to the gate
    s += path(rough([(118, 590), (178, 540), (240, 470), (322, 390)], jit=1.3, seed=240), 1.4)
    s += path(rough([(152, 598), (212, 548), (270, 482), (352, 398)], jit=1.3, seed=241), 1.4)
    for k in range(9):
        t = k / 9
        x1, y1 = 118 + (322 - 118) * t, 590 + (390 - 590) * t
        s += path(f"M{x1:.0f} {y1:.0f} l{30:.0f} {8:.0f}", 0.6, op=0.6)
    s += label(292, 524, "die Rampe", 20, rot=-45)
    # courtyard + well
    s += label(392, 322, "Burghof", 22) + num(362, 292, 2)
    s += f'<circle cx="470" cy="325" r="9" fill="none" stroke="{INK}" stroke-width="1.6"/><circle cx="470" cy="325" r="3.5" fill="{INK}"/>'
    s += label(470, 354, "trockener Brunnen", 15)
    # beacon tower at the north tip
    s += f'<circle cx="452" cy="122" r="24" fill="#d9c69e" stroke="{INK}" stroke-width="2.2"/><circle cx="452" cy="122" r="11" fill="none" stroke="{INK}" stroke-width="1.2"/>'
    s += path("M444 114 l16 16 M460 114 l-16 16", 1.2)
    s += num(498, 112, 3) + label(520, 100, "Signalturm", 20, anchor="start")
    # fallen keep: broken square + rubble scribble + stair down
    s += path(rough([(380, 175), (470, 175), (470, 225)], jit=1.2, seed=260), 3)
    s += path(rough([(380, 175), (380, 238), (405, 238)], jit=1.2, seed=261), 3)
    rr = random.Random(262)
    scr = [(rr.uniform(392, 468), rr.uniform(186, 236)) for _ in range(22)]
    s += path(rough(scr, jit=1, seg=40, seed=263), 0.8, op=0.8)
    for k in range(5):
        s += path(f"M{432 + k * 5} {244 + k * 4} l14 0", 1.2)
    s += num(356, 205, 4) + label(428, 164, "eingestürzter Bergfried", 18, anchor="middle")
    if GM:
      s += path(rough([(462, 262), (540, 214), (634, 202)], jit=1, seed=270), 1, dash="4 4", col=RED)
      s += num(650, 200, 5) + label(668, 205, "Treppe hinab", 16, anchor="start") + label(668, 224, "zur tiefen Tür &amp;", 16, anchor="start") + label(668, 243, "zur Waffenkammer", 16, anchor="start")
      s += label(668, 261, "(unter der Erde)", 14, anchor="start", col="#6b4a24")
    # hidden postern on the west cliff
    if GM:
        s += path(rough([(262, 262), (238, 270), (222, 292), (204, 300), (190, 326), (170, 340)], jit=0.8, seed=280), 1.1, dash="3 4", col=RED)
        s += label(112, 364, "verborgene Ausfallpforte", 18, col=RED) + label(112, 382, "(Ziegenpfad)", 15, col="#6b4a24")
    # orcs come up the valley from the south
    for k, (x, y) in enumerate([(690, 548), (610, 542), (530, 548)] if GM else []):
        s += path(rough([(x + 4, y + 40), (x, y)], jit=0.6, seed=290 + k), 1.4, col=RED)
        s += path(f"M{x} {y} l-5 9 M{x} {y} l6 9", 1.4, col=RED)
    s += label(610, 528, "das Tal · die Orks kommen von Süden", 18, col=RED) if GM else label(620, 578, "das Tal", 20)
    # direction to the next beacon hill
    s += path(rough([(110, 470), (40, 540)], jit=0.8, seed=300), 1.3, dash="6 5")
    s += path("M40 540 l4 -12 M40 540 l12 -4", 1.3)
    if GM:
        s += label(36, 456, "zum nächsten Signalhügel", 16, anchor="start") + label(36, 474, "(Halbarads Lager)", 15, anchor="start", col="#6b4a24")
    else:
        s += label(36, 456, "die Signalfeuer-Linie,", 16, anchor="start") + label(36, 474, "zurück nach Fornost", 16, anchor="start")
    s += trees(700, 420, 8, 40, 310) + trees(90, 140, 8, 40, 311)
    s += compass(735, 390)
    s += cartouche(28, 24, "Die Finsterwacht", "Zustand im Frühjahr TA 2965" if GM else "wie die Gefährten sie vorfinden", 270)
    return frame(s, 23)


# ---------------- The beacon line (players only) ----------------
def beacons():
    s = ""
    MI = 8.5                       # map units per mile
    B = [(334, 372), (454, 302), (574, 232), (694, 158)]
    # Lake Evendim (west edge)
    lake = blob(70, 210, 95, 60, irr=0.12, n=30, seed=401)
    s += path(rough(lake, closed=True, jit=1.5, seed=402), 1.6, fill="#c9c3a4", op=0.9)
    for k in range(5):
        y = 180 + k * 14
        s += path(rough([(20, y), (90 + (k % 2) * 20, y + 2)], jit=0.8, seed=403 + k), 0.6, op=0.6)
    s += label(70, 300, "Lake Evendim", 20)
    # Hills of Evendim
    rr = random.Random(410)
    for k in range(9):
        x, y = 222 + rr.uniform(-40, 40), 158 + rr.uniform(-28, 28)
        s += path(rough([(x - 16, y + 6), (x - 4, y - 10), (x + 6, y - 3), (x + 16, y + 6)], jit=0.8, seg=6, seed=411 + k), 1.2)
    s += label(222, 118, "Hills of Evendim", 19, col="#6b4a24")
    # North Downs: band of hill strokes along the beacon line
    rr = random.Random(420)
    for k in range(46):
        t = rr.random()
        bx = 200 + t * 520 + rr.uniform(-25, 25)
        by = 470 - t * 330 + rr.uniform(-75, 75)
        if min(min(math.hypot(bx - x, by - y), math.hypot(bx - x - 20, by - y - 20), math.hypot(bx - x + 24, by - y - 8)) for x, y in B) < 28:
            continue
        if 530 < bx < 680 and 95 < by < 160:      # keep the Finsterwacht label clear
            continue
        w_ = rr.uniform(10, 18)
        s += path(rough([(bx - w_, by + 5), (bx, by - 8), (bx + w_, by + 5)], jit=0.7, seg=6, seed=430 + k), 1.1, op=0.85)
    s += label(610, 430, "North Downs", 26, rot=-30, col="#6b4a24")
    # the empty north
    s += label(560, 62, "die leeren Lande gen Angmar", 19, col="#6b4a24")
    s += path(rough([(470, 76), (650, 76)], jit=1, seed=440), 0.8, dash="2 5", op=0.6)
    # Greenway from the south to Fornost
    s += path(rough([(150, 600), (160, 540), (172, 490), (180, 466)], jit=1.4, seed=450), 1.3)
    s += path(rough([(178, 600), (186, 540), (196, 492), (202, 468)], jit=1.4, seed=451), 1.3)
    s += label(140, 536, "der Greenway", 19, anchor="end") + label(140, 554, "Bree liegt etwa", 15, anchor="end") + label(140, 570, "100 Meilen südlich", 15, anchor="end")
    # Fornost (Deadmen's Dike): hill with ruins
    s += path(rough(blob(190, 450, 34, 22, irr=0.1, seed=460), closed=True, jit=1, seed=461), 1.4, fill="#d9c69e")
    for k, (x, y) in enumerate([(178, 446), (194, 440), (204, 452)]):
        s += path(rough([(x - 5, y + 4), (x - 5, y - 4), (x + 5, y - 4), (x + 5, y + 4)], jit=0.5, seg=4, seed=470 + k), 1.1)
    s += label(150, 462, "Fornost Erain", 22, anchor="end") + label(150, 480, "(Deadmen's Dike)", 15, anchor="end", col="#6b4a24")
    # the beacon line: dashed path from Fornost through the four marks
    pts = [(214, 440)] + B
    s += path(rough(pts, jit=1.2, seed=480), 1.5, dash="8 6")
    roman = ["I", "II", "III", "IV"]
    for k, (x, y) in enumerate(B[:-1]):
        s += path(rough([(x - 10, y + 8), (x, y - 10), (x + 10, y + 8)], closed=True, jit=0.6, seg=6, seed=490 + k), 1.5, fill="#cdb78c")
        s += f'<circle cx="{x}" cy="{y - 15}" r="4" fill="url(#lamp)"/>'
        s += f'<text x="{x + 14}" y="{y + 24}" font-family="TeX Gyre Pagella" font-size="15" font-weight="700" fill="{RED}" text-anchor="start">{roman[k]}</text>'
    # IV: the Finsterwacht, tower and star
    x, y = B[-1]
    s += path(rough(blob(x, y + 6, 24, 15, irr=0.12, seed=500), closed=True, jit=0.8, seed=501), 1.5, fill="#d9c69e")
    s += path(rough([(x - 6, y + 2), (x - 6, y - 22), (x + 6, y - 22), (x + 6, y + 2)], jit=0.5, seg=6, seed=502), 1.6, fill="#efe2c4")
    star = "M{0} {1} l2.6 6.2 6.6 .5 -5 4.3 1.6 6.4 -5.8 -3.5 -5.8 3.5 1.6 -6.4 -5 -4.3 6.6 -.5z".format(x, y - 46)
    s += path(star, 0.8, col=RED, fill=RED, op=0.9)
    s += f'<text x="{x + 28}" y="{y + 30}" font-family="TeX Gyre Pagella" font-size="15" font-weight="700" fill="{RED}" text-anchor="start">IV</text>'
    s += label(x - 36, y - 34, "das vierte Zeichen:", 16, anchor="end", col="#6b4a24") + label(x - 36, y - 14, "die Finsterwacht?", 20, anchor="end", col=RED)
    s += label(286, 340, "jedes Feuer in Sichtweite des nächsten", 16, rot=-28, col="#6b4a24")
    # rough camp marks: a 3-4 day march at a hard pace
    for k, (x, y) in enumerate([(310, 374), (430, 304), (550, 234)]):
        s += f'<path d="M{x - 5} {y + 12} L{x} {y + 4} L{x + 5} {y + 12} Z" fill="{INK}" opacity="0.75"/>'
    s += label(406, 400, "Lager: je etwa ein Tagesmarsch", 15, anchor="start", col="#6b4a24")
    # scale bar
    x0, y0 = 470, 548
    s += path(f"M{x0} {y0} L{x0 + 20 * MI} {y0}", 1.6)
    for m in (0, 10, 20):
        s += path(f"M{x0 + m * MI} {y0 - 6} L{x0 + m * MI} {y0 + 6}", 1.4)
        s += label(x0 + m * MI, y0 + 22, f"{m}", 15)
    s += path(f"M{x0} {y0} L{x0 + 10 * MI} {y0}", 4, op=0.8)
    s += label(x0 + 20 * MI + 14, y0 + 5, "Meilen", 16, anchor="start")
    s += label(x0 + 10 * MI, y0 - 24, "etwa 60 Meilen von Fornost bis zum vierten Zeichen", 15, col="#6b4a24")
    s += compass(735, 470)
    s += cartouche(28, 24, "Signalfeuer-Linie", "aus der Halle der Schriftrollen", 270)
    return frame(s, 37)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": W * 2, "height": H * 2})
    jobs = []
    for gm in (True, False):
        GM = gm
        suf = "" if gm else "-players"
        jobs += [("map-fornost" + suf, fornost()), ("map-finsterwacht" + suf, finsterwacht())]
    GM = False
    jobs.append(("map-beacons-players", beacons()))
    for name, svg in jobs:
        open(SVG + name + "-de.svg", "w").write(svg)
        pg.set_content(f'<html><body style="margin:0;background:#fff">{svg}</body></html>', wait_until="load")
        pg.screenshot(path=D + name + "-de.png", clip={"x": 0, "y": 0, "width": W * 2, "height": H * 2})
    b.close()
from PIL import Image
for name, _ in jobs:
    Image.open(D + name + "-de.png").convert("RGB").save(D + name + "-de.jpg", quality=88)
    os.remove(D + name + "-de.png")
print("ok")
