import sigrokdecode as srd

class Decoder(srd.Decoder):
    api_version = 3
    id = 'acorn_post'
    name = 'Acorn POST'
    longname = 'Acorn POST diagnostic adapter protocol'
    desc = 'Decodes the proprietary bit protocol sent to A23 and D0 lines of the Acorn diagnostic adapter.'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = []
    tags = ['Debug/trace']
    channels = (
        {'id': 'a23', 'name': 'A23', 'desc': 'A23 pin'},
        {'id': 'd0', 'name': 'D0', 'desc': 'D0 pin'},
    )
    annotations = (
        ('out_bits', 'Output bits'),
        ('in_bits', 'Input bits'),
        ('read', 'Read'),
        ('write', 'Write'),
        ('warnings', 'Human readable warnings')
    )
    annotation_rows = (
         ('bits', 'Bits', (0,1)),
         ('commands', 'Commands', (2,3)),
         ('warnings', 'Warnings', (4,))
     )

    def __init__(self):
       self.reset()

    def reset(self):
        pass
   
    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)
        
        # Use existing rate or default to 20MHz
        self.samplerate = getattr(self, 'samplerate', 20_000_000)
        self.pulse_duration = (self.samplerate // 1_000_000) * 4
        self.interbit_interval = (self.samplerate // 1_000_000) * 164

    # Look for a burst of pulses within 164μS window
    def count_pulses(self):
        pulse_count = 0
        self.wait({0: 'l'})
        self.wait([{0: 'r'}, {'skip': self.interbit_interval}])
        start = self.samplenum
        if self.matched == 2:
            return (0, start)
        else:
            pulse_count += 1
        
        # Count the number of consecutive pulses
        while pulse_count < 4:
            self.wait([{0: 'r'}, {'skip': self.pulse_duration}])
            if (self.matched == 1): # WTF: shouldn't this be self.matched == (True, False)?
                self.wait({0: 'f'})
                pulse_count += 1
            else:
                break

        return (pulse_count, start)
        
    def decode_input(self):
        # wait for adapter to acknowledge read request
        self.wait([{0: 'h', 1: 'h'}, {'skip': self.pulse_duration}])
        if self.matched == 2:
            return 0

        value = 0
        bits_received = 0

        while bits_received <= 32:
            start = self.samplenum
            self.wait([{0: 'r'}, {'skip': self.pulse_duration}])
            if self.matched == 1:
                a23, d0 = self.wait({0: 'f'})
                bits_received += 1
                value = (value << 1) | d0
                self.put(start, self.samplenum, self.out_ann, [1, [d0]])
            else:
                break

        return value

    def decode_output_byte(self):
        value = 0
        for bit in range(8):
            pulse_count, start = self.count_pulses()
            value = value << 1
            match pulse_count:
                case 1:
                    self.put(start, self.samplenum, self.out_ann, [0, ['1']])
                    value = value | 1
                case 2:
                    self.put(start, self.samplenum, self.out_ann, [0, ['0']])
                    value = value | 0
                case _:
                    self.put(start, self.samplenum, self.out_ann, [4, ['Invalid bits', 'INV', 'IN', 'I']])
                    return None
        return value

    def decode_output(self):
        value = 0
        while (byte:= self.decode_output_byte()) is not None:
            value = (value << 8) + byte
            pulse_count, start = self.count_pulses()
            if pulse_count == 4:
                # lcd outputs pulse for 12 bits...
                self.count_pulses() # second 4 pulses
                self.count_pulses() # third 4 pulses
            elif pulse_count == 3:
                # 3 pulses either means another byte will be sent
                # or this is end of the output stream.
                pass
            else:
                self.put(start, self.samplenum, self.out_ann, [4, ['Invalid bits', 'INV', 'IN', 'I']])
                return None
        return value


    def decode_adapter_operation(self):
        start = self.samplenum
        pulse_count, start = self.count_pulses()
        match pulse_count:
            case 4:
                value = self.decode_input()
                self.put(start, self.samplenum, self.out_ann, [2, ['Input: ' + hex(value), 'IN', 'R']])
            case 3:
                value = self.decode_output()
                self.put(start, self.samplenum, self.out_ann, [3, ['Output: ' + hex(value), 'OUT', 'O']])
            case 0:
                pass
            case _: 
                self.put(start, self.samplenum, self.out_ann, [4, ['Invalid bits', 'INV', 'IN', 'I']])
                
    def decode(self):
        while True:
            self.decode_adapter_operation()
