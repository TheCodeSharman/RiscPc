#!/usr/bin/env python3
"""Drive ModeServ mode changes until it stops answering, and say what died.

    python3 modeserv_soak.py --host 192.168.88.10 --settle 15

Two hangs on 2026-08-22 both happened with ModeServ running and being driven,
and a night idle in its accept loop survived -- so the mode changes are what is
under suspicion, not the listener. This is the unattended version of that: it
cycles modes, logs every command with a timestamp, and stops on the first
failure with enough state to say which half went.

ICMP is answered by the Internet module without ModeServ's involvement, so the
classification at the end is real: the machine still pinging means ModeServ died
under it, and no ping means the machine went down with it.

Nothing here touches the scaler. The picture will move throughout; that is the
point, and nobody needs to watch it.
"""
import argparse
import socket
import subprocess
import sys
import time

DEFAULT_MODES = [
    "MODE X320 Y256 C256 F50",
    "MODE X640 Y480 C256 F60",
    "MODE X640 Y480 C256 F73",
    "MODE X640 Y480 C256 F75",
]

parser = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--host", default="192.168.88.10")
parser.add_argument("--port", type=int, default=6502)
parser.add_argument("--settle", type=float, default=15.0,
                    help="seconds between mode changes")
parser.add_argument("--log", default="modeserv-soak.log")
parser.add_argument("modes", nargs="*", default=DEFAULT_MODES)
args = parser.parse_args()


def stamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def machine_answers_icmp():
    return subprocess.run(["ping", "-c", "3", "-W", "2", args.host],
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0


def say(line, log):
    print(line, flush=True)
    log.write(line + "\n")
    log.flush()


def send(mode):
    s = socket.create_connection((args.host, args.port), 10)
    try:
        s.sendall((mode + "\n").encode())
        # ModeServ closes to end the reply, so read until it does.
        chunks = []
        while True:
            chunk = s.recv(200)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks).decode(errors="replace").strip()
    finally:
        s.close()


started = time.time()
with open(args.log, "a") as log:
    say(f"=== {stamp()}  soak started, {len(args.modes)} modes, "
        f"{args.settle}s settle ===", log)

    iteration = 0
    while True:
        for mode in args.modes:
            iteration += 1
            elapsed = time.time() - started
            try:
                reply = send(mode)
            except Exception as error:
                say(f"{stamp()}  FAILED after {iteration} changes, "
                    f"{elapsed / 60:.1f} min: {error!r}", log)
                alive = machine_answers_icmp()
                say(f"{stamp()}  machine answers ICMP: {alive}", log)
                say(f"{stamp()}  -> {'ModeServ died, machine alive' if alive else 'the MACHINE went down'}",
                    log)
                sys.exit(1)

            say(f"{stamp()}  {iteration:5d}  {elapsed / 60:7.1f} min  "
                f"{mode:26s} -> {reply}", log)
            time.sleep(args.settle)
