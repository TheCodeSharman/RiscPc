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

**Acorn's own modes are capped at 110 MHz here.** The round number topping
AKF80 and AKF85, where every other pixel rate in them is awkward, looks like a
machine limit, and 100.00 MHz caps the AKF60 group the same way -- but a
monitor definition states what the MONITOR accepts, not what VIDC20 can clock,
and AKF91/92 carry 136 MHz modes. So the cap is a convention here and not a
proven ceiling. The four modes above it are left out of the Acorn block only
because nothing needs them.

**What settles it is the machine, and asking costs nothing.** RISC OS will not
offer a mode it cannot generate, and ModeServ's MODE replies with what the
hardware landed in rather than what was asked for -- so the 148.5 MHz entries
below are a question put to the machine. If they appear in MODES they work.

**Deduplicated on resolution and integer field rate**, which is what the mode
selector keys on: two modes agreeing on both are one mode as far as MODE and
MODES are concerned, and the second is unreachable. 299 of the 352 modes are
duplicates that way. Where two files disagree about the timings behind one key,
the first in Acorn's numbering wins.

## What 2 MB of VRAM actually costs

It caps the DEPTH, not the resolution, and across this file the cap never lands
where it hurts:

    1920x1080   1.98 MB at C256   C256 is the ceiling, and it fits by 23 KB
    1280x1024   1.25 MB at C256   C256 ceiling
    1600x600    0.92 MB at C256   C64K still fits
    800x600     0.46 MB at C256   everything fits

**C256 fits every mode here, 1080p included**, and C256 is exactly what the test
card needs: at 16 colours the PM5544 palette comes out wrong, measured. So
nothing in this file is depth-blocked and no monochrome mode is called for. What
2 MB costs is C64K above 1280x720 and C16M above 800x600, which nothing here
wants.

**Bandwidth is the argument against 1080p60, not the clock and not the size.**
VIDC20 fetches pixel_rate x bytes_per_pixel, so at C256:

    1280x1024 @ 110.00 MHz   110 MB/s   an Acorn mode, shipped in AKF80
    1920x1080 @  74.25 MHz    74 MB/s   1080p30, comfortably under it
    1920x1080 @ 148.50 MHz   148 MB/s   1080p60, half as much again

That 110 MB/s figure is the useful one: Acorn shipped a mode needing it, so the
machine does at least that much.

**Three things could refuse 1080p60, and MODES tells them apart.** Depth changes
the size and the bandwidth and leaves the pixel clock alone, so what a mode is
offered AT is the discriminator:

    offered at no depth at all     the motherboard's video PLL cannot reach
                                   148.5 MHz -- depth cannot help a clock
    offered at C16 but not C256    bandwidth, and a lower depth buys it back
    offered at C256                it works, and the doubt was unfounded

Size is already out: 1920x1080 at C256 fits by 23 KB.

**VTOTALs are NOT distinct here** -- 20 of them across 53 modes -- so a watcher
cannot name the mode on air from the sync counters alone. ModeSweep's list can,
and deliberately; this file cannot and is not for that.
Beyond Acorn's own modes it carries a CEA-861 block and one true NTSC line, so
the machine can present timings no Acorn monitor ever asked for. See CEA below.
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


# --- CEA-861, and the one SD line Acorn never drew -------------------------
#
# Acorn's modes are PAL-centric and stop at 63.7 kHz, so nothing in them
# presents a timing a television source would. These do, which is what lets the
# machine stand in for sources the bench has none of.
#
# **THIS IS THE ONLY WAY TO REACH STANDARDS 5, 6 AND 7.** Mode Detect names
# those from the TIMING alone -- STATUS_IF_INP_720, _1080I, _1808P -- and
# getVideoMode() consults neither the connector nor the colour space on the way
# there, so a 720p-timed RGBHV source should classify as 720p. The bench has no
# HD component source and the Wii stops at 480p, so without these the three
# arms are unexercisable. It tests the timing half only: the colour path
# follows the input selection, and this arrives on an RGB one.
#
# Timings are CEA-861's, copied. h_timings and v_timings are
# sync/back/border/display/border/front, and CEA states sync, back and front, so
# the borders are zero except where a total needs padding.
#
# **1080p50 and 1080p60 want 148.5 MHz**, above anything Acorn's own files ask
# for. They are here as a question rather than a claim: if the machine cannot
# clock them they will not appear in MODES, and 1080p24/25/30 carry the same
# 1125-line shape at 74.25 MHz either way.
#
# Bit depth does not help with a clock, but it may with the bandwidth behind
# one: 1920x1080 is 2.07 MB at 8 bpp and 259 KB at 1 bpp, and a definition
# names no depth -- RISC OS offers whichever ones fit. So a mode that is
# refused at 8 bpp and offered at 1 or 2 is a bandwidth answer, not a clock
# one.
#
# **The interlaced modes are absent too.** A monitor definition has no interlace
# key -- it is *TV vert,interlace, which ModeServ's INTERLACE command sets and
# which re-applies the mode -- so 480i, 576i and 1080i are that mechanism's
# rather than this file's, and pairing the two has not been worked out.
#
# 1920x1080 is 2,073,600 bytes at 8 bpp against 2 MB of VRAM. It fits by 23 KB.
CEA = [
    # A true NTSC line. Acorn's SD is 15.625 kHz on 312 lines; this is the
    # 15.734 kHz on 262 that every NTSC console and the composite path produce,
    # and no Acorn definition contains it.
    ( 640,  240,  13500, "62,60,40,640,40,16",   "6,15,0,240,0,1",    3, "NTSC SD"),

    ( 720,  480,  27000, "62,60,0,720,0,16",     "6,30,0,480,0,9",    3, "CEA 2/3 480p"),
    ( 720,  576,  27000, "64,68,0,720,0,12",     "5,39,0,576,0,5",    3, "CEA 17/18 576p"),
    (1280,  720,  74250, "40,220,0,1280,0,110",  "5,20,0,720,0,5",    0, "CEA 4 720p60"),
    (1280,  720,  74250, "40,220,0,1280,0,440",  "5,20,0,720,0,5",    0, "CEA 19 720p50"),
    (1920, 1080,  74250, "44,148,0,1920,0,88",   "5,36,0,1080,0,4",   0, "CEA 34 1080p30"),
    (1920, 1080,  74250, "44,148,0,1920,0,528",  "5,36,0,1080,0,4",   0, "CEA 33 1080p25"),
    (1920, 1080,  74250, "44,148,0,1920,0,638",  "5,36,0,1080,0,4",   0, "CEA 32 1080p24"),

    # Above every rate Acorn's files ask for. See the note above: these are a
    # question for the machine, not a claim about it.
    (1920, 1080, 148500, "44,148,0,1920,0,88",   "5,36,0,1080,0,4",   0, "CEA 16 1080p60"),
    (1920, 1080, 148500, "44,148,0,1920,0,528",  "5,36,0,1080,0,4",   0, "CEA 31 1080p50"),
]

# Per-console modes are deliberately absent. The scaler sees sync edges and not
# pixels, so a source's dot clock and active width are invisible to it -- NES,
# SNES and Mega Drive are one 15.7 kHz, 262-line, 60 Hz source as far as any
# register here is concerned, and three entries producing identical STATUS_
# readings would prove one thing three times. What was missing was the LINE
# RATE, which is the NTSC SD entry above.

MODES = MODES + CEA


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
