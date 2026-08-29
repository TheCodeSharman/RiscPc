# Vendor 3D models

STEP for the board neighbours KiCad's own library does not carry. Everything
here is imported by `_package()` in `vram_retainer.py`, which searches this
directory before the KiCad tree.

**These are display geometry.** The clearance sums that matter are driven by the
plan outlines measured off the TRM drawings, not by these solids — see the
`_NEIGHBOURS` table. A vendor model is a *nominal* part, not this board's part.

| file | ref | what | source |
|---|---|---|---|
| `5535070-5.STEP` | SK4 | TE Connectivity DIN 41612 type C, 3 × 16 = 48 way, female straight | SnapEDA (now SnapMagic Search) |
| `5822030-3.stp` | SK6 | TE Connectivity SIMM socket, 72 way, 1.27 mm pitch, vertical, through-hole | TraceParts |

`5822030-3.txt` is TraceParts' own attribute dump, kept as provenance — it is
what identifies the part as "72 ME .050 VERT M/L PB-FREE" and confirms the
vertical variant rather than an angled one.

## Why not KiCad's

KiCad has `DIN41612_C_3x16_Female_Vertical_THT`, but every DIN 41612 model it
ships is the same 94.90 × 10.50 × 14.10 full-size body — `2x16`, `3x16` and
`3x32` measure identically. SK4 is the half-size 16-position part at 55.39 mm
drawn, so KiCad's would render 40 mm too long.

For SK6 there is no choice at all: KiCad's 3D library has no SIMM or DIMM
socket of any kind.

## Datum and orientation

KiCad's convention is the board's top face at z = 0, +Z out of the board. A
vendor file need not follow it, and neither of these does. `_DATUM` in
`vram_retainer.py` carries the correction per file, applied at import so
everything downstream can go on assuming KiCad's convention.

Both corrections were measured by **slicing the solid**, not read off a
datasheet — neither file states its datum, and the cross-sectional area gives
the board plane away, jumping from pin section to body section as it crosses it.

| file | correction | how it was found |
|---|---|---|
| `5535070-5.STEP` | board plane 11.50 below the origin | 8.8 mm² of pin up to z = −11.50, then 139 mm² of standoff foot |
| `5822030-3.stp` | stand up 90° about X, then board plane 4.80 below | lies on its side: 18 mm² of pin up to y = −4.80, then 851 mm² of body |

## How they measure against the drawing

| ref | model | drawn (drg 0197,000/A) | above board |
|---|---|---|---|
| SK4 | 53.22 × 10.60 | 55.39 × 11.39 | 11.50, pins 3.30 below |
| SK6 | 115.57 × 8.51 | 115.24 × 9.77 | 14.64, pins 4.41 below |

Both are a little under the drawn outline, which is the ordinary
body-versus-silkscreen difference and is why the fit report lists them in its
"package model smaller than the outline drawn" warning. SK6's length agrees to
0.33 mm, which is a good independent check on the drawing having been read 1:1.

## Licensing

Not yet cleared for redistribution. These are vendor CAD files obtained through
free CAD-library services for design use; whether that extends to shipping them
in a public repo has not been checked. If it turns out it does not, delete them
— `_package()` falls back to a keep-out prism and every printed dimension is
unchanged.
