# A text netlist language that auto-lays-out a schematic

Write a circuit as a flat netlist with no positions in it; get a schematic
drawn with KiCad's own symbols. Currently renders SVG. The KiCad writer is
the next piece and is not written yet.

```bash
nix develop --command python3 render.py circuit.cir -o circuit.svg
nix develop --command python3 render.py circuit.cir --check     # routing sanity
nix develop --command python3 render.py circuit.cir --layout    # what was inferred
nix develop --command python3 render.py circuit.cir --netlist   # net by net
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
4. **Bridges** — an off-spine part touching the spine twice is drawn over the
   top. This is why the composite-amp feedback lands where feedback belongs
   without anything being told it is feedback.

Lanes come from cutting the source, so the two channels separate without
anyone saying they are channels.

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
| `route.py` | A* obstacle routing |
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
3. Wires may cross other **wires**. That is normal on a schematic and is what
   junction dots are for, but the junction dots are currently only emitted at
   route endpoints, not at genuine crossings of the same net.
4. `Rpull` is classified as a bridge spanning Q..Rs1 rather than a stub to
   the negative rail. It draws correctly but reads oddly.

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
