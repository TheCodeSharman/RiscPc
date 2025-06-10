import sigrokdecode as srd

class Decoder(srd.Decoder):
    api_version = 3
    id = 'acorn_post_wire'
    name = 'Acorn POST wire'
    longname = 'Acorn POST diagnostic adapter wire protocol'
    desc = 'Decodes the proprietary bit protocol sent to A23 and D0 lines of the Acorn diagnostic adapter.'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = ['python']
    tags = ['Debug/trace']
    channels = (
        {'id': 'a23', 'name': 'A23', 'desc': 'A23 pin'},
        {'id': 'd0', 'name': 'D0', 'desc': 'D0 pin'},
    )
    annotations = (
        ('out_bits', 'Output bits'),
        ('in_bits', 'Input bits'),
        ('input', 'Input'),
        ('output', 'Output'),
        ('warnings', 'Human readable warnings')
    )
    annotation_rows = (
         ('bits', 'Bits', (0,1)),
         ('commands', 'Commands', (2,3)),
         ('warnings', 'Warnings', (4,))
     )
    class Pulse:
        def __init__(self, count, start, end, data):
            self.count = count
            self.start = start
            self.end = end
            self.data = data

    def __init__(self):
       self.reset()

    def reset(self):
        self.pulse_buffer = []
   
    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.out_python = self.register(srd.OUTPUT_PYTHON)
        
        # Use existing rate or default to 20MHz
        self.samplerate = getattr(self, 'samplerate', 20_000_000)
        self.pulse_duration = (self.samplerate // 1_000_000) * 8
        self.interbit_interval = (self.samplerate // 1_000_000) * 164

    # Look for a burst of pulses within 164μS window
    def count_pulses(self, window = None):
        pulse_count = 0
        data = None
        if not window:
            window = self.pulse_duration
        self.wait({0: 'l'})
        self.wait([{0: 'r'}, {'skip': window}])
        start = self.samplenum
        if self.matched == 2:
            return Decoder.Pulse(0, start, self.samplenum, data)
        else:
            pulse_count += 1
        
        # Count the number of consecutive pulses
        while pulse_count < 4:
            self.wait([{0: 'r'}, {'skip': self.pulse_duration}])
            if (self.matched == 1):
                _, data = self.wait({0: 'f'})
                pulse_count += 1
            else:
                break

        return Decoder.Pulse(pulse_count, start, self.samplenum, data)
        
    def decode_input(self):
        if not(len(self.pulse_buffer) == 1 and self.pulse_buffer[0].count == 4):
            return
        
        value = 0
        pulse = self.pulse_buffer.pop()
        ack = pulse.data
    
        # wait for adapter to acknowledge read request
        while not ack:
            _, ack = self.wait([{0: 'r' }, {'skip': self.pulse_duration}])
            if self.matched == 2:
                return

        while True:
            start = self.samplenum
            self.wait([{0: 'r'}, {'skip': self.pulse_duration}])
            if self.matched == 1:
                _, data = self.wait({0: 'f'}) 
                value = (value << 1) | data
                self.put(start, self.samplenum, self.out_ann, [1, [str(data)]])
            else:
                break

        self.put(pulse.start, self.samplenum, self.out_ann, [2, ['Input: ' + hex(value),  hex(value), 'I']])
        self.put(pulse.start, self.samplenum, self.out_python, ['input', value])

    def decode_output(self):
        if not (len(self.pulse_buffer) == 1 and self.pulse_buffer[0].count == 3):
            return
        
        value = 0
        begin_pulse = self.pulse_buffer.pop()
        previous_pulse = begin_pulse

        while True:
            pulse = self.count_pulses(self.interbit_interval)
            # Replace match-case with if-elif-else for compatibility
            if pulse.count == 1:
                self.put(pulse.start, pulse.end, self.out_ann, [0, ['1']])
                value = (value << 1) | 1
            elif pulse.count == 2:
                self.put(pulse.start, pulse.end, self.out_ann, [0, ['0']])
                value = (value << 1) | 0
            elif pulse.count == 3:
                # 3 pulses seperate one byte from the next
                pass
            elif pulse.count == 0:
                break
            elif pulse.count == 4:
                # Leave the input pulse in the buffer so it can be processed next
                self.pulse_buffer.append(pulse)
                break
            previous_pulse = pulse

        self.put(begin_pulse.start, previous_pulse.end, self.out_ann, [3, ['Output: ' + hex(value), hex(value), 'O']])
        self.put(begin_pulse.start, previous_pulse.end, self.out_python, ['output', value])
            
    def invalid_bits(self):
        if not(len(self.pulse_buffer) == 1 and self.pulse_buffer[0].count in (1, 2)):
            return
        
        pulse = self.pulse_buffer.pop()
        self.put(pulse.start, pulse.end, self.out_ann, [4, ['Invalid bits', 'INV', 'IN', 'I']])
    
    def no_pulse(self):
        if not( len(self.pulse_buffer) == 1 and self.pulse_buffer[0].count == 0 ):
            return
        self.pulse_buffer.pop()

    def decode_adapter_operation(self):
        self.pulse_buffer.append(self.count_pulses())

        while len(self.pulse_buffer) > 0:
            self.decode_input()
            self.decode_output()
            self.invalid_bits()
            self.no_pulse()
                
    def decode(self):
        while True:
            self.decode_adapter_operation()
