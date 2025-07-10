import sys
sys.path.append('../')
import pyscan as ps
import matplotlib.pyplot as plt
from IPython.display import display, clear_output
from twotone_spinecho_scripts import *
from spinecho_gui import *
import gui_setup as gs

plt.rc('lines', lw=2)
plotfont = {'family': 'serif', 'size': 16}
plt.rc('font', **plotfont)
plt.rc('mathtext', fontset='cm')
default_file = 'bse_defaults.pkl'

secont_keys['synth'][0] = ['freq1', 'freq2', 'att1', 'att2']
secont_keys['fpga'] = [['delay1', 'pulse1_1', 'mult1', 'period'],
                       ['delay2', 'pulse2_1', 'mult2', 'p2start', 'block'],
                       ['cpmg', 'pulse_block', 'nutation_delay', 'nutation_width']]
secont_keys['measure'] = [['subtract', 'reps', 'twotone_expt'],
                          ['wait', 'sltime', 'init', 'turn_off'],
                          ['int_start', 'int_end', 'int_start2', 'int_end2'],
                          ['sweep_start', 'sweep_end', 'sweep_step']]



def biread(sig, devices, output, fig):
    """
    Read the oscilloscope and plot it in the output window.

    Parameters
    ----------
    sig : pyscan ItemAttribute
        Signal object for accessing the scope data. Updated by this function.
    devices : pyscan ItemAttribute
        Devices object for accessing the acquisition equipment.
    output : ipyWidgets Output
        Output window.
    fig : pyplot Figure
        Figure used to plot the scope data.

    Returns
    -------
    None.

    """
    devices.scope.read_vxys(d=sig)
    for ax in fig.axes:
        ax.remove()
    ax = fig.add_subplot(111)
    ax.plot(sig.time*1e6, sig.volt1, color='yellow', label='CH1')
    ax.plot(sig.time*1e6, sig.volt2, color='b', label='CH2')
    ax.plot(sig.time*1e6, sig.x1, color='m', label='AMP1')
    ax.plot(sig.time*1e6, sig.volt3, color='r', label='CH3')
    ax.plot(sig.time*1e6, sig.volt4, color='g', label='CH4')
    ax.plot(sig.time*1e6, sig.x2, color='black', label='AMP2')
    ax.set_xlabel('Time (μs)')
    ax.set_ylabel('Subtracted Signal (V)')
    ax.legend(loc='upper right')
    with output:
        clear_output(wait=True)
        display(ax.figure)


def single_shot(sig, parameters, devices, output, fig):
    """
    Take and plot a single background-subtracted measurement.

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
    func = bifunction_select[parameters['subtract']]
    ave = parameters['ave']
    phase = devices.synth.c2_phase#parameters['phase']
    reps = parameters['reps']
    delay1 = parameters['delay1']
    delay2 = parameters['delay2']
    sltime = parameters['sltime']
    b_off = parameters['p2start']/1000
    lims = [[-parameters['int_start'], parameters['int_end']],
            [b_off-parameters['int_start2'], b_off+parameters['int_end2']]]
    func(devices, ave=ave, phase=phase, reps=reps, delay1=delay1,
         delay2=delay2, d=sig, sltime=sltime, lims=lims)
    win = sig.win
    for ax in fig.axes:
        ax.remove()
    ax = fig.add_subplot(111)
    ax.plot(sig.time*1e6, sig.v1sub, color='yellow', label='CH1')
    ax.plot(sig.time*1e6, sig.v2sub, color='b', label='CH2')
    ax.plot(sig.time*1e6, sig.x1sub, color='m', label='AMP1')
    ax.plot(sig.time*1e6, sig.v3sub, color='r', label='CH3')
    ax.plot(sig.time*1e6, sig.v4sub, color='g', label='CH4')
    ax.plot(sig.time*1e6, sig.x2sub, color='black', label='AMP2')
    ax.set_xlabel('Time (μs)')
    ax.set_ylabel('Subtracted Signal (V)')
    [ax.axvline(x=w*1e6, color='m', ls='--') for w in win[0]]
    [ax.axvline(x=w*1e6, color='black', ls='-.') for w in win[1]]
    ax.legend(loc='upper right')
    with output:
        clear_output(wait=True)
        display(ax.figure)


def init_experiment(devices, parameters, sweep):
    parameters['pulse1_2'] = parameters['pulse1_1']*parameters['mult1']
    parameters['pulse2_2'] = parameters['pulse2_1']*parameters['mult2']
    parameters['pulse1'] = parameters['pulse1_1']
    parameters['pulse2'] = parameters['pulse1_2']
    parameters['delay'] = parameters['delay1']

    nut_time = parameters['nutation_width']+parameters['nutation_delay']
    p1_time = parameters['pulse1_1']+(parameters['delay1']*2+parameters['pulse1_2'])*parameters['cpmg']
    p2_time = parameters['p2start']+parameters['pulse2_1']+(parameters['delay2']*2+parameters['pulse2_2'])*parameters['cpmg']
    switch_time = 500 + nut_time + p1_time
    # Turn on all the channels
    [devices.scope.write('SEL:CH'+str(ch)+' 1')
     for ch in devices.scope.channels[2:]]
    devices.fpga.bimodal_spin_echo(parameters)
    devices.synth.bimodal_spin_echo(parameters)
    devices.scope.setup_spin_echo(parameters)
    if parameters['use_psu']:
        devices.psu.set_magnet(parameters)
        devices.psu.set_switch_1pulse(switch_time)
    setup_twotone_experiment(parameters, devices, sweep)


twotone_spinecho_gui = gs.init_gui(secont_keys, init_experiment, default_file, 
    single_shot, gs.run_sweep, biread)
