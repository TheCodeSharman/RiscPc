"""Turn a layout into absolute coordinates and wires.

Format-agnostic on purpose: this is the shared stage between the SVG preview
and the KiCad writer, so routing is solved once. Everything is in millimetres
on KiCad's 1.27 mm grid, with y increasing downwards (schematic convention,
not symbol-library convention — the library has y up, and `pin_xy` flips it).

Routing avoids overlaps structurally rather than by search. The layout has
already split each lane into a spine, bridges over it and stubs under it, so:

  * spine parts sit in a row and wire to their neighbour horizontally — two
    consecutive parts cannot collide;
  * a bridge gets its own tier above the row, and drops verticals at its own
    x extent, clear of the spine;
  * a stub gets its own vertical below the row, at its host's x;
  * a global net never routes at all — it terminates in a power symbol at
    the pin.

The only remaining collision risk is two bridges sharing a span, and
layout.py has already assigned them different tiers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import symbols

GRID = 1.27
COL = GRID * 12          # spine pitch
ROW = GRID * 28          # vertical distance between lanes
TIER = GRID * 12         # height of one bridge tier above the row
STUB = GRID * 8          # drop from the row to a stub part


def snap(v: float) -> float:
    return round(v / GRID) * GRID


@dataclass
class Placed:
    ref: str
    lib_id: str
    unit: int
    x: float
    y: float
    angle: float = 0.0        # degrees, counter-clockwise
    mirror: str | None = None
    value: str = ""
    traced: bool = True
    pins: dict[str, str] = field(default_factory=dict)   # pin -> net


@dataclass
class Wire:
    pts: list[tuple[float, float]]
    net: str
    traced: bool = True


@dataclass
class PowerPin:
    lib_id: str
    net: str
    x: float
    y: float
    angle: float = 0.0


@dataclass
class Sheet:
    placed: list[Placed] = field(default_factory=list)
    wires: list[Wire] = field(default_factory=list)
    powers: list[PowerPin] = field(default_factory=list)
    junctions: list[tuple[float, float]] = field(default_factory=list)
    labels: list[tuple[float, float, str]] = field(default_factory=list)
    title: str = ""

    def bounds(self):
        xs = [p.x for p in self.placed] + [x for w in self.wires for x, _ in w.pts]
        ys = [p.y for p in self.placed] + [y for w in self.wires for _, y in w.pts]
        return (min(xs, default=0), min(ys, default=0),
                max(xs, default=0), max(ys, default=0))


def pin_xy(placed: Placed, sym: symbols.Symbol, pin: str) -> tuple[float, float]:
    """Absolute position of a pin's *endpoint* — where a wire must meet it.

    The library defines pins with y up and `at` giving the connection end;
    the schematic has y down, hence the negation.
    """
    p = sym.units[placed.unit].pins[pin]
    px, py = p.x, p.y
    th = math.radians(placed.angle)
    rx = px * math.cos(th) - py * math.sin(th)
    ry = px * math.sin(th) + py * math.cos(th)
    if placed.mirror == "y":
        rx = -rx
    return (snap(placed.x + rx), snap(placed.y - ry))


def pin_dir(placed: Placed, sym: symbols.Symbol, pin: str) -> tuple[float, float]:
    """Unit vector pointing *out* of the body along the pin, in sheet space.

    A library pin's angle points from its endpoint into the body, so outward
    is the opposite. Wires must approach along this direction, otherwise they
    cut across the symbol they are trying to reach.
    """
    p = sym.units[placed.unit].pins[pin]
    a = math.radians(p.angle)
    ox, oy = -math.cos(a), -math.sin(a)
    th = math.radians(placed.angle)
    rx = ox * math.cos(th) - oy * math.sin(th)
    ry = ox * math.sin(th) + oy * math.cos(th)
    if placed.mirror == "y":
        rx = -rx
    n = math.hypot(rx, ry) or 1.0
    return (round(rx / n, 6), round(-ry / n, 6))


def _two_terminal_angle(sym: symbols.Symbol, unit: int) -> float:
    """Angle that lays a two-pin symbol out horizontally.

    Device:R and friends are drawn vertically in the library, so they need
    rotating; a symbol already drawn horizontally does not.
    """
    pins = list(sym.units[unit].pins.values())
    if len(pins) != 2:
        return 0.0
    dx = abs(pins[0].x - pins[1].x)
    dy = abs(pins[0].y - pins[1].y)
    return 90.0 if dy > dx else 0.0


class Builder:
    def __init__(self, cir, lay):
        self.cir = cir
        self.lay = lay
        self.sheet = Sheet()
        self._syms: dict[str, symbols.Symbol] = {}

    def sym(self, ref: str) -> symbols.Symbol:
        if ref not in self._syms:
            self._syms[ref] = symbols.for_part(self.cir.parts[ref])
        return self._syms[ref]

    # --- placement ----------------------------------------------------
    def place(self, ref: str, x: float, y: float, unit: int | None = None,
              angle: float | None = None) -> Placed:
        part = self.cir.parts[ref]
        sym = self.sym(ref)
        if unit is None:
            unit = sym.unit_for(part.pins) if len(sym.units) > 1 else \
                next(iter(sym.units))
        if angle is None:
            angle = _two_terminal_angle(sym, unit)
        p = Placed(
            ref=ref, lib_id=sym.lib_id, unit=unit,
            x=snap(x), y=snap(y), angle=angle,
            value=part.value, traced=part.traced,
        )
        self.sheet.placed.append(p)
        return p

    def net_of(self, ref: str, pin: str) -> str:
        n = self.cir.net_at(ref, pin)
        return n.name if n else ""

    # --- wiring -------------------------------------------------------
    def wire(self, a, b, net: str, traced: bool = True) -> None:
        """An orthogonal run from a to b: horizontal, then vertical."""
        (ax, ay), (bx, by) = a, b
        if abs(ax - bx) < 1e-6 or abs(ay - by) < 1e-6:
            pts = [(ax, ay), (bx, by)]
        else:
            pts = [(ax, ay), (bx, ay), (bx, by)]
        self.sheet.wires.append(Wire(pts=pts, net=net, traced=traced))

    def power(self, net: str, at, angle: float = 0.0) -> bool:
        """Terminate a global net in a power symbol. Returns False if unmapped."""
        lib_id = symbols.power_lib_id(net)
        if not lib_id:
            return False
        self.sheet.powers.append(
            PowerPin(lib_id=lib_id, net=net, x=at[0], y=at[1], angle=angle)
        )
        return True
