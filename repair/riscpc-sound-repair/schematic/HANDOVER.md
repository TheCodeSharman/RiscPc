# Handover — sound schematic work

State as of 2026-08-28. Branch **`feature/sound-schematic`**, 11 commits,
**nothing pushed**. Working tree clean apart from `tools/video-source/ModeServ.bas`,
which is the user's own edit and unrelated.

## The question this started from

Is there a text-based electronics tool that auto-lays-out a schematic, the way
mermaid does for architecture diagrams? Answer: not really, and the reasons
are interesting. Three approaches were built to find out.

## Where each one landed

| | what it is | verdict |
|---|---|---|
| [`headphone_amp.py`](headphone_amp.py) | schemdraw, layout by hand | **done.** The drawing for the repair notes |
| [`tscircuit/`](tscircuit/) | declarative TSX → KiCad | **evaluated, dead end.** See below |
| [`declarative/`](declarative/) | our own `.cir` language + auto-layout | **live work.** SVG done, KiCad writer next |

### schemdraw — finished

`headphone-amp.svg` is the deliverable for [`../README.md`](../README.md).
Both channels, grey for anything untraced. Publication quality, no netlist.
Not expected to change unless the probing map does.

### tscircuit — why it was abandoned

It genuinely auto-lays-out from a coordinate-free source, and exports a real
KiCad 9 project (verified: balanced s-expressions, `version 20250114`, 38
symbols, 120 wires, ERC runs). The plan was to hand-tidy it in KiCad.

That failed on one thing: **it fragments nets into islands joined by generated
labels** (`U1C_pin2` and friends). You cannot trace a net visually or drag it
into shape, which is exactly what hand-tidying requires. Also 158 of its
coordinates are off KiCad's 1.27 mm grid, so 28 genuinely-connected pins read
as unconnected, and its symbols are its own invented ones with orientation
baked into the name (`Device:boxresistor_right`), four variants per part.

Kept for reference, not being developed. `kicad-project/` is committed as
text and is tracked on purpose — see that README.

### declarative — the live work

Read [`declarative/README.md`](declarative/README.md) first; it is current
and complete. Summary: three-construct netlist language, no coordinates, no
declared semantics. Layout inferred from four graph rules, symbols from
KiCad's own libraries, A* routing around symbol bodies. Renders SVG in 0.2 s
with zero wires crossing bodies.

## The routing rebuild (most recent session)

The SVG was drawing `Rfb_R` with its two legs shorted together and `Q4` as
about seven wires on top of each other. Both turned out to be the same bug,
and the fix was to change the unit of work.

**What was wrong.** Routing was per *edge*: each connection got its own A*,
run from the pin, with no knowledge of any other net. So a net with four pins
drew four wires radiating from one pin, and two different nets could lie on
the same line — which is not a smudge, it is a short, and it is invisible.

**What was built.**

- `verify.py` + `render.py --verify` — the round-trip check. Throw the
  netlist away, read the geometry back the way KiCad reads a sheet, union
  whatever touches, diff the partition against the source. This is the idea
  from *Weave* (arXiv 2607.03835) and it is the single highest-value thing
  in the directory. On first run it found nine connectivity errors in
  `circuit.cir` — and a wire through both bodies in **two resistors in
  series**.
- `tests/` + `tests/run.sh` — a ladder of nine circuits, each one shape
  bigger than the last, smallest first, so a failure names the smallest
  circuit that shows it. This was the user's suggestion and it was the right
  call: t01 was broken, which is not something the full drawing would ever
  have told you.
- `route.py` rewritten around a **shared occupancy grid**, one net at a time,
  grown as a rectilinear tree. Crossings allowed (that is what a schematic
  is), collinear overlap and corners-on-foreign-nets forbidden.
- `place.py` split into placement then one wiring pass. It used to emit wires
  from six different places, each drawing its own straight line, none aware
  of the others. There is now exactly one function that emits a wire.

All nine rungs pass, `--check` reports zero body crossings, 0.2 s.

**What is still wrong is now placement, not routing** — the router draws what
it is given without lying about the connectivity. See "Known-wrong" in the
declarative README.

## Next steps, in order

1. **The KiCad writer.** This is the point of the whole detour and the reason
   `geometry.py` was kept format-agnostic — placement and routing are already
   solved, so it should be mostly translation into `.kicad_sch` s-expressions.
   Emit real `lib_id`s and copy each symbol's definition into `lib_symbols`
   the way KiCad does. Everything is already on a 1.27 mm grid, which is what
   tscircuit got wrong.
2. **The `hints:` section.** The user's design: layout stays inferred by
   default, hints only override. Two concrete cases already visible to test
   against are listed in the declarative README under "Known-wrong".
3. **Placement, informed by the literature.** *Weave* is the closest prior
   art and it is worth reading: it runs a layered (Sugiyama) engine — elkjs —
   for the signal chain, and handles feedback, divider legs, hanging shunts
   and supply corners as explicit placement *patterns* kept **outside** that
   graph, because forcing them in degrades the main chain. That is what the
   four graph rules here are groping towards, and the named prior systems in
   its related work (Swinkels & Hafer 1990; Jehng 1991; Arsintescu 1996;
   Frezza & Levitan's SPAR 1993) are the classical heuristics.
4. **Push the branch and open the self-review PR.** CLAUDE.md asks for this
   for code subprojects and it has not been done.

## Conclusions worth not re-deriving

These cost real time to establish.

- **Almost all schematic semantics are recoverable from the graph.** An early
  design had the author declare "this block is a transimpedance stage", "this
  resistor is feedback", "this net is a rail". That was wrong. Rank the parts
  and feedback *is* an edge pointing backwards; a rail *is* a net touching
  many parts. The user pushed back on this twice and was right both times —
  do not reintroduce a semantic ontology.
- **The spine must be the heaviest path, not the shortest.** A feedback
  resistor is always a shorter way past an amplifier than through it, so
  shortest-path leaves the active devices off the backbone and draws the
  circuit inside out. Maximum pin count overcorrects into a snake through
  every part. Scoring `pins - 2`, ties broken on fewer hops, is what works.
- **Verify the drawing, not the intent.** Every check that reasoned about
  what the router *meant* to do passed while the drawing was shorted. The
  only check that found it read the geometry back and rebuilt the netlist
  from it. Build that first next time.
- **Route nets, not wires.** A net is a tree. Routing its edges
  independently is what produced both the stacked wires and the shorts, and
  no amount of tuning the per-edge A* would have fixed either.
- **Start at two parts.** The full drawing is too big to tell you anything.
  Two resistors in series was broken in four separate ways, and every one of
  them was also wrong in the big circuit.
- **"No overlaps by construction" is not enough.** It held for sideways pins
  and failed silently for downward-pointing ones — a feedback leg was landing
  exactly on a transistor's base, which is a short, not a smudge. Routing
  needs real obstacle avoidance. `render.py --check` exists to catch this.
- **Checking pins is not the same as checking bodies.** A column can miss
  every pin and still run through a transistor.
- **Once a schematic is viable in KiCad it can be hand-tidied**, so
  auto-layout only has to be a good starting point, not a finished drawing.
  This is why the bar moved from "beautiful" to "editable" mid-way.

## Environment

- `nix develop` — python3 + schemdraw + librsvg + poppler. Used by
  `headphone_amp.py` and all of `declarative/`.
- `nix develop .#tscircuit` — node + bun + librsvg, kept separate so the
  everyday shell stays lean. `@tscircuit/cli` needs an npm `overrides`
  pinning `circuit-json` to `0.0.479` or it dies on startup.
- KiCad 10 is installed locally, with its symbol libraries at
  `/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols`.
  `kicad-cli` is on `PATH`; the Schematic Editor needs its full bundle path,
  `open -a "/Applications/KiCad/KiCad.app/Contents/Applications/eeschema.app"`.

## Also done this session, unrelated

- `.gitignore` gaps fixed — `**/__pycache__/` (the `/*` form left the
  directory untracked), `**/.history/`, `**/node_modules/` at root.
- `ds-view/POSTexample.dsl` renamed to `postexample-335ms.dsl`. It collided
  case-insensitively with `postexample.dsl`; that collision was the phantom
  "modified" file that had been sitting in the working tree for ages.
