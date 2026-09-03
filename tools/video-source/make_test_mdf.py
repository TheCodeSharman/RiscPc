#!/usr/bin/env python3
"""Generate the scaler test monitor definition.

    ./make_test_mdf.py > RetroScaler-Test.mdf

Every mode here exists to exercise one decision in the scaler being
characterised, and the timings are derived rather than typed: give a target
field rate and the horizontal and vertical totals, and the pixel rate follows.

    line rate  = pixel_rate / h_total
    field rate = line rate  / v_total

h_timings and v_timings are, in order, sync / back porch / left border /
display / right border / front porch -- checked against every mode of the
stock definition, which this reproduces exactly.

**Sync TYPE is not here.** A monitor definition carries sync POLARITY per mode
and nothing else; composite versus separate is one CMOS value for the machine
(*Configure Sync, OS_ReadSysInfo 1), which ModeServ's SYNC command sets.
"""

BASE = [
    # A 15 kHz line at three field rates on ONE line count. The scaler compares
    # the line count to decide a source moved, so a source returning at the same
    # count and a different rate is the case it cannot see. Three points, because
    # two cannot disconfirm a line.
    (320, 256, 512, 312, 50.08, 0, "same 312 lines, 50 Hz"),
    (320, 256, 512, 312, 55.00, 0, "same 312 lines, 55 Hz"),
    (320, 256, 512, 312, 60.00, 0, "same 312 lines, 60 Hz"),

    # All four sync polarities at ONE timing. Only x_res differs, and the border
    # absorbs it, so the line total, the line count and the field rate are
    # identical across the four -- the polarity is the only variable.
    (328, 256, 512, 312, 50.08, 1, "polarity 1, -H +V"),
    (336, 256, 512, 312, 50.08, 2, "polarity 2, +H -V"),
    (344, 256, 512, 312, 50.08, 3, "polarity 3, -H -V"),

    # Either side of the 400-line doubling threshold, close enough that nothing
    # else about the source has changed.  x_res differs only to keep the two
    # selectable apart; the border absorbs it.
    (640, 352, 768, 396, 60.00, 0, "396 lines, doubler on"),
    (648, 352, 768, 404, 60.00, 0, "404 lines, doubler off"),

    # Either side of the 280 and 380 line buckets the scaling-RGBHV arm sorts on.
    # x_res again differs only to keep the 50 Hz pair selectable apart.
    (640, 200, 1020, 262, 60.00, 0, "262 lines, below the 280 bucket"),
    (640, 288, 1024, 340, 50.00, 0, "340 lines, between the buckets"),
    (648, 288, 1024, 420, 50.00, 0, "420 lines, above the 380 bucket"),

    # Either side of 20 kHz, which is where the scaler stops calling a source
    # low line rate, at one line count so only the rate moves.
    (640, 256, 1024, 312, 55.00, 0, "312 lines, 17.2 kHz"),
    (640, 256, 1024, 312, 70.00, 0, "312 lines, 21.8 kHz"),

    # Either side of 650 lines, where the progressive post divider drops an
    # octave.  x_res differs only to keep the pair selectable apart.
    (800, 600, 1056, 628, 60.00, 0, "628 lines, ordinary divider"),
    (808, 600, 1056, 680, 60.00, 0, "680 lines, tall divider"),
]


def achieved(x, y, htotal, vtotal, field, pol, why):
    """The mode as the selector sees it: XOS_ScreenMode 2 reports an integer rate."""
    pixel_khz = round(field * vtotal * htotal / 1000)
    return (x, y, round(pixel_khz * 1000 / (htotal * vtotal)))


def check_distinct(specs):
    """A mode the selector cannot name is a mode that cannot be tested.

    Modes are chosen by resolution, depth and integer field rate, so two modes
    agreeing on all three are one mode as far as MODE and MODES are concerned --
    the first wins and the second is unreachable.  Vary x_res and let the border
    absorb it: the line total, the line count and the field rate stay put.
    """
    seen = {}
    clashes = []
    for spec in specs:
        key = achieved(*spec)
        if key in seen:
            clashes.append((key, seen[key], spec[-1]))
        seen[key] = spec[-1]
    if clashes:
        lines = [
            f"  X{k[0]} Y{k[1]} F{k[2]}: {a!r} and {b!r}" for k, a, b in clashes
        ]
        raise SystemExit(
            "unreachable modes -- these share resolution and field rate:\n"
            + "\n".join(lines)
        )


def timings(total, display, sync, back, front):
    border = (total - display - sync - back - front) // 2
    spare = total - display - sync - back - front - 2 * border
    return [sync, back + spare, border, display, border, front]


def mode(x, y, htotal, vtotal, field, pol, why):
    pixel_khz = round(field * vtotal * htotal / 1000)
    h = timings(htotal, x, 36, 30, 38)
    v = timings(vtotal, y, 3, 16, 3)
    line = pixel_khz * 1000 / htotal
    return (
        f"# {why} -- {line/1000:.3f} kHz line, {line/vtotal:.2f} Hz field, "
        f"h total {htotal}, v total {vtotal}\n"
        "startmode\n"
        "mode_name:\n"
        f"x_res:{x}\n"
        f"y_res:{y}\n"
        f"pixel_rate:{pixel_khz}\n"
        f"h_timings:{','.join(str(n) for n in h)}\n"
        f"v_timings:{','.join(str(n) for n in v)}\n"
        f"sync_pol:{pol}\n"
        "endmode\n"
    )


check_distinct(BASE)

print("file_format:1")
print("monitor_title:RetroScaler Test")
print("DPMS_state:0")
print()
print("# Generated by make_test_mdf.py -- edit that, not this.")
print("#")
print("# Each mode exercises one scaler decision. Sync TYPE is not a mode file")
print("# field: use ModeServ's SYNC command (*Configure Sync).")
print()
for spec in BASE:
    print(mode(*spec))
