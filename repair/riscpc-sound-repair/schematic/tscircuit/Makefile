# tscircuit evaluation — see README.md.
# Run inside:  nix develop .#tscircuit --command make -C <this dir>

SRC := headphone-amp.circuit.tsx

all: headphone-amp.svg netlist.txt

headphone-amp.svg: $(SRC) node_modules
	npx tsci export $(SRC) -f schematic-svg -o $@

netlist.txt: $(SRC) node_modules
	npx tsci export $(SRC) -f readable-netlist -o $@

# Not committed (large, derived).
# `kicad`     -> a single KiCad 9 schematic (format version 20250114).
# `kicad-zip` -> a full project: .kicad_sch + .kicad_pcb + .kicad_pro + 3D models.
kicad: $(SRC) node_modules
	npx tsci export $(SRC) -f kicad_sch -o headphone-amp.kicad_sch

kicad-zip: $(SRC) node_modules
	npx tsci export $(SRC) -f kicad_zip -o headphone-amp-kicad.zip

# The committed project. NOTE this overwrites hand edits — kicad-project/ is
# tracked precisely so it can be edited in KiCad, so check `git status` first.
kicad-project: kicad-zip
	rm -rf kicad-project
	unzip -q -o headphone-amp-kicad.zip -d kicad-project

node_modules: package.json
	npm install
	@touch $@

clean:
	rm -f headphone-amp.svg netlist.txt headphone-amp.kicad_sch \
	      headphone-amp-kicad.zip

.PHONY: all kicad kicad-zip kicad-project clean
