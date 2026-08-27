"""Parser for the .cir netlist language.

Three constructs, all line-oriented:

    net GND                          declare a named net
    part 47k:Rin_R                   declare a part, <type>:<ref>
    Rin_R@2 -> U1D@13 -> GND         connect; chains allowed

Pins are referred to by their real number on the device — no aliases, so
the file can be checked straight against a datasheet.

A trailing ? on a part type ("Cf?") marks it as never confirmed on the
board. Blank lines and # comments are ignored; indentation is not
significant.

There is nothing about layout or drawing in here, and nothing about what
any part *means*. Kinds are inferred from the reference designator, the
way an engineer reads them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


class ParseError(Exception):
    """Raised with a file:line prefix so errors are clickable."""


# Reference-designator conventions. Longest prefix wins, so "SK" beats "S".
KIND_BY_PREFIX = [
    ("SK", "terminal"),
    ("PL", "terminal"),
    ("IC", "chip"),
    ("R", "resistor"),
    ("C", "capacitor"),
    ("L", "inductor"),
    ("Q", "npn"),
    ("D", "diode"),
    ("J", "terminal"),
    ("U", "chip"),
]

@dataclass
class Part:
    ref: str
    type: str
    kind: str
    traced: bool = True
    pins: list[str] = field(default_factory=list)   # in first-use order

    @property
    def value(self) -> str:
        """The type doubles as the value: `47k`, `TDA1545A`, `BC849C`."""
        return self.type


@dataclass
class Net:
    name: str
    pins: list[tuple[str, str]] = field(default_factory=list)  # (ref, pin)
    named: bool = False       # declared with `net`, rather than inferred


class Circuit:
    def __init__(self) -> None:
        self.parts: dict[str, Part] = {}
        self.nets: dict[str, Net] = {}
        self.title: str = ""
        self.subtitle: str = ""
        self._parent: dict[str, str] = {}   # union-find over pin/net nodes

    # --- union-find ---------------------------------------------------
    def _find(self, x: str) -> str:
        self._parent.setdefault(x, x)
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def _union(self, a: str, b: str) -> None:
        ra, rb = self._find(a), self._find(b)
        if ra == rb:
            return
        # Prefer a declared net name as the representative, so the net keeps
        # the name the author gave it rather than an arbitrary pin.
        if rb.startswith("net:"):
            ra, rb = rb, ra
        self._parent[rb] = ra

    # --- queries ------------------------------------------------------
    def nets_of(self, ref: str) -> list[Net]:
        return [n for n in self.nets.values() if any(p[0] == ref for p in n.pins)]

    def net_at(self, ref: str, pin: str) -> Net | None:
        for n in self.nets.values():
            if (ref, pin) in n.pins:
                return n
        return None

    def parts_on(self, net: Net) -> list[str]:
        seen, out = set(), []
        for ref, _ in net.pins:
            if ref not in seen:
                seen.add(ref)
                out.append(ref)
        return out


def infer_kind(ref: str) -> str:
    """Kind from the reference designator, the way an engineer reads one.

    The prefix is the *maximal leading run of capitals*, so R in `Riv_R` is a
    resistor while `DAC` is not a diode and `VIDC` is not an inductor.
    """
    run = re.match(r"^[A-Z]+", ref)
    if not run:
        return "box"
    prefix = run.group(0)
    for known, kind in KIND_BY_PREFIX:
        if prefix == known:
            return kind
    return "chip"


def _is_polar(type_: str) -> bool:
    """Electrolytics: a capacitance in µF rather than pF/nF."""
    return bool(re.search(r"\d\s*(u|µ)", type_, re.I))


_PART_RE = re.compile(r"^part\s+(?P<type>\S+?):(?P<ref>\S+)\s*$")
_NET_RE = re.compile(r"^net\s+(?P<name>\S+)\s*$")


def parse(text: str, filename: str = "<cir>") -> Circuit:
    cir = Circuit()

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue

        def fail(msg: str):
            return ParseError(f"{filename}:{lineno}: {msg}\n  {raw.strip()}")

        if m := _NET_RE.match(line):
            name = m.group("name")
            cir.nets.setdefault(name, Net(name=name, named=True))
            cir._find(f"net:{name}")
            continue

        if m := _PART_RE.match(line):
            ref, type_ = m.group("ref"), m.group("type")
            if ref in cir.parts:
                raise fail(f"part {ref} declared twice")
            traced = not type_.endswith("?")
            type_ = type_.rstrip("?")
            cir.parts[ref] = Part(
                ref=ref, type=type_, kind=infer_kind(ref), traced=traced
            )
            continue

        if "->" in line:
            nodes = [t.strip() for t in line.split("->")]
            if any(not t for t in nodes):
                raise fail("empty term in connection")
            keys = []
            for tok in nodes:
                if "@" in tok:
                    ref, pin = tok.split("@", 1)
                    if ref not in cir.parts:
                        raise fail(f"unknown part {ref}")
                    part = cir.parts[ref]
                    if pin not in part.pins:
                        part.pins.append(pin)
                    keys.append(f"pin:{ref}@{pin}")
                else:
                    if tok not in cir.nets:
                        raise fail(
                            f"unknown net {tok!r} — declare it with `net {tok}`"
                        )
                    keys.append(f"net:{tok}")
            for a, b in zip(keys, keys[1:]):
                cir._union(a, b)
            continue

        raise fail("not a net or part declaration, or a connection")

    _materialise(cir)
    _refine_kinds(cir)
    return cir


def _materialise(cir: Circuit) -> None:
    """Collapse the union-find into named nets."""
    groups: dict[str, list[str]] = {}
    for key in list(cir._parent):
        groups.setdefault(cir._find(key), []).append(key)

    anon = 0
    for root, members in groups.items():
        declared = sorted(m[4:] for m in members if m.startswith("net:"))
        if declared:
            name = declared[0]
        else:
            # Name an inferred net after the pin that drives it, so the
            # netlist reads as DAC.IOR rather than whichever pin sorts first.
            pins = sorted(m[4:] for m in members if m.startswith("pin:"))
            if pins:
                name = max(pins, key=_net_name_rank(cir)).replace("@", ".")
            else:
                name = f"N${anon}"
                anon += 1

        net = cir.nets.setdefault(name, Net(name=name))
        for m in members:
            if m.startswith("pin:"):
                ref, pin = m[4:].split("@", 1)
                if (ref, pin) not in net.pins:
                    net.pins.append((ref, pin))

    # Drop declared-but-unused nets so they do not clutter the drawing.
    for name in [n for n, v in cir.nets.items() if not v.pins]:
        del cir.nets[name]


def _net_name_rank(cir: Circuit):
    """Prefer the busiest part on the net, then alphabetical order."""
    def rank(key: str):
        ref, _ = key.split("@", 1)
        part = cir.parts.get(ref)
        return (len(part.pins) if part else 0, key)
    return rank


def _refine_kinds(cir: Circuit) -> None:
    """Second pass, now that pin usage is known."""
    for part in cir.parts.values():
        if part.kind == "capacitor" and _is_polar(part.type):
            part.kind = "capacitor_polar"


def load(path: str) -> Circuit:
    with open(path) as fh:
        return parse(fh.read(), filename=path)
