"""VRAM card retainer — Acorn RISC PC. One printed clip, bonded to the socket.

The problem
-----------
The VRAM module is held in its 136-way DIMM socket by edge-connector friction
and a single plastic latch at the left-hand end -- a cream moulding clipped
into the black tower, separate from it. That latch cracked, and has since been
removed altogether, so the socket now has NO retention of its own: this clip is
not supplementing anything, it is the whole mechanism. It matters more here
than it would elsewhere: two socket contacts were snapped off and repaired by
bending the remaining halves out to meet the card
(tools/risc-pc-diag/README.md), so seating pressure is doing the work a full
contact spring would otherwise do, and the recorded symptom is errors that
appear only while the board is flexed.

The part
--------
One piece, lowered straight down onto the fitted card:

  * a **bar** along the card's top edge, which is what stops it lifting;
  * a **jaw** at each end that embraces both card faces, which is what stops it
    flexing sideways;
  * a **cap** at each end that drops over the socket's end tower and is bonded
    to it, which is what holds the whole thing down.

Why the jaws are at the ends and not continuous. Photographs of this card
measured against the TRM's 102.87 length show the TSOPs sitting flush with the
top edge and the 47uF electrolytics 0.8 below it -- there is no clear card to
grip along the length, and a channel clearing a 6.5 component stack one side
and 4.0 the other would be ~16 across in a socket 6.5 wide. But both ends carry
a component-free zone about 8 mm wide (side A) and 7 mm (side B), full card
height, and that is where the jaws go. Conveniently that is also where the
socket's towers are, so gripping the card and anchoring to the socket become
one feature instead of two.

Why bonded rather than screwed. The SK9 close-up shows ~3.5 mm of clear board
beyond the left tower before a large electrolytic, and effectively none beyond
the right. There is nowhere to put a screw boss. A bonded cap loads the joint
in shear when the card lifts, which is the direction adhesive is strong in.

How the tower's unmeasured dimensions are absorbed. The cap pockets are open at
the bottom and open on the inner face, and are deliberately oversized by EPOXY
on every side. Nothing bottoms out on the tower: the part's height is set by the
bar sitting on the card's top edge, the cap slides down over the tower as far as
it goes, and the adhesive fills whatever gap is left. So TOWER_H does not have
to be right -- only large enough not to foul the jaw above it -- and the tower's
plan size only has to be right to within about a millimetre.

Fitting is therefore: card in, adhesive into the two cap pockets, clip straight
down. Removing the card later means cutting the clip off and printing another,
which at 5 cm^3 of PETG is not much of a price.

Geometry
--------
Origin is the centre of the card, on the card's mid-plane, at the height of the
socket's top face. +X along the card, +Y toward Side B (the 4.00 mm component
side; the TRM has Side A facing the front of the main PCB), +Z up.
"""

import re
from pathlib import Path

from build123d import *

# --- Card. TRM Figure 2.18 (page 2-27), plus photographs of this card. ------
CARD_L = 102.87        # overall length
CARD_H = 28.0          # overall height, max
CARD_T = 1.27          # PCB thickness, +/- 0.1
CLEAR_END = 6.5        # component-free zone at each end. Measured off photos:
                       # ~8 on side A, ~7 on side B. Take the smaller, less a
                       # margin -- overrunning it means sitting on a TSOP.

# --- MEASURE ---------------------------------------------------------------
# Socket length and width are scaled off the SK9 close-up against the 1.27 mm
# contact pitch, so roughly +/- 2 mm. The tower figures are eyeballed off the
# same photo; see the docstring for why that is survivable.
SOCKET_L = 110.36      # MEASURED. Socket overall, outer face of one end tower
                       # to the other. The photo-scaled estimate was 105, which
                       # would have put each anchor 2.7 mm out of position --
                       # nearly three times what the slotted screw holes absorb.
                       # It also means the towers stand 3.75 mm proud of the
                       # card's ends rather than sitting flush with them.
# Two heights referenced to the motherboard, which is how they are actually
# measured -- and the only two that decide whether the jaw has anything to grip.
# The socket's own height cancels out of that calculation entirely: the grip is
# just CARD_TOP - TOWER_TOP - TOWER_CLEAR.
TOWER_TOP = 18.90      # MEASURED. Top of the black tower, above the motherboard.
CARD_TOP = 31.0        # MEASURED. Top edge of the card, seated, above the
                       # motherboard. Puts the card's bottom edge 3 mm above the
                       # board and 6 mm inside the socket, which is consistent
                       # with the TRM's 28.0 overall.
SOCKET_H = 5.2         # MEASURED. Socket body top face, above the motherboard.
                       # Only sets where the anchor stops and how the context
                       # geometry draws -- not the grip. Lower than assumed, so
                       # the card turns out to sit only 2.2 mm into the socket:
                       # its bottom edge is 3 mm off the board against a 5.2 mm
                       # socket. Which is worth knowing on its own -- there is
                       # very little engagement holding this card in.

TOWER_H = TOWER_TOP - SOCKET_H      # tower, above the socket's top face
CARD_SUNK = CARD_H - (CARD_TOP - SOCKET_H)   # card buried in the socket
TOWER_X = 7.7          # MEASURED. End tower, along the socket -- square in plan
                       # with TOWER_Y. The tower is the black
                       # moulding only; the cream latch that clipped into it is
                       # gone, so its end face and both flanks are clear.
TOWER_Y = 7.7          # MEASURED. End tower, across the socket
CAP_SIDE = +1          # which flank of the socket the cap wraps onto. The
                       # board is not symmetric here: a sharp top view puts
                       # roughly 5 mm of clear board on the RP14/RP15 side of
                       # the left tower and about 2 on the side carrying the SO
                       # packages, so the cap takes the roomy one. Flip to -1 if
                       # that is the wrong way round on the real board.

CARD_FREE = CARD_TOP - SOCKET_H  # card standing proud of the socket

# --- Print -----------------------------------------------------------------
FIT = 0.2              # printer tolerance, per face. Everything that has to
                       # mate with something else is derived from this rather
                       # than carrying its own number, so a test print that
                       # comes out tight is one edit, not six.
WALL = 2.0             # jaw walls
CAP_WALL = 1.2         # cap walls. Thinner than the jaw because every
                       # millimetre here is measured against 1-2 mm of clear
                       # board; the cap is loaded in shear along a bonded face,
                       # not in bending, so section buys nothing.
GAP = FIT + 0.1        # per-face clearance to the card. Deliberately looser
                       # than FIT: this slides onto a thirty-year-old PCB whose
                       # edge may carry burrs, residue or a little swelling,
                       # and a slot that grips is worse than one that doesn't.
PRESS = 0.15           # interference per flank, so the pocket is 0.3 narrower
                       # than the tower and the anchor presses on rather than
                       # being bonded. Raised from 0.10, which printed and went
                       # on but did not grip hard enough to trust on its own.
                       # Note this compounds with TIE below: closing the fourth
                       # side stiffens the flanks a long way, so the SAME
                       # interference already bites harder than it used to. The U puts the printed part in tension
                       # and the 30-year-old tower in compression, which is the
                       # right way round for the old plastic. Adhesive is still
                       # available as a belt-and-braces addition; it is no
                       # longer what holds the part on.
                       #
                       # PETG creeps, so an interference fit relaxes over years.
                       # The margin is large enough to absorb that: flank
                       # contact is ~350 mm2, and even a fraction of the initial
                       # contact pressure leaves friction far above the few
                       # newtons this has to resist. If it ever does loosen, a
                       # drop of epoxy in the same joint recovers it.
BAR_H = 5.0            # bar depth above the card's top edge
FOOT_T = 3.0           # yoke's foot, sitting on the anchor's roof
ANCHOR_DROP = 0.6      # how far the anchor's roof sits BELOW the yoke datum,
                       # adding to SEAT_GAP to make the total preload travel.
                       # Two reasons it lives here rather than in SEAT_GAP,
                       # which is geometrically the same thing:
                       #
                       # 1. It is on the anchor, and the anchors are the part
                       #    being reprinted anyway. A yoke that already fits
                       #    stays fitted -- 2 x 1.1 cm3 instead of 4.3.
                       # 2. It keeps _jaw_z0 fixed. That datum also sets the
                       #    yoke's jaw bottom and the clearance the insert boss
                       #    needs over the tower, so moving it to chase preload
                       #    would quietly change the card grip as well.
                       #
                       # This is the ONLY knob for preload force. The joint is
                       # displacement-controlled: once the foot lands on the
                       # roof, more screw torque clamps foot to anchor harder
                       # and adds nothing to the card. Which is the property
                       # worth keeping -- it cannot be over-tightened onto a
                       # 30-year-old card, and it repeats build to build.
SEAT_GAP = 0.4         # designed gap under the foot. The yoke's height is set
                       # by the bar resting on the card's top edge, so the foot
                       # must NOT reach the anchor's roof on its own -- if it
                       # did, any stack-up error would hold the bar off the
                       # card, which is the one job it has. Leaving a gap makes
                       # the screw close it, which preloads the bar downward
                       # instead.
SCREW_CLEAR = 2.0 + 2 * FIT   # M2 clearance. Printed holes come out
                       # undersize by roughly a layer width, so this is nominal
                       # plus FIT per side rather than a table value.
INSERT_D = 3.2         # M2 heat-set insert: bore diameter...
INSERT_L = 4.0         # ...and length. Check against the inserts actually held;
                       # 3.2 x 4.0 is the common M2 short.
SCREW_HEAD_D = 4.3     # M2 pan head (4.0 nominal) plus clearance.
SCREW_CBORE = 1.8      # counterbore depth, against a ~1.6 M2 pan head. A
                       # counterbore and a pan head, not a countersink: the
                       # holes below are SLOTTED, and a countersunk head
                       # self-centres, which would fight the slot and pull the
                       # yoke back to nominal anyway.
                       #
                       # M2 rather than M2.5 because that is what is on hand.
                       # It also buys back roughly 0.8 mm on the flank, which
                       # is the direction that matters: the boss clearance past
                       # the socket body is the one dimension still unverified.
SCREW_SLOT = 1.0       # +/- travel in the screw slots. The anchors are bonded
                       # to real towers, not placed at modelled coordinates, so
                       # they will not land exactly where SOCKET_L says. This is
                       # what absorbs that -- and it is cheaper than measuring
                       # SOCKET_L to a tenth.

TOWER_CLEAR = INSERT_L + 1.5   # jaw stops this far above the tower. Sized by
                       # the insert, not by clearance: the insert's boss cannot
                       # sit beside the tower without being pushed a further
                       # 1.2 mm outboard into board space this design does not
                       # have, so instead the whole yoke interface lifts until
                       # the boss clears the tower and can come inboard. It
                       # costs grip on the card, which the towers are largely
                       # providing anyway.

TIE_CLEAR = 0.25       # extra per face in the anchor's card slot, over and
                       # above the yoke's GAP. The yoke is located by the screws
                       # and lands where the anchors put it, but these two slots
                       # are on parts pressed onto real towers by hand, so the
                       # card has to thread through both of them before the yoke
                       # is anywhere near. Cheaper to open them up than to make
                       # the card fight two hand-placed alignments.
TIE_Z0 = 0.0           # ...which also makes the tabs a DEPTH STOP, and that
                       # turns out to matter more than the tie did. Nothing else
                       # on this anchor bottoms out on anything: the flanks pass
                       # the socket body outboard and stop 1.5 above the board,
                       # so before the tabs existed the anchor's height on the
                       # tower was just however hard it was pressed. Preload is
                       # SEAT_GAP + ANCHOR_DROP measured from the anchor's ROOF,
                       # so an anchor sitting 0.5 high or low was 0.5 of preload
                       # error -- half the travel, set by feel. The tabs land on
                       # the socket body's top face at exactly nominal depth, so
                       # now: press until they seat, and the preload is the
                       # number in the report. Glue, if used, goes on after that
                       # -- the stop sets the height, not the adhesive.
                       #
                       # the tie starts at the socket's TOP FACE, not at the
                       # bottom of the anchor. Below that the socket body (~6.5
                       # across) is wider than the tower (7.7) only in the sense
                       # that the flanks clear it -- a wall on the inner face
                       # would run straight into the body. Above it there is
                       # nothing but the card, which the slot is for.

_jaw_hw = CARD_T / 2 + GAP + WALL            # jaw half-width
_grip_hw = TOWER_Y / 2 - PRESS               # pocket half-width; undersize
_cap_hw = _grip_hw + CAP_WALL                # anchor half-width, both flanks
_slot_hw = CARD_T / 2 + GAP                  # card slot half-width
_tie_hw = _slot_hw + TIE_CLEAR               # ...and the anchor's, looser
_cap_x1 = SOCKET_L / 2 + FIT + CAP_WALL      # cap outer face
_cap_x0 = SOCKET_L / 2 - TOWER_X             # cap inner face
_jaw_x0 = CARD_L / 2 - CLEAR_END             # jaw reaches this far in
_jaw_z0 = TOWER_H + TOWER_CLEAR              # jaw bottom, clear of the tower
_anchor_z1 = _jaw_z0 - ANCHOR_DROP           # anchor roof, dropped below it
# The anchor runs almost to the motherboard rather than stopping at the socket's
# top face. The tower is full height and 7.7 across where the socket body is
# only ~6.5, so the anchor's flanks clear the body all the way down -- and the
# bonded area roughly doubles for nothing but a taller print. 1.5 mm of standoff
# keeps it off the solder fillets.
_anchor_z0 = 1.5 - SOCKET_H
# The screw lands over the tower, on the roomy flank, in the card's
# component-free end zone -- so a driver comes straight down beside the bar with
# nothing in the way. Anywhere further inboard and it would be under a TSOP.
_screw_x = SOCKET_L / 2 - TOWER_X / 2
# Two constraints set how far out the screw sits, and picking a number by hand
# violated the second: the pilot hole reached inboard of the boss's inner face,
# because the boss cannot start further in than the tower's flank, and the hole
# broke straight out of the side. Derived from both, it cannot drift again.
#   1. the head's counterbore must clear the jaw's outer face
#   2. the pilot hole must sit wholly inside a boss that starts at the tower
_boss_in = _jaw_hw + FIT       # boss clears the jaw; it is above the tower now
_screw_y = CAP_SIDE * max(
    _jaw_hw + SCREW_HEAD_D / 2 + 0.1,      # counterbore clears the jaw
    _boss_in + 1.2 + INSERT_D / 2,         # insert bore keeps a 1.2 wall
)
_foot_y = CAP_SIDE * (abs(_screw_y) + SCREW_HEAD_D / 2 + 1.0)


def _slab(x0, x1, y0, y1, z0, z1) -> Part:
    """A box given by its bounds. The geometry here is all axis-aligned faces
    against a real socket, so bounds read far more directly than centres.
    Bounds are sorted, so a mirrored feature can be written by negating both
    ends without the pair coming out reversed."""
    (x0, x1), (y0, y1), (z0, z1) = sorted((x0, x1)), sorted((y0, y1)), sorted((z0, z1))
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(
        x1 - x0, y1 - y0, z1 - z0
    )


def _slotted(x, y, z, length, dia, height) -> Part:
    """A rounded slot running along X: two cylinders and the box between."""
    return (
        Pos(x - length / 2, y, z) * Cylinder(dia / 2, height)
        + Pos(x + length / 2, y, z) * Cylinder(dia / 2, height)
        + _slab(x - length / 2, x + length / 2, y - dia / 2, y + dia / 2,
                z - height / 2, z + height / 2)
    )


def _bevel(part: Part, length: float, test, axis=None) -> Part:
    """Chamfer, selected by position the same way as _round."""
    edges = part.edges().filter_by(axis) if axis else part.edges()
    picked = [e for e in edges if test(e.center())]
    if not picked:
        return part
    for L in (length, length * 0.6, length * 0.35):
        try:
            return chamfer(picked, L)
        except Exception:
            pass
    print(f"  note: no chamfer fitted those {len(picked)} edges; left square")
    return part


def _round(part: Part, radius: float, test, axis=None) -> Part:
    """Fillet every edge whose midpoint satisfies `test`. Selecting by position
    rather than by index keeps the choice readable and stops it silently moving
    when a dimension changes."""
    edges = part.edges().filter_by(axis) if axis else part.edges()
    picked = [e for e in edges if test(e.center())]
    if not picked:
        return part
    # Step down rather than fail. A radius is capped by the smallest face it
    # runs onto, and those faces move every time a socket dimension changes;
    # losing 0.5 mm of radius is not worth a broken build, but it is worth
    # saying out loud.
    for r in (radius, radius * 0.6, radius * 0.35):
        try:
            return fillet(picked, r)
        except Exception:
            if r == radius:
                print(f"  note: r={radius} refused on {len(picked)} edges, stepping down")
    print(f"  note: no radius fitted those {len(picked)} edges; left square")
    return part


def yoke() -> Part:
    top = CARD_FREE + BAR_H

    # The bar, running the whole length. It rests on the card's 1.27 mm top
    # edge and everything else it spans is thin air -- the components stand
    # proud of the card's faces, not above its edge.
    part = _slab(-_cap_x1, _cap_x1, -_jaw_hw, _jaw_hw, CARD_FREE, top)

    for s in (-1, 1):
        # Jaw: down the card's faces, in the component-free end zone.
        part += _slab(s * _jaw_x0, s * _cap_x1, -_jaw_hw, _jaw_hw, _jaw_z0, CARD_FREE)
        # Foot: widens the jaw sideways to sit on the anchor's roof, and takes
        # the screw.
        part += _slab(
            s * (_screw_x - 5.0), s * (_screw_x + 5.0),
            CAP_SIDE * _jaw_hw, _foot_y,
            _jaw_z0 + SEAT_GAP, _jaw_z0 + SEAT_GAP + FOOT_T,
        )
        _ft = _jaw_z0 + SEAT_GAP + FOOT_T          # top of the foot
        # Buttress over the foot, which is what lets this print without support.
        # Printed as the handover says -- bar's top face on the bed -- "up" is
        # -Z, so the foot's TOP face is its floor in the printer and it lands
        # 8.2 mm up with nothing beneath it: a 6.15 mm cantilever off the jaw
        # wall, at 90 degrees. Filling the wedge above it at 45 degrees (rise
        # equals reach) means each layer grows outward from the jaw by no more
        # than the layer height, so it carries itself.
        #
        # It has to be hollow or it would bury the screw. The channel is the
        # counterbore's own slot carried up through the wedge, which is exactly
        # the right size by construction: whatever driver turns the head fits
        # through the hole the head came down. What's left is two ribs, and they
        # land under the two solid strips of the foot's floor either side of the
        # counterbore -- the parts that actually need holding up.
        _reach = abs(_foot_y) - _jaw_hw
        _wedge = Plane.YZ * Polygon(
            (CAP_SIDE * _jaw_hw, _ft),
            (_foot_y, _ft),
            (CAP_SIDE * _jaw_hw, _ft + _reach),
            align=None,
        )
        part += Pos(s * _screw_x, 0, 0) * extrude(_wedge, amount=5.0, both=True)
        part -= _slotted(s * _screw_x, _screw_y, _ft + _reach / 2,
                         2 * SCREW_SLOT, SCREW_HEAD_D, _reach)
        part -= _slotted(s * _screw_x, _screw_y, _ft - FOOT_T / 2,
                         2 * SCREW_SLOT, SCREW_CLEAR, FOOT_T * 3)
        part -= _slotted(s * _screw_x, _screw_y, _ft - SCREW_CBORE / 2 + 0.05,
                         2 * SCREW_SLOT, SCREW_HEAD_D, SCREW_CBORE)

    # One slot for the card, through jaws and cap roofs alike. Stops short of
    # the cap's outer wall, which is solid.
    part -= _slab(
        -(CARD_L / 2 + 0.5), CARD_L / 2 + 0.5, -_slot_hw, _slot_hw, -6.0, CARD_FREE
    )

    # Lead-in at the mouth of the card slot: this is lowered on blind, into a
    # slot between the SIMM bank and VIDC.
    part = _round(
        part, 0.6,
        lambda c: abs(c.Z - _jaw_z0) < 0.05 and abs(abs(c.Y) - _slot_hw) < 0.05,
    )
    # The step where each jaw meets its cap, and the outer corners.
    part = _round(
        part, 1.5,
        lambda c: abs(c.Z - _jaw_z0) < 0.05 and abs(abs(c.Y) - _jaw_hw) < 0.05,
    )
    part = _round(
        part, 1.0, lambda c: abs(abs(c.X) - _cap_x1) < 0.05, axis=Axis.Z
    )
    return part


def anchor(right: bool = True) -> Part:
    """One press-fit anchor over the socket's end tower, taking both flanks, the
    outer end face and — above the socket body — most of the inner face too.
    Modelled at +X and mirrored, so the pair is identical and only handed.

    The pocket is open at the bottom and undersize by PRESS on each flank, so it
    presses on rather than being bonded; nothing bottoms out on the tower, and
    the part's height is set by the yoke's bar landing on the card."""
    # A ring in plan, broken only by the card slot: both flanks, the outer end
    # wall, and two tabs across the inner face. Open at the bottom so it presses
    # straight down over the tower.
    block = _slab(  # outer end wall
        SOCKET_L / 2 + FIT, _cap_x1, -_cap_hw, _cap_hw, _anchor_z0, _anchor_z1
    )
    for f in (-1, 1):
        block += _slab(
            _cap_x0, _cap_x1, f * _grip_hw, f * _cap_hw, _anchor_z0, _anchor_z1
        )
    # The fourth side. As a U the flanks could splay apart under the very load
    # the part exists to resist -- the outer end wall ties them at one end only,
    # so the mouth is free to open and the grip is whatever the print's stiffness
    # in bending happens to be. Two tabs across the inner face close the ring and
    # put the flanks in tension instead, which is what makes the interference
    # actually bear.
    #
    # It cannot be a full wall: the card passes through here (the towers stand
    # 3.75 mm proud of the card's ends, so the card's end is INSIDE the tower's
    # footprint in X), hence the slot between the tabs. And it cannot run the
    # full height: below the socket's top face the body is in the way, which is
    # why the flanks clear it out at +/-3.75 and a tab at +/-1.2 would not.
    for f in (-1, 1):
        block += _slab(
            _cap_x0 - CAP_WALL, _cap_x0,
            f * _tie_hw, f * _cap_hw,
            TIE_Z0, _anchor_z1,
        )
    # No roof over the tower. It would have to cross whatever posts and latch
    # arms stand up from it, which are the one thing no photograph has shown me
    # clearly. It turns out to be doing no work: the load path is yoke -> screw
    # -> boss -> flank -> bond, and the flank boss below sits outboard of the
    # tower in Y, so nothing of this part passes over the tower at all.
    # Boss under the screw, since the roof alone is thinner than the thread.
    block += _slab(
        _screw_x - 5.0, _screw_x + 5.0,
        CAP_SIDE * _boss_in, _foot_y,
        _anchor_z1 - INSERT_L - 1.5, _anchor_z1,
    )
    # Insert bore, open at the top so the insert is set in from above with an
    # iron. Sunk a little deeper than the insert, so displaced plastic has
    # somewhere to go rather than lifting it proud of the face the yoke lands on.
    block -= Pos(_screw_x, _screw_y, _anchor_z1 - (INSERT_L + 0.8) / 2) * Cylinder(
        INSERT_D / 2, INSERT_L + 0.8
    )
    # Print this ROOF DOWN -- the face the yoke's feet land on against the bed.
    # That puts this boss and both tie tabs on the build plate; mouth down leaves
    # the boss cantilevered and costs 51 mm2 of 90-degree overhang against 8.
    # It also means the tabs' stop face prints as a clean top surface rather than
    # a supported underside, and that face is the preload datum.
    #
    # Lead-in at the mouth, so a press fit starts square instead of catching a
    # corner on the tower and shearing a flank off.
    block = _bevel(
        block, CAP_WALL * 0.6,
        lambda c: abs(c.Z - _anchor_z0) < 0.05 and abs(abs(c.Y) - _grip_hw) < 0.05,
    )
    return block if right else mirror(block, Plane.YZ)


def coupon() -> Part:
    """One end of the yoke, for a two-minute test print. It carries the card
    slot, the foot and the screw hole -- everything whose fit is uncertain --
    so GAP and SCREW_CLEAR can be checked against the real card and a real
    screw before committing to the full part or trusting the socket figures."""
    return yoke() & _slab(
        _jaw_x0 - 4.0, _cap_x1 + 1, -20, 20, -10, CARD_FREE + BAR_H + 1
    )


def card() -> Part:
    """The VRAM module, for fit checking only -- never exported."""
    return _slab(-CARD_L / 2, CARD_L / 2, -CARD_T / 2, CARD_T / 2, -CARD_SUNK, CARD_FREE)


def socket() -> Part:
    """Socket body and the two end towers, for fit checking only."""
    body = _slab(-SOCKET_L / 2, SOCKET_L / 2, -3.25, 3.25, -SOCKET_H, 0)
    for s in (-1, 1):
        body += _slab(
            s * (SOCKET_L / 2 - TOWER_X), s * SOCKET_L / 2,
            -TOWER_Y / 2, TOWER_Y / 2, 0, TOWER_H,
        )
    return body - _slab(-CARD_L / 2, CARD_L / 2, -CARD_T, CARD_T, -SOCKET_H + 2, TOWER_H)


if __name__ == "__main__":
    here = Path(__file__).parent
    # Both hands exported. The U is symmetric across the flanks, but the part
    # is not: the end wall is at one end and the screw boss on one flank, so the
    # pair is chiral and no rotation turns one into the other. Shipping both
    # beats a note in a README that says "mirror this one".
    parts = {
        "yoke": yoke(),
        "anchor_right": anchor(True),
        "anchor_left": anchor(False),
        "coupon": coupon(),
    }
    for name, p in parts.items():
        step = here / f"vram_{name}.step"
        export_step(p, str(step))
        # STEP writes the wall-clock time into its header, so an unchanged model
        # still produces a changed file and every regeneration shows up as a
        # diff. Pinning it makes the artifacts reproducible: `git status` then
        # only reports geometry that actually moved.
        step.write_text(
            re.sub(r"'\d{4}-\d{2}-\d{2}T[\d:]+'", "'1970-01-01T00:00:00'",
                   step.read_text(), count=1)
        )
        export_stl(p, str(here / f"vram_{name}.stl"))
        bb = p.bounding_box()
        print(f"{name:10s} {bb.size.X:6.1f} x {bb.size.Y:5.1f} x {bb.size.Z:5.1f} mm"
              f"   {p.volume / 1000:5.1f} cm^3   solids={len(p.solids())}")
    print(f"jaw grips  {CARD_FREE - _jaw_z0:.1f} mm of card face, both sides, "
          f"{CLEAR_END:.1f} mm in from each end")
    print(f"           = CARD_TOP {CARD_TOP} - TOWER_TOP {TOWER_TOP} "
          f"- {TOWER_CLEAR} clearance, both above the motherboard")
    print("           card top vs grip: " + "  ".join(
        f"{t:.0f}->{t - TOWER_TOP - TOWER_CLEAR:.1f}" for t in (26, 28, 29, 31)
    ) + f"   (CARD_TOP -> mm of grip; at or below "
        f"{TOWER_TOP + TOWER_CLEAR:.1f} there is none)")
    print(f"bar        {2 * _jaw_hw:.2f} mm across, vs 6.5 for the socket body")
    _grip_h = _jaw_z0 - _anchor_z0
    _I = 2 * _jaw_hw * BAR_H ** 3 / 12
    _rate = 48 * 2000.0 * _I / (2 * _screw_x) ** 3
    print(f"bar stiff  ~{_rate:.0f} N/mm mid-span (E=2 GPa printed PETG, I={_I:.0f} mm4), "
          f"so {SEAT_GAP + ANCHOR_DROP:.2f} mm travel is roughly "
          f"{_rate * (SEAT_GAP + ANCHOR_DROP):.0f} N. Order of magnitude only -- E for a "
          f"printed part is good to about a factor of two.")
    print(f"preload    {SEAT_GAP + ANCHOR_DROP:.2f} mm of yoke deflection "
          f"(SEAT_GAP {SEAT_GAP} + ANCHOR_DROP {ANCHOR_DROP}); "
          f"screw spans {SEAT_GAP + ANCHOR_DROP + FOOT_T - SCREW_CBORE + INSERT_L:.1f} mm "
          f"head-face to insert bottom")
    print(f"press fit  {2 * PRESS:.2f} mm interference across {TOWER_Y} of tower, "
          f"over 2 x {TOWER_X * _grip_h:.0f} mm2 of flank")
    print(f"           sticks out {_cap_hw - 3.25:.2f} mm past the socket body, "
          f"both flanks (the screw boss needs {abs(_foot_y) - 3.25:.2f} on one)")
    print(f"anchor U   {2 * _cap_hw:.2f} mm across, pocket {2 * _grip_hw:.2f} "
          f"onto a {TOWER_Y} tower")
    print(f"stands     {top_h:.1f} mm above the motherboard "
          f"({CARD_H - CARD_SUNK + SOCKET_H:.1f} for the bare card)"
          if (top_h := CARD_FREE + BAR_H + SOCKET_H) else "")

    try:
        from ocp_vscode import show

        show(parts["yoke"], anchor(True), anchor(False), card(), socket(),
             names=["yoke", "anchor R", "anchor L", "card", "socket"])
    except Exception as exc:
        print(f"viewer not connected ({exc.__class__.__name__})")
