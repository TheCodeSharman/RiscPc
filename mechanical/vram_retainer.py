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

Why the jaws are at the ends and not continuous. The TSOPs sit flush with the
card's top edge and the 47uF electrolytics 0.68 below it -- there is no clear
card to grip along the length, and a channel clearing a 6.5 component stack one
side and 4.0 the other would be ~16 across in a socket 6.5 wide. But both ends
carry a component-free zone, full card height, and that is where the jaws go.
Conveniently that is also where the socket's towers are, so gripping the card
and anchoring to the socket become one feature instead of two.

Those zones were first scaled off photographs at "about 8 mm side A, 7 mm side
B". They are now measured off the TRM assembly drawing (see the components
section below), which says 6.74 at one end and 7.08 at the other -- and that
the tighter face SWAPS between the ends, so the jaw has to clear 6.74 at both
whichever way round the card goes. CLEAR_END 6.5 does, and the report checks
it as a boolean against the real packages rather than trusting the arithmetic.

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
from functools import lru_cache
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
ANCHOR_DROP = 1.0      # how far the anchor's roof sits BELOW the yoke datum,
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
CARD_SEATED = 25.0     # MEASURED on the fitted card: its top edge above the
                       # socket's TOP FACE. The model had 25.8 for this
                       # (CARD_TOP 31.0 - SOCKET_H 5.2), so the card sits 0.8
                       # deeper than the calipers first said -- it pushes further
                       # home than it did when measured out of circuit.
SEAT_ERROR = CARD_FREE - CARD_SEATED   # = 0.8, and derived rather than typed:
                       # it is exactly how far the card turned out to sit below
                       # where the model had it, taken back off the anchor's
                       # roof, which is what the yoke lands on.
                       #
                       # It started life as the 1.2 mm gap measured under the
                       # yoke on the first test fit, before CARD_SEATED existed.
                       # Deriving it instead is worth the change: 1.2 closed the
                       # gap but left the foot ON the roof with nothing for the
                       # screw to pull through, and 0.8 leaves the designed
                       # 1.0 mm. The other 0.4 of that first gap was the anchors
                       # not yet pressed fully home.
                       #
                       # This does NOT touch the preload: travel stays
                       # SEAT_GAP + ANCHOR_DROP, because the roof and the foot
                       # move together. It only puts the roof where the yoke
                       # actually arrives. CARD_TOP is deliberately left at 31.0
                       # -- it is the datum the PRINTED yoke was cut to, and
                       # correcting it there would reshape a part that fits. If
                       # the yoke is ever reprinted, set CARD_TOP 30.2 and drop
                       # SEAT_ERROR to 0.4.
SEAT_GAP = 0.0         # gap under the foot, ON THE YOKE. Now zero, and kept as a
                       # name because the reasoning is worth more than the
                       # number: the foot must not reach the anchor's roof while
                       # the bar is still off the card, or a stack-up error gets
                       # held open instead of preloaded. That is still true --
                       # ANCHOR_DROP just carries all of it now.
                       #
                       # Zero because at 0.4 it stood the foot's underside 0.4
                       # proud of the jaw's bottom, and the screw hole broke out
                       # on that little raised island rather than on the yoke's
                       # own underside. The two are geometrically the same knob
                       # (the comment on ANCHOR_DROP says so), so the 0.4 moved
                       # there and the foot came down flush. Travel, preload and
                       # every fit are unchanged -- only the step is gone.
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
_anchor_z1 = _jaw_z0 - ANCHOR_DROP - SEAT_ERROR   # anchor roof, dropped below it
# Where the yoke's jaw ends up once the screw has pulled it all the way down,
# less a little. The anchor must have NOTHING in the jaw's channel above this.
#
# It did, and it was quietly eating the preload. The jaw hangs SEAT_GAP below
# the foot, so anything on the anchor level with the roof -- the tie tabs, the
# middle of the outer end wall -- stands 0.4 mm proud of where the jaw finishes.
# The jaw landed on those after ANCHOR_DROP of travel, which made them the stop
# instead of the roof and gave up 0.4 mm of the 1.0 the screw is there to
# deliver. Cut as one channel rather than by capping each feature, so nothing
# added here later can grow back into it.
#
# JAW_CLEAR is how far BELOW the jaw's finishing height that channel floor sits,
# and it is deliberately generous rather than flush. Nothing locates on it -- it
# is not a fit surface -- so the only thing a deeper cut costs is a couple of
# millimetres off a tie that is 15 mm tall. Being tight there is not a tight fit
# but a silent one: the jaw lands on the tabs instead of the foot landing on the
# roof, and the preload goes missing with nothing to see. So it carries two
# printer tolerances rather than one, which also covers PETG flexing under load
# and the anchor sitting a touch high on its tower.
#
# The ROOF is deliberately NOT treated this way. It is the one surface on this
# part that has to be at a designed height -- it is the preload datum, and
# pulling it back would not protect anything, it would just quietly add travel.
JAW_CLEAR = 0.0        # ...and now zero, which is what makes the anchor's top
                       # FLUSH. With SEAT_GAP zero the yoke's whole underside --
                       # jaw and foot alike -- is one plane, so the anchor's top
                       # can be one plane too and there is no second surface to
                       # clear. Nothing can become the wrong stop when there is
                       # only one. It also stops the top face reading as a
                       # stepped notch, and hands the joint a lot more bearing
                       # area than the boss had on its own.
                       #
                       # Kept as a name because it stops being zero the moment
                       # SEAT_GAP does: put 0.4 back on the yoke and the jaw
                       # drops below the foot again, and this is what has to
                       # cover it.
LID_T = 1.0            # lid over the anchor's pocket, so the assembled joint is
                       # not a hole to look down. Cosmetic, and it costs nothing
                       # structurally, but it is the one feature that reaches
                       # over the tower -- see LID_CLEAR.
_jaw_sweep = _jaw_z0 - SEAT_ERROR - SEAT_GAP - ANCHOR_DROP - JAW_CLEAR
# How much air the lid leaves over the tower's measured top. Not a design knob --
# a derived number worth printing, because it is the only claim this part makes
# about what stands up from a tower nobody has photographed clearly.
LID_CLEAR = (_jaw_sweep - LID_T) - TOWER_H
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
# The foot runs from here out to the yoke's own end face rather than sitting
# symmetrically about the screw. Symmetric left a 0.25 mm step short of the end
# -- nothing structural, but the outer face reads better carried straight
# through, and the extra 0.25 is free bearing area on the anchor's roof.
_foot_x0 = _screw_x - 5.0
_foot_x1 = _cap_x1
_boss_in = _jaw_hw + FIT       # boss clears the jaw; it is above the tower now
_boss_z0 = _anchor_z1 - INSERT_L - 1.5   # underside of the boss, and where the
                       # insert bore breaks out: INSERT_L of insert plus 1.5 of
                       # clear hole beneath it for the melt to escape into.
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
            s * _foot_x0, s * _foot_x1,
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
        part += Pos(s * (_foot_x0 + _foot_x1) / 2, 0, 0) * extrude(
            _wedge, amount=(_foot_x1 - _foot_x0) / 2, both=True)
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
    # A lid over the pocket. Not structural -- it is there because with the yoke
    # screwed down you would otherwise look through the 0.2 mm of clearance
    # either side of the jaw into a 3.3 mm well with the tower at the bottom,
    # which reads as a hole rather than as a joint.
    #
    # It sits at the floor of the jaw's channel, i.e. as high as it can go
    # without the jaw ever reaching it, so what shows through the clearance is
    # solid plastic half a millimetre down instead of a shadow. That also keeps
    # it clear of the thing the original design was avoiding: a roof at the
    # anchor's own roof height would have to cross whatever posts and latch arms
    # stand up from the tower, which no photograph has shown clearly. This one
    # leaves LID_CLEAR above the tower's measured top, and the yoke's own jaw
    # already passes closer than that, so it assumes nothing new.
    #
    # Printing roof-down it is a bridge between the two flanks, 7.4 mm across and
    # starting LID_T off the bed, with both ends anchored. That prints.
    # Two strips, not one slab: the card's END passes through this pocket -- the
    # towers stand 3.75 mm proud of the card's ends -- so the lid has to carry
    # the same slot the tie tabs do, or it saws straight through the card.
    for f in (-1, 1):
        block += _slab(_cap_x0, SOCKET_L / 2 + FIT,
                       f * _tie_hw, f * _grip_hw,
                       _jaw_sweep - LID_T, _jaw_sweep)
    # Boss under the screw, since the roof alone is thinner than the thread.
    boss = _slab(
        _foot_x0, _foot_x1,
        CAP_SIDE * _boss_in, _foot_y,
        _boss_z0, _anchor_z1,
    )
    # ...notched for the tower. The boss's inner face is at _boss_in, which is
    # 0.7 mm INSIDE the tower's flank -- that was free while the roof stood clear
    # above the tower, and SEAT_ERROR has since dropped the roof past its top.
    # So cut the tower out of the boss and let the boss be locally thinner where
    # it passes. It costs nothing: the insert bore sits 0.5 mm further out again,
    # and below the cut the flank wall is already there to carry the load.
    #
    # The cut is deliberately made against the BOSS ONLY, not the whole anchor.
    # Subtracting a FIT-oversize tower from the flanks would open the pocket to
    # 2 x 4.05 and destroy the 0.15/flank interference that holds this part on.
    boss -= _slab(_cap_x0 - 1, SOCKET_L / 2 + 1,
                  -(TOWER_Y / 2 + FIT), TOWER_Y / 2 + FIT,
                  _anchor_z0 - 1, TOWER_H + FIT)
    block += boss
    # The channel the yoke's jaw sweeps through. Takes the tops off both tie tabs
    # and the middle of the end wall; leaves all three full height outboard of
    # the jaw, which is where the flanks are and where the tying actually
    # happens. The boss starts at exactly the channel's edge, by construction --
    # _boss_in is the same _jaw_hw + FIT -- so it is untouched.
    block -= _slab(_cap_x0 - CAP_WALL - 1, _cap_x1 + 1,
                   -(_jaw_hw + FIT), _jaw_hw + FIT,
                   _jaw_sweep, _anchor_z1 + 10)
    # Insert bore, and it goes STRAIGHT THROUGH the boss rather than stopping
    # short. It used to be a blind hole 0.8 mm deeper than the insert, on the
    # theory that 0.8 mm was somewhere for displaced plastic to go. It is not:
    # setting a brass insert with an iron pushes a surprising volume of melt
    # ahead of it, a blind hole packs solid, and the insert then either stops
    # high or splits the boss -- which is one insert already lost. Through, the
    # melt has the whole hole and then open air, the insert seats on nothing but
    # its own knurl, and there is 17 mm of clear space under the boss for
    # anything that runs out. A screw a size too long is harmless too.
    block -= Pos(_screw_x, _screw_y, (_boss_z0 - 1 + _anchor_z1 + 1) / 2) * Cylinder(
        INSERT_D / 2, (_anchor_z1 + 1) - (_boss_z0 - 1)
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


# --- Card components. TRM "VRAM [2M] PCB ASSEMBLY", drg 0197,004/A. ---------
# Context, like card() and socket() -- but not decoration: these are what
# CLEAR_END is spending its margin against, so they are measured rather than
# sketched, and the report below checks the printed parts against them.
#
# The drawing is 1:1. It was rendered at 600 dpi and every figure here is the
# centre of one of its outlines, scaled so the card outline it draws
# (27.90 x 102.74) maps onto the 28.0 x 102.87 of Fig 2.18 -- the scan is true
# to 0.35 %, and dividing that out costs nothing.
#
# Two datums, both of which the drawing gives directly:
#   u  mm along the card, from the end the drawing puts C12 and IC24 at
#   v  mm DOWN from the card's top edge -- the edge the TSOPs sit flush with
#
# Side A is the 6.5 mm envelope (TSOPs, electrolytics, beads); side B is the
# 4.00 mm one (TSOPs and chip caps only). The 1M card, drg 0197,003/A, is this
# card with side B bare and nothing else changed -- set POPULATE_B False.
POPULATE_B = True
CARD_FLIP = True       # OBSERVED on the machine: the card sits with side A --
                       # the electrolytics -- facing the VIDC20, which is +Y.
                       # The TRM assembly drawing was transcribed the other way
                       # up, so the whole card assembly turns 180 degrees about
                       # Z to match.
                       #
                       # A turn, NOT a mirror: that is the only way a card can
                       # actually go in, and it swaps which END sits at which
                       # tower as well as which face points where. Nothing about
                       # the retainer changes -- the jaws are symmetric and
                       # CLEAR_END already takes the tighter face at each end --
                       # but the report's side A / side B stack heights swap
                       # over, and so does which end of the drawing is at the
                       # C73 tower.

# The VRAM itself: HM538253BTT/HM538254BTT, 2 Mbit dual-port video RAM, 44-pin
# TSOP-II (TTP-44/40DA) -- body 18.41 x 10.16 x 1.20 max, 0.10 standoff, leads
# out to an 11.76 span. Eight of them are the 2M card's 16 Mbit.
#
# The drawing's outline is the LAND PATTERN, 19.1 x 13.2, which is 0.7 wider
# each side than the leads actually reach. Checking the jaw against that would
# throw away 0.7 mm of real clearance at each end, so the model uses the
# datasheet body and lead span and the outline only for position.
TSOP_L, TSOP_W, TSOP_H = 18.41, 10.16, 1.20   # across the card, along it, tall
TSOP_LEAD = 11.76          # lead span, along the card
TSOP_STAND = 0.10          # standoff under the body
# 47uF SMD aluminium electrolytics. The drawn outline is 6.74 along the card by
# 7.90 across, chamfered at one end with a "+" beside it: a 6.3 mm can whose
# terminals run ACROSS the card, which is why the can models are spun 90 deg.
# 6.3 x 5.4 is the tallest 6.3 mm case that stays inside the TRM's 6.5 envelope.
CAN_D, CAN_H = 6.3, 5.4
# L1-L4. The one population the drawing does not identify: a 9.35 x 2.92
# outline, long axis across the card, in the supply to each side-A VRAM -- so,
# ferrite beads. Height is ASSUMED; nothing else here is.
BEAD_X, BEAD_Z, BEAD_H = 2.92, 9.35, 2.0
# C1-C8 and C13-C16, decoupling. Drawn as ref-des boxes of a fixed ~4 x 3.3
# rather than as lands, so only the centre and the long axis are readable off
# them; 1206 is the size that fits the boxes and the era.
CHIP_L, CHIP_W, CHIP_H = 3.2, 1.6, 1.3

# (u, side). Every TSOP is flush with the top edge -- drawn 19.1 deep from
# v = 0.13 on both sides -- so v is one number for all eight.
TSOP_V = 9.70
_TSOPS = [(24.20, "A"), (45.99, "A"), (67.73, "A"), (89.22, "A"),    # IC4 2 3 1
          (13.38, "B"), (35.04, "B"), (56.97, "B"), (78.54, "B")]    # IC24 22 23 21
_CANS = [(13.29, "A"), (35.07, "A"), (56.86, "A"), (78.60, "A")]     # C12 11 10 9
CAN_V = 4.58
_BEADS = [(13.33, "A"), (35.16, "A"), (56.86, "A"), (78.48, "A")]    # L4 3 2 1
BEAD_V = 16.10
_CHIPS = [  # (u, v, side, spin) -- spin 90 puts the chip's length across the card
    (23.63, 20.25, "A", 0), (45.42, 20.25, "A", 0),                  # C4 C3
    (67.12, 20.18, "A", 0), (88.65, 20.22, "A", 0),                  # C2 C1
    (14.64, 20.22, "B", 0), (36.46, 20.22, "B", 0),                  # C8 C7
    (58.18, 20.22, "B", 0), (79.84, 20.22, "B", 0),                  # C6 C5
    (23.06, 2.63, "B", 90), (44.86, 3.25, "B", 90),                  # C16 C15
    (67.87, 3.29, "B", 90), (87.98, 3.33, "B", 90),                  # C14 C13
]
# Not modelled: the item-8 label on side A, 14.94 x 5.93 at u 96.3-102.3. It is
# paper, and it is the one thing that reaches into a jaw's end zone -- its edge
# lands within 0.05 mm of the jaw's inner face. GAP is 0.30 per face and the
# label is ~0.1 thick, so the jaw rides over it; worth knowing, not worth a solid.

# KiCad ships exact 3D models for three of these four packages, and this machine
# has them. Where the library is found they are used verbatim; where it is not,
# each falls back to a block built to the same datasheet numbers, so the model
# runs anywhere and the clearance check is unchanged either way. KiCad's
# convention is the one wanted here: origin at the footprint centre, part
# sitting on z = 0, +Z out of the board.
_KICAD = next((p for p in (
    Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels"),
    Path("/usr/share/kicad/3dmodels"),
    Path.home() / ".local/share/kicad/3dmodels",
) if p.is_dir()), None)


@lru_cache(maxsize=None)
def _package(rel: str | None) -> Part | None:
    """One KiCad 3D package, imported once and reused. None if unavailable."""
    if rel is None or _KICAD is None:
        return None
    try:
        return import_step(str(_KICAD / rel))
    except Exception as exc:
        print(f"  note: {rel} would not import ({exc.__class__.__name__}); using a block")
        return None


def _tsop() -> Part:
    return _package("Package_SO.3dshapes/TSOP-II-44_10.16x18.41mm_P0.8mm.step") or (
        Pos(0, 0, 0.15) * Box(TSOP_LEAD, TSOP_L, 0.30)
        + Pos(0, 0, TSOP_STAND + TSOP_H / 2) * Box(TSOP_W, TSOP_L, TSOP_H)
    )


def _can() -> Part:
    return _package("Capacitor_SMD.3dshapes/C_Elec_6.3x5.4.step") or (
        Pos(0, 0, 0.15) * Box(7.8, 6.6, 0.30)
        + Pos(0, 0, CAN_H / 2) * Cylinder(CAN_D / 2, CAN_H)
    )


def _chip() -> Part:
    return _package("Capacitor_SMD.3dshapes/C_1206_3216Metric.step") or (
        Pos(0, 0, CHIP_H / 2) * Box(CHIP_L, CHIP_W, CHIP_H)
    )


def _bead() -> Part:
    return Pos(0, 0, BEAD_H / 2) * Box(BEAD_X, BEAD_Z, BEAD_H)


def _on_card(part: Part, u: float, v: float, side: str, spin: float = 0.0) -> Part:
    """Stand a component on one face of the card. It arrives in KiCad's frame --
    on z = 0, +Z out of the board -- and is tipped so that +Z becomes the card's
    outward normal: -Y for side A, +Y for side B."""
    return (
        Pos(u - CARD_L / 2, (CARD_T / 2) * (1 if side == "B" else -1), CARD_FREE - v)
        * Rot(-90 if side == "B" else 90, 0, 0)
        * Rot(0, 0, spin)
        * part
    )


def components() -> dict[str, Part]:
    """The card's population, grouped by type so each shows in its own colour.
    Fit checking and display only -- never exported."""
    def group(items):
        out = None
        for p in items:
            out = p if out is None else out + p
        return out

    on_b = POPULATE_B
    turn = Rot(0, 0, 180 if CARD_FLIP else 0)
    return {k: turn * v for k, v in {
        "VRAM": group([_on_card(_tsop(), u, TSOP_V, s)
                       for u, s in _TSOPS if s == "A" or on_b]),
        "electrolytics": group([_on_card(_can(), u, CAN_V, s, spin=90)
                                for u, s in _CANS]),
        "beads": group([_on_card(_bead(), u, BEAD_V, s) for u, s in _BEADS]),
        "chip caps": group([_on_card(_chip(), u, v, s, spin=sp)
                            for u, v, s, sp in _CHIPS if s == "A" or on_b]),
    }.items()}


# --- The motherboard around SK9. TRM "MAIN PCB ASSEMBLY", drg 0197,000/A. ---
# Context, and one answer: this drawing settles the measurement HANDOVER.md has
# been carrying as the last open question -- whether there is board beside a
# tower for the screw boss. See the report at the bottom; the short version is
# that one tower has it and the other does not.
#
# Like the card drawing, this one is 1:1 -- SK9 is drawn 110.62 long against the
# 110.36 measured with calipers, and IC29 comes out 27.69 x 27.81 against the
# 28 x 28 of a 160-pin PQFP. Rendered at 600 dpi and measured the same way.
#
# Frame: the drawing's own, so a view down -Z reproduces the drawing. +X runs
# along the socket toward the end the drawing puts on the right (C151, C36,
# LK13); +Y is CAP_SIDE, the VIDC/RP14 flank; the board's top face is the
# motherboard datum at z = -SOCKET_H.
BOARD_T = 1.6              # FR4, nominal -- the drawing is a plan view
BOARD_X, BOARD_Y0, BOARD_Y1 = 88.0, -32.0, 38.0   # the window modelled

# SK9's own plan outline, which is NOT the 6.5 the calipers gave for its body.
# The calipers spanned the moulding around the card slot, up where the anchor
# grips; the drawing is the whole footprint, flanges and all. Both are true and
# the difference matters here, because clearance to a neighbour is measured from
# the footprint, not from the part the anchor touches.
SOCKET_PLAN_W = 9.86
# And how little there is past its ends. C151 and R213 stand this far off the
# right end; C73 is 1.14 off the left. The anchors' outer end walls want 1.40.
SOCKET_PLAN_END = 0.30
# Which is worth stating on its own: the anchor is 9.80 across, so it is very
# slightly NARROWER than the socket's own footprint. Nothing about the anchor's
# flanks can foul the board that the socket does not foul already. Only the
# screw boss reaches past, out to |Y| = 9.09.

# Neighbours, as (ref, X, Y, along X, along Y) -- the centre and size of each
# outline the drawing draws, for everything within about 62 x 22 mm of SK9.
# HEIGHTS ARE NOT IN THIS DRAWING. It is a plan view, so these are extruded to
# one nominal depth and are keep-out prisms for PLAN clearance only; the report
# below measures in plan and says so. A part could be 3 mm tall and irrelevant
# at the boss's height (18.3 to 23.8 above the board) or 20 mm and fatal, and
# nothing here can tell you which.
NEIGHBOUR_H = 4.0
_NEIGHBOURS = [
    # +Y -- the VIDC flank, the one CAP_SIDE puts the screw boss on
    ("SK4",  -58.75,  15.12, 55.39, 11.39),
    ("R148", -32.26,   7.56,  2.41,  1.35),
    ("C91",  -22.31,  10.03,  4.70,  6.56),
    ("C99",  -17.21,   7.54,  1.78,  3.17),
    ("IC29",   1.72,  22.78, 27.69, 27.81),   # VIDC20, 160-pin PQFP
    ("C118",  16.30,   6.27,  3.17,  1.91),
    ("R184",  20.70,   6.86,  1.40,  2.75),
    ("RP14",  27.05,  11.35,  5.21, 10.79),
    ("RP15",  40.26,  11.35,  5.21, 10.79),
    ("R213",  56.92,   6.69,  2.88,  5.46),
    ("C36",   61.13,   1.91,  4.70,  3.34),
    # -Y -- the flank carrying the SO packages
    ("LK5",  -59.90,  -5.00,  2.16,  2.16),
    ("RP6",  -58.63, -12.57,  5.21, 10.71),
    ("IC22", -42.19, -12.62,  7.28, 12.32),
    ("C83",  -33.42,  -8.21,  1.78,  3.17),
    ("C84",  -33.42, -17.02,  1.78,  3.09),
    ("IC26", -25.40, -12.62,  7.24, 12.32),
    ("RP11", -12.76, -12.62,  5.33, 10.79),
    ("C107",  -5.19,  -8.25,  1.86,  3.26),
    ("C108",  -4.55, -17.70,  1.86,  3.17),
    ("IC30",   4.30, -12.64,  7.28, 12.28),
    ("C115",  13.12,  -6.33,  3.17,  1.78),
    ("RP13",  18.18, -12.64,  5.25, 10.75),
    ("C126",  25.80, -16.43,  1.69,  3.17),
    ("IC33",  34.59, -12.62,  7.24, 12.32),
    ("C142",  43.43,  -6.29,  3.17,  1.86),
    ("RP16",  51.05, -12.62,  5.21, 10.79),
    ("C160",  59.25, -10.73,  1.78,  3.13),
    ("SK6",   -8.23, -25.32,115.24,  9.77),
    # off the right end, which is why there is nothing to grip out there
    ("C151",  56.92,   0.11,  2.88,  5.84),
]
# KiCad packages for the neighbours whose drawn outline matches a standard body.
# This drawing draws BODIES, not land patterns -- IC29 comes out 27.69 x 27.81
# against a 28 x 28 PQFP and SK9 110.62 x 9.86 against its measured 110.36 -- so
# a body that matches to half a millimetre is a real identification rather than a
# guess, which is why these are assigned and the other seven are not.
#
# What this buys is HEIGHT, which the drawing does not have. Read the warning on
# NEIGHBOUR_H before believing any of it: a KiCad model's height is that
# package's nominal, not this board's part. It matters most for C152, which
# decides the right tower, and it is exactly the kind of number that a caliper
# settles in ten seconds and a library cannot settle at all -- KiCad's D10 can is
# 10 mm tall and real 10 mm cans run to 20.
_SO20 = "Package_SO.3dshapes/SOIC-20W_7.5x12.8mm_P1.27mm.step"
_SO16 = "Package_SO.3dshapes/SOIC-16W_5.3x10.2mm_P1.27mm.step"
_CHIPC = "Capacitor_SMD.3dshapes/C_1206_3216Metric.step"
_CHIPR = "Resistor_SMD.3dshapes/R_1206_3216Metric.step"
_CAN10 = "Capacitor_THT.3dshapes/CP_Radial_D10.0mm_P5.00mm.step"
_PACKAGE = {
    "C73": _CAN10, "C152": _CAN10,          # radial electrolytics, drawn as circles
    "IC29": "Package_QFP.3dshapes/PQFP-160_28x28mm_P0.65mm.step",   # VIDC20
    "IC22": _SO20, "IC26": _SO20, "IC30": _SO20, "IC33": _SO20,     # 7.3 x 12.3
    "RP6": _SO16, "RP11": _SO16, "RP13": _SO16,                     # 5.2 x 10.8
    "RP14": _SO16, "RP15": _SO16, "RP16": _SO16,
    "C83": _CHIPC, "C84": _CHIPC, "C99": _CHIPC, "C107": _CHIPC,
    "C108": _CHIPC, "C115": _CHIPC, "C118": _CHIPC, "C126": _CHIPC,
    "C142": _CHIPC, "C160": _CHIPC,
    "R148": _CHIPR, "R184": _CHIPR,
}
# Left as prisms, because nothing standard is 5.2 x 10.8 or 55 x 11 and inventing
# a package would be worse than admitting the height is unknown: SK4, SK6, LK5,
# C91, C36 -- and C151 and R213, which is a pity, because those two are what the
# anchors' end walls run into.

# The two radial electrolytics, as (ref, X, Y, diameter). C73 is the one the
# HANDOVER already knew about: it stands off the socket's LEFT end, and the
# drawing puts it 1.0 mm away rather than the 3.3 scaled off a photograph.
_ROUND = [("C73", -61.83, 2.14, 11.01), ("C152", 54.19, 12.57, 9.86)]


def board() -> Part:
    """The motherboard local to SK9. Fit checking and display only."""
    return _slab(-BOARD_X, BOARD_X, BOARD_Y0, BOARD_Y1,
                 -SOCKET_H - BOARD_T, -SOCKET_H)


def _neighbour_parts() -> dict[str, Part]:
    """Each neighbour as its own solid, keyed by reference. A KiCad package where
    the outline identifies one, a keep-out prism where it does not."""
    z0 = -SOCKET_H                      # the board's top face
    out = {}
    for ref, X, Y, w, h in _NEIGHBOURS + [(r, X, Y, d, d) for r, X, Y, d in _ROUND]:
        pkg = _package(_PACKAGE.get(ref))
        if pkg is None:
            out[ref] = _slab(X - w / 2, X + w / 2, Y - h / 2, Y + h / 2,
                             z0, z0 + NEIGHBOUR_H)
            continue
        # The package arrives in KiCad's frame -- on z = 0, +Z out of the board,
        # any through-leads below it. Spun a quarter turn when its footprint is
        # the other way up from the outline the drawing gives, which is decided
        # by comparing which way round each is longer rather than by hand.
        bb = pkg.bounding_box()
        spin = 0 if (w >= h) == (bb.size.X >= bb.size.Y) else 90
        spun = Rot(0, 0, spin) * pkg
        # ...and centred on its OWN bounds rather than dropped on its origin. A
        # KiCad model's origin is the footprint's, which for the two-pad radial
        # cans is a pad and not the middle -- C73 landed 2.5 mm out before this.
        # The drawing gives body centres, so match body centres.
        c = spun.bounding_box().center()
        out[ref] = Pos(X - c.X, Y - c.Y, z0) * spun
    return out


def neighbours() -> Part:
    """What is on the board beside the socket."""
    part = None
    for p in _neighbour_parts().values():
        part = p if part is None else part + p
    return part


def _fouls(printed: Part):
    """Which neighbours the printed parts run into, and by how much. Per part, so
    the answer names the component; bounding boxes screen first so only the few
    that can possibly touch cost a boolean.

    This is a real 3D check for the 25 neighbours that carry a KiCad package and
    a plan check for the seven that do not, since those are prisms of an invented
    height. The report says which is which rather than pretending otherwise."""
    pb = printed.bounding_box()
    out = []
    for ref, part in _neighbour_parts().items():
        bb = part.bounding_box()
        if (bb.min.X > pb.max.X or bb.max.X < pb.min.X
                or bb.min.Y > pb.max.Y or bb.max.Y < pb.min.Y
                or bb.min.Z > pb.max.Z or bb.max.Z < pb.min.Z):
            continue
        try:
            hit = printed & part
        except Exception:
            continue
        if hit.volume > 1e-6:
            h = hit.bounding_box()
            out.append((ref, h.size.X, h.size.Y, hit.volume, ref in _PACKAGE))
    out.sort(key=lambda t: -t[3])
    return out


def _plan_clearance():
    """For each tower and each flank, the nearest neighbour OUTLINE to SK9's
    footprint, in plan. Bounding boxes throughout, so a round part is measured
    at its square -- pessimistic, which is the right way to be wrong here."""
    edge = SOCKET_PLAN_W / 2
    boxes = [(r, X - w / 2, X + w / 2, Y - h / 2, Y + h / 2)
             for r, X, Y, w, h in _NEIGHBOURS]
    boxes += [(r, X - d / 2, X + d / 2, Y - d / 2, Y + d / 2) for r, X, Y, d in _ROUND]
    out = {}
    for end, x0, x1 in (("left", -SOCKET_L / 2, -SOCKET_L / 2 + TOWER_X),
                        ("right", SOCKET_L / 2 - TOWER_X, SOCKET_L / 2)):
        for flank, sign in (("+Y", 1), ("-Y", -1)):
            best, who = 99.0, "nothing"
            for r, bx0, bx1, by0, by1 in boxes:
                if bx1 < x0 or bx0 > x1:
                    continue
                near = by0 if sign > 0 else -by1
                if near < edge:            # straddles the socket -- not a flank
                    continue
                if near - edge < best:
                    best, who = near - edge, r
            out[end, flank] = (best, who)
    return out


# Colours for the viewer. The printed parts share one filament colour so they
# read as the one assembly; the card is board green and the socket is the black
# of the real SK9 moulding. The TSOPs are black plastic too, but a real black
# against a black socket is unreadable on screen, so they are lifted a couple of
# shades -- the only colour here that is chosen for legibility over likeness.
COLOURS = {
    "yoke": "#d98a2b", "anchor R": "#d98a2b", "anchor L": "#d98a2b",
    "card": "#1e7a3c", "socket": "#141416",
    "VRAM": "#33333a", "electrolytics": "#42424a",
    "beads": "#55555e", "chip caps": "#b99a6b",
    "board": "#0d4423", "neighbours": "#3a3a42",
}


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
    _travel = SEAT_GAP + ANCHOR_DROP
    _anch = parts["anchor_right"] + parts["anchor_left"]
    _checks = [(d, ((Pos(0, 0, -d) * parts["yoke"]) & _anch).volume)
               for d in (SEAT_ERROR, SEAT_ERROR + _travel)]
    print(f"seating    card top measured {CARD_SEATED} above the socket, "
          f"{CARD_FREE - CARD_SEATED:+.1f} on the model; SEAT_ERROR {SEAT_ERROR:.1f} off the "
          f"anchor's roof puts it back under the yoke, and the grip is untouched at "
          f"{CARD_SEATED - (_jaw_z0 - SEAT_ERROR):.1f} mm because both moved together")
    print(f"           anchor roof {_jaw_z0 - 0.6 - _anchor_z1:.1f} mm lower than the first "
          f"print ({SEAT_ERROR:.1f} of card + {ANCHOR_DROP - 0.6:.1f} "
          f"of SEAT_GAP moved off the yoke), so the anchor is that much shorter")
    print(f"           yoke vs anchors: "
          + ",  ".join(f"{'seated' if i == 0 else 'preloaded'} {v:.2f} mm3"
                       for i, (d, v) in enumerate(_checks))
          + ("   CLEAR" if all(v < 1e-6 for _, v in _checks) else "   FOULING"))
    print(f"press fit  {2 * PRESS:.2f} mm interference across {TOWER_Y} of tower, "
          f"over 2 x {TOWER_X * _grip_h:.0f} mm2 of flank")
    print(f"           sticks out {_cap_hw - 3.25:.2f} mm past the socket body, "
          f"both flanks (the screw boss needs {abs(_foot_y) - 3.25:.2f} on one)")
    print(f"anchor U   {2 * _cap_hw:.2f} mm across, pocket {2 * _grip_hw:.2f} "
          f"onto a {TOWER_Y} tower, lidded {LID_CLEAR:.2f} above its top "
          f"(the jaw itself comes to {_jaw_z0 - SEAT_ERROR - SEAT_GAP - ANCHOR_DROP - TOWER_H:.2f})")
    print(f"stands     {top_h:.1f} mm above the motherboard "
          f"({CARD_H - CARD_SUNK + SOCKET_H:.1f} for the bare card)"
          if (top_h := CARD_FREE + BAR_H + SOCKET_H) else "")

    # What the components are here for. CLEAR_END was picked off photographs at
    # "~8 mm side A, ~7 mm side B"; the assembly drawing says 6.74 at one end and
    # 7.08 at the other, and the two are on OPPOSITE faces -- so the jaws have to
    # clear the tighter of the pair at each end whichever way round the card goes.
    # Checked as a boolean against the real packages rather than against the
    # drawing's land outlines, which are 0.7 mm/side wider than the leads reach.
    comps = components()
    printed = parts["yoke"] + parts["anchor_right"] + parts["anchor_left"]
    every = None
    for grp in comps.values():
        every = grp if every is None else every + grp
    try:
        fouled = (printed & every).volume
    except Exception:
        fouled = 0.0
    boxes = [s.bounding_box() for grp in comps.values() for s in grp.solids()]
    reach = max(max(abs(bb.min.X), abs(bb.max.X)) for bb in boxes)
    print(f"components {len(boxes)} on the card "
          f"(drg 0197,004/A" + ("" if POPULATE_B else ", side B bare") + f"), "
          f"{'KiCad packages' if _KICAD else 'datasheet blocks'}")
    print(f"           nearest reaches X {reach:.2f}; the jaws start at "
          f"{_jaw_x0:.2f}, so {_jaw_x0 - reach:.2f} mm to spare -- "
          f"{'CLEAR the card' if fouled < 1e-6 else f'FOULING {fouled:.1f} mm3'}")
    _upY = max(bb.max.Y for bb in boxes) - CARD_T / 2
    _dnY = max(-bb.min.Y for bb in boxes) - CARD_T / 2
    print(f"           side A faces {'+Y, the VIDC20' if CARD_FLIP else '-Y'}; stack "
          + ",  ".join(f"{f} {h:.2f} vs the TRM's {e}" for f, h, e in (
              ("A", _upY if CARD_FLIP else _dnY, 6.5),
              ("B", _dnY if CARD_FLIP else _upY, 4.00)))
          + " -- envelope, not clearance: the jaws never cross the card's faces")

    # The board beside the socket -- the last open measurement in HANDOVER.md.
    # Plan only: the assembly drawing has no heights, so this says where there is
    # board, not how much air there is at the boss's own height.
    gaps = _plan_clearance()
    need = abs(_foot_y) - SOCKET_PLAN_W / 2
    _n = len(_NEIGHBOURS) + len(_ROUND)
    _pkg = sum(1 for r in _neighbour_parts() if r in _PACKAGE)
    print(f"board      drg 0197,000/A, {_n} neighbours -- {_pkg} as KiCad packages "
          f"(real heights, nominal ones), {_n - _pkg} as prisms (height invented); "
          f"SK9's footprint is {SOCKET_PLAN_W} across, not the {2 * 3.25} the "
          f"calipers gave for its body")
    print(f"           anchor flanks {2 * _cap_hw:.2f} -- inside that footprint, so only "
          f"the boss reaches past it, by {need:.2f} mm")
    for end in ("left", "right"):
        cells = []
        for flank in ("+Y", "-Y"):
            mm, who = gaps[end, flank]
            cells.append(f"{flank} {mm:5.2f} ({who})"
                         + (" OK" if mm >= need else " NO"))
        print(f"           {end:5s} tower  " + "   ".join(cells))
    print(f"           so the boss goes on the LEFT tower and the RIGHT one has "
          f"nowhere in plan -- but heights are unknown, see the comment")
    fouls = _fouls(printed)
    if fouls:
        print("           the anchors' OUTER END WALLS also hit: "
              + ",  ".join(f"{r} by {dx:.2f}" + ("" if pkg else " [prism]")
                           for r, dx, dy, v, pkg in fouls))
        _small = [(r, w - b.size.X, h - b.size.Y)
              for r, X, Y, w, h in _NEIGHBOURS + [(r, X, Y, d, d) for r, X, Y, d in _ROUND]
              if r in _PACKAGE and (b := _neighbour_parts()[r].bounding_box())
              and (w - b.size.X > 0.3 or h - b.size.Y > 0.3)]
    if _small:
        print("           NOTE a package model smaller than the outline drawn hides "
              "fouls: " + ",  ".join(f"{r} by {max(dx, dy):.2f}" for r, dx, dy in _small)
              + " -- the plan table above uses the drawn size and is the one to trust")
    print(f"           each wants {_cap_x1 - SOCKET_L / 2:.2f} mm past the socket's "
              f"end and the drawing leaves {SOCKET_PLAN_END:.2f}. The anchor stands "
              f"{1.5} mm off the board, so this is only real for a part taller than that.")

    try:
        from ocp_vscode import show

        # The card, its population and the yoke are drawn SEATED -- dropped by
        # SEAT_ERROR onto where the card really sits -- while the anchors, socket
        # and board stay put. Without that the viewer shows the gap under the
        # yoke's foot as SEAT_GAP + ANCHOR_DROP + SEAT_ERROR and it looks far too
        # big, because the yoke is cut to a card height that turned out to be
        # 0.8 mm out. Seated, what you see is the 1.00 mm the screw pulls through.
        seated = Pos(0, 0, -SEAT_ERROR)
        shown = [("yoke", seated * parts["yoke"]),
                 ("anchor R", parts["anchor_right"]),
                 ("anchor L", parts["anchor_left"]), ("card", seated * card()),
                 ("socket", socket()), ("board", board()),
                 ("neighbours", neighbours()),
                 *((n, seated * g) for n, g in comps.items())]
        show(*[p for _, p in shown], names=[n for n, _ in shown],
             colors=[COLOURS[n] for n, _ in shown])
    except Exception as exc:
        print(f"viewer not connected ({exc.__class__.__name__})")
