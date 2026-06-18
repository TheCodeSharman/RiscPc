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

When a new mainline release ships (e.g. `release_0.9.6`), use the helper
script that automates the hg-clone + rsync mechanics:

```bash
git checkout main
git checkout -b sync/rpcemu-0.9.6
./tools/raster-lab/scripts/sync-rpcemu-upstream.sh release_0.9.6
git diff HEAD -- external/rpcemu/         # review the upstream delta
git add external/rpcemu/
git commit -m "Import RPCEmu 0.9.6"
git tag -a rpcemu-v0.9.6-import -m "RPCEmu release_0.9.6 verbatim"
git rebase main                           # bring local patches forward
# resolve conflicts where upstream and our patches collide
# open PR sync/rpcemu-0.9.6 -> main
```

The script refuses to run unless you're on a `sync/...` branch — that's
a guardrail because the rsync silently reverts local patches that aren't
yet upstream, so the script must produce a branch with a clean intent.

Why not git-remote-hg: we tried.  Marutan's hg server is too old to
advertise the wire-bundle features modern git-remote-hg expects
(`missing support for changegroup`), so the bridge doesn't work for this
specific upstream.  Plain rsync against a sidecar hg clone is the
reliable path.

## Local patches applied

See `git log --oneline rpcemu-v0.9.5-import..HEAD -- external/rpcemu/`.
