# riscos-boot-build

A reproducible builder for a **universal RISC OS `!Boot`** tree, assembled from
official RISC OS Open sources plus this repo's `!RaFS`. The output is a
**HostFS-shaped directory** (every file carries its `,xxx` filetype suffix) that
copies straight onto a fresh FileCore disc through RPCEmu's HostFS, filetypes
intact — no renaming.

## Why this exists

The RiscPC's SD card accumulated a bad stored boot state: booting from it
triggered an ADFFS data abort (`&038xxxxx`, ADFFS's emulated Archimedes ROM
region) that a clean boot structure does not. The abort **reproduces under
RPCEmu** — healthy emulated hardware — so it is data/software, not the cable or
RAM. Rather than chase the corrupt byte, the fix is a **fresh, known-good boot
image**, rebuilt from official sources by a script we can re-run and audit.
See `docs/handover-disc-vs-hardware.md` and the Dev Diary for the investigation.

## What it builds

1. **HardDisc4** (ROOL) → the disc root: `!Boot` (all `ROxxxHook` incl.
   `RO370Hook` for RISC OS 3.7), `Apps`, `Utilities`, … It also bundles a
   RISC-OS-5-era `!System` at `!Boot.Resources.!System`.
2. **PlingSystem** (ROOL "System resources") → the disc-based module sets
   `310/350/360/370/400` that older, 26-bit OSes need. These are **merged** into
   HardDisc4's `!System`.
3. **PackMan** (Alan Buckley, `arm` arch = 26/32-bit) → `Utilities.!PackMan`.
4. **`!RaFS`** (this repo, `rafs/rafs116/!raFS`) → `Utilities.!RaFS`.

PackMan and RaFS go in **`Utilities` and are not auto-booted** — RaFS is kept
off the boot path deliberately (the ADFFS abort only appeared with RaFS active),
so it loads only when you run it.

## The `!System` merge (what `!SysMerge` does)

RISC OS's `!SysMerge` runs an `Installer` module and `Install_Update <src> <dst>`
per module: **copy only if the incoming module is a newer version** — never
downgrade. `build.py` replicates exactly that:

- Union the two `!System`s. Everything unique is copied.
- For files present in **both**, replace HardDisc4's copy only if PlingSystem's
  is strictly newer — by **module version** (parsed from the module's help
  string) for modules, else by **datestamp** (from the zip's Acorn extra-field).

Only **3 modules** actually overlap (`ABCLib`, `Network/MManager`, `Fonts`); the
rest is a clean union. Every overlap decision is logged. Installing the full
`310–400` set (even parts a 3.7 machine doesn't strictly need) is safe *because*
the merge only ever upgrades — that's what makes the result a truly universal
boot.

## Filetypes: the Acorn extra-field → HostFS `,xxx`

ROOL/packages zips store load/exec (hence filetype + datestamp) in an **Acorn
extra-field**, not in the filename. A plain `unzip` drops every type. `roextract.py`
reads that field and writes `name,xxx`, so files are HostFS-correct on disk.

## Usage

```sh
python3 build.py
```

Downloads (sha256-verified per `sources.json`) land in `downloads/`; the output
tree in `build/disc/`. Both are git-ignored — the **recipe** is what's tracked.

## Deploy

Copy the contents of `build/disc/` onto a fresh FileCore disc via RPCEmu HostFS
(HostFS decodes the `,xxx` names back into real filetypes). Then snapshot the
FileCore image as your known-good baseline.

## `local/rafs-config/` (build input, author once in RPCEmu)

The RaFS nested-`!Packages` config is fiddly to author by hand, so create it once
inside RPCEmu, copy the resulting folder out via HostFS into `local/rafs-config/`,
and commit it. `build.py` overlays it onto the disc root if present.

## Re-pinning versions

`sources.json` pins each archive by sha256 so the build is reproducible even
though the URLs serve "latest". When bumping a version, update the sha256 and
re-check the merge log — a new release could change which of the 3 overlapping
modules wins.
