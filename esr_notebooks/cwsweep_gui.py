import sys
sys.path.append('../')
import pyscan as ps
import matplotlib.pyplot as plt
import numpy as np
from datetime import date, datetime
from pathlib import Path
import pickle
import ipywidgets as ipw
from cwsweep_scripts import *
import gui_setup as gs

plt.rc('lines', lw=2)
plotfont = {'family': 'serif', 'size': 16}
plt.rc('font', **plotfont)
plt.rc('mathtext', fontset='cm')
default_file = 'cw_defaults.pkl'

cwcont_keys = {'devices': [['scope_address', 'fpga_address', 'synth_address', 'psu_address']],
             'synth': [['freq_start', 'freq_end', 'freq_step', 'power2']],
             'scope': [['ave', 'scale']],
             'psu': [['field', 'gauss_amps', 'current_limit']],
             'save': [['save_dir', 'file_name']],
             'measure': [['reps', 'wait', 'sltime'],
                         ['init', 'turn_off']]
                   }
    
    
def read(sig, config, soc, output, fig):
    """
    Take and plot a single measurement.

    Parameters
    ----------
    sig : pyscan ItemAttribute
        Signal object for accessing the data. Updated by this function.
    parameters : dict
        Experimental parameters from the controls.
    devices : pyscan ItemAttribute
        Devices object for accessing the acquisition equipment.
    output : ipyWidgets Output
        Output window.
    fig : pyplot Figure
        Figure used to plot the data.

    Returns
    -------
    None.

    """
    config['single'] = True
    config['soft_avgs'] = 1
    prog = CPMGProgram(soc, config)
    measure_phase(prog, soc, sig)
    
    for ax in fig.axes:
        ax.remove()
    ax = fig.add_subplot(111)
    ax.plot(sig.time, sig.i, color='yellow', label='CH1')
    ax.plot(sig.time, sig.q, color='b', label='CH2')
    ax.plot(sig.time, sig.x, color='g', label='AMP')
    ax.set_xlabel('Time (μs)')
    ax.set_ylabel('Signal (a.u.)')
    #[ax.axvline(x=w*1e6, color='purple', ls='--') for w in win]
    ax.legend()
    with output:
        clear_output(wait=True)
        display(ax.figure)
    

def init_experiment(devices, parameters, sweep):
    devices.synth.freq_sweep(parameters)
    devices.scope.setup_freq_sweep(parameters)
    devices.fpga.freq_sweep(1)
    devices.psu.set_magnet(parameters)
    setup_experiment(parameters, devices, sweep)


cwsweep_gui = gs.init_gui(cwcont_keys, init_experiment, default_file,
    single_shot, gs.run_sweep, gs.read)
