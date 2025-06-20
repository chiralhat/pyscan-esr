"""
spinecho_scripts.py

Defines hardware control logic and measurement procedures for Spin Echo experiments.
Handles sweep configuration, signal fitting, and experiment setup routines.

Key Responsibilities:
- Generate appropriate pulse sequences and phase shifts.
- Create and configure `RunInfo` and `Sweep` objects for PyScan.
- Perform signal integration and Fourier analysis.

Key Interactions:
- Called by `server.py` to initialize Spin Echo experiments.
- Uses `rfsoc2.py` for RFSoC pulse generation and signal acquisition.
"""

from rfsoc2 import *
import sys

sys.path.append("../../")
from time import sleep, time
from scipy.fft import rfft, rfftfreq
import numpy as np
import pyscan as ps


def integrate_echo(times, data, alldat=False, backsub=False, prewin=False):
    """Prompts for the integration window, and then integrates all the data
    in that window. If 'alldat' is True, all the datasets are shown in the
    integration prompt, otherwise only the first is shown. If 'backsub' is
    'linear', a linear fit is made between the integration endpoints and
    subtracted from the data before integrating; if it is 'end', the last 50
    points are averaged and subtracted from the data before integrating.
    If 'prewin' is not false it needs to be a two-element list with the
    window limits, in which case the integration prompt doesn't run."""
    # Pick the integration window values by inspecting the data and seeing
    # what window works
    lower_limit, upper_limit = prewin or int_window(times, data, alldat)
    # Check if the limits are entirely outside of our times, and if so
    # set them to be the existing time boundaries
    if lower_limit > times[-1] or upper_limit < times[0]:
        lower_limit, upper_limit = times[[0, -1]]
    lims = [np.abs(times - n).argmin() for n in [lower_limit, upper_limit]]
    tlim = times[lims[0] : lims[1]]

    # Integrate the data over the window
    if backsub == "linear":
        tdiff = tlim[-1] - tlim[0]
        limrange = [np.arange(lims[0], lims[0] + 10), np.arange(lims[1] - 10, lims[1])]
        slope = np.array(
            [
                (np.mean(dat[limrange[1]]) - np.mean(dat[limrange[0]])) / tdiff
                for dat in data
            ]
        )
        intercept = np.array(
            [
                np.mean(data[n][limrange[0]]) - slope[n] * tlim[0]
                for n in np.arange(len(slope))
            ]
        )
        dat_sub = np.array(
            [data[n] - (slope[n] * times + intercept[n]) for n in np.arange(len(slope))]
        )
        se_area = [simps(d[lims[0] : lims[1]], tlim) for d in dat_sub]
        # se_mean = [np.mean(d[lims[0]:lims[1]]) for d in dat_sub]
    elif backsub == "end":
        dat_sub = np.array([dat - np.mean(dat[50:]) for dat in data])
        se_area = [simps(d[lims[0] : lims[1]], tlim) for d in dat_sub]
        # se_mean = [np.mean(d[lims[0]:lims[1]]) for d in dat_sub]
    else:
        se_area = [simps(d[lims[0] : lims[1]], tlim) for d in data]
        # se_mean = [np.mean(d[lims[0]:lims[1]]) for d in data]
    return np.array(se_area)


def fourier_signals(d, fstart=3, fstop=100):
    ns = range(len(d.x))
    d.fourier = np.array(
        [[np.abs(rfft(sig)) for sig in [d.x[n], d.i[n], d.q[n]]] for n in ns]
    )
    # d.fourier.append([np.sqrt(four[:][1]**2+four[:][2]**2) for four in d.fourier])
    d.fourier = np.array(d.fourier)
    d.ffreqs = rfftfreq(len(d.x[0]), d.time[0][1] - d.time[0][0])
    flen = len(d.fourier)
    d.ffit = np.zeros((len(d.x), flen, 4))
    for n in ns:
        for i in range(flen):
            try:
                lordat = np.array([d.ffreqs[n], -d.fourier[n][i]])[:, fstart:fstop]
                d.ffit[n][i] = lor_fit(lordat)[0]
            except:
                d.ffit[n][i] = np.zeros(4)
    d.xfamp = np.array([-fit[0][1] for fit in d.ffit])
    d.ifamp = np.array([-fit[1][1] for fit in d.ffit])
    d.qfamp = np.array([-fit[2][1] for fit in d.ffit])
    # d.xxfamp = np.array([-fit[3][1] for fit in d.ffit])
    d.ffdet = np.array([fit[1][-1] for fit in d.ffit])
    d.ffdet2 = np.array([fit[2][-1] for fit in d.ffit])
    # d.ffdetx = np.array([fit[3][-1] for fit in d.ffit])
    return d


def sback(sig, backnum=100):
    return sig - np.mean(sig[-backnum:])


def try_fit(func, dat, guess):
    try:
        fit = np.array(ps.func_fit(func, dat, guess)[:2])
    except:
        fit = np.zeros((2, len(guess)))
    return fit


def end_func(d, expt, run, dim=0):
    if dim == 0:
        sigs = list(expt.xmean[:-1]) + [d.xmean]
    else:
        sigs = list(expt.xmean[:-1, dim[1]]) + [d.xmean]
    if "fit" not in expt.keys() and not dim == 0:
        expt.fit = np.zeros((dim[0], 2, 4))
        expt.out = np.zeros(dim[0])
        expt.outerr = np.zeros(dim[0])
    if run == "Rabi":  # Rabi sweep
        rabidat = np.array([expt.rabi_sweep, sigs])
        guess = [
            rabidat[1].min(),
            rabidat[1].max(),
            rabidat[0][-1] / 2,
            rabidat[0][-1] / 2,
        ]
        fit = try_fit(ps.rabifitnophi, rabidat, guess)
        if dim == 0:
            expt.fit, expt.out, expt.outerr = fit, *fit[:, 2] / 2
        else:
            expt.fit[dim[1]], expt.out[dim[1]], expt.outerr[dim[1]] = (
                fit,
                *fit[:, 2] / 2,
            )
    elif run == "Hahn Echo" or run == "CPMG":  # Hahn or CPMG sweep
        deldat = np.array([expt.echo_delay, sigs])
        try:
            fit = np.array(ps.exp_fit_norange(deldat, 1, 1)[:2])
        except:
            fit = np.zeros((2, 4))
        if dim == 0:
            fit, expt.out, expt.outerr = fit, *fit[:, 2]
        else:
            expt.fit[dim[1]], expt.out[dim[1]], expt.outerr[dim[1]] = fit, *fit[:, 2]
    elif run == "Phase Sweep":  # Phase sweep
        phasedat = np.array([expt.phase_sweep, sigs])
        try:
            fit, maxphase, pherr = phase_fit(phasedat)
        except:
            fit, maxphase, pherr = np.zeros((2, 4)), 0, 0
        if dim == 0:
            fit, expt.out, expt.outerr = fit, maxphase, pherr
        else:
            expt.fit[dim[1]], expt.out[dim[1]], expt.outerr[dim[1]] = (
                fit,
                maxphase,
                pherr,
            )
    elif run == "Inversion Sweep":  # Inversion sweep
        invdat = np.array([expt.inversion_sweep, sigs])
        try:
            fit = np.array(ps.exp_fit_norange(invdat, 1, 1)[:2])
        except:
            fit = np.zeros((2, 4))
        if dim == 0:
            fit, expt.out, expt.outerr = fit, *fit[:, 2]
        else:
            expt.fit[dim[1]], expt.out[dim[1]], expt.outerr[dim[1]] = fit, *fit[:, 2]


def setup_measure_function(soc, integrate):
    def measure_echo(expt):
        """ """

        runinfo = expt.runinfo
        devices = expt.devices

        if integrate:
            d = acquire_phase(runinfo.parameters, soc)
        else:
            d = measure_phase(runinfo.parameters, soc)

            expt.t = d.time

        d.current_time = time()

        if "ls335" in devices.keys():
            d.temp = devices.ls335.get_temp()

        if runinfo._indicies[0] == (runinfo._dims[0] - 1):
            if runinfo.parameters["sweep2"]:
                dim = [runinfo._dims[1], runinfo.indicies[1]]
            else:
                dim = 0
            end_func(d, expt, runinfo.parameters["expt"], dim)
            if runinfo.parameters["sweep2"] and not runinfo._indicies[1] == (
                runinfo._dims[1] - 1
            ):
                pass
            else:
                expt.elapsed_time = expt.current_time - expt.start_time

        return d

    return measure_echo


def setup_experiment(parameters, devices, sweep, soc):
    def pulse_time(tpi2):
        parameters["pulse1_1"] = tpi2
        parameters["pulse1_2"] = tpi2

    def delay_sweep(delay):
        parameters["delay"] = delay

    def phase_sweep(phase):
        parameters["pi2_phase"] = 0 + phase
        parameters["pi_phase"] = 90 + phase

    def period_sweep(period):
        parameters["period"] = period

    def rabi_sweep(nutation):
        parameters["nutation_length"] = nutation

    def freq_sweep(freq):
        parameters["freq"] = freq

    def inversion_sweep(delay):
        parameters["nutation_delay"] = delay

    def cpmg_sweep(pulses):
        parameters["pulses"] = pulses

    expt_select = {
        "Pulse Sweep": 0,
        "Rabi": 1,
        "Period Sweep": 2,
        "Hahn Echo": 3,
        "EDFS": 4,
        "Freq Sweep": 5,
        "Phase Sweep": 6,
        "Inversion Sweep": 7,
        "CPMG": 8,
    }
    wait = parameters["wait"]
    sweep_range = ps.drange(
        parameters["sweep_start"], parameters["sweep_step"], parameters["sweep_end"]
    )
    sweep2_range = ps.drange(
        parameters["sweep2_start"], parameters["sweep2_step"], parameters["sweep2_end"]
    )
    setup_vars = {
        "y_name": [
            "pulse_time",
            "rabi_sweep",
            "period_sweep",
            "echo_delay",
            "psu_field",
            "freq_sweep",
            "phase_sweep",
            "inversion_sweep",
            "echo_delay",
        ],
        "scan": [
            [
                ps.FunctionScan(pulse_time, s_range, dt=wait),
                ps.FunctionScan(rabi_sweep, s_range, dt=wait),
                ps.FunctionScan(period_sweep, s_range, dt=wait),
                ps.FunctionScan(delay_sweep, s_range, dt=wait),
                ps.PropertyScan({"psu": s_range}, prop="field", dt=wait),
                ps.FunctionScan(freq_sweep, s_range, dt=wait),
                ps.FunctionScan(phase_sweep, s_range, dt=wait),
                ps.FunctionScan(inversion_sweep, s_range, dt=wait),
                ps.FunctionScan(cpmg_sweep, s_range, dt=wait),
            ]
            for s_range in [sweep_range, sweep2_range]
        ],
        "file": [
            "PSweep",
            "Rabi",
            "Period",
            "Hahn",
            "EDFS",
            "EFSweep",
            "PhiSweep",
            "T1",
            "CPMG",
        ],
    }
    run_1 = expt_select[parameters["expt"]]
    run_2 = expt_select[parameters["expt2"]]
    parameters["y_name"] = setup_vars["y_name"][run_1]
    fname = setup_vars["file"][run_1]
    if parameters["loopback"]:
        parameters["single"] = True
        fname += "_looptest"
        parameters["ave_reps"] = 1
    runinfo = ps.RunInfo()
    runinfo.scan0 = setup_vars["scan"][0][run_1]
    if parameters["sweep2"]:  # TODO: Fix sweep range in functions for sweep2
        parameters["y_name2"] = setup_vars["y_name"][run_2]
        runinfo.scan1 = setup_vars["scan"][1][run_2]
        fname = setup_vars["file"][run_2] + "_" + fname

    def progfunc(parameters):
        return CPMGProgram(soc, parameters)

    runinfo.progfunc = progfunc
    runinfo.measure_function = setup_measure_function(soc, parameters["integrate"])

    runinfo.parameters = parameters
    runinfo.wait_time = wait
    sweep["name"] = parameters["outfile"] + fname
    sweep["runinfo"] = runinfo


def phase_fit(dat):
    phase, sig = dat
    guess = [0, np.max(sig), np.pi / 180, 0]
    fit = func_fit(sinefit, np.array([phase, sig]), guess)
    return (
        fit,
        ((90 - fit[0][-1] * 180 / np.pi + 90 * (1 - np.sign(fit[0][1]))) % 360),
        fit[1][-1],
    )


def setup_sweep_sequence(parameters, devices, sweep):
    """Function to prepare (and possibly run) multiple consecutive sweeps,
    possibly using information from one sweep in the following sweeps.
    An example of this would be to run a pulse sweep, then pick the length
    corresponding to the maximum signal. Then run a phase sweep, picking the
    phase corresponding to the maximum Ch1 signal. Then run a Rabi sweep,
    a Hahn echo sweep, and an EDFS.

    Requirements:
    * Need to be able to specify the order of the sweeps.
    * Should be able to specify whether to apply the maxphase, etc.
    * Should create different save files for each sweep (as normal)
    * Should maybe be a new tab in the GUI

    """
    return 0
