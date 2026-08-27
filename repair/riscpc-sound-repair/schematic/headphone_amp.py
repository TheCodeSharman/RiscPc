#!/usr/bin/env python3
"""RISC PC (main PCB drawing 1208,000) — headphone amplifier, reverse-engineered.

No public schematic exists for this board revision; every net below was found by
probing.  The authority for it is ../README.md — this script is a *drawing* of
that map, not an independent source.  If the two disagree, the README wins.

The two channels are electrically identical mirrors, so they are described once,
as data (CHANNELS), and drawn twice by draw_channel().  That is the whole reason
this is a script and not a hand-drawn schematic: the map is still changing, and
a correction must not have to be applied twice.

Anything not actually traced is drawn grey with a "?" rather than invented.
See UNCERTAIN at the foot of the file.

Render:  nix develop --command make -C repair/riscpc-sound-repair/schematic
"""

import schemdraw
from schemdraw import elements as elm

schemdraw.use('svg')

# --- Drawing conventions applied below ---------------------------------------
# Signal flows left -> right.  Supply rails point up (+) and down (-).  Ground
# points down.  Feedback returns right-to-left *over the top* of its amplifier.
# Op-amp in1 (top) is the inverting input, in2 (bottom) non-inverting.

BLUE = '#1a4d7a'      # pin numbers / measured voltages
RED = '#a03030'       # supply rails
GREY = '#777777'      # uncertain / not traced

# --- The circuit, once ------------------------------------------------------
# From README "TL074 #1 (headphone amp) — section -> pin map" and
# "Signal path — RIGHT channel (LEFT is the mirror image)".
CHANNELS = [
    dict(name='RIGHT', y=0.0,
         dac_pin='8', dac_sig='IOR', dac_anchor='ior',
         iv_sec='A', iv_in='2', iv_ref='3', iv_out='1',
         dr_sec='D', dr_in='13', dr_ref='12', dr_out='14',
         q='Q4', tip='R tip'),
    dict(name='LEFT', y=-10.5,
         dac_pin='6', dac_sig='IOL', dac_anchor='iol',
         iv_sec='B', iv_in='6', iv_ref='5', iv_out='7',
         dr_sec='C', dr_in='9', dr_ref='10', dr_out='8',
         q='Q1', tip='L tip'),
]

X_BUS = 3.0      # vertical corridor carrying IOL/IOR out of the DAC
X_IV = 5.6       # I/V converter op-amp (inverting input)
X_DRV = 15.0     # driver op-amp (inverting input)
X_OUT = 26.5     # jack terminals


def draw_channel(d, ch):
    """Draw one channel: I/V converter -> AC coupling -> unity driver -> jack."""
    y = ch['y']

    # ---- I/V converter: DAC output current -> voltage ------------------
    iv = elm.Opamp(leads=True).right().at((X_IV, y)).anchor('in1')
    iv.label(f"TL074#1\n{ch['iv_sec']}", loc='center', ofst=(0.6, 0), halign='center',
             fontsize=10)
    iv.label(ch['iv_in'], loc='in1', color=BLUE)
    iv.label(ch['iv_ref'], loc='in2', color=BLUE)
    iv.label(ch['iv_out'], loc='out', color=BLUE, ofst=(0.06, 0.24))
    d += iv

    d += elm.Line().at(iv.in1).left().tox(X_BUS).label(
        ch['dac_sig'], loc='top', fontsize=9, ofst=(0, 0.05))
    iv_in_node = d.here

    d += elm.Line().at(iv.out).right(0.7)
    iv_out = d.here
    d += elm.Dot()

    # I/V feedback, over the top: 2k1 in parallel with Cf.
    for dy, elem, col in ((1.7, elm.Resistor().label('2k1'), 'black'),
                          (3.0, elm.Capacitor().label('Cf ?', color=GREY), GREY)):
        d += elm.Line().at(iv.in1).up().toy(y + dy).color(col)
        d += elm.Line().at(iv_out).up().toy(y + dy).color(col)
        d += elem.at((X_IV, y + dy)).right().tox(iv_out[0]).color(col)

    # +in sits at the DAC's own reference, not at ground.
    d += elm.Line().at(iv.in2).left(1.5)
    d += elm.Dot(open=True).label('VREF\n3.3 V', loc='left', halign='right',
                                 fontsize=9, color=BLUE)

    # ---- AC coupling into the driver -----------------------------------
    d += elm.Line().at(iv_out).right(0.6)
    d += elm.Capacitor2(polar=True).right().label('47µ 16V').label(
        '+', loc='left', ofst=(-0.15, 0.3), fontsize=10)
    d += elm.Resistor().right().label('47k')
    d += elm.Line().tox(X_DRV)

    # ---- Driver: unity-gain line driver, Q inside the loop -------------
    drv = elm.Opamp(leads=True).right().at((X_DRV, y)).anchor('in1')
    drv.label(f"TL074#1\n{ch['dr_sec']}", loc='center', ofst=(0.6, 0), halign='center',
              fontsize=10)
    drv.label(ch['dr_in'], loc='in1', color=BLUE)
    drv.label(ch['dr_ref'], loc='in2', color=BLUE)
    drv.label(ch['dr_out'], loc='out', color=BLUE, ofst=(0.06, 0.24))
    d += drv
    d += elm.Dot().at(drv.in1)

    # +in biased to 0 V through 15k — NOT a hard ground (README gotcha).
    d += elm.Line().at(drv.in2).left(1.2)
    d += elm.Resistor().down().label('15k', loc='bottom')
    d += elm.Ground()

    # ---- Output emitter-follower, inside the feedback loop -------------
    d += elm.Line().at(drv.out).right(1.1)
    q = elm.BjtNpn().right().anchor('base').label(f"{ch['q']}\nBC849C", ofst=(0.45, 0.5))
    d += q

    d += elm.Line().at(q.collector).up().toy(y + 1.5)
    d += elm.Vdd().label('+5 V', color=RED, fontsize=10)

    d += elm.Line().at(q.emitter).down().toy(y - 1.1)
    e_node = d.here
    d += elm.Dot()

    # Class-A pull-down to -12 V, ~35 mA.  Emitter idles at 0 V.
    d += elm.Resistor().down()
    d += elm.Label().at((e_node[0] - 0.45, e_node[1] - 1.1)).label(
        '340R\n(680R∥680R)', halign='right', fontsize=10)
    d += elm.Line().down(0.4)
    d += elm.Vss().label('-12 V', color=RED, fontsize=10)

    # Junction offset to the right of Q, so the feedback riser does not run
    # up through the collector.
    d += elm.Line().at(e_node).right(1.2)
    j = d.here
    d += elm.Dot()

    # Feedback is taken from the EMITTER, over the top of the driver.  This is
    # why op-amp out <-> -in reads OPEN in circuit (README gotcha).
    fb_y = y + 3.6
    d += elm.Line().at(j).up().toy(fb_y)
    d += elm.Line().at((X_DRV, y)).up().toy(fb_y)
    d += elm.Line().right(1.4)
    d += elm.Resistor().right().label('47k').label(
        'reads 4k7 on board?', loc='bottom', fontsize=8, color=GREY)
    d += elm.Line().tox(j[0])

    # DC-coupled to the phones — no series output capacitor.
    d += elm.Line().at(j).right(0.5)
    d += elm.Resistor().right().label('33R')
    d += elm.Resistor().right().label('3R3')
    d += elm.Line().tox(X_OUT)
    d += elm.Dot(open=True).label(f"SK12 {ch['tip']}", loc='right', halign='left',
                                 fontsize=10)

    return iv_in_node


def draw_dac(d, inputs):
    """TDA1545A, drawn once, feeding both channels."""
    y = (CHANNELS[0]['y'] + CHANNELS[1]['y']) / 2
    dac = elm.Ic(
        pins=[
            elm.IcPin(name='DATA', pin='3', side='L'),
            elm.IcPin(name='WS', pin='2', side='L'),
            elm.IcPin(name='BCK', pin='1', side='L'),
            elm.IcPin(name='IOL', pin='6', side='R', anchorname='iol'),
            elm.IcPin(name='IREF', pin='7', side='R', anchorname='iref'),
            elm.IcPin(name='IOR', pin='8', side='R', anchorname='ior'),
            elm.IcPin(name='VDD', pin='5', side='T'),
            elm.IcPin(name='GND', pin='4', side='B'),
        ],
        size=(4.2, 8.0), plblsize=8, leadlen=0.7,
    ).right().at((-3.4, y)).anchor('center')
    dac.label('TDA1545A\ndual 16-bit DAC', loc='center', ofst=(0, -6.1),
              halign='center', fontsize=9)
    d += dac

    d += elm.Line().at(dac.VDD).up(0.5)
    d += elm.Vdd().label('+5 V', color=RED, fontsize=10)
    d += elm.Line().at(dac.GND).down(0.5)
    d += elm.Ground()

    d += elm.Line().at(dac.iref).right(1.1)
    d += elm.Dot(open=True).label('0.83 V', loc='right', halign='left',
                                  fontsize=9, color=BLUE)

    # I2S in from VIDC20 — bussed into the three digital pins.
    xb = dac.BCK[0] - 1.3
    for anchor in (dac.BCK, dac.WS, dac.DATA):
        d += elm.Line().at(anchor).left().tox(xb)
    d += elm.Line().at((xb, dac.BCK[1])).down().toy(dac.DATA[1])
    d += elm.Line().at((xb, dac.WS[1])).left(1.0).label(
        'VIDC20\nI²S', loc='left', halign='right', fontsize=10)

    # Right-angle routes out to each channel's I/V summing node.
    for ch in CHANNELS:
        anchor = getattr(dac, ch['dac_anchor'])
        node = inputs[ch['name']]
        d += elm.Line().at(anchor).right().tox(X_BUS)
        d += elm.Line().to((X_BUS, node[1]))


def draw_supply(d):
    """+/-12 V op-amp feed through the L13/L14 chokes (shared by both channels)."""
    x = 0.0
    y = CHANNELS[1]['y'] - 5.5

    d += elm.Label().at((x + 4.0, y + 1.6)).label(
        'Op-amp supply feed (shared by both channels)', fontsize=11, halign='center')

    for dy, rail, choke, pin, sym in ((0.0, '+12 V', 'L13', '4', elm.Vdd),
                                      (-4.2, '-12 V', 'L14', '11', elm.Vss)):
        d += sym().at((x, y + dy)).label(rail, color=RED, fontsize=10)
        d += elm.Line().at((x, y + dy)).right(0.6)
        d += elm.Inductor2().right().label(f'{choke}  2µ2')
        node = d.here
        d += elm.Dot()
        d += elm.Line().right(1.8)
        d += elm.Dot(open=True).label(f'TL074#1 pin {pin}', loc='right', halign='left',
                                      fontsize=9, color=BLUE)
        d += elm.Capacitor2(polar=True).at(node).down(1.5)
        d += elm.Label().at((node[0] - 0.4, node[1] - 0.8)).label(
            'reservoir\n(value ?)', halign='right', fontsize=8, color=GREY)
        d += elm.Line().down(0.3)
        d += elm.Ground()


def main():
    with schemdraw.Drawing(file='headphone-amp.svg', show=False) as d:
        d.config(unit=2.2, fontsize=11, lw=1.4)

        d += elm.Label().at((13.0, 6.6)).label(
            'RISC PC main PCB 1208,000 — headphone amplifier (reverse-engineered)',
            fontsize=16, halign='center')
        d += elm.Label().at((13.0, 5.8)).label(
            'Both channels shown — they are electrical mirrors.  '
            'Grey = not traced or unconfirmed.',
            fontsize=9, halign='center', color=GREY)

        inputs = {}
        for ch in CHANNELS:
            d += elm.Label().at((X_BUS - 1.2, ch['y'] + 2.4)).label(
                ch['name'], fontsize=13, halign='left')
            inputs[ch['name']] = draw_channel(d, ch)

        draw_dac(d, inputs)
        draw_supply(d)

        # SK12 sleeve — common to both channels (README: "SK12 sleeve = GND").
        y_sleeve = (CHANNELS[0]['y'] + CHANNELS[1]['y']) / 2
        d += elm.Dot(open=True).at((X_OUT, y_sleeve)).label(
            'SK12 sleeve', loc='right', halign='left', fontsize=10)
        d += elm.Line().at((X_OUT, y_sleeve)).down(1.0)
        d += elm.Ground()


# --- UNCERTAIN: drawn grey above, still to confirm on the board -------------
# * Cf across the I/V feedback resistor — present, value never measured.
# * VREF (~3.3 V, 2/3 VDD) is shown as a net stub; its divider is untraced.
# * The driver feedback/input resistors read "4k7" on the board vs 47k in the
#   traced netlist (README fault #7) — the 47k here follows the unity-gain
#   result (-Rf/Rin = -1), which holds either way if both are the same value.
# * Reservoir capacitor values on the L13/L14 rails not recorded.
# * op-amp #2 (speaker path) and the LM386 output network are NOT drawn —
#   deliberately unmapped, see README "Remaining".

if __name__ == '__main__':
    main()
