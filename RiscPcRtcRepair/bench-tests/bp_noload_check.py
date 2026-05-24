#!/usr/bin/env python3
"""Bus Pirate no-load rail check.

With NOTHING connected to the probes, enable the supplies and read the pin
voltages to tell a damaged on-board 3V3 regulator apart from a harness short.
Leaves the Bus Pirate powered off in HiZ.
"""
import serial
import sys
import time

PORT = "/dev/ttyUSB0"
BAUD = 115200


def send(ser, cmd, delay=0.4, label=None):
    print(f"\n>>> {label or cmd!r}")
    ser.reset_input_buffer()
    ser.write(cmd.encode() + b"\r")
    ser.flush()
    time.sleep(delay)
    out = b""
    while ser.in_waiting:
        out += ser.read(ser.in_waiting)
        time.sleep(0.05)
    text = out.decode(errors="replace")
    print(text, end="" if text.endswith("\n") else "\n")
    return text


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.3)
    time.sleep(0.2)
    for _ in range(3):
        ser.write(b"\r")
        time.sleep(0.05)
    time.sleep(0.2)
    ser.reset_input_buffer()

    send(ser, "#", delay=0.5, label="reset to HiZ")

    # Enter I2C mode so the rails behave the same as the previous test.
    print("\n>>> mode menu -> I2C (3) -> 100kHz (3)")
    for c in ("m", "3", "3"):
        ser.write(c.encode() + b"\r")
        time.sleep(0.4)
        while ser.in_waiting:
            sys.stdout.write(ser.read(ser.in_waiting).decode(errors="replace"))
            time.sleep(0.05)

    send(ser, "W", delay=0.5, label="power supplies ON (no load)")
    time.sleep(0.3)
    send(ser, "v", delay=0.5, label="pin/voltage state #1")
    send(ser, "v", delay=0.5, label="pin/voltage state #2 (confirm)")

    send(ser, "w", delay=0.3, label="power supplies OFF")
    send(ser, "#", delay=0.4, label="reset to HiZ")
    ser.close()


if __name__ == "__main__":
    main()
