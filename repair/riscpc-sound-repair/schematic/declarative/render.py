#!/usr/bin/env python3
"""Render a .cir to SVG, or dump what the layout worked out.

    render.py circuit.cir -o circuit.svg
    render.py circuit.cir --layout        # what the graph rules decided
    render.py circuit.cir --netlist       # net by net, for checking by hand

The SVG is a preview of the KiCad output, not a separate drawing: symbol
artwork comes from KiCad's own libraries, so what appears here is what will
appear there.
"""

from __future__ import annotations

import argparse
import sys

import layout
import netlist
import place
import render_svg


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", help="path to a .cir file")
    ap.add_argument("-o", "--output", help="SVG output path")
    ap.add_argument("--layout", action="store_true", help="print the layout")
    ap.add_argument("--netlist", action="store_true", help="print the netlist")
    ap.add_argument("--check", action="store_true",
                    help="report wires that cross a symbol body")
    args = ap.parse_args(argv)

    try:
        cir = netlist.load(args.source)
    except netlist.ParseError as exc:
        print(exc, file=sys.stderr)
        return 1

    if args.netlist:
        _print_netlist(cir)
        return 0

    lay = layout.build(cir)

    if args.layout:
        _print_layout(cir, lay)
        return 0

    sheet = place.build(cir, lay)

    if args.check:
        return _check(cir, sheet)

    svg = render_svg.render(sheet, cir)
    out = args.output or args.source.rsplit(".", 1)[0] + ".svg"
    with open(out, "w") as fh:
        fh.write(svg)
    print(
        f"{out}: {len(sheet.placed)} symbols, {len(sheet.wires)} wires, "
        f"{len(sheet.powers)} power pins"
    )
    return 0


def _check(cir, sheet) -> int:
    """Report any wire running through a symbol body.

    Worth having as a command rather than a habit: a wire crossing a body is
    invisible in a thumbnail and obvious in KiCad, and the routing bugs that
    produced them were also producing real shorts.
    """
    import geometry
    import symbols

    boxes = []
    for placed in sheet.placed:
        box = geometry.body_box(placed, symbols.for_part(cir.parts[placed.ref]))
        if box:
            boxes.append((placed.ref, box))

    def crosses(p1, p2, box) -> bool:
        x0, y0, x1, y1 = box
        (ax, ay), (bx, by) = p1, p2
        if abs(ax - bx) < 1e-6:
            lo, hi = sorted((ay, by))
            return x0 < ax < x1 and lo < y1 - 0.01 and hi > y0 + 0.01
        if abs(ay - by) < 1e-6:
            lo, hi = sorted((ax, bx))
            return y0 < ay < y1 and lo < x1 - 0.01 and hi > x0 + 0.01
        return False

    bad = set()
    for wire in sheet.wires:
        for p1, p2 in zip(wire.pts, wire.pts[1:]):
            for ref, box in boxes:
                if crosses(p1, p2, box):
                    bad.add((wire.net, ref))

    if not bad:
        print(f"ok: {len(sheet.wires)} wires, none crossing a symbol body")
        return 0
    print(f"{len(bad)} net/body crossings:")
    for net, ref in sorted(bad):
        print(f"   net {net} crosses {ref}")
    return 1


def _print_netlist(cir) -> None:
    untraced = [p.ref for p in cir.parts.values() if not p.traced]
    print(f"{len(cir.parts)} parts, {len(cir.nets)} nets")
    if untraced:
        print(f"NOT CONFIRMED ON THE BOARD: {', '.join(sorted(untraced))}")
    print()
    for net in sorted(cir.nets.values(), key=lambda n: (-len(n.pins), n.name)):
        pins = ", ".join(f"{r}.{p}" for r, p in net.pins)
        print(f"{net.name:16} {pins}")


def _print_layout(cir, lay) -> None:
    print("globals:", " ".join(sorted(lay.globals)))
    if lay.stubs:
        print("stubs  :", lay.stubs)
    for i, group in enumerate(lay.groups):
        kind = "supply" if group.supply else f"head={group.head}"
        print(f"\n--- group {i}  {kind}")
        for lane in group.lanes:
            print("   spine:", " -> ".join(lane.spine))
            for att in lane.attachments:
                span = (att.spans[0] if att.spans[0] == att.spans[1]
                        else f"{att.spans[0]}..{att.spans[1]}")
                where = "above" if att.above else "below"
                print(f"      {att.kind:6} {att.ref:9} {span:18} "
                      f"{where} tier={att.tier} {att.net or ''}")


if __name__ == "__main__":
    sys.exit(main())
