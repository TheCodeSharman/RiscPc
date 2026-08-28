# VRAM retainer — handover

State as of 2026-08-28. The model is [`vram_retainer.py`](vram_retainer.py); its
docstring carries the design reasoning, this file carries the project context
that isn't in the code.

## The problem

The RISC PC's VRAM module sat in socket **SK9** (136-way DIMM) held by
edge-connector friction plus one cream plastic latch clipped into the black
tower at the left-hand end. That latch cracked, and has since been **removed
altogether** — so the socket now has no retention of its own and this bracket is
the whole mechanism, not an assist.

Measurement made that worse than it sounded: the socket body stands 5.2 mm off
the board and the card's bottom edge 3 mm, so **only 2.2 mm of the card is
engaged**. And two socket contacts were previously snapped off and repaired by
bending the remaining halves outward to meet the card
(`tools/risc-pc-diag/README.md`), so seating pressure is doing the work a full
contact spring would otherwise do. The recorded symptom is errors appearing only
while the board is flexed.

## The part

One yoke, two anchors, two screws.

- A **bar** capping the card's top edge — this is what resists lift, and it is
  the load-bearing element.
- Two **jaws** embracing the card's faces in the component-free zones at its
  ends, screwed down to the anchors.
- Two **anchors**, a U in plan, **press-fitted** onto the socket's black end
  towers. No adhesive required.

## Measured facts

All calipers unless noted. Heights are above the **motherboard**, which is the
datum the design uses — the socket's own height cancels out of everything that
matters.

| | value | source |
|---|---|---|
| Card overall | 102.87 × 28.0 × 1.27 mm | TRM Fig 2.18, p.2-27 |
| Card components | 6.5 max side A, 4.00 max side B | TRM Fig 2.18 |
| Card mounting holes | ø3.18, 3.38 in from each end, 6.35 up | TRM Fig 2.18 |
| Card top edge, seated | **31.0 mm** | calipers |
| Tower top | **18.90 mm** | calipers |
| Socket body top | **5.2 mm** | calipers |
| Tower plan | **7.7 × 7.7 mm** (square) | calipers |
| Socket overall, tower outer to tower outer | **110.36 mm** | calipers |
| Clear card at each end (no components) | ~8 mm side A, ~7 mm side B | photo vs TRM length |
| Clear card above the top components | **~0** — TSOPs flush, electrolytics 0.8 below | photo vs TRM length |
| Clear board beyond left tower | 3.3 mm, then C73 | photo, ~19 px/mm |
| Clear board beyond right tower | ~0 | photo |

Derived: card sits **2.2 mm** into the socket; jaw grips **6.6 mm** of card face;
assembly stands **36.0 mm** above the board against 31.0 for the bare card.

## Still outstanding

**One measurement blocks nothing else.** The screw boss needs **6.29 mm of clear
board past the socket body** on the flank it sits on. That was scaled off a
photograph at roughly 5 mm, so it is unverified and may not fit.

Measure: clear board beside a **tower** (not mid-span), each flank, from the
socket body's edge outward. If it is under 6.3 mm, in increasing order of what
they cost:

1. `INSERT_D`/`SCREW_*` to M2 — saves ~0.8 mm, still far stronger than needed.
2. `WALL` 2.0 → 1.5 on the jaw — saves 0.5 mm.
3. Flip `CAP_SIDE` to put the boss on the other flank.

The anchor's U itself only needs 1.70 mm per flank and is fine either way.

`SOCKET_L` is measured, but the screw holes stay slotted ±1 mm because the
anchors are pressed onto real towers by hand, not placed at modelled
coordinates.

## Dead ends — do not re-tread

Each of these was drawn and then killed by a measurement. The reasons are the
useful part.

- **Plate down the card's front face, hooking over the top edge.** Killed by
  side clearance: the socket has ~1 mm of clear board one flank and ~2 the
  other, and the plate wanted 14.
- **Beam on legs dropping outboard of the socket ends.** Killed by end
  clearance: C73 is 3.3 mm beyond the left tower and there is nothing at all
  beyond the right, where the legs needed ~13.
- **Full-length channel gripping both card faces.** Killed by the card itself:
  the TSOPs are flush with its top edge, so clearing a 6.5 mm component stack
  one side and 4.0 the other needs ~16 mm across a 6.5 mm socket. The hug moved
  to the component-free zones at the card's ends.
- **A peg through the card's ø3.18 mounting holes.** They are occluded by the
  tower plastic — the towers stand 3.75 mm proud of the card's ends and enclose
  them.
- **Screws into the socket.** Nowhere to put one; hence bonded, then pressed.
- **Bonded L anchors.** Superseded by the press fit, which came out *narrower*
  (1.70 mm per flank against 2.20 on one) because the epoxy slop it dropped was
  wider than the interference it gained.

## Printing

PETG. `FIT = 0.2` at the top of the model is the single printer-tolerance knob.

| file | qty | notes |
|---|---|---|
| `vram_coupon.stl` | 1 | **print first** — 15.6 mm, one end of the yoke |
| `vram_yoke.stl` | 1 | 113.2 × 12.5 × 11.6, 4.3 cm³ |
| `vram_anchor_left.stl` | 1 | 0.9 cm³ |
| `vram_anchor_right.stl` | 1 | 0.9 cm³ |

The anchors are a **chiral pair** — both hands are exported, do not mirror in
the slicer and do not print two of one.

Orientation: yoke with the bar's top face on the bed, so the card slot opens
upward and the jaws stay self-supporting. Anchors standing on the bonded end
face, which puts the insert bore vertical for setting with an iron.

The coupon carries everything whose fit is uncertain — card slot at 0.3 per
face, M2.5 hole, foot — and none of the socket geometry. Print it, push it onto
the card's end, try a screw. Then adjust `FIT` if needed.

`PRESS = 0.10` is the interference per flank. Print **one** anchor and try it on
a tower before committing to the pair: raise toward 0.05 if it will not start,
drop toward 0.15 if it slides on freely. The towers are 30-year-old plastic and
worth one deliberate test.

## Hardware

- 2 × M2.5 heat-set inserts, 3.6 mm bore × 4.0 mm — check against what's on hand
  and adjust `INSERT_D` / `INSERT_L`.
- 2 × M2.5 pan-head screws, ~8 mm.
- No adhesive needed. PETG creeps, so the interference will relax over years; if
  it ever loosens, epoxy in the same joint recovers it.

## Assembly order

1. Press an anchor onto each tower (lead-in chamfer at the mouth guides it).
2. Set an insert into each anchor from above.
3. Fit the VRAM card.
4. Lower the yoke on — jaws straddle the card's ends, bar lands on its top edge.
5. Screw down. The 0.4 mm `SEAT_GAP` under each foot means the screws close the
   gap and **preload the bar onto the card**, rather than the foot bottoming out
   and holding the bar off it.

## Running the toolchain

```sh
nix develop .#cad          # from the repo root — provides uv
cd mechanical && uv sync
./.venv/bin/python vram_retainer.py    # prints the fit report, writes STL + STEP
```

build123d is not in nixpkgs (nor is `cadquery-ocp` under it, which ships only as
wheels), so this is a uv venv pinned by `uv.lock`, not a nix closure. See
[README.md](README.md).

For rendered views: OCP CAD Viewer is pinned in `nix-config`
(`bernhard-42.ocp-cad-viewer` 4.0.1, matched to the `ocp-vscode` pin here).
Cmd-Shift-P → *OCP CAD Viewer: Open viewer*, then run the file.

STEP exports carry a pinned timestamp, so regenerating an unchanged model leaves
`git status` clean.

## Repo state

All of this is merged to `main` and pushed. `feature/vram-retainer`,
`feature/sound-schematic` and `feature/modeserv-mode-string` are merged and can
be deleted.

Gotcha: `ds-view/postexample.dsl` disappears on checkout of branches predating
`03727bb`, because macOS cannot distinguish it from the old `POSTexample.dsl`.
`git checkout -- ds-view/postexample.dsl` restores it.
