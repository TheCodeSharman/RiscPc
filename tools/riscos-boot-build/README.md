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
3. **Extra apps**, placed via the `placements` table in `sources.json`. Each
   app's user-visible part goes where you'd expect; its satellite resource/config
   dirs go where that app's own `!Run` looks them up (not just next to it):
   - **PackMan** 0.9.7-1 (**vendored**, `vendor/PackMan/`) → `Utilities.!PackMan`
     — see *26- vs 32-bit compatibility* below for why 0.9.7 and why vendored.
   - **PartMgr** 1.05-1 (JASPP) → `Utilities.Caution.!PartMgr` (disc/partition tool)
   - **StrongED** 4.69f14 (stronged.iconbar.com) → `Apps.!StrongED`;
     **`!StrED_cfg` → `!Boot.Choices`** (StrongED reads it from `Choices$Write`)
   - **Zap** 1.45 (zap.tartarus.org, 26-bit-era stable) → `Apps.!Zap`;
     **`!ZapFonts` → `!Boot.Resources`** (`BootResources:!ZapFonts`) and
     **`!ZapUser` → `!Boot.Choices`** (`Choices:!ZapUser`; without it Zap errors
     *"Please locate !ZapUser"*)
   - **`!RaFS`** (this repo, `rafs/rafs116/!raFS`) → `Utilities.!RaFS`

StrongED and Zap aren't in ROOL's packaging, so they're pinned to their authors'
sites by sha256. RaFS goes in **`Utilities` and is not auto-booted** — kept off
the boot path deliberately (the ADFFS abort only appeared with RaFS active), so
it loads only when you run it.

## 26- vs 32-bit compatibility (this is a RISC OS 3.7 / 26-bit target)

The target RISC PC runs **RISC OS 3.7, which is 26-bit** (on ARM710, and still
26-bit even with a StrongARM card). Everything in the boot must therefore be
26-bit-runnable. The non-obvious rule, learned the hard way:

> **"32-bit" is not a reliable signal of 26-bit *in*compatibility.** Most RISC OS
> software — including GCCSDK/UnixLib C++ apps — is built **26/32-bit neutral**
> and runs on both. Do **not** infer "won't run on 3.7" from a binary being a
> 32-bit-APCS build, nor from its AIF address-mode word (`+0x30`) reading `32`.

What actually tells you:

- **RISC OS Packaging Project `arm` architecture = 26/32-neutral by design.**
  `arm` packages run on RISC OS 3.1–5.x, 26- and 32-bit; this is the whole point
  of the project. The genuinely-incompatible tag is **`armv5`** (Iyonix / Pi-class
  ARMv5+). So the ROOL repo's `arm` packages generally *do* run on 3.7.
- **`CallASWI`** in an app's `!Run` is an explicit 26/32-neutral marker (StrongED
  uses it) — such apps run on 26-bit despite an AIF address-mode of 32.
- The reliable discriminators are: does it need `armv5`-only instructions, or
  hard-require a 32-bit-only module? When unsure, **trust real-hardware evidence
  over the binary's flags.**

**PackMan is the cautionary tale.** The ROOL-repo *latest*, **0.9.8-1**, fails to
load on 26-bit (*"No writeable memory at this address"*) — an individual broken
build, **not** a rule about 32-bit apps. **0.9.7-1** runs fine on 26-bit (verified
on real hardware; it's the copy RPCEmu bundles in its RISC OS 3.71 quick-start).
0.9.7 and 0.9.8 are *both* AIF address-mode 32 + UnixLib, which is exactly why the
flag is not the discriminator. We therefore pin **0.9.7**, and **vendor** it under
`vendor/PackMan/` (with a `README.md`) because it has no stable download URL — the
ROOL repo only serves latest, and GitHub's `v0.9.7` tag ships no built asset.

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

It also **recreates directory entries, including empty ones**. RISC OS zips carry
meaningful empty dirs — HardDisc4 ships the `ROxxxHook.Res`/`.Apps` folders (which
the boot `Filer_Boot`s), plus `!Boot.Choices` and `Public`, as empty dirs. Dropping
them (the naïve "skip anything ending in `/`") makes the RISC OS 3.7 boot throw
"not found" for each missing `ROxxxHook.Res`, so extraction must preserve them.

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

## `local/*/` overlays (machine-specific build inputs)

Each directory under `local/` is a **HostFS-shaped overlay** (mirrors disc paths,
`,xxx`-typed files) copied onto the disc root in step 6. Use these for config
that's authored once in RPCEmu / lifted off a real card, not derived from the
official sources. Dirs ending in **`.example`** are committed placeholder
templates and are **never** overlaid.

- **`local/rafs-config/`** — the RaFS nested-`!Packages` config, fiddly to author
  by hand: create it once inside RPCEmu, copy the folder out via HostFS, commit it.
- **`local/net-config/`** — **preconfigured networking**, so the boot never prompts
  for InetSetup. Lifted from the old card; **git-ignored** because it holds this
  machine's LAN IPs/hostname and the repo is public. Copy `local/net-config.example/`
  (placeholder IPs) to `local/net-config/` and edit for your network. It supplies:
  - `!Boot.Choices.Internet.{Startup,Routes,User}` — the actual config (host name,
    static IP/mask, resolver, default route, ShareFS/Freeway).
  - `!Boot.RO370Hook.Boot.PreDesk.SetupNet` = `Run BootResources:!Internet` — the
    trigger. The stock hook template only starts ShareFS; InetSetup rewrites this
    (in `Choices:Boot`) when you configure the net, so we ship it pre-rewritten.
    `SetChoices` copies the hook's `Boot` template into `Choices:Boot` on first
    boot, so the networking `SetupNet` lands there without a full pre-seeded Choices.
  - `!Boot.Resources.Configure.!InetSetup.AutoSense.EtherX` — Elesar's EtherX
    autosense (BSD-3), so InetSetup still detects the card if re-run.

  The EtherX **driver module lives in the NIC's podule ROM**, so it isn't on disc;
  `RMEnsure EtherX 2.00 …` finds the ROM copy and the RMLoad is skipped. The
  Internet stack modules (`Internet`, `Resolver`, `Freeway`, `ShareFS`, …) are
  already in the merged `!System` from the official sources.

## Re-pinning versions

`sources.json` pins each archive by sha256 so the build is reproducible even
though the URLs serve "latest". When bumping a version, update the sha256 and
re-check the merge log — a new release could change which of the 3 overlapping
modules wins.
