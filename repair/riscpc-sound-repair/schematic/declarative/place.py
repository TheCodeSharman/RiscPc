"""Place a laid-out circuit, then wire it.

Two phases, and keeping them apart is the whole point.

**Placement** decides where every symbol sits, using the decomposition
layout.py already made — a spine along the row, bridges tiered above it,
stubs hung below, globals terminating in a power symbol at the pin:

    tier 1        ---[ bridge ]---            (above, one row per tier)
    tier 0     ------[ bridge ]------
    spine    >--[ A ]---[ B ]---[ C ]-->      (the row itself)
    stubs             [ stub ]                (below)
                         |
                        GND

**Wiring** then runs once, over the finished sheet, one *net* at a time
through a shared occupancy grid (see route.py).

The earlier version wired as it placed, and emitted wires from six different
places — the spine, bridges, stubs, globals, loose pins, terminals — each
drawing its own straight line and none of them aware of the others. That is
how two resistors in series came out with the wire through both bodies and
the label lying on top of it. There is now exactly one function that emits a
wire, it sees the whole sheet, and `verify.py` reads back what it drew.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import route
from geometry import (COL, GRID, ROW, STUB, TIER, Builder, Sheet, body_box,
                      pin_dir, pin_xy, snap)

MARGIN_X = GRID * 16
MARGIN_Y = GRID * 24
HEAD_GAP = COL * 2          # source part to the first lane column
POWER_STUB = GRID * 4       # pin to power symbol
GLYPH = GRID * 2            # room the power symbol's own artwork takes
# A stub hangs below its host, and *both* carry text into the gap — the
# host's value underneath it, the stub's reference above itself. Clearing
# the symbols is not enough; STUB alone put "Rpull_R" on top of "BC849C".
STUB_DROP = STUB * 2
# Two legs off one host stand side by side rather than stacking down the same
# column — collinear vertical parts would run each other's wire through the
# other's body. Half a spine column keeps the second leg clear of the next
# spine part, whose own legs sit a full column away.
LEG_SHIFT = GRID * 6
# (supply parts used to lay out as a grid of their own; they now flow through
# the ordinary spine-and-legs path, so no separate pitch is needed.)
# How much a turn must save before it is worth making. A two-terminal part is
# electrically symmetric, so flipping it end-for-end is often free and the
# distance it saves is arbitrary noise — swapping which pin is the nearer by
# the part's own span. Only reorient when the gain clearly exceeds that, which
# is what tells a genuinely back-to-front part from a coin-toss and stops a
# marginal turn from trading a tidy wire for a crossing.
FLIP_MARGIN = GRID * 7


@dataclass
class _Stub:
    """A pin that leads out to a power symbol or an off-sheet label."""
    at: tuple[float, float]
    out: tuple[float, float]        # the pin's own outward direction
    net: str
    traced: bool
    power: bool
    prefer_horizontal: bool = False


class Placer(Builder):
    def __init__(self, cir, lay):
        super().__init__(cir, lay)
        self._bridges = {}
        self._pending: list[_Stub] = []
        self._spares: list[tuple[str, int]] = []
        # A rail with two pins in one lane (an inductor and its reservoir cap)
        # is drawn as a wire between them with a single label — an "island" —
        # rather than a power symbol at each pin. `_island` is every such pin,
        # `_island_quiet` the ones whose symbol is suppressed (all but one).
        self._island: set[tuple[str, str]] = set()
        self._island_quiet: set[tuple[str, str]] = set()
        self._island_tap: set[tuple[str, str]] = set()

    def run(self) -> Sheet:
        y = MARGIN_Y
        width = 0.0
        blocks = []
        for group in self.lay.groups:
            if group.head is None:
                # No head joins its lanes, so each is an independent block —
                # collected to flow, whatever kind of circuit it is.
                blocks += [self._lane_block(lane) for lane in group.lanes]
            else:
                y = self._group(group, y) + ROW // 2
                width = max(width, self.sheet.bounds()[2] - MARGIN_X)
        # A package's spare supply unit is a block like any other.
        blocks += [self._spare_block(sp) for sp in self._spares]
        self._flow(blocks, y, width)
        self._wire_all()
        self._title()
        return self.sheet

    # --- block flow ---------------------------------------------------
    def _flow(self, blocks, y0: float, max_width: float) -> float:
        """Pack loose circuit blocks left-to-right, wrapping at a width.

        Anything that is not part of a connected, head-anchored group — a
        supply filter, a bare ground stub, a package's spare supply unit — is a
        small block a few columns wide. A column of them wastes the sheet; laid
        across to the width the signal chain already spans and wrapped onto a
        new shelf when the next would overflow, they take a strip. Nothing here
        is specific to what a block *is* — each carries its own width and a
        closure that places it; the flow only decides where.
        """
        if max_width <= 0:
            max_width = COL * 14
        x, y, shelf = MARGIN_X, y0, 0.0
        for width, place in blocks:
            if x > MARGIN_X and x - MARGIN_X + width > max_width:
                x = MARGIN_X
                y += shelf + ROW // 2
                shelf = 0.0
            shelf = max(shelf, place(x, y))
            x += width
        return y + shelf

    def _lane_block(self, lane):
        """A lane as a flow block: (width, place-at)."""
        def place(x, y):
            self._lane(lane, x, y + self._headroom(lane), None)
            return self._headroom(lane) + self._legroom(lane)
        return (self._block_width(lane), place)

    def _spare_block(self, sp):
        """A spare package unit as a flow block — pins up/down, so it is narrow."""
        ref, unit = sp
        def place(x, y):
            self._globals_for(self.place(ref, x, y + TIER, unit=unit, angle=0.0))
            return ROW // 2
        return (COL * 2, place)

    @staticmethod
    def _block_width(lane) -> float:
        """Footprint width: the spine, plus room for a side label where one is.

        A filter carries a rail label off each end and needs the room; a bare
        stub — a jack sleeve to ground — has its label below and packs tight.
        A hung leg (a reservoir cap) is what tells the two apart.
        """
        pad = COL * 1.5 if lane.attachments else COL * 0.5
        return len(lane.spine) * COL + pad

    def _group(self, group, y0: float) -> float:

        # Draw each lane at the height of the head pin that feeds it, so the
        # fan-out does not cross itself. The DAC's pin 8 sits above pin 6 but
        # feeds the other channel; ordered by pin, the two feeds run straight
        # out instead of swapping over. layout.py cannot do this — the pin
        # geometry only exists here.
        if group.head and len(group.lanes) > 1:
            group.lanes.sort(
                key=lambda ln: -self._head_pin_y(group.head, ln))

        # A lane is as tall as its own bridge stack. Spacing them by a fixed
        # pitch means the tallest lane's bridges climb into the lane above.
        ys, cur = [], y0
        for lane in group.lanes:
            cur += self._headroom(lane)
            ys.append(cur)
            cur += self._legroom(lane) + TIER
        x0 = MARGIN_X

        head = None
        if group.head:
            hy = sum(ys) / len(ys)
            head = self._place_multi(group.head, x0, hy)
            self._globals_for(head)
            self._hangers_for(head, hy, defaultdict(int))
            self._loose_for(head)
            x0 += HEAD_GAP

        for lane, y in zip(group.lanes, ys):
            self._lane(lane, x0, y, head)
        return ys[-1] + self._legroom(group.lanes[-1])

    @staticmethod
    def _headroom(lane) -> float:
        """Vertical space a lane needs above its row for stacked bridges.

        One tier per stacked bridge, plus half a tier for the topmost bridge's
        label. Reserving a whole extra tier is what left the op-amps sitting
        that much below their feedback.
        """
        top = max((a.tier for a in lane.attachments if a.above), default=-1)
        return (top + 1) * TIER + TIER / 2

    def _legroom(self, lane) -> float:
        """Space below the row for legs — vertical drops to a rail.

        Legs now stand side by side at one depth rather than stacking down the
        column, so the room needed below the row is the same whether a host
        carries one leg or three: the resistor plus its drop to the rail.
        """
        has_leg = any(
            not att.above or att.kind == "stub" for att in lane.attachments
        ) or any(
            any(self.cir.parts[r].kind != "terminal"
                for r in self.lay.stubs.get(ref, []))
            for ref in lane.spine
        )
        return STUB_DROP + STUB if has_leg else STUB * 2

    # --- one lane -----------------------------------------------------
    def _lane(self, lane, x0: float, y: float, head) -> None:
        placed: dict[str, object] = {}
        parts = []
        x = x0
        for ref in lane.spine:
            placed[ref] = self._place_multi(ref, x, y)
            parts.append(placed[ref])
            x += COL

        # Attachments — bridges over the row, legs under it. Positions only:
        # orientation waits until every part is down, so each can be turned to
        # face neighbours that actually exist yet.
        below = defaultdict(int)
        for att in lane.attachments:
            if att.kind == "bridge":
                b = self._place_bridge(att, placed, y)
                if b is not None:
                    parts.append(b)
            else:
                p = self._stub(att, placed, y)
                if p is not None:
                    parts.append(p)
                    below[att.spans[0]] = max(below[att.spans[0]], att.tier + 1)
        for ref in lane.spine:
            parts.extend(self._hangers_for(placed[ref], y, below))

        # One rule turns every part, whatever it is (see _orient).
        for p in parts:
            self._orient(p)

        # A rail shared by two parts of this lane is wired between them, not
        # symbol-per-pin (see _register_islands); that has to be known before
        # globals are recorded so the wired pins can be left out.
        self._register_islands(parts)

        # Pins now sit where they finally are, so their leads out to power
        # symbols and off-sheet labels can be recorded.
        for p in parts:
            self._globals_for(p)
        for ref in lane.spine:
            self._loose_for(placed[ref])
            self._terminals_for(placed[ref])

    def _register_islands(self, parts) -> None:
        """Find rails a lane wires internally: an inductor and its cap on 12V.

        A supply filter's two parts share a rail (its output), which globally
        is a power symbol everywhere it appears — so an inductor and its
        reservoir cap came out as two segments each carrying the same label,
        not one filter. When a global rail touches two pins of a single lane
        the connection is local and short, so it is drawn as a wire with a
        lone label instead. All but one of the island's pins have their symbol
        suppressed; the survivor is the rail's tap out to the rest of the
        sheet, by name, exactly as before.
        """
        by_net: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for p in parts:
            sym = self.sym(p.ref)
            for pin in sym.units[p.unit].pins:
                net = self.cir.net_at(p.ref, pin)
                if net and net.name in self.lay.globals:
                    by_net[net.name].append((p.ref, pin))
        for members in by_net.values():
            if len(members) < 2:
                continue
            self._island.update(members)
            self._island_quiet.update(members[1:])
            self._island_tap.add(members[0])   # keeps the label; send it sideways

    # --- wiring, once, over the whole sheet ----------------------------
    def _wire_all(self) -> None:
        """Draw every net, each as one tree, on one shared occupancy grid.

        Placement is finished by the time this runs, so the router can see
        every body and every pin at once. Nothing here knows what a spine or
        a bridge is: those distinctions did their job during placement, and a
        net is a net.
        """
        grid = route.Grid(self.sheet.bounds(), pad=GRID * 24)
        for placed in self.sheet.placed:
            box = body_box(placed, self.sym(placed.ref), pad=GRID * 0.5)
            if box:
                grid.add_body(box)

        terminals: dict[str, list] = defaultdict(list)
        for placed in self.sheet.placed:
            sym = self.sym(placed.ref)
            for pin in sym.units[placed.unit].pins:
                net = self.cir.net_at(placed.ref, pin)
                if not net:
                    continue
                at = pin_xy(placed, sym, pin)
                grid.add_pin(at, net.name)
                # Local nets route; a global normally does not — unless it is an
                # island rail, wired between two pins of one lane.
                if (net.name not in self.lay.globals
                        or (placed.ref, pin) in self._island):
                    terminals[net.name].append(
                        (at, pin_dir(placed, sym, pin), placed.traced))

        # Global and off-sheet stubs go down first. They are short and
        # straight, so it is the signal nets that must give way to them.
        self._place_stubs(grid)

        # Shortest net first: a net with the least room to move should choose
        # before the sheet fills up around it.
        def cost(name: str):
            pts = [t[0] for t in terminals[name]]
            w = max(p[0] for p in pts) - min(p[0] for p in pts)
            h = max(p[1] for p in pts) - min(p[1] for p in pts)
            return (len(pts), w + h, name)

        for name in sorted((n for n in terminals if len(terminals[n]) > 1),
                           key=cost):
            self._wire_net(grid, name, terminals[name])

    def _wire_net(self, grid, name: str, terms: list) -> None:
        """Grow one net as a rectilinear tree, nearest terminal first.

        The first two pins are joined directly; every pin after that routes to
        whatever of the net is *already drawn*, so it branches off the trunk
        instead of starting another run back from the first pin. That is what
        a junction dot means, and it is why an emitter with four things on it
        no longer draws four wires stacked on each other.

        Confirmed parts are wired before unconfirmed ones, so the trunk is
        what was actually probed and the guesses hang off it. Greyness then
        belongs to the *branch*, not the net: one unconfirmed capacitor used
        to grey out the 2k1 sitting in parallel with it, which says something
        about the resistor that is not true.
        """
        # Traced first, so the solid skeleton exists before anything grey
        # attaches to it; distance decides within each group.
        remaining = sorted(terms, key=lambda t: not t[2])
        seed = remaining.pop(0)
        tree = {grid.cell(seed[0])}
        tree_pts = [seed[0]]
        first = True

        while remaining:
            i = min(range(len(remaining)),
                    key=lambda k: (not remaining[k][2],
                                   min(_manhattan(remaining[k][0], q)
                                       for q in tree_pts)))
            at, direction, traced = remaining.pop(i)
            if first:
                traced = traced and seed[2]
            goals = [seed[0]] if first else [grid.point(c) for c in tree]
            pts = grid.route(name, at, goals, direction,
                             [seed[1]] if first else None)
            if pts is None:
                # Draw it anyway rather than dropping the net silently: a wrong
                # wire is a bug report, a missing one is a mystery. --verify
                # will name it.
                pts = _elbow(at, seed[0] if first else _nearest(at, tree_pts))
            for a, b in zip(pts, pts[1:]):
                self.wire(a, b, name, traced)
            grid.occupy(pts, name)
            if not first:
                self.sheet.junctions.append(pts[-1])
            tree |= grid.path_cells(pts)
            tree_pts.extend(pts)
            first = False

    # --- attachments (positions; orientation is one pass, in _lane) ----
    def _place_bridge(self, att, placed, row_y: float):
        lo, hi = placed.get(att.spans[0]), placed.get(att.spans[1])
        if lo is None or hi is None:
            return None
        # One tier of gap above the row, whether the bridge spans two parts or
        # sits over one op-amp's body — a tier already clears the body, so the
        # feedback rides just above its op-amp, the same distance the driver's
        # Rfb rides above its own. What used to add a second tier for a
        # self-bridge only parked the I/V feedback 15 mm too high.
        y = row_y - (att.tier + 1) * TIER
        b = self._place_multi(att.ref, snap((lo.x + hi.x) / 2), y)
        self._bridges[att.ref] = b
        return b

    def _pin_name_at(self, placed, net: str):
        sym = self.sym(placed.ref)
        for pin in sym.units[placed.unit].pins:
            n = self.cir.net_at(placed.ref, pin)
            if n and n.name == net:
                return pin
        return None

    def _stub(self, att, placed, row_y: float):
        host = placed.get(att.spans[0])
        if host is None:
            return None
        # `_stack` has already given co-located stubs distinct tiers; a leg is
        # drawn vertically dropping to its rail, so the tier shifts it sideways
        # rather than down — two legs stood in one column would each route a
        # wire through the other's body, which is what Rf and Rpull did the
        # moment Rpull stopped being mistaken for a bridge.
        base_x = self._host_pin_x(host, att.ref, host.x)
        x = base_x + att.tier * LEG_SHIFT
        y = row_y + STUB_DROP
        return self._place_multi(att.ref, x, y, vertical=True)

    # --- helpers ------------------------------------------------------
    def _place_multi(self, ref: str, x: float, y: float, angle=None,
                     vertical: bool = False):
        """Place a part, emitting a second instance for a spare unit.

        A quad op-amp's supply pins live on their own unit; KiCad expects that
        as a separate symbol on the sheet, so U1A becomes unit 1 here plus
        unit 5 parked below the row.
        """
        sym = self.sym(ref)
        part = self.cir.parts[ref]
        by_unit = sym.split_by_unit(part.pins) if len(sym.units) > 1 else None

        if not by_unit or len(by_unit) == 1:
            return self.place(ref, x, y, angle=angle, vertical=vertical)

        main = min(by_unit, key=lambda u: -len(by_unit[u]))
        p = self.place(ref, x, y, unit=main, angle=angle, vertical=vertical)
        for unit in by_unit:
            if unit != main:
                self._spares.append((ref, unit))
        return p

    def _main_unit(self, ref: str) -> int:
        """The unit `_place_multi` will draw as the part's body."""
        sym = self.sym(ref)
        if len(sym.units) == 1:
            return next(iter(sym.units))
        by_unit = sym.split_by_unit(self.cir.parts[ref].pins)
        return min(by_unit, key=lambda u: -len(by_unit[u]))

    def _head_pin_y(self, head_ref: str, lane) -> float:
        """Library y (y-up) of the head pin(s) that feed `lane`.

        A larger value sits higher on the sheet, so sorting lanes by it
        descending draws the fan-out in pin order. Averaged when a lane is fed
        by more than one head pin; zero if none is found, which leaves such a
        lane where the stable sort had it.
        """
        members = set(lane.spine) | {a.ref for a in lane.attachments}
        sym = self.sym(head_ref)
        unit = self._main_unit(head_ref)
        ys = []
        for pin, pinobj in sym.units[unit].pins.items():
            net = self.cir.net_at(head_ref, pin)
            if not net or net.name in self.lay.globals:
                continue
            if any(r in members for r, _ in net.pins):
                ys.append(pinobj.y)
        return sum(ys) / len(ys) if ys else 0.0

    def _shared_net(self, a: str, b: str) -> str | None:
        na = {n.name for n in self.cir.nets_of(a)}
        nb = {n.name for n in self.cir.nets_of(b)}
        both = na & nb - self.lay.globals
        return sorted(both)[0] if both else None

    def _shared_rail(self, a: str, b: str) -> str | None:
        """A global rail two parts share — how a filter cap meets its inductor.

        Their only common net is the rail (12V), which `_shared_net` skips as a
        global; but for an island the leg does drop from that pin, so it is
        worth finding.
        """
        na = {n.name for n in self.cir.nets_of(a)}
        nb = {n.name for n in self.cir.nets_of(b)}
        both = sorted((na & nb) & self.lay.globals)
        return both[0] if both else None

    def _pin_at(self, placed, net: str):
        sym = self.sym(placed.ref)
        for pin in sym.units[placed.unit].pins:
            n = self.cir.net_at(placed.ref, pin)
            if n and n.name == net:
                return pin_xy(placed, sym, pin)
        return None

    def _host_pin_x(self, host, leg_ref: str, fallback: float) -> float:
        """x a leg should drop from, given the host pin it attaches to.

        Dropping from the host's centre makes a leg off an op-amp's +in jog
        sideways across the −in wiring — the last two crossings in the amp were
        exactly that. So the leg drops from the pin. But a pin that points
        *sideways* (an op-amp input) can only be entered horizontally: a leg
        directly beneath it forces the wire to S back in, while a leg set off
        to the side the pin faces makes a clean L — out along the pin, one turn
        down. A pin already pointing up or down takes the leg straight under.
        """
        net = self._shared_net(leg_ref, host.ref)
        rail = self._shared_rail(leg_ref, host.ref) if not net else None
        pin = self._pin_name_at(host, net or rail) if (net or rail) else None
        if not pin:
            return fallback
        sym = self.sym(host.ref)
        x = pin_xy(host, sym, pin)[0]
        # The side-step is for a pin that can only be entered horizontally — an
        # op-amp input. A rail tap takes the cap straight beneath it.
        if rail is None:
            dx, dy = pin_dir(host, sym, pin)
            if abs(dx) > abs(dy):
                x += dx * (GRID * 2)
        return x

    def _orient(self, placed) -> None:
        """Turn a part to face its neighbours — one rule for every component.

        Try each orientation the part's slot allows and keep the one where its
        pins sit closest to what they connect to. Out of that fall all the old
        special cases: a spine passive turns so its ends meet the parts either
        side; a leg so its live pin faces its host and its rail pin the rail; a
        bridge so each end faces the side it spans; an op-amp so its inputs
        meet the feedback above and the bias below — a vertical mirror if that
        is which way round they need to be. Nothing is keyed on what a part
        *is*; the geometry of what it reaches decides. A turn is only made when
        it clearly helps (see FLIP_MARGIN), so a symmetric passive keeps the
        orientation it was placed with unless it was genuinely back-to-front.

        This runs only once every part is placed, so a part's neighbours are
        real positions to aim at rather than intentions.
        """
        candidates = self._candidates(placed)
        if len(candidates) < 2:
            return
        placed.angle, placed.mirror = candidates[0]
        best, best_cost = candidates[0], self._facing_cost(placed)
        for cand in candidates[1:]:
            placed.angle, placed.mirror = cand
            cost = self._facing_cost(placed)
            if cost < best_cost - FLIP_MARGIN:
                best, best_cost = cand, cost
        placed.angle, placed.mirror = best

    def _candidates(self, placed):
        """The orientations a part's slot allows — the scorer picks among them.

        A two-terminal part may flip end-for-end within the axis its position
        assumes; the flip keeps that axis. A part of three pins or more (an
        active device) is not rotated — its facing is fixed by the symbol — but
        may be mirrored top-to-bottom, which swaps an op-amp's inputs while
        leaving its output on the tip.
        """
        sym = self.sym(placed.ref)
        n = len(sym.units[placed.unit].pins)
        if n < 2:
            return [(placed.angle, placed.mirror)]
        if n >= 3:
            return [(placed.angle, None), (placed.angle, "x")]
        a = placed.angle
        return [(a, placed.mirror), ((a + 180) % 360, placed.mirror)]

    def _facing_cost(self, placed) -> float:
        """Sum of Manhattan distances from each pin to what its net reaches.

        Global nets are skipped: a rail is drawn as a local stub at the pin, so
        it pulls in no direction, and its many members have no meaningful
        centre. The local nets are what a part should face.
        """
        sym = self.sym(placed.ref)
        total = 0.0
        for pin in sym.units[placed.unit].pins:
            net = self.cir.net_at(placed.ref, pin)
            if not net or net.name in self.lay.globals:
                continue
            target = self._net_target(placed.ref, net.name)
            if target is None:
                continue
            px, py = pin_xy(placed, sym, pin)
            total += abs(px - target[0]) + abs(py - target[1])
        return total

    def _net_target(self, ref: str, netname: str):
        """Mean position of the pins other placed parts put on this net."""
        xs, ys = [], []
        for p in self.sheet.placed:
            if p.ref == ref:
                continue
            hp = self._pin_at(p, netname)
            if hp:
                xs.append(hp[0])
                ys.append(hp[1])
        if not xs:
            return None
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def _globals_for(self, placed, prefer_horizontal: bool = False) -> None:
        """Note every global pin. Where its symbol goes is decided later.

        The direction cannot be settled here: four of the DAC's pins are
        global and they are all on one side, so dropping each straight down
        laid four stubs on top of each other. Which way is free is only
        knowable once everything is placed, so this records the pin and
        `_place_stubs` chooses.
        """
        sym = self.sym(placed.ref)
        for pin in sym.units[placed.unit].pins:
            net = self.cir.net_at(placed.ref, pin)
            if not net or net.name not in self.lay.globals:
                continue
            if (placed.ref, pin) in self._island_quiet:
                continue                # wired to its island's tap, no symbol
            self._pending.append(_Stub(
                at=pin_xy(placed, sym, pin),
                out=pin_dir(placed, sym, pin),
                net=net.name,
                traced=placed.traced,
                power=True,
                # an island tap sends its label sideways, leaving the way down
                # clear for the cap wired beneath it.
                prefer_horizontal=(prefer_horizontal
                                   or (placed.ref, pin) in self._island_tap),
            ))

    def _loose_for(self, placed) -> None:
        """Label a pin whose net has no other part — an off-sheet connection."""
        sym = self.sym(placed.ref)
        for pin in sym.units[placed.unit].pins:
            net = self.cir.net_at(placed.ref, pin)
            if not net or net.name in self.lay.globals:
                continue
            if len({r for r, _ in net.pins}) > 1:
                continue
            self._pending.append(_Stub(
                at=pin_xy(placed, sym, pin),
                out=pin_dir(placed, sym, pin),
                net=net.name,
                traced=placed.traced,
                power=False,
            ))

    def _place_stubs(self, grid) -> None:
        """Lead each global and off-sheet pin out to a clear spot.

        Tried in order of what a schematic normally does — rails up, grounds
        down, labels out along the pin — and falling back to whatever is
        actually free. Each stub is given its own key in the grid even when
        two are the same net, because two GND leads drawn on top of each
        other are still two symbols in one place.
        """
        for i, stub in enumerate(self._pending):
            key = f"{stub.net}#{i}"
            up = not stub.net.lstrip().startswith("-") and \
                not stub.net.upper().startswith(("GND", "0V"))
            out = (round(stub.out[0]), round(stub.out[1]))
            order = [out, (0, -1) if up else (0, 1), (0, 1) if up else (0, -1),
                     (1, 0), (-1, 0)]
            if stub.power and not stub.prefer_horizontal and out[1] == 0:
                # A sideways power pin still reads better dropping to its rail
                # than sticking out, when there is room.
                order = [order[1]] + order
            length = POWER_STUB if stub.power else POWER_STUB * 1.5

            end = None
            for d in _unique(order):
                cand = (stub.at[0] + d[0] * length, stub.at[1] + d[1] * length)
                if grid.clear(stub.at, cand, key):
                    end = cand
                    break
            if end is None:
                end = (stub.at[0] + order[0][0] * length,
                       stub.at[1] + order[0][1] * length)

            self.wire(stub.at, end, stub.net, stub.traced)
            grid.occupy([stub.at, end], key)
            grid.add_pin(end, key)
            if not (stub.power and self.power(stub.net, end, 0.0 if up else 180.0)):
                self.sheet.labels.append((end[0], end[1], stub.net))

            # The glyph itself takes up room. Without this a net could cross
            # exactly on the arrowhead, which is not a short but reads as one.
            gy = end[1] - GLYPH if up else end[1] + GLYPH
            lo, hi = sorted((end[1], gy))
            grid.add_body((end[0] - GLYPH / 2, lo, end[0] + GLYPH / 2, hi))

    def _hangers_for(self, placed, row_y: float, below) -> list:
        """Place the rule-2 stub parts that hang off this host.

        A part whose only neighbour is one other part never takes a column of
        its own, so it is not in any lane and nothing else places it. Only
        off-board terminals were being handled, which meant both 15k bias
        resistors were simply absent from the drawing — and no check noticed,
        because a part with no pins on the sheet cannot disagree with
        anything. `--verify` now reports that as MISSING. Positions only; the
        orientation pass in `_lane` turns each so its rail pin drops.
        """
        out = []
        for ref in self.lay.stubs.get(placed.ref, []):
            if self.cir.parts[ref].kind == "terminal":
                continue                    # `_terminals_for` puts those inline
            tier = below[placed.ref]
            below[placed.ref] += 1
            base_x = self._host_pin_x(placed, ref, placed.x)
            out.append(self._place_multi(
                ref, base_x + tier * LEG_SHIFT, row_y + STUB_DROP,
                vertical=True))
        return out

    def _terminals_for(self, placed) -> None:
        """Off-board connections hang off their host as a labelled point."""
        for stub in self.lay.stubs.get(placed.ref, []):
            part = self.cir.parts[stub]
            if part.kind != "terminal":
                continue
            net = self._shared_net(stub, placed.ref)
            if not net:
                continue
            host_pin = self._pin_at(placed, net)
            if not host_pin:
                continue
            self.place(stub, host_pin[0] + COL, host_pin[1])

    def _title(self) -> None:
        self.sheet.title = self.cir.title or "circuit"


def build(cir, lay) -> Sheet:
    return Placer(cir, lay).run()


def _manhattan(a, b) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _nearest(at, pts):
    return min(pts, key=lambda q: _manhattan(at, q))


def _elbow(a, b):
    """Last-resort L, horizontal then vertical."""
    if abs(a[0] - b[0]) < 1e-6 or abs(a[1] - b[1]) < 1e-6:
        return [a, b]
    return [a, (b[0], a[1]), b]


def _unique(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
