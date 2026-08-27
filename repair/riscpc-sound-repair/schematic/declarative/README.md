# PARKED — a text netlist language with generic auto-layout

**Not in use. Superseded by [`../tscircuit/`](../tscircuit/).** Kept because
the layout engine works and the reasoning is worth not re-deriving.

## What it is

A three-construct netlist language and a layout engine that draws it with no
positioning information whatsoever.

```
net GND
part 47k:Rin_R
Rin_R@2 -> U1D@13 -> GND
```

Pins are the real numbers on the device, so a `.cir` can be checked straight
against a datasheet. A trailing `?` on a part type (`part Cf?:Cf_R`) marks
something never confirmed on the board.

- [`circuit.cir`](circuit.cir) — the headphone amplifier
- [`netlist.py`](netlist.py) — parser; union-find over pins and named nets
- [`layout.py`](layout.py) — the layout engine
- Renderer — **never written.** This produces no picture.

## Why it exists

The question was whether a declarative circuit description can be laid out by
software applying schematic conventions, instead of by hand. The first attempt
answered it the wrong way: a vocabulary where you *declared* that a block was
a transimpedance stage, that a resistor was feedback, that a net was a rail.

That was wrong, and the correction is the useful part of this directory:
**almost all of it is recoverable from the graph.** `layout.py` derives it
from four rules and no semantics at all —

1. **Globals** — a net that is a supply by name, or touches a lot of parts, is
   drawn as a local stub rather than routed. This is what puts rails at edges.
2. **Stubs** — a part whose only neighbour is one other part hangs off it
   instead of taking a column. Keeps connectors out of the signal chain.
3. **Spine** — the best source-to-sink path is the backbone, laid left to
   right; everything else hangs off it.
4. **Bridges** — an off-spine part touching the spine twice is drawn over the
   top. A part spanning backwards is feedback; nothing needs to be told that.

Verified working on `circuit.cir`: it finds the two channels as separate lanes
by cutting the source (nothing declares them channels), puts `U1A`/`U1D`/`Q4`
on the spine, and classifies `Riv`/`Cf`/`Rfb` as bridges and `Rbias`/`Rpull`
as stubs to ground and the negative rail. That is the correct electrical
reading, from connectivity alone.

## The one genuinely hard bit

Choosing the spine. Two obvious objectives both fail:

- **Shortest path** skips the amplifiers — a feedback resistor is always a
  shorter way past an op-amp than going through it, so the circuit comes out
  inside-out with `U1A` and `Q4` drawn as attachments.
- **Maximum weight by pin count** overcorrects into a snake through every
  part in the lane.

What works: score each part `pins - 2`, so ordinary two-terminal passives are
worth nothing and ties break on fewer hops. The backbone then runs *through*
the active devices while a feedback resistor round one of them stays a detour
— both score the same, and the direct route is shorter. Longest simple path is
NP-hard, but a lane is a dozen parts, so it is searched exhaustively with a
greedy fallback above `SEARCH_LIMIT`.

## Why it was parked

It cannot get to KiCad, and that turned out to be the whole point: once a
schematic is viable in KiCad it can be hand-tidied, so the auto-layout only
has to be a valid starting point rather than a finished drawing.
`../tscircuit/` clears that bar today and exports `.kicad_sch`, `.kicad_pcb`
and a full project. Finishing a renderer here would have produced a nicer
picture and no route into an editor.

Worth reviving only if the `.cir` syntax is wanted for its own sake, or to fix
tscircuit's specific layout failures — see [`../tscircuit/README.md`](../tscircuit/README.md).

```bash
nix develop --command python3 -c "
import netlist, layout
c = netlist.load('circuit.cir'); lay = layout.build(c)
for g in lay.groups:
    for ln in g.lanes: print(' -> '.join(ln.spine))"
```
