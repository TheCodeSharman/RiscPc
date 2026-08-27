"""Orthogonal wire routing around obstacles.

The first attempt picked a drop column from a ladder of offsets and checked
each against a list of pins. That is not enough: a column can miss every pin
and still run straight through a transistor, and when the ladder ran out the
fallback was far enough away that the wire crossed its *own* body getting
there. Both happened.

This does it properly — an A* over a coarse grid, with symbol bodies and
foreign pins as obstacles and a penalty per corner so routes come out
straight rather than staircased. The sheet is a few thousand cells, so the
search is not worth optimising.

Wires may still cross other wires; that is normal on a schematic and is what
junction dots are for. What they must never do is cross a body.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass

STEP = 2.54                 # routing grid, two KiCad grid units
TURN_COST = 6.0             # in units of STEP; high enough to prefer straight
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass
class Obstacles:
    boxes: list[tuple[float, float, float, float]]
    blocked_pts: list[tuple[float, float]]
    origin: tuple[float, float]
    size: tuple[int, int]

    def blocked(self, cx: int, cy: int) -> bool:
        x = self.origin[0] + cx * STEP
        y = self.origin[1] + cy * STEP
        for bx0, by0, bx1, by1 in self.boxes:
            if bx0 <= x <= bx1 and by0 <= y <= by1:
                return True
        for px, py in self.blocked_pts:
            if abs(px - x) < STEP * 0.75 and abs(py - y) < STEP * 0.75:
                return True
        return False


def build(boxes, blocked_pts, bounds, pad: float = 25.0) -> Obstacles:
    x0, y0, x1, y1 = bounds
    origin = (x0 - pad, y0 - pad)
    size = (int((x1 - x0 + 2 * pad) / STEP) + 2,
            int((y1 - y0 + 2 * pad) / STEP) + 2)
    return Obstacles(list(boxes), list(blocked_pts), origin, size)


def _cell(obs: Obstacles, p) -> tuple[int, int]:
    return (round((p[0] - obs.origin[0]) / STEP),
            round((p[1] - obs.origin[1]) / STEP))


def _point(obs: Obstacles, c) -> tuple[float, float]:
    return (obs.origin[0] + c[0] * STEP, obs.origin[1] + c[1] * STEP)


def route(obs: Obstacles, start, goal, start_dir=None, goal_dir=None):
    """A* from start to goal. Returns a list of points, or None.

    `start_dir` / `goal_dir` force the wire to leave and arrive along a pin's
    own axis, which is what stops it cutting across the symbol it belongs to.
    """
    s, g = _cell(obs, start), _cell(obs, goal)
    if s == g:
        return [start, goal]

    W, H = obs.size
    in_bounds = lambda c: 0 <= c[0] < W and 0 <= c[1] < H

    # The endpoints sit on their own pins, so they are exempt from blocking.
    free = {s, g}
    blocked_cache: dict[tuple[int, int], bool] = {}

    def is_blocked(c):
        if c in free:
            return False
        if c not in blocked_cache:
            blocked_cache[c] = obs.blocked(*c)
        return blocked_cache[c]

    def h(c):
        return (abs(c[0] - g[0]) + abs(c[1] - g[1]))

    start_states = []
    if start_dir:
        d = (round(start_dir[0]), round(start_dir[1]))
        if d in DIRS:
            start_states.append((s, d))
    if not start_states:
        start_states = [(s, d) for d in DIRS]

    openq = [(h(s), 0.0, st) for st in start_states]
    heapq.heapify(openq)
    best: dict[tuple, float] = {st: 0.0 for st in start_states}
    prev: dict[tuple, tuple] = {}

    goal_dirs = None
    if goal_dir:
        d = (round(-goal_dir[0]), round(-goal_dir[1]))
        if d in DIRS:
            goal_dirs = {d}

    limit = W * H * 4
    seen = 0
    while openq:
        _, cost, state = heapq.heappop(openq)
        seen += 1
        if seen > limit:
            return None
        c, d = state
        if cost > best.get(state, 1e18):
            continue
        if c == g and (goal_dirs is None or d in goal_dirs):
            return _rebuild(obs, prev, state)
        for nd in DIRS:
            if nd == (-d[0], -d[1]):
                continue            # no doubling back
            nc = (c[0] + nd[0], c[1] + nd[1])
            if not in_bounds(nc) or is_blocked(nc):
                continue
            step = 1.0 + (TURN_COST if nd != d else 0.0)
            ns = (nc, nd)
            ncost = cost + step
            if ncost < best.get(ns, 1e18):
                best[ns] = ncost
                prev[ns] = state
                heapq.heappush(openq, (ncost + h(nc), ncost, ns))
    return None


def _rebuild(obs, prev, state):
    cells = []
    while state in prev:
        cells.append(state[0])
        state = prev[state]
    cells.append(state[0])
    cells.reverse()

    # Collapse collinear runs so the output is corners, not every cell.
    pts = [_point(obs, cells[0])]
    for i in range(1, len(cells) - 1):
        ax, ay = cells[i - 1]
        bx, by = cells[i]
        cx, cy = cells[i + 1]
        if (bx - ax, by - ay) != (cx - bx, cy - by):
            pts.append(_point(obs, cells[i]))
    pts.append(_point(obs, cells[-1]))
    return pts
