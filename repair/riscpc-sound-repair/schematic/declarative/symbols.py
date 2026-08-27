"""Resolve parts to KiCad library symbols.

This is the seam the whole approach turns on. A `.cir` says `part TL074:U1A`
and nothing about how to draw it; the symbol comes from KiCad's own installed
libraries, so the output uses `Device:R` and `Amplifier_Operational:TL074`
rather than invented shapes. That is what makes the result editable in KiCad
instead of merely openable.

Two things are read out of a library symbol:

  * its s-expression body, copied into the output's `lib_symbols` block —
    which is how a .kicad_sch carries its own symbol definitions;
  * every pin's position and angle, without which wires cannot be drawn to
    land on pins. Getting this wrong is exactly the failure that makes the
    tscircuit export unusable.

Multi-section devices need no annotation: a part's unit is worked out from
which pins it uses. `U1A` uses 1/2/3 and TL074 unit 1 has pins 1/2/3, so
they match. Pins 4 and 11 land on unit 5, the shared supply, and are emitted
as a separate symbol instance the way KiCad expects.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

# Where KiCad keeps its libraries. Overridable for a non-default install.
SEARCH = [
    os.environ.get("KICAD_SYMBOL_DIR", ""),
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols",
    "/usr/share/kicad/symbols",
    "/usr/local/share/kicad/symbols",
    str(Path.home() / ".local/share/kicad/symbols"),
]

# part type (from the .cir) -> KiCad lib_id. Checked before KIND_MAP.
TYPE_MAP = {
    "TL074": "Amplifier_Operational:TL074",
    "BC849C": "Transistor_BJT:BC849",
    "BC849": "Transistor_BJT:BC849",
    "BC847": "Transistor_BJT:BC847",
    "LM386": "Amplifier_Audio:LM386",
}

# Fallback by inferred kind, for the ordinary passives.
KIND_MAP = {
    "resistor": "Device:R",
    "capacitor": "Device:C",
    "capacitor_polar": "Device:C_Polarized",
    "inductor": "Device:L",
    "npn": "Device:Q_NPN",
    "diode": "Device:D",
    "terminal": "Connector:TestPoint",
}

# Power symbols, by net name. These are what put rails at the edges.
POWER_MAP = {
    "GND": "power:GND",
    "AGND": "power:GNDA",
    "0V": "power:GND",
    "5V": "power:+5V",
    "12V": "power:+12V",
    "-12V": "power:-12V",
    "3V3": "power:+3V3",
}


class SymbolError(Exception):
    pass


@dataclass
class Pin:
    number: str
    name: str
    x: float
    y: float
    angle: float          # 0 = pin body extends to the right of its endpoint
    length: float


@dataclass
class Unit:
    """One drawable section of a symbol: unit 1 of a TL074, say."""
    index: int
    pins: dict[str, Pin] = field(default_factory=dict)
    # Extent of the drawn body in symbol space, excluding pin leads. Wires
    # must route around this: checking pins alone let a feedback leg drop
    # straight through a transistor.
    box: tuple[float, float, float, float] | None = None


@dataclass
class Symbol:
    lib_id: str
    body: str                                 # verbatim, for lib_symbols
    units: dict[int, Unit] = field(default_factory=dict)
    power: bool = False
    # A symbol that `extends` another carries no artwork of its own: TL074 is
    # properties only and draws as LM2902. These point at whichever symbol
    # actually holds the graphics, and under what name its units are called.
    art_body: str = ""
    art_name: str = ""

    def unit_for(self, pins) -> int:
        """Which unit covers these pin numbers.

        This is what removes the need to declare that U1A is section A.
        """
        wanted = set(pins)
        for idx, unit in sorted(self.units.items()):
            if wanted <= set(unit.pins):
                return idx
        # No single unit holds them all — caller must split by unit.
        raise SymbolError(
            f"{self.lib_id}: pins {sorted(wanted)} span more than one unit"
        )

    def split_by_unit(self, pins) -> dict[int, list[str]]:
        """Group a part's pins by the unit each belongs to."""
        out: dict[int, list[str]] = {}
        for pin in pins:
            for idx, unit in sorted(self.units.items()):
                if pin in unit.pins:
                    out.setdefault(idx, []).append(pin)
                    break
            else:
                raise SymbolError(f"{self.lib_id}: no unit has pin {pin}")
        return out


def library_dir() -> Path:
    for cand in SEARCH:
        if cand and Path(cand).is_dir():
            return Path(cand)
    raise SymbolError(
        "KiCad symbol libraries not found. Set KICAD_SYMBOL_DIR to the "
        "directory holding Device.kicad_sym."
    )


def _extract(text: str, opener: str) -> str:
    """Pull one balanced s-expression starting at `opener`."""
    i = text.index(opener)
    depth, j, instr = 0, i, False
    while True:
        ch = text[j]
        if ch == '"' and text[j - 1] != "\\":
            instr = not instr
        if not instr:
            depth += (ch == "(") - (ch == ")")
        j += 1
        if depth == 0:
            return text[i:j]


_LIB_CACHE: dict[str, str] = {}


def _read_lib(lib: str) -> str:
    if lib not in _LIB_CACHE:
        path = library_dir() / f"{lib}.kicad_sym"
        if not path.exists():
            raise SymbolError(f"no such KiCad library: {path}")
        _LIB_CACHE[lib] = path.read_text()
    return _LIB_CACHE[lib]


_PIN_RE = re.compile(
    r'\(pin\s+\S+\s+\S+\s*\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)\s*'
    r'\(length\s+([-\d.]+)\).*?\(name\s+"([^"]*)".*?\(number\s+"([^"]*)"',
    re.S,
)


def load(lib_id: str, _seen: set[str] | None = None) -> Symbol:
    """Load a symbol, following `extends` to wherever the graphics live."""
    _seen = _seen or set()
    if lib_id in _seen:
        raise SymbolError(f"circular extends at {lib_id}")
    _seen.add(lib_id)

    lib, name = lib_id.split(":", 1)
    src = _read_lib(lib)
    try:
        body = _extract(src, f'(symbol "{name}"')
    except ValueError:
        raise SymbolError(f"{lib_id} not found in {lib}.kicad_sym") from None

    # TL074 carries only properties and defers its drawing to LM2902.
    if m := re.search(r'\(extends\s+"([^"]+)"\)', body):
        parent = load(f"{lib}:{m.group(1)}", _seen)
        sym = Symbol(lib_id=lib_id, body=body, units=parent.units)
        sym.power = parent.power
        sym.art_body = parent.art_body
        sym.art_name = parent.art_name
        return sym

    sym = Symbol(lib_id=lib_id, body=body)
    sym.power = bool(re.search(r"\(power\b", body))
    sym.art_body, sym.art_name = body, name

    for m in re.finditer(rf'\(symbol\s+"{re.escape(name)}_(\d+)_(\d+)"', body):
        idx = int(m.group(1))
        sub = _extract(body[m.start():], "(symbol")
        unit = sym.units.setdefault(idx, Unit(index=idx))
        for x, y, ang, length, pname, number in _PIN_RE.findall(sub):
            unit.pins[number] = Pin(
                number=number, name=pname,
                x=float(x), y=float(y),
                angle=float(ang), length=float(length),
            )

    _measure(sym, body, name)

    # Drop unit 0 (common graphics) when real units exist, and drop any unit
    # that turned out to hold no pins.
    sym.units = {i: u for i, u in sym.units.items() if u.pins}
    if not sym.units:
        raise SymbolError(f"{lib_id} defines no pins")
    return sym


# --- generated symbols ------------------------------------------------------
# A part KiCad has no symbol for (the TDA1545A here) gets a plain box with its
# pins in DIP order: down the left, then up the right. Generated rather than
# hand-drawn so an unknown chip never blocks a render, and emitted into
# lib_symbols like any other symbol so KiCad can edit it.

PIN_PITCH = 2.54
BOX_HALF_W = 7.62


def generate_box(part) -> Symbol:
    pins = sorted(part.pins, key=lambda p: int(p) if p.isdigit() else 1e9)
    half = (len(pins) + 1) // 2
    left, right = pins[:half], pins[half:][::-1]
    rows = max(len(left), len(right))
    top = (rows - 1) * PIN_PITCH / 2

    sym = Symbol(lib_id=f"Generated:{part.type}", body="")
    unit = Unit(index=1)
    graphics = []

    for i, num in enumerate(left):
        y = top - i * PIN_PITCH
        unit.pins[num] = Pin(num, num, -BOX_HALF_W - PIN_PITCH, y, 0.0, PIN_PITCH)
        graphics.append(_pin_sexp(num, -BOX_HALF_W - PIN_PITCH, y, 0))
    for i, num in enumerate(right):
        y = top - i * PIN_PITCH
        unit.pins[num] = Pin(num, num, BOX_HALF_W + PIN_PITCH, y, 180.0, PIN_PITCH)
        graphics.append(_pin_sexp(num, BOX_HALF_W + PIN_PITCH, y, 180))

    unit.box = (-BOX_HALF_W, -(top + PIN_PITCH), BOX_HALF_W, top + PIN_PITCH)
    sym.units[1] = unit
    sym.art_name = part.type
    h = top + PIN_PITCH
    sym.body = f'''(symbol "{part.type}"
    (pin_numbers (hide no))
    (pin_names (offset 1.016))
    (exclude_from_sim no) (in_bom yes) (on_board yes)
    (property "Reference" "U" (at 0 {h + 2.54:.2f} 0)
      (effects (font (size 1.27 1.27))))
    (property "Value" "{part.type}" (at 0 {-h - 2.54:.2f} 0)
      (effects (font (size 1.27 1.27))))
    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (symbol "{part.type}_1_1"
      (rectangle (start {-BOX_HALF_W:.2f} {h:.2f}) (end {BOX_HALF_W:.2f} {-h:.2f})
        (stroke (width 0.254) (type default))
        (fill (type background)))
{chr(10).join(graphics)}
    )
  )'''
    return sym


def _pin_sexp(number: str, x: float, y: float, angle: int) -> str:
    return (
        f'      (pin passive line (at {x:.2f} {y:.2f} {angle}) (length {PIN_PITCH})\n'
        f'        (name "{number}" (effects (font (size 1.27 1.27))))\n'
        f'        (number "{number}" (effects (font (size 1.27 1.27)))))'
    )


def for_part(part) -> Symbol:
    """The symbol for a part: from KiCad's libraries, or generated."""
    try:
        return load(lib_id_for(part))
    except SymbolError:
        if part.kind in ("chip", "box"):
            return generate_box(part)
        raise


_COORD_RE = re.compile(r"\((?:xy|start|end|center|mid) ([-\d.]+) ([-\d.]+)\)")
_RADIUS_RE = re.compile(r"\(radius ([-\d.]+)\)")


def _measure(sym: Symbol, body: str, name: str) -> None:
    """Bounding box of each unit's artwork, in symbol space.

    Unit 0 holds graphics common to every unit, so its extent is merged into
    all of them.
    """
    boxes: dict[int, list[float]] = {}
    for m in re.finditer(rf'\(symbol\s+"{re.escape(name)}_(\d+)_(\d+)"', body):
        idx = int(m.group(1))
        sub = _extract(body[m.start():], "(symbol")
        xs = [float(a) for a, _ in _COORD_RE.findall(sub)]
        ys = [float(b) for _, b in _COORD_RE.findall(sub)]
        for r in (float(v) for v in _RADIUS_RE.findall(sub)):
            cm = re.search(r"\(center ([-\d.]+) ([-\d.]+)\)", sub)
            if cm:
                cx, cy = float(cm.group(1)), float(cm.group(2))
                xs += [cx - r, cx + r]
                ys += [cy - r, cy + r]
        if not xs:
            continue
        b = boxes.setdefault(idx, [min(xs), min(ys), max(xs), max(ys)])
        b[0], b[1] = min(b[0], min(xs)), min(b[1], min(ys))
        b[2], b[3] = max(b[2], max(xs)), max(b[3], max(ys))

    common = boxes.get(0)
    for idx, unit in sym.units.items():
        b = boxes.get(idx) or (list(common) if common else None)
        if b and common and idx != 0:
            b = [min(b[0], common[0]), min(b[1], common[1]),
                 max(b[2], common[2]), max(b[3], common[3])]
        unit.box = tuple(b) if b else None


def lib_id_for(part) -> str:
    """Map a parsed part to a KiCad lib_id."""
    if part.type in TYPE_MAP:
        return TYPE_MAP[part.type]
    if part.kind in KIND_MAP:
        return KIND_MAP[part.kind]
    raise SymbolError(
        f"no symbol for {part.ref} (type {part.type!r}, kind {part.kind!r}) — "
        f"add it to TYPE_MAP in symbols.py"
    )


def power_lib_id(net_name: str) -> str | None:
    key = net_name.upper().replace("+", "").rstrip("_RAW")
    return POWER_MAP.get(net_name) or POWER_MAP.get(key)
