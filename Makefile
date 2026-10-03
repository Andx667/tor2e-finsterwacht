# make        -> build/Die-Finsterwacht-TOR2e-DE.pdf und …-Buch.pdf
# make blatt  -> nur die Blattfassung (gelocht)
# make buch   -> nur die Buchfassung (zum Binden)
# make maps   -> Karten neu zeichnen (braucht Playwright, siehe tools/maps.py)
# make clean
.PHONY: pdf blatt buch maps clean
pdf:
	python3 tools/build.py
blatt buch:
	python3 tools/build.py $@
maps:
	python3 tools/maps.py
clean:
	rm -rf build
