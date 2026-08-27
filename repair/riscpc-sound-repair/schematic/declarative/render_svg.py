"""Render a placed sheet to SVG.

Symbol artwork is read out of KiCad's own libraries and translated primitive
by primitive, so this is a preview of the KiCad output rather than a separate
drawing that happens to look similar. If a symbol comes out wrong here it will
come out wrong there too, which is the point of previewing in SVG first.

KiCad symbol space has y up; the sheet has y down. Every primitive is flipped
on y as it is emitted.
"""

from __future__ import annotations

import math
import re

import symbols
from geometry import Sheet

PX = 4.0                # px per mm
PAD = 40.0

STROKE = "#1a1a1a"
WIRE = "#1a6b1a"
PIN = "#8b1a1a"
TEXT = "#1a1a1a"
VALUE = "#8b1a1a"
GREY = "#999999"
FILL = "#fffce8"


def _num(s: str) -> float:
    return float(s)


def _pts(body: str) -> list[tuple[float, float]]:
    return [(_num(x), _num(y)) for x, y in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", body)]


def _fill_for(blk: str, colour: str) -> str:
    """KiCad fill types.

    `outline` means fill with the outline colour — that is what makes a
    transistor arrowhead solid. `background` means the sheet's body colour,
    as on an op-amp triangle. Treating outline as background was drawing the
    arrowheads in cream, so they disappeared.
    """
    m = re.search(r"\(fill\s*\(type (\w+)\)", blk)
    kind = m.group(1) if m else "none"
    if kind == "outline":
        return colour
    if kind == "background":
        return FILL
    return "none"


def _blocks(body: str, head: str) -> list[str]:
    """Every balanced `(head ...)` block in body."""
    out, i = [], 0
    while True:
        j = body.find(f"({head}", i)
        if j < 0:
            return out
        depth, k, instr = 0, j, False
        while k < len(body):
            ch = body[k]
            if ch == '"' and body[k - 1] != "\\":
                instr = not instr
            if not instr:
                depth += (ch == "(") - (ch == ")")
            k += 1
            if depth == 0:
                break
        out.append(body[j:k])
        # Step past the opener only, not the whole block — a symbol's unit
        # sub-symbols are nested inside it, and skipping to the end hid them.
        i = j + 1


class Renderer:
    def __init__(self, sheet: Sheet, cir):
        self.sheet = sheet
        self.cir = cir
        self.out: list[str] = []
        self._syms: dict[str, symbols.Symbol] = {}

    def sym(self, placed):
        key = placed.lib_id
        if key not in self._syms:
            if key.startswith("Generated:"):
                self._syms[key] = symbols.generate_box(self.cir.parts[placed.ref])
            else:
                self._syms[key] = symbols.load(key)
        return self._syms[key]

    # --- transforms ---------------------------------------------------
    def xf(self, placed, x: float, y: float) -> tuple[float, float]:
        th = math.radians(placed.angle)
        rx = x * math.cos(th) - y * math.sin(th)
        ry = x * math.sin(th) + y * math.cos(th)
        if placed.mirror == "y":
            rx = -rx
        return (placed.x + rx, placed.y - ry)

    def P(self, x: float, y: float) -> tuple[float, float]:
        return ((x - self.x0) * PX + PAD, (y - self.y0) * PX + PAD)

    # --- primitives ---------------------------------------------------
    def _shape(self, placed, blk: str, kind: str, colour: str) -> None:
        w = 0.2 * PX
        if kind == "rectangle":
            m = re.search(r"\(start ([-\d.]+) ([-\d.]+)\).*?\(end ([-\d.]+) ([-\d.]+)\)",
                          blk, re.S)
            if not m:
                return
            ax, ay, bx, by = (_num(g) for g in m.groups())
            c = [self.P(*self.xf(placed, x, y))
                 for x, y in ((ax, ay), (bx, ay), (bx, by), (ax, by))]
            pts = " ".join(f"{p[0]:.2f},{p[1]:.2f}" for p in c)
            self.out.append(
                f'<polygon points="{pts}" fill="{_fill_for(blk, colour)}" '
                f'stroke="{colour}" stroke-width="{w:.2f}"/>'
            )
        elif kind in ("polyline", "bezier"):
            c = [self.P(*self.xf(placed, x, y)) for x, y in _pts(blk)]
            if len(c) < 2:
                return
            pts = " ".join(f"{p[0]:.2f},{p[1]:.2f}" for p in c)
            self.out.append(
                f'<polyline points="{pts}" fill="{_fill_for(blk, colour)}" '
                f'stroke="{colour}" stroke-width="{w:.2f}" '
                f'stroke-linejoin="round" stroke-linecap="round"/>'
            )
        elif kind == "circle":
            m = re.search(r"\(center ([-\d.]+) ([-\d.]+)\).*?\(radius ([-\d.]+)\)",
                          blk, re.S)
            if not m:
                return
            cx, cy = self.P(*self.xf(placed, _num(m.group(1)), _num(m.group(2))))
            r = _num(m.group(3)) * PX
            self.out.append(
                f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
                f'fill="{_fill_for(blk, colour)}" stroke="{colour}" '
                f'stroke-width="{w:.2f}"/>'
            )
        elif kind == "arc":
            m = re.findall(r"\((?:start|mid|end) ([-\d.]+) ([-\d.]+)\)", blk)
            if len(m) < 3:
                return
            a, mid, b = [self.P(*self.xf(placed, _num(x), _num(y))) for x, y in m[:3]]
            self.out.append(
                f'<path d="M {a[0]:.2f},{a[1]:.2f} Q {mid[0]:.2f},{mid[1]:.2f} '
                f'{b[0]:.2f},{b[1]:.2f}" fill="none" stroke="{colour}" '
                f'stroke-width="{w:.2f}"/>'
            )

    def _pins(self, placed, sym, colour: str) -> None:
        unit = sym.units[placed.unit]
        for pin in unit.pins.values():
            th = math.radians(pin.angle)
            ex = pin.x + pin.length * math.cos(th)
            ey = pin.y + pin.length * math.sin(th)
            a = self.P(*self.xf(placed, pin.x, pin.y))
            b = self.P(*self.xf(placed, ex, ey))
            self.out.append(
                f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" '
                f'y2="{b[1]:.2f}" stroke="{colour}" stroke-width="{0.2*PX:.2f}"/>'
            )
            self.out.append(
                f'<circle cx="{a[0]:.2f}" cy="{a[1]:.2f}" r="{0.35*PX:.2f}" '
                f'fill="none" stroke="{PIN}" stroke-width="0.6" opacity="0.55"/>'
            )
            tx, ty = self.P(*self.xf(placed, pin.x - 0.6 * math.cos(th),
                                     pin.y - 0.6 * math.sin(th)))
            self.out.append(
                f'<text x="{tx:.2f}" y="{ty:.2f}" font-size="{1.0*PX:.1f}" '
                f'fill="{PIN}" text-anchor="middle" opacity="0.75">{pin.number}</text>'
            )

    # --- sheet --------------------------------------------------------
    def run(self) -> str:
        x0, y0, x1, y1 = self.sheet.bounds()
        self.x0, self.y0 = x0 - 14, y0 - 16
        w = (x1 - x0 + 30) * PX + 2 * PAD
        h = (y1 - y0 + 34) * PX + 2 * PAD

        self.out.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" '
            f'height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}">'
        )
        self.out.append(f'<rect width="{w:.0f}" height="{h:.0f}" fill="#ffffff"/>')
        self.out.append(
            '<style>text{font-family:"DejaVu Sans",Helvetica,Arial,sans-serif}</style>'
        )

        if self.sheet.title:
            self.out.append(
                f'<text x="{PAD:.0f}" y="{PAD*0.6:.0f}" font-size="16" '
                f'fill="{TEXT}">{_esc(self.sheet.title)}</text>'
            )

        for wire in self.sheet.wires:
            col = GREY if not wire.traced else WIRE
            pts = " ".join(f"{p[0]:.2f},{p[1]:.2f}"
                           for p in (self.P(*q) for q in wire.pts))
            self.out.append(
                f'<polyline points="{pts}" fill="none" stroke="{col}" '
                f'stroke-width="{0.25*PX:.2f}" stroke-linecap="round"/>'
            )

        for jx, jy in self.sheet.junctions:
            p = self.P(jx, jy)
            self.out.append(
                f'<circle cx="{p[0]:.2f}" cy="{p[1]:.2f}" r="{0.45*PX:.2f}" '
                f'fill="{WIRE}"/>'
            )

        for placed in self.sheet.placed:
            self._symbol(placed)

        for pw in self.sheet.powers:
            self._power(pw)

        for lx, ly, text in self.sheet.labels:
            p = self.P(lx, ly)
            self.out.append(
                f'<text x="{p[0]:.2f}" y="{p[1]-4:.2f}" font-size="{1.1*PX:.1f}" '
                f'fill="{VALUE}" text-anchor="middle">{_esc(text)}</text>'
            )

        self.out.append("</svg>")
        return "\n".join(self.out)

    def _symbol(self, placed) -> None:
        sym = self.sym(placed)
        colour = GREY if not placed.traced else STROKE
        name = sym.art_name or sym.lib_id.split(":", 1)[1]
        pat = re.compile(rf'\(symbol "{re.escape(name)}_(\d+)_')
        unit_bodies = [
            b for b in _blocks(sym.art_body or sym.body, "symbol")
            if (m := pat.match(b)) and int(m.group(1)) in (0, placed.unit)
        ]
        for body in unit_bodies:
            for kind in ("rectangle", "polyline", "circle", "arc", "bezier"):
                for blk in _blocks(body, kind):
                    self._shape(placed, blk, kind, colour)
        self._pins(placed, sym, colour)

        p = self.P(placed.x, placed.y)
        dy = 9 * (1 if placed.angle in (0.0, 180.0) else 1)
        self.out.append(
            f'<text x="{p[0]:.2f}" y="{p[1]-dy-10:.2f}" font-size="{1.2*PX:.1f}" '
            f'fill="{colour}" text-anchor="middle">{_esc(placed.ref)}</text>'
        )
        if placed.value:
            self.out.append(
                f'<text x="{p[0]:.2f}" y="{p[1]+dy+16:.2f}" font-size="{1.1*PX:.1f}" '
                f'fill="{GREY if not placed.traced else VALUE}" '
                f'text-anchor="middle">{_esc(placed.value)}</text>'
            )

    def _power(self, pw) -> None:
        p = self.P(pw.x, pw.y)
        up = pw.angle == 0.0
        ground = pw.net.upper().startswith(("GND", "AGND", "DGND", "0V"))
        d = 0.9 * PX
        if not up and not ground:
            self.out.append(
                f'<polyline points="{p[0]-d:.2f},{p[1]+d:.2f} {p[0]:.2f},'
                f'{p[1]+2*d:.2f} {p[0]+d:.2f},{p[1]+d:.2f}" fill="none" '
                f'stroke="{PIN}" stroke-width="1.4"/>'
            )
            self.out.append(
                f'<text x="{p[0]:.2f}" y="{p[1]+2*d+11:.2f}" '
                f'font-size="{1.1*PX:.1f}" fill="{PIN}" '
                f'text-anchor="middle">{_esc(pw.net)}</text>'
            )
            return
        if up:
            self.out.append(
                f'<polyline points="{p[0]-d:.2f},{p[1]-d:.2f} {p[0]:.2f},'
                f'{p[1]-2*d:.2f} {p[0]+d:.2f},{p[1]-d:.2f}" fill="none" '
                f'stroke="{PIN}" stroke-width="1.4"/>'
            )
            ty = p[1] - 2 * d - 4
        else:
            for i, k in enumerate((1.0, 0.62, 0.28)):
                yy = p[1] + d * (0.5 + i * 0.55)
                self.out.append(
                    f'<line x1="{p[0]-d*k:.2f}" y1="{yy:.2f}" x2="{p[0]+d*k:.2f}" '
                    f'y2="{yy:.2f}" stroke="{PIN}" stroke-width="1.4"/>'
                )
            ty = p[1] + d * 3.2 + 9
        self.out.append(
            f'<text x="{p[0]:.2f}" y="{ty:.2f}" font-size="{1.1*PX:.1f}" '
            f'fill="{PIN}" text-anchor="middle">{_esc(pw.net)}</text>'
        )


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render(sheet: Sheet, cir) -> str:
    return Renderer(sheet, cir).run()
