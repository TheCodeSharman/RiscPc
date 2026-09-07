# A text netlist language that auto-lays-out a schematic

Write a circuit as a flat netlist with no positions in it; get a schematic
drawn with KiCad's own symbols. Currently renders SVG. The KiCad writer is
the next piece and is not written yet.

```bash
nix develop --command python3 render.py circuit.cir -o circuit.svg
nix develop --command python3 render.py circuit.cir --verify    # is it the circuit?
nix develop --command python3 render.py circuit.cir --check     # does it cross a body?
nix develop --command python3 render.py circuit.cir --crossings # do two nets cross?
nix develop --command python3 render.py circuit.cir --layout    # what was inferred
nix develop --command python3 render.py circuit.cir --netlist   # net by net
nix develop --command bash tests/run.sh                         # the whole ladder
```

Needs KiCad's symbol libraries installed (found automatically on macOS and
Linux; override with `KICAD_SYMBOL_DIR`).

## The language

Three constructs, line-oriented, `#` comments:

```
net GND                      declare a named net — a join point
part 47k:Rin_R               <type>:<ref>;  a trailing ? on the type means
                             never confirmed on the board (draws grey)
Rin_R@2 -> U1D@13 -> GND     connect; chains allowed
```

Pins are the **real numbers on the device**, so a `.cir` can be checked
straight against a datasheet. There are no pin aliases and no layout hints —
see [circuit.cir](circuit.cir) for the worked example, the RISC PC headphone
amplifier from [`../../README.md`](../../README.md).

Kinds are inferred from the reference designator by its *maximal leading run
of capitals*, so `Riv_R` is a resistor while `DAC` is not a diode.

## How the layout is worked out

Nothing declares what anything means. `layout.py` derives the electrical
reading from four graph rules:

1. **Globals** — a net that is a supply by name, or touches a lot of parts,
   is drawn as a local stub rather than routed. Puts rails at the edges.
2. **Stubs** — a part whose only neighbour is one other part hangs off it
   instead of taking a column.
3. **Spine** — the *heaviest* source-to-sink path is the backbone, laid left
   to right. Heaviest, not shortest: a feedback resistor is always a shorter
   way past an amplifier than through it, so shortest-path draws the circuit
   inside out. Scoring is `pins - 2` with ties broken on fewer hops.
4. **Bridges** — an off-spine part is anchored by *net*, not by neighbour.
   Each of its own nets is asked which spine parts it reaches; two nets
   reaching the spine make a bridge over the tightest pair of anchors, one
   net makes a leg hanging off its anchor.

   Counting neighbours instead got both cases wrong. `Rpull` touches both the
   transistor and the series resistor, so it looked like a bridge spanning
   the pair — but through *one* net, and it is a leg to the negative rail.
   `Riv` and `Cf` reach four parts between them, so they stretched across two
   spine positions — but both their nets meet at the op-amp, so they are
   feedback round one part and now sit directly over it. Neither needed to be
   told what it was.

Lanes come from cutting the source, so the two channels separate without
anyone saying they are channels.

More rules then run once positions exist and the pin geometry is known —
things `layout.py` cannot decide because it works on the graph alone. Some
settle *where* a part sits:

- **Lanes are ordered by the head pin that feeds them.** The DAC's pin 8 sits
  above pin 6 but feeds the *other* channel; drawn in lane order the two feeds
  swap over and cross at the DAC. Sorted by the height of their feeding pin,
  they run straight out. This is what put the three DAC-fan-out crossings to
  zero.
- **A leg drops from its pin.** A part hanging to a rail is placed below its
  host, at the *pin* it attaches to rather than the host's centre, so the wire
  runs straight down. Off a sideways-pointing pin (an op-amp input) it steps
  aside to the way the pin faces, turning down once — a clean L instead of an
  S back in. Two legs off one host stand side by side, never down one column,
  where they would route through each other's bodies.
- **A feedback bridge sits in the gap, not the stratosphere.** A self-bridge
  drawn over an op-amp's body must clear it; a bridge spanning *two* parts sits
  in the gap between them, over nothing but the wire on the row, so it drops a
  tier closer. The output-to-input feedback resistor round the driver stage
  was being parked 30 mm up with long riser legs; it now sits just above the
  row where it belongs.
- **A supply filter is drawn as a block, not scattered.** Parts whose every
  net is a rail never join the signal graph, so they used to be laid out one
  to a lane and wired only by label — an inductor and its reservoir cap came
  out as two segments both stamped `12V`, not a filter. `layout.py` now links
  them by the rail they share (ground excepted — it is the return, a leg to a
  symbol), the inductor a spine with the cap hung beneath it. And when a rail
  touches two pins of one lane, `place.py` draws that stretch as a real wire
  with a single tapped-out label — an *island* — instead of a symbol at each
  pin. Nowhere else in the corpus does a rail land twice in a lane, so only
  the filters are touched; the signal sheet is untouched. The filter blocks
  are then *flowed* — laid left to right across the width the signal chain
  already spans and wrapped onto a new shelf when the next would overflow —
  rather than stacked one to a tall column, so they take a strip.

And **one** rule settles *which way every part faces* — `place.py`'s `_orient`:

> Try each orientation the part's slot allows and keep the one where its pins
> sit closest to what they connect to; only turn when the gain clearly beats
> leaving it as placed. A two-terminal part flips end-for-end; a part of three
> pins or more (an active device) is not rotated but may be mirrored
> top-to-bottom.

Out of that single rule fall every case that used to be written out by hand: a
spine passive meets the parts either side; a leg's rail pin drops while its
live pin faces the host; a feedback resistor stops coming out back-to-front (a
loop over the top and an S beneath); an op-amp mirrors so its inputs meet the
feedback above and the bias below; a transistor keeps collector-up,
emitter-down because that is what its neighbours pull it to. Nothing is keyed
on what a part *is* — the geometry of what it reaches decides, which is why it
orients a device the corpus has never seen without a new rule. The margin (a
turn must beat the placed orientation by more than a passive's own pin span)
is what separates a genuinely back-to-front part from a coin-toss between two
electrically identical ways round; without it a marginal turn would trade a
tidy wire for a crossing. This is the *placement pattern* the four earlier
rules were each reaching for, in the Weave sense — a fix outside the layout
graph, keyed on geometry the graph cannot see — now stated once.

## Symbols

`symbols.py` resolves parts to KiCad's own libraries — `Device:R`,
`Device:C_Polarized`, `Transistor_BJT:BC849`, `Amplifier_Operational:TL074`.
That is the seam that makes the output editable in KiCad rather than merely
openable.

A part's **unit is derived from which pins it uses**, so `U1A` needs no
annotation to be section A: it uses 1/2/3 and TL074 unit 1 has pins 1/2/3.
Its supply pins 4/11 land on unit 5 and are emitted as a separate symbol, as
KiCad expects. Only the TDA1545A is generated (a DIP box), KiCad having no
symbol for it.

## Routing

`route.py` is an A* over a 2.54 mm grid. Symbol bodies and foreign pins are
obstacles; corners cost six steps so routes come out straight; each pin's
direction constrains how a wire leaves and arrives. The whole sheet routes in
about 0.2 s.

This replaced a scheme that picked a drop column from a ladder of offsets and
checked it against a list of pins. That was not enough — a column can miss
every pin and still cross a transistor, and when the ladder ran out the
fallback was far enough away that the wire crossed its own body getting
there. `render.py --check` counted ten such crossings; it now reports zero,
and exists so the next regression is caught rather than squinted at.

## Files

| | |
|---|---|
| `circuit.cir` | the headphone amplifier |
| `netlist.py` | parser; union-find over pins and named nets |
| `layout.py` | the four graph rules — globals, stubs, spine, bridges |
| `symbols.py` | KiCad symbol lookup, pin geometry, bounding boxes |
| `geometry.py` | format-agnostic placement types; shared with the KiCad writer |
| `place.py` | placement and wiring |
| `route.py` | the occupancy grid and the A* |
| `verify.py` | reads the drawing back and diffs it against the netlist |
| `tests/` | the ladder, smallest circuit first |
| `render_svg.py` | draws KiCad symbol artwork as SVG |
| `render.py` | CLI |

`geometry.py` is deliberately format-agnostic: it is the shared stage so that
routing is solved once and the KiCad writer is mostly translation.

## Known-wrong, in priority order

1. **No KiCad writer.** SVG only. This is the whole point of the exercise and
   it is the next thing to do.
2. **No hints section.** Layout is pure inference. The design intent is a
   short `hints:` block for the cases inference gets wrong — group these
   parts, order this lane, use this symbol. Two concrete cases are already
   visible and would be the tests:
   - `Cf_L` / `Cf_R` legs run a long way left to reach the op-amp's
     inverting input; a "keep these together" hint would place them better.
   - `U1A`'s supply unit (pins 4/11) floats below the row looking orphaned.
3. **The headphone amp draws with no crossings; two toy tests still cross.**
   `--crossings` counts wire-to-wire crossings (nicer at zero, not a
   correctness check). The lane-ordering, upright-leg and input-mirror rules
   took `circuit.cir` from 5 crossings to **0**, and the test ladder from 10
   to 2. The two that remain are `t05-inverting` and `t07-parallel-fb`: a
   single op-amp with feedback and *no forward load*, so the output has to
   wrap back over the top to the inverting input and crosses that node's wire.
   The same I/V stage inside `circuit.cir` does not cross — the forward path
   (Cac → Rin → driver) pulls the output out to the right and gives the loop
   room. Fixing the bare case means routing the wrap-around on the far side of
   the output, which needs the router to prefer that side; it is a genuinely
   tighter problem than the input mirror and is not worth over-fitting two
   synthetic circuits for. *Weave* runs a layered (Sugiyama) engine for the
   signal chain and handles feedback, divider legs, hanging shunts and supply
   corners as explicit patterns outside that graph; the input mirror above is
   the first of those, and more of the same is where the next gains are.
4. **The spare supply unit reads as two stalks.** A quad op-amp's pins 4 and
   11 are one pair shared by all four sections, so KiCad draws them as a
   fifth symbol with no body. They are parked together at the foot of the
   sheet, which is the right place, but with nothing drawn between them they
   look like two unrelated fragments. A dashed box would say "package".
5. **No rip-up and reroute.** Nets are routed shortest-first and never
   revisited, so a late net can be boxed in. When routing fails the wire is
   drawn as a plain L rather than dropped — wrong is a bug report, missing is
   a mystery — and `--verify` names it as a diagonal or an overlap. Nothing
   in the current corpus triggers it.
6. Whitespace is still generous — the sheet is taller than it needs to be,
   and lane pitch is driven by the worst case rather than by what each lane
   uses.

## Gotchas

- `elm.Ic`-style traps do not apply here, but KiCad's own format has several:
  - A symbol may `extends` another and carry **no artwork of its own** —
    TL074 is properties only and draws as LM2902. `Symbol.art_body` /
    `art_name` point at wherever the graphics actually live.
  - `(fill (type outline))` means *fill with the outline colour* — that is
    what makes a transistor arrowhead solid. Treating it as background fill
    drew the arrowheads in cream and they vanished.
  - Library pins are defined with **y up**; the sheet has y down. Every
    primitive is flipped as it is emitted.
  - A pin's `angle` points from its endpoint *into* the body, so outward is
    the opposite. Wires must approach along that axis.
- Rectangles use `(start …) (end …)`, not `(xy …)` like polylines.
