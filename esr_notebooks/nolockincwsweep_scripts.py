import sys, os
sys.path.append('../')
import pyscan as ps
import matplotlib.pyplot as plt
import numpy as np
from datetime import date, datetime
from pathlib import Path
from IPython.display import display, clear_output
import pyvisa
import ipywidgets as ipw

plt.rc('lines', lw=2)
plotfont = {'family': 'serif', 'size': 16}
plt.rc('font', **plotfont)
plt.rc('mathtext', fontset='cm')


def v_to_s(ch1, ch2, out=0):
    if isinstance(out, int):
        out = ps.ItemAttribute()
    out.freq = ch1[0]
    i = ch1[1]
    q = ch2[1]
    out.i = i
    out.q = q
    out.x = np.sqrt(i**2 + q**2)
    
    return out


def setup_experiment(parameters, devices, sweep):
    expt_select = {'Freq Sweep': 0}
    wait = parameters['wait']
    sweep_range = ps.drange(parameters['freq_start'],
                            parameters['freq_step'],
                            parameters['freq_end'])
    setup_vars = {'y_name': ['chfreq'],
                  'loop': [ps.FunctionScan(chfreq, sweep_range, dt=wait)],
                  'file': ['FSweep']
                  }
    run_n = 0#expt_select[parameters['expt']]
    parameters['y_name'] = setup_vars['y_name'][run_n]
    fname = setup_vars['file'][run_n]
    runinfo = ps.RunInfo()
    runinfo.loop0 = setup_vars['loop'][run_n]
    runinfo.measure_function = measure_freq_sweep
    runinfo.sltime = parameters['sltime']
    # devices.scope.read_scope()

    runinfo.parameters = parameters
    runinfo.wait_time = parameters['wait']
    
    expt = ps.Sweep(runinfo, devices, parameters['outfile']+fname)
    sweep['expt'] = expt
    sweep['runinfo'] = runinfo
