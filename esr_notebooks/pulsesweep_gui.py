import sys
sys.path.append('../')
import pyscan as ps
import matplotlib.pyplot as plt
import gui_setup as gs
from esr.backend.pulsesweep_scripts import *

plt.rc('lines', lw=2)
plotfont = {'family': 'serif', 'size': 16}
plt.rc('font', **plotfont)
plt.rc('mathtext', fontset='cm')
default_file = 'ps_defaults.pkl'

pscont_keys = {'devices': [['use_psu', 'moku']],
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


def single_shot(sig, parameters, devices, output, fig):
    devices.scope.read_vxy(d=sig)
    for ax in fig.axes:
        ax.remove()
    ax = fig.add_subplot(111)
    freq = devices.synth.c_freqs
    fit, err = ps.plot_exp_fit_norange(np.array([sig.time*1e6, sig.x]),
                                       freq, 1, plt=ax)
    sig.fit = fit
    fitstr = f'A={fit[1]:.3g} V, t={fit[2]:.3g} μs, Q={fit[2]*np.pi*freq/1e6:.3g}'
    # fourstr = f'famp: v1={sig.v1famp:.3g}, v2={sig.v2famp:.3g}'
    # fourfstr = f'ffreq (MHz): v1={sig.ffdet/1e6:.3g}, v2={sig.ffdet2/1e6:.3g}'
    freqstr = f'freq (MHz): {freq/1e6}'
    ax.set_xlabel('Time (μs)')
    ax.set_ylabel('Voltage (V)')
    xpt = sig.time[len(sig.time)//5]*1e6
    ypt = sig.x.max()*np.array([0.75, 0.65, 0.55, 0.85])
    ax.text(xpt, ypt[0], fitstr)
    # ax.text(xpt, ypt[1], fourstr)
    # ax.text(xpt, ypt[2], fourfstr)
    ax.text(xpt, ypt[3], freqstr)
    with output:
        clear_output(wait=True)
        display(ax.figure)


def init_experiment(devices, parameters, sweep):
    parameters['pulse2'] = parameters['pulse1']*parameters['mult']
    # p1_time = parameters['pulse1']+(parameters['delay']*2+parameters['pulse2'])*parameters['cpmg']
    # switch_time = 500 + p1_time
    devices.fpga.pulse_freq_sweep(parameters)
    devices.synth.pulse_freq_sweep(parameters)
    devices.scope.setup_pulse_decay(parameters)
    if not parameters['moku']=="None":
        devices.moku.set_switch_1pulse(2*parameters['delay']) 
        devices.moku.set_magnet(parameters)
    if parameters["use_psu"]:
        devices.psu.output = True
    setup_experiment(parameters, devices, sweep)


pulsesweep_gui = gs.init_gui(pscont_keys, init_experiment, default_file, 
    single_shot, gs.run_sweep, gs.read)
