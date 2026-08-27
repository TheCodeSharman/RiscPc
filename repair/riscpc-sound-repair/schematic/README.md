# Sound schematics (generated)

The RISC PC main PCB **1208,000** has no public schematic — the audio section
was reverse-engineered by probing. [`../README.md`](../README.md) is the
authority for what connects to what; the scripts here are a **drawing** of that
map, generated with [schemdraw](https://schemdraw.readthedocs.io).

| Script | Output | Covers |
|---|---|---|
| `headphone_amp.py` | `headphone-amp.svg` | TDA1545A → TL074 #1 (I/V + driver) → Q1/Q4 → SK12, both channels, ±12 V feed |

[`tscircuit/`](tscircuit/) holds the same circuit written declaratively, as an
evaluation of whether software can apply the schematic conventions for you.
Short answer: it can, but less well than a person — see its README. The
schemdraw drawing above remains the one for the notes.

op-amp #2 and the LM386 speaker path are **not** drawn — they are deliberately
unmapped, see "Remaining" in [`../README.md`](../README.md).

## Rendering

```bash
nix develop --command make -C repair/riscpc-sound-repair/schematic       # .svg
nix develop --command make -C repair/riscpc-sound-repair/schematic png   # + .png
```

`schemdraw` and `rsvg-convert` come from the repo dev shell (`flake.nix`).
The `.svg` is committed; `.png` is gitignored — regenerate it with `make png`.

## Why a script and not a drawn schematic

Two reasons, both specific to this circuit:

1. **The channels are mirrors.** Left and right are the same circuit on
   different TL074 sections and different pins. They are described once, as
   data (`CHANNELS`), and drawn twice. A correction to the map is made in one
   place — which matters, because the map is still changing.
2. **It diffs.** The schematic lives next to the notes and travels with them in
   git, so a correction to the trace shows up as a reviewable change rather
   than a silently-replaced binary.

This is a *documentation* tool: no netlist, no ERC, no KiCad export. It will
happily draw a wrong circuit. The probing notes remain the source of truth.

## Conventions the script applies

Schemdraw does not auto-layout — it does *relative* placement, so the drawing
conventions are applied by hand and are worth stating:

- Signal flows left → right; supply rails point up (+) and down (−).
- Feedback returns right-to-left over the top of its amplifier.
- Op-amp `in1` (top) is inverting, `in2` (bottom) non-inverting.
- **Grey = not traced or unconfirmed.** Nothing is invented to fill a gap;
  see the `UNCERTAIN` block at the foot of `headphone_amp.py`.

## Gotchas found while writing this

Schemdraw quirks that cost time and will bite again:

- `elm.Ic` takes `size=(w, h)`. Passing `w=`/`h=` is silently swallowed by
  `**kwargs` — no error, no effect.
- `elm.Ic` lays out each side's pins **bottom-up**, so a side's list must be
  given in reverse reading order.
- Elements inherit the *current drawing direction*. An `elm.Ic` placed after a
  leftward line comes out mirrored; `.right()` pins it down.
- `.up().toy(v)` forces the direction, so it silently draws the wrong way when
  `v` is below the start — which shorted IOL onto IOR's riser. Use
  `.to((x, y))`, which picks its own direction.
- Labels on right-to-left elements rotate with the element. Draw the element
  left-to-right and set its endpoint with `.tox()` instead.
