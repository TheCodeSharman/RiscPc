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

## Why not KiCad's

KiCad has `DIN41612_C_3x16_Female_Vertical_THT`, but every DIN 41612 model it
ships is the same 94.90 × 10.50 × 14.10 full-size body — `2x16`, `3x16` and
`3x32` measure identically. SK4 is the half-size 16-position part at 55.39 mm
drawn, so KiCad's would render 40 mm too long.

There is no SIMM or DIMM socket anywhere in KiCad's 3D library, which is why
SK6 is still a prism.

## Datum

KiCad's convention is the board's top face at z = 0, +Z out of the board. A
vendor file need not follow it, and `_DATUM` in `vram_retainer.py` carries the
correction per file. `5535070-5.STEP` is datumed on the body's **top** face:
slicing it gives 8.8 mm² of pin section up to z = −11.50 and 139 mm² of standoff
foot from there, so the board plane is 11.5 below the file's origin.

Measured: 53.22 × 10.60 × 14.80, of which 11.5 stands above the board and 3.3 of
pin below. Against 55.39 × 11.39 drawn — the usual body-versus-silkscreen
difference.

## Licensing

Not yet cleared for redistribution. These are vendor CAD files obtained through
a free CAD-library service for design use; whether that extends to shipping them
in a public repo has not been checked. If it turns out it does not, delete the
file — `_package()` falls back to a keep-out prism and every printed dimension
is unchanged.
