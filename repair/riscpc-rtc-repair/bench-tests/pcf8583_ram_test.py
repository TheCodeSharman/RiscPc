#!/usr/bin/env python3
"""Bus Pirate test of the PCF8583T's 240-byte general-purpose RAM.

The PCF8583 register map:
    0x00-0x0F : control / time / date / alarm
    0x10-0xFF : 240 bytes general-purpose RAM (used by RISC PC for CMOS settings)

Test sequence:
    1. Save the original contents of 0x10-0xFF.
    2. Write incrementing pattern (byte at addr N = N).
    3. Read back, verify.
    4. Write complement pattern (byte at addr N = ~N).
    5. Read back, verify.
    6. Restore originals, verify.

Setup and wiring: see pcf8583_i2c_test.py header.
"""
import re
import serial
import sys
import time

PORT = "/dev/ttyUSB0"
BAUD = 115200

RAM_START = 0x10
RAM_END = 0xFF                  # inclusive
RAM_LEN = RAM_END - RAM_START + 1   # 240
CHUNK = 16                       # bytes per I2C transaction

I2C_WRITE_ADDR = 0xA0            # 7-bit 0x50 << 1 | W
I2C_READ_ADDR = 0xA1             # 7-bit 0x50 << 1 | R

READ_RE = re.compile(r"READ:\s*((?:0x[0-9A-Fa-f]{2}\s*(?:ACK|NACK)?\s*)+)")
BYTE_RE = re.compile(r"0x([0-9A-Fa-f]{2})")

def drain(ser, settle=0.15):
    """Read everything available, with a small settle in case more is incoming."""
    time.sleep(settle)
    buf = b""
    while ser.in_waiting:
        buf += ser.read(ser.in_waiting)
        time.sleep(0.03)
    return buf.decode(errors="replace")

def cmd(ser, line, settle=0.25, quiet=False):
    ser.reset_input_buffer()
    ser.write(line.encode() + b"\r")
    ser.flush()
    out = drain(ser, settle=settle)
    if not quiet:
        sys.stdout.write(out)
        sys.stdout.flush()
    return out

def setup(ser):
    # Wake / sync.
    for _ in range(3):
        ser.write(b"\r"); time.sleep(0.05)
    drain(ser, 0.2)

    cmd(ser, "#", settle=0.6)                # reset to HiZ
    # mode menu
    ser.write(b"m\r"); drain(ser, 0.3)
    ser.write(b"3\r"); drain(ser, 0.3)       # I2C
    ser.write(b"3\r"); drain(ser, 0.3)       # 100 kHz
    cmd(ser, "W", settle=0.4)                # power on
    cmd(ser, "P", settle=0.4)                # pull-ups on
    cmd(ser, "v", settle=0.4)                # pinstates sanity

def teardown(ser):
    cmd(ser, "w", settle=0.3)
    cmd(ser, "p", settle=0.3)
    cmd(ser, "#", settle=0.4)

def read_block(ser, addr, n):
    """Read n bytes starting at PCF8583 register addr."""
    line = f"[0x{I2C_WRITE_ADDR:02X} 0x{addr:02X}][0x{I2C_READ_ADDR:02X} r:{n}]"
    out = cmd(ser, line, settle=0.4, quiet=True)
    # extract READ bytes
    m = READ_RE.search(out)
    if not m:
        raise RuntimeError(f"no READ block in response for addr 0x{addr:02X}:\n{out}")
    bytes_found = [int(b, 16) for b in BYTE_RE.findall(m.group(1))]
    if len(bytes_found) != n:
        raise RuntimeError(
            f"expected {n} bytes from 0x{addr:02X}, got {len(bytes_found)}:\n{out}"
        )
    return bytes_found

def write_block(ser, addr, data):
    """Write data (list/bytes) starting at PCF8583 register addr."""
    payload = " ".join(f"0x{b:02X}" for b in data)
    line = f"[0x{I2C_WRITE_ADDR:02X} 0x{addr:02X} {payload}]"
    out = cmd(ser, line, settle=0.4, quiet=True)
    # crude verify: count ACKs — should be 1 (addr byte) + 1 (reg ptr) + len(data)
    acks = out.count("ACK")
    naks = out.count("NACK")
    expected = 2 + len(data)
    if acks < expected or naks > 0:
        raise RuntimeError(
            f"write to 0x{addr:02X} len {len(data)} bad ACK count "
            f"(acks={acks}, naks={naks}, expected>={expected}):\n{out}"
        )

def read_all_ram(ser, label):
    print(f"\n--- reading RAM ({label}) ---")
    data = []
    for off in range(0, RAM_LEN, CHUNK):
        addr = RAM_START + off
        n = min(CHUNK, RAM_LEN - off)
        data.extend(read_block(ser, addr, n))
        sys.stdout.write("."); sys.stdout.flush()
    print()
    return data

def write_all_ram(ser, data, label):
    print(f"\n--- writing RAM ({label}) ---")
    assert len(data) == RAM_LEN
    for off in range(0, RAM_LEN, CHUNK):
        addr = RAM_START + off
        n = min(CHUNK, RAM_LEN - off)
        write_block(ser, addr, data[off:off + n])
        sys.stdout.write("."); sys.stdout.flush()
    print()

def hexdump(data, base=RAM_START, prefix=""):
    for off in range(0, len(data), 16):
        row = data[off:off+16]
        hexs = " ".join(f"{b:02X}" for b in row)
        ascii_ = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        print(f"{prefix}0x{base+off:02X}: {hexs:<47} |{ascii_}|")

def diff_report(expected, actual, label):
    mismatches = [(i, e, a) for i, (e, a) in enumerate(zip(expected, actual)) if e != a]
    if not mismatches:
        print(f"PASS: {label} — all {len(expected)} bytes match")
        return True
    print(f"FAIL: {label} — {len(mismatches)} mismatch(es):")
    for i, e, a in mismatches[:16]:
        print(f"  reg 0x{RAM_START+i:02X}: expected 0x{e:02X}  got 0x{a:02X}")
    if len(mismatches) > 16:
        print(f"  ... and {len(mismatches) - 16} more")
    return False

def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.3)
    time.sleep(0.2)
    ser.reset_input_buffer()
    try:
        setup(ser)

        # 1. Save originals.
        original = read_all_ram(ser, "original contents")
        print("Original RAM dump (0x10-0xFF):")
        hexdump(original)

        results = []

        # 2/3. Address-as-data pattern.
        pattern1 = [(RAM_START + i) & 0xFF for i in range(RAM_LEN)]
        write_all_ram(ser, pattern1, "address-as-data pattern")
        readback1 = read_all_ram(ser, "address-as-data readback")
        results.append(diff_report(pattern1, readback1, "address-as-data pattern"))

        # 4/5. Complement pattern.
        pattern2 = [(~p) & 0xFF for p in pattern1]
        write_all_ram(ser, pattern2, "inverted-address pattern")
        readback2 = read_all_ram(ser, "inverted-address readback")
        results.append(diff_report(pattern2, readback2, "inverted-address pattern"))

        # 6. Restore originals + verify.
        write_all_ram(ser, original, "restoring originals")
        restored = read_all_ram(ser, "post-restore readback")
        results.append(diff_report(original, restored, "restore-original"))

        print("\n========= SUMMARY =========")
        print(f"address-as-data:       {'PASS' if results[0] else 'FAIL'}")
        print(f"inverted-address:      {'PASS' if results[1] else 'FAIL'}")
        print(f"restore-original:      {'PASS' if results[2] else 'FAIL'}")
        print(f"overall:               {'PASS' if all(results) else 'FAIL'}")
    finally:
        teardown(ser)
        ser.close()

if __name__ == "__main__":
    main()
