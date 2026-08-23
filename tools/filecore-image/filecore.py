"""Read the structures of a FileCore new-map (E/F format) hard disc image.

The map is not at offset zero: object 2 sits at the start of the middle zone,
and the sectors at offset zero are disc-record copies. `find_map` locates it by
searching for the disc record and validating the zone checks, so nothing here
depends on a hardcoded offset. RD-5725 has no bearing; the authority is the
FileCore source under external/FileCore/Doc.
"""

DIRSIZE = 2048
DIR_TAIL_NAME = 2043
DIR_TAIL_SEQ = 2042
DIR_NAME = 2032
DIR_PARENT = 2010
DIR_HDR = 5
DIR_ENTRY = 26
DIR_ENTRIES = 77
BOOT_BLOCK = 0xC00


class DiscRecord:
    def __init__(self, b):
        self.log2secsize = b[0]
        self.secspertrack = b[1]
        self.heads = b[2]
        self.density = b[3]
        self.idlen = b[4]
        self.log2bpmb = b[5]
        self.skew = b[6]
        self.bootoption = b[7]
        self.lowsector = b[8]
        self.nzones = b[9]
        self.zone_spare = int.from_bytes(b[10:12], "little")
        self.root = int.from_bytes(b[12:16], "little")
        self.disc_size = int.from_bytes(b[16:20], "little")
        self.disc_id = int.from_bytes(b[20:22], "little")
        self.disc_name = b[22:32].split(b"\x00")[0].decode("latin-1").rstrip()

    @property
    def secsize(self):
        return 1 << self.log2secsize

    @property
    def signature(self):
        """The invariant head of the record: everything up to the cycle id."""
        return bytes([self.log2secsize, self.secspertrack, self.heads,
                      self.density, self.idlen, self.log2bpmb, self.skew,
                      self.bootoption, self.lowsector, self.nzones]) + \
            self.zone_spare.to_bytes(2, "little") + \
            self.root.to_bytes(4, "little") + \
            self.disc_size.to_bytes(4, "little")

    def __str__(self):
        return (f"{self.disc_name!r} {self.disc_size} bytes, secsize "
                f"{self.secsize}, nzones {self.nzones}, idlen {self.idlen}, "
                f"lfau {1 << self.log2bpmb}, zone_spare {self.zone_spare}, "
                f"root &{self.root:X}, bootoption {self.bootoption}, "
                f"disc_id &{self.disc_id:04X}")


def zone_check(m, log2secsize, zone):
    v0 = v1 = v2 = v3 = 0
    zone_start = zone << log2secsize
    rover = ((zone + 1) << log2secsize) - 4
    while rover > zone_start:
        v0 += m[rover] + (v3 >> 8)
        v3 &= 0xff
        v1 += m[rover + 1] + (v0 >> 8)
        v0 &= 0xff
        v2 += m[rover + 2] + (v1 >> 8)
        v1 &= 0xff
        v3 += m[rover + 3] + (v2 >> 8)
        v2 &= 0xff
        rover -= 4
    v0 += v3 >> 8
    v1 += m[rover + 1] + (v0 >> 8)
    v2 += m[rover + 2] + (v1 >> 8)
    v3 += m[rover + 3] + (v2 >> 8)
    return (v0 ^ v1 ^ v2 ^ v3) & 0xff


def boot_block_checksum(b):
    acc = carry = 0
    for x in b[:-1]:
        acc = acc + x + carry
        carry = (acc >> 8) & 1
        acc &= 0xff
    return acc


def find_all(buf, needle):
    out, i = [], 0
    while True:
        i = buf.find(needle, i)
        if i < 0:
            return out
        out.append(i)
        i += 1


def find_map(data, dr):
    """Byte offset of the live allocation map, or None."""
    size = dr.nzones << dr.log2secsize
    for hit in find_all(data, dr.signature):
        base = hit - 4
        if base < 0 or base + size > len(data):
            continue
        m = data[base:base + size]
        if all(m[z << dr.log2secsize] == zone_check(m, dr.log2secsize, z)
               for z in range(dr.nzones)):
            return base
    return None


def cross_check(m, dr):
    c = 0
    for z in range(dr.nzones):
        c ^= m[(z << dr.log2secsize) + 3]
    return c


def ctrl_strip(b):
    out = []
    for c in b:
        if c < 32:
            break
        out.append(c)
    return bytes(out).decode("latin-1")


class Directory:
    def __init__(self, offset, raw):
        self.offset, self.raw = offset, raw

    @property
    def name(self):
        return ctrl_strip(self.raw[DIR_NAME:DIR_NAME + 10])

    @property
    def parent(self):
        return int.from_bytes(self.raw[DIR_PARENT:DIR_PARENT + 3], "little")

    @property
    def start_seq(self):
        return self.raw[0]

    @property
    def end_seq(self):
        return self.raw[DIR_TAIL_SEQ]

    @property
    def written_whole(self):
        return self.start_seq == self.end_seq

    def entries(self):
        out = []
        for n in range(DIR_ENTRIES):
            o = DIR_HDR + n * DIR_ENTRY
            if self.raw[o] == 0:
                break
            out.append((ctrl_strip(self.raw[o:o + 10]),
                        int.from_bytes(self.raw[o + 22:o + 25], "little"),
                        int.from_bytes(self.raw[o + 18:o + 22], "little")))
        return out


def directories(data, sig=b"Nick"):
    """Every directory on the disc, keyed by byte offset."""
    found = {}
    for i in find_all(data, sig):
        s = i - 1
        if s < 0 or s + DIRSIZE > len(data):
            continue
        if data[s + DIR_TAIL_NAME:s + DIR_TAIL_NAME + 4] == sig:
            found[s] = Directory(s, data[s:s + DIRSIZE])
    return found


def load(path):
    data = open(path, "rb").read()
    return data, DiscRecord(data[4:68])
