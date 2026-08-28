# VRAM retainer — handover

State as of **2026-08-29**. The clip is **fitted and the machine is running
clean** — see `Dev Diary.md`, entry of Aug 28. The model is
[`vram_retainer.py`](vram_retainer.py); this file carries the project context
that isn't in the code.

## Where this stands, in one paragraph

Designed, printed, fitted, working. The fault it exists to fix — garbage on
100 % of boots with the VRAM in, clean with it out — has stopped. Nothing is
blocking, no change is pending, and the only open item is **attribution**: the
board was washed, dried, reassembled and the card reseated in the same session,
so a clean machine does not by itself prove the clip is why. Pulling the clip
later and seeing whether the fault returns settles that whenever it is worth
doing. Everything below is the record of how the design got here and what to
re-check if it ever stops being true.

**If you are picking this up cold:** read this file, then the model's docstring,
then `Dev Diary.md` from the Aug 23 entry onward. The four STLs in this
directory are current, are in print orientation, and match what is on the
machine.

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
| Card components | 6.5 max side A, 4.00 max side B (actual **6.04** / **1.60**) | TRM Fig 2.18; drg 0197,004/A |
| Card mounting holes | ø3.18, 3.38 in from each end, 6.35 up | TRM Fig 2.18 |
| Card top edge, seated | 31.0 mm — **superseded**, see `CARD_SEATED` | calipers |
| Card top edge above the **socket's** top face | **25.0 mm** | calipers, seated |
| Tower top | **18.90 mm** | calipers |
| Socket body top | **5.2 mm** | calipers |
| Tower plan | **7.7 × 7.7 mm** (square) | calipers |
| Socket overall, tower outer to tower outer | **110.36 mm** | calipers |
| Assembly height, and it clears the 2nd slice | **36.0 mm** | case reassembled |
| Clear card at each end (no components) | **6.74** one end (side B, IC24), **7.08** the other (side A, IC1) | drg 0197,004/A |
| Clear card above the top components | **0.49** TSOPs, **0.68** electrolytics | drg 0197,004/A |
| SK9 plan footprint | **110.62 × 9.86 mm** (body alone is 6.5) | drg 0197,000/A |
| Clear board beyond left tower | **1.14 mm**, then C73 | drg 0197,000/A |
| Clear board beyond right tower | **0.30 mm**, then C151 / R213 | drg 0197,000/A |
| Clear board beside left tower | **4.49** +Y (SK4), **15.51** −Y (SK6) | drg 0197,000/A |
| Clear board beside right tower | **2.71** +Y (C152), **2.29** −Y (RP16) | drg 0197,000/A |

Derived: card sits **2.2 mm** into the socket; jaw grips **6.6 mm** of card face;
assembly stands **36.0 mm** above the board against 31.0 for the bare card.

The card's population is modelled from the TRM's **VRAM [2M] PCB ASSEMBLY**
(drg 0197,004/A), which is drawn 1:1 — eight HM538253BTT VRAMs in 44-pin
TSOP-II, four 6.3 mm electrolytics, four ferrite beads and twelve chip caps,
all measured off the drawing at 600 dpi and checked against the printed parts
as a boolean. That replaces the photo estimates in the two rows above, and it
moves one number the right way: the free zone at each end is set by the tighter
FACE, not the tighter end, and the two are on opposite faces (side B at one end,
side A at the other), so `CLEAR_END` has to clear 6.74 whichever way round the
card goes. It does — the nearest package reaches X 43.89 against a jaw starting
at 44.94, so **1.05 mm to spare**, because the drawing's outlines are land
patterns 0.7 mm/side wider than the TSOP leads actually reach.

The one thing that does reach into a jaw's end zone is the item-8 **paper label**
on side A, whose edge lands within 0.05 mm of the jaw's inner face. It is ~0.1
thick against 0.30 of `GAP` per face, so the jaw rides over it.

## First test fit — what it changed

Printed, pressed on and dry-fitted. Five things came back, four of them changes
to the model — which is why everything was reprinted before the fit that stuck.

**The press fit is right.** `PRESS` 0.15/flank goes on hard and holds. Do not
touch it.

**The card sits 0.8 mm lower than the calipers first said.** Measured directly:
25.0 mm from the card's top edge to the socket's top face, against 25.8 modelled
(`CARD_TOP` 31.0 − `SOCKET_H` 5.2). It pushes further home in circuit than it did
when measured out of it. That is now `CARD_SEATED`, and `SEAT_ERROR` is derived
from it rather than typed — it comes off the anchor's **roof**, which is what the
yoke lands on, so the yoke that already fits keeps fitting and the card grip
stays at 6.6 mm. `CARD_TOP` is deliberately left at 31.0: it is the datum the
yoke's jaws are cut to, and correcting it there would reshape the yoke for
nothing.

Symptom this explains: the bar stood ~1.2 mm off the card instead of resting on
it. 0.8 was the card; the other 0.4 was the anchors not yet pressed fully home.

**The tie tabs were stealing the preload.** They and the middle of the outer end
wall topped out level with the roof — but the yoke's jaw hung `SEAT_GAP` below
its foot, so the jaw landed on *them* after 0.6 mm and the foot never reached the
roof. Worth 0.4 mm of the 1.0 the screw is there to deliver, and invisible from
outside. Fixed by moving `SEAT_GAP` onto the anchor (0.4 → 0, `ANCHOR_DROP`
0.6 → 1.0): the yoke's underside is now **one plane**, so the anchor's top can be
one plane too and there is no second surface left to become the wrong stop.

That single move also settled three cosmetic complaints at once — the screw hole
now breaks out on the yoke's own underside instead of a raised island, the
anchor's top face is flush instead of stepped, and `JAW_CLEAR` fell to zero.

**The anchor's pocket is lidded.** With the yoke down you were looking through
the clearance beside the jaw into a 3.3 mm well. The lid sits flush in the top
face, slotted for the card's end, and leaves `LID_CLEAR` 2.7 mm over the tower —
less than the yoke's own jaw already passes, so it assumes nothing new.

**The insert bore goes straight through.** It was blind, 0.8 mm deeper than the
insert, which is not enough: setting a brass insert pushes real volume of melt
ahead of it, the hole packs solid and the insert stops high or splits the boss.
One insert was lost that way. Through, the melt has 1.5 mm of clear hole and then
17 mm of open air under the boss.

Also cosmetic, both parts: the screw holders now run out flush with the end
faces instead of stopping 0.25 mm short.

## Status — clear to build

**Nothing blocks. Both remaining risks were checked on the machine (2026-08-28)
and both are clear.**

- **The end walls fit.** The model's last worry was the outer end walls against
  C151 and R213 off the right end and C73 off the left — 1.10, 1.10 and 0.26 mm
  of plan overlap, from parts whose heights the drawing does not give. Test
  rigged on the real board: there is room. The numbers below stay as the record
  of *why* it was a worry and of what to re-check if an anchor ever will not seat
  flush, but they are not a live constraint.
- **The case closes, but it is SNUG.** The assembly stands **36.0 mm** above the
  motherboard against 31.0 for the bare card, and with the case reassembled the
  yoke clears the **second slice** with little to spare — fitted and
  confirmed, not modelled; there is no case in `vram_retainer.py`. Treat 36.0 as
  a ceiling that has now been **spent**, not as headroom. `BAR_H` 5.0 is the
  whole of the margin over the bare card, so anything that grows it, or raises
  `CARD_TOP`, eats a clearance nobody has measured.

The rest of this section is how that was arrived at, and what to re-check if
any of it ever stops being true.

**The board question is answered, and the answer changed the question.** The
TRM's **MAIN PCB ASSEMBLY** (drg 0197,000/A) is drawn 1:1 — SK9 comes out 110.62
long against the 110.36 measured with calipers, and IC29 27.69 × 27.81 against
the 28 × 28 of a 160-pin PQFP — so the board around the socket is now modelled
from it rather than from photographs, and `vram_retainer.py` checks the printed
parts against it. Three things fell out.

**1. SK9's footprint is 9.86 mm across, not the 6.5 the calipers gave.** The
calipers spanned the moulding around the card slot, up where the anchor grips;
the drawing is the whole footprint. Both are true, and the difference is worth
1.68 mm of clearance in every sum below. It also means the anchor, at 9.80
across, is *narrower than the socket's own footprint* — nothing about its flanks
can foul the board that the socket does not foul already.

**2. The screw boss fits at one tower and not the other.** It reaches
|Y| = 9.09, i.e. 4.16 mm past that footprint. Clear board beside each tower, in
plan, outline to outline:

| | +Y (VIDC / RP14 flank) | −Y (SO packages) |
|---|---|---|
| **left tower** | **4.49** — SK4 ✔ | **15.51** — nothing until SK6 ✔ |
| **right tower** | **2.71** — C152 ✘ | **2.29** — RP16 ✘ |

**`CAP_SIDE` is now −1 and that closes it.** It was +1, off a photograph read
mid-span ("~5 mm on the RP14/RP15 side, ~2 on the SO package side") — backwards
where it matters: beside the *left* tower, −Y is the roomy flank by a factor of
three, because the SO packages start further along the socket.

The deciding reason is not board space, though. **SK4 has a network card in it**
on this machine, standing up right where the boss and a driver want to be.
Observed on the machine; nothing in the TRM says a card is fitted.

And the flip pays twice. On +Y the right tower was blocked by **C152**, a ~10 mm
radial can the boss could never clear. On −Y the nearest thing is **RP16**, an
SOIC-16W **1.6 mm** tall — the boss flies **15.5 mm** over it, confirmed by the
3D check, not just by plan. So the right tower stops being a problem at all, and
the boss's plan clearance stops being the binding number anywhere.

**3. Both anchors' outer end walls overlap something in plan.** Each wants
1.40 mm past the socket's end; the drawing leaves **0.30**. R213 and C151 sit off
the right end (1.10 mm of overlap each) and C73 off the left (0.26). C73 is 1.14
off the socket, not the 3.3 scaled off a photograph.

**Which end is which on the real board.** The model's `anchor_left` is the −X
end: the one with **C73** — a ~11 mm radial electrolytic — hard against it. The
`anchor_right` end is the one with **LK13** and the battery **BT1** beyond it.
Get this the wrong way round and the boss goes to the tower that has no room.

The heights that drove the worry, if it ever needs re-opening: C151 and R213
identify as no standard package (2.9 × 5.5 and 2.9 × 5.8), so they are prisms of
an invented height and still show as fouls in the report. C73's 3D foul vanishes
only because KiCad's D10 can is 1.0 mm smaller than the ø11.01 drawn — the plan
figure, 0.26 mm, is the one to trust there. The anchor stands 1.5 mm off the
board, so anything shorter than that passes under it regardless.

If an end wall ever does foul, in increasing order of cost:

1. `CAP_WALL` on the outer end face only — the end walls need 1.10 mm off to
   clear C151/R213, which is most of the 1.2 they have.
2. `WALL` 2.0 → 1.5 on the jaw — saves 0.5 mm, and now spare rather than needed.
3. Screw only the left anchor and let the right one be press-fit alone. The
   preload is set by the yoke's bar deflecting, so one screw still preloads —
   asymmetrically, and the report's stiffness figure would need redoing.

The anchor's U itself only needs 1.70 mm per flank and is fine everywhere.

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
| `vram_yoke.stl` | 1 | 113.2 × 12.0 × 11.6, 4.5 cm³ |
| `vram_anchor_left.stl` | 1 | 1.0 cm³, 21.1 tall |
| `vram_anchor_right.stl` | 1 | 1.0 cm³, 21.1 tall |

**These four are the ones on the machine.** They are the second set: the first
test fit made the anchors 1.2 mm shorter and moved the yoke's foot, and
`CAP_SIDE` then flipped the screw boss to the other flank. Nothing has changed
since they were printed and fitted, so a reprint is only for a spare or a
replacement, not a pending revision.

**The exported files are already in print orientation** — yoke and coupon on the
bar's top face, anchors roof-down, all sitting on Z = 0. Load and slice; do not
flip them, and do not mirror an anchor to make its pair.

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
yoke reprint and height above the board, and **that height is already spent**:
the assembly stands 36.0 mm and the second slice closes on it with little to
spare (Aug 28, fitted — not modelled). Do not add a millimetre to `BAR_H`
without re-measuring above SK9 with the case on.
Raising `ANCHOR_DROP` is the cheap alternative (anchors are 1.1 cm³), but it
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
5. Screw down. The gap under each foot — `ANCHOR_DROP` **1.0 mm**, with
   `SEAT_GAP` now 0 so the whole of it is on the anchor — means the screws close
   it and **preload the bar onto the card**, rather than the foot bottoming out
   and holding the bar off it.

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

All of this is merged to `main` and pushed, and the working tree is clean.
`feature/vram-retainer`, `feature/sound-schematic` and
`feature/modeserv-mode-string` have been merged and deleted; `main` is the only
branch, per the repo's commit-straight-to-`main` rule.

Gotcha: `ds-view/postexample.dsl` disappears on checkout of branches predating
`03727bb`, because macOS cannot distinguish it from the old `POSTexample.dsl`.
`git checkout -- ds-view/postexample.dsl` restores it.
