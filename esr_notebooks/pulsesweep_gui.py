import sys
sys.path.append('../')
import pyscan as ps
import matplotlib.pyplot as plt
import gui_setup as gs

plt.rc('lines', lw=2)
plotfont = {'family': 'serif', 'size': 16}
plt.rc('font', **plotfont)
plt.rc('mathtext', fontset='cm')
default_file = 'ps_defaults.pkl'

pscont_keys = {'devices': [['scope_address', 'fpga_address', 'synth_address', 'psu_address']],
             'synth': [['freq', 'port'],
                       ['power', 'power2', 'phase']],
             'fpga': [['delay', 'pulse1', 'mult'],
                      ['pulse_block', 'period', 'block']],
             'scope': [['ave', 'scale', 'h_offset'],
                       ['tdiv', 'v_offset']],
             'psu': [['field', 'gauss_amps', 'current_limit']],
             'save': [['save_dir', 'file_name']],
             'measure': [['sweep_start', 'sweep_end', 'sweep_step', 'turn_off'],
                         ['psexpt', 'wait', 'sltime', 'init']],
             }


def init_experiment(devices, parameters, sweep):
    parameters['pulse2'] = parameters['pulse1']*parameters['mult']
    devices.fpga.pulse_freq_sweep(parameters)
    devices.synth.pulse_freq_sweep(parameters)
    devices.scope.setup_pulse_decay(parameters)
    devices.psu.set_magnet(parameters)
    setup_experiment(parameters, devices, sweep)


pulsesweep_gui = gs.init_gui(pscont_keys, init_experiment, default_file, 
    single_shot, gs.run_sweep, gs.read)
