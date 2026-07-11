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
  5. place apps. RaFS-related placements are gated by --format e|f:
       e (default, RISC OS 3.7, 10-char FileCore): !RaFS + the Pkg RaFS disc, so
         !Packages gets long names via a RaFS volume the PackMan !Run hook mounts;
       f (RISC OS 4.02/5.30, native long names): a plain !Packages in
         !Boot.Resources (Filer_Boot'd at startup) -- no RaFS, hook stays inert.
  6. overlay local/*/ if present

The output is intentionally NOT committed; the recipe + local inputs are.
"""
import os, sys, json, shutil, hashlib, subprocess, argparse
from pathlib import Path
import roextract

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DL = HERE / 'downloads'
WORK = HERE / 'build'
STAGE = WORK / '_stage'
OUT = WORK / 'disc'
LOCAL = HERE / 'local'


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


def _ro_leaf(name):
    """RISC OS leafname: drop a trailing ,xxx host filetype suffix if present."""
    if len(name) >= 4 and name[-4] == ',' and all(c in '0123456789abcdefABCDEF' for c in name[-3:]):
        return name[:-4]
    return name


def _ro_clash(path, want_dir):
    """True if path's parent already holds a *different-kind* object with the same
    RISC OS leafname (after dropping ,xxx). HostFS shows e.g. '!Help,fff' (file) and
    '!Help' (dir) both as '!Help', which RISC OS then can't copy to FileCore."""
    parent = path.parent
    if not parent.exists():
        return False
    want = _ro_leaf(path.name)
    for sib in parent.iterdir():
        if sib.name != path.name and _ro_leaf(sib.name) == want and sib.is_dir() != want_dir:
            return True
    return False


def merge_tree_add_missing(src_root, out_root):
    """Add files under src_root into out_root only where the target doesn't already
    have them -- so the existing (HardDisc4/ROOL) tree wins every overlap and this
    only ADDS what's missing (Acorn 3.7 content is always older than HardDisc4).
    Collision-safe: a source item is skipped when it would clash, by RISC OS leafname,
    with a different-kind target object (e.g. Acorn's '!Help/' dir vs HardDisc4's
    '!Help,fff' file) -- so overlapping apps keep the target's whole version rather
    than Frankenstein-merging the two into a copy-breaking duplicate."""
    added = kept = 0
    for root, dirs, files in os.walk(src_root):
        rel = os.path.relpath(root, src_root)
        tgt_dir = out_root if rel == '.' else out_root / rel
        if rel != '.' and _ro_clash(tgt_dir, want_dir=True):
            dirs[:] = []          # don't descend a dir that clashes with a target file
            kept += len(files)
            continue
        for fn in files:
            tgt = tgt_dir / fn
            if tgt.exists() or _ro_clash(tgt, want_dir=False):
                kept += 1
                continue
            tgt.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(root) / fn, tgt)
            added += 1
    return added, kept


def _target_has(tgt_dir, name):
    """True if tgt_dir already holds an object with the same RISC OS leafname
    (ignoring the ,xxx type suffix) as `name`."""
    if not tgt_dir.exists():
        return False
    want = _ro_leaf(name)
    return any(_ro_leaf(p.name) == want for p in tgt_dir.iterdir())


def place_children_add_missing(src_container, tgt_container):
    """Place each immediate child of src_container into tgt_container WHOLE (the entire
    file or app directory), but only where tgt_container lacks that RISC OS leafname.
    This adds the apps/content the authoritative disc doesn't have WITHOUT ever
    descending into an existing app to splice files together -- app-merging is what
    duplicated !Flasher's !Help. The more authoritative target (HardDisc4/ROOL) keeps
    its whole app on every overlap; only genuinely-missing items are added."""
    added = kept = 0
    if not src_container.exists():
        return added, kept
    tgt_container.mkdir(parents=True, exist_ok=True)
    for child in sorted(src_container.iterdir()):
        if _target_has(tgt_container, child.name):
            kept += 1
            continue
        dst = tgt_container / child.name
        if child.is_dir():
            copytree(child, dst)
        else:
            shutil.copy2(child, dst)
        added += 1
    return added, kept


def main():
    ap = argparse.ArgumentParser(description="Build the universal RISC OS !Boot tree.")
    ap.add_argument('--format', choices=['e', 'f'], default='e', dest='fmt',
                    help="target FileCore format: 'e' = RISC OS 3.7 (10-char names; "
                         "!Packages via a RaFS volume, RaFS off the boot path) [default]; "
                         "'f' = RISC OS 4.02/5.30 (native long names; plain !Packages in "
                         "!Boot.Resources, no RaFS)")
    fmt = ap.parse_args().fmt
    log(f"== target FileCore format: {fmt.upper()} "
        f"({'3.7 -- RaFS-wrapped !Packages' if fmt == 'e' else '4.02/5.30 -- plain !Packages, no RaFS'}) ==")

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
        man[s['name']] = roextract.extract(DL / s['file'], STAGE / s['name'],
                                           strip=s.get('strip', ''), only=s.get('extract_only'))
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

    log("== 5. place apps (PackMan/PartMgr in Utilities, StrongED/Zap in Apps, RaFS) ==")
    for p in cfg.get('placements', []):
        if p.get('only_format') and p['only_format'] != fmt:
            log(f"  (skip {p['to']} -- only_format={p['only_format']}, building {fmt})")
            continue
        src = REPO / p['repo'] if 'repo' in p else STAGE / p['source'] / p['path']
        dst = OUT / p['to']
        if not src.exists():
            sys.exit(f"placement source missing: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        copytree(src, dst)
        log(f"  {p.get('source', p.get('repo'))}{('/' + p['path']) if 'path' in p else ''} -> {p['to']}")

    log("== 5b. place whole apps/content the authoritative disc lacks (Acorn 3.7 games/sound/movies/manuals; NO app-merging) ==")
    for m in cfg.get('content_place', []):
        src = STAGE / m['source'] / m['container']
        if not src.exists():
            sys.exit(f"content_place source missing: {m['source']}/{m['container']}")
        added, kept = place_children_add_missing(src, OUT / m['container'])
        log(f"  {m['source']} -> {m['container']}: +{added} placed whole, {kept} kept (authoritative already had)")

    log("== 5c. subtree merges (app-bundled !System/!Boot deps, add-missing so ROOL wins overlaps) ==")
    for m in cfg.get('subtree_merges', []):
        src = STAGE / m['source'] / m['from']
        if not src.exists():
            sys.exit(f"subtree_merge source missing: {m['source']}/{m['from']}")
        added, kept = merge_tree_add_missing(src, OUT / m['to'])
        log(f"  {m['source']}/{m['from']} -> {m['to']}: +{added} added, {kept} kept")

    log("== 6. apply local overlays (local/*/ each mirrors disc paths; e.g. acorn = Browse+media, rafs-config) ==")
    # `*.example` dirs are committed placeholder templates, never overlaid.
    overlays = sorted(p for p in LOCAL.glob('*')
                      if p.is_dir() and not p.name.endswith('.example')) if LOCAL.exists() else []
    if not overlays:
        log("  (no local/*/ overlays present)")
    for ov in overlays:
        copytree(ov, OUT)
        log(f"  applied overlay from local/{ov.name}/")

    log("== 7. prune excluded root files ==")
    for ex in cfg.get('exclude_root', []):
        hits = list(OUT.glob(ex)) + list(OUT.glob(ex + ',???'))  # bare or ,xxx-typed, root only
        if not hits:
            log(f"  (no match for {ex})")
        for p in hits:
            p.unlink() if p.is_file() else shutil.rmtree(p)
            log(f"  removed {p.relative_to(OUT)}")

    log(f"\nDONE. Disc tree: {OUT}")
    log("Deploy: copy its contents onto a fresh FileCore disc via RPCEmu HostFS.")


if __name__ == '__main__':
    main()
