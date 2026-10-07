# make        -> build/Die-Finsterwacht-TOR2e-DE.pdf und …-Buch.pdf
# make blatt  -> nur die Blattfassung (gelocht)
# make buch   -> nur die Buchfassung (zum Binden)
# make check  -> nur die Gegenstände gegen src/rules.toml prüfen
# make maps   -> Karten neu zeichnen (braucht Playwright, siehe tools/maps.py)
# make clean
.PHONY: pdf blatt buch check maps clean
pdf:
	python3 tools/build.py
blatt buch:
	python3 tools/build.py $@
check:
	python3 tools/check.py
maps:
	python3 tools/maps.py
clean:
	rm -rf build
