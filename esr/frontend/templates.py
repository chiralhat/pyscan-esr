# Keys for the Pulsed Frequency Sweep experiment type
pulse_freq_sweep_keys = {
    "Main": [
        "freq",
        "psexpt",
        "comp_save",
        "comp_sweep",
    ],
    "Scope": [
        "h_offset",
        "tdiv",
        "ave",
        "scale",
    ],
    "Magnet": [
        "comp_field",
        "use_psu",
        "turn_off",
    ],
    "Synth": [
        "port",
        "power",
        "power2",
        "att",
        "phase",
    ],
    "FPGA": [
        "delay",
        "pulse1",
        "mult",
        "period",
        "block",
        "pulse_block",
    ],
    "Temp": [
        "comp_temp",
        "temp",
        "use_temp",
    ],
    "Uncommon Settings": [
        "wait",
        "sltime",
    ],
    "Never Change": [
        "subtract",
        "moku",
    ],
}

# Keys for the Spin Echo experiment type
spin_echo_sweep_keys = {
    "Main": [          
        "freq",
        "delay",
        "pulse1",
        'nutation_delay',
        'nutation_width',
        "ave",
        "reps",
        "expt",
        "comp_save",
        "comp_sweep",
    ],
    "Scope": [
        "h_offset",
        "scale",
        "tdiv",
    ],
    "Magnet": [
        "comp_field",
        "use_psu",
        "turn_off",
    ],
    "Synth": [
        "port",
        "power",
        "power2",
        "att",
        "phase",
    ],
    "FPGA": [
        "period",
        "cpmg",
        "pulse_block",
        "mult",
        "block",
        "pre_att",
    ],
    "Temp": [
        "comp_temp",
        "temp",
        "use_temp",
    ],
    "Uncommon Settings": [
        "wait",
        "sltime",
        'int_start',
        'int_end',
    ],
    "Never Change": [
        "subtract",
        "moku",
        "phase_sub",
    ],
}

cpmgs = [str(n) for n in range(1, 256)]
voltage_limits = [0.002, 10]
tdivs = ['2e-9', '4e-9']
for n in range(8, 3, -1):
    tdivs += [f'{i}e-{n}' for i in [1, 2, 4]]
for n in range(3, -1, -1):
    tdivs += [str(i*10**-n) for i in [1, 2, 4]]
tdivs += ['10']
tdivs

# Global setting trees for the Pulse Frequency Sweep and Spin Echo experiment settings
sweep_list = [
    "Pulse Sweep",
    "Phase Sweep",
    "Rabi",
    "Inversion Sweep",
    "Period Sweep",
    "Hahn Echo",
    "EDFS",
    "Freq Sweep",
    "CPMG",
    "Gain",
    "DEER",
    "Temp"
]

twotone_sweep_list = [
    "A Pulse Sweep",
    "B Pulse Sweep",
    "Both Pulse Sweep",
    "B Rabi",
    "Period Sweep",
    "Hahn Echo",
    "EDFS",
    "A Freq Sweep",
    "B Freq Sweep",
    "Both Freq Sweep",
    "DEER",
]


def build_experiment_templates(key_dict, control_dict):
    """
    Build experimental control templates based on a provided dictionary of control names

    Args:
        key_dict: nested dictionary of control keys; primary key provides the group name
            and secondary key is the entry from control_dict
        control_dict: nested dictionary of control keys; primary key is the associated
            context and secondary key is the parameter name (except for combinations)

    Returns:
        EXPERIMENT_TEMPLATES for pyscan GUI
    """
    # Flat lookup: secondary_key -> entry, regardless of group
    flat_lookup = {
        sec_key: entry
        for group in control_dict.values()
        for sec_key, entry in group.items()
    }

    groups = {}
    for primary_key in key_dict.keys():
        if primary_key not in groups:
            groups[primary_key] = []

        for secondary_key in key_dict[primary_key]:
            if secondary_key in flat_lookup:
                groups[primary_key].append(flat_lookup[secondary_key])
            else:
                print(f'{secondary_key} not found')

    return {"groups": groups}


CONTROL_DICT = {
    'Synth': {
        'freq': {
            'key': 'freq',
            'display': 'Freq (MHz)',
            'type': 'double_spin',
            'min': 50.0,
            'max': 14999.0,
            'default': 50.0,
            'decimals': 3,
        },
        'freq1': {
            'key': 'freq1',
            'display': 'Ch1 Freq (MHz)',
            'type': 'double_spin',
            'min': 50.0,
            'max': 14999.0,
            'default': 50.0,
            'decimals': 3,
        },
        'freq2': {
            'key': 'freq2',
            'display': 'Ch2 Freq (MHz)',
            'type': 'double_spin',
            'min': 50.0,
            'max': 14999.0,
            'default': 50.0,
            'decimals': 3,
        },
        'detune': {
            'key': 'detune',
            'display': 'Detuning',
            'type': 'double_spin',
            'min': -5000.0,
            'max': 5000.0,
            'default': 0.0,
            'decimals': 3,
        },
        'port': {
            'key': 'port',
            'display': 'Output Port',
            'type': 'combo',
            'options': ['1', '2', 'Both'],
            'default': '1'
        },
        'power': {
            'key': 'power',
            'display': 'Ch1 Power (dBm)',
            'type': 'double_spin',
            'min': -50.0,
            'max': 19.0,
            'default': 0.0,
            'decimals': 3,
        },
        'power2': {
            'key': 'power2',
            'display': 'Ch2 Power',
            'type': 'double_spin',
            'min': -50.0,
            'max': 19.0,
            'default': 0.0,
            'decimals': 3,
        },
        'phase': {
            'key': 'phase',
            'display': 'Phase',
            'type': 'double_spin',
            'min': 0.0,
            'max': 360.0,
            'default': 0.0,
            'decimals': 3,
        },
        'att': {
            'key': 'att',
            'display': 'Attenuator?',
            'type': 'check',
            'default': True
        },
        'att1': {
            'key': 'att1',
            'display': 'Ch1 Attenuator?',
            'type': 'check',
            'default': True
        },
        'att2': {
            'key': 'att2',
            'display': 'Ch2 Attenuator?',
            'type': 'check',
            'default': True
        }},
    'FPGA': {
        'delay': {
            'key': 'delay',
            'display': 'Delay (ns)',
            'type': 'double_spin',
            'min': 10.0,
            'max': 652100.0,
            'default': 10.0
        },
        'delay1': {
            'key': 'delay1',
            'display': 'Ch1 Delay (ns)',
            'type': 'double_spin',
            'min': 10.0,
            'max': 652100.0,
            'default': 10.0
        },
        'delay2': {
            'key': 'delay2',
            'display': 'Ch2 Delay (ns)',
            'type': 'double_spin',
            'min': 10.0,
            'max': 652100.0,
            'default': 10.0
        },
        'pulse1': {
            'key': 'pulse1',
            'display': '90 Pulse (ns)',
            'type': 'double_spin',
            'min': 0.0,
            'max': 652100.0,
            'default': 0.0
        },
        'pulse2': {
            'key': 'pulse2',
            'display': '180 Pulse (ns)',
            'type': 'double_spin',
            'min': 0.0,
            'max': 652100.0,
            'default': 0.0
        },
        'mult': {
            'key': 'mult',
            'display': '180 Pulse Mult',
            'type': 'double_spin',
            'min': 0.0,
            'max': 652100.0,
            'default': 0.0
        },
        'pulse1_1': {
            'key': 'pulse1_1',
            'display': 'Ch1 90 Pulse (ns)',
            'type': 'double_spin',
            'min': 0.0,
            'max': 652100.0,
            'default': 0.0
        },
        'pulse1_2': {
            'key': 'pulse1_2',
            'display': 'Ch1 180 Pulse (ns)',
            'type': 'double_spin',
            'min': 0.0,
            'max': 652100.0,
            'default': 0.0
        },
        'mult1': {
            'key': 'mult1',
            'display': 'Ch1 180 Pulse Mult',
            'type': 'double_spin',
            'min': 0.0,
            'max': 652100.0,
            'default': 0.0
        },
        'pulse2_1': {
            'key': 'pulse2_1',
            'display': 'Ch2 90 Pulse (ns)',
            'type': 'double_spin',
            'min': 0.0,
            'max': 652100.0,
            'default': 0.0
        },
        'pulse2_2': {
            'key': 'pulse2_2',
            'display': 'Ch2 180 Pulse (ns)',
            'type': 'double_spin',
            'min': 0.0,
            'max': 652100.0,
            'default': 0.0
        },
        'mult2': {
            'key': 'mult2',
            'display': 'Ch2 180 Pulse Mult',
            'type': 'double_spin',
            'min': 0.0,
            'max': 652100.0,
            'default': 0.0
        },
        'p2start': {
            'key': 'p2start',
            'display': 'Ch2 Pulse Offset (ns)',
            'type': 'double_spin',
            'min': 0.0,
            'max': 652100.0,
            'default': 0.0
        },
        'period': {
            'key': 'period',
            'display': 'Period (us)',
            'type': 'double_spin',
            'min': 10.0,
            'max': 20000000.0,
            'default': 1000.0
        },
        'cpmg': {
            'key': 'cpmg',
            'display': '# 180 Pulses',
            'type': 'combo',
            'options': cpmgs,
            'default': '1',
        },
        'block': {
            'key': 'block',
            'display': 'Block Pulses',
            'type': 'check',
            'default': False
        },
        'phase_sub': {
            'key': 'phase_sub',
            'display': 'Auto Phase Sub',
            'type': 'check',
            'default': False
        },
        'pulse_block': {
            'key': 'pulse_block',
            'display': 'Block Delay (ns)',
            'type': 'double_spin',
            'min': -5000.0,
            'max': 5000.0,
            'default': 0.0
        },
        'nutation_delay': {
            'key': 'nutation_delay',
            'display': 'Nut. Delay (ns)',
            'type': 'double_spin',
            'min': 0.0,
            'max': 655360.0,
            'default': 600000.0
        },
        'nutation_width': {
            'key': 'nutation_width',
            'display': 'Nut. Pulse Width',
            'type': 'double_spin',
            'min': 0.0,
            'max': 655360.0,
            'default': 0.0
        },
        'pre_att': {
            'key': 'pre_att',
            'display': 'Input Attenuation (Ω)',
            'type': 'double_spin',
            'min': 0.0,
            'max': 31.5,
            'default': 0.0,
            'decimals': 3,
        }},
    'Scope': {
        'ave': {
            'key': 'ave',
            'display': 'Ave',
            'type': 'spin',
            'min': 1,
            'max': 10240,
            'default': 1
        },
        'scale': {
            'key': 'scale',
            'display': 'Scale (V)',
            'type': 'double_spin',
            'min': 0.001,
            'max': 10.0,
            'default': 0.001,
            'decimals': 3,
        },
        'h_offset': {
            'key': 'h_offset',
            'display': 'Time Offset (ns)',
            'type': 'double_spin',
            'min': -100000.0,
            'max': 100000.0,
            'default': 0.0,
            'decimals': 3,
        },
        'tdiv': {
            'key': 'tdiv',
            'display': 'Time Scale (s)',
            'type': 'combo',
            'options': tdivs,
            'default': '1e-7',
        },
        'v_offset': {
            'key': 'v_offset',
            'display': 'Vert Offset?',
            'type': 'check',
            'default': False
        }},
    'PSU': {
        'comp_field': {
            "display": "Field, Scale, I limit",
            "key": ["field", "gauss_amps", "current_limit"],
            "type": "composite",
            "default": [0.0, 276.0, 3.5],
            'decimals': 3,
        },
        'field': {
            'key': 'field',
            'display': 'Magnetic Field (G)',
            'type': 'double_spin',
            'min': 0.0,
            'max': 2500.0,
            'default': 0.0,
            'decimals': 3,
        },
        'gauss_amps': {
            'key': 'gauss_amps',
            'display': 'Magnet Scale (G/A)',
            'type': 'double_spin',
            'min': 0.001,
            'max': 10000.0,
            'default': 277,
            'decimals': 3,
        },
        'current_limit': {
            'key': 'current_limit',
            'display': 'Current Limit (A)',
            'type': 'double_spin',
            'min': 0.0,
            'max': 10.0,
            'default': 3.5,
            'decimals': 3,
        },
        'use_psu': {
            "display": "Use PSU?",
            "key": "use_psu",
            "type": "check",
            "default": False,
        },
        'moku': {
            "display": "Moku",
            "key": "moku",
            "type": "combo",
            "options": ['Cryostat', 'Bench', 'None'],
            "default": "Cryostat",
        }},
    'Temp': {
        'comp_temp': {
            "display": "Set Temp, Ramp, Heater",
            "key": ["set_temp", "temp_ramp", "heater_on"],
            "type": "composite",
            "default": [False, True, False],
        },
        'temp': {
            "display": "Setpoint (K)",
            "key": "temp",
            "type": "double_spin",
            "min": 1.0,
            "max": 325,
            "default": 4,
            'decimals': 3,
        },
        'use_temp': {
            "display": "Use Lakeshore?",
            "key": "use_temp",
            "type": "check",
            "default": False,
        },
    },
    'Save': {
        'comp_save': {
            "display": "Dir and Name",
            "key": ["save_dir", "file_name"],
            "type": "composite",
            "default": ["", ""],
        },
        'save_dir': {
            'key': 'save_dir',
            'display': 'Data Dir',
            'type': 'text',
            'default': ''
        },
        'file_name': {
            'key': 'file_name',
            'display': 'File Name',
            'type': 'text',
            'default': ''
        }},
    'Measure': {
        'subtract': {
            'key': 'subtract',
            'display': 'Sub Method',
            'type': 'combo',
            'options': ['Phase', 'Delay', 'Both', 'None'],
            'default': 'Phase'
        },
        'reps': {
            'key': 'reps',
            'display': 'Reps',
            'type': 'spin',
            'min': 1,
            'max': 1000,
            'default': 1
        },
        'expt': {
            'key': 'expt',
            'display': 'Experiment',
            'type': 'combo',
            'options': sweep_list,
            'default': 'Pulse Sweep'
        },
        'twotone_expt': {
            'key': 'twotone_expt',
            'display': 'Experiment',
            'type': 'combo',
            'options': twotone_sweep_list,
            'default': 'A Pulse Sweep'
        },
        'psexpt': {
            'key': 'psexpt',
            'display': 'Experiment',
            'type': 'combo',
            'options': ['Freq Sweep', 'Field Sweep'],
            'default': 'Freq Sweep'
        },
        'wait': {
            'key': 'wait',
            'display': 'Wait Time (s)',
            'type': 'double_spin',
            'min': 0.0,
            'max': 20.0,
            'default': 0.0,
            'decimals': 3,
        },
        'sltime': {
            'key': 'sltime',
            'display': 'Averaging Time (s)',
            'type': 'double_spin',
            'min': 0.0,
            'max': 20.0,
            'default': 0.0,
            'decimals': 3,
        },
        'comp_sweep': {
            "display": "Sweep start, end, step",
            "key": ["sweep_start", "sweep_end", "sweep_step"],
            "type": "composite",
            "default": [150.0, 1000.0, 50.0],
            'decimals': 3,
        },
        'int_start': {
            'key': 'int_start',
            'display': 'Int. Window (μs): Pre',
            'type': 'double_spin',
            'default': 0.0,
            'decimals': 3,
        },
        'int_end': {
            'key': 'int_end',
            'display': 'Post Delay',
            'type': 'double_spin',
            'default': 0.0,
            'decimals': 3,
        },
        'int_start2': {
            'key': 'int_start2',
            'display': 'Int. Window 2 (μs): Pre',
            'type': 'double_spin',
            'default': 0.0,
            'decimals': 3,
        },
        'int_end2': {
            'key': 'int_end2',
            'display': 'Post Delay 2',
            'type': 'double_spin',
            'default': 0.0,
            'decimals': 3,
        },
        'turn_off': {
            'key': 'turn_off',
            'display': 'Turn off after sweep?',
            'type': 'check',
            'default': False
        }}
}

EXPERIMENT_TEMPLATES = {
    "Pulse Frequency Sweep": build_experiment_templates(
        pulse_freq_sweep_keys, CONTROL_DICT
    ),
    "Spin Echo": build_experiment_templates(
        spin_echo_sweep_keys, CONTROL_DICT
    ),
}