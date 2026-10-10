"""Background noise logger for hand-held probing.

Fixed AC settings (nothing switches, so the screen stays steady), one RAW capture
(12k points @ 100 kSa/s = 120 ms) about every second, wall-clock stamped.  Prints the
noise in audio bands and saves every capture to raw/HHMMSS_us.npy for scope_spec.py.

    python3 scope_log.py [ch] [secs] [V/div] > log.txt

Workflow: the person probing says in chat what they touched and when; a Ctrl-G beep
(~508 Hz, clips at mV/div) before each point marks it in the log.  A floating probe
shows as steady 50 Hz pickup; a floor reading is the probe tip on its own ground.
"""
import datetime, os, sys, time
import numpy as np
from rigol import Rigol

ch = int(sys.argv[1]) if len(sys.argv) > 1 else 1
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 900
s = Rigol()
P = float(s.query(f':CHAN{ch}:PROB?'))
vdiv = float(sys.argv[3]) if len(sys.argv) > 3 else 0.002 * P
for c in [':RUN', f':CHAN{ch}:DISP 1', f':CHAN{ch}:COUP AC', f':CHAN{ch}:BWL 20M',
          f':CHAN{ch}:SCAL {vdiv:g}', f':CHAN{ch}:OFFS 0', ':TIM:SCAL 0.01',
          ':ACQ:TYPE NORM', ':ACQ:MDEP 12000', ':TRIG:SWE AUTO']:
    s.write(c)
time.sleep(1.5)
print(f'CH{ch} x{P:g} {s.query(f":CHAN{ch}:SCAL?")} V/div, srate {s.query(":ACQ:SRAT?")}', flush=True)

os.makedirs('raw', exist_ok=True)
t0 = time.time()
while time.time() - t0 < secs:
    time.sleep(0.4)
    try:
        dt, v = s.waveform(f'CHAN{ch}', raw=True)
    except Exception as e:
        print('err', e, flush=True); s.write(':RUN'); continue
    if len(v) < 1000:
        continue
    clip = np.ptp(v) >= 0.98 * 8 * float(s.query(f':CHAN{ch}:SCAL?'))
    ts = datetime.datetime.now()
    np.save(f'raw/{ts:%H%M%S_%f}.npy', v.astype(np.float32))
    v = v - v.mean()
    sp = np.abs(np.fft.rfft(v * np.hanning(len(v)))) * 4 / len(v)
    f = np.fft.rfftfreq(len(v), dt)
    band = lambda lo, hi: np.sqrt((sp[(f >= lo) & (f < hi)] ** 2).sum() / 2) * 1e3
    m = (f > 20) & (f < 20e3)
    top = np.argsort(sp * m)[-3:][::-1]
    print(f'{ts:%H:%M:%S}  20-400 {band(20, 400):5.2f}  0.4-1k {band(400, 1e3):5.2f}  '
          f'1-3k {band(1e3, 3e3):5.2f}  3-8k {band(3e3, 8e3):5.2f}  8-20k {band(8e3, 20e3):5.2f}  '
          f'>20k {band(20e3, 50e3):5.2f} mVrms | '
          + ', '.join(f'{f[k]:.0f}Hz {sp[k]*1e3:.2f}' for k in top) + ('  CLIP' if clip else ''),
          flush=True)
