# VRAM retainer — handover

State as of 2026-08-28 (revised after the first anchor print). The model is [`vram_retainer.py`](vram_retainer.py); its
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
- Two **anchors**, a broken ring in plan, **press-fitted** onto the socket's
  black end towers. Both flanks, the outer end wall, and — above the socket
  body only — two tabs across the inner face, parted by a slot the card passes
  through. No adhesive required, though see the note below.

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

**One measurement blocks nothing else.** The screw boss needs **5.84 mm of clear
board past the socket body** on the flank it sits on. That was scaled off a
photograph at roughly 5 mm, so it is unverified and may not fit.

Measure: clear board beside a **tower** (not mid-span), each flank, from the
socket body's edge outward. If it is under 5.9 mm, in increasing order of what
they cost:

1. ~~`INSERT_D`/`SCREW_*` to M2~~ — **spent**. The move to M2 bought 0.45 mm
   (6.29 → 5.84) and is already in the model.
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
| `vram_yoke.stl` | 1 | 113.2 × 12.0 × 11.6, 4.3 cm³ |
| `vram_anchor_left.stl` | 1 | 1.1 cm³, 22.3 tall |
| `vram_anchor_right.stl` | 1 | 1.1 cm³, 22.3 tall |

The anchors are a **chiral pair** — both hands are exported, do not mirror in
the slicer and do not print two of one.

Orientation: yoke with the bar's top face on the bed, so the card slot opens
upward and the jaws stay self-supporting. Anchors **roof down** — the face the
yoke's feet land on goes against the bed, insert bore opening downward into it.

That is upside down from what this file used to say, and the old advice was
simply wrong: mouth-down leaves the screw boss cantilevered in mid-air. Roof
down puts the boss and both tie tabs on the bed. Proven on the printer first,
then confirmed by the audit below. The bore is vertical either way, so nothing
is lost for setting the insert with an iron — the part is just flipped after
printing.

**The yoke needs no support in that orientation.** It used to: printed top-face
down, the foot's *top* face is its floor in the printer, landing 8.2 mm up as a
6.15 mm cantilever off the jaw wall at 90°. A 45° buttress now fills the wedge
above each foot, hollowed by the counterbore's own slot carried up through it so
the driver still reaches. Costs 0.2 cm³ and nothing in the bounding box.

Audited rather than assumed — every face whose normal points into the build
direction, by area:

| part | orientation | remaining 90° faces | what |
|---|---|---|---|
| yoke | bar top on bed | 2 × 13.8 mm² | the counterbore seats, 0.95 mm wide |
| anchor | **roof on bed** | 8.0 mm² | blind bottom of the insert bore |
| anchor | mouth on bed | 51.2 mm² | 41.9 of it under the screw boss |

The yoke's remainder is deliberate. That face is the screw's flat seat, and it is
0.95 mm wide across a slot, which bridges. Sloping it to 45° would make it a
countersink, and a countersunk head self-centres — which is exactly what the
slotted holes exist to avoid.

Both parts print without support. The anchor's remaining 8.0 mm² is a ø3.2
ceiling over the relief pocket the insert's displaced plastic goes into, so a
little droop there is harmless by construction.

Printing roof down has a second benefit worth keeping in mind if anyone is ever
tempted to flip it back: the tabs' depth-stop face comes out as a clean printed
**top** surface. Mouth down it is an overhang, and support scarring on that face
is not cosmetic — it is the datum the whole preload is measured from.

The coupon carries everything whose fit is uncertain — card slot at 0.3 per
face, M2.5 hole, foot — and none of the socket geometry. Print it, push it onto
the card's end, try a screw. Then adjust `FIT` if needed.

`PRESS = 0.15` is the interference per flank — raised from 0.10, which printed
and went on but did not grip hard enough to trust. Print **one** anchor and try
it on a tower before committing to the pair: back toward 0.10 if it will not
start, on toward 0.20 if it still slides on freely. The towers are 30-year-old
plastic and worth one deliberate test.

**Read that number together with the fourth-side tabs.** As a U the flanks were
tied at one end only, so the mouth could open and much of the nominal
interference was absorbed in bending rather than felt as grip. Closing the ring
stiffens them a long way, so 0.15 with the tabs bites much harder than 0.15
would have without them — the two changes compound, and the tabs alone may
account for most of what the first print was missing. If an anchor will not
start, drop `PRESS` before touching the tabs.

## How hard it presses

`BAR_H` sets it, and the bar is the soft part. Estimated at E = 2 GPa for
printed PETG — good to about a factor of two, so treat these as ratios rather
than absolutes:

| `BAR_H` | I (mm⁴) | mid-span rate | force at 1.0 mm | stands |
|---|---|---|---|---|
| **5.0** (current) | 61 | ~5 N/mm | **~5 N** | 36 mm |
| 6.0 | 106 | ~9 N/mm | ~9 N | 37 mm |
| 7.0 | 168 | ~15 N/mm | ~15 N | 38 mm |

5 N is the "few newtons this has to resist" the press-fit note assumes, so the
current bar is adequate rather than generous. Going stiffer costs a 4.3 cm³
yoke reprint and height above the board, and **nothing here records what
clearance there is above SK9 with the case on** — measure that before spending
it. Raising `ANCHOR_DROP` is the cheap alternative (anchors are 1.1 cm³), but it
buys force by winding up travel the press fit has to hold, where a stiffer bar
buys it for free at the same travel.

Note the bar also sags between the screws, so a floppier bar means the middle of
the card is clamped least — which is where it matters, given the recorded
symptom is errors only while the board is flexed.

## Hardware

- 2 × M2 heat-set inserts, 3.2 mm bore × 4.0 mm — check against what's on hand
  and adjust `INSERT_D` / `INSERT_L`.
- 2 × M2 pan-head screws, ~8 mm.
- Adhesive optional but reasonable. The preload reacts by trying to pull the
  anchors up off their towers, so gluing that joint is belt-and-braces against
  the one load it sees. PETG creeps and the interference relaxes over years
  regardless, so epoxy is the long-term answer either way. Seat on the tab stop
  before it goes off.

## Assembly order

1. Press an anchor onto each tower (lead-in chamfer at the mouth guides it)
   **until the two inner tabs seat on the socket body's top face**. That is a
   positive depth stop and it is what makes the preload repeatable: nothing else
   on the anchor bottoms out, so before the tabs existed its height on the tower
   was set by feel, and preload is measured from the anchor's roof. An anchor
   0.5 mm high or low was half the preload travel, gone. If gluing, seat on the
   stop first and glue after — the stop sets the height, not the adhesive.
2. Set an insert into each anchor from above.
3. Fit the VRAM card.
4. Lower the yoke on — jaws straddle the card's ends, bar lands on its top edge.
   Note step 3 now threads the card through the anchors' own slots as well, so
   they want to be square on their towers before the card goes in. `TIE_CLEAR`
   opens those slots 0.25 per face wider than the yoke's for exactly this.
5. Screw down. The gap under each foot — `SEAT_GAP` 0.4 plus `ANCHOR_DROP` 0.6,
   **1.0 mm** total — means the screws close it and **preload the bar onto the
   card**, rather than the foot bottoming out and holding the bar off it.

   The joint is **displacement-controlled**: once the foot lands on the anchor's
   roof, more torque clamps foot to anchor and adds nothing to the card. So
   preload is set by geometry, not by how hard the screws go up. Keep it that
   way — it cannot be over-tightened onto a 30-year-old card, and it repeats
   build to build. `ANCHOR_DROP` is the only knob for more force.

   Note the reaction: the card pushes the bar up, so the screws hold the yoke
   ends down and the **anchors are pulled up off their towers by the preload
   itself**. Preload and press fit are not independent — every 0.1 on
   `ANCHOR_DROP` is more pull-off asking to be carried by `PRESS` and the
   fourth-side tabs.

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
