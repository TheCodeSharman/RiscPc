# tscircuit evaluation

The same headphone amplifier as [`../headphone_amp.py`](../headphone_amp.py),
written in [tscircuit](https://tscircuit.com) instead of schemdraw — to answer
one question: **can you describe a circuit declaratively and have software
apply schematic conventions for you?**

Short answer: **yes, and it works.** Every component here is placed and every
net routed by tscircuit, from a file that contains no coordinates at all. But
the conventions it applies are weaker than a human's, and the result is
noticeably less readable than the hand-conventioned schemdraw drawing.

## Running

```bash
nix develop .#tscircuit --command make -C repair/riscpc-sound-repair/schematic/tscircuit
nix develop .#tscircuit --command make -C repair/riscpc-sound-repair/schematic/tscircuit kicad
```

`node`, `bun` (the CLI shells out to it) and `rsvg-convert` come from the
`tscircuit` devShell in `flake.nix` — kept separate from `default` so the
everyday shell stays lean. Deps come from npm, not nixpkgs.

Committed: `headphone-amp.svg`, `netlist.txt`, `package-lock.json`, and
`kicad-project/` — the extracted KiCad project.
Gitignored: `node_modules/`, the `.zip`, KiCad's `~*.lck` locks, and
`kicad-project/3dmodels/` (2.6 MB of STEP, regenerable).

**`kicad-project/` is tracked on purpose.** It starts out derived, but the
whole point of exporting to KiCad is to hand-tidy the layout there — and the
moment it is edited it stops being derived and becomes source. So it is
committed as text (`.kicad_sch`, `.kicad_pcb` and `.kicad_pro` are all
s-expressions or JSON, and diff readably), and `make kicad-project`
**overwrites it**. Check `git status` before re-running that target.

## What it got right

- **It genuinely auto-lays-out.** No `schX`/`schY` anywhere. It placed 27
  components and routed every net unaided, and the output reads as a
  schematic — op-amp triangles pointing the right way, resistors on their
  correct axis, the two channels ending up as visibly separate clusters.
- **It is a netlist, not a picture.** `netlist.txt` is a real net-by-net
  listing that can be checked against the probing notes — something schemdraw
  fundamentally cannot give, because schemdraw only draws lines.
- **KiCad export works, and it is a real file.** Verified rather than
  assumed: balanced s-expressions, format `version 20250114` (KiCad 9),
  38 symbol instances, 120 wire segments, 12 junctions, 14 global labels,
  every reference present. `make kicad-zip` gives a whole project —
  `.kicad_sch` + `.kicad_pcb` + `.kicad_pro` + STEP models.

  Caveat: symbols are tscircuit's own embedded `lib_symbols`
  (`Device:boxresistor_right`, `Custom:rail_up`), not KiCad's standard
  `Device:R`. Because `.kicad_sch` embeds its symbol definitions, it opens
  and renders standalone — but editing it against KiCad's own libraries, or
  taking it to a board with real footprints, means remapping symbols first.
- **Same mirror win as schemdraw.** `Channel` is written once and instantiated
  twice.

## What it got wrong

- **Signal flow is not left→right.** The DAC landed in the middle-right,
  feeding I/V converters to its upper-left, with `IOL` lassoed all the way
  around the left edge of the sheet.
- **Rails are not at the top, grounds not at the bottom.** `V_PLUS12` /
  `V_MINUS12` became floating net labels wherever the router happened to
  finish, and the L13/L14 supply feed ended up as a disconnected island in the
  bottom-right corner with its labels overlapping.
- **It gives up and drops a label.** Where routing a wire was awkward it emits
  a net-label stub instead — `U1D_pin2`, `U1A_pin3`, `R_s1_RIGHT_pin2` — drawn
  rotated 90°. These are the ugliest thing on the sheet and they actively hide
  the topology: the composite-amp feedback path, the single most important
  feature of this circuit, is broken up by them.
- **Op-amp supply pins are not on the symbol**, so the ±12 V feed cannot be
  drawn where it belongs.
- **`schAutoLayoutEnabled` and `schTraceAutoLabelEnabled` do nothing.** Both
  exist in `@tscircuit/props`; setting them on `<board>` produced a
  byte-identical SVG. Not wired up in this version.

## Version pinning gotcha

`@tscircuit/cli@0.1.2021` crashes on startup — `SyntaxError: Export named
'schematic_sheet_size' not found in module circuit-json` — because npm resolves
`circuit-json` to `0.0.464` while the CLI needs a newer one. Fixed with an
npm `overrides` block in `package.json` pinning `circuit-json` to `0.0.479`.
If the CLI is upgraded, try removing that override first.

## Verdict

The two tools are not competing; they answer different questions.

| | schemdraw | tscircuit |
|---|---|---|
| Layout | you apply the conventions | software applies them |
| Output quality | publication-ready | readable, not presentable |
| Netlist / ERC | none | yes |
| KiCad export | none | yes (non-idiomatic symbols) |
| Effort for this circuit | ~an hour of layout tuning | none |

For **documenting this repair**, schemdraw wins — the drawing is the
deliverable and it has to be clear. `../headphone-amp.svg` stays the one that
goes in the notes.

For **verifying the trace**, tscircuit wins, and this is not a small thing:
`netlist.txt` is machine-checkable against the probing notes in a way a drawing
never is. If op-amp #2 is ever mapped, or a repair board is ever built, this is
the file to grow.

Keeping both. They are the same circuit described twice, which is also a
cross-check in itself.
