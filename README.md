# Die Finsterwacht

Ein Abenteuer für *The One Ring, 2nd Edition* · Eriador, Frühjahr TA 2965.

Dieses Repository enthält den Text des Abenteuers und die Pipeline, die daraus die
Druckfassung baut. Bei jedem Commit baut GitHub Actions das PDF
(Reiter **Actions** → letzter Lauf → Artefakt **Die-Finsterwacht-PDF**).

## Aufbau

| Pfad | Inhalt |
| --- | --- |
| `src/finsterwacht.md` | Der Abenteuertext (Pandoc-Markdown) – hier wird geschrieben |
| `src/cards.toml` | Die Gegenstandskarten (Werte, Texte, Reihenfolge) |
| `assets/maps/` | Die gezeichneten Karten als JPG, Quellen als SVG in `svg/` |
| `latex/finsterwacht.sty` | Das Layout: Ränder, Notizspalte, Kästen, Tabellen, Karten, Handouts |
| `latex/finsterwacht.tex` | Das Gerüst der Druckfassung (Titel, Anhänge, Karten, Handouts) |
| `filters/finsterwacht.lua` | Pandoc-Filter: Markdown-Elemente → Layout-Bausteine |
| `tools/build.py` | Baut das PDF |
| `tools/maps.py` | Zeichnet die Karten neu (optional, braucht Playwright) |
| `.github/workflows/build.yml` | CI: baut das PDF bei jedem Commit |

## Schreibregeln im Markdown

- `## Kapitel {#id}` beginnt ein Kapitel auf neuer Seite mit Notizspalte;
  `{#id .nonotes}` setzt es ohne Notizspalte in voller Breite.
- `### Abschnitt` ist eine Zwischenüberschrift.
- Absätze, die mit einem dieser fetten Labels beginnen, werden zu Kästen:
  **Hinweis für den Loremaster:**, **Optionale Erweiterung – …:**,
  **Erinnerung für den Loremaster – …:**, **Möglicher Abschluss:**,
  **Wenn sie trotzdem gehen:**, **Erfahrung:**
- Der Absatz **Gabe der Wacht (Hausregel …):** mit folgender Liste und folgendem Absatz
  wird zum gerahmten Hausregel-Kasten.
- Das Wort `Überspringbar` wird zur grauen Markierung.
- Karten im Text: `![Bildunterschrift](assets/maps/datei.jpg){.map}`
- Der Brief: `::: letter … :::` mit `\` am Zeilenende; er erscheint im Text und
  zusätzlich als Handout-Seite.
- Tabellen: normale Pipe-Tabellen; die Spaltenbreiten richten sich nach dem ersten
  Spaltenkopf (siehe `TABLES` im Filter).
- Regelbegriffe kursiv (`*Council*`), Tolkien-Namen und Regelbegriffe bleiben englisch.

## Version und Stand

Version und Datum in der Fußzeile kommen aus git:

- Auf einem getaggten Commit (`v2.1`) steht dort **Version 2.1**.
- Commits danach erscheinen als **Version 2.1+3 (abc1234)**.
- Uncommittete Änderungen werden als „lokal geändert“ markiert.
- „Stand“ ist das Datum des letzten Commits.

Neue Version veröffentlichen:

```sh
git tag v2.1
git push --tags
```

Ein Tag `v*` erzeugt zusätzlich ein GitHub-Release mit dem PDF.

## Lokal bauen

Voraussetzungen: TeX Live mit LuaLaTeX und `latexmk`, `pandoc`, Python 3.11+.

```sh
make            # oder: python3 tools/build.py
```

Das PDF liegt danach in `build/Die-Finsterwacht-TOR2e-DE.pdf`. Fehlt LuaLaTeX
(`luaotfload`), nimmt das Skript ersatzweise XeLaTeX. Fehlen die deutschen Trennmuster,
setzt es Flattersatz. Maßgeblich ist der CI-Build.

## Geschichte

Bis Version 1.51 entstand das Abenteuer in einer Claude-Docs-Datei mit einer
HTML-zu-PDF-Pipeline. Diese Datei bleibt als Archiv dieses Weges bestehen. Ab Version 2.0
ist dieses Repository die maßgebliche Quelle.
