# tscircuit evaluation — see README.md.
# Run inside:  nix develop .#tscircuit --command make -C <this dir>

SRC := headphone-amp.circuit.tsx

all: headphone-amp.svg netlist.txt

headphone-amp.svg: $(SRC) node_modules
	npx tsci export $(SRC) -f schematic-svg -o $@

netlist.txt: $(SRC) node_modules
	npx tsci export $(SRC) -f readable-netlist -o $@

# Not committed (large, derived). KiCad 9 .kicad_sch.
kicad: $(SRC) node_modules
	npx tsci export $(SRC) -f kicad_sch -o headphone-amp.kicad_sch

node_modules: package.json
	npm install
	@touch $@

clean:
	rm -f headphone-amp.svg netlist.txt headphone-amp.kicad_sch

.PHONY: all kicad clean
