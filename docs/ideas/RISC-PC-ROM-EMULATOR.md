# RISC PC ROM Emulator Research Notes

## Background

The goal is to replace the two 27C800 ROM chips in a RISC PC with an emulator that can serve RISC OS ROM images, enabling easy ROM switching and experimentation.

---

## RISC PC ROM Architecture

### Physical ROM chips

The RISC PC uses **two 27C800 EPROMs** in a 42-pin DIP package:

- Each chip is **8Mbit = 1MB** in 16-bit word mode (1M × 16-bit)
- Together they form a **32-bit wide, 2MB ROM** (1M × 32-bit)
- Both chips receive the **same address lines (A0–A19)** and the same /ROMCS
- Chip 0 drives D0–D15, Chip 1 drives D16–D31

### IOMD ROM controller

From the IOMD Functional Specification (Acorn drawing 0297,030/FS Issue 4):

- Two ROM banks (ROMCR0, ROMCR1), each 16MB, individually configurable
- ROM control register bits [4:0]:
  - Bits [2:0] = initial access speed (Sp0–Sp2)
  - Bits [4:3] = burst access speed (Brst0–Brst1)
- RISC OS sets the RISC PC ROM to:
  - **Initial access: 156.25nS** (Sp = 0b010)
  - **Burst: 93.75nS** (Brst = 0b10) on ARM610 and ARM710A+
  - **Burst off** on early ARM710 revisions
- ROMCR value for normal RISC PC: `0x12` (156.25ns + 93.75ns burst)

Burst mode at the signal level means /ROMCS is held low while address lines
increment. The emulator simply needs to present valid data within 93.75nS of
each address change during a burst — there is no special protocol.

### ROM bus voltage

The RISC PC ROM bus operates at **5V** (confirmed from service documentation
and repair notes). Any emulator must be 5V tolerant on all address, data and
control inputs.

### Codename notes

- **Kryten** = Acorn A7000 (ARM7500 SoC)
- **Morris** = Acorn A7000+ (ARM7500FE SoC, RISC OS 3.71)
- The slower ROM speed initialisation in the POST code (`s/ARM600`, `TestSrc/Begin`) is gated behind a Morris/Kryten IOMD ID check (`&98`/`&5B`) and is **not executed on the RISC PC** — the RISC PC IOMD has a different ID and branches past it.

---

## One ROM Analysis

[One ROM](https://github.com/piersfinlayson/one-rom) is an open source ROM
emulator using the RP2350B/RP2354B. The existing `fire-40-a` board targets
27C400 (40-pin, 512K × 16-bit) ROMs. We investigated extending it for the
27C800.

### GPIO pinout (fire-40-a)

| Function | GPIOs |
|---|---|
| Data D0–D15 | 0–15 |
| /OE | 16 |
| /CE | 17 |
| /BYTE / A0 | 18 |
| Address A0–A18 | 18–37 (see JSON config) |
| Image select | 38–41 |
| Status LED | 42 |
| USB VBUS | 46 |
| Flash /CS | 47 |

**Total used: 43 of 48 GPIOs**

### 5V tolerance problem

On the RP2350 (all steppings including A4), **GPIOs 26–29 are NOT 5V tolerant**.
They are shared with the ADC and have an internal reverse diode to the 3.3V
VDDIO rail, limiting absolute maximum input to ~3.6V. This cannot be changed
in software or configuration.

The fire-40-a maps four address lines onto these pins:

| GPIO | Address line |
|---|---|
| 26 | A10 |
| 27 | A9 |
| 28 | A18 |
| 29 | A8 |

This is a **latent bug in fire-40-a for 5V systems** including the RISC PC.
GPIOs 0–25 and 30–47 on RP2350B A4 silicon are 5V tolerant and safe to use.

A fire-42-a design must remap A8, A9, A10, A18 off GPIOs 26–29 onto safe
GPIOs. The extra PCB length from the 42-pin DIP body (~5mm vs 40-pin) gives
additional routing room to do this.

### Memory limitation — the fundamental blocker

The RP2350B has **520KB of SRAM**. One ROM allocates **512KB** of this for the
ROM image buffer. ROM images must be preloaded from flash into SRAM at boot —
serving directly from flash XIP is too slow.

| | Size |
|---|---|
| 27C800 image (per chip) | 1MB |
| SRAM image buffer | 512KB |
| **Shortfall per board** | **512KB** |

With two boards required (one per ROM socket), the total shortfall is 1MB.
This is a fundamental problem that requires either:

- External PSRAM on the board (firmware + hardware changes)
- A completely different emulator architecture

---

## Alternative Design: SRAM + MCU

Given the memory constraints of the pure-software approach, a simpler and more
robust design uses a dedicated SRAM chip for ROM emulation, with an MCU only
responsible for loading the image at power-on.

### Concept

```
                  ┌─────────────────────────────┐
RISC PC bus ──────┤  1Mx16 SRAM                 │
  A0–A19  ───────►│  (e.g. AS6C8016 or IS61WV)  ├──── D0–D15 ──► RISC PC bus
  /ROMCS  ───────►│  CE                          │
  /OE     ───────►│  OE                          │
                  └──────────┬──────────┬────────┘
                             │ A0–A19   │ D0–D15
                             │ /WE      │
                  ┌──────────┴──────────┴────────┐
                  │  MCU (e.g. RP2040)            │
                  │  - Reads ROM image from SPI   │
                  │    flash or SD card at boot   │
                  │  - Writes image into SRAM     │
                  │  - Tristates and steps aside  │
                  └──────────────────────────────┘
```

### How it works

1. At power-on, MCU takes control of address + data + /WE lines
2. MCU loads 1MB ROM image from SPI flash into SRAM (write cycle)
3. MCU tristates its address/data outputs
4. /WE is permanently deasserted (tied high or held high by MCU)
5. RISC PC accesses SRAM directly — /ROMCS → /CE, /OE → /OE
6. SRAM responds within its rated access time (no MCU involvement)

### Advantages over pure-software approach

- **No timing constraints on MCU** — SRAM handles all bus cycles in hardware
- **Easily meets 156.25ns** — fast SRAM (e.g. 10–55ns rated) has massive margin
- **Burst mode works automatically** — SRAM just follows the address bus
- **No 5V tolerance issues** — SRAM inputs are natively 5V compatible
- **Simpler firmware** — MCU only does a one-time sequential write at boot
- **No SRAM shortage** — a 1Mx16 SRAM chip holds the full 27C800 image

### Suitable SRAM chips (1Mx16, 5V compatible)

| Part | Access time | Package | Notes |
|---|---|---|---|
| AS6C8016 | 55ns | 44-pin TSOP | Cheap, widely available |
| IS61WV102416 | 10ns | 44-pin TSOP | Very fast |
| CY62167 | 55ns | 44-pin TSOP | Alliance/Cypress |

All of the above are 3.3V/5V compatible and have 5V-tolerant inputs.

### MCU choice

The MCU only needs to:
- Drive 20 address lines + 16 data lines + /WE = 37 GPIO outputs
- Read a ROM image from SPI flash (4 SPI pins)
- Tristate its outputs after loading

An **RP2040** or simple microcontroller works fine. The RP2350 is overkill but
usable. With an RP2040 (30 GPIOs), you'd need a small 8-bit latch or shift
register for the upper address bits — or just use a 44-pin MCU with enough
pins.

Alternatively, the MCU address and data buses can be **shared** with the RISC
PC bus and SRAM during load (MCU drives, SRAM listens), then MCU tristates and
RISC PC takes over. Only /WE needs switching.

### PCB design considerations

- Two boards required (one per ROM socket), each with its own SRAM + MCU
- 42-pin DIP form factor to fit the RISC PC ROM sockets
- SPI flash (e.g. 8MB W25Q64) to hold one or more ROM images
- Image select jumpers to choose between ROM images
- /WE control: MCU asserts during load, deasserts and tristates after
- Both boards receive same A0–A19 and /ROMCS from the RISC PC
- Board 0 drives D0–D15, Board 1 drives D16–D31

### RISC PC ROM socket pinout (27C800, 42-pin DIP)

| Pin | Signal | Pin | Signal |
|---|---|---|---|
| 1 | A18 | 42 | A19 |
| 2 | A8 | 41 | VCC (+5V) |
| 3 | A7 | 40 | /OE |
| 4 | A6 | 39 | A17 |
| 5 | A5 | 38 | A16 |
| 6 | A4 | 37 | A15 |
| 7 | A3 | 36 | A14 |
| 8 | A2 | 35 | A13 |
| 9 | A1 | 34 | A12 |
| 10 | A0 | 33 | A11 |
| 11 | /CE | 32 | A10 |
| 12 | D7 | 31 | A9 |
| 13 | D6 | 30 | D15 |
| 14 | D5 | 29 | D14 |
| 15 | D4 | 28 | D13 |
| 16 | D3 | 27 | D12 |
| 17 | D2 | 26 | D11 |
| 18 | D1 | 25 | D10 |
| 19 | D0 | 24 | D9 |
| 20 | GND | 23 | D8 |
| 21 | /BYTE | 22 | /WE |

*Note: verify pinout against 27C800 datasheet before PCB layout.*

---

## Open Questions

1. **Confirm 27C800 pinout** — verify against the actual datasheet (in `docs/`
   if available) before committing to PCB layout.
2. **Image loading speed** — at SPI flash speeds, loading 1MB takes ~100ms at
   80MHz SPI. Acceptable? RISC PC boot waits for ROM from power-on.
3. **/WE tristate** — confirm the MCU GPIO tristates reliably before the RISC
   PC starts driving the bus. May need a hardware interlock.
4. **RISC OS ROM image format** — confirm whether the 1MB per chip is simply a
   flat binary split of the 2MB ROM image (low 16 bits vs high 16 bits, or low
   1MB vs high 1MB of address space).
5. **One ROM contribution** — the GPIO 26–29 5V tolerance bug in fire-40-a is
   worth reporting upstream regardless of which emulator design is pursued.

---

## References

- `docs/IOMD Functional Specification.pdf` — ROM control register (Figure 4.4, p.9)
- `external/Kernel/s/ARM600` — RISC PC ROM speed initialisation
- `external/Kernel/TestSrc/Begin` — Morris/Kryten ROM speed (skipped on RISC PC)
- `external/Kernel/s/Morris` — Morris platform ROM header
- `external/one-rom/` — One ROM source code and documentation
- `external/one-rom/rust/config/json/fire-40-a.json` — GPIO assignments
- `external/one-rom/docs/RP2350.md` — RP2350 timing and memory analysis
- `ACORN_POST.md` — POST protocol documentation
- `Dev Diary.md` — Hardware repair log
