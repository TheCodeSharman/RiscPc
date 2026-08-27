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

    def run(self) -> Sheet:
        y = MARGIN_Y
        for group in self.lay.groups:
            y = self._group(group, y) + ROW // 2
        self._wire_all()
        self._title()
        return self.sheet

    # --- groups -------------------------------------------------------
    def _group(self, group, y0: float) -> float:
        if group.supply:
            return self._supply(group, y0)

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
            head = self._place_multi(group.head, x0, sum(ys) / len(ys))
            self._globals_for(head)
            self._loose_for(head)
            x0 += HEAD_GAP

        for lane, y in zip(group.lanes, ys):
            self._lane(lane, x0, y, head)
        return ys[-1] + self._legroom(group.lanes[-1])

    @staticmethod
    def _headroom(lane) -> float:
        """Vertical space a lane needs above its row for stacked bridges."""
        top = max((a.tier for a in lane.attachments if a.above), default=-1)
        return (top + 2) * TIER

    @staticmethod
    def _legroom(lane) -> float:
        """Space below the row for stubs and for spare units parked there."""
        has_stub = any(not a.above or a.kind == "stub" for a in lane.attachments)
        return STUB * (3 if has_stub else 2)

    def _supply(self, group, y0: float) -> float:
        """Rail filtering: each part runs horizontally between its globals."""
        y = y0
        for lane in group.lanes:
            ref = lane.spine[0]
            p = self.place(ref, MARGIN_X + COL, y)
            self._globals_for(p, prefer_horizontal=True)
            y += ROW // 2
        return y - ROW // 2

    # --- one lane -----------------------------------------------------
    def _lane(self, lane, x0: float, y: float, head) -> None:
        placed: dict[str, object] = {}
        x = x0
        for ref in lane.spine:
            placed[ref] = self._place_multi(ref, x, y)
            x += COL

        # Orient each part so the pin it shares with its upstream neighbour
        # faces left. Nothing is wired here — a resistor whose pin 1 ends up
        # downstream would make the wire double back through its own body,
        # and the router cannot undo that.
        for a, b in zip(lane.spine, lane.spine[1:]):
            self._orient(placed[a], placed[b])

        for att in lane.attachments:
            if att.kind == "bridge":
                self._place_bridge(att, placed, y)
            else:
                self._stub(att, placed, y)
        for att in lane.attachments:
            if att.kind == "bridge":
                self._globals_for(self._bridges[att.ref])

        for ref in lane.spine:
            self._globals_for(placed[ref])
            self._loose_for(placed[ref])
            self._terminals_for(placed[ref])

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
                if net.name not in self.lay.globals:
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
        """
        traced = all(t[2] for t in terms)
        remaining = list(terms)
        seed = remaining.pop(0)
        tree = {grid.cell(seed[0])}
        tree_pts = [seed[0]]
        first = True

        while remaining:
            i = min(range(len(remaining)),
                    key=lambda k: min(_manhattan(remaining[k][0], q)
                                      for q in tree_pts))
            at, direction, _ = remaining.pop(i)
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

    # --- attachments --------------------------------------------------
    def _place_bridge(self, att, placed, row_y: float) -> None:
        lo, hi = placed.get(att.spans[0]), placed.get(att.spans[1])
        if lo is None or hi is None:
            return
        y = row_y - (att.tier + 1) * TIER - TIER
        self._bridges[att.ref] = self._place_multi(
            att.ref, snap((lo.x + hi.x) / 2), y)

    def _pin_name_at(self, placed, net: str):
        sym = self.sym(placed.ref)
        for pin in sym.units[placed.unit].pins:
            n = self.cir.net_at(placed.ref, pin)
            if n and n.name == net:
                return pin
        return None

    def _stub(self, att, placed, row_y: float) -> None:
        host = placed.get(att.spans[0])
        if host is None:
            return
        p = self._place_multi(att.ref, host.x, row_y + STUB, angle=90.0)
        self._globals_for(p)

    # --- helpers ------------------------------------------------------
    def _place_multi(self, ref: str, x: float, y: float, angle=None):
        """Place a part, emitting a second instance for a spare unit.

        A quad op-amp's supply pins live on their own unit; KiCad expects that
        as a separate symbol on the sheet, so U1A becomes unit 1 here plus
        unit 5 parked below the row.
        """
        sym = self.sym(ref)
        part = self.cir.parts[ref]
        by_unit = sym.split_by_unit(part.pins) if len(sym.units) > 1 else None

        if not by_unit or len(by_unit) == 1:
            return self.place(ref, x, y, angle=angle)

        main = min(by_unit, key=lambda u: -len(by_unit[u]))
        p = self.place(ref, x, y, unit=main, angle=angle)
        for unit in by_unit:
            if unit == main:
                continue
            extra = self.place(ref, x, y + STUB * 2, unit=unit, angle=0.0)
            self._globals_for(extra)
        return p

    def _shared_net(self, a: str, b: str) -> str | None:
        na = {n.name for n in self.cir.nets_of(a)}
        nb = {n.name for n in self.cir.nets_of(b)}
        both = na & nb - self.lay.globals
        return sorted(both)[0] if both else None

    def _pin_at(self, placed, net: str):
        sym = self.sym(placed.ref)
        for pin in sym.units[placed.unit].pins:
            n = self.cir.net_at(placed.ref, pin)
            if n and n.name == net:
                return pin_xy(placed, sym, pin)
        return None

    def _orient(self, a, b) -> None:
        net = self._shared_net(a.ref, b.ref)
        if net:
            self._face_left(b, net)

    def _face_left(self, placed, net: str) -> None:
        """Rotate a two-terminal part so its `net` pin is the leftmost."""
        sym = self.sym(placed.ref)
        pins = sym.units[placed.unit].pins
        if len(pins) != 2:
            return
        xs = {p: pin_xy(placed, sym, p)[0] for p in pins}
        target = next(
            (p for p in pins
             if (n := self.cir.net_at(placed.ref, p)) and n.name == net), None
        )
        if target and xs[target] == max(xs.values()) and len(set(xs.values())) > 1:
            placed.angle = (placed.angle + 180) % 360

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
            self._pending.append(_Stub(
                at=pin_xy(placed, sym, pin),
                out=pin_dir(placed, sym, pin),
                net=net.name,
                traced=placed.traced,
                power=True,
                prefer_horizontal=prefer_horizontal,
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
