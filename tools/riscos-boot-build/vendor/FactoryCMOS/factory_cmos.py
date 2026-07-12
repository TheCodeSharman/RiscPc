#!/usr/bin/env python3
"""Reconstruct a RISC OS *factory* CMOS image from Kernel source.

The multi-ROM `!Boot` (build.py patch_bootrun_per_os_bootcfg) keeps a per-OS
CMOS snapshot so the position-keyed module-unplug mask can't misfire across ROM
versions.  A brand-new OS with no snapshot must be seeded from a *factory* image
-- NOT from the outgoing OS's (mis-keyed) live CMOS.  This module builds that
factory image straight from the Kernel's own `DefaultCMOSTable`, so it is the
authoritative reset state for each RISC OS version, checksum and all.

Sources (per RISC OS version, a Kernel source tree):
  s/NewReset      -- `DefaultCMOSTable`: the non-zero reset defaults, as
                     `= <symbol>, <value>` byte pairs terminated by `= &FF`.
  hdr/CMOS        -- the CMOS location map (symbol -> byte offset), an ObjAsm
                     storage map built from `*` (EQU) and `#` (reserve) with
                     `^` setting the counter.

Output: a 240-byte image of CMOS *logical* locations 0..239 (type &FF2), the
exact format !SaveCMOS / CMOSSwap read and write.  Location 239 is the checksum
(`(CMOSxseed + sum of locs 0..238) & &FF`, per s/PMF/i2cutils ValChecksum).

Machine config flags (RiscPC / IOMD defaults):
  Select16BitSound = True   -> TutuCMOS is set dynamically by hardware probe,
                               so it is NOT in the static table (left 0 here).
  NewClockChip     = False  -> A1-only; its NewADFSCMOS+1 entry is excluded.
"""
import re
import sys
from pathlib import Path

CMOS_LEN = 240          # logical locations 0..239
CHECKSUM_LOC = 0xEF     # CheckSumCMOS
CMOS_XSEED = 0x01       # CMOSxseed: checksum initial value


# --- ObjAsm expression evaluation -----------------------------------------

def _eval(expr, syms):
    """Evaluate an ObjAsm integer/boolean expression against a symbol dict."""
    e = expr.strip()
    # boolean literals
    e = e.replace('{TRUE}', 'True').replace('{FALSE}', 'False')
    # infix binary/unary ObjAsm operators -> Python (word-boundary safe: they
    # are colon-delimited, so a plain replace is unambiguous)
    for a, b in (
        (':SHL:', '<<'), (':SHR:', '>>'),
        (':OR:', '|'), (':AND:', '&'), (':EOR:', '^'),
        (':MOD:', '%'), (':LAND:', ' and '), (':LOR:', ' or '),
        (':LNOT:', ' not '), (':NOT:', ' ~'),
    ):
        e = e.replace(a, b)
    # ObjAsm base-n literal `<base>_<digits>` (e.g. 2_0100 binary) -> decimal
    e = re.sub(r'\b(\d+)_([0-9A-Za-z]+)',
               lambda m: str(int(m.group(2), int(m.group(1)))), e)
    # hex: &HH -> decimal (no letters, so the symbol pass below can't grab it)
    e = re.sub(r'&([0-9A-Fa-f]+)', lambda m: str(int(m.group(1), 16)), e)
    # bare symbols -> syms[...]; leave Python keywords/numbers alone
    def sub_sym(m):
        name = m.group(0)
        if name in ('True', 'False', 'and', 'or', 'not'):
            return name
        return f'syms[{name!r}]'
    e = re.sub(r'[A-Za-z_][A-Za-z0-9_]*', sub_sym, e)
    try:
        return eval(e, {'__builtins__': {}}, {'syms': syms})  # noqa: S307 (trusted source)
    except KeyError as ex:
        raise KeyError(f"undefined symbol {ex} in expression {expr!r}") from ex


# --- hdr/CMOS: symbol -> offset map ---------------------------------------

def parse_cmos_map(hdr_cmos):
    """Parse hdr/CMOS into {symbol: value}. Locations come from the `#`/`^`
    storage counter and explicit `* &HH` EQUs; bit constants resolve too."""
    syms = {}
    counter = 0
    for raw in Path(hdr_cmos).read_text(errors='replace').splitlines():
        line = raw.split(';', 1)[0].rstrip()
        if not line.strip():
            continue
        # `^ <expr>` : set the storage counter (may be indented, no label)
        m = re.match(r'\s*\^\s+(.+)$', line)
        if m:
            counter = _eval(m.group(1), syms)
            continue
        # `<label> # <size>` : reserve, label = current counter
        m = re.match(r'(\w+)\s+#\s+(.+)$', line)
        if m:
            name, size = m.group(1), _eval(m.group(2), syms)
            syms[name] = counter
            counter += size
            continue
        # `<label> * <expr>` : EQU
        m = re.match(r'(\w+)\s+\*\s+(.+)$', line)
        if m:
            syms[m.group(1)] = _eval(m.group(2), syms)
            continue
        # directives we can ignore (SUBT, OPT, END, ASSERT, GBLx, SET*, etc.)
    return syms


# --- s/NewReset: DefaultCMOSTable -> {loc: value} -------------------------

def parse_default_table(newreset, syms, config):
    """Return {loc: byte} from DefaultCMOSTable, honouring `[ cond ... ]`
    conditional blocks against `config` (e.g. Select16BitSound, NewClockChip)."""
    text = Path(newreset).read_text(errors='replace').splitlines()
    # isolate the table body: from `DefaultCMOSTable` label to the `= &FF` end
    start = next(i for i, l in enumerate(text)
                 if re.match(r'DefaultCMOSTable\b', l))
    body = []
    for l in text[start + 1:]:
        body.append(l)
        if re.match(r'\s*=\s*&FF\s*(;.*)?$', l):
            break

    cfgsyms = dict(syms)
    cfgsyms.update(config)  # config flags visible to `[ cond ]` evaluation

    out = {}
    cond_stack = [True]  # active if all entries True
    for raw in body:
        line = raw.split(';', 1)[0].rstrip()
        s = line.strip()
        if not s:
            continue
        if s.startswith('['):
            cond = s[1:].strip()
            active = cond_stack[-1] and bool(_eval(cond, cfgsyms)) if cond else cond_stack[-1]
            cond_stack.append(active)
            continue
        if s.startswith('|'):  # else
            rest = s[1:].strip()
            parent = cond_stack[-2]
            cond_stack[-1] = parent and not cond_stack[-1]
            if rest:
                s = rest  # `| = sym,val` inline else (not used here, but safe)
            else:
                continue
        if s.startswith(']'):
            cond_stack.pop()
            continue
        if not cond_stack[-1]:
            continue
        # a data line: `= <loc-expr>, <value-expr>`  or the `= &FF` terminator
        m = re.match(r'=\s*(.+)$', s)
        if not m:
            continue
        operand = m.group(1)
        if re.match(r'&FF\s*$', operand):
            break
        loc_expr, val_expr = operand.split(',', 1)
        loc = _eval(loc_expr, syms)
        val = _eval(val_expr, syms) & 0xFF
        out[loc] = val
    return out


# --- assemble the 240-byte image ------------------------------------------

def build_image(kernel_src, config=None):
    """Build the 240-byte factory CMOS image for a Kernel source tree.

    kernel_src: path to a Kernel checkout (has s/NewReset).
    Uses HdrSrc's hdr/CMOS for the location map (submodule alongside).
    """
    kernel_src = Path(kernel_src)
    config = {'Select16BitSound': True, 'NewClockChip': False,
              **(config or {})}
    hdr_cmos = _find_hdr_cmos(kernel_src)
    syms = parse_cmos_map(hdr_cmos)
    # ConfiguredLang lives in s/GetAll (default 10); expose it for the table.
    syms.setdefault('ConfiguredLang', _configured_lang(kernel_src))
    table = parse_default_table(kernel_src / 's' / 'NewReset', syms, config)

    img = bytearray(CMOS_LEN)
    for loc, val in table.items():
        if 0 <= loc < CMOS_LEN:
            img[loc] = val
    img[CHECKSUM_LOC] = checksum(img)
    return bytes(img)


def checksum(img):
    """(CMOSxseed + sum of locs 0..238) & 0xFF -- per ValChecksum."""
    return (CMOS_XSEED + sum(img[0:CHECKSUM_LOC])) & 0xFF


def _configured_lang(kernel_src):
    getall = Path(kernel_src) / 's' / 'GetAll'
    if getall.exists():
        m = re.search(r'ConfiguredLang\s+SETA\s+(\d+)', getall.read_text(errors='replace'))
        if m:
            return int(m.group(1))
    return 10  # RISC OS default (UK)


def _find_hdr_cmos(kernel_src):
    """Locate hdr/CMOS: HdrSrc submodule sits beside the Kernel checkout."""
    for cand in (
        kernel_src.parent / 'HdrSrc' / 'hdr' / 'CMOS',
        kernel_src / 'hdr' / 'CMOS',
    ):
        if cand.exists():
            return cand
    raise FileNotFoundError(
        f"hdr/CMOS not found near {kernel_src} (expected ../HdrSrc/hdr/CMOS)")


# --- physical<->logical mangle (for validating against a raw cmos.ram) -----

def logical_to_phys(loc):
    """CMOS logical location -> 8583 physical byte (= cmos.ram file offset)."""
    return ((loc + 0x30) % 0xF0) + 0x10


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('kernel_src', help="path to a Kernel source tree (has s/NewReset)")
    ap.add_argument('-o', '--out', help="write the image here")
    ap.add_argument('--os-version', type=int, metavar='N',
                    help="append a 4-byte LE OS-version trailer (e.g. 370), so the "
                         "file matches the OS's own 244-byte ResetCMOS format exactly")
    ap.add_argument('--validate', metavar='CMOS.RAM',
                    help="compare table locations against a raw 256-byte cmos.ram")
    a = ap.parse_args()

    img = build_image(a.kernel_src)
    print(f"built {len(img)}-byte factory CMOS; checksum loc 239 = &{img[0xEF]:02X}", file=sys.stderr)
    out_bytes = img
    if a.os_version is not None:
        out_bytes = img + a.os_version.to_bytes(4, 'little')  # OS's ResetCMOS trailer
        print(f"appended 4-byte LE OS-version trailer &{a.os_version:X} "
              f"-> {len(out_bytes)}-byte ResetCMOS", file=sys.stderr)
    if a.out:
        Path(a.out).write_bytes(out_bytes)
        print(f"wrote {a.out}", file=sys.stderr)
    if a.validate:
        ram = Path(a.validate).read_bytes()
        syms = parse_cmos_map(_find_hdr_cmos(Path(a.kernel_src)))
        syms.setdefault('ConfiguredLang', _configured_lang(a.kernel_src))
        table = parse_default_table(Path(a.kernel_src) / 's' / 'NewReset', syms,
                                    {'Select16BitSound': True, 'NewClockChip': False})
        ok = bad = 0
        inv = {v: k for k, v in sorted(syms.items()) if isinstance(v, int) and v < 240}
        for loc in sorted(table):
            phys = logical_to_phys(loc)
            want, got = img[loc], ram[phys]
            name = inv.get(loc, f'loc{loc}')
            if want == got:
                ok += 1
            else:
                bad += 1
                print(f"  DIFF {name:<20} loc &{loc:02X} phys &{phys:02X}: "
                      f"table=&{want:02X} ram=&{got:02X}")
        print(f"table locations: {ok} match, {bad} differ (differences are "
              f"dynamic/hardware-set locations)", file=sys.stderr)
