import matplotlib.pyplot as plt
from IPython.display import display, clear_output
from esr.backend.spinecho_scripts import *
import gui_setup as gs

# Set up the plots to be pretty
plt.rc('lines', lw=2)
plotfont = {'family': 'serif', 'size': 16}
plt.rc('font', **plotfont)
plt.rc('mathtext', fontset='cm')

# function_select = {'Phase': subback_phase,
#                    'Delay': subback_delay,
#                    'Both': subback_phasedelay,
#                        'None': subback_none,
#                        'Autophase': subback_autophase}

default_file = 'se_defaults.pkl'

# These are all the controls to add for this GUI
secont_keys = {'devices': [['use_psu', 'use_temp']],
                'rfsoc': [['freq', 'gain', 'period'],
                            ['delay', 'pulse1_1', 'mult1'],
                            ['nutation_delay', 'nutation_length'],
                            ['soft_avgs', 'h_offset', 'readout_length'],
                            ['phase', 'pulses', 'loopback']],
             'psu': [['field', 'gauss_amps', 'current_limit']],
             'save': [['save_dir', 'file_name']],
             'measure': [['ave_reps', 'wait', 'sweep2'],
                         ['expt', 'sweep_start', 'sweep_end', 'sweep_step'],
                         ['expt2', 'sweep2_start', 'sweep2_end', 'sweep2_step'],
                         ['integrate', 'init', 'turn_off']],
             }


def read(sig, config, soc, output, fig):
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
    single = config['single']
    avgs = config['soft_avgs']
    config['single'] = True
    config['soft_avgs'] = 1
    measure_phase(config, soc, sig)
    
    for ax in fig.axes:
        ax.remove()
    ax = fig.add_subplot(111)
    ax.plot(sig.time, sig.i, color='yellow', label='CH1')
    ax.plot(sig.time, sig.q, color='b', label='CH2')
    ax.plot(sig.time, sig.x, color='g', label='AMP')
    ax.set_xlabel('Time (μs)')
    ax.set_ylabel('Signal (a.u.)')
    #[ax.axvline(x=w*1e6, color='purple', ls='--') for w in win]
    ax.legend()
    with output:
        clear_output(wait=True)
        display(ax.figure)
    config['single'] = single
    config['soft_avgs'] = avgs


def single_shot(sig, config, soc, output, fig):
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
    single = config['single']
    config['single'] = config['loopback']
    measure_phase(config, soc, sig)
    
    for ax in fig.axes:
        ax.remove()
    ax = fig.add_subplot(111)
    ax.plot(sig.time, sig.i, color='yellow', label='CH1')
    ax.plot(sig.time, sig.q, color='b', label='CH2')
    ax.plot(sig.time, sig.x, color='g', label='AMP')
    ax.set_xlabel('Time (μs)')
    ax.set_ylabel('Signal (a.u.)')
    #[ax.axvline(x=w*1e6, color='purple', ls='--') for w in win]
    ax.legend()
    with output:
        clear_output(wait=True)
        display(ax.figure)
    config['single'] = single
        

def init_experiment(devices, parameters, sweep, soc):
    parameters['pulse1_2'] = parameters['pulse1_1']*parameters['mult1']
    parameters['pi2_phase'] = 0
    parameters['pi_phase'] = 90
    parameters['cpmg_phase'] = 0
    channel = 1 if parameters['loopback'] else 0
    parameters['res_ch'] = channel
    parameters['ro_chs'] = [channel]
    parameters['reps'] = 1
    parameters['single'] = parameters['loopback']
    if parameters['use_psu'] and not parameters['loopback']:
        devices.psu.set_magnet(parameters)
    setup_experiment(parameters, devices, sweep, soc)
    

spinecho_gui = gs.init_gui(secont_keys, init_experiment, default_file, 
    single_shot, gs.run_sweep, read)
