import matplotlib.pyplot as plt
from IPython.display import display, clear_output
import gui_setup as gs
from pulsesweep_scripts import *

plt.rc('lines', lw=2)
plotfont = {'family': 'serif', 'size': 16}
plt.rc('font', **plotfont)
plt.rc('mathtext', fontset='cm')
default_file = 'ps_defaults.pkl'

# These are all the controls to add for this GUI
pscont_keys = {'devices': [['psu_address', 'use_psu', 'use_temp']],
                'rfsoc': [['freq', 'gain', 'period', 'loopback'],
                            ['pulse1_1','soft_avgs', 'h_offset', 'readout_length']],
             'psu': [['field', 'gauss_amps', 'current_limit']],
             'save': [['save_dir', 'file_name']],
             'measure': [['ave_reps', 'psexpt', 'wait'],
                         ['sweep_start', 'sweep_end', 'sweep_step'],
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
    config['single'] = True
    config['soft_avgs'] = 1
    #prog = CPMGProgram(soc, config)
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


# I need to set up a new way of measuring, using the phase-based subtraction,
# which might do a better job of showing what is actually coming from the resonator
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
    #prog = CPMGProgram(soc, config)
    measure_decay(config, soc, sig)
    freq = config['freq']
    
    for ax in fig.axes:
        ax.remove()
    ax = fig.add_subplot(111)
    fit, err = ps.plot_exp_fit_norange(np.array([sig.time, sig.x]),
                                       freq, 1, plt=ax)
    sig.fit = fit
    fitstr = f'A={fit[1]:.3g} V, t={fit[2]:.3g} μs, Q={fit[-1]:.3g}'
    freqstr = f'freq (MHz): {freq}'
    ax.set_xlabel('Time (μs)')
    ax.set_ylabel('Signal (a.u.)')
    #[ax.axvline(x=w*1e6, color='purple', ls='--') for w in win]
    xpt = sig.time[len(sig.time)//5]
    ypt = sig.x.max()*np.array([0.75, 0.65])
    ax.text(xpt, ypt[0], fitstr)
    ax.text(xpt, ypt[1], freqstr)
    with output:
        clear_output(wait=True)
        display(ax.figure)
        

def init_experiment(devices, parameters, sweep, soc):
    parameters['single'] = True
    parameters['pulses'] = 0
    parameters['pulse1_2'] = parameters['pulse1_1']
    parameters['pi2_phase'] = 0
    parameters['pi_phase'] = 90
    parameters['delay'] = 300
    parameters['cpmg_phase'] = 0
    channel = 1 if parameters['loopback'] else 0
    parameters['res_ch'] = channel
    parameters['ro_chs'] = [channel]
    parameters['nutation_delay'] = 5000
    parameters['nutation_length'] = 0
    parameters['reps'] = 1
    parameters['sweep2'] = 0
    if parameters['use_psu']:
        devices.psu.set_magnet(parameters)
    setup_experiment(parameters, devices, sweep, soc)


pulsesweep_gui = gs.init_gui(pscont_keys, init_experiment, default_file, 
    single_shot, gs.run_sweep, read)
