/**
 * RISC PC (main PCB drawing 1208,000) — headphone amplifier.
 *
 * Same circuit as ../headphone_amp.py, expressed in tscircuit instead of
 * schemdraw, to compare the two approaches.  ../../README.md is the authority
 * for the netlist; both files are drawings of it.
 *
 * Deliberately carries NO schX/schY placement hints — the point of the
 * exercise is to see what tscircuit's schematic auto-layout does on its own.
 */

interface ChannelProps {
  name: string
  /** TL074 #1 section letters, e.g. "A" (I/V) and "D" (driver). */
  ivSec: string
  drvSec: string
  /** SOT-23 output emitter-follower designator. */
  q: string
  /** DAC current output feeding this channel's I/V converter. */
  dacPin: string
  /** Net carrying this channel to the jack. */
  tip: string
}

/**
 * One channel: I/V converter -> AC coupling -> unity-gain driver -> jack.
 * Left and right are electrical mirrors, so this is written once.
 */
const Channel = ({ name, ivSec, drvSec, q, dacPin, tip }: ChannelProps) => (
  <group name={name}>
    {/* --- I/V converter: DAC output current -> voltage ----------------- */}
    <opamp name={`U1${ivSec}`} footprint="soic14" />
    {/* 2k1 in parallel with Cf, from output back to the summing node. */}
    <resistor name={`R_iv_${name}`} resistance="2.1k" footprint="0603" />
    <capacitor name={`C_f_${name}`} capacitance="100pF" footprint="0603" />

    <trace from={`.U1${ivSec} > .inverting_input`} to={`net.${dacPin}`} />
    <trace from={`.U1${ivSec} > .non_inverting_input`} to="net.VREF" />
    <trace from={`.U1${ivSec} > .positive_supply`} to="net.V_PLUS12" />
    <trace from={`.U1${ivSec} > .negative_supply`} to="net.V_MINUS12" />
    <trace from={`.R_iv_${name} > .pin1`} to={`.U1${ivSec} > .inverting_input`} />
    <trace from={`.R_iv_${name} > .pin2`} to={`.U1${ivSec} > .output`} />
    <trace from={`.C_f_${name} > .pin1`} to={`.U1${ivSec} > .inverting_input`} />
    <trace from={`.C_f_${name} > .pin2`} to={`.U1${ivSec} > .output`} />

    {/* --- AC coupling into the driver ---------------------------------- */}
    {/* +ve terminal faces the I/V output. */}
    <capacitor
      name={`C_ac_${name}`}
      capacitance="47uF"
      polarized
      footprint="0805"
    />
    <resistor name={`R_in_${name}`} resistance="47k" footprint="0603" />

    <trace from={`.C_ac_${name} > .anode`} to={`.U1${ivSec} > .output`} />
    <trace from={`.C_ac_${name} > .cathode`} to={`.R_in_${name} > .pin1`} />
    <trace from={`.R_in_${name} > .pin2`} to={`.U1${drvSec} > .inverting_input`} />

    {/* --- Driver: unity gain, Q inside the feedback loop ---------------- */}
    <opamp name={`U1${drvSec}`} footprint="soic14" />
    {/* +in biased to 0 V through 15k — not a hard ground. */}
    <resistor name={`R_bias_${name}`} resistance="15k" footprint="0603" />
    {/* Feedback taken from the EMITTER, not the op-amp output. */}
    <resistor name={`R_fb_${name}`} resistance="47k" footprint="0603" />

    <trace from={`.U1${drvSec} > .non_inverting_input`} to={`.R_bias_${name} > .pin1`} />
    <trace from={`.R_bias_${name} > .pin2`} to="net.GND" />
    <trace from={`.U1${drvSec} > .positive_supply`} to="net.V_PLUS12" />
    <trace from={`.U1${drvSec} > .negative_supply`} to="net.V_MINUS12" />

    {/* --- Output emitter-follower -------------------------------------- */}
    <transistor name={q} type="npn" footprint="sot23" />
    {/* 680R || 680R class-A pull-down, ~35 mA. */}
    <resistor name={`R_pull_${name}`} resistance="340" footprint="0603" />
    <resistor name={`R_s1_${name}`} resistance="33" footprint="0603" />
    <resistor name={`R_s2_${name}`} resistance="3.3" footprint="0603" />

    <trace from={`.${q} > .base`} to={`.U1${drvSec} > .output`} />
    <trace from={`.${q} > .collector`} to="net.V_PLUS5" />
    <trace from={`.${q} > .emitter`} to={`.R_fb_${name} > .pin1`} />
    <trace from={`.R_fb_${name} > .pin2`} to={`.U1${drvSec} > .inverting_input`} />
    <trace from={`.${q} > .emitter`} to={`.R_pull_${name} > .pin1`} />
    <trace from={`.R_pull_${name} > .pin2`} to="net.V_MINUS12" />
    <trace from={`.${q} > .emitter`} to={`.R_s1_${name} > .pin1`} />
    <trace from={`.R_s1_${name} > .pin2`} to={`.R_s2_${name} > .pin1`} />
    <trace from={`.R_s2_${name} > .pin2`} to={`net.${tip}`} />
  </group>
)

export default () => (
  // schAutoLayoutEnabled / schTraceAutoLabelEnabled exist in @tscircuit/props
  // but setting them changed the exported SVG by not one byte, so they are
  // left off rather than kept as decoration.
  <board name="riscpc-headphone-amp" width="120mm" height="80mm">
    {/* Philips dual 16-bit DAC — current outputs into the I/V converters. */}
    <chip
      name="DAC"
      footprint="dip8"
      manufacturerPartNumber="TDA1545A"
      pinLabels={{
        pin1: "BCK",
        pin2: "WS",
        pin3: "DATA",
        pin4: "GND",
        pin5: "VDD",
        pin6: "IOL",
        pin7: "IREF",
        pin8: "IOR",
      }}
    />
    <trace from=".DAC > .GND" to="net.GND" />
    <trace from=".DAC > .VDD" to="net.V_PLUS5" />
    <trace from=".DAC > .IOR" to="net.IOR" />
    <trace from=".DAC > .IOL" to="net.IOL" />

    {/* +/-12 V op-amp feed through the L13/L14 chokes. */}
    <inductor name="L13" inductance="2.2uH" footprint="0805" />
    <inductor name="L14" inductance="2.2uH" footprint="0805" />
    <trace from=".L13 > .pin1" to="net.V_PLUS12_RAW" />
    <trace from=".L13 > .pin2" to="net.V_PLUS12" />
    <trace from=".L14 > .pin1" to="net.V_MINUS12_RAW" />
    <trace from=".L14 > .pin2" to="net.V_MINUS12" />

    <Channel name="RIGHT" ivSec="A" drvSec="D" q="Q4" dacPin="IOR" tip="SK12_R" />
    <Channel name="LEFT" ivSec="B" drvSec="C" q="Q1" dacPin="IOL" tip="SK12_L" />
  </board>
)
