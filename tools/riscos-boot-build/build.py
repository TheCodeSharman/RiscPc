#!/usr/bin/env python3
"""Build a universal RISC OS !Boot tree from official sources.

Produces a HostFS-shaped directory tree (files carry ,xxx filetype suffixes) that
can be copied straight onto a FileCore disc via RPCEmu's HostFS with types intact.

Recipe:
  1. download + sha256-verify HardDisc4, PlingSystem, PackMan (sources.json)
  2. extract each with correct HostFS ,xxx names (roextract)
  3. lay HardDisc4 down as the disc root
  4. merge PlingSystem's !System into HardDisc4's bundled !System,
     newest-version-wins -- exactly what RISC OS's !SysMerge/Install_Update does
     (only 3 modules actually overlap; everything else is a clean union)
  5. drop PackMan and !RaFS (from rafs/ in this repo) into Utilities, NOT auto-booted
  6. overlay local/rafs-config/ if present (the RaFS nested-!Packages config)

The output is intentionally NOT committed; the recipe + local inputs are.
"""
import os, sys, json, shutil, hashlib, subprocess
from pathlib import Path
import roextract

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DL = HERE / 'downloads'
WORK = HERE / 'build'
STAGE = WORK / '_stage'
OUT = WORK / 'disc'
RAFS_SRC = REPO / 'rafs' / 'rafs116' / '!raFS'
RAFS_CONFIG = HERE / 'local' / 'rafs-config'


def log(m): print(m, flush=True)


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def ensure_downloads(sources):
    DL.mkdir(parents=True, exist_ok=True)
    for s in sources:
        dest = DL / s['file']
        if dest.exists() and sha256(dest) == s['sha256']:
            log(f"  [cached] {s['file']}")
            continue
        log(f"  downloading {s['file']} ...")
        try:
            import urllib.request
            req = urllib.request.Request(s['url'], headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as r, open(dest, 'wb') as f:
                shutil.copyfileobj(r, f)
        except Exception as e:
            log(f"    urllib failed ({e}); falling back to curl")
            subprocess.run(['curl', '-sL', '-A', 'Mozilla/5.0', '-o', str(dest), s['url']], check=True)
        got = sha256(dest)
        if got != s['sha256']:
            sys.exit(f"sha256 mismatch for {s['file']}:\n  got  {got}\n  want {s['sha256']}")
        log(f"    verified {s['file']}")


def module_version(path):
    """Version float from a RISC OS module's help string, else None (not a module)."""
    try:
        data = open(path, 'rb').read()
    except OSError:
        return None
    if len(data) < 0x1c:
        return None
    help_off = int.from_bytes(data[0x14:0x18], 'little')
    if help_off == 0 or help_off + 1 >= len(data):
        return None
    end = data.find(b'\x00', help_off)
    s = data[help_off:end if end >= 0 else len(data)].decode('latin-1', 'replace')
    if '\t' not in s:
        return None
    tail = s.split('\t', 1)[1].strip()
    num = ''
    for ch in tail:
        if ch.isdigit() or ch == '.':
            num += ch
        elif num:
            break
    try:
        return float(num) if num else None
    except ValueError:
        return None


def replace_p(tgt_file, src_file, tgt_meta, src_meta):
    """Should PlingSystem's src replace HardDisc4's target? Mirrors Install_Update:
    replace only if the incoming file is strictly newer (module version, else datestamp)."""
    tv, sv = module_version(tgt_file), module_version(src_file)
    if tv is not None and sv is not None:
        return sv > tv, f"module version target={tv} src={sv}"
    ts = (tgt_meta or {}).get('stamp')
    ss = (src_meta or {}).get('stamp')
    if ts is not None and ss is not None:
        return ss > ts, f"datestamp target={ts} src={ss}"
    # Non-comparable: for the disc-based System resources, prefer PlingSystem's copy.
    return True, "no comparable metadata -> take PlingSystem (System resources)"


def merge_system(src_sys, tgt_sys, src_man, tgt_man, src_prefix, tgt_prefix):
    added = kept = replaced = 0
    for root, _dirs, files in os.walk(src_sys):
        rel = os.path.relpath(root, src_sys)
        for fn in files:
            src_file = Path(root) / fn
            relpath = fn if rel == '.' else f"{rel}/{fn}"
            tgt_file = tgt_sys / relpath
            if not tgt_file.exists():
                tgt_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, tgt_file)
                added += 1
                continue
            src_meta = src_man.get(f"{src_prefix}{relpath}")
            tgt_meta = tgt_man.get(f"{tgt_prefix}{relpath}")
            do, why = replace_p(tgt_file, src_file, tgt_meta, src_meta)
            log(f"    overlap {relpath}: {'REPLACE' if do else 'keep    '}  ({why})")
            if do:
                shutil.copy2(src_file, tgt_file)
                replaced += 1
            else:
                kept += 1
    log(f"  merged: {added} added, {replaced} replaced (newer), {kept} kept (target newer/equal)")


def write_basic64_fallback(out):
    """Housekeeping from !SysMerge: a fallback BASIC64 command in Boot.Library."""
    lib = out / '!Boot' / 'Library'
    lib.mkdir(parents=True, exist_ok=True)
    body = 'RMEnsure BASIC64 0 RMLoad System:Modules.BASIC64\n'
    (lib / 'BASIC64,feb').write_text(body)  # type &FEB = Obey


def copytree(src, dst):
    shutil.copytree(src, dst, dirs_exist_ok=True)


def main():
    cfg = json.load(open(HERE / 'sources.json'))
    sources = cfg['sources']
    byname = {s['name']: s for s in sources}

    log("== 1. download + verify official sources ==")
    ensure_downloads(sources)

    if WORK.exists():
        shutil.rmtree(WORK)
    STAGE.mkdir(parents=True)

    log("== 2. extract archives with HostFS ,xxx names ==")
    man = {}
    for s in sources:
        man[s['name']] = roextract.extract(DL / s['file'], STAGE / s['name'], strip=s.get('strip', ''))
        typed = sum(1 for v in man[s['name']].values() if v and v.get('ftype') is not None)
        log(f"  {s['name']}: {len(man[s['name']])} files ({typed} typed)")

    log("== 3. lay HardDisc4 down as the disc root ==")
    copytree(STAGE / 'HardDisc4', OUT)

    log("== 4. merge PlingSystem !System -> !Boot.Resources.!System (newest-wins) ==")
    merge_system(
        STAGE / 'PlingSystem' / '!System',
        OUT / '!Boot' / 'Resources' / '!System',
        man['PlingSystem'], man['HardDisc4'],
        src_prefix='!System/',
        tgt_prefix='!Boot/Resources/!System/',
    )
    write_basic64_fallback(OUT)

    log("== 5. PackMan + !RaFS into Utilities (not auto-booted) ==")
    util = OUT / 'Utilities'
    util.mkdir(exist_ok=True)
    copytree(STAGE / 'PackMan' / 'Apps' / 'Admin' / '!PackMan', util / '!PackMan')
    if not RAFS_SRC.exists():
        sys.exit(f"!RaFS source not found at {RAFS_SRC}")
    copytree(RAFS_SRC, util / '!RaFS')

    log("== 6. RaFS nested-!Packages config overlay ==")
    if RAFS_CONFIG.exists():
        copytree(RAFS_CONFIG, OUT)
        log(f"  applied overlay from {RAFS_CONFIG}")
    else:
        log("  (local/rafs-config not present yet -> skipped; author it in RPCEmu and copy out)")

    log(f"\nDONE. Disc tree: {OUT}")
    log("Deploy: copy its contents onto a fresh FileCore disc via RPCEmu HostFS.")


if __name__ == '__main__':
    main()
