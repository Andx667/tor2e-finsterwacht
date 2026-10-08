# Die Finsterwacht

Ein Abenteuer für *The One Ring, 2nd Edition* · Eriador, Frühjahr TA 2965.

Dieses Repository enthält den Text des Abenteuers und die Pipeline, die daraus die
Druckfassung baut. Bei jedem Commit baut GitHub Actions die PDFs
(Reiter **Actions** → letzter Lauf → Artefakte `Die-Finsterwacht-TOR2e-DE-v….pdf` und
`Die-Finsterwacht-TOR2e-DE-Buch-v….pdf`, direkt als PDF, ohne ZIP).

## Aufbau

| Pfad | Inhalt |
| --- | --- |
| `src/finsterwacht.md` | Der Abenteuertext (Pandoc-Markdown) – hier wird geschrieben |
| `src/cards.toml` | Die Gegenstandskarten (Gegenstände, Texte, Reihenfolge) |
| `src/rules.toml` | Gegenstandsarten, Handwerkskunst und die Eigenschaften mit ihren Regeltexten (aus tor2e-items) |
| `assets/maps/` | Die gezeichneten Karten als JPG, Quellen als SVG in `svg/` |
| `latex/finsterwacht.sty` | Das Layout: Ränder, Notizspalte, Kästen, Tabellen, Karten, Handouts |
| `latex/finsterwacht.tex` | Gerüst der Blattfassung (einseitig gedacht, links gelocht) |
| `latex/finsterwacht-buch.tex` | Gerüst der Buchfassung (Buchblock zum Binden) |
| `latex/inhalt.tex` | Inhalt beider Fassungen (Titel, Anhänge, Karten, Handouts) |
| `filters/finsterwacht.lua` | Pandoc-Filter: Markdown-Elemente → Layout-Bausteine |
| `tools/build.py` | Baut das PDF |
| `tools/check.py` | Prüft die Gegenstände gegen `src/rules.toml` (aus tor2e-items); der Build ruft es auf |
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
- Das Wort `Optional` wird zur grauen Markierung.
- Karten im Text: `![Bildunterschrift](assets/maps/datei.jpg){.map}`
- Der Brief: `::: letter … :::` mit `\` am Zeilenende; er erscheint im Text und
  zusätzlich als Handout-Seite.
- Tabellen: normale Pipe-Tabellen; die Spaltenbreiten richten sich nach dem ersten
  Spaltenkopf (siehe `TABLES` im Filter).
- Regelbegriffe kursiv (`*Council*`), Tolkien-Namen und Regelbegriffe bleiben englisch.

## Version und Stand

Version und Datum in der Fußzeile kommen aus git; daneben steht der Autorenhinweis
(„by Andy Börner – MIT License“).

- In der Fußzeile steht die Nummer des letzten Tags: nach `v2.1.1` also **Version 2.1.1**,
  auch für Commits danach und für uncommittete Änderungen.
- „Stand“ ist das Datum des letzten Commits.
- Der Dateiname nennt die genaue Version: `Die-Finsterwacht-TOR2e-DE-v2.1.1.pdf` auf dem
  getaggten Commit, danach `…-v2.1.1+3-abc1234.pdf` (lokal geändert: Zusatz `-lokal`).

Neue Version veröffentlichen:

```sh
git tag v2.1
git push --tags
```

Ein Tag `v*` erzeugt zusätzlich ein GitHub-Release mit beiden PDFs.

## Gegenstandskarten

Die Gegenstände in `src/cards.toml` haben dasselbe Format wie in tor2e-items (Schatzkammer): Name, Art,
`base`, `craftsmanship`, Werte, `qualities` und `banes`. Werte und Regeltexte der Eigenschaften kommen aus
`src/rules.toml`; die Karte zeigt die Grundwerte, und was die Eigenschaften daran ändern, klein darunter. `src/rules.toml` und
`tools/check.py` sind unverändert aus tor2e-items übernommen und werden dort gepflegt.

Nur für die Finsterwacht gibt es zwei Zusätze in `src/cards.toml`: `order` (die Karten in Druckreihenfolge, ein
Eintrag je Exemplar) und `immediate` (die einfachen Rewards). Auf der Karte stehen die einfachen Rewards und
freie Effekte ohne Kennwort, alles andere – bessere Rewards, Banes und Blessings – unter **Gabe der Wacht**.
Die Fußzeile, die die Gabe erklärt, erscheint nur auf Karten, die eine haben. Alles, was kein
einfacher Reward ist, macht einen Gegenstand berühmt (*Famous Weapon*); mit nichts als einfachen Rewards ist er nur
gut gemacht und trägt keine solche Zeile. `source` setzt das Zeichen der Finsterwacht in die Ecke der Karte
(`assets/icons/`, ebenfalls aus tor2e-items).

`python3 tools/check.py` prüft die Gegenstände allein; der Build bricht bei einem Fehler ab.

## Blattfassung und Buchfassung

Der Build erzeugt zwei PDFs aus demselben Text:

- **Blattfassung** (`Die-Finsterwacht-TOR2e-DE-v….pdf`): lose Blätter für den Ordner,
  26 mm Rand links für die Lochung, Karten und Handouts im Querformat, Gegenstandskarten
  in Originalgröße zum Ausschneiden.
- **Buchfassung** (`Die-Finsterwacht-TOR2e-DE-Buch-v….pdf`): Buchblock zum Binden,
  doppelseitig zu drucken. Titelblatt mit leerer Rückseite; der Bundsteg (26 mm) liegt
  innen, Notizspalte, Kapitelname und Seitenzahl außen. Alle Seiten sind A4 hoch: Karten
  und Handouts stehen um 90° gedreht (Kopf links) und auf 93 % verkleinert. Die
  Gegenstandskarten bleiben in Originalgröße, stehen aber 2 × 3 statt 3 × 2 je Seite,
  damit der Bundsteg frei bleibt. Am Ende füllen Notizseiten (liniert wie die
  Notizspalte) auf eine durch 4 teilbare Seitenzahl auf.

Die Buchfassung enthält Einzelseiten in Lesereihenfolge. Für Klebe- oder Spiralbindung
einfach doppelseitig drucken; für gefalzte Bogen (Heft, Fadenbindung) im Druckdialog
„Broschüre“ wählen oder die Druckerei ausschießen lassen.

## Lokal bauen

Voraussetzungen: TeX Live mit LuaLaTeX und `latexmk`, `pandoc`, Python 3.11+.

```sh
make            # beide Fassungen; oder: python3 tools/build.py
make buch       # nur eine Fassung (blatt | buch)
```

Die PDFs liegen danach in `build/Die-Finsterwacht-TOR2e-DE.pdf` und
`build/Die-Finsterwacht-TOR2e-DE-Buch.pdf`, dazu je eine Kopie mit der Version im Namen
(`…-v2.1.pdf`). Fehlt LuaLaTeX
(`luaotfload`), nimmt das Skript ersatzweise XeLaTeX. Fehlen die deutschen Trennmuster,
setzt es Flattersatz. Maßgeblich ist der CI-Build.

## Geschichte

Bis Version 1.51 entstand das Abenteuer in einer Claude-Docs-Datei mit einer
HTML-zu-PDF-Pipeline. Diese Datei bleibt als Archiv dieses Weges bestehen. Ab Version 2.0
ist dieses Repository die maßgebliche Quelle.
