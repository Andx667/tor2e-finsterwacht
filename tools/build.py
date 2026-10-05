#!/usr/bin/env python3
"""Baut die Druckfassung von „Die Finsterwacht“.

    python3 tools/build.py            # beide Fassungen
    python3 tools/build.py buch       # nur eine: blatt | buch

Schritte:
  1. Version und Stand aus git (letztes Tag v*, Commit-Datum) -> build/version.tex
  2. src/finsterwacht.md -> build/body.tex (pandoc + filters/finsterwacht.lua)
  3. src/cards.toml -> build/cards.tex
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
def cards_tex():
    with open(os.path.join(ROOT, "src", "cards.toml"), "rb") as f:
        data = tomllib.load(f)
    terms = sorted(data["terms"], key=len, reverse=True)
    term_re = re.compile(r"(?<![\w])(" + "|".join(re.escape(t) for t in terms) + r")(?![\w])")

    def it(s):
        return term_re.sub(lambda m: r"\textit{" + m[1] + "}", tex_escape(s))

    def card(key):
        c = data["cards"][key]
        up = [r"\fwcardname{" + tex_escape(c["name"]) + "}", r"\fwcardkind{" + it(c["kind"]) + "}"]
        if "stats" in c:
            up.append(r"\fwcardstats{" + it(c["stats"]) + "}{" + it(c.get("stats_note", "")) + "}")
        up.append(r"\fwcardtext{" + it(c["text"]) + "}")
        up.append(r"\begin{fwcardeffects}")
        up += [r"\item \textbf{" + tex_escape(a) + ":} " + it(b) for a, b in c["effects"]]
        up.append(r"\end{fwcardeffects}")
        return r"\fwcard{" + "\n".join(up) + "}{" + tex_escape(data["footer"]) + "}"

    # Sechs Karten je Seite; die Reihen (3 × 2 bzw. 2 × 3) bricht \fwcard in finsterwacht.sty um
    order = data["order"]
    pages = [order[i:i + 6] for i in range(0, len(order), 6)]
    out = []
    for page in pages:
        out.append(r"\fwcardspage{" + tex_escape(data["hint"]) + "}{%\n" + "\n".join(card(k) for k in page) + "}")
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
