import sys, os
sys.path.append('../../../pyscan-master/')
import pyscan as ps
import matplotlib.pyplot as plt
import numpy as np
import utility as ut
from datetime import date, datetime
from pathlib import Path
from IPython.display import display, clear_output
import pyvisa
import ipywidgets as ipw

plt.rc('lines', lw=2)
plotfont = {'family': 'serif', 'size': 16}
plt.rc('font', **plotfont)
plt.rc('mathtext', fontset='cm')


def single_shot(sig, parameters, devices, output, fig):
    sltime = 1e3/1e9*2*parameters['ave']
    reps = parameters['reps']
    ave = parameters['ave']

    devices.scope.read_freq_sweep(d=sig, ave=1, sltime=sltime, reps=reps, init=False)

    for ax in fig.axes:
        ax.remove()
    ax = fig.add_subplot(111)
    labs = ['x', 'i', 'q']
    endn = 100
    [ax.plot(sig.ffreqs[1:endn], sig.fourier[n][1:endn], '.', label=labs[n]) for n in range(3)]
    ax.legend()
    ax.set_xlabel('Freq (MHz)')
    ax.set_ylabel('Signal (a.u.)')
    with output:
        clear_output(wait=True)
        display(ax.figure)


def measure_freq_sweep(expt):
    runinfo = expt.runinfo
    devices = expt.devices

    sltime = runinfo.parameters['sltime'] or 1e-5*2*runinfo.parameters['ave']    
    reps = runinfo.parameters['reps']
    ave = runinfo.parameters['ave']
    
    d = devices.scope.read_freq_sweep(ave=ave,
                                        sltime=sltime, reps=reps, init=False)
    
    if runinfo._indicies[0]==(runinfo._dims[0]-1):
        if runinfo.parameters['turn_off']:
            devices.synth.power_off()
            devices.psu.output = False
    return d

    
def setup_experiment(parameters, devices, sweep):
    def chfreq(freq):
        devices.synth.c1_freq = freq+1
        devices.synth.c2_freq = freq
    
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
    
    # expt = ps.Sweep(runinfo, devices, parameters['outfile']+fname)
    # sweep['expt'] = expt
    sweep['name'] = parameters['outfile']+fname
    sweep['runinfo'] = runinfo
