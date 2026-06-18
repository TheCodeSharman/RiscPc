# RPCEmu (vendored)

This directory contains a snapshot of RPCEmu, the Acorn Risc PC emulator,
vendored into this repo so the raster-lab workflow can build a customised
RPCEmu without depending on an external fork or repo.

## Upstream

- **Project home:** https://www.marutan.net/rpcemu/
- **Mainline VCS:** Mercurial at `http://www.home.marutan.net/hg/rpcemu`
- **Imported revision:** `release_0.9.5` (changeset `f005be758787`, 2024-10-23)

The import commit (`rpcemu-v0.9.5-import` tag) captures the upstream state
verbatim.  Local modifications appear as ordinary commits to this directory
on top of that tag.  Extract our changes as a clean upstream-ready diff via:

```
git diff rpcemu-v0.9.5-import HEAD -- external/rpcemu/
```

## Syncing with a new upstream release

When a new mainline release ships (e.g. `release_0.9.6`):

1. `hg pull` in a separate hg clone of mainline, `hg update release_0.9.6`
2. Rsync that clone over `external/rpcemu/` (excluding `.hg`)
3. Commit as "Import RPCEmu 0.9.6"
4. Tag as `rpcemu-v0.9.6-import`
5. Rebase or re-apply local patches on top, resolving conflicts

## Local patches applied

See `git log --oneline rpcemu-v0.9.5-import..HEAD -- external/rpcemu/`.
