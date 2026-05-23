#!/usr/bin/env python3
"""Bus Pirate I2C test for PCF8583T.

Brings the Bus Pirate into I2C mode @ 100 kHz, enables 3V3 power and pull-ups,
runs the 7-bit address scan, and (if 0x50 / 0x51 ACK) reads the first 8 RTC
registers starting at 0x00.

Setup:
    python3 -m venv .venv && .venv/bin/pip install pyserial
    .venv/bin/python pcf8583_i2c_test.py

Wiring (Bus Pirate v3.5/v3.6 rainbow ribbon -> PCF8583T SO-8):
    pin 4 (VSS) <- Brown  (GND)
    pin 5 (SDA) <- Grey   (MOSI)
    pin 6 (SCL) <- Purple (CLK)
    pin 8 (VDD) <- Red    (3V3)
    Tie Green (Vpu) to Red (3V3) so the on-board pull-ups are powered.

A successful scan ACKs at 7-bit 0x50 (A0 low) - Bus Pirate prints it as
"0xA0(0x50 W) 0xA1(0x50 R)".
"""
import serial
import sys
import time

PORT = "/dev/ttyUSB0"
BAUD = 115200

def send(ser, cmd, delay=0.2, label=None):
    """Send cmd + CR, wait, return what came back."""
    if label:
        print(f"\n>>> {label}: {cmd!r}")
    else:
        print(f"\n>>> {cmd!r}")
    ser.reset_input_buffer()
    ser.write(cmd.encode() + b"\r")
    ser.flush()
    time.sleep(delay)
    out = b""
    while ser.in_waiting:
        out += ser.read(ser.in_waiting)
        time.sleep(0.05)
    text = out.decode(errors="replace")
    print(text, end="")
    if not text.endswith("\n"):
        print()
    return text

def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.3)
    time.sleep(0.2)
    ser.reset_input_buffer()

    # Wake up — a few blank lines flush any half-typed state.
    for _ in range(3):
        ser.write(b"\r")
        time.sleep(0.05)
    time.sleep(0.2)
    ser.reset_input_buffer()

    # Reset to HiZ, then identify firmware.
    send(ser, "#", delay=0.5, label="reset to HiZ")
    send(ser, "i", delay=0.4, label="firmware info")

    # Enter mode menu and pick I2C (option 3 per memory).
    print("\n>>> entering mode menu (m) then '3' for I2C, then '3' for 100kHz")
    ser.write(b"m\r")
    time.sleep(0.4)
    # drain
    while ser.in_waiting:
        sys.stdout.write(ser.read(ser.in_waiting).decode(errors="replace"))
        time.sleep(0.05)
    ser.write(b"3\r")   # I2C
    time.sleep(0.4)
    while ser.in_waiting:
        sys.stdout.write(ser.read(ser.in_waiting).decode(errors="replace"))
        time.sleep(0.05)
    ser.write(b"3\r")   # speed: 100 kHz (option 3 in CFW)
    time.sleep(0.4)
    while ser.in_waiting:
        sys.stdout.write(ser.read(ser.in_waiting).decode(errors="replace"))
        time.sleep(0.05)

    # Enable power and pull-ups.
    send(ser, "W", delay=0.4, label="power supplies ON")
    send(ser, "P", delay=0.4, label="pull-ups ON")
    send(ser, "v", delay=0.4, label="pin/voltage state (sanity check pull-ups + Vpu)")

    # Run 7-bit address search macro.
    scan = send(ser, "(1)", delay=1.0, label="I2C 7-bit address scan")

    # Look for PCF8583 addresses. Bus Pirate prints 7-bit found addresses as
    # "0xA0(0x50 W) 0xA1(0x50 R)" etc. We just grep for 0x50 / 0x51 ACKs.
    pcf_present = ("0x50" in scan) or ("0x51" in scan) or ("0xA0" in scan) or ("0xA2" in scan)

    if pcf_present:
        print("\n*** PCF8583 ACK detected on address scan — reading registers ***")
        # Read 8 bytes starting at register 0 (control/status, then time/date).
        # Bus Pirate 8-bit I2C syntax: 0xA0 = write to 0x50, 0xA1 = read from 0x50.
        send(ser, "[0xA0 0x00][0xA1 r:8]", delay=0.6,
             label="set reg pointer to 0x00, read 8 bytes")
    else:
        print("\n*** No ACK from 0x50 or 0x51 — PCF8583 not responding ***")

    # Park: power off, leave in HiZ.
    send(ser, "w", delay=0.3, label="power supplies OFF")
    send(ser, "p", delay=0.3, label="pull-ups OFF")
    send(ser, "#", delay=0.4, label="reset to HiZ")
    ser.close()

if __name__ == "__main__":
    main()
