"""
pulsesweep_scripts.py

Defines how Pulse Frequency Sweep experiments are configured and executed.
Sets up sweep ranges and measurement routines to evaluate signal decay across frequencies or fields.

Key Responsibilities:
- Configure frequency/field sweep loops.
- Link `RunInfo` with appropriate pulse generation and readout logic.
- Return time-domain signal data and optional temperature readings.

Key Interactions:
- Called by `server.py` for Pulse Sweep experiment setup.
- Uses `rfsoc2.py` to communicate with RFSoC and acquire signal data.
"""

from rfsoc2 import *
import sys

sys.path.append("../../")
import spinecho_scripts as ses
import pyscan as ps
import numpy as np
from time import sleep, time


def try_fit(func, dat):
    try:
        fit = np.array(ps.func_fit(func, dat)[:2])
    except:
        fit = np.zeros((2, 4))
    return fit


def end_func(d, expt, run):
    sigs = list(expt.xmean[:-1]) + [d.xmean]
    expt.fit = np.zeros((2, 4))
    expt.out, expt.outerr = 0, 0
    if run == "Freq Sweep":  # Frequency sweep
        dat = np.array([expt.freq_sweep, sigs])
        fit = try_fit(ps.lor_fit, dat)
        expt.fit, expt.out, expt.outerr = fit, *fit[:, -1]


def decay_freq_sweep(expt):
    """ """

    runinfo = expt.runinfo
    devices = expt.devices

    d = read_wait(devices, runinfo.parameters)
    #    d = devices.scope.read_vxy()
    expt.t = d.time
    ses.fourier_signal(d)
    if "ls335" in devices.keys():
        d.temp = devices.ls335.get_temp()

    return d


def decay_freq_sweep_onoff(expt):
    """ """

    runinfo = expt.runinfo
    devices = expt.devices

    d = devices.scope.read_vxy_onoff(devices)
    expt.t = d.time
    if "ls335" in devices.keys():
        d.temp = devices.ls335.get_temp()

    return d


def setup_measure_function(soc, function):
    def measure_function(expt):
        runinfo = expt.runinfo
        devices = expt.devices

        prog = runinfo.progfunc(runinfo.parameters)

        # if function==0:
        d = measure_decay(prog, soc)
        # else:
        #    d = runinfo.measure_phase(prog, soc)

        if "ls335" in devices.keys():
            d.temp = devices.ls335.get_temp()

        expt.t = d.time

        d.current_time = time()

        if runinfo._indicies[0] == (runinfo._dims[0] - 1):
            end_func(d, expt, runinfo.parameters["expt"])
            expt.elapsed_time = d.current_time - expt.start_time

        return d

    return measure_function


def setup_experiment(parameters, devices, sweep, soc):
    def freq_sweep(freq):
        parameters["freq"] = freq

    expt_select = {"Freq Sweep": 0, "Field Sweep": 1}
    wait = parameters["wait"]
    sweep_range = ps.drange(
        parameters["sweep_start"], parameters["sweep_step"], parameters["sweep_end"]
    )
    setup_vars = {
        "y_name": ["freq_sweep", "psu_field"],
        "loop": [
            ps.FunctionScan(freq_sweep, sweep_range, dt=wait),
            ps.PropertyScan({"psu": sweep_range}, prop="field", dt=wait),
        ],
        "file": ["PulseFreqSweep", "PulseBSweep"],
    }
    run_n = expt_select[parameters["psexpt"]]
    parameters["y_name"] = setup_vars["y_name"][run_n]
    fname = setup_vars["file"][run_n]
    runinfo = ps.RunInfo()
    runinfo.loop0 = setup_vars["loop"][run_n]

    def progfunc(parameters):
        return CPMGProgram(soc, parameters)

    runinfo.progfunc = progfunc
    runinfo.measure_function = setup_measure_function(soc, run_n)

    runinfo.parameters = parameters
    runinfo.wait_time = wait

    sweep["name"] = parameters["outfile"] + fname
    sweep["runinfo"] = runinfo
