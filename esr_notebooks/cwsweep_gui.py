import sys, os
sys.path.append('../../../pyscan-master/')
import pyscan as ps
import matplotlib.pyplot as plt
import numpy as np
import utility as ut
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
    

def init_experiment(devices, parameters, sweep):
    devices.synth.freq_sweep(parameters)
    devices.scope.setup_freq_sweep(parameters)
    devices.fpga.freq_sweep(1)
    devices.psu.set_magnet(parameters)
    setup_experiment(parameters, devices, sweep)


cwsweep_gui = gs.init_gui(cwcont_keys, init_experiment, default_file,
    single_shot, gs.run_sweep, gs.read)
