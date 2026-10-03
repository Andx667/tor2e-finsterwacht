# make        -> build/Die-Finsterwacht-TOR2e-DE.pdf
# make maps   -> Karten neu zeichnen (braucht Playwright, siehe tools/maps.py)
# make clean
.PHONY: pdf maps clean
pdf:
	python3 tools/build.py
maps:
	python3 tools/maps.py
clean:
	rm -rf build
