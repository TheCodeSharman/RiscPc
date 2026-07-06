# RISC PC session handover — 2026-07-07 → next session

End of a marathon session. The **Freeway/Toolbox mission is DONE** (its own handover,
`docs/rpcemu-freeway-handover.md`, is now historical). This session ran far past it:
PackMan, long filenames, StrongARM game compatibility, memory, and two new
hardware-project ideas. Read the **Immediate next task** first — it's ready to go.

## DONE this session (all committed + pushed)
- **Acorn Access/Freeway over WiFi → working. Toolbox 1.71 merged onto the real RISC PC.**
  The "duplicate IP" wedge was RISC OS's **AUN/Econet `1.x` identity** being answered by
  the blunt tap proxy-ARP → fixed by **scoping the tap's proxy-ARP to the LAN subnet**
  (`arptables`, new `lanSubnet` module option). Persisted: rpcemu fork `integration`
  **93c9e6e**, nix-config `main` **c22bb8a**, `nixos-rebuild` applied.
- **RPCEmu fork**: new *additive* **`NetworkType_IPTunnellingTap`** (unprivileged
  pre-created-tap mode; own GUI radio + "Tunnel Interface" field). Built, tested, merged.
- **Dev diary + memory** updated; two Jul-7 diary entries committed (**9ad4f5a**).
- Only uncommitted in the repo: `.claude/settings.json` (pre-existing, deliberately left).

## Real RISC PC — current state
- **CPU cards**: StrongARM (`RPCSA`, default) **and a physical ARM710** card — swappable
  (RISC PC has two processor slots).
- **RAM**: **8 MB DRAM + 2 MB VRAM**. **2×16 MB SIMMs on order** (eBay, AUD$18, *untested*)
  → 32 MB when they land.
- **Boot**: SD card via **IDE→SD adapter** (FileCore/ADFS). Whole system runs off it fine —
  media is healthy (ruled out as a fault source).
- **OS**: RISC OS **3.71** (26-bit).
- **PackMan**: the **0.9.7 beta** (from the QuickStart). Current 0.9.8+ is 32-bit/RO5-only
  and won't run on 26-bit 3.71 (`No writeable memory at this address`).
- **ADFFS**: **2.88-1** (via PackMan — current release).
- **RaFS** (long-filename image FS): confined to holding **`!PackMan` + `!Packages` only**;
  everything else on plain ADFS. Games live on ADFS, so RaFS can be `*RMKill`'d during
  gaming to free memory. PackMan package root is on RaFS so long-named packages install.

## KEY CONCLUSION — old games vs StrongARM (settled)
- **SWIV / Nevryon / SwivBUZZ hard-crash on the real StrongARM**, but **boot fine on the
  real ARM710** (and in RPCEmu-as-ARM710). **Lemmings2SA works on StrongARM** — it's the
  StrongARM-patched build.
- **Root cause = StrongARM's split I/D cache vs the games' self-modifying code.** ARM710
  (ARMv3, unified cache) runs them; StrongARM (ARMv4, split cache) needs a cache flush the
  old games never do. **Confirmed by hot-swapping real CPUs** — clean A/B, only the chip
  changed.
- **RaFS is NOT the cause**: RPCEmu never touches RaFS yet still shows the CPU-dependent
  behaviour.
- **ADFFS is *supposed* to patch this** (its ARMv4 JIT / per-game fixes) but on this setup
  it doesn't. **Working theory: ADFFS's StrongARM game-compat is developed/tested on
  RISC OS 5; real StrongARM + RO 3.71 is an untested corner and the JIT may not engage on a
  26-bit OS.** Unconfirmed — settle it via the source-dive below.
- **Working answer today: use the ARM710 card for the old games**, StrongARM for modern.
  Two-minute card swap.

## IMMEDIATE NEXT TASK (ready to go) — ADFFS source-dive
ADFFS is **source-available**: Jon Abbott publishes `source<version>.zip` on the JASPP
forum (there'll be a **`source288.zip`** matching 2.88). **JASPP forum AND Wayback both
403 automated fetches**, so the **user must download it in a browser** and drop it on the
Linux box; then read it locally (it's largely ARM assembler). One download answers three
things:
1. **Is the StrongARM/JIT SA-compat gated on RISC OS version?** Grep for
   `OS_ReadSysInfo`/version checks around the JIT init and per-game SA patches. An
   `if RO≥5` gate confirms why 3.71+StrongARM crashes.
2. **The ADFFS debug build (`ADFFS…db`) output channel** — screen vs serial vs buffer.
   ADFFS **has** a debug module variant ("see what's happening / where a game hangs or
   crashes"). If it's **screen-only**, a screen-hogging game defeats it → the worthwhile
   contribution is **adding serial / persistent-buffer output** (source available; Jon may
   take the patch).
3. **The abort handler** — ADFFS already tracks aborts (page-scavenging ~every 10 s). See
   what it records and whether it can report the fault cause/address for SWIV/Nevryon.

## Hardware pending — the 2×16 MB SIMMs
- On arrival: fit **one at a time**, confirm RISC OS reports the right size, then
  **soak-test for flaky cells** — bad RAM = *random data aborts / corruption*, the exact
  ghosts that muddied game debugging today.
- **Repo tie-in**: the RISC PC's **POST tests DRAM at power-on**, and this repo's
  `acorn-post` sigrok decoders read that POST — so **capture the POST to vet a dodgy SIMM**.
- 16 MB is a well-supported size (less RiscPC SIMM-pickiness than big sticks). If one isn't
  detected: reseat, try alone, check a known-good-SIMM list before condemning it.

## NEW PROJECT IDEAS (bench, longer-term)
### Second-CPU-slot bus sniffer → in-circuit debugger
- The **second processor slot is a bus-master slot** (that's how the PC card works). The
  user **already attaches the DSLogic there** for POST captures → **tap is proven**; the
  limit is **channel count** (DSLogic ~16 ch; full bus ≈ **75**: 32 addr + 32 data + ~10
  control).
- **Phase 1 — passive sigrok FPGA capture card** (ECP5 + USB, ~75 ch, ring buffer, trigger
  on abort/freeze). **Make it sigrok/DSView-compatible** so the existing `acorn-post`
  decoders + a new ARM-bus decoder + the whole workflow scale up for free. Bonus: full-bus
  capture makes POST decoding trivial.
- **Phase 2 — active arbitration** (drive the bus-master handshake): **halt** the main CPU
  (starve it of the bus) + **bus-cycle single-step** (grant one cycle at a time). A real
  "halt + step + observe" debugger.
- **Two honest limits**: (a) you step/see **bus cycles, not instructions** — StrongARM
  cached execution never hits the bus (far better on ARM610/710); (b) **no register/internal
  state** via the bus (needs the ARM's JTAG/EmbeddedICE). For *freeze* debugging the
  bus-access sequence usually tells the story without registers.
- **Gating research**: the **second-processor arbitration protocol + pinout** (PC-card
  interface docs / RISC PC tech ref) — decides Phase 2's difficulty *and* is needed for
  Phase 1's cycle-decode. **Do passive first** — it de-risks the active build and hands you
  the real bus protocol.
- **Software-debugger alternative** (the teenage route): defeated by games taking the screen
  + hard freezes (a software debugger shares fate with the crashing machine).
  Complementary, not a replacement. **Serial** debug output survives a screen takeover for
  *soft* crashes.

## PARKED (whenever)
- **RO5 ROM project**: any RiscPC CPU is 32-bit-capable (ARM6/7 = ARMv3; only ARM2/3 are
  26-bit-only), so the StrongARM can take RO5. ROOL sells RiscPC RO5 **ROM sets**; user mused
  about **burning EPROMs + a ROM-switcher board**. RISC PC ROM = **2-chip interleaved** (the
  repo's `ROMS/` has known-good per-chip dumps to validate a burn; RO5 is open/buildable,
  RO3.x only partially). Clears the 26-bit **and** long-filename walls at once — and ADFFS's
  SA support would then be in its tested (RO5) home.
- **JASPP bug report**: ADFFS 2.88 SA game-compat not working on real StrongARM + RO 3.71
  (SWIV/Nevryon crash; boot on ARM710; RPCEmu-as-StrongARM black-screens). Clean, documented
  repro — Jon Abbott is active on the forum.
- **txqueuelen/qdisc fold into `rpcemu-freeway` module** — low value (bulk-Access "lost
  contact" was **IP fragmentation** of ~8 KB AUN datagrams, not tap drops; user routes
  around bulk Access now). Only if bulk Access returns.

## REUSABLE LESSONS (kept biting today)
- **Reboot clean between game tests** — a crashed game leaves RISC OS's workspace corrupt,
  so the *next* thing data-aborts from *residual* state. Change **one variable at a time**.
- **The real recurring villain = version / OS incompatibility** (26-bit vs 32-bit, 3.71 vs
  modern builds), NOT transfer corruption. Reach for the version/arch explanation first.
- **Move files over Access as a *zip*** (CRC catches silent corruption); single files beat
  multi-file trees; only PackMan (small) needs to cross — it fetches everything else over
  the machine's **own internet (TCP)**.
- **FileCore = 10-char names.** Long names need a shim (**RaFS worked; LongFiles HUNG on the
  SD-backed ADFS**) or an OS upgrade (RO4/5). Keep the shim confined to where it's needed
  (`!Packages`/`!PackMan`).
- **ADFFS runs games from a *disc image* via `*ADFBootFloppy`** (the `!Run` calls it), not by
  running the game files bare. Per-game fixes (e.g. Nevryon's MODE 0) live in that boot
  script.
