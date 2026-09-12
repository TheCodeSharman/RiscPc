#!/usr/bin/env python3
"""Generate the combined Acorn monitor definition.

    ./make_acorn_mdf.py > RetroScaler-Acorn.mdf

One definition spanning every line rate the machine can drive, 15.6 kHz to
63.7 kHz, so the scaler sees the whole range from a single monitor type and a
session can move across it over ModeServ without a bench trip.

**The timings are Acorn's, copied rather than derived.** That is the whole
point: these are the framings the scaler's defaults have to land on untuned, so
a derived approximation of them would be testing the approximation. Contrast
make_test_mdf.py, whose modes are synthetic and exist one per scaler decision.

The table is the union of the thirteen Acorn definitions RISC OS ships,
extracted once from !Boot.Resources.Configure.Monitors.Acorn and embedded here
so the script needs no RISC OS install to run.

Two rules shaped it.

**Pixel rate capped at 110 MHz.** That is the machine's ceiling, and what says
so is the round number topping AKF80 and AKF85 where every other pixel rate in
them is an awkward one -- 100.00 MHz caps the AKF60 group the same way. Four
modes exceed it, all 136 MHz, all in AKF91/92, and they are left out.

**Deduplicated on resolution and integer field rate**, which is what the mode
selector keys on: two modes agreeing on both are one mode as far as MODE and
MODES are concerned, and the second is unreachable. 299 of the 352 modes are
duplicates that way. Where two files disagree about the timings behind one key,
the first in Acorn's numbering wins.

**VTOTALs are NOT distinct here** -- 20 of them across 53 modes -- so a watcher
cannot name the mode on air from the sync counters alone. ModeSweep's list can,
and deliberately; this file cannot and is not for that.
"""

# x_res, y_res, pixel_rate kHz, h_timings, v_timings, sync_pol, source file
MODES = [
    ( 320,  250,   8000, "38,44,48,320,48,14", "3,19,19,250,19,2", 0, "AKF11-40"),   #  15.6 kHz
    ( 320,  256,   8000, "38,44,48,320,48,14", "3,19,16,256,16,2", 0, "AKF11-40"),   #  15.6 kHz
    ( 640,  250,  16000, "76,88,96,640,96,28", "3,19,19,250,19,2", 0, "AKF11-40"),   #  15.6 kHz
    ( 640,  256,  16000, "76,88,96,640,96,28", "3,19,16,256,16,2", 0, "AKF11-40"),   #  15.6 kHz
    ( 768,  288,  16000, "76,120,0,768,0,60", "3,19,0,288,0,2", 0, "AKF11-40"),   #  15.6 kHz
    (1056,  250,  24000, "114,132,96,1056,96,42", "3,19,19,250,19,2", 0, "AKF11-40"),   #  15.6 kHz
    (1056,  256,  24000, "114,132,96,1056,96,42", "3,19,16,256,16,2", 0, "AKF11-40"),   #  15.6 kHz
    ( 640,  200,  16000, "72,146,16,640,16,130", "3,34,0,200,0,25", 0, "AKF50"),   #  15.7 kHz
    ( 896,  352,  24000, "118,38,20,896,20,8", "3,9,0,352,0,0", 2, "AKF50"),   #  21.8 kHz
    ( 640,  352,  16783, "76,20,16,640,16,0", "3,9,0,352,0,0", 2, "AKF50"),   #  21.9 kHz
    ( 640,  512,  24000, "56,92,20,640,20,68", "3,18,0,512,0,1", 0, "AKF50"),   #  26.8 kHz
    ( 240,  352,   8400, "20,16,20,240,8,8", "2,58,0,352,0,37", 2, "AKF91"),   #  26.9 kHz
    ( 480,  352,  18800, "20,46,26,480,26,10", "2,58,0,352,0,37", 2, "AKF70"),   #  30.9 kHz
    ( 240,  352,   9440, "20,16,8,240,8,8", "2,58,0,352,0,37", 2, "AKF50"),   #  31.5 kHz
    ( 320,  250,  12587, "36,14,12,320,12,6", "2,109,0,250,0,88", 2, "AKF60"),   #  31.5 kHz
    ( 320,  256,  12587, "36,14,12,320,12,6", "2,106,0,256,0,85", 2, "AKF60"),   #  31.5 kHz
    ( 320,  480,  12587, "42,14,12,320,12,0", "2,32,0,480,0,11", 3, "AKF50"),   #  31.5 kHz
    ( 384,  288,  18881, "68,16,66,384,66,0", "2,58,32,288,32,37", 2, "AKF50"),   #  31.5 kHz
    ( 480,  352,  18881, "68,16,18,480,18,0", "2,58,0,352,0,37", 2, "AKF50"),   #  31.5 kHz
    ( 640,  200,  25175, "88,22,22,640,22,6", "2,134,0,200,0,113", 2, "AKF60"),   #  31.5 kHz
    ( 640,  250,  25175, "88,22,22,640,22,6", "2,109,0,250,0,88", 2, "AKF60"),   #  31.5 kHz
    ( 640,  256,  25175, "88,22,22,640,22,6", "2,106,0,256,0,85", 2, "AKF60"),   #  31.5 kHz
    ( 640,  352,  25175, "88,22,22,640,22,6", "2,58,0,352,0,37", 2, "AKF60"),   #  31.5 kHz
    ( 640,  480,  25175, "94,22,22,640,22,0", "2,32,0,480,0,11", 3, "AKF50"),   #  31.5 kHz
    (1280,  480,  50350, "188,44,44,1280,44,0", "2,32,0,480,0,11", 3, "AKF50"),   #  31.5 kHz
    ( 360,  480,  16783, "64,46,16,360,16,30", "2,32,0,480,0,11", 3, "AKF50"),   #  31.5 kHz
    (1280,  480,  50350, "188,44,24,1280,24,20", "2,32,0,480,0,11", 3, "AKF91"),   #  31.9 kHz
    ( 320,  512,  13350, "36,14,12,320,12,6", "2,32,20,512,20,11", 3, "AKF91"),   #  33.4 kHz
    ( 800,  600,  36000, "72,84,34,800,34,0", "2,22,0,600,0,1", 0, "AKF50"),   #  35.2 kHz
    (1600,  600,  72000, "144,168,68,1600,68,0", "2,22,0,600,0,1", 0, "AKF50"),   #  35.2 kHz
    ( 320,  480,  16200, "24,40,16,320,16,32", "3,28,0,480,0,9", 3, "AKF91"),   #  36.2 kHz
    ( 640,  512,  32000, "64,76,30,640,30,30", "3,16,40,512,40,4", 3, "AKF91"),   #  36.8 kHz
    ( 360,  480,  17400, "50,40,6,360,6,10", "2,32,0,480,0,11", 0, "AKF70"),   #  36.9 kHz
    (1280,  480,  64000, "96,172,32,1280,32,100", "3,28,10,480,10,9", 3, "AKF91"),   #  37.4 kHz
    ( 320,  480,  15750, "24,44,16,320,16,0", "3,16,0,480,0,1", 3, "AKF50"),   #  37.5 kHz
    ( 640,  480,  30000, "94,22,22,640,22,0", "2,32,0,480,0,11", 3, "AKF91"),   #  37.5 kHz
    ( 640,  480,  31500, "64,76,30,640,30,0", "3,16,0,480,0,1", 3, "AKF50"),   #  37.5 kHz
    (1280,  480,  63000, "128,156,58,1280,58,0", "3,16,0,480,0,1", 3, "AKF50"),   #  37.5 kHz
    ( 320,  480,  15750, "24,40,16,320,16,0", "3,28,0,480,0,9", 3, "AKF50"),   #  37.9 kHz
    ( 640,  480,  31500, "48,84,30,640,30,0", "3,28,0,480,0,9", 3, "AKF50"),   #  37.9 kHz
    (1280,  480,  63000, "96,172,58,1280,58,0", "3,28,0,480,0,9", 3, "AKF50"),   #  37.9 kHz
    ( 800,  600,  40000, "128,48,40,800,40,0", "4,23,0,600,0,1", 0, "AKF50"),   #  37.9 kHz
    (1600,  600,  80000, "256,98,78,1600,78,2", "4,23,0,600,0,1", 0, "AKF50"),   #  37.9 kHz
    ( 640,  512,  37500, "64,76,30,640,30,30", "3,16,40,512,40,4", 3, "AKF91"),   #  43.1 kHz
    ( 800,  600,  49500, "80,46,42,800,42,46", "3,21,0,600,0,1", 0, "AKF60"),   #  46.9 kHz
    (1600,  600,  99000, "160,92,84,1600,84,92", "3,21,0,600,0,1", 0, "AKF60"),   #  46.9 kHz
    ( 800,  600,  50000, "88,34,42,800,42,34", "6,23,0,600,0,37", 0, "AKF60"),   #  48.1 kHz
    (1600,  600, 100000, "176,68,84,1600,84,68", "6,23,0,600,0,37", 0, "AKF60"),   #  48.1 kHz
    (1024,  768,  65000, "128,36,60,1024,60,36", "6,29,0,768,0,3", 0, "AKF60"),   #  48.4 kHz
    (1024,  768,  75000, "124,36,72,1024,72,0", "6,29,0,768,0,3", 0, "AKF80"),   #  56.5 kHz
    (1024,  768,  80310, "122,86,30,1024,76,0", "3,28,0,768,0,1", 0, "AKF80"),   #  60.0 kHz
    (1280, 1024, 110000, "166,90,140,1280,30,30", "3,32,50,1024,50,4", 0, "AKF91"),   #  63.4 kHz
    (1280, 1024, 110000, "166,90,96,1280,96,0", "3,32,0,1024,0,3", 0, "AKF80"),   #  63.7 kHz
]


def totals(timings):
    return sum(int(n) for n in timings.split(","))


def check_distinct(modes):
    """A mode the selector cannot name is a mode that cannot be tested."""
    seen = {}
    for x, y, px, h, v, pol, src in modes:
        key = (x, y, round(px * 1000 / (totals(h) * totals(v))))
        if key in seen:
            raise SystemExit(
                "unreachable mode: X%d Y%d F%d appears in %s and %s"
                % (key[0], key[1], key[2], seen[key], src))
        seen[key] = src


check_distinct(MODES)

print("file_format:1")
print("monitor_title:RetroScaler Acorn")
print("DPMS_state:0")
print()
print("# Generated by make_acorn_mdf.py -- edit that, not this.")
print("#")
print("# Acorn's own timings, every line rate the machine drives in one file.")
print("# Sync TYPE is not a mode file field: use ModeServ's SYNC command.")
print()
for x, y, px, h, v, pol, src in MODES:
    line = px * 1000 / totals(h)
    print("# %s -- %.1f kHz line, %.2f Hz field, %d lines"
          % (src, line / 1000, line / totals(v), totals(v)))
    print("startmode")
    print("mode_name:")
    print("x_res:%d" % x)
    print("y_res:%d" % y)
    print("pixel_rate:%d" % px)
    print("h_timings:%s" % h)
    print("v_timings:%s" % v)
    print("sync_pol:%d" % pol)
    print("endmode")
    print()
