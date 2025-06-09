import sigrokdecode as srd

class Decoder(srd.Decoder):
    api_version = 3
    id = 'acorn_post_interpreter'
    name = 'Acorn POST Interpreter'
    longname = 'Acorn POST command interpreter'
    desc = 'Interprets the commands from the Acorn POST decoder into meaningful operations.'
    license = 'gplv2+'
    inputs = ['python']
    outputs = ['python']
    tags = ['Debug/trace']
    annotations = (
        ('command', 'Command'),
        ('warning', 'Warning'),
    )
    annotation_rows = (
        ('commands', 'Commands', (0,)),
        ('warnings', 'Warnings', (1,)),
    )

    def __init__(self):
        self.reset()

    def reset(self):
        pass

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.out_python = self.register(srd.OUTPUT_PYTHON)

    def decode(self, startsample, endsample, data):
        if not data:
            return
            
        cmd_type, value = data
        
        # Simply relay the command with its value
        self.put(startsample, endsample, self.out_ann,
                [0, [f'{cmd_type.title()}: {value:02X}h']])
        self.put(startsample, endsample, self.out_python,
                [cmd_type, value]) 