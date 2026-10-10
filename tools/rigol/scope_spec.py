"""Averaged noise spectra of time windows from scope_log.py's raw/ captures.

    python3 scope_spec.py floor:180350:180357 pin7:180335:180338 pin1:180401:180404

Each capture is detrended with a cubic first (hand-held probing on a DC node leaves an
AC-coupling settling tail that otherwise swamps the low bands), then Welch-averaged in
2000-point segments (50 Hz bins); the median across captures resists contact glitches.
"""
import glob, os, sys
import numpy as np

FS = 1e5
SEG = 2000
BANDS = [(400, 1e3), (1e3, 3e3), (3e3, 8e3), (8e3, 20e3), (20e3, 50e3)]


def psds(t0, t1):
    out = []
    for p in sorted(glob.glob('raw/*.npy')):
        if not t0 <= os.path.basename(p)[:6] <= t1:
            continue
        v = np.load(p).astype(float)
        if np.ptp(v) == 0:   # fully clipped capture
            continue
        x = np.arange(len(v))
        v = v - np.polyval(np.polyfit(x, v, 3), x)
        w = np.hanning(SEG)
        segs = [np.abs(np.fft.rfft(v[k:k + SEG] * w)) ** 2 / (FS * (w ** 2).sum())
                for k in range(0, len(v) - SEG + 1, SEG // 2)]
        out.append(np.mean(segs, axis=0))
    return np.fft.rfftfreq(SEG, 1 / FS), np.array(out)


for name, t0, t1 in (a.split(':') for a in sys.argv[1:]):
    f, S = psds(t0, t1)
    if not len(S):
        print(f'{name:12s} no captures'); continue
    psd = np.median(S, axis=0)
    rms = [np.sqrt(2 * psd[(f >= lo) & (f < hi)].sum() * (f[1] - f[0])) * 1e3 for lo, hi in BANDS]
    print(f'{name:12s} n={len(S):2d}  '
          + '  '.join(f'{lo/1e3:g}-{hi/1e3:g}k {r:5.2f}' for (lo, hi), r in zip(BANDS, rms)) + '  mVrms')
