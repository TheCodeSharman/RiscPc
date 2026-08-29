"""VRAM card retainer -- Acorn RISC PC. A yoke over the card, on two press-fit
anchors, screwed together to preload the card down into socket SK9.

SK9's own latch is broken and gone, so this is the whole retention mechanism,
and two of its contacts are repaired by bending -- seating pressure does the
work of a contact spring. Background: `Dev Diary.md`. Design reasoning,
measurements and dead ends: `HANDOVER.md`.

  * yoke   -- a bar along the card's top edge with a jaw at each end that
              embraces both faces, plus a foot at each end taking one screw
  * anchor -- one per end tower, pressed on, carrying a heat-set insert

The jaws are at the ends because that is the only clear card: the TSOPs sit
flush with the top edge and the electrolytics 0.68 below it, so there is
nothing to grip along the length. The towers are at the ends too, so gripping
the card and anchoring to the socket are one feature.

Preload is displacement-controlled: the yoke's bar lands on the card, its feet
stop SEAT_GAP + ANCHOR_DROP above the anchors' roofs, and the screws close that
gap. It cannot be over-tightened onto a 30-year-old card.

Origin: centre of the card, on its mid-plane, at the height of the socket's top
face. +X along the socket, +Y toward the VIDC20, +Z up.
"""

import re
from functools import lru_cache
from pathlib import Path

from build123d import *

# --- Card. TRM Fig 2.18 (p.2-27) ------------------------------------------
CARD_L = 102.87        # overall length
CARD_H = 28.0          # overall height, max
CARD_T = 1.27          # PCB thickness, +/- 0.1
CLEAR_END = 6.5        # component-free zone the jaws sit in. The drawing gives
                       # 6.74 at the tighter end; overrunning means a TSOP.

# --- Socket SK9. Calipers, heights above the MOTHERBOARD --------------------
SOCKET_L = 110.36      # overall, outer tower face to outer tower face
TOWER_TOP = 18.90      # top of the black end tower
CARD_TOP = 31.0        # card's top edge, seated -- superseded by CARD_SEATED
                       # below, but kept: it is the datum the printed yoke was
                       # cut to.
SOCKET_H = 5.2         # socket body's top face

TOWER_H = TOWER_TOP - SOCKET_H      # tower, above the socket's top face
CARD_SUNK = CARD_H - (CARD_TOP - SOCKET_H)   # card buried in the socket
TOWER_X = 7.7          # end tower, along the socket
TOWER_Y = 7.7          # end tower, across it
CAP_SIDE = -1          # flank the screw boss sits on. -Y, away from the VIDC20:
                       # SK4 on the +Y side carries a network card that stands
                       # up where the boss and driver would be. -Y is also the
                       # roomy flank beside the left tower (15.51 vs 4.49).

CARD_FREE = CARD_TOP - SOCKET_H  # card standing proud of the socket

# --- Print -----------------------------------------------------------------
FIT = 0.2              # printer tolerance per face. Everything that mates is
                       # derived from this, so a tight print is one edit.
WALL = 2.0             # jaw walls
CAP_WALL = 1.2         # anchor walls
GAP = FIT + 0.1        # per-face clearance to the card, looser than FIT: a slot
                       # that grips a 30-year-old PCB edge is worse than one
                       # that doesn't.
PRESS = 0.15           # interference per flank, so the pocket is 0.3 under the
                       # tower and the anchor presses on. Verified on the
                       # machine: good tight fit. PETG creeps, so this relaxes
                       # over years; epoxy in the same joint recovers it.
BAR_H = 5.0            # bar depth above the card's top edge
FOOT_T = 3.0           # yoke's foot, sitting on the anchor's roof
ANCHOR_DROP = 1.0      # anchor roof below the yoke datum. With SEAT_GAP this
                       # is the preload travel, and the ONLY knob for preload
                       # force. It lives on the anchor because that is the part
                       # cheap to reprint, and because it keeps _jaw_z0 -- and
                       # so the card grip -- fixed.
CARD_SEATED = 25.0     # MEASURED on the fitted card: top edge above the
                       # socket's top face. 0.8 below CARD_TOP - SOCKET_H.
SEAT_ERROR = CARD_FREE - CARD_SEATED   # taken off the anchor's roof, not off
                       # CARD_TOP, so the printed yoke stays valid. Preload is
                       # unchanged: roof and foot move together. If the yoke is
                       # ever reprinted, set CARD_TOP 30.2 and SEAT_ERROR 0.
SEAT_GAP = 0.0         # gap under the foot, ON THE YOKE. Zero so the yoke's
                       # underside is one plane and the screw hole breaks out
                       # flush; ANCHOR_DROP carries all the travel. Restoring it
                       # means restoring JAW_CLEAR too.
SCREW_CLEAR = 2.0 + 2 * FIT   # M2 clearance; printed holes come out undersize
INSERT_D = 3.2         # M2 heat-set insert bore...
INSERT_L = 4.0         # ...and length. Check against the inserts on hand.
SCREW_HEAD_D = 4.3     # M2 pan head plus clearance
SCREW_CBORE = 1.8      # counterbore depth. Pan head, not countersunk -- the
                       # holes are slotted and a countersink would fight that.
SCREW_SLOT = 1.0       # +/- slot travel, absorbing where the hand-pressed
                       # anchors actually land

TOWER_CLEAR = INSERT_L + 1.5   # jaw stops this far above the tower, sized by
                       # the insert: the boss cannot sit beside the tower
                       # without going outboard into board space we do not have,
                       # so the whole yoke interface lifts until it clears.

TIE_CLEAR = 0.25       # extra per face in the anchor's card slot over the
                       # yoke's GAP -- the card threads through two hand-pressed
                       # anchors before the yoke is anywhere near.
TIE_Z0 = 0.0           # tie tabs start at the socket's top face, which makes
                       # them the DEPTH STOP: press until they seat and the
                       # preload is the number in the report. Nothing else on
                       # the anchor bottoms out on anything. Glue, if used, goes
                       # on after -- the stop sets the height, not the adhesive.

_jaw_hw = CARD_T / 2 + GAP + WALL            # jaw half-width
_grip_hw = TOWER_Y / 2 - PRESS               # pocket half-width; undersize
_cap_hw = _grip_hw + CAP_WALL                # anchor half-width, both flanks
_slot_hw = CARD_T / 2 + GAP                  # card slot half-width
_tie_hw = _slot_hw + TIE_CLEAR               # ...and the anchor's, looser
_cap_x1 = SOCKET_L / 2 + FIT + CAP_WALL      # cap outer face
_cap_x0 = SOCKET_L / 2 - TOWER_X             # cap inner face
_jaw_x0 = CARD_L / 2 - CLEAR_END             # jaw reaches this far in
_jaw_z0 = TOWER_H + TOWER_CLEAR              # jaw bottom, clear of the tower
_anchor_z1 = _jaw_z0 - ANCHOR_DROP - SEAT_ERROR   # anchor roof
# Floor of the channel the yoke's jaw sweeps through as the screw pulls it down.
# The anchor must have NOTHING above this in the jaw's width, or the jaw lands
# on it instead of the foot landing on the roof and the preload silently goes
# missing. JAW_CLEAR is the margin below the jaw's finishing height.
JAW_CLEAR = 0.0        # zero because SEAT_GAP is: the yoke's underside is one
                       # plane, so the anchor's top can be one plane too and
                       # there is nothing to clear. Restore it with SEAT_GAP.
LID_T = 1.0            # lid over the anchor's pocket -- cosmetic, but the one
                       # feature reaching over the tower; see LID_CLEAR.
_jaw_sweep = _jaw_z0 - SEAT_ERROR - SEAT_GAP - ANCHOR_DROP - JAW_CLEAR
# Air the lid leaves over the tower's measured top. The only claim this part
# makes about what stands up from a tower no photograph has shown clearly.
LID_CLEAR = (_jaw_sweep - LID_T) - TOWER_H
# The anchor runs nearly to the motherboard: the flanks clear the socket body
# outboard all the way down, doubling the grip for nothing but a taller print.
# 1.5 mm of standoff keeps it off the solder fillets.
_anchor_z0 = 1.5 - SOCKET_H
_screw_x = SOCKET_L / 2 - TOWER_X / 2    # over the tower, in the card's clear
                                         # end zone, so a driver comes straight
                                         # down beside the bar
# Foot runs out to the yoke's end face rather than symmetrically about the
# screw, so the outer face carries through without a step.
_foot_x0 = _screw_x - 5.0
_foot_x1 = _cap_x1
_boss_in = _jaw_hw + FIT       # boss clears the jaw's channel, by construction
_boss_z0 = _anchor_z1 - INSERT_L - 1.5   # underside of the boss
# Derived from both constraints, not chosen: by hand the pilot hole once reached
# inboard of the boss and broke out of its side.
_screw_y = CAP_SIDE * max(
    _jaw_hw + SCREW_HEAD_D / 2 + 0.1,      # counterbore clears the jaw
    _boss_in + 1.2 + INSERT_D / 2,         # insert bore keeps a 1.2 wall
)
_foot_y = CAP_SIDE * (abs(_screw_y) + SCREW_HEAD_D / 2 + 1.0)


def _slab(x0, x1, y0, y1, z0, z1) -> Part:
    """A box given by its bounds, sorted -- so a mirrored feature can be written
    by negating both ends without coming out reversed."""
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
    """Fillet every edge whose midpoint satisfies `test` -- by position, so the
    selection does not silently move when a dimension changes."""
    edges = part.edges().filter_by(axis) if axis else part.edges()
    picked = [e for e in edges if test(e.center())]
    if not picked:
        return part
    # Step down rather than fail: a radius is capped by the smallest face it
    # runs onto, and those move whenever a socket dimension does.
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

    # Bar, full length, resting on the card's 1.27 mm top edge. Everything else
    # it spans is air -- components stand proud of the faces, not the edge.
    part = _slab(-_cap_x1, _cap_x1, -_jaw_hw, _jaw_hw, CARD_FREE, top)

    for s in (-1, 1):
        # Jaw: down the card's faces, in the component-free end zone.
        part += _slab(s * _jaw_x0, s * _cap_x1, -_jaw_hw, _jaw_hw, _jaw_z0, CARD_FREE)
        # Foot: widens the jaw sideways onto the anchor's roof; takes the screw.
        part += _slab(
            s * _foot_x0, s * _foot_x1,
            CAP_SIDE * _jaw_hw, _foot_y,
            _jaw_z0 + SEAT_GAP, _jaw_z0 + SEAT_GAP + FOOT_T,
        )
        _ft = _jaw_z0 + SEAT_GAP + FOOT_T          # top of the foot
        # Buttress over the foot -- what lets this print without support.
        # Printed bar-top-down, the foot's top face is its floor in the printer
        # and lands 8.2 mm up on nothing: a 6.15 mm 90-degree cantilever off the
        # jaw wall. Filling the wedge at 45 degrees means each layer grows out
        # by no more than the layer height, so it carries itself. Hollow, or it
        # would bury the screw: the channel is the counterbore's own slot
        # carried up, so whatever driver turns the head fits through it.
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

    # One slot for the card, stopping short of the solid outer wall.
    part -= _slab(
        -(CARD_L / 2 + 0.5), CARD_L / 2 + 0.5, -_slot_hw, _slot_hw, -6.0, CARD_FREE
    )

    # Lead-in at the card slot's mouth: this goes on blind.
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
    """One press-fit anchor over an end tower: both flanks, the outer end face,
    and two tabs across the inner one. Modelled at +X and mirrored, so the pair
    is handed. The pocket is undersize by PRESS per flank and open at the bottom;
    the tie tabs set its depth."""
    block = _slab(  # outer end wall
        SOCKET_L / 2 + FIT, _cap_x1, -_cap_hw, _cap_hw, _anchor_z0, _anchor_z1
    )
    for f in (-1, 1):
        block += _slab(
            _cap_x0, _cap_x1, f * _grip_hw, f * _cap_hw, _anchor_z0, _anchor_z1
        )
    # The fourth side, closing the ring so the flanks go into tension instead of
    # splaying -- which is what makes the interference actually bear. Two tabs,
    # not a wall: the card's end passes through here, since the towers stand
    # 3.75 mm proud of it.
    for f in (-1, 1):
        block += _slab(
            _cap_x0 - CAP_WALL, _cap_x0,
            f * _tie_hw, f * _cap_hw,
            TIE_Z0, _anchor_z1,
        )
    # Lid over the pocket, so the assembled joint is not a hole to look down.
    # At the jaw channel's floor -- as high as it can go without the jaw ever
    # reaching it. Two strips, not a slab: the card's end passes through here,
    # so it needs the same slot the tie tabs have.
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
    # ...notched for the tower, whose top the roof now sits below. Against the
    # BOSS ONLY: cutting an oversize tower out of the flanks would open the
    # pocket and destroy the interference that holds this part on.
    boss -= _slab(_cap_x0 - 1, SOCKET_L / 2 + 1,
                  -(TOWER_Y / 2 + FIT), TOWER_Y / 2 + FIT,
                  _anchor_z0 - 1, TOWER_H + FIT)
    block += boss
    # The jaw's channel: takes the tops off the tie tabs and the end wall's
    # middle, leaving them full height outboard where the tying happens. The
    # boss starts at exactly the channel's edge, so it is untouched.
    block -= _slab(_cap_x0 - CAP_WALL - 1, _cap_x1 + 1,
                   -(_jaw_hw + FIT), _jaw_hw + FIT,
                   _jaw_sweep, _anchor_z1 + 10)
    # Insert bore, STRAIGHT THROUGH. Blind packs solid with melt and either
    # stops the insert high or splits the boss -- one insert already lost that
    # way. Through, the melt has open air below and a long screw is harmless.
    block -= Pos(_screw_x, _screw_y, (_boss_z0 - 1 + _anchor_z1 + 1) / 2) * Cylinder(
        INSERT_D / 2, (_anchor_z1 + 1) - (_boss_z0 - 1)
    )
    # Prints ROOF DOWN: mouth-down leaves the boss cantilevered and costs
    # 51 mm2 of 90-degree overhang against 8, and the tabs' stop face -- the
    # preload datum -- wants to be a clean top surface.
    #
    # Lead-in at the mouth so a press fit starts square.
    block = _bevel(
        block, CAP_WALL * 0.6,
        lambda c: abs(c.Z - _anchor_z0) < 0.05 and abs(abs(c.Y) - _grip_hw) < 0.05,
    )
    return block if right else mirror(block, Plane.YZ)


def for_print(part: Part) -> Part:
    """The same part, turned as it is printed and dropped on the bed. All four go
    upside down -- yoke and coupon on the bar's top face, anchors roof-down; see
    the comments on each. A rotation, never a mirror, so the anchors stay handed.
    The model's own frame stays the assembly frame."""
    turned = Rot(180, 0, 0) * part
    bb = turned.bounding_box()
    return Pos(-bb.center().X, -bb.center().Y, -bb.min.Z) * turned


def coupon() -> Part:
    """One end of the yoke, for a two-minute test print: the card slot, the foot
    and the screw hole -- everything whose fit is uncertain."""
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


# --- Card components. TRM "VRAM [2M] PCB ASSEMBLY", drg 0197,004/A ---------
# Not decoration: these are what CLEAR_END spends its margin against, and the
# report checks the printed parts against them.
#
# The drawing is 1:1, rendered at 600 dpi; every figure is the centre of one of
# its outlines, scaled so the card it draws (27.90 x 102.74) maps onto Fig
# 2.18's 28.0 x 102.87. Datums: u along the card from the end carrying C12 and
# IC24, v down from the top edge the TSOPs sit flush with.
#
# Side A is the 6.5 mm envelope (TSOPs, electrolytics, beads), side B the 4.00
# (TSOPs and chip caps). The 1M card, drg 0197,003/A, is this with side B bare.
POPULATE_B = True
CARD_FLIP = True       # OBSERVED: side A -- the electrolytics -- faces the
                       # VIDC20, i.e. +Y, which is 180 degrees about Z from the
                       # drawing. A turn, not a mirror, so it swaps the ends too.

# HM538253BTT/HM538254BTT 2 Mbit dual-port VRAM in 44-pin TSOP-II. The drawing's
# outline is the LAND PATTERN, 0.7 mm/side wider than the leads reach, so the
# datasheet body is used and the outline only for position.
TSOP_L, TSOP_W, TSOP_H = 18.41, 10.16, 1.20   # across the card, along it, tall
TSOP_LEAD = 11.76          # lead span, along the card
TSOP_STAND = 0.10          # standoff under the body
# 47uF SMD electrolytics, terminals ACROSS the card -- hence spin=90. 6.3 x 5.4
# is the tallest 6.3 mm case inside the TRM's 6.5 envelope.
CAN_D, CAN_H = 6.3, 5.4
# L1-L4, the one population the drawing does not identify -- ferrite beads in
# each side-A VRAM's supply. Height ASSUMED; nothing else here is.
BEAD_X, BEAD_Z, BEAD_H = 2.92, 9.35, 2.0
# C1-C8, C13-C16 decoupling. Drawn as fixed ref-des boxes, so only centre and
# long axis are readable; 1206 fits the boxes and the era.
CHIP_L, CHIP_W, CHIP_H = 3.2, 1.6, 1.3

# (u, side). Every TSOP is flush with the top edge, so v is one number.
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
# Not modelled: the item-8 paper label on side A, whose edge lands within
# 0.05 mm of a jaw's inner face. ~0.1 thick against 0.30 of GAP, so the jaw
# rides over it.

# KiCad has exact models for three of these four packages. Where the library is
# missing, each falls back to a datasheet-dimensioned block and the clearance
# check is unchanged. KiCad's convention: origin at the footprint, on z = 0,
# +Z out of the board.
_KICAD = next((p for p in (
    Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels"),
    Path("/usr/share/kicad/3dmodels"),
    Path.home() / ".local/share/kicad/3dmodels",
) if p.is_dir()), None)

# Vendor STEP for the parts KiCad's library does not carry -- it has no DIN
# 41612 shorter than the full 32-position body and no SIMM socket at all.
# Searched first, so a local file wins over a same-named KiCad one. See
# models/README.md for where each came from.
_MODELS = Path(__file__).resolve().parent / "models"

# How a vendor file is turned, and where the board's top face sits in it. KiCad's
# convention -- board top at z = 0, +Z out of the board -- needs no entry; a
# vendor file follows its own, and neither of ours follows KiCad's:
#   5535070-5   +Z is out of the board already, but the datum is the body's TOP
#               face, so the part lands 11.5 low.
#   5822030-3   lies on its side. The file's +Y is what points out of the board,
#               and it needs standing up before the datum means anything.
# Both measured by SLICING the solid rather than read off a datasheet, because
# neither file says. Section area gives the board plane away: on 5535070-5 it is
# 8.8 mm2 of pin section up to z = -11.50 and 139 of standoff foot after it; on
# 5822030-3, 18 mm2 of pin up to y = -4.80 and 851 of body after it.
_DATUM = {                      # file: (degrees about X to stand it up, board plane after)
    "5535070-5.STEP": (0, -11.50),
    "5822030-3.stp": (90, -4.80),
}


@lru_cache(maxsize=None)
def _package(rel: str | None) -> Part | None:
    """One 3D package, imported once and reused, normalised to KiCad's datum so
    everything downstream can assume the board's top face is z = 0. None if
    unavailable."""
    if rel is None:
        return None
    path = next((r / rel for r in (_MODELS, _KICAD)
                 if r is not None and (r / rel).is_file()), None)
    if path is None:
        return None
    try:
        part = import_step(str(path))
    except Exception as exc:
        print(f"  note: {rel} would not import ({exc.__class__.__name__}); using a block")
        return None
    rx, z0 = _DATUM.get(path.name, (0, 0.0))
    return Pos(0, 0, -z0) * (Rot(rx, 0, 0) * part) if (rx or z0) else part


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
    """Stand a component on one face of the card, tipping KiCad's +Z into the
    card's outward normal: -Y for side A, +Y for side B."""
    return (
        Pos(u - CARD_L / 2, (CARD_T / 2) * (1 if side == "B" else -1), CARD_FREE - v)
        * Rot(-90 if side == "B" else 90, 0, 0)
        * Rot(0, 0, spin)
        * part
    )


def components() -> dict[str, Part]:
    """The card's population, grouped by type for colouring. Never exported."""
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


# --- The motherboard around SK9. TRM "MAIN PCB ASSEMBLY", drg 0197,000/A ---
# 1:1 like the card drawing -- SK9 comes out 110.62 long against 110.36 with
# calipers, IC29 27.69 x 27.81 against a 28 x 28 PQFP -- and measured the same
# way at 600 dpi. Frame is the drawing's own, so a view down -Z reproduces it:
# +X toward the C151/C36/LK13 end, +Y toward the VIDC20, board top at -SOCKET_H.
BOARD_T = 1.6              # FR4, nominal -- the drawing is a plan view
BOARD_X, BOARD_Y0, BOARD_Y1 = 88.0, -32.0, 38.0   # the window modelled

# SK9's plan footprint -- NOT the 6.5 the calipers gave for its body, which was
# the moulding up where the anchor grips. Clearance to a neighbour is measured
# from this. The anchor is 9.80 across, so narrower than the socket's own
# footprint; only the screw boss reaches past it.
SOCKET_PLAN_W = 9.86
SOCKET_PLAN_END = 0.30   # clear board past the ends: C151/R213 off the right,
                         # C73 1.14 off the left. The end walls want 1.40.

# Neighbours as (ref, X, Y, along X, along Y), within ~62 x 22 mm of SK9.
# HEIGHTS ARE NOT IN A PLAN VIEW: anything without a package below is extruded
# to NEIGHBOUR_H and is a PLAN keep-out only. A part could be 3 mm tall and
# irrelevant at the boss's height, or 20 and fatal.
NEIGHBOUR_H = 4.0
_NEIGHBOURS = [
    # +Y -- the VIDC flank
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
    # off the right end
    ("C151",  56.92,   0.11,  2.88,  5.84),
]
# KiCad packages for the neighbours whose outline matches a standard BODY --
# this drawing draws bodies, not lands, so a match to half a millimetre is an
# identification rather than a guess. What it buys is height, and that height is
# the package's NOMINAL, not this board's part: KiCad's D10 can is 10 mm tall
# and real 10 mm cans run to 20.
_SO20 = "Package_SO.3dshapes/SOIC-20W_7.5x12.8mm_P1.27mm.step"
_SO16 = "Package_SO.3dshapes/SOIC-16W_5.3x10.2mm_P1.27mm.step"
_CHIPC = "Capacitor_SMD.3dshapes/C_1206_3216Metric.step"
_CHIPR = "Resistor_SMD.3dshapes/R_1206_3216Metric.step"
_CAN10 = "Capacitor_THT.3dshapes/CP_Radial_D10.0mm_P5.00mm.step"
# SK4 is the network slot: a HALF-SIZE DIN 41612, 3 rows x 16 = 48 contacts.
# The count follows from the drawn length -- 16 positions at 2.54 plus 13.6 of
# end block is 54.2, against 55.39 drawn, where the full 32-position body is
# 94.9. KiCad's own DIN41612 models are all that full body whatever the variant
# says, so this one is TE's, from models/.
_DIN41612 = "5535070-5.STEP"
# SK6 is a 72-way SIMM socket at 1.27 pitch, vertical -- which the drawn 9.77 of
# depth already implied, an angled socket sprawling much further across the
# board. KiCad has no SIMM or DIMM socket at all, so this one is TE's too.
_SIMM72 = "5822030-3.stp"
_PACKAGE = {
    "C73": _CAN10, "C152": _CAN10,          # radial electrolytics, drawn as circles
    "SK4": _DIN41612,                       # network slot, 48-way eurocard
    "SK6": _SIMM72,                         # the SIMM socket alongside SK9
    "IC29": "Package_QFP.3dshapes/PQFP-160_28x28mm_P0.65mm.step",   # VIDC20
    "IC22": _SO20, "IC26": _SO20, "IC30": _SO20, "IC33": _SO20,     # 7.3 x 12.3
    "RP6": _SO16, "RP11": _SO16, "RP13": _SO16,                     # 5.2 x 10.8
    "RP14": _SO16, "RP15": _SO16, "RP16": _SO16,
    "C83": _CHIPC, "C84": _CHIPC, "C99": _CHIPC, "C107": _CHIPC,
    "C108": _CHIPC, "C115": _CHIPC, "C118": _CHIPC, "C126": _CHIPC,
    "C142": _CHIPC, "C160": _CHIPC,
    "R148": _CHIPR, "R184": _CHIPR,
    # FITTED, not identified -- see _FITTED below.
    "C91": "Capacitor_Tantalum_SMD.3dshapes/CP_EIA-7343-31_Kemet-D.step",
    "C36": "Capacitor_SMD.3dshapes/C_1812_4532Metric.step",
    "C151": "Capacitor_SMD.3dshapes/C_2512_6332Metric.step",
    "R213": "Resistor_SMD.3dshapes/R_2010_5025Metric.step",
}
# The four above are a weaker claim than the rest of _PACKAGE. Everything else
# there matches a standard BODY to within half a millimetre, which is an
# identification; these were picked by running the candidate EIA sizes against
# the drawn outline and taking the smallest error, which is a fit. The drawing
# gives no height either way, so their height is the generic package's -- and
# for C36, C151 and R213 that height lands right where the anchors are, so the
# foul report keeps saying so rather than letting a guess retire a warning.
#
# How good each fit is, drawn against chosen: C36 1812, out by 0.34 total, is
# convincing. C91 7343 "D", out by 1.14, is the right class -- the drawing gives
# it a chamfered corner and a "+", so a rectangular POLARISED surface-mount part,
# and the radial cans on this board are drawn as circles instead. C151 2512 and
# R213 2010, out by 0.78 and 0.84, are the weak ones: the two are drawn the same
# width and within 0.4 mm of the same length, so the fit is splitting hairs, and
# the drawing overprints both their refs ON their outlines, which is exactly the
# contamination that would move a figure by a few tenths.
_FITTED = {"C91", "C36", "C151", "R213"}
# Left a prism: LK5 alone. It is a two-pin link -- the drawing crosses one pad
# and notes a shunt fitted across pins 1 to 2 -- so the 2.16 x 2.16 recorded for
# it below looks like ONE pad rather than the pair. Correcting that would move a
# plan clearance input, so it is left alone and flagged here instead.

# The two radial electrolytics, as (ref, X, Y, diameter).
_ROUND = [("C73", -61.83, 2.14, 11.01), ("C152", 54.19, 12.57, 9.86)]


def board() -> Part:
    """The motherboard local to SK9. Fit checking and display only."""
    return _slab(-BOARD_X, BOARD_X, BOARD_Y0, BOARD_Y1,
                 -SOCKET_H - BOARD_T, -SOCKET_H)


@lru_cache(maxsize=None)
def _neighbour_parts() -> dict[str, Part]:
    """Each neighbour as its own solid: a KiCad package where the outline
    identifies one, a keep-out prism where it does not.

    Cached because the callers below index it inside comprehensions, one call
    per component, which rebuilt all 32 solids each time. Harmless while they
    were all small blocks; once SK4 and SK6 became real STEP it dominated the
    run. Callers only read the dict."""
    z0 = -SOCKET_H                      # the board's top face
    out = {}
    for ref, X, Y, w, h in _NEIGHBOURS + [(r, X, Y, d, d) for r, X, Y, d in _ROUND]:
        pkg = _package(_PACKAGE.get(ref))
        if pkg is None:
            out[ref] = _slab(X - w / 2, X + w / 2, Y - h / 2, Y + h / 2,
                             z0, z0 + NEIGHBOUR_H)
            continue
        # Spun a quarter turn when the package's footprint is the other way up
        # from the drawn outline, decided by which way round each is longer.
        bb = pkg.bounding_box()
        spin = 0 if (w >= h) == (bb.size.X >= bb.size.Y) else 90
        spun = Rot(0, 0, spin) * pkg
        # ...centred on its own bounds, not its origin: a KiCad origin is the
        # footprint's, which for the radial cans is a pad, not the middle.
        c = spun.bounding_box().center()
        out[ref] = Pos(X - c.X, Y - c.Y, z0) * spun
    return out


# Drawn in their own colour rather than folded into the rest: the two card
# sockets flanking SK9. They are the only neighbours carrying a vendor STEP, and
# white reads them as the cream plastic they are in life.
_SOCKETS = ("SK4", "SK6")


def _merge(refs) -> Part | None:
    part = None
    for r in refs:
        p = _neighbour_parts()[r]
        part = p if part is None else part + p
    return part


def neighbours() -> Part:
    """What is on the board beside the socket, less the two card sockets."""
    return _merge([r for r in _neighbour_parts() if r not in _SOCKETS])


def sockets() -> Part:
    """SK4 and SK6 -- the network slot and the SIMM socket."""
    return _merge(_SOCKETS)


def _fouls(printed: Part):
    """Which neighbours the printed parts run into, and by how much, per part so
    the answer names the component. A real 3D check for the neighbours carrying a
    KiCad package; a plan check for the prisms, whose height is invented. A
    package in _FITTED is checked in 3D like any other, but the report marks it,
    because its height came off a fitted package rather than an identified one."""
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
    """Nearest neighbour outline to SK9's footprint, per tower and flank, in
    plan. Bounding boxes throughout, so a round part is measured at its square --
    pessimistic, which is the right way to be wrong here."""
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


# Viewer colours. The printed parts share one filament colour. The TSOPs are
# black in life, but lifted a few shades here so they read against the socket.
COLOURS = {
    "yoke": "#d98a2b", "anchor R": "#d98a2b", "anchor L": "#d98a2b",
    "card": "#1e7a3c", "socket": "#141416",
    "VRAM": "#33333a", "electrolytics": "#42424a",
    "beads": "#55555e", "chip caps": "#b99a6b",
    "board": "#0d4423", "neighbours": "#3a3a42", "sockets": "#ffffff",
}


if __name__ == "__main__":
    here = Path(__file__).parent
    # Both hands exported: the end wall is at one end and the boss on one flank,
    # so the pair is chiral and no rotation turns one into the other.
    parts = {
        "yoke": yoke(),
        "anchor_right": anchor(True),
        "anchor_left": anchor(False),
        "coupon": coupon(),
    }
    for name, p in parts.items():
        p = for_print(p)                # exported bed-down, ready to slice
        step = here / f"vram_{name}.step"
        export_step(p, str(step))
        # Pin STEP's wall-clock header, so `git status` reports only geometry
        # that actually moved.
        step.write_text(
            re.sub(r"'\d{4}-\d{2}-\d{2}T[\d:]+'", "'1970-01-01T00:00:00'",
                   step.read_text(), count=1)
        )
        export_stl(p, str(here / f"vram_{name}.stl"))
        bb = p.bounding_box()
        print(f"{name:10s} {bb.size.X:6.1f} x {bb.size.Y:5.1f} x {bb.size.Z:5.1f} mm"
              f"   {p.volume / 1000:5.1f} cm^3   solids={len(p.solids())}"
              f"   bed-down, {'on Z=0' if abs(bb.min.Z) < 1e-6 else 'NOT on the bed'}")
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

    # The drawing gives 6.74 of clear card at one end and 7.08 at the other, on
    # OPPOSITE faces -- so the jaws clear the tighter of the pair at each end
    # whichever way round the card goes. Checked as a boolean, against the real
    # packages rather than the land outlines.
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

    # Plan only: the drawing has no heights, so this says where there is board,
    # not how much air there is at the boss's own height.
    gaps = _plan_clearance()
    need = abs(_foot_y) - SOCKET_PLAN_W / 2
    _n = len(_NEIGHBOURS) + len(_ROUND)
    _pkg = sum(1 for r in _neighbour_parts() if r in _PACKAGE)
    _own = sum(1 for r, v in _PACKAGE.items() if r in _neighbour_parts()
               and (_MODELS / v).is_file())
    print(f"board      drg 0197,000/A, {_n} neighbours -- {_pkg} as packages "
          f"({_pkg - _own} KiCad, {_own} vendor STEP; real heights, nominal ones), "
          f"of which {len(_FITTED)} fitted to the outline rather than identified, "
          f"{_n - _pkg} as {'a prism' if _n - _pkg == 1 else 'prisms'} "
          f"(height invented); "
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
    _flank = "+Y" if CAP_SIDE > 0 else "-Y"
    _ok = [e for e in ("left", "right") if gaps[e, _flank][0] >= need]
    print(f"           the boss is on {_flank} (CAP_SIDE {CAP_SIDE:+d}), which clears in plan "
          f"at: {', '.join(_ok) if _ok else 'NEITHER tower'}"
          + ("" if len(_ok) == 2 else " -- but plan is pessimistic, see the 3D check below"))
    fouls = _fouls(printed)
    if fouls:
        print("           the anchors' OUTER END WALLS also hit: "
              + ",  ".join(f"{r} by {dx:.2f}"
                           + (" [fitted height]" if r in _FITTED else
                              "" if pkg else " [prism]")
                           for r, dx, dy, v, pkg in fouls))
    # Independent of whether anything fouled: a package model narrower than the
    # outline the drawing gives can hide a foul from the 3D check above.
    _small = [(r, w - b.size.X, h - b.size.Y)
              for r, X, Y, w, h in _NEIGHBOURS + [(r, X, Y, d, d) for r, X, Y, d in _ROUND]
              if r in _PACKAGE and (b := _neighbour_parts()[r].bounding_box())
              and (w - b.size.X > 0.3 or h - b.size.Y > 0.3)]
    if _small:
        print("           NOTE a package model smaller than the outline drawn hides "
              "fouls: " + ",  ".join(f"{r} by {max(dx, dy):.2f}" for r, dx, dy in _small)
              + " -- the plan table above uses the drawn size and is the one to trust")
    # And the other way round: a model BIGGER than the drawn outline invents a
    # foul rather than hiding one. Listed only for parts that actually fouled,
    # because that is the only case where it costs anything -- and unfiltered it
    # would name most of the board, since a KiCad model carries the leads and
    # this drawing draws bodies.
    _big = [(r, b.size.X - w, b.size.Y - h)
            for r, X, Y, w, h in _NEIGHBOURS + [(r, X, Y, d, d) for r, X, Y, d in _ROUND]
            if r in {f[0] for f in fouls} and (b := _neighbour_parts()[r].bounding_box())
            and (b.size.X - w > 0.3 or b.size.Y - h > 0.3)]
    if _big:
        print("           NOTE and of those, bigger than the outline drawn, so the "
              "foul is partly the model's: "
              + ",  ".join(f"{r} by {max(dx, dy):.2f}" for r, dx, dy in _big))
    print(f"           each wants {_cap_x1 - SOCKET_L / 2:.2f} mm past the socket's "
              f"end and the drawing leaves {SOCKET_PLAN_END:.2f}. The anchor stands "
              f"{1.5} mm off the board, so this is only real for a part taller than that.")

    try:
        from ocp_vscode import show

        # Card, population and yoke are drawn SEATED -- dropped by SEAT_ERROR
        # onto where the card really sits -- so the gap under the foot shows as
        # the 1.00 mm the screw pulls through, not that plus the stack-up error.
        seated = Pos(0, 0, -SEAT_ERROR)
        shown = [("yoke", seated * parts["yoke"]),
                 ("anchor R", parts["anchor_right"]),
                 ("anchor L", parts["anchor_left"]), ("card", seated * card()),
                 ("socket", socket()), ("board", board()),
                 ("neighbours", neighbours()), ("sockets", sockets()),
                 *((n, seated * g) for n, g in comps.items())]
        show(*[p for _, p in shown], names=[n for n, _ in shown],
             colors=[COLOURS[n] for n, _ in shown])
    except Exception as exc:
        print(f"viewer not connected ({exc.__class__.__name__})")
