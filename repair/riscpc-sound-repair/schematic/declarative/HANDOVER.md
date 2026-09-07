# Handover — declarative schematic auto-layout

Written 2026-09-08, end of the placement-engine session. Read `README.md`
first — it is the authoritative design doc and was kept current throughout.
This file is the shorter "where we are / what's next".

## Where it stands

Takes a flat `.cir` netlist (no positions) and auto-lays-out a schematic using
KiCad's own symbols, **rendering SVG** (there is no KiCad writer yet — see
below). As of this session the layout is crossing-free and compact:

- `circuit.cir` (the RISC PC headphone amp — the hero circuit): **81 wires,
  0 wire-to-wire crossings, 0 body crossings**, `--verify` reads the drawing
  back and diffs it against the netlist *identically*, sheet 159 × 198 mm.
- All 8 rungs of the test ladder verify at 0 crossings.

Check any time (from this directory):

```
nix develop --command bash tests/run.sh                          # the ladder
nix develop --command python3 render.py circuit.cir -o circuit.svg
nix develop --command python3 render.py circuit.cir --verify     # is it the circuit?
nix develop --command python3 render.py circuit.cir --check      # crosses a body?
nix develop --command python3 render.py circuit.cir --crossings  # wire crossings?
```

Render the SVG and open it directly to view — in-session image display hit a
limit late in this session, so trust `--verify`/`--check`/`--crossings` for the
numbers and open the SVG for the look.

## What this session changed (all pushed to `main`, `5d6a9c6..7733388`)

The whole session was the placement engine. In order:

| commit | what |
|--------|------|
| `dd25bb2` | upright rail legs; order lanes by their feeding head-pin; `--crossings` diagnostic (amp 5→2) |
| `a70c55a` | op-amp input mirror (2→0) |
| `4dfa422` | L-shaped legs off sideways (op-amp-input) pins |
| `ed3de08` | feedback bridge dropped into the gap it spans |
| `0c8076b` | orient a bridge to face the sides it reaches |
| `60499f1` | **one generic orientation rule** (`place.py::_orient`) replacing four special cases — faces any part to its neighbours by pin-to-target distance, incl. transistors; −28 lines |
| `fd3db0c` | supply filters linked into blocks (`layout._lay_supply` groups L+C by shared rail; `place.py` "island" wiring draws a rail shared by two pins of one lane as a *wire* with one tapped label, not a symbol per pin) |
| `8a472d8` | flow small blocks left-to-right across a width, wrapping |
| `76e6d07` | generalise the flow to **any** head-less block (not power-specific); fold the op-amp spare-supply units in |
| `7733388` | lift each op-amp to meet its feedback (one tier of gap, matching the driver's Rfb); delete the self-bridge clearance; `route.CROSS_COST` 10→40 (also cleared the t05/t07 residual crossings). 229→198 mm |

## The next task — the KiCad writer (known-wrong #1)

This is the point of the exercise and the only major piece not done. The SVG
is deliberately a *preview* of the KiCad output — same symbols, same
placement, same routing. The pipeline is built for it:

- `place.build(cir, lay)` returns a `geometry.Sheet` with `.placed`
  (`Placed`: ref, lib_id, unit, x, y, angle, mirror, value, pins), `.wires`
  (`Wire`: pts, net, traced), `.powers`, `.junctions`, `.labels`, `.title`.
- `symbols.py` already resolves every part to its real KiCad `lib_id`
  (`Device:R`, `Device:C_Polarized`, `Amplifier_Operational:TL074`,
  `Transistor_BJT:BC849`, …).

So the writer is mostly translation. Suggested shape: add `render_kicad.py`
mirroring `render_svg.py` (both just walk the same `Sheet`), and a
`--kicad` / `-o foo.kicad_sch` path in `render.py`. Emit `(symbol (lib_id …)
(at x y angle) (mirror …) (unit N) …)`, `(wire (pts …))`, `(junction …)`,
power symbols / `(global_label …)`, `(text …)` for the title.

Gotchas for the writer (see README "Gotchas" too):

- **y-axis:** KiCad symbol libraries define pins y-up; this tool's sheet is
  y-down. `geometry.pin_xy` already flips for positions.
- **mirror convention:** this tool uses `mirror="y"` = horizontal flip
  (negate x), `mirror="x"` = vertical flip (negate y). Map to KiCad's
  `(mirror x)`/`(mirror y)` carefully — KiCad's naming is the *opposite* axis,
  so expect to swap.
- **the DAC has no KiCad symbol.** TDA1545A is drawn from `symbols.generate_box`
  (a generated DIP box). A real `.kicad_sch` needs an actual symbol for it, or
  the generated one embedded in the file's `lib_symbols`.
- **multi-unit parts:** an op-amp's supply pins (4/11) are a separate unit
  placed as a parked "spare". KiCad expects all units of one symbol to share a
  reference — emit them as the same symbol, different `unit`, same `ref`.

Validating is easy: the SVG preview already proves placement/routing is right,
so the writer only has to get the S-expression format correct — open the
result in KiCad and fix syntax until it loads clean.

## Other remaining known-wrong (README has the full list)

- **No `hints:` block.** Layout is pure inference; a short hints section for
  the few cases inference gets wrong is the natural follow-up *after* KiCad.
- The spare op-amp supply unit draws as a bodyless symbol; a dashed "package"
  box would read better.
- **No rip-up-and-reroute.** Nets route shortest-first and never revisit.
  Nothing in the corpus triggers a failure and `CROSS_COST=40` keeps it clean,
  but a genuinely boxed-in net falls back to a plain elbow, which `--verify`
  names as a diagonal/overlap. Worth doing if a future circuit trips it.

## File map (see README for detail)

`netlist.py` parse + union-find · `layout.py` the graph rules → groups/lanes ·
`symbols.py` KiCad symbol lookup + geometry · `geometry.py` format-agnostic
placement types (the shared stage for the KiCad writer) · `place.py` placement
+ orientation + one-pass wiring · `route.py` A* on the occupancy grid ·
`verify.py` reads the drawing back and diffs it · `render_svg.py` the SVG ·
`render.py` CLI · `tests/` the ladder.
