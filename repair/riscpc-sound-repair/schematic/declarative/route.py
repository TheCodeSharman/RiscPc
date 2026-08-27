"""Orthogonal wire routing: a shared occupancy grid, one Steiner tree per net.

Two earlier attempts failed, and the way they failed is the design rationale.

The first picked a drop column from a ladder of offsets and checked it against
a list of pins. A column can miss every pin and still run through a transistor.

The second was an A* per *edge* — good routes, wrong unit of work. Two things
follow from routing edges independently, and both were visible in the drawing:

  * a net with four pins on it left four separate wires radiating from one
    pin, piled on top of each other. A net is a **tree**, not a bag of paths.
  * nothing knew where any other net had been, so two nets could lie on the
    same line. That is not a smudge, it is a short — and it is invisible,
    which is why `verify.py` exists.

So: one grid, shared by every net, and the router is asked for a whole net at
a time. The first two pins are joined; each remaining pin is then routed to
*whatever of its own net is already on the grid*, which is what makes a
T-junction appear where a T-junction belongs.

The occupancy rules are the schematic's own, not a proximity test:

  * a cell may be shared by two nets only if they pass through it straight
    and on **different axes** — that is a crossing, and a crossing without a
    junction dot is not a connection;
  * a **corner** may not sit on a foreign net: our vertex would land on their
    wire, which is a connection;
  * an **endpoint** may not sit on a foreign net, for the same reason;
  * running along a foreign net on the same axis is forbidden outright.

Symbol bodies and foreign pins are hard obstacles. Corners cost, so routes
come out straight, and reusing our own net's cells is free, so the tree
prefers to branch off an existing run rather than draw a parallel one.
"""

from __future__ import annotations

import heapq
from collections import defaultdict

STEP = 1.27                 # routing grid — KiCad's own, so nothing snaps later
TURN_COST = 8.0             # in units of STEP; high enough to prefer straight
CROSS_COST = 10.0           # crossing a foreign net is legal but not free
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))

H, V = "h", "v"


def _axis(d) -> str:
    return H if d[0] else V


class Grid:
    """Everything already committed to the sheet, in routing coordinates."""

    def __init__(self, bounds, pad: float = 30.0) -> None:
        x0, y0, x1, y1 = bounds
        self.origin = (x0 - pad, y0 - pad)
        self.size = (int((x1 - x0 + 2 * pad) / STEP) + 2,
                     int((y1 - y0 + 2 * pad) / STEP) + 2)
        self.bodies: set[tuple[int, int]] = set()
        # cell -> net -> axes in use. "pin" is an axis nothing may share.
        self.used: dict[tuple[int, int], dict[str, set[str]]] = defaultdict(dict)
        self._exempt: set[tuple[int, int]] = set()   # endpoints of the route in hand

    # --- coordinates --------------------------------------------------
    def cell(self, p) -> tuple[int, int]:
        return (round((p[0] - self.origin[0]) / STEP),
                round((p[1] - self.origin[1]) / STEP))

    def point(self, c) -> tuple[float, float]:
        return (self.origin[0] + c[0] * STEP, self.origin[1] + c[1] * STEP)

    def in_bounds(self, c) -> bool:
        return 0 <= c[0] < self.size[0] and 0 <= c[1] < self.size[1]

    # --- what is on the sheet -----------------------------------------
    def add_body(self, box) -> None:
        """Block every cell inside a symbol's drawn body."""
        x0, y0, x1, y1 = box
        c0, c1 = self.cell((x0, y0)), self.cell((x1, y1))
        for cx in range(c0[0], c1[0] + 1):
            for cy in range(c0[1], c1[1] + 1):
                self.bodies.add((cx, cy))

    def add_pin(self, p, net: str) -> None:
        """A pin is its net's, absolutely: no other net may touch that cell."""
        self.used[self.cell(p)].setdefault(net, set()).add("pin")

    def occupy(self, pts, net: str) -> None:
        """Mark a routed polyline as belonging to `net`."""
        for a, b in zip(pts, pts[1:]):
            ca, cb = self.cell(a), self.cell(b)
            ax = H if ca[1] == cb[1] else V
            i = 0 if ax == H else 1
            lo, hi = sorted((ca[i], cb[i]))
            for k in range(lo, hi + 1):
                c = (k, ca[1]) if ax == H else (ca[0], k)
                self.used[c].setdefault(net, set()).add(ax)

    def cells_of(self, net: str) -> set[tuple[int, int]]:
        return {c for c, nets in self.used.items() if net in nets}

    def path_cells(self, pts) -> set[tuple[int, int]]:
        """Every cell a polyline passes through."""
        out = set()
        for a, b in zip(pts, pts[1:]):
            ca, cb = self.cell(a), self.cell(b)
            i = 0 if ca[1] == cb[1] else 1
            lo, hi = sorted((ca[i], cb[i]))
            for k in range(lo, hi + 1):
                out.add((k, ca[1]) if i == 0 else (ca[0], k))
        return out

    def clear(self, a, b, net: str) -> bool:
        """Is a straight run from a to b free for `net`, endpoint included?"""
        ca, cb = self.cell(a), self.cell(b)
        if ca == cb:
            return False
        ax = H if ca[1] == cb[1] else V
        if ca[0] != cb[0] and ca[1] != cb[1]:
            return False
        i = 0 if ax == H else 1
        lo, hi = sorted((ca[i], cb[i]))
        # The run starts on its own pin, which is marked under the pin's real
        # net rather than this stub's key, so skip it: a stub is always
        # allowed to leave the pin it belongs to.
        for k in range(lo, hi + 1):
            c = (k, ca[1]) if ax == H else (ca[0], k)
            if c == ca:
                continue
            if not self.in_bounds(c):
                return False
            if self._passable(c, net, {ax}, terminal=(c == cb)) is None:
                return False
        return True

    # --- the rules ----------------------------------------------------
    def _foreign(self, c, net: str):
        nets = self.used.get(c)
        if not nets:
            return None
        return {n: ax for n, ax in nets.items() if n != net} or None

    def _passable(self, c, net: str, axes: set[str], terminal: bool) -> float | None:
        """Cost of using cell `c` on `axes`, or None if we may not.

        `terminal` means our wire stops here, so it may not share the cell at
        all — an endpoint on someone else's wire is a connection, not a
        crossing.
        """
        if c in self.bodies and c not in self._exempt:
            return None
        foreign = self._foreign(c, net)
        if not foreign:
            return 0.0
        if terminal or len(axes) > 1:
            return None                 # endpoint or corner on a foreign net
        for used in foreign.values():
            if "pin" in used or axes & used:
                return None
        return CROSS_COST

    # --- search -------------------------------------------------------
    def route(self, net: str, start, goals, start_dir=None, goal_dirs=None):
        """A* from one pin to a *set* of goal points. Returns points or None.

        `goals` is a set of sheet points — for the second and later pins of a
        net it is every cell that net already occupies, which is what turns a
        sequence of routes into a tree.
        """
        s = self.cell(start)
        gset = {self.cell(g) for g in goals}
        gset.discard(s)
        if not gset:
            return None
        if s in gset:
            return [start, start]

        self._exempt = {s} | gset
        gx = (min(c[0] for c in gset), max(c[0] for c in gset))
        gy = (min(c[1] for c in gset), max(c[1] for c in gset))

        def h(c) -> float:
            dx = max(gx[0] - c[0], 0, c[0] - gx[1])
            dy = max(gy[0] - c[1], 0, c[1] - gy[1])
            return dx + dy

        arrive = None
        if goal_dirs:
            arrive = {(round(-d[0]), round(-d[1])) for d in goal_dirs}

        starts = []
        if start_dir:
            d = (round(start_dir[0]), round(start_dir[1]))
            if d in DIRS:
                starts.append(d)
        if not starts:
            starts = list(DIRS)

        openq = [(h(s), 0.0, (s, d)) for d in starts]
        heapq.heapify(openq)
        best: dict = {(s, d): 0.0 for d in starts}
        prev: dict = {}
        limit = self.size[0] * self.size[1] * 4
        seen = 0

        while openq:
            _, cost, state = heapq.heappop(openq)
            if cost > best.get(state, 1e18):
                continue
            seen += 1
            if seen > limit:
                self._exempt = set()
                return None
            c, d = state
            if c in gset and (arrive is None or d in arrive):
                if self._passable(c, net, {_axis(d)}, terminal=True) is not None:
                    self._exempt = set()
                    return self._rebuild(prev, state)
            for nd in DIRS:
                if nd == (-d[0], -d[1]):
                    continue                    # no doubling back
                axes = {_axis(d), _axis(nd)}
                here = self._passable(c, net, axes, terminal=False)
                if here is None:
                    continue
                nc = (c[0] + nd[0], c[1] + nd[1])
                if not self.in_bounds(nc):
                    continue
                if self._passable(nc, net, {_axis(nd)}, terminal=False) is None:
                    continue
                step = 1.0 + here + (TURN_COST if nd != d else 0.0)
                ns = (nc, nd)
                nxt = cost + step
                if nxt < best.get(ns, 1e18):
                    best[ns] = nxt
                    prev[ns] = state
                    heapq.heappush(openq, (nxt + h(nc), nxt, ns))
        self._exempt = set()
        return None

    def _rebuild(self, prev, state):
        cells = []
        while state in prev:
            cells.append(state[0])
            state = prev[state]
        cells.append(state[0])
        cells.reverse()
        pts = [self.point(cells[0])]
        for i in range(1, len(cells) - 1):
            a, b, c = cells[i - 1], cells[i], cells[i + 1]
            if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
                pts.append(self.point(cells[i]))
        pts.append(self.point(cells[-1]))
        return pts
