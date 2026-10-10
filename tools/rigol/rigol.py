"""Minimal USBTMC client for the Rigol DS1104Z (1ab1:04ce) via pyusb.

    python3 rigol.py '*IDN?' ':CHAN1:SCAL 0.002' ':CHAN1:SCAL?'   # '?' = query
    python3 rigol.py --shot screen.bmp                            # screenshot
"""
import struct, sys
import numpy as np
import usb.core, usb.util


class Rigol:
    def __init__(self):
        d = usb.core.find(idVendor=0x1ab1, idProduct=0x04ce)
        if d is None:   # 1ab1:8805 = USB mode set to PictBridge, not Computer
            raise SystemExit('scope not found (Utility > IO Setting > USB Device = Computer?)')
        for i in range(d.get_active_configuration().bNumInterfaces):
            if d.is_kernel_driver_active(i):
                d.detach_kernel_driver(i)
        intf = d.get_active_configuration()[(0, 0)]
        # USBTMC also has an interrupt-IN endpoint; match on transfer type, not just direction
        bulk = lambda e: usb.util.endpoint_type(e.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK
        self.ep_out = usb.util.find_descriptor(intf, custom_match=lambda e: bulk(e) and
            usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
        self.ep_in = usb.util.find_descriptor(intf, custom_match=lambda e: bulk(e) and
            usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)
        self.d, self.tag = d, 1

    def _hdr(self, msgid, n, attr=0):
        t = self.tag
        self.tag = self.tag % 255 + 1
        return struct.pack('<BBBxIBxxx', msgid, t, (~t) & 0xff, n, attr)

    def write(self, cmd):
        b = cmd.encode() + b'\n'
        pkt = self._hdr(1, len(b), 1) + b
        pkt += b'\0' * (-len(pkt) % 4)
        self.ep_out.write(pkt, timeout=5000)

    def read_raw(self):
        """One response, which may span several DEV_DEP_MSG_IN transfers."""
        out = b''
        while True:
            self.ep_out.write(self._hdr(2, 1 << 20), timeout=5000)
            data = b''
            while len(data) < 12:   # a transfer that fills whole packets is followed by a ZLP
                data += bytes(self.ep_in.read(1 << 20 | 64, timeout=10000))
            n, attr = struct.unpack_from('<IB', data, 4)
            body = data[12:]
            while len(body) < n:
                body += bytes(self.ep_in.read(1 << 20 | 64, timeout=10000))
            out += body[:n]
            if attr & 1:   # EOM
                return out

    def query(self, cmd):
        self.write(cmd)
        return self.read_raw().decode(errors='replace').strip()

    def block(self, cmd):
        """Send a query whose reply is an IEEE 488.2 #N<len><data> block; return the data."""
        self.write(cmd)
        r = self.read_raw()
        nd = int(r[1:2])
        return r[2 + nd:2 + nd + int(r[2:2 + nd])]

    def waveform(self, src='CHAN1', raw=False, points=12000):
        """(dt, volts).  raw=False: the 1200-point screen trace (runs live).
        raw=True: `points` from acquisition memory (stops the scope, restarts it)."""
        if raw:
            self.write(':STOP')
        self.write(f':WAV:SOUR {src}')
        self.write(f':WAV:MODE {"RAW" if raw else "NORM"}')
        self.write(':WAV:FORM BYTE')
        if raw:
            self.write(':WAV:STAR 1')
            self.write(f':WAV:STOP {points}')
        pre = [float(x) for x in self.query(':WAV:PRE?').split(',')]
        b = np.frombuffer(self.block(':WAV:DATA?'), np.uint8).astype(float)
        if raw:
            self.write(':RUN')
        return pre[4], (b - pre[8] - pre[9]) * pre[7]

    def screenshot(self, path):
        # BMP24, not PNG: the PNG came back undecodable ("invalid distance too far back")
        img = self.block(':DISP:DATA? ON,OFF,BMP24')
        open(path, 'wb').write(img)
        return len(img)


if __name__ == '__main__':
    s = Rigol()
    if sys.argv[1:2] == ['--shot']:
        print(s.screenshot(sys.argv[2]), 'bytes')
    else:
        for c in sys.argv[1:]:
            print(c, '->', s.query(c) if c.endswith('?') else (s.write(c) or 'ok'))
