#!/usr/bin/env python3
"""Baut die Druckfassung von „Die Finsterwacht“.

    python3 tools/build.py            # beide Fassungen
    python3 tools/build.py buch       # nur eine: blatt | buch

Schritte:
  1. Version und Stand aus git (letztes Tag v*, Commit-Datum) -> build/version.tex
  2. src/finsterwacht.md -> build/body.tex (pandoc + filters/finsterwacht.lua)
  3. src/cards.toml (geprüft mit tools/check.py gegen src/rules.toml) -> build/cards.tex
  4. LuaLaTeX (latexmk) -> build/Die-Finsterwacht-TOR2e-DE.pdf (Blattfassung, gelocht)
     und build/Die-Finsterwacht-TOR2e-DE-Buch.pdf (Buchfassung zum Binden)
  5. Kopie mit Version im Namen -> build/Die-Finsterwacht-TOR2e-DE-v2.0.pdf

Benötigt: pandoc, LuaLaTeX mit latexmk (TeX Live), Python 3.11+.
Ohne luaotfload wird ersatzweise XeLaTeX genutzt (FW_ENGINE=… erzwingt eine Engine).
"""
import datetime
import os
import re
import shutil
import subprocess
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import check  # Gegenstände und Regeln (src/rules.toml), von tor2e-items übernommen

BUILD = os.path.join(ROOT, "build")
JOB = "Die-Finsterwacht-TOR2e-DE"
# Fassung -> (LaTeX-Gerüst, Jobname)
EDITIONS = {
    "blatt": ("latex/finsterwacht.tex", JOB),
    "buch": ("latex/finsterwacht-buch.tex", JOB + "-Buch"),
}


def run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True, **kw)


def git(*args):
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""
    except FileNotFoundError:
        return ""


# ------------------------------------------------------------------ 1. Version
def version():
    """Die Version im PDF ist die Nummer des letzten Tags: v2.1.1 -> „2.1.1“.

    Dritter Rückgabewert ist die genaue Version für den Dateinamen: „v2.1.1“ auf dem
    getaggten Commit, drei Commits danach „v2.1.1+3-abc1234“.
    """
    desc = git("describe", "--tags", "--long", "--match", "v*")
    m = re.match(r"v(.+)-(\d+)-g([0-9a-f]+)$", desc)
    if m:
        ver = m[1]
        slug = "v" + (m[1] if m[2] == "0" else f"{m[1]}+{m[2]}-{m[3]}")
    else:
        commit = git("rev-parse", "--short", "HEAD")
        ver = "0.0"
        slug = "v0.0" + ("-" + commit if commit else "")
    if git("status", "--porcelain", "--untracked-files=no"):
        slug += "-lokal"
    stand = git("log", "-1", "--format=%cd", "--date=format:%d.%m.%Y") or datetime.date.today().strftime("%d.%m.%Y")
    return ver, stand, slug


def tex_escape(s):
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"),
                 ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}")):
        s = s.replace(a, b)
    return s


# ------------------------------------------------------------------ 3. Karten
def kind_line(item, rules):
    """Die Zeile unter dem Namen. Ein Superior Reward macht einen Gegenstand berühmt; ohne ihn
    (und ohne Blessings oder freie Effekte) ist er nur gut gemacht und bekommt das `plain_label`
    der Gegenstandsart statt ihres `label`."""
    kind = rules["types"][item["type"]]
    famous = (any(rules["qualities"][q].get("superior") for q in item.get("qualities", []))
              or item.get("blessings") or item.get("effects"))
    label = kind["plain_label"] if not famous and "plain_label" in kind else kind["label"]
    return " · ".join(x for x in (label, item.get("base"), item.get("craft")) if x)


def quality_text(name, item, rules):
    """Was die Karte hinter dem Namen einer Eigenschaft sagt: die Texte der Teile, die für
    Handwerkskunst und Basis des Gegenstands gelten."""
    effects = check.quality_effects(rules["qualities"][name], item)
    return "; ".join(e["text"] for e in effects if e.get("text"))


def stats_entries(item, rules):
    """Die Werte als (Name, Wert), mit den `modifies` und `sets` der Eigenschaften angewendet;
    die Injury einer vielseitigen Waffe ist „18/20“."""
    item = dict(item)
    for q in item.get("qualities", []):
        for effect in check.quality_effects(rules["qualities"][q], item):
            for stat, value in effect.get("sets", {}).items():
                if stat in item:
                    item[stat] = value
            for stat, change in effect.get("modifies", {}).items():
                for key in (stat, "injury_two_handed") if stat == "injury" else (stat,):
                    if key in item:
                        item[key] += change
    if "load" in item:
        item["load"] = max(0, item["load"])
    entries = []
    if "damage" in item:
        entries.append(("Damage", str(item["damage"])))
    if "injury" in item:
        injury = str(item["injury"])
        if "injury_two_handed" in item:
            injury += f"/{item['injury_two_handed']}"
        entries.append(("Injury", injury))
    if "protection" in item:
        entries.append(("Protection", f"{item['protection']}d"))
    if "parry" in item:
        entries.append(("Parry", f"{item['parry']:+d}"))
    if "load" in item:
        entries.append(("Load", str(item["load"])))
    return entries


def cards_tex():
    rules = check.load_rules()
    db, duplicates = check.load_db()
    problems = check.check(db, rules, duplicates)
    if problems:
        sys.exit("\n".join("Fehler: " + p for p in problems))
    data = check.load_toml("src", "cards.toml")  # Reihenfolge und Sofort-Liste stehen nur hier
    immediate = set(data["immediate"])
    terms = set(db["terms"]) | set(rules["qualities"]) | {t["label"] for t in rules["types"].values()}
    terms = sorted(terms, key=len, reverse=True)
    term_re = re.compile(r"(?<![\w])(" + "|".join(re.escape(t) for t in terms) + r")(?![\w])")

    def it(s):
        return term_re.sub(lambda m: r"\textit{" + m[1] + "}", tex_escape(s))

    def card(key):
        c = db["items"][key]
        up = [r"\fwcardname{" + tex_escape(c["name"]) + "}", r"\fwcardkind{" + it(kind_line(c, rules)) + "}"]
        stats = stats_entries(c, rules)
        if stats:  # Namen wie Tabellenköpfe, die Werte darunter
            heads = " & ".join(r"\fwstathead{" + tex_escape(label) + "}" for label, _ in stats)
            values = " & ".join(tex_escape(value) for _, value in stats)
            up.append(r"\fwcardstats{%d}{%s}{%s}{%s}" % (len(stats), heads, values, it(c.get("stats_note", ""))))
        if c.get("text"):
            up.append(r"\fwcardtext{" + it(c["text"]) + "}")
        # Einfache Rewards und freie Effekte: „Sofort“; bessere Rewards, Banes, Blessings: „Gabe der Wacht“
        sofort, gabe = [], []
        for q in c.get("qualities", []):
            text = quality_text(q, c, rules)
            (sofort if q in immediate else gabe).append(it(q) + (" (" + it(text) + ")" if text else ""))
        sofort += [tex_escape(a) + " (" + it(b) + ")" for a, b in c.get("effects", [])]
        if c.get("banes"):
            gabe.append(it("Bane: " + ", ".join(c["banes"])))
        if c.get("blessings"):
            gabe.append(it(("Blessings: " if len(c["blessings"]) > 1 else "Blessing: ") + ", ".join(c["blessings"])))
        bullets = [(label, items) for label, items in (("Sofort", sofort), ("Gabe der Wacht", gabe)) if items]
        if bullets:
            up.append(r"\begin{fwcardeffects}")
            up += [r"\item \textbf{" + label + ":} " + " · ".join(items) for label, items in bullets]
            up.append(r"\end{fwcardeffects}")
        footer = tex_escape(db["footer"]) if gabe else ""  # die Fußzeile erklärt die Gabe
        return r"\fwcard{" + "\n".join(up) + "}{" + footer + "}"

    # Sechs Karten je Seite; die Reihen (3 × 2 bzw. 2 × 3) bricht \fwcard in finsterwacht.sty um
    order = data["order"]
    pages = [order[i:i + 6] for i in range(0, len(order), 6)]
    out = []
    for page in pages:
        out.append(r"\fwcardspage{" + tex_escape(db["hint"]) + "}{%\n" + "\n".join(card(k) for k in page) + "}")
    return "\n\n".join(out) + "\n"


# ------------------------------------------------------------------ Ablauf
def main():
    editions = sys.argv[1:] or list(EDITIONS)
    for e in editions:
        if e not in EDITIONS:
            sys.exit(f"Unbekannte Fassung „{e}“ – möglich: " + ", ".join(EDITIONS))
    os.makedirs(BUILD, exist_ok=True)
    ver, stand, slug = version()
    with open(os.path.join(BUILD, "version.tex"), "w", encoding="utf-8") as f:
        f.write("\\def\\fwversion{%s}\n\\def\\fwstand{%s}\n" % (tex_escape(ver), stand))
    print(f"Version {ver} · Stand {stand}")

    env = dict(os.environ, FW_BUILD=BUILD)
    run(["pandoc", "src/finsterwacht.md", "-f", "markdown", "-t", "latex",
         "--lua-filter", "filters/finsterwacht.lua",
         "-o", os.path.join(BUILD, "body.tex")], env=env)

    with open(os.path.join(BUILD, "cards.tex"), "w", encoding="utf-8") as f:
        f.write(cards_tex())

    env["TEXINPUTS"] = os.path.join(ROOT, "latex") + "//" + os.pathsep + env.get("TEXINPUTS", "")
    tex = ["-interaction=nonstopmode", "-halt-on-error", "-file-line-error"]
    # LuaLaTeX ist die Referenz (CI); fehlt luaotfload, ersatzweise XeLaTeX
    engine = os.environ.get("FW_ENGINE") or (
        "lualatex" if subprocess.run(["kpsewhich", "luaotfload-main.lua"], capture_output=True, text=True).stdout.strip()
        else "xelatex")
    print("TeX-Engine:", engine)
    for e in editions:
        src, job = EDITIONS[e]
        if shutil.which("latexmk"):
            run(["latexmk", "-" + engine, "-outdir=build", "-jobname=" + job, *tex, src], env=env)
        else:  # ohne latexmk: drei Läufe reichen für Seitenverweise und Lesezeichen
            for _ in range(3):
                run([engine, *tex, "-output-directory=build", "-jobname=" + job, src], env=env)
        # Kopie mit Version im Dateinamen – diese Datei veröffentlicht die CI
        pdf = os.path.join("build", f"{job}-{slug}.pdf")
        shutil.copyfile(os.path.join(BUILD, job + ".pdf"), os.path.join(ROOT, pdf))
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write("pdf=" + pdf.replace(os.sep, "/") + "\n")
        print("fertig:", pdf)


if __name__ == "__main__":
    sys.exit(main())
