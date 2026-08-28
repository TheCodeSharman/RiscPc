"""Work out where everything goes, from connectivity alone.

Nothing here knows what a circuit *means*. There is no notion of an I/V
converter, a bias network or a feedback path. Four graph rules do the work,
and the electrical reading falls out of them:

  1. GLOBALS.  A net that is a supply by name, or that touches a lot of
     parts, is drawn as a local stub wherever it is referenced rather than
     routed across the sheet. This is what puts rails at the edges.

  2. STUBS.  A part whose only neighbour is one other part is drawn hanging
     off that part instead of taking a column of its own. This is what keeps
     connectors and sources out of the signal chain.

  3. SPINE.  Within a lane, the *heaviest* path from source to sink is the
     spine, laid left to right; everything else hangs off it. Heaviest, not
     shortest — a feedback resistor is always a shorter way past an
     amplifier than going through it, so shortest-path leaves the active
     devices off the backbone and draws the circuit inside out.

  4. BRIDGES.  An off-spine part touching the spine twice is drawn *over the
     top*, spanning the parts it connects. A part that spans backwards is
     feedback — but nothing here needs to know that, it just draws it where
     feedback belongs.

Lanes come from the source's branches, so the two channels separate without
anyone saying they are channels.
"""

from __future__ import annotations

import itertools

import re
from collections import deque
from dataclasses import dataclass, field

from netlist import Circuit, Net

# Supply-net names. Matched, not declared, so `net -12V` needs no annotation.
GLOBAL_NAME = re.compile(
    r"^(GND|AGND|DGND|0V|VCC|VDD|VSS|VEE|VREF|IREF|[A-Z]*REF)$"
    r"|^[+-]?[\d.]+V(_RAW)?$",
    re.I,
)
# Backstop for an undeclared net that is obviously a bus. Above any plausible
# signal node: a summing node with a feedback pair is already four pins.
GLOBAL_FANOUT = 6


@dataclass
class Attachment:
    """An off-spine part hanging off the spine."""
    ref: str
    kind: str                 # "bridge" | "stub"
    spans: tuple[str, str]    # spine refs it connects (equal for a self-bridge)
    net: str | None = None    # for a stub, the global net it terminates on
    above: bool = True
    tier: int = 0             # stacking order when several share a span


@dataclass
class Lane:
    spine: list[str] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)


@dataclass
class Group:
    """A connected component: a source with lanes hanging off it."""
    head: str | None = None
    lanes: list[Lane] = field(default_factory=list)
    supply: bool = False      # parts wired only to globals, e.g. a rail filter


@dataclass
class Layout:
    groups: list[Group] = field(default_factory=list)
    globals: set[str] = field(default_factory=set)
    stubs: dict[str, list[str]] = field(default_factory=dict)  # host -> stubs
    rank: dict[str, int] = field(default_factory=dict)


def is_global(net: Net) -> bool:
    parts = {r for r, _ in net.pins}
    return bool(GLOBAL_NAME.match(net.name)) or len(parts) >= GLOBAL_FANOUT


def build(cir: Circuit, hints: dict | None = None) -> Layout:
    hints = hints or {}
    lay = Layout()

    # --- rule 1: globals ---------------------------------------------
    forced = set(hints.get("globals", []))
    local = set(hints.get("locals", []))
    for net in cir.nets.values():
        if net.name in local:
            continue
        if is_global(net) or net.name in forced:
            lay.globals.add(net.name)

    # Adjacency over local nets only.
    adj: dict[str, set[str]] = {ref: set() for ref in cir.parts}
    net_between: dict[tuple[str, str], str] = {}
    for net in cir.nets.values():
        if net.name in lay.globals:
            continue
        refs = cir.parts_on(net)
        for a in refs:
            for b in refs:
                if a != b:
                    adj[a].add(b)
                    net_between[(a, b)] = net.name

    # --- rule 2: stubs ------------------------------------------------
    stub_of: dict[str, str] = {}
    for ref, nbrs in adj.items():
        if len(nbrs) == 1:
            host = next(iter(nbrs))
            # Only if the host is busier, else two 1-pin parts orphan each other.
            if len(adj[host]) > 1:
                stub_of[ref] = host
    for ref, host in stub_of.items():
        lay.stubs.setdefault(host, []).append(ref)

    core = {r for r in cir.parts if r not in stub_of}

    # A part with no local nets is not part of any signal chain — it sits
    # between rails. Collect those separately so the rail filtering does not
    # come out as a scatter of one-part components.
    only_global = {
        r for r in core
        if cir.nets_of(r) and all(n.name in lay.globals for n in cir.nets_of(r))
    }
    core -= only_global
    core_adj = {r: {n for n in adj[r] if n in core} for r in core}

    # --- components ---------------------------------------------------
    seen: set[str] = set()
    for start in sorted(core, key=lambda r: (-len(cir.parts[r].pins), r)):
        if start in seen:
            continue
        comp = _component(start, core_adj)
        seen |= comp
        lay.groups.append(_lay_group(cir, comp, core_adj, net_between, lay, hints))

    if only_global:
        lay.groups.append(_lay_supply(cir, only_global, lay))

    return lay


def _lay_supply(cir, refs, lay) -> Group:
    """One lane per part, each running between the globals it connects."""
    group = Group(supply=True)
    for ref in sorted(refs, key=lambda r: (len(cir.nets_of(r)), r), reverse=True):
        group.lanes.append(Lane(spine=[ref]))
    return group


def _component(start: str, adj: dict[str, set[str]]) -> set[str]:
    out, q = {start}, deque([start])
    while q:
        for n in adj[q.popleft()]:
            if n not in out:
                out.add(n)
                q.append(n)
    return out


def _lay_group(cir, comp, adj, net_between, lay, hints) -> Group:
    """Rank from the busiest part, split into lanes, then find each spine."""
    seed = hints.get("source")
    if seed not in comp:
        seed = max(comp, key=lambda r: (len(cir.parts[r].pins), r))

    rank, prev = _bfs(seed, adj, comp)
    lay.rank.update(rank)

    branches = sorted(adj[seed], key=lambda r: r)
    group = Group(head=seed if len(comp) > 1 else None)

    if not branches:
        group.lanes.append(Lane(spine=[seed]))
        return group

    # Cutting the source splits the graph into its lanes. This is what
    # separates the two channels, without anyone saying they are channels.
    cut = {r: adj[r] - {seed} for r in comp if r != seed}
    lanes, seen = [], set()
    for ref in sorted(cut, key=lambda r: (rank.get(r, 0), r)):
        if ref in seen:
            continue
        members = _component(ref, cut)
        seen |= members
        lanes.append(members)

    for members in lanes:
        group.lanes.append(_lay_lane(cir, members, adj, net_between, lay, rank, seed))
    return group


def _bfs(start, adj, allowed):
    rank, prev, q = {start: 0}, {}, deque([start])
    while q:
        cur = q.popleft()
        for n in sorted(adj[cur]):
            if n in allowed and n not in rank:
                rank[n] = rank[cur] + 1
                prev[n] = cur
                q.append(n)
    return rank, prev


def _lay_lane(cir, members, adj, net_between, lay, rank, seed) -> Lane:
    """Rule 3 and 4: longest path is the spine, the rest attaches to it."""
    sub = {r: adj[r] & members for r in members}

    entries = [r for r in members if seed in adj[r]] or [
        min(members, key=lambda r: (rank.get(r, 0), r))
    ]
    # The sink is whatever hosts an off-board terminal, else the deepest part.
    sinks = [
        r for r in members
        if any(cir.parts[s].kind == "terminal" for s in lay.stubs.get(r, []))
    ] or [max(members, key=lambda r: (rank.get(r, 0), r))]
    spine = _heaviest_path(cir, members, sub, entries, sinks)

    lane = Lane(spine=spine)
    on_spine = set(spine)

    for ref in sorted(members - on_spine, key=lambda r: (rank.get(r, 0), r)):
        globals_on = [
            n.name for n in cir.nets_of(ref) if n.name in lay.globals
        ]
        # Anchor each of the part's own nets to the spine. What decides
        # bridge-or-stub is how many *nets* reach the spine, not how many
        # parts: Rpull touches both Q and Rs1, but through one net — it is a
        # leg to the rail, not something spanning the pair.
        anchors = []
        for net in cir.nets_of(ref):
            if net.name in lay.globals:
                continue
            on = sorted(set(cir.parts_on(net)) & on_spine, key=spine.index)
            if on:
                anchors.append(on)

        if len(anchors) >= 2:
            # Of all the ways to pick one anchor per net, take the tightest.
            # Rfb touches Rin, U1C, Q and Rs1; spanning Rin..Rs1 stretches it
            # across the whole stage when U1C..Q says the same thing. Equal
            # indices mean feedback round a single part, which is how Riv and
            # Cf come to sit directly over their op-amp.
            lo, hi = min(
                (tuple(sorted((spine.index(a), spine.index(b))))
                 for a, b in itertools.product(anchors[0], anchors[1])),
                key=lambda pr: pr[1] - pr[0],
            )
            lane.attachments.append(
                Attachment(ref, "bridge", (spine[lo], spine[hi]), above=True)
            )
        else:
            # One anchor, or none at all. None happens when a part reaches the
            # spine only through another off-spine part — it used to be
            # dropped from the drawing without a word, so fall back to the
            # nearest spine part by graph distance.
            host = anchors[0][0] if anchors else _nearest_on_spine(
                ref, adj, on_spine, spine)
            if host is None:
                continue
            net = globals_on[0] if globals_on else None
            lane.attachments.append(
                Attachment(ref, "stub", (host, host), net=net,
                           above=_rail_is_up(net))
            )

    _stack(lane)
    return lane


# Above this, the exhaustive search is abandoned for a cheap greedy walk.
# No lane in a hand-traced circuit comes close; this is a runaway guard.
SEARCH_LIMIT = 22


def _nearest_on_spine(ref, adj, on_spine, spine):
    """The spine part fewest hops away, for a part that touches none directly."""
    seen, frontier = {ref}, [ref]
    while frontier:
        nxt = []
        for r in frontier:
            for n in sorted(adj[r]):
                if n in seen:
                    continue
                if n in on_spine:
                    return n
                seen.add(n)
                nxt.append(n)
        frontier = nxt
    return spine[0] if spine else None


def _heaviest_path(cir, members, sub, entries, sinks) -> list[str]:
    """The best source-to-sink path through the lane.

    A part scores `pins - 2`, so an ordinary two-terminal passive is worth
    nothing and ties are settled by taking fewer hops. That is what makes
    the backbone run *through* the amplifiers while a feedback resistor
    round one of them stays a detour: both routes score the same, and the
    direct one is shorter.

    Scoring by pin count alone does not work — it just finds the longest
    snake through every part in the lane.
    """
    weight = lambda r: len(cir.parts[r].pins) - 2

    if len(members) > SEARCH_LIMIT:
        return _greedy_path(cir, members, sub, entries, weight)

    targets = set(sinks)
    best: tuple[int, int, list[str]] = (-(10**6), 0, [])

    def walk(ref, seen, score, path):
        nonlocal best
        score += weight(ref)
        path = path + [ref]
        if ref in targets:
            cand = (score, -len(path), path)
            if cand[:2] > best[:2]:
                best = cand
        for nxt in sorted(sub[ref]):
            if nxt not in seen:
                walk(nxt, seen | {nxt}, score, path)

    for entry in sorted(entries):
        walk(entry, {entry}, 0, [])
    return best[2] or sorted(members)[:1]


def _greedy_path(cir, members, sub, entries, weight) -> list[str]:
    """Fallback for a lane too big to search: always step to the heaviest."""
    entry = max(entries, key=weight)
    path, seen = [entry], {entry}
    while True:
        nxt = [n for n in sub[path[-1]] if n not in seen]
        if not nxt:
            return path
        step = max(nxt, key=lambda r: (weight(r), r))
        path.append(step)
        seen.add(step)


def _rail_is_up(net: str | None) -> bool:
    """Positive rails go up, grounds and negative rails go down."""
    if not net:
        return False
    if net.upper().startswith(("GND", "AGND", "DGND", "0V", "VSS", "VEE")):
        return False
    return not net.lstrip().startswith("-")


def _stack(lane: Lane) -> None:
    """Give overlapping attachments distinct tiers so they do not collide."""
    for group in (True, False):
        rows: list[list[tuple[int, int]]] = []
        for att in [a for a in lane.attachments if a.above == group]:
            try:
                lo = lane.spine.index(att.spans[0])
                hi = lane.spine.index(att.spans[1])
            except ValueError:
                continue
            for tier, occupied in enumerate(rows):
                if all(hi < s or lo > e for s, e in occupied):
                    occupied.append((lo, hi))
                    att.tier = tier
                    break
            else:
                rows.append([(lo, hi)])
                att.tier = len(rows) - 1
