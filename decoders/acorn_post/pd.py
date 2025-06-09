import sigrokdecode as srd

class Decoder(srd.Decoder):
    api_version = 3
    id = 'acorn_post'
    name = 'Acorn POST'
    longname = 'Acorn POST diagnostic adapter protocol'
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
        self.out_python = self.register(srd.OUTPUT_PYTHON)
        
        # Use existing rate or default to 20MHz
        self.samplerate = getattr(self, 'samplerate', 20_000_000)
        self.pulse_duration = (self.samplerate // 1_000_000) * 4
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
            return (0, start, data)
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

        return (pulse_count, start, data)
        
    def decode_input(self, ack):
        value = 0
        reading_bits = True
    
        # wait for adapter to acknowledge read request
        while not ack:
            _, ack = self.wait([{0: 'r' }, {'skip': self.pulse_duration}])
            if self.matched == 2:
                break
                reading_bits = False

        while reading_bits:
            start = self.samplenum
            self.wait([{0: 'r'}, {'skip': self.pulse_duration}])
            if self.matched == 1:
                _, data = self.wait({0: 'f'}) 
                value = (value << 1) | data
                self.put(start, self.samplenum, self.out_ann, [1, [str(data)]])
            else:
                reading_bits = False

        self.put(self.start, self.samplenum, self.out_ann, [2, ['Input: ' + hex(value), 'IN', '']])
        self.put(self.start, self.samplenum, self.out_python, ['input', value])
        return value

    def decode_output(self):
        value = 0
        ouput_start = self.start
        last_pulse_start = self.samplenum
        outputing_bits = True
        foundTrailingInput = False
        while outputing_bits:
            pulse_count, last_pulse_start, data = self.count_pulses(self.interbit_interval)
            # Replace match-case with if-elif-else for compatibility
            if pulse_count == 1:
                self.put(last_pulse_start, self.samplenum, self.out_ann, [0, ['1']])
                value = (value << 1) | 1
            elif pulse_count == 2:
                self.put(last_pulse_start, self.samplenum, self.out_ann, [0, ['0']])
                value = (value << 1) | 0
            elif pulse_count == 3:
                # 3 pulses seperate one byte from the next
                pass
            elif pulse_count == 0:
                # We didn't find any pulses so this output is complete
                outputing_bits = False
            elif pulse_count == 4:
                # output ends with an immediate input, we need to signal this
                # to the caller to immediate start readinf the input
                self.start = last_pulse_start # set the global start to the beginning of the input
                outputing_bits = False
                foundTrailingInput = True
                
        self.put(ouput_start, last_pulse_start, self.out_ann, [3, ['Output: ' + hex(value), hex(value), 'O']])
        self.put(ouput_start, last_pulse_start, self.out_python, ['output', value])
        return (value, foundTrailingInput, data)


    def decode_adapter_operation(self):
        self.start = self.samplenum
        pulse_count, start, data = self.count_pulses()
        # Replace match-case with if-elif-else for compatibility
        if pulse_count == 4:
            self.decode_input(data)
        elif pulse_count == 3:
            _, inputDetected, data = self.decode_output()
            # somes times outputs are followed by an input
            if inputDetected:
                self.decode_input(data)
        elif pulse_count == 0:
            pass
        else:
            self.put(start, self.samplenum, self.out_ann, [4, ['Invalid bits', 'INV', 'IN', 'I']])
                
    def decode(self):
        while True:
            self.decode_adapter_operation()
