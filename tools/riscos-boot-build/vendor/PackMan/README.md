# PackMan 0.9.7-1 (vendored — 26-bit-capable)

`!PackMan` here is **PackMan 0.9.7-1** by Alan Buckley, vendored because it is
the newest release that actually runs on **26-bit RISC OS 3.7** (verified on a
real RISC PC). It is the copy that ships pre-installed in RPCEmu's bundled
RISC OS 3.71 quick-start image.

## Why not download it like the other sources?

The build normally pins each source to a URL + sha256 (`sources.json`). PackMan
can't be: the ROOL package repo (`packages.riscosopen.org`) only ever serves the
**latest** build (currently **0.9.8-1**), and the GitHub `v0.9.7` release tag has
**no built asset** (source only). So there is no stable URL for a clean 0.9.7 zip
— hence it's vendored here and placed via a `repo` entry, exactly like `!raFS`.

## The 0.9.8 regression

0.9.8-1 (the ROOL-repo latest) **fails to load on 26-bit** with *"No writeable
memory at this address"*. Both 0.9.7 and 0.9.8 are GCCSDK/UnixLib C++ builds
carrying an AIF address-mode of 32, so the AIF flag is **not** the discriminator
— 0.9.7 is 26/32-neutral in practice and 0.9.8 regressed (a newer GCCSDK /
SharedUnixLibrary that dropped 26-bit neutrality). The package's `Environment:
arm` tag claims "all ARM machines", which 0.9.8 no longer honours on 26-bit —
i.e. an upstream packaging error, not something on our side.

## Provenance

Copied from `~/Projects/rpcemu/installs/riscos-371/hostfs/Apps/Admin/!PackMan`.
PackMan's mutable state (Choices, Sources, package DB) lives **outside** the app
dir (in `!Boot.Choices.PackMan` and `!Boot.Resources.!Packages`), so this app
directory is pristine. Licence: Apache-2.0 (see `!PackMan/LICENSE`).
