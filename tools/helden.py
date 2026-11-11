#!/usr/bin/env python3
"""Vorgefertigte Helden: src/helden.toml -> build/helden.tex (Heldenbögen, quer).

    python3 tools/helden.py           # prüft und schreibt build/helden.tex
    python3 tools/helden.py --check   # prüft nur

Das Skript rechnet aus, was sich aus den Erschaffungsregeln der Core Rules ergibt, damit die
Bögen nicht von Hand nachgerechnet werden müssen:

  * TN = 20 − Attribut, oder 18 − Attribut mit `tn_basis = 18` (Option der Core Rules für kurze
    Spiele); Prowess: −1 auf ein TN, Kings of Men: +1 auf ein Attribut
  * Endurance, Hope, Parry aus den Kulturwerten unten, dazu Hardiness, Confidence, Nimbleness
  * Skills = Kulturwerte (ggf. mit den Tauschpaaren der Hausregel) + Previous Experience;
    die Previous Experience muss genau 10 Punkte kosten (Skill-Rang 1/2/3/4: 1/2/3/5 Punkte,
    Combat-Rang 1/2/3: 2/4/6 Punkte)
  * Attribute aus einer Zeile der Kulturtabelle, Distinctive Features aus der Liste der Kultur,
    Standard of Living für Kettenhemd, Kettenpanzer, Schild und Großen Schild; Treasure zu Beginn
  * Load aus der Ausrüstung (Redoubtable: Rüstung und Helm halb, aufgerundet), Belohnung
    und Schild in Damage, Injury und Parry eingerechnet

Die Kulturwerte unten sind aus den Core Rules (Third Printing, Kapitel 3) abgeschrieben und mit Errata
und FAQ abgeglichen (FAQ: Redoubtable halbiert die Load erst nach Cunning Make). Dieselben Werte stehen im
Heldenbuch (github.com/Andx667/tor2e-helden, src/rules.toml).

Benötigt: Python 3.11+.
"""
import math
import os
import re
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.environ.get("FW_BUILD") or os.path.join(ROOT, "build")

SKILLS = [
    ["Awe", "Athletics", "Awareness", "Hunting", "Song", "Craft"],            # Strength
    ["Enhearten", "Travel", "Insight", "Healing", "Courtesy", "Battle"],      # Heart
    ["Persuade", "Stealth", "Scan", "Explore", "Riddle", "Lore"],             # Wits
]
ALL_SKILLS = [s for g in SKILLS for s in g]
ATTRS = ["Strength", "Heart", "Wits"]
PROFS = ["Axes", "Bows", "Spears", "Swords"]


def sk(*vals):
    return dict(zip(ALL_SKILLS, vals))


# Kulturwerte der Core Rules: Zuschläge auf Endurance/Hope/Parry, Skill-Werte, die Skills, aus
# denen der favorisierte gewählt wird, die Combat Proficiencies (eine auf 2, eine andere auf 1)
# und die Kultureinträge mit Kurztext für den Bogen.
CULTURES = {
    "Bardings": dict(
        mods=(20, 8, 12),
        skills=sk(1, 1, 0, 2, 1, 1, 2, 1, 2, 0, 2, 2, 3, 0, 1, 1, 0, 1),
        favoured=["Enhearten", "Athletics"],
        profs2=["Bows", "Swords"],
        rows=[(5, 7, 2), (4, 7, 3), (5, 6, 3), (4, 6, 4), (5, 5, 4), (6, 6, 2)],
        features=["Bold", "Eager", "Fair", "Fierce", "Generous", "Proud", "Tall", "Wilful"],
        blessings=[("Stout-hearted", "Deine *Valour*-Würfe sind *favoured*.")],
    ),
    "Dwarves of Durin's Folk": dict(
        mods=(22, 8, 10),
        skills=sk(2, 1, 0, 0, 1, 2, 0, 3, 0, 0, 1, 1, 0, 0, 3, 2, 2, 1),
        favoured=["Craft", "Travel"],
        profs2=["Axes", "Swords"],
        rows=[(7, 2, 5), (7, 3, 4), (6, 3, 5), (6, 4, 4), (5, 4, 5), (6, 2, 6)],
        features=["Cunning", "Fierce", "Lordly", "Proud", "Secretive", "Stern", "Wary", "Wilful"],
        blessings=[("Redoubtable", "Rüstung und Helm zählen nur halb zur *Load* (schon eingerechnet).")],
        redoubtable=True,
    ),
    "Elves of Lindon": dict(
        mods=(20, 8, 12),
        skills=sk(2, 2, 2, 0, 2, 2, 1, 0, 0, 1, 0, 0, 0, 3, 0, 0, 0, 3),
        favoured=["Lore", "Song"],
        profs2=["Bows", "Spears"],
        rows=[(5, 2, 7), (4, 3, 7), (5, 3, 6), (4, 4, 6), (5, 4, 5), (6, 2, 6)],
        features=["Fair", "Keen-eyed", "Lordly", "Merry", "Patient", "Subtle", "Swift", "Wary"],
        blessings=[("Elven-skill", "1 *Hope*: ein *Magical success* bei einem Skill-Wurf, solange du nicht *Miserable* bist."),
                   ("The Long Defeat", "*Shadow* schüttelst du schwerer ab als die Sterblichen.")],
    ),
    "Hobbits of the Shire": dict(
        mods=(18, 10, 12),
        skills=sk(0, 0, 2, 0, 2, 1, 0, 0, 2, 1, 2, 0, 2, 3, 0, 0, 3, 0),
        favoured=["Courtesy", "Stealth"],
        profs2=["Bows", "Swords"],
        rows=[(3, 6, 5), (3, 7, 4), (2, 7, 5), (4, 6, 4), (4, 5, 5), (2, 6, 6)],
        features=["Eager", "Fair-spoken", "Faithful", "Honourable", "Inquisitive", "Keen-eyed", "Merry", "Rustic"],
        blessings=[("Hobbit-sense", "*Wisdom*-Würfe *favoured*; (1d) auf *Shadow Tests* gegen *Greed*."),
                   ("Halflings", "Nur kleine Waffen (*Core Rules* S. 38), kein Great shield.")],
    ),
    "Men of Bree": dict(
        mods=(20, 10, 10),
        skills=sk(0, 1, 1, 1, 1, 2, 2, 1, 2, 0, 3, 0, 2, 1, 1, 1, 2, 0),
        favoured=["Insight", "Riddle"],
        profs2=["Axes", "Spears"],
        rows=[(2, 5, 7), (3, 4, 7), (3, 5, 6), (4, 4, 6), (4, 5, 5), (2, 6, 6)],
        features=["Cunning", "Fair-spoken", "Faithful", "Generous", "Inquisitive", "Patient", "Rustic", "True-hearted"],
        blessings=[("Bree-blood", "Deine Gemeinschaft hat 1 *Fellowship*-Punkt mehr.")],
    ),
    "Rangers of the North": dict(
        mods=(20, 6, 14),
        skills=sk(1, 2, 2, 2, 0, 0, 0, 2, 0, 2, 0, 2, 0, 2, 1, 2, 0, 2),
        favoured=["Hunting", "Lore"],
        profs2=["Spears", "Swords"],
        rows=[(7, 5, 2), (7, 4, 3), (6, 5, 3), (6, 4, 4), (5, 5, 4), (6, 6, 2)],
        features=["Bold", "Honourable", "Secretive", "Stern", "Subtle", "Swift", "Tall", "True-hearted"],
        blessings=[("Kings of Men", "+1 auf *{kings}* (schon eingerechnet)."),
                   ("Allegiance of the Dúnedain", "In der *Fellowship Phase* erholst du weniger *Hope* (*Core Rules*).")],
        kings=True,
    ),
}

CALLINGS = {
    "Captain": (["Battle", "Enhearten", "Persuade"], "Leadership", "Lure of Power"),
    "Champion": (["Athletics", "Awe", "Hunting"], "Enemy-lore", "Curse of Vengeance"),
    "Messenger": (["Courtesy", "Song", "Travel"], "Folk-lore", "Wandering-madness"),
    "Scholar": (["Craft", "Lore", "Riddle"], "Rhymes of Lore", "Lure of Secrets"),
    "Treasure Hunter": (["Explore", "Scan", "Stealth"], "Burglary", "Dragon-sickness"),
    "Warden": (["Awareness", "Healing", "Insight"], "Shadow-lore", "Path of Despair"),
}

VIRTUES = {
    "Confidence": "+2 *Hope*, eingerechnet",
    "Dour-handed": "+1 *Damage* bei einem *Heavy Blow*",
    "Hardiness": "+2 *Endurance*, eingerechnet",
    "Mastery": "zwei weitere *favoured* Skills, markiert",
    "Nimbleness": "+1 *Parry*, eingerechnet",
    "Prowess": "−1 auf das TN von *{attr}*, eingerechnet",
}

# Ausrüstung (Werte der Core Rules, wie src/rules.toml in tor2e-finsterwacht).
# weapon: (Proficiency, Damage, Injury, Injury zweihändig, Load); armour/helm: (Protection, Load);
# shield: (Parry, Load)
WEAPONS = {
    "Dagger": ("Brawling", 2, 14, None, 0),
    "Short sword": ("Swords", 3, 16, None, 1),
    "Sword": ("Swords", 4, 16, None, 2),
    "Long sword": ("Swords", 5, 16, 18, 3),
    "Short spear": ("Spears", 3, 14, None, 2),
    "Spear": ("Spears", 4, 14, 16, 3),
    "Axe": ("Axes", 5, 18, None, 2),
    "Long-hafted axe": ("Axes", 6, 18, 20, 3),
    "Bow": ("Bows", 3, 14, None, 2),
}
ARMOUR = {"Leather shirt": (1, 3), "Leather corslet": (2, 6), "Mail-shirt": (3, 9), "Coat of mail": (4, 12)}
HELMS = {"Helm": (1, 4)}
SHIELDS = {"Buckler": (1, 2), "Shield": (2, 4), "Great shield": (3, 6)}
REWARDS = {
    "Close-fitting": ("armour", "+2 auf *Protection*-Würfe"),
    "Cunning Make": ("gear", "*Load* −2"),
    "Fell": ("weapon", "*Injury* +2, eingerechnet"),
    "Grievous": ("weapon", "*Damage* +1, eingerechnet"),
    "Keen": ("weapon", "*Piercing Blow* schon bei 9"),
    "Reinforced": ("shield", "*Parry* +1, eingerechnet"),
}
GEAR_DE = {
    "Dagger": "Dolch", "Short sword": "Kurzschwert", "Sword": "Schwert", "Long sword": "Langschwert",
    "Short spear": "Kurzspeer", "Spear": "Speer", "Axe": "Axt", "Long-hafted axe": "Langstielaxt",
    "Bow": "Bogen", "Leather shirt": "Lederhemd", "Leather corslet": "Lederharnisch",
    "Mail-shirt": "Kettenhemd", "Coat of mail": "Kettenpanzer", "Helm": "Helm", "Buckler": "Faustschild",
    "Shield": "Schild", "Great shield": "Großer Schild",
}


# Previous Experience (Core Rules S. 46): Kosten je erreichtem Rang
SKILL_COSTS = [1, 2, 3, 5]
# Standard of Living (S. 72, 100): Treasure zu Beginn und Mindeststand für schwere Rüstung und Schilde
TREASURE = {"Frugal": 0, "Common": 30, "Prosperous": 90}
LIVING_ORDER = ["Poor", "Frugal", "Common", "Prosperous", "Rich", "Very Rich"]
NEEDS_LIVING = {"Mail-shirt": "Common", "Coat of mail": "Prosperous", "Shield": "Common", "Great shield": "Prosperous"}


class Problem(Exception):
    pass


def compute(h, tn_basis=20):
    """Alle Werte eines Helden; wirft Problem bei Regelverstößen."""
    who = h.get("name", "?")

    def fail(msg):
        raise Problem(f"{who}: {msg}")

    base = h.get("basis", h["kultur"])
    if base not in CULTURES:
        fail(f"unbekannte Kultur „{base}“")
    cul = CULTURES[base]
    if h["berufung"] not in CALLINGS:
        fail(f"unbekannte Berufung „{h['berufung']}“")
    cfav, cfeat, cpath = CALLINGS[h["berufung"]]

    attrs = {a: h["attribute"][a] for a in ATTRS}
    if tuple(attrs[a] for a in ATTRS) not in cul["rows"]:
        fail(f"Attribute {'/'.join(str(attrs[a]) for a in ATTRS)} stehen in keiner Zeile der Tabelle von {base}")
    if cul.get("kings"):
        k = h.get("kings_of_men")
        if k not in ATTRS:
            fail("Kings of Men: `kings_of_men` muss ein Attribut nennen")
        attrs[k] += 1
    tn = {a: tn_basis - attrs[a] for a in ATTRS}
    if h["tugend"] == "Prowess":
        p = h.get("prowess")
        if p not in ATTRS:
            fail("Prowess: `prowess` muss ein Attribut nennen")
        tn[p] -= 1

    skills = dict(cul["skills"])
    for a, b in h.get("tausch", []):
        skills[a], skills[b] = skills[b], skills[a]
    cost = 0
    for s in h.get("erfahrung", []):
        if s not in skills:
            fail(f"Previous Experience: unbekannter Skill „{s}“")
        skills[s] += 1
        if skills[s] > len(SKILL_COSTS):
            fail(f"{s} {skills[s]}: höher als {len(SKILL_COSTS)} geht es bei der Erschaffung nicht")
        cost += SKILL_COSTS[skills[s] - 1]
    profs = dict(h["kampf"])
    ranks = sorted(profs.values())
    if ranks != [1, 2] or not set(profs) <= set(PROFS):
        fail("Combat Proficiencies: genau eine auf 2 und eine andere auf 1")
    two = [p for p, r in profs.items() if r == 2][0]
    if two not in cul["profs2"]:
        fail(f"{two} 2 ist für {base} nicht wählbar ({', '.join(cul['profs2'])})")
    for p in h.get("kampf_erfahrung", []):
        profs[p] = profs.get(p, 0) + 1
        cost += 2 * profs[p]
    if cost != 10:
        fail(f"Previous Experience kostet {cost} statt 10 Punkte")

    fav_c = h["favoured_kultur"]
    if fav_c not in cul["favoured"]:
        fail(f"favorisierter Kultur-Skill muss einer von {cul['favoured']} sein")
    fav_b = h["favoured_berufung"]
    if len(fav_b) != 2 or not set(fav_b) <= set(cfav):
        fail(f"zwei favorisierte Skills aus {cfav}")
    favoured = {fav_c, *fav_b} | set(h.get("mastery", []))
    if len(favoured) != 3 + 2 * (h["tugend"] == "Mastery"):
        fail("favorisierte Skills doppelt gewählt")

    end_m, hope_m, parry_m = cul["mods"]
    endurance = attrs["Strength"] + end_m + 2 * (h["tugend"] == "Hardiness")
    hope = attrs["Heart"] + hope_m + 2 * (h["tugend"] == "Confidence")
    parry = attrs["Wits"] + parry_m + (h["tugend"] == "Nimbleness")

    rw = h["belohnung"]
    if rw["art"] not in REWARDS:
        fail(f"unbekannte Belohnung „{rw['art']}“")
    if rw["gegenstand"] not in h["ausruestung"]:
        fail("die Belohnung sitzt nicht auf einem Stück der Ausrüstung")
    kind = REWARDS[rw["art"]][0]
    target = rw["gegenstand"]
    if kind == "weapon" and target not in WEAPONS or kind == "shield" and target not in SHIELDS \
            or kind == "armour" and target not in {**ARMOUR, **HELMS} \
            or kind == "gear" and target not in {**ARMOUR, **HELMS, **SHIELDS}:
        fail(f"{rw['art']} passt nicht zu {target}")

    gear, load, shield = [], 0, 0
    half = cul.get("redoubtable", False)
    for g in h["ausruestung"]:
        mine = g == target
        r = rw["art"] if mine else None
        if g in WEAPONS:
            prof, dmg, inj, inj2, ld = WEAPONS[g]
            if prof != "Brawling" and prof not in profs:
                fail(f"{g}: keine Combat Proficiency in {prof}")
            dmg += r == "Grievous"
            inj += 2 * (r == "Fell")
            if inj2:
                inj2 += 2 * (r == "Fell")
            gear.append(dict(kind="weapon", name=g, prof=prof, damage=dmg, injury=inj, injury2=inj2,
                             load=ld, reward=r))
            load += ld
        elif g in ARMOUR or g in HELMS:
            prot, ld = ARMOUR.get(g) or HELMS[g]
            ld -= 2 * (r == "Cunning Make")
            if half:
                ld = math.ceil(ld / 2)
            gear.append(dict(kind="armour", name=g, protection=prot, load=ld, reward=r,
                             bonus=2 if r == "Close-fitting" else 0))
            load += ld
        elif g in SHIELDS:
            par, ld = SHIELDS[g]
            par += r == "Reinforced"
            ld -= 2 * (r == "Cunning Make")
            shield = par
            gear.append(dict(kind="shield", name=g, parry=par, load=ld, reward=r))
            load += ld
        else:
            fail(f"unbekannte Ausrüstung „{g}“")

    for m in h["merkmale"]:
        if not m:
            fail("leeres Merkmal")
    if len(h["merkmale"]) != 2:
        fail("zwei Distinctive Features aus der Kultur")
    for m in h["merkmale"]:
        if m not in cul["features"]:
            fail(f"Distinctive Feature „{m}“ gehört nicht zu {base} ({', '.join(cul['features'])})")
    for g in h["ausruestung"]:
        need = NEEDS_LIVING.get(g)
        if need and LIVING_ORDER.index(LIVING[base]) < LIVING_ORDER.index(need):
            fail(f"{g} braucht mindestens den Standard of Living {need} ({base}: {LIVING[base]})")
    if h["tugend"] not in VIRTUES:
        fail(f"unbekannte Tugend „{h['tugend']}“")
    return dict(attrs=attrs, tn=tn, skills=skills, favoured=favoured, profs=profs, endurance=endurance,
                hope=hope, parry=parry, shield=shield, gear=gear, load=load, culture=cul,
                feature=cfeat, path=cpath)


# ------------------------------------------------------------------ LaTeX
TEX_ESCAPES = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
               "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def esc(s):
    return re.sub(r"[\\&%$#_{}~^]", lambda m: TEX_ESCAPES[m[0]], s)


def md(s):
    """*kursiv*, **fett**, „…“ bleibt; sonst nur maskieren."""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", s)
    s = re.sub(r"\*(.+?)\*", r"\\emph{\1}", s)
    return s


def it(s):
    return r"\emph{" + esc(s) + "}"


LIVING = {"Bardings": "Prosperous", "Dwarves of Durin's Folk": "Prosperous", "Elves of Lindon": "Frugal",
          "Hobbits of the Shire": "Common", "Men of Bree": "Common", "Rangers of the North": "Frugal"}
TWO_HANDED_ONLY = {"Bow"}


def node(x, y, style, text, anchor="base west", extra=""):
    return r"\node[%s, anchor=%s%s] at (%s,%s) {%s};" % (style, anchor, extra, x, y, text)


def rule(x1, x2, y):
    return r"\draw[fwh rule] (%s,%s)--(%s,%s);" % (x1, y, x2, y)


def field(x1, x2, y, label, value, style="fwh ink"):
    """Kopffeld wie auf dem Bogen der Core Rules: Beschriftung, Eintrag, Linie darunter."""
    return [node(x1, y, "fwh lab", label), node(x1 + len_label(label), y, style, value), rule(x1, x2, y - 1.4)]


def len_label(label):
    return 1.25 * len(label) + 2.4   # Breite der Kapitälchen-Beschriftung, grob in mm


def sheet(h, v, patron=""):
    cul = v["culture"]
    base = h.get("basis", h["kultur"])
    out = []
    # ---------------------------------------------------------------- Kopf
    out.append(r"\draw[fwh red, fill=fwparchdark, rounded corners=1mm] (54,159.5) rectangle (144,171);")
    out.append(node(99, 168.6, "fwh lab", "Name", anchor="base"))
    out.append(node(99, 162.6, "fwh ink", r"\fontsize{19}{20}\selectfont " + esc(h["name"]), anchor="base"))
    out.append(node(148, 167.6, "fwh note", md(h["zeile"]), anchor="north west", extra=", text width=44mm"))
    out.append(node(6, 167.6, "fwh note", "", anchor="north west"))
    kultur = esc(h["kultur"]) if h.get("basis") else esc(h["kultur"])
    out += field(6, 82, 152, "Heroic Culture", kultur)
    out += field(6, 82, 145, "Cultural Blessing", " – ".join(esc(n) for n, _ in cul["blessings"]),
                 style="fwh inks")
    out += field(6, 82, 138, "Calling", esc(h["berufung"]))
    out += field(86, 100, 152, "Age", esc(h["alter"]), style="fwh inks")
    out += field(102, 142, 152, "Standard of Living", esc(LIVING[base]), style="fwh inks")
    out += field(86, 140, 145, "Patron", esc(patron), style="fwh inks")
    out += field(86, 140, 138, "Shadow Path", esc(v["path"]), style="fwh inks")
    out += field(144, 192, 152, "Distinctive Features", " – ".join(esc(x) for x in h["merkmale"]), style="fwh inks")
    out += [node(146, 145, "fwh inks", esc(v["feature"])), rule(144, 192, 143.6)]
    out += field(144, 172, 138, "Flaws", "")
    out += [node(175, 138, "fwh lab", "Treasure"), r"\draw[fwh thin] (185,136.6) rectangle (192,141.6);",
            node(188.5, 137.7, "fwh inks", str(TREASURE[LIVING[base]]), anchor="base")]
    if h.get("basis"):
        out.append(node(6, 133.4, "fwh note", r"%s: Werte wie \emph{%s} (Hausregel)" % (esc(h["kultur"]), esc(h["basis"]))))

    # ---------------------------------------------------------------- Attributspalten
    derived = {"Strength": ("Endurance", v["endurance"], ""),
               "Heart": ("Hope", v["hope"], ""),
               "Wits": ("Parry", v["parry"] + v["shield"],
                        (r"%d + Schild %d" % (v["parry"], v["shield"])) if v["shield"] else "")}
    for x in (68, 130):
        out.append(r"\draw[fwh red] (%d,130)--(%d,26);" % (x, x))
    out.append(r"\draw[fwh red] (6,130.5)--(192,130.5);")
    for gi, attr in enumerate(ATTRS):
        x0 = 6 + gi * 62
        cx = x0 + 31
        out.append(node(cx, 124.5, "fwh title", attr, anchor="base"))
        tx, ty = x0 + 22, 110
        out.append(r"\fwhdia{%s}{%s}{11}{%d}{24}" % (tx, ty, v["tn"][attr]))
        out.append(r"\fwhdia{%s}{%s}{5.6}{%d}{15}" % (tx + 15, ty + 7, v["attrs"][attr]))
        dname, dval, dnote = derived[attr]
        out.append(r"\fwhdia{%s}{%s}{5.6}{%d}{15}" % (tx + 15, ty - 7, dval))
        out.append(node(tx - 12.5, ty - 9, "fwh lab", "TN"))
        out.append(node(tx + 21.5, ty + 9.5, "fwh lab", "Rating"))
        out.append(node(tx + 21.5, ty - 10.5, "fwh lab", dname))
        if dnote:
            out.append(node(tx + 21.5, ty - 13.3, "fwh note", dnote))
        # Skills
        for k, sname in enumerate(SKILLS[gi]):
            y = 85.5 - k * 5.6
            out.append(r"\fwhbox{%s}{%s}{%d}" % (x0 + 2.5, y + 0.9, sname in v["favoured"]))
            out.append(node(x0 + 6, y, "fwh name", sname))
            out.append(rule(x0 + 5.5, x0 + 31, y - 1.6))
            for j in range(6):
                out.append(r"\fwhpip{%s}{%s}{%d}" % (round(x0 + 34 + j * 4.5, 2), y + 0.9, j < v["skills"][sname]))
    out.append(r"\draw[fwh red] (6,93.6)--(86,93.6); \draw[fwh red] (112,93.6)--(192,93.6);")
    out.append(node(99, 92.4, "fwh title", "Skills", anchor="base"))
    out.append(r"\draw[fwh red] (6,53)--(192,53);")

    # unter Strength: Combat Proficiencies
    out.append(node(37, 47.5, "fwh sub", "Combat Proficiencies", anchor="base"))
    for k, prof in enumerate(PROFS):
        y = 42 - k * 4.9
        out.append(node(8, y, "fwh name", prof))
        out.append(rule(7.5, 31, y - 1.5))
        for j in range(6):
            out.append(r"\fwhpip{%s}{%s}{%d}" % (round(40 + j * 4.5, 2), y + 0.9, j < v["profs"].get(prof, 0)))
    # unter Heart: Rewards und Valour; unter Wits: Virtues und Wisdom
    rw = h["belohnung"]
    reward = "%s %s" % (esc(rw["art"]), esc(GEAR_DE[rw["gegenstand"]]))
    virtue = esc(h["tugend"])
    for x0, title, lab, ink, note in (
            (68, "Rewards", "Valour", reward, md(REWARDS[rw["art"]][1])),
            (130, "Virtues", "Wisdom", virtue, md(VIRTUES[h["tugend"]].format(attr=h.get("prowess", ""))))):
        out.append(node(x0 + 26, 47.5, "fwh sub", title, anchor="base"))
        out.append(r"\fwhdia{%s}{%s}{4.8}{1}{12}" % (x0 + 53, 44))
        out.append(node(x0 + 46.5, 50, "fwh lab", lab, anchor="base east"))
        out.append(node(x0 + 4, 38, "fwh ink", ink))
        out.append(rule(x0 + 3, x0 + 59, 36.4))
        out.append(node(x0 + 4, 33.2, "fwh note", note, anchor="north west", extra=", text width=54mm"))
    out.append(r"\draw[fwh red] (6,25.5)--(192,25.5);")

    # ---------------------------------------------------------------- War Gear und Rüstung
    out.append(node(7, 21, "fwh sub", "War Gear"))
    for x, lab in ((58, "Damage"), (70, "Injury"), (81, "Load"), (89, "Notes")):
        out.append(node(x, 21, "fwh lab", lab))
    weapons = [g for g in v["gear"] if g["kind"] == "weapon"]
    for k in range(3):
        y = 15.5 - k * 5
        out.append(rule(7, 132, y - 1.5))
        if k >= len(weapons):
            continue
        g = weapons[k]
        notes = []
        if g["injury2"]:
            notes.append("1- oder 2-händig, 2h: Injury %d" % g["injury2"])
        elif g["name"] in TWO_HANDED_ONLY:
            notes.append("2-händig, Fernkampf")
        if g.get("reward"):
            notes.append(g["reward"] + (" (Piercing Blow ab 9)" if g["reward"] == "Keen" else ""))
        out.append(node(8, y, "fwh ink", esc(GEAR_DE[g["name"]])))
        out.append(node(62, y, "fwh ink", str(g["damage"]), anchor="base"))
        out.append(node(73.5, y, "fwh ink", str(g["injury"]), anchor="base"))
        out.append(node(83.5, y, "fwh ink", str(g["load"]), anchor="base"))
        out.append(node(89, y, "fwh inks", r"\fontsize{8.4}{9}\selectfont " + esc(" · ".join(notes))))
    out.append(r"\draw[fwh red] (135,25.5)--(135,3);")
    out.append(node(138, 21, "fwh sub", "Armour"))
    out.append(node(176, 21, "fwh lab", "Protection", anchor="base"))
    out.append(node(188.5, 21, "fwh lab", "Load", anchor="base"))
    armour = [g for g in v["gear"] if g["kind"] == "armour" and g["name"] != "Helm"]
    helm = [g for g in v["gear"] if g["name"] == "Helm"]
    shield = [g for g in v["gear"] if g["kind"] == "shield"]
    rows = [("", armour, lambda g: "%dd%s" % (g["protection"], " +2" if g["bonus"] else "")),
            ("Helm", helm, lambda g: "+%dd" % g["protection"]),
            ("Shield", shield, lambda g: "Parry +%d" % g["parry"])]
    for k, (lab, items, val) in enumerate(rows):
        y = 15.5 - k * 5
        if lab:
            out.append(node(138, y, "fwh lab", lab))
        out.append(rule(137, 192, y - 1.5))
        if items:
            g = items[0]
            out.append(node(147, y, "fwh ink", esc(GEAR_DE[g["name"]])))
            out.append(node(176, y, "fwh inks", val(g), anchor="base"))
            out.append(node(188.5, y, "fwh ink", str(g["load"]), anchor="base"))

    # ---------------------------------------------------------------- rechte Spalte
    out.append(r"\draw[fwh red] (197,172)--(197,3);")
    out.append(r"\draw[fwh thin, fill=fwparch] (201,131) rectangle (266,171);")
    out.append(node(203, 168.4, "fwh lab", "Hintergrund"))
    out.append(node(203, 166, "fwh txt", md(h["kurz"]), anchor="north west", extra=", text width=61mm"))
    for k, lab in enumerate(["Adventure Points", "Skill Points", "Fellowship Score"]):
        x = 211 + k * 22
        out.append(node(x, 126.2, "fwh lab", lab, anchor="base"))
        out.append(r"\fwhdia{%s}{%s}{4.8}{%s}{12}" % (x, 119, "" if k == 2 else "0"))
    for y0, big, sm1, v1, sm2, v2 in ((101, "Current Endurance", "Load", str(v["load"]), "Fatigue", "0"),
                                      (80, "Current Hope", "Shadow", "0", "Shadow Scars", "0")):
        out.append(r"\fwhdia{%s}{%s}{8.5}{}{18}" % (211, y0))
        out.append(node(222, y0 + 6.2, "fwh sub", big))
        out.append(r"\fwhdia{%s}{%s}{4.4}{%s}{12}" % (229, y0 - 1.5, v1))
        out.append(node(229, y0 - 8.4, "fwh lab", sm1, anchor="base"))
        out.append(r"\fwhdia{%s}{%s}{4.4}{%s}{12}" % (251, y0 - 1.5, v2))
        out.append(node(251, y0 - 8.4, "fwh lab", sm2, anchor="base"))
    out.append(node(211, 89.5, "fwh note", "max %d" % v["endurance"], anchor="base"))
    out.append(node(211, 68.5, "fwh note", "max %d" % v["hope"], anchor="base"))
    out.append(r"\draw[fwh red] (200,65)--(266,65);")
    out.append(node(201, 60.5, "fwh sub", "Conditions"))
    for k, (cname, trig) in enumerate((("Weary", r"\emph{Load} $\geq$ akt. \emph{Endurance}"),
                                      ("Miserable", r"\emph{Shadow} $\geq$ akt. \emph{Hope}"),
                                      ("Wounded", ""))):
        y = 55 - k * 5.2
        out.append(r"\fwhbox{%s}{%s}{0}" % (203, y + 0.9))
        out.append(node(206, y, "fwh name", r"\emph{%s}" % cname))
        if trig:
            out.append(node(221, y, "fwh note", r"\fontsize{5.8}{6.6}\selectfont " + trig))
    out.append(r"\draw[fwh thin] (250,43) rectangle (266,56);")
    out.append(node(251, 57.6, "fwh lab", "Injury"))
    out.append(r"\draw[fwh red] (200,40)--(266,40);")
    out.append(node(201, 35.5, "fwh sub", "Travelling Gear"))
    for k in range(3):
        y = 29.5 - k * 5.2
        out.append(rule(201, 266, y - 1.5))
        if k < len(h["nuetzlich"]):
            u = h["nuetzlich"][k]
            out.append(node(202, y, "fwh inks", r"%s \textsc{(%s)}" % (esc(u["name"]), esc(u["skill"]).upper())))
    out.append(node(201, 11.2, "fwh note", r"\fontsize{6.2}{7.4}\selectfont " + r"\par ".join(
        r"\textbf{\emph{%s}}: %s" % (esc(n), md(t.format(kings=h.get("kings_of_men", ""))))
        for n, t in cul["blessings"]), anchor="north west", extra=", text width=64mm"))

    label = "held-" + h["id"]
    return r"\fwhero{%s}{%s}{%%" % (label, esc(h["name"])) + "\n" + "\n".join(out) + "}\n"


def main():
    with open(os.path.join(ROOT, "src", "helden.toml"), "rb") as f:
        data = tomllib.load(f)
    out, problems = [], []
    first = True
    for h in data["helden"]:
        try:
            v = compute(h, data.get("tn_basis", 20))
        except (Problem, KeyError) as e:
            problems.append(str(e) if isinstance(e, Problem) else f"{h.get('name', '?')}: Feld fehlt: {e}")
            continue
        if first:
            out.append(r"\fwherogroup{%s}" % esc(data.get("gruppe", "Vorgefertigte Helden")))
            first = False
        out.append(sheet(h, v, data.get("patron", "")))
        print(f"  {h['name']}: End {v['endurance']}, Hope {v['hope']}, Parry {v['parry']}"
              f"{'+' + str(v['shield']) if v['shield'] else ''}, Load {v['load']}")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    if "--check" not in sys.argv:
        os.makedirs(BUILD, exist_ok=True)
        with open(os.path.join(BUILD, "helden.tex"), "w", encoding="utf-8") as f:
            f.write("% erzeugt von tools/helden.py aus src/helden.toml\n" + "\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
