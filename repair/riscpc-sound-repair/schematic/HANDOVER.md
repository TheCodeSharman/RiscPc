# Handover — sound schematic work

State as of 2026-08-28. Branch **`feature/sound-schematic`**, 10 commits,
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
3. **Push the branch and open the self-review PR.** CLAUDE.md asks for this
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
