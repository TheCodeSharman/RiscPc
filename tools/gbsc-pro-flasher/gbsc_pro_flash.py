#!/usr/bin/env python3
"""
gbsc_pro_flash.py — native Linux flasher for the RetroScaler GBSC Pro AV module.

Replaces the Windows-only GBSC_PRO_Programmer.exe. The AV module is an HDSC HC32
MCU whose resident bootloader speaks a lightly-customised YMODEM-128 over a
USB-CDC serial port. This is the firmware that changes between GBSC Pro releases'
AV-module bins (e.g. the v1.3 "1X crop" / 525p-625p autoswitch fix).

The wire protocol was reverse-engineered from the vendor tool; see PROTOCOL.md
in this directory for the full spec and provenance.

Usage:
    ./gbsc_pro_flash.py firmware/GBSC_PRO_AV_MODULE_v1.3.bin
    ./gbsc_pro_flash.py --port /dev/ttyACM0 firmware.bin
    ./gbsc_pro_flash.py --list          # list candidate serial ports
    ./gbsc_pro_flash.py --selftest      # verify CRC/packet framing, no hardware

Requires: pyserial (in the repo dev shell: python3 + pyserial are provided).
"""

import argparse
import binascii
import sys
import time

# USB identity the HC32 bootloader enumerates with (VID:PID).
GBSC_VID = 0x2E88
GBSC_PID = 0x4603

BAUD = 115200

# YMODEM / control bytes
SOH = 0x01  # 128-byte packet
EOT = 0x04  # end of transmission
ACK = 0x06
NAK = 0x15
CAN = 0x18
CRC_CHAR = 0x43  # 'C' — receiver ready, CRC mode
PAD = 0x1A       # Ctrl-Z padding for short final block

BLOCK = 128


def crc16_ccitt(data: bytes, crc: int = 0x0000) -> int:
    """CRC-16/CCITT (XMODEM): poly 0x1021, init 0x0000, no reflection, no xorout.

    This is exactly Python's stdlib binascii.crc_hqx (same polynomial and
    conventions), so we defer to it rather than hand-roll the bit loop.
    """
    return binascii.crc_hqx(data, crc)


def build_packet(seq: int, data: bytes) -> bytes:
    """One 133-byte YMODEM-128 packet: SOH, seq, ~seq, 128 data, CRC hi, CRC lo."""
    assert len(data) == BLOCK, f"data must be {BLOCK} bytes, got {len(data)}"
    crc = crc16_ccitt(data)
    return bytes([SOH, seq & 0xFF, (255 - (seq & 0xFF)) & 0xFF]) + data + bytes([crc >> 8, crc & 0xFF])


def block0_data(filename: str) -> bytes:
    """Header block payload: filename only (gb2312), NUL-terminated, zero-padded.

    Mirrors the vendor tool, which — unlike canonical YMODEM — omits the size field.
    """
    name = filename.replace(" ", "_")
    raw = name.encode("gb2312", errors="replace")
    payload = raw[:BLOCK - 1] + b"\x00"
    return payload + b"\x00" * (BLOCK - len(payload))


# --------------------------------------------------------------------------- #
#  Serial helpers                                                             #
# --------------------------------------------------------------------------- #

def find_port():
    """Return the /dev path of the GBSC Pro bootloader, or None."""
    from serial.tools import list_ports
    for p in list_ports.comports():
        if p.vid == GBSC_VID and p.pid == GBSC_PID:
            return p.device
    return None


def list_ports_cmd():
    from serial.tools import list_ports
    any_found = False
    for p in list_ports.comports():
        vid = f"{p.vid:04X}" if p.vid is not None else "----"
        pid = f"{p.pid:04X}" if p.pid is not None else "----"
        match = "  <-- GBSC Pro" if (p.vid == GBSC_VID and p.pid == GBSC_PID) else ""
        print(f"  {p.device}  VID:{vid} PID:{pid}  {p.description}{match}")
        any_found = True
    if not any_found:
        print("  (no serial ports found)")


def _read_existing(ser) -> bytes:
    """Drain and return whatever is currently in the input buffer."""
    n = ser.in_waiting
    return ser.read(n) if n else b""


def _read_byte(ser):
    """Read exactly one byte within the port timeout; return int or None."""
    b = ser.read(1)
    return b[0] if b else None


def _wait_for(ser, target: int, tries: int = 300, sleep: float = 0.03) -> bool:
    """Poll for a specific byte (e.g. 'C'), matching the vendor tool's loop."""
    for _ in range(tries):
        b = _read_byte(ser)
        if b == target:
            return True
        time.sleep(sleep)
    return False


# --------------------------------------------------------------------------- #
#  Handshake + transfer                                                       #
# --------------------------------------------------------------------------- #

def enter_upgrade_mode(ser) -> bool:
    """Drive the HC32 bootloader banner into YMODEM download mode."""
    time.sleep(0.2)
    banner = _read_existing(ser)
    text = banner.decode("latin1", errors="replace")

    if "HCMGBoot." in text:
        ser.write(b"U")
        time.sleep(0.1)
        _read_existing(ser)
        ser.write(b"1")
        time.sleep(0.1)
        resp = _read_existing(ser).decode("latin1", errors="replace")
        if "Enter download" in resp:
            return True
        print(f"[!] Sent U/1 but did not see 'Enter download'. Got: {resp!r}")
        return False

    if "Enter  1" in text:  # note: two spaces, matches vendor tool
        return True

    print("[!] Can not enter upgrade mode. Please check the connection / power-cycle "
          f"the AV module. Banner was: {text!r}")
    return False


def send_firmware(ser, fw: bytes, filename: str, progress=True) -> bool:
    """YMODEM-128 send of the raw firmware image. Returns True on success."""
    total_blocks = (len(fw) + BLOCK - 1) // BLOCK

    # 1. Wait for initial 'C'
    if not _wait_for(ser, CRC_CHAR):
        print("[!] Receiver never sent 'C' — bootloader not ready.")
        return False
    ser.reset_input_buffer()

    # 2/3. Block 0 (header = filename), expect ACK
    ser.write(build_packet(0, block0_data(filename)))
    if _read_byte(ser) != ACK:
        print("[!] Header packet (block 0) not ACKed.")
        return False

    # 4. Receiver requests data with another 'C'
    if _read_byte(ser) != CRC_CHAR:
        print("[!] Did not get 'C' after header packet.")
        return False

    # 5. Data blocks
    seq = 0
    sent = 0
    for off in range(0, len(fw), BLOCK):
        chunk = fw[off:off + BLOCK]
        if len(chunk) < BLOCK:
            chunk = chunk + bytes([PAD]) * (BLOCK - len(chunk))
        seq += 1
        pkt = build_packet(seq, chunk)

        for attempt in range(10):
            ser.write(pkt)
            resp = _read_byte(ser)
            if resp == ACK:
                break
            if resp == NAK:
                continue  # resend
            if resp == CAN:
                print("\n[!] Receiver cancelled transfer (CAN).")
                return False
            print(f"\n[!] Unexpected response {resp!r} to block {seq}.")
            return False
        else:
            print(f"\n[!] Block {seq} failed after retries.")
            return False

        sent += 1
        if progress:
            pct = sent * 100 // total_blocks
            print(f"\r    sending {sent}/{total_blocks} blocks ({pct}%)", end="", flush=True)
    if progress:
        print()

    # 6. EOT — vendor tool accepts ACK or NAK here
    ser.write(bytes([EOT]))
    resp = _read_byte(ser)
    if resp not in (ACK, NAK):
        print(f"[!] EOT not acknowledged (got {resp!r}).")
        return False
    time.sleep(2.0)

    # 7. Closing null header (end of batch)
    if not _wait_for(ser, CRC_CHAR):
        print("[!] No 'C' before closing packet.")
        return False
    ser.write(build_packet(0, b"\x00" * BLOCK))
    if _read_byte(ser) != ACK:
        print("[!] Closing packet not ACKed.")
        return False

    return True


def probe(port: str) -> int:
    """Read-only: print whatever the bootloader emits, sending nothing.

    The HC32 bootloader prints its banner (and any menu/version text) only when
    in bootloader mode. This never writes to the device, so it cannot erase or
    corrupt anything — it's the safe way to see what's currently there.
    """
    import re
    import serial

    ser = serial.Serial()
    ser.port = port
    ser.baudrate = BAUD
    ser.bytesize = serial.EIGHTBITS
    ser.parity = serial.PARITY_NONE
    ser.stopbits = serial.STOPBITS_ONE
    ser.timeout = 0.2
    ser.dtr = True
    ser.rts = True
    ser.open()
    try:
        print(f"[*] Listening on {port} @ {BAUD} for ~3s (sending nothing)...")
        buf = bytearray()
        t0 = time.time()
        while time.time() - t0 < 3.0:
            n = ser.in_waiting
            if n:
                buf += ser.read(n)
            else:
                time.sleep(0.05)
        if not buf:
            print("[!] No output received. The AV module is almost certainly NOT in "
                  "bootloader mode (the HC32 only emits its banner from the bootloader). "
                  "Power-cycle/reset it with USB connected, then re-run --probe promptly.")
            return 1
        text = buf.decode("latin1", errors="replace")
        print("=== bootloader output (verbatim) ===")
        print(text)
        print("=== hex ===")
        print(buf.hex(" "))
        hits = sorted(set(re.findall(r"[Vv]?\d+\.\d+[\w.-]*", text)))
        if hits:
            print("[i] possible version token(s):", ", ".join(hits))
        else:
            print("[i] no version-like string in the banner — this bootloader may not "
                  "report one (the current firmware version is then unknowable in software).")
        return 0
    finally:
        ser.close()


def flash(port: str, path: str) -> int:
    import os
    import serial

    fw = open(path, "rb").read()
    if not fw:
        print("[!] Firmware file is empty.")
        return 2
    filename = os.path.basename(path)
    print(f"[*] Firmware: {filename} ({len(fw)} bytes, "
          f"{(len(fw)+BLOCK-1)//BLOCK} blocks)")
    print(f"[*] Port:     {port} @ {BAUD} 8N1")

    ser = serial.Serial()
    ser.port = port
    ser.baudrate = BAUD
    ser.bytesize = serial.EIGHTBITS
    ser.parity = serial.PARITY_NONE
    ser.stopbits = serial.STOPBITS_ONE
    ser.timeout = 1.0
    ser.dtr = True
    ser.rts = True
    ser.open()
    try:
        print("[*] Entering upgrade mode...")
        if not enter_upgrade_mode(ser):
            return 1
        print("[*] In download mode. Sending firmware...")
        t0 = time.time()
        if not send_firmware(ser, fw, filename):
            return 1
        print(f"[+] Update success! Time-consuming: {time.time()-t0:.1f} seconds")
        return 0
    finally:
        ser.close()


# --------------------------------------------------------------------------- #
#  Self-test (no hardware)                                                    #
# --------------------------------------------------------------------------- #

def selftest() -> int:
    ok = True

    # Known CRC-16/XMODEM check value.
    v = crc16_ccitt(b"123456789")
    exp = 0x31C3
    print(f"CRC('123456789') = 0x{v:04X} (expect 0x{exp:04X}) "
          f"{'OK' if v == exp else 'FAIL'}")
    ok &= (v == exp)

    # Packet framing: length, header bytes, CRC placement.
    pkt = build_packet(1, bytes(BLOCK))
    frame_ok = (len(pkt) == 133 and pkt[0] == SOH and pkt[1] == 1 and pkt[2] == 254)
    crc_zero = crc16_ccitt(bytes(BLOCK))
    crc_ok = (pkt[-2] == (crc_zero >> 8) and pkt[-1] == (crc_zero & 0xFF))
    print(f"packet len=133 & header  {'OK' if frame_ok else 'FAIL'}")
    print(f"packet CRC placement     {'OK' if crc_ok else 'FAIL'}")
    ok &= frame_ok and crc_ok

    # Sequence complement wraps correctly at 255.
    p255 = build_packet(255, bytes(BLOCK))
    seq_ok = (p255[1] == 255 and p255[2] == 0)
    print(f"seq/~seq wrap at 255     {'OK' if seq_ok else 'FAIL'}")
    ok &= seq_ok

    # Block 0 carries filename, NUL-terminated, no size field, 128 bytes.
    b0 = block0_data("GBSC_PRO_AV_MODULE_v1.3.bin")
    b0_ok = (len(b0) == BLOCK and b0.startswith(b"GBSC_PRO_AV_MODULE_v1.3.bin\x00")
             and b0[27] == 0)
    print(f"block0 filename layout   {'OK' if b0_ok else 'FAIL'}")
    ok &= b0_ok

    print("\nSELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Flash the RetroScaler GBSC Pro AV module (HC32) over YMODEM.")
    ap.add_argument("firmware", nargs="?", help="AV-module .bin (e.g. GBSC_PRO_AV_MODULE_v1.3.bin)")
    ap.add_argument("--port", help="serial device (default: auto-detect by USB VID:PID 2E88:4603)")
    ap.add_argument("--list", action="store_true", help="list serial ports and exit")
    ap.add_argument("--probe", action="store_true",
                    help="read-only: print the bootloader banner (sends nothing); "
                         "the only way to glimpse the installed version")
    ap.add_argument("--selftest", action="store_true", help="verify CRC/framing without hardware")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if args.list:
        list_ports_cmd()
        return 0

    if args.probe:
        port = args.port or find_port()
        if not port:
            print("[!] GBSC Pro bootloader not found (USB 2E88:4603). "
                  "Connect the AV module in bootloader mode, or pass --port.")
            return 1
        return probe(port)

    if not args.firmware:
        ap.error("firmware .bin path is required (or use --list / --probe / --selftest)")

    port = args.port or find_port()
    if not port:
        print("[!] GBSC Pro bootloader not found (USB 2E88:4603). "
              "Is the AV module connected and in bootloader mode? "
              "Try --list, or pass --port explicitly.")
        return 1
    return flash(port, args.firmware)


if __name__ == "__main__":
    sys.exit(main())
