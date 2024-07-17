import sys
sys.path.append('../')
import pyscan as ps
import matplotlib.pyplot as plt
from IPython.display import display, clear_output
from spinecho_scripts import *
import gui_setup as gs

# Set up the plots to be pretty
plt.rc('lines', lw=2)
plotfont = {'family': 'serif', 'size': 16}
plt.rc('font', **plotfont)
plt.rc('mathtext', fontset='cm')

function_select = {'Phase': subback_phase,
                   'Delay': subback_delay,
                   'Both': subback_phasedelay,
                       'None': subback_none}

default_file = 'se_defaults.pkl'

# These are all the controls to add for this GUI
secont_keys = {'devices': [['scope_address', 'fpga_address', 'synth_address'],
                           ['psu_address', 'use_psu']],
             'synth': [['freq', 'port', 'att'], ['power', 'power2', 'phase']],
             'fpga': [['delay', 'pulse1', 'mult'],
                      ['period', 'pre_att'],
                      ['nutation_delay', 'nutation_width'],
                      ['cpmg', 'pulse_block', 'block', 'phase_sub']],
             'scope': [['ave', 'scale', 'h_offset', 'tdiv']],
             'psu': [['field', 'gauss_amps', 'current_limit']],
#                     ['field_start', 'field_end', 'field_step']],
             'save': [['save_dir', 'file_name']],
             'measure': [['subtract', 'reps', 'expt'],
                         ['wait', 'sltime', 'int_start', 'int_end'],
                         ['sweep_start', 'sweep_end', 'sweep_step', 'init', 'turn_off']],
             }


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
    func = function_select[parameters['subtract']]
    ave = parameters['ave']
    phase = devices.synth.c2_phase#parameters['phase']
    reps = parameters['reps']
    delay = parameters['delay']
    delay2 = parameters['delay']
    port = parameters['port']
    sltime = parameters['sltime']
    lims = [-parameters['int_start'], parameters['int_end']]
    func(devices, ave=ave, phase=phase, reps=reps,
         delay=delay, delay2=delay2, d=sig, port=port, sltime=sltime, lims=lims)
    win = sig.win
    for ax in fig.axes:
        ax.remove()
    ax = fig.add_subplot(111)
    ax.plot(sig.time*1e6, sig.v1sub, color='yellow', label='CH1')
    ax.plot(sig.time*1e6, sig.v2sub, color='b', label='CH2')
    ax.plot(sig.time*1e6, sig.xsub, color='g', label='AMP')
    ax.set_xlabel('Time (μs)')
    ax.set_ylabel('Subtracted Signal (V)')
    [ax.axvline(x=w*1e6, color='purple', ls='--') for w in win]
    ax.legend()
    with output:
        clear_output(wait=True)
        display(ax.figure)


#    for ax in fig.axes:
#        ax.remove()
#    ax = fig.add_subplot(111)
#    ps.live_plot2D(sweep['expt'], x_name='t', y_name=parameters['y_name'], data_name='xsub', transpose=1)
    # with output:
    #     clear_output(wait=True)
    #     display(ax.figure)
        

def init_experiment(devices, parameters, sweep):
    parameters['pulse2'] = parameters['pulse1']*parameters['mult']
    chs = devices.scope.channels
    if len(chs)>2:
        [devices.scope.write('SEL:CH'+str(ch)+' 0') for ch in chs[2:]]
    devices.fpga.spin_echo(parameters)
    devices.synth.spin_echo(parameters)
    devices.scope.setup_spin_echo(parameters)
    if parameters['use_psu']:
        devices.psu.set_magnet(parameters)
    setup_experiment(parameters, devices, sweep)
    

spinecho_gui = gs.init_gui(secont_keys, init_experiment, default_file, 
    single_shot, gs.run_sweep, gs.read)
