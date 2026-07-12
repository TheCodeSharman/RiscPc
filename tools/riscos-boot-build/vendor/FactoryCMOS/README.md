# FactoryCMOS — vendored per-OS factory CMOS seeds for the multi-ROM `!Boot`

The multi-ROM switcher (`build.py` `patch_bootrun_per_os_bootcfg` + `CMOSSwap`)
keeps a per-OS CMOS snapshot so the position-keyed module-unplug mask can't
misfire across ROM versions. A brand-new OS with no snapshot must be seeded from
its **factory** image — its own reset defaults, every module-unplug bit clear —
**not** from the outgoing OS's mis-keyed live CMOS (that was the bootstrap bug).
`build.py` `place_factory_cmos()` pre-places `!Boot.Choices.CMOS-<tag>` from
these factory images.

## Where each OS's factory image comes from

Every OS's factory image is its hook's **`ResetCMOS`** — a 244-byte file = a
**240-byte SaveCMOS image** (CMOS locations 0..239) **+ a 4-byte little-endian
OS-version trailer** (`&172` = 370, `&190` = 400, `&1F4` = 500). `build.py` seeds
`Choices.CMOS-<tag>` from the leading 240 bytes.

- **RISC OS 4.02 / 5.x** — the OS **ships its own** `ResetCMOS` inside the boot
  structure: `!Boot.RO400Hook.ResetCMOS` and `!Boot.RO500Hook.ResetCMOS` (RO5.3
  inherits RO500Hook's). `build.py` reads them straight from the assembled disc
  — nothing to vendor here.
- **RISC OS 3.7** — ships **no** `ResetCMOS`, so we supply one, named and
  formatted identically to the OS's own: **`RO370Hook/ResetCMOS,ff2`**,
  reconstructed from Kernel source. This keeps the Kernel/HdrSrc submodules out
  of the boot builder's runtime dependencies — `build.py` just copies the
  committed file.

## Files

- **`RO370Hook/ResetCMOS,ff2`** — the vendored RISC OS 3.70 factory image
  (240-byte type `&FF2` SaveCMOS image + 4-byte LE `370` trailer = 244 bytes),
  the `ResetCMOS` that RISC OS 3.70 would have shipped in its hook. **This is
  what ships.** Regenerate it with the script below only when the reconstruction
  logic or the Kernel source changes.
- **`factory_cmos.py`** — the generator/provenance tool. Reconstructs the image
  from the Kernel's own reset table; also validates it against a real `cmos.ram`.

## How `CMOS-RO370,ff2` is reconstructed

`factory_cmos.py` reads two files from the RISC OS 3.70 Kernel checkout
(`external/Kernel` @ `RO_3_70`, with `external/HdrSrc` beside it):

- **`s/NewReset` → `DefaultCMOSTable`** — the list of non-zero reset defaults as
  `= <symbol>, <value>` byte pairs, terminated by `= &FF`.
- **`hdr/CMOS`** — the CMOS location map (ObjAsm storage map: `*` EQU, `#`
  reserve, `^` set counter) giving each symbol's byte offset.

It evaluates the ObjAsm expressions (`:SHL:`/`:OR:`, `2_…` binary, `&` hex, and
the `[ … ]` conditional blocks under the RiscPC config `Select16BitSound=TRUE`,
`NewClockChip=FALSE`), lays the values into a 240-byte image, and writes the
checksum at location 239 as `(CMOSxseed + Σ locs 0..238) & &FF` — the exact
algorithm from `s/PMF/i2cutils` `ValChecksum`.

### Regenerate

```
python3 factory_cmos.py <path-to-Kernel> --os-version 370 -o "RO370Hook/ResetCMOS,ff2"
```
e.g. from this directory, with the submodules initialised:
```
python3 factory_cmos.py ../../../../external/Kernel --os-version 370 -o "RO370Hook/ResetCMOS,ff2"
```
(`--os-version 370` appends the 4-byte LE trailer so the file matches the OS's
own 244-byte `ResetCMOS` format exactly.)

### Validate against a real machine

Compare the reconstructed table locations against a raw 256-byte `cmos.ram`
(from any RISC OS 3.70 install). The static table locations must match
byte-for-byte; the only differences are runtime/hardware-set locations —
YearCMOS (RTC), configured filing system, RMA size, volume bit, CDROMFS config,
and SystemSpeedCMOS's CMOSResetBit (cleared post-boot):

```
python3 factory_cmos.py ../../../../external/Kernel \
        --validate /path/to/installs/riscos-370/cmos.ram
```
