# Render the reverse-engineered sound schematics.
# Run inside the repo dev shell:  nix develop --command make -C <this dir>
#
# The .svg is the committed artefact (text, diffs sensibly). The .png is a
# convenience render for pasting into notes and is gitignored.

PY      := python3
SOURCES := headphone_amp.py
SVGS    := $(SOURCES:%.py=%.svg)
PNGS    := $(SVGS:%.svg=%.png)

# headphone_amp.py writes headphone-amp.svg (hyphen, not underscore).
all: headphone-amp.svg

headphone-amp.svg: headphone_amp.py
	$(PY) $<

png: headphone-amp.png
headphone-amp.png: headphone-amp.svg
	rsvg-convert -w 2600 $< -o $@

clean:
	rm -f headphone-amp.svg headphone-amp.png

.PHONY: all png clean
