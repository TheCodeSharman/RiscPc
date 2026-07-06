# GBSC Pro flasher (Linux)

A native Linux flasher for the **RetroScaler GBSC Pro** upscaler — the composite/
S-video variant of gbs-control that sits on the RISC PC's video→HDMI path.

RetroScaler only ship Windows tools (`GBSC_PRO_Programmer.exe`,
`NodeMCU-PyFlasher.exe`) in their firmware zip. This directory reverse-engineers the
AV-module programmer's serial protocol and reimplements it in Python so the GBSC Pro
can be updated from this box without Windows. See [`PROTOCOL.md`](PROTOCOL.md) for the
full wire spec and how it was derived (ILSpy decompile of the vendor exe).

## The GBSC Pro has two firmwares

| Part | Chip | File in release zip | Flash with |
|------|------|---------------------|------------|
| **AV module** | HDSC **HC32** (+ LM1881 sync) | `GBSC_PRO_AV_MODULE_vX.Y.bin` | `gbsc_pro_flash.py` (this tool) |
| **ESP module** | ESP8266 (web UI) | `GBSCPro_YYYY-M-D.ino.bin` | `esptool` (see below) |

For **v1.3** the *only* change is in the AV module (the "1X crop" / 525p-625p
autoswitch fix); the ESP bin is unchanged since v1.2.3. The matching official bins for
v1.3 are staged in [`firmware/`](firmware/).

## Requirements

`pyserial`. In this repo just use the dev shell, or:

```bash
nix-shell -p 'python3.withPackages(ps: [ps.pyserial])'
```

Your user needs access to the serial device (`dialout` group, or run under the
sudo-askpass wrapper).

## Flashing the AV module (this tool)

1. Connect the AV module's programming USB/UART to this machine and put it in
   bootloader mode (power-on/reset — the bootloader prints its `HCMGBoot.` banner for
   a short window). In bootloader mode it enumerates as USB **2E88:4603** →
   `/dev/ttyACM*`.
2. Confirm it's seen:
   ```bash
   ./gbsc_pro_flash.py --list
   ```
3. Flash (auto-detects the port by VID:PID):
   ```bash
   ./gbsc_pro_flash.py firmware/GBSC_PRO_AV_MODULE_v1.3.bin
   ```
   or pin the port: `--port /dev/ttyACM0`.

Verify the tool without any hardware attached:

```bash
./gbsc_pro_flash.py --selftest      # checks CRC-16/XMODEM + packet framing
```

**Safety:** the transfer is plain YMODEM to a resident bootloader — a failed/
interrupted flash leaves the bootloader intact, so just power-cycle and retry. Only
flash the official AV-module bin for your hardware; do not send the ESP `.ino.bin`
here.

## Flashing the ESP module (esptool, not this tool)

The ESP half is a stock Arduino/ESP8266 image; flash it at offset `0x0`:

```bash
nix-shell -p esptool --run \
  'esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash 0x0 firmware/GBSCPro_2025-7-29.ino.bin'
```

(This is exactly what the bundled NodeMCU-PyFlasher does; it relies on DTR/RTS
auto-reset to enter flash mode.) Back up your slots/Wi-Fi config from the web UI first
if the flash might reset them. For v1.3 you can skip this — the ESP bin didn't change.

## Provenance

- Upstream firmware: <https://github.com/RetroScaler/gbsc-pro> (v1.3, 2025-11-15)
- Vendor tool reversed: `GBSC_PRO_Programmer.exe` ("GBSC PRO Programmer V0.2",
  .NET/WinForms on the YModemWin library)
