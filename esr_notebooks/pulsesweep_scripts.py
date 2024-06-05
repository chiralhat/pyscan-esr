import sys
sys.path.append('../')
import spinecho_scripts as ses
import pyscan as ps
import numpy as np
from time import sleep
from IPython.display import display, clear_output


def single_shot(sig, parameters, devices, output, fig):
    devices.scope.read_vxy(d=sig)
    for ax in fig.axes:
        ax.remove()
    ax = fig.add_subplot(111)
    freq = devices.synth.c_freqs
    fit, err = ps.plot_exp_fit_norange(np.array([sig.time*1e6, sig.xsub]),
                                       freq, 1, plt=ax)
    sig.fit = fit
    fitstr = f'A={fit[1]:.3g} V, t={fit[2]:.3g} μs, Q={fit[2]*np.pi*freq/1e6:.3g}'
    fourstr = f'famp: v1={sig.v1famp:.3g}, v2={sig.v2famp:.3g}'
    fourfstr = f'ffreq (MHz): v1={sig.ffdet/1e6:.3g}, v2={sig.ffdet2/1e6:.3g}'
    freqstr = f'freq (MHz): {freq/1e6}'
    ax.set_xlabel('Time (μs)')
    ax.set_ylabel('Voltage (V)')
    xpt = sig.time[len(sig.time)//5]*1e6
    ypt = sig.xsub.max()*np.array([0.75, 0.65, 0.55, 0.85])
    ax.text(xpt, ypt[0], fitstr)
    ax.text(xpt, ypt[1], fourstr)
    ax.text(xpt, ypt[2], fourfstr)
    ax.text(xpt, ypt[3], freqstr)
    with output:
        clear_output(wait=True)
        display(ax.figure)


def read_wait(devices, parameters):
    ave = devices.scope.average
    if ave > 1:
        period = parameters['period']/1e9
        devices.scope.average = 1
        sleep(0.1)
        devices.scope.average = ave
        sleep(period*ave*2)

    return devices.scope.read_vxy()

        
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
    
    if runinfo._indicies[0]==(runinfo._dims[0]-1):
        if runinfo.parameters['turn_off']:
            devices.synth.power_off()
            devices.psu.output = False
    
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

    if runinfo._indicies[0]==(runinfo._dims[0]-1):
        if runinfo.parameters['turn_off']:
            devices.synth.power_off()
            devices.psu.output = False
    
    return d


def decay_field_sweep(expt):
    runinfo = expt.runinfo
    devices = expt.devices

    sltime = runinfo.parameters['sltime'] or runinfo.parameters['period']/1e9*2*devices.scope.average
    if 'reps' in runinfo.parameters.keys():
        reps = runinfo.parameters.reps
    else:
        reps = 1
    
    sleep(sltime)
    d = devices.scope.read_vxy(sltime=sltime, reps=reps)
    expt.t = d.time
    d.fit, d.err = exp_fit_norange_noback(np.array([d.time-d.time[0], d.xsub]),
                                             parameters['freq_start'], 1)[:2]
    d.Q = d.fit[-1]
    d.A = d.fit[0]

    if runinfo._indicies[0]==(runinfo._dims[0]-1):
        if runinfo.parameters['turn_off']:
            devices.synth.power_off()
            devices.psu.output = False
    
    return d


def setup_experiment(parameters, devices, sweep):
    expt_select = {'Freq Sweep': 0,
                   'Field Sweep': 1}
    wait = parameters['wait']
    sweep_range = ps.drange(parameters['sweep_start'],
                            parameters['sweep_step'],
                            parameters['sweep_end'])
    setup_vars = {'y_name': ['synth_c_freqs',
                            'psu_field'],
                 'loop': [ps.PropertyScan({'synth': sweep_range}, prop='c_freqs', dt=wait),
                              ps.PropertyScan({'psu': sweep_range}, prop='field', dt=wait)],
                  'file': ['PulseFreqSweep',
                           'PulseBSweep'],
                  'function': [decay_freq_sweep,
                               decay_field_sweep]
                  }
    run_n = expt_select[parameters['psexpt']]
    parameters['y_name'] = setup_vars['y_name'][run_n]
    fname = setup_vars['file'][run_n]
    runinfo = ps.RunInfo()
    runinfo.loop0 = setup_vars['loop'][run_n]
    runinfo.measure_function = setup_vars['function'][run_n]

    runinfo.parameters = parameters
    runinfo.wait_time = 0.1
    
    # expt = ps.Sweep(runinfo, devices, parameters['outfile']+fname)
    # sweep['expt'] = expt
    sweep['name'] = parameters['outfile']+fname
    sweep['runinfo'] = runinfo
