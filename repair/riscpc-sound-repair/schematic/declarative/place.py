"""Place and route a laid-out circuit into absolute geometry.

The overlap problem is handled by construction rather than by search, because
layout.py has already decomposed each lane into a spine, bridges over it and
stubs under it. Each of those owns a disjoint band of the sheet:

    tier 1        ---[ bridge ]---            (above, one row per tier)
    tier 0     ------[ bridge ]------
    spine    >--[ A ]---[ B ]---[ C ]-->      (the row itself)
    stubs             [ stub ]                (below)
                         |
                        GND

Verticals from a bridge drop at that bridge's own x extent; verticals from a
stub drop at its host's x. Neither can land on the other, and two bridges
sharing a span already have different tiers. So no wire crosses another
except where nets genuinely meet.
"""

from __future__ import annotations

import route
from geometry import (COL, GRID, ROW, STUB, TIER, Builder, Sheet, body_box,
                      pin_dir, pin_xy, snap)

MARGIN_X = GRID * 16
MARGIN_Y = GRID * 24
HEAD_GAP = COL * 2          # source part to the first lane column
POWER_STUB = GRID * 4       # pin to power symbol


class Placer(Builder):
    def __init__(self, cir, lay):
        super().__init__(cir, lay)
        self._bridges = {}
        self._pins_cache = None
        self._box_cache = None

    def run(self) -> Sheet:
        y = MARGIN_Y
        for group in self.lay.groups:
            y = self._group(group, y) + ROW // 2
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

        # Wire the spine together, orienting each part so its incoming pin
        # faces left — otherwise a resistor's pin 1 can end up downstream and
        # the wire doubles back on itself.
        for a, b in zip(lane.spine, lane.spine[1:]):
            self._connect(placed[a], placed[b], orient=True)

        if head is not None and lane.spine:
            self._connect(head, placed[lane.spine[0]])

        for att in lane.attachments:
            if att.kind == "bridge":
                self._place_bridge(att, placed, y)
            else:
                self._stub(att, placed, y)
        self._pins_cache = None
        self._box_cache = None
        for att in lane.attachments:
            if att.kind == "bridge":
                self._wire_bridge(att, placed)

        for ref in lane.spine:
            self._globals_for(placed[ref])
            self._terminals_for(placed[ref])

    # --- attachments --------------------------------------------------
    def _place_bridge(self, att, placed, row_y: float) -> None:
        lo, hi = placed.get(att.spans[0]), placed.get(att.spans[1])
        if lo is None or hi is None:
            return
        y = row_y - (att.tier + 1) * TIER - TIER
        self._bridges[att.ref] = self._place_multi(
            att.ref, snap((lo.x + hi.x) / 2), y)

    def _wire_bridge(self, att, placed) -> None:
        lo, hi = placed.get(att.spans[0]), placed.get(att.spans[1])
        p = self._bridges.get(att.ref)
        if lo is None or hi is None or p is None:
            return
        x = p.x
        for target in (lo, hi):
            net = self._shared_net(p.ref, target.ref)
            if not net:
                continue
            self._route(p, target, net, toward=x)
        self._globals_for(p)

    def _route(self, source, target, net: str, toward: float) -> None:
        """Wire one pin to another, around every symbol body in the way."""
        spin = self._pin_name_at(source, net)
        tpin = self._pin_name_at(target, net)
        if spin is None or tpin is None:
            return
        ssym, tsym = self.sym(source.ref), self.sym(target.ref)
        a, b = pin_xy(source, ssym, spin), pin_xy(target, tsym, tpin)
        adir = pin_dir(source, ssym, spin)
        bdir = pin_dir(target, tsym, tpin)

        pts = route.route(self._obstacles(net), a, b, adir, bdir)
        if pts is None:
            # Nothing found: fall back to a plain L so the net is still drawn
            # rather than silently dropped. It may look wrong; it will not be
            # missing, and --check reports it.
            self.wire(a, b, net, source.traced)
        else:
            for p1, p2 in zip(pts, pts[1:]):
                self.wire(p1, p2, net, source.traced)
        self.sheet.junctions.append(b)

    def _obstacles(self, net: str):
        """Bodies and foreign pins the router must avoid, for one net."""
        pts = [(x, y) for x, y, n in self._pin_map() if n != net]
        return route.build(self._boxes(), pts, self.sheet.bounds())

    def _pin_map(self):
        """Every placed pin with its net. Rebuilt whenever placement changes."""
        if self._pins_cache is None:
            out = []
            for pl in self.sheet.placed:
                sym = self.sym(pl.ref)
                for pin in sym.units[pl.unit].pins:
                    px, py = pin_xy(pl, sym, pin)
                    n = self.cir.net_at(pl.ref, pin)
                    out.append((px, py, n.name if n else ""))
            self._pins_cache = out
        return self._pins_cache

    def _boxes(self):
        """Every placed symbol's drawn body, padded so wires do not graze."""
        if self._box_cache is None:
            self._box_cache = [
                box for box in
                (body_box(pl, self.sym(pl.ref), pad=GRID * 0.5)
                 for pl in self.sheet.placed)
                if box
            ]
        return self._box_cache

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
        net = self._shared_net(p.ref, host.ref)
        if net:
            a, b = self._pin_at(p, net), self._pin_at(host, net)
            if a and b:
                self.wire(b, a, net, p.traced)
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

    def _connect(self, a, b, orient: bool = False) -> None:
        net = self._shared_net(a.ref, b.ref)
        if not net:
            return
        if orient:
            self._face_left(b, net)
        pa, pb = self._pin_at(a, net), self._pin_at(b, net)
        if pa and pb:
            self.wire(pa, pb, net)

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
        """Every global pin terminates in a power symbol at the pin itself."""
        sym = self.sym(placed.ref)
        for pin in sym.units[placed.unit].pins:
            net = self.cir.net_at(placed.ref, pin)
            if not net or net.name not in self.lay.globals:
                continue
            at = pin_xy(placed, sym, pin)
            up = not net.name.lstrip().startswith("-") and \
                not net.name.upper().startswith(("GND", "0V"))
            if prefer_horizontal:
                end = (at[0] + (POWER_STUB if at[0] > placed.x else -POWER_STUB), at[1])
            else:
                end = (at[0], at[1] - POWER_STUB if up else at[1] + POWER_STUB)
            self.wire(at, end, net.name)
            if not self.power(net.name, end, 0.0 if up else 180.0):
                self.sheet.labels.append((end[0], end[1], net.name))

    def _loose_for(self, placed) -> None:
        """Label a pin whose net has no other part — an off-sheet connection."""
        sym = self.sym(placed.ref)
        for pin in sym.units[placed.unit].pins:
            net = self.cir.net_at(placed.ref, pin)
            if not net or net.name in self.lay.globals:
                continue
            if len({r for r, _ in net.pins}) > 1:
                continue
            at = pin_xy(placed, sym, pin)
            end = (at[0] - POWER_STUB * 1.5 if at[0] < placed.x
                   else at[0] + POWER_STUB * 1.5, at[1])
            self.wire(at, end, net.name)
            self.sheet.labels.append((end[0], end[1], net.name))

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
            p = self.place(stub, host_pin[0] + COL, host_pin[1])
            a = self._pin_at(p, net)
            if a:
                self.wire(host_pin, a, net)

    def _title(self) -> None:
        self.sheet.title = self.cir.title or "circuit"


def build(cir, lay) -> Sheet:
    return Placer(cir, lay).run()
