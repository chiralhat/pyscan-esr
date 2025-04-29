"""
pulsesweep_scripts.py

This module sets up the hardware and measurement logic for Pulse Frequency Sweep experiments.

Key responsibilities:
- Define how the experiment should update parameters (e.g., sweeping frequency)
- Configure the sweep range and looping behavior for frequency or field sweeps
- Set up measurement functions that capture decay signals at each sweep point
- Connect with the RFSoC board (via `rfsoc2`) and scope hardware for data acquisition
- Update experiment objects with time series signal data and optional temperature readings

Dependencies:
- pyscan.py for Scan and Sweep utilities
- spinecho_scripts for signal processing functions (like Fourier transforms)
- rfsoc2.py for RFSoC interaction
"""

from rfsoc2 import *
import sys
sys.path.append('../')
import spinecho_scripts as ses
import pyscan as ps
import numpy as np
from time import sleep, time


def decay_freq_sweep(expt):
    """
    """
     
    runinfo = expt.runinfo
    devices = expt.devices

    d = read_wait(devices, runinfo.parameters)
#    d = devices.scope.read_vxy()
    expt.t = d.time
    ses.fourier_signal(d)
    if 'ls335' in devices.keys():
        d.temp = devices.ls335.get_temp()
    
    return d


def decay_freq_sweep_onoff(expt):
    """
    """
     
    runinfo = expt.runinfo
    devices = expt.devices

    d = devices.scope.read_vxy_onoff(devices)
    expt.t = d.time
    if 'ls335' in devices.keys():
        d.temp = devices.ls335.get_temp()
    
    return d


def setup_measure_function(soc, function):
    def measure_function(expt):
        runinfo = expt.runinfo
        devices = expt.devices

        prog = runinfo.progfunc(runinfo.parameters)

        #if function==0:
        d = measure_decay(prog, soc)
        #else:
        #    d = runinfo.measure_phase(prog, soc)

        if 'ls335' in devices.keys():
            d.temp = devices.ls335.get_temp()

        expt.t = d.time

        d.current_time = time()

        return d
    
    return measure_function


def setup_experiment(parameters, devices, sweep, soc):
    def freq_sweep(freq):
        parameters['freq'] = freq
    expt_select = {'Freq Sweep': 0,
                   'Field Sweep': 1}
    wait = parameters['wait']
    sweep_range = ps.drange(parameters['sweep_start'],
                            parameters['sweep_step'],
                            parameters['sweep_end'])
    setup_vars = {'y_name': ['freq_sweep',
                            'psu_field'],
                 'loop': [ps.FunctionScan(freq_sweep, sweep_range, dt=wait),
                              ps.PropertyScan({'psu': sweep_range}, prop='field', dt=wait)],
                  'file': ['PulseFreqSweep',
                           'PulseBSweep']
                  }
    run_n = expt_select[parameters['psexpt']]
    parameters['y_name'] = setup_vars['y_name'][run_n]
    fname = setup_vars['file'][run_n]
    runinfo = ps.RunInfo()
    runinfo.loop0 = setup_vars['loop'][run_n]
    def progfunc(parameters):
        return CPMGProgram(soc, parameters)
    runinfo.progfunc = progfunc
    runinfo.measure_function = setup_measure_function(soc, run_n)

    runinfo.parameters = parameters
    runinfo.wait_time = wait

    sweep['name'] = parameters['outfile']+fname
    sweep['runinfo'] = runinfo



