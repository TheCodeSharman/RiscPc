# CMOSSwap — per-OS CMOS save/restore for the universal `!Boot`

A tiny standalone BBC BASIC utility the multi-ROM switcher calls from `BootRun`
(see `build.py` `patch_bootrun_per_os_bootcfg`). On a ROM swap it saves the
outgoing OS's CMOS to `Choices.CMOS-<owner>` and restores the incoming OS's
`Choices.CMOS-<tag>`, so each RISC OS version keeps its own CMOS.

**Why:** the CMOS **module-unplug mask is position-keyed** to ROM-module order
and misfires across ROMs — e.g. 4.02's Freeway/ShareFS unplug bits (positions
90/91) land on 3.7's **Net/BootNet** (its core network stack). A shared CMOS
therefore breaks networking on a swap. See the memory
`riscpc-multiboot-network-cross-contamination` and the Jul 12 Dev Diary entry.

## Files

- **`Source,fff`** — the readable source (text, no line numbers). Edit this.
- **`CMOSSwap,ffb`** — the tokenised BASIC that `build.py` places at
  `!Boot.Utils.CMOSSwap`. **This is what actually ships.**

## Format / mechanism

Mirrors `!SaveCMOS`'s proven calls: a 240-byte type `&FF2` image of CMOS
locations `0..239` (`OS_Byte 161` to read, `162` to write; `OS_File 10/255` to
save/load). Locations `0..239` **exclude the RTC clock**, so a restore never
disturbs the time. Restore skips location 0 (as `!SaveCMOS` does). Same format
as the hooks' `ResetCMOS` (the per-OS *factory* image).

Reads two system variables set by `BootRun`:
- `CMOSSwap$Save` — file to write the outgoing OS's CMOS to (unset = skip)
- `CMOSSwap$Load` — file to restore this OS's CMOS from (seeded if absent)

## Re-tokenising after editing `Source,fff`

There is no host-side BASIC tokeniser (our `bastotxt` is detokenise-only), so
produce `,ffb` inside RISC OS (e.g. under RPCEmu). In a command window:

```
BASIC
TEXTLOAD "<path>.Source"
SAVE "<path>.CMOSSwap"
QUIT
```

Then copy `CMOSSwap,ffb` back here. Verify the round-trip with
`bastotxt -i CMOSSwap,ffb` — it should match `Source,fff` (auto-numbered).

## Known limitation (apply-timing)

The CMOS unplug mask is consumed at **ROM module-init, before `!Boot` runs**, so
restoring in `BootRun` is too late for *that* boot — it takes effect on the next
reset. The first boot after a swap runs with the previous OS's module set; the
intended fix is to restore early and force a reset (reset vector via an
`OS_EnterOS` stub). Until then: reboot once after a ROM swap, or (emulator only)
have `swap-rom` pre-apply the per-OS `cmos.ram`.
