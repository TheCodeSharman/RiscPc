# Rigol DS1104Z from the host

Scripts that drive the bench scope over USBTMC with pyusb, so measurements can be
logged and compared instead of eyeballed. Written for the Oct 10 2026 audio-hiss hunt
(see `Dev Diary.md`), where the deciding difference was a few dB of audible-band noise.
That's invisible on the trace.

```bash
nix-shell -p 'python3.withPackages(p:[p.pyusb p.numpy])'
cd tools/rigol
python3 rigol.py '*IDN?'                       # sanity check
python3 scope_log.py 1 1200 0.002 > log.txt &  # log CH1 for 20 min at 2 mV/div
python3 scope_spec.py left:180335:180346 right:180401:180404
python3 rigol.py --shot screen.bmp             # what the person at the bench is seeing
```

| File | Does |
|---|---|
| `rigol.py` | USBTMC client: `write`, `query`, `block`, `waveform` (screen or RAW memory), `screenshot`. Also a CLI for one-off SCPI. |
| `scope_log.py` | Background logger for hand-held probing: fixed AC settings, band-split noise per capture, raw captures saved to `raw/`. |
| `scope_spec.py` | Averaged, detrended spectra of chosen time windows from `raw/`. |

## Gotchas

- **USB mode.** It only speaks SCPI as `1ab1:04ce` (*Utility > IO Setting > USB Device =
  Computer*). As `1ab1:8805` it is PictBridge. The udev rule in `nix-config` covers both.
- **Endpoints.** USBTMC has a bulk-IN *and* an interrupt-IN endpoint. Matching on
  direction alone picks the wrong one and every read times out.
- **Zero-length packets.** A transfer that exactly fills its USB packets is followed by a
  ZLP, which reads as empty. Skip it. Large replies (screenshots) also span several
  transfers, so read until EOM.
- **One client at a time.** A second process gets `Resource busy`. Stop the logger first.
  `pkill -f '^python3 ...'` does **not** match it under nix-shell, because argv[0] is the
  full store path. Kill by PID.
- **Screenshots: BMP24, not PNG.** The PNG came back undecodable.
- **Probe ×1 vs ×10 matters here.** At ×10 the floor is about 2 mVrms, which buries
  headphone-level hiss. At ×1, 1–2 mV/div gives a floor of about 0.1 mVrms. Set the scope's probe
  factor to match the switch (`:CHAN1:PROB 1`).
- **FFT display (Math > FFT) needs a large offset.** The noise is about −100 dBV per bin.
  Around `:MATH:OFFS 90` at 10 dB/div puts it on screen, and 10 dB/div is the finest.
  A few dB of difference is still invisible in the grass, so use `scope_spec.py`.
- **Math > Filter (low-pass 3 kHz) + a Vrms measurement on MATH** is the at-the-bench
  version of the same comparison. It shows the audible-band noise the full-bandwidth
  trace hides. `:MATH:FILT:W1` is clamped by the timebase (1 kHz max at 2 ms/div,
  3 kHz at 0.5 ms/div), and the Math source channel must be displayed.
