{
    "Channel Mode": 20,
    "CollectMode": 0,
    "Device": "DSLogic",
    "DeviceMode": 0,
    "Enable RLE Compress": 1,
    "Filter Targets": 0,
    "Horizontal trigger position": 0,
    "Language": 31,
    "Max Height": "1X",
    "Operation Mode": 0,
    "Sample count": "50000896",
    "Sample rate": "50000000",
    "Stop Options": 1,
    "Threshold Level": "2",
    "Title": "DSView v1.3.2",
    "Trigger channel": 0,
    "Trigger hold off": "0",
    "Trigger margin": 8,
    "Trigger slope": 0,
    "Trigger source": 0,
    "Using Clock Negedge": 0,
    "Using External Clock": 1,
    "Version": 3,
    "channel": [
        {
            "colour": "#ffff7f",
            "enabled": true,
            "index": 0,
            "name": "d0",
            "strigger": 0,
            "type": 10000,
            "view_index": 0
        },
        {
            "colour": "#62a0ea",
            "enabled": true,
            "index": 1,
            "name": "a23",
            "strigger": 1,
            "type": 10000,
            "view_index": 1
        },
        {
            "colour": "#00007f",
            "enabled": true,
            "index": 2,
            "name": "a12",
            "strigger": 0,
            "type": 10000,
            "view_index": 2
        },
        {
            "colour": "#0000ff",
            "enabled": true,
            "index": 3,
            "name": "a13",
            "strigger": 0,
            "type": 10000,
            "view_index": 3
        },
        {
            "colour": "#0055ff",
            "enabled": true,
            "index": 4,
            "name": "a14",
            "strigger": 0,
            "type": 10000,
            "view_index": 4
        },
        {
            "colour": "#00aaff",
            "enabled": true,
            "index": 5,
            "name": "a15",
            "strigger": 0,
            "type": 10000,
            "view_index": 5
        },
        {
            "colour": "#55aaff",
            "enabled": true,
            "index": 6,
            "name": "a16",
            "strigger": 0,
            "type": 10000,
            "view_index": 6
        },
        {
            "colour": "#5555ff",
            "enabled": true,
            "index": 7,
            "name": "a17",
            "strigger": 0,
            "type": 10000,
            "view_index": 7
        },
        {
            "colour": "#5555ff",
            "enabled": true,
            "index": 8,
            "name": "a18",
            "strigger": 0,
            "type": 10000,
            "view_index": 8
        },
        {
            "colour": "#5500ff",
            "enabled": true,
            "index": 9,
            "name": "a19",
            "strigger": 0,
            "type": 10000,
            "view_index": 9
        },
        {
            "colour": "#55007f",
            "enabled": true,
            "index": 10,
            "name": "a20",
            "strigger": 0,
            "type": 10000,
            "view_index": 10
        },
        {
            "colour": "#550000",
            "enabled": true,
            "index": 11,
            "name": "a21",
            "strigger": 0,
            "type": 10000,
            "view_index": 11
        }
    ],
    "decoder": [
        {
            "channel": [
                {
                    "d14": 13
                },
                {
                    "d13": 12
                },
                {
                    "d12": 11
                },
                {
                    "d11": 10
                },
                {
                    "d10": 9
                },
                {
                    "d9": 8
                },
                {
                    "d8": 7
                },
                {
                    "d7": 6
                },
                {
                    "d6": 5
                },
                {
                    "d5": 4
                },
                {
                    "d4": 3
                },
                {
                    "d3": 2
                },
                {
                    "d2": 1
                }
            ],
            "id": "parallel",
            "label": "Parallel",
            "options": {
                "clock_edge": "rising",
                "endianness": "little",
                "wordsize": 0
            },
            "show": {
                "parallel": true,
                "parallel: Items": true,
                "parallel: Words": true
            },
            "stacked decoders": [
            ],
            "version": 2,
            "view_index": -1
        },
        {
            "channel": [
                {
                    "a23": 1
                },
                {
                    "d0": 0
                }
            ],
            "id": "acorn_post_wire",
            "label": "Acorn POST",
            "options": {
            },
            "show": {
                "acorn_post": true,
                "acorn_post: Commands": true,
                "acorn_post: Text": true,
                "acorn_post_wire": true,
                "acorn_post_wire: Bits": true,
                "acorn_post_wire: Commands": true,
                "acorn_post_wire: Warnings": true
            },
            "stacked decoders": [
                {
                    "id": "acorn_post",
                    "options": {
                    }
                }
            ],
            "version": 2,
            "view_index": -1
        }
    ],
    "trigger": {
        "advTriggerMode": false,
        "serialTriggerBits": 0,
        "serialTriggerChannel": 0,
        "serialTriggerClock": "X X X X X X X X X X X X X X X X",
        "serialTriggerData": "X X X X X X X X X X X X X X X X",
        "serialTriggerStart": "X X X X X X X X X X X X X X X X",
        "serialTriggerStop": "X X X X X X X X X X X X X X X X",
        "stageTriggerContiguous0": false,
        "stageTriggerContiguous1": false,
        "stageTriggerContiguous10": false,
        "stageTriggerContiguous11": false,
        "stageTriggerContiguous12": false,
        "stageTriggerContiguous13": false,
        "stageTriggerContiguous14": false,
        "stageTriggerContiguous15": false,
        "stageTriggerContiguous2": false,
        "stageTriggerContiguous3": false,
        "stageTriggerContiguous4": false,
        "stageTriggerContiguous5": false,
        "stageTriggerContiguous6": false,
        "stageTriggerContiguous7": false,
        "stageTriggerContiguous8": false,
        "stageTriggerContiguous9": false,
        "stageTriggerCount0": 3,
        "stageTriggerCount1": 1,
        "stageTriggerCount10": 1,
        "stageTriggerCount11": 1,
        "stageTriggerCount12": 1,
        "stageTriggerCount13": 1,
        "stageTriggerCount14": 1,
        "stageTriggerCount15": 1,
        "stageTriggerCount2": 1,
        "stageTriggerCount3": 1,
        "stageTriggerCount4": 1,
        "stageTriggerCount5": 1,
        "stageTriggerCount6": 1,
        "stageTriggerCount7": 1,
        "stageTriggerCount8": 1,
        "stageTriggerCount9": 1,
        "stageTriggerInv00": 0,
        "stageTriggerInv01": 0,
        "stageTriggerInv010": 0,
        "stageTriggerInv011": 0,
        "stageTriggerInv012": 0,
        "stageTriggerInv013": 0,
        "stageTriggerInv014": 0,
        "stageTriggerInv015": 0,
        "stageTriggerInv02": 0,
        "stageTriggerInv03": 0,
        "stageTriggerInv04": 0,
        "stageTriggerInv05": 0,
        "stageTriggerInv06": 0,
        "stageTriggerInv07": 0,
        "stageTriggerInv08": 0,
        "stageTriggerInv09": 0,
        "stageTriggerInv10": 0,
        "stageTriggerInv11": 0,
        "stageTriggerInv110": 0,
        "stageTriggerInv111": 0,
        "stageTriggerInv112": 0,
        "stageTriggerInv113": 0,
        "stageTriggerInv114": 0,
        "stageTriggerInv115": 0,
        "stageTriggerInv12": 0,
        "stageTriggerInv13": 0,
        "stageTriggerInv14": 0,
        "stageTriggerInv15": 0,
        "stageTriggerInv16": 0,
        "stageTriggerInv17": 0,
        "stageTriggerInv18": 0,
        "stageTriggerInv19": 0,
        "stageTriggerLogic0": 1,
        "stageTriggerLogic1": 1,
        "stageTriggerLogic10": 1,
        "stageTriggerLogic11": 1,
        "stageTriggerLogic12": 1,
        "stageTriggerLogic13": 1,
        "stageTriggerLogic14": 1,
        "stageTriggerLogic15": 1,
        "stageTriggerLogic2": 1,
        "stageTriggerLogic3": 1,
        "stageTriggerLogic4": 1,
        "stageTriggerLogic5": 1,
        "stageTriggerLogic6": 1,
        "stageTriggerLogic7": 1,
        "stageTriggerLogic8": 1,
        "stageTriggerLogic9": 1,
        "stageTriggerValue00": "X X X X X X X X X X X X X X X R",
        "stageTriggerValue01": "X X X X X X X X X X X X X X X F",
        "stageTriggerValue010": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue011": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue012": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue013": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue014": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue015": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue02": "X X X X X X X X X X X X X X X R",
        "stageTriggerValue03": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue04": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue05": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue06": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue07": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue08": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue09": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue10": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue11": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue110": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue111": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue112": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue113": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue114": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue115": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue12": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue13": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue14": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue15": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue16": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue17": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue18": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue19": "X X X X X X X X X X X X X X X X",
        "triggerPos": 1,
        "triggerStages": 1,
        "triggerTab": 0
    }
}
