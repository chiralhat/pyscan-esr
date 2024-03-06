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


def v_to_s(ch1, ch2, out=0):
    if isinstance(out, int):
        out = ps.ItemAttribute()
    out.freq = ch1[0]
    i = ch1[1]#-ch1[1].min()+(ch1[1].max()-ch1[1].min())*.1
    q = ch2[1]
#     i = ch1[1]
    out.i = i
    out.q = q
#     q1 = v2-np.mean([v2.max(),v2.min()])
#     out.q = q1/q1.max()
#     i1 = v1-v1.min()
#     i2 = i1/i1.max()*0.95
#     out.i = i2+.05
#     out.s = out.i+1j*out.q
    out.x = np.sqrt(i**2 + q**2)
#     out.p = np.arctan(q/i)
#     out.p = np.arccos((i**2 - q**2) / (i**2 + q**2)) / 2
    
    return out


# def sweep_nosave(sig, parameters, devices, output, fig):
#     ch1 = devices.scope.measure_freq_sweep(parameters)
#     ch2 = devices.scope.measure_freq_sweep(parameters, channel=2)
#     v_to_s(ch1, ch2, sig)
#     for ax in fig.axes:
#         ax.remove()
#     sax = fig.add_subplot(212)
#     chax = fig.add_subplot(211, sharex=sax)
#     chax.plot(ch1[0], ch1[1], ch2[0], ch2[1])
#     sax.plot(sig.freq, sig.x)
# #     # ax.plot(ch1[0], ch1[1])
#     sax.set_xlabel('Frequency (MHz)')
#     sax.set_ylabel('Signal (a.u.)')
#     chax.set_ylabel('Signal (a.u.)')
#     with output:
#         clear_output(wait=True)
#         display(chax.figure)


def setup_experiment(parameters, devices, sweep):
    expt_select = {'Freq Sweep': 0}
    wait = parameters['wait']
    sweep_range = ps.drange(parameters['freq_start'],
                            parameters['freq_step'],
                            parameters['freq_end'])
    setup_vars = {'y_name': ['chfreq'],
                  'loop': [ps.FunctionScan(chfreq, sweep_range, dt=wait),]
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
