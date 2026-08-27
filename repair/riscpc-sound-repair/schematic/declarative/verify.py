"""Rebuild the netlist from the drawn geometry and compare it to the source.

`render.py --check` asks "does a wire cross a body?" — a question about
tidiness. This asks the only question that actually matters: **is the drawing
the circuit?**

It throws the netlist away and reads the picture back the way KiCad reads a
sheet — pins, wire segments, junction dots, power symbols, labels — unions
whatever touches, and compares the partition it gets against the partition the
`.cir` asked for. Two pins that ended up on one node when they should not have
is a short; a net that came out in pieces is an open.

This catches the class of bug that `--check` cannot see. `Rfb_R`'s two legs
both dropped onto one horizontal wire, so a 47k feedback resistor was drawn
short-circuited — no wire crossed any body, and `--check` said "ok".

The connectivity model is KiCad's, not "lines that look near each other":

  * wire endpoints at the same point connect;
  * a wire endpoint landing on another wire's *interior* connects (KiCad
    infers the junction);
  * two wires **crossing** interior-to-interior do **not** connect unless a
    junction dot sits on the crossing — this is the whole reason a schematic
    can be drawn flat at all;
  * two collinear wires that **overlap** connect, because they share more than
    a point. This is the one that bites, because it is invisible;
  * a pin connects to a wire it touches, at an endpoint or mid-span;
  * power symbols and labels of the same name are one node, sheet-wide.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import geometry
import symbols

EPS = 1e-6

HORIZONTAL = "h"
VERTICAL = "v"
DIAGONAL = "d"


# --- geometry ---------------------------------------------------------------

@dataclass(frozen=True)
class Seg:
    """One straight run of wire, normalised so a <= b along its axis."""
    a: tuple[float, float]
    b: tuple[float, float]
    net: str                 # what the router *intended*; used only in reports
    axis: str

    @property
    def fixed(self) -> float:
        return self.a[1] if self.axis == HORIZONTAL else self.a[0]

    @property
    def span(self) -> tuple[float, float]:
        i = 0 if self.axis == HORIZONTAL else 1
        return (self.a[i], self.b[i])


def _axis(p, q) -> str:
    if abs(p[1] - q[1]) < EPS:
        return HORIZONTAL
    if abs(p[0] - q[0]) < EPS:
        return VERTICAL
    return DIAGONAL


def _make(p, q, net: str) -> Seg | None:
    ax = _axis(p, q)
    if ax == DIAGONAL:
        return Seg(p, q, net, DIAGONAL)
    if p > q:
        p, q = q, p
    if abs(p[0] - q[0]) < EPS and abs(p[1] - q[1]) < EPS:
        return None                      # zero length; nothing to connect
    return Seg(p, q, net, ax)


def _on(seg: Seg, pt) -> str | None:
    """Where `pt` sits on `seg`: "end", "interior", or None."""
    if seg.axis == DIAGONAL:
        for e in (seg.a, seg.b):
            if abs(e[0] - pt[0]) < EPS and abs(e[1] - pt[1]) < EPS:
                return "end"
        return None
    i, j = (0, 1) if seg.axis == HORIZONTAL else (1, 0)
    if abs(pt[j] - seg.fixed) > EPS:
        return None
    lo, hi = seg.span
    if pt[i] < lo - EPS or pt[i] > hi + EPS:
        return None
    if abs(pt[i] - lo) < EPS or abs(pt[i] - hi) < EPS:
        return "end"
    return "interior"


def _overlap(s: Seg, t: Seg) -> tuple[float, float] | None:
    """The shared run of two collinear segments, if it is longer than a point."""
    if s.axis != t.axis or s.axis == DIAGONAL:
        return None
    if abs(s.fixed - t.fixed) > EPS:
        return None
    lo = max(s.span[0], t.span[0])
    hi = min(s.span[1], t.span[1])
    return (lo, hi) if hi - lo > EPS else None


def _cross(s: Seg, t: Seg) -> tuple[float, float] | None:
    """Interior-to-interior crossing of a horizontal and a vertical segment."""
    if {s.axis, t.axis} != {HORIZONTAL, VERTICAL}:
        return None
    h, v = (s, t) if s.axis == HORIZONTAL else (t, s)
    if not (v.span[0] < h.fixed - EPS < v.span[1] - EPS):
        return None
    if not (h.span[0] < v.fixed - EPS < h.span[1] - EPS):
        return None
    return (v.fixed, h.fixed)


# --- union-find -------------------------------------------------------------

class _UF:
    def __init__(self) -> None:
        self.parent: dict = {}
        self.why: dict = {}          # child -> (other, reason, at)

    def add(self, x):
        self.parent.setdefault(x, x)
        return x

    def find(self, x):
        self.add(x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b, reason: str, at) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        self.parent[rb] = ra
        self.why[rb] = (a, b, reason, at)


# --- the check --------------------------------------------------------------

@dataclass
class Finding:
    kind: str                # "short" | "open" | "overlap" | "diagonal"
    detail: str

    def __str__(self) -> str:
        return f"{self.kind.upper():9} {self.detail}"


def _pin_positions(cir, sheet):
    """Every pin actually drawn, as ("R1", "2") -> (x, y)."""
    out: dict[tuple[str, str], tuple[float, float]] = {}
    for placed in sheet.placed:
        sym = symbols.for_part(cir.parts[placed.ref])
        for pin in sym.units[placed.unit].pins:
            out[(placed.ref, pin)] = geometry.pin_xy(placed, sym, pin)
    return out


def _segments(sheet) -> list[Seg]:
    segs = []
    for wire in sheet.wires:
        for p, q in zip(wire.pts, wire.pts[1:]):
            s = _make(p, q, wire.net)
            if s is not None:
                segs.append(s)
    return segs


def check(cir, sheet) -> list[Finding]:
    """Read the sheet back and report every way it disagrees with the source."""
    findings: list[Finding] = []
    segs = _segments(sheet)
    pins = _pin_positions(cir, sheet)
    junctions = {(round(x, 6), round(y, 6)) for x, y in sheet.junctions}

    uf = _UF()
    for i in range(len(segs)):
        uf.add(("seg", i))
    for key in pins:
        uf.add(("pin",) + key)

    # 1. Segment against segment.
    for i, s in enumerate(segs):
        for j in range(i + 1, len(segs)):
            t = segs[j]
            ov = _overlap(s, t)
            if ov is not None:
                uf.union(("seg", i), ("seg", j), "overlap", ov)
                if s.net != t.net:
                    findings.append(Finding(
                        "overlap",
                        f"nets {s.net} and {t.net} share a {s.axis} run "
                        f"at {_fmt(s.fixed)} over {_fmt(ov[0])}..{_fmt(ov[1])}"))
                continue
            touched = False
            for end in (t.a, t.b):
                if _on(s, end):
                    uf.union(("seg", i), ("seg", j), "endpoint", end)
                    touched = True
                    break
            if touched:
                continue
            for end in (s.a, s.b):
                if _on(t, end):
                    uf.union(("seg", i), ("seg", j), "endpoint", end)
                    touched = True
                    break
            if touched:
                continue
            x = _cross(s, t)
            if x is not None and (round(x[0], 6), round(x[1], 6)) in junctions:
                uf.union(("seg", i), ("seg", j), "junction dot", x)

    # 2. Pins against segments.
    for key, pt in pins.items():
        for i, s in enumerate(segs):
            if _on(s, pt):
                uf.union(("pin",) + key, ("seg", i), "pin on wire", pt)

    # 3. Pins against pins — a pin dropped straight onto another pin.
    by_point: dict[tuple[float, float], list] = defaultdict(list)
    for key, pt in pins.items():
        by_point[(round(pt[0], 6), round(pt[1], 6))].append(key)
    for pt, keys in by_point.items():
        for other in keys[1:]:
            uf.union(("pin",) + keys[0], ("pin",) + other, "coincident pins", pt)

    # 4. Power symbols and labels — global by name, wherever they sit.
    globals_at: dict[str, list] = defaultdict(list)
    for p in sheet.powers:
        globals_at[p.net].append((p.x, p.y))
    for x, y, name in sheet.labels:
        globals_at[name].append((x, y))
    for name, points in globals_at.items():
        anchor = ("global", name)
        uf.add(anchor)
        for pt in points:
            for i, s in enumerate(segs):
                if _on(s, pt):
                    uf.union(anchor, ("seg", i), f"power/label {name}", pt)
            for key, ppt in pins.items():
                if abs(ppt[0] - pt[0]) < EPS and abs(ppt[1] - pt[1]) < EPS:
                    uf.union(anchor, ("pin",) + key, f"power/label {name}", pt)

    # 5. Compare the partitions.
    drawn: dict = defaultdict(set)
    for key in pins:
        drawn[uf.find(("pin",) + key)].add(key)

    expected: dict[tuple[str, str], str] = {}
    for net in cir.nets.values():
        for ref, pin in net.pins:
            expected[(ref, pin)] = net.name

    # Shorts: one drawn node carrying pins from two different source nets.
    for node, keys in drawn.items():
        names = {expected.get(k) for k in keys if expected.get(k)}
        if len(names) > 1:
            witness = ", ".join(
                f"{r}.{p}={expected.get((r, p))}" for r, p in sorted(keys))
            findings.append(Finding(
                "short", f"{' + '.join(sorted(names))} joined: {witness}"))

    # Opens: one source net drawn as more than one node.
    for net in cir.nets.values():
        present = [(r, p) for r, p in net.pins if (r, p) in pins]
        if len(present) < 2:
            continue
        nodes = defaultdict(list)
        for key in present:
            nodes[uf.find(("pin",) + key)].append(key)
        if ("global", net.name) in uf.parent:
            nodes.pop(uf.find(("global", net.name)), None)
            if not nodes:
                continue
        if len(nodes) > 1:
            groups = " | ".join(
                " ".join(f"{r}.{p}" for r, p in sorted(g))
                for g in nodes.values())
            findings.append(Finding(
                "open", f"net {net.name} drawn in {len(nodes)} pieces: {groups}"))

    # 6. Drawing defects that are not connectivity errors but signal a fallback.
    for s in segs:
        if s.axis == DIAGONAL:
            findings.append(Finding(
                "diagonal",
                f"net {s.net} drawn as a diagonal "
                f"{_fmt(s.a[0])},{_fmt(s.a[1])} -> {_fmt(s.b[0])},{_fmt(s.b[1])}"))

    return _dedupe(findings)


def _dedupe(findings: list[Finding]) -> list[Finding]:
    seen, out = set(), []
    order = {"short": 0, "open": 1, "overlap": 2, "diagonal": 3}
    for f in sorted(findings, key=lambda f: (order.get(f.kind, 9), f.detail)):
        if (f.kind, f.detail) not in seen:
            seen.add((f.kind, f.detail))
            out.append(f)
    return out


def _fmt(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")
