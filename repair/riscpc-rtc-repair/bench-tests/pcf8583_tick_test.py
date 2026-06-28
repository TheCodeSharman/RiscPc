#!/usr/bin/env python3
"""Bus Pirate "tick test" for the PCF8583T.

Reading the time registers proves the I2C/digital side works, but NOT that the
32.768 kHz crystal oscillator is actually running. This test reads the time
twice within a single power session, a few seconds apart, and checks that the
count advanced by roughly the elapsed wall-clock time.

    PASS  -> oscillator is running; RTC is fully functional.
    FAIL  -> count didn't advance (or barely); oscillator/crystal suspect.

PCF8583 time registers (BCD):
    0x00 control/status   0x01 1/100 s   0x02 seconds   0x03 minutes   0x04 hours

Setup and wiring: see pcf8583_i2c_test.py header. Run this chip at 5V.
"""
import re
import sys
import time

import serial

PORT = "/dev/ttyUSB0"
BAUD = 115200

I2C_WRITE_ADDR = 0xA0           # 7-bit 0x50 << 1 | W
I2C_READ_ADDR = 0xA1            # 7-bit 0x50 << 1 | R

WAIT_SECONDS = 4.0             # gap between the two time reads

READ_RE = re.compile(r"READ:\s*((?:0x[0-9A-Fa-f]{2}\s*(?:ACK|NACK)?\s*)+)")
BYTE_RE = re.compile(r"0x([0-9A-Fa-f]{2})")


def drain(ser, settle=0.15):
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
    for _ in range(3):
        ser.write(b"\r"); time.sleep(0.05)
    drain(ser, 0.2)
    cmd(ser, "#", settle=0.6)               # reset to HiZ
    ser.write(b"m\r"); drain(ser, 0.3)
    ser.write(b"3\r"); drain(ser, 0.3)      # I2C
    ser.write(b"3\r"); drain(ser, 0.3)      # 100 kHz
    cmd(ser, "W", settle=0.4)               # power on
    cmd(ser, "P", settle=0.4)               # pull-ups on
    cmd(ser, "v", settle=0.4)               # pinstates sanity


def teardown(ser):
    cmd(ser, "w", settle=0.3)
    cmd(ser, "p", settle=0.3)
    cmd(ser, "#", settle=0.4)


def read_block(ser, addr, n):
    line = f"[0x{I2C_WRITE_ADDR:02X} 0x{addr:02X}][0x{I2C_READ_ADDR:02X} r:{n}]"
    out = cmd(ser, line, settle=0.4, quiet=True)
    m = READ_RE.search(out)
    if not m:
        raise RuntimeError(f"no READ block for addr 0x{addr:02X}:\n{out}")
    found = [int(b, 16) for b in BYTE_RE.findall(m.group(1))]
    if len(found) != n:
        raise RuntimeError(f"expected {n} bytes from 0x{addr:02X}, got {len(found)}:\n{out}")
    return found


def bcd(b):
    return (b >> 4) * 10 + (b & 0x0F)


def read_time(ser):
    """Return (control, hundredths, seconds, minutes, hours, t_monotonic)."""
    regs = read_block(ser, 0x00, 5)         # 0x00..0x04
    t = time.monotonic()
    ctrl, h100, sec, mins, hrs = regs
    return ctrl, bcd(h100), bcd(sec), bcd(mins), bcd(hrs & 0x3F), t


def clock_seconds(h100, sec, mins, hrs):
    """Fractional seconds-within-12h, for delta math (handles minute rollover)."""
    return ((hrs * 60 + mins) * 60 + sec) + h100 / 100.0


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.3)
    time.sleep(0.2)
    ser.reset_input_buffer()
    try:
        setup(ser)

        ctrl1, h1, s1, m1, hr1, t1 = read_time(ser)
        # NB: the PCF8583 datasheet Fig.3 draws the control/status bits in the
        # reverse order to its own body text. The body text (and the Linux
        # rtc-pcf8583 driver) are authoritative, LSB-based:
        #   bit0 timer/seconds flag, bit1 alarm flag, bit2 alarm enable,
        #   bit3 mask, bits5:4 function mode, bit6 hold (0x40), bit7 stop (0x80).
        stopped = bool(ctrl1 & 0x80)
        hold = bool(ctrl1 & 0x40)
        mode = (ctrl1 >> 4) & 0x03
        mode_name = {0: "clock 32.768kHz", 1: "clock 50Hz",
                     2: "event counter", 3: "test"}[mode]
        print(f"\nControl/status 0x{ctrl1:02X}: mode={mode_name}, "
              f"stop={stopped}, hold={hold}")
        print(f"Read #1: {hr1:02d}:{m1:02d}:{s1:02d}.{h1:02d}")

        if stopped or hold:
            print("\n*** WARNING: counter is STOPPED/HELD — it will not tick. "
                  "Clearing stop/hold bits would be needed to test. ***")

        print(f"\nWaiting {WAIT_SECONDS:.1f}s ...")
        time.sleep(WAIT_SECONDS)

        ctrl2, h2, s2, m2, hr2, t2 = read_time(ser)
        print(f"Read #2: {hr2:02d}:{m2:02d}:{s2:02d}.{h2:02d}")

        elapsed_wall = t2 - t1
        c1 = clock_seconds(h1, s1, m1, hr1)
        c2 = clock_seconds(h2, s2, m2, hr2)
        delta = c2 - c1
        if delta < 0:                       # 12h rollover guard
            delta += 12 * 3600

        print(f"\nRTC advanced:  {delta:+.2f} s")
        print(f"Wall elapsed:  {elapsed_wall:.2f} s")

        # Allow generous tolerance: I2C/read latency, BCD 1s granularity.
        ok = abs(delta - elapsed_wall) <= 1.5 and delta > 0.5
        print("\n========= RESULT =========")
        if ok:
            print("PASS: oscillator is running — RTC is ticking correctly.")
        elif delta <= 0.5:
            print("FAIL: count did NOT advance — oscillator/crystal not running.")
        else:
            print(f"SUSPECT: advanced {delta:.2f}s vs {elapsed_wall:.2f}s wall — "
                  "off by more than tolerance, re-run to confirm.")
    finally:
        teardown(ser)
        ser.close()


if __name__ == "__main__":
    main()
