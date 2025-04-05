import matplotlib.pyplot as plt
from IPython.display import display, clear_output
import gui_setup as gs
from pulsesweep_scripts import *

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

import matplotlib.pyplot as plt
from IPython.display import display, clear_output
import gui_setup as gs
from pulsesweep_scripts import *

import numpy as np
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from pulsesweep_scripts import *
import gui_setup as gs
import pyscan as ps


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


class PulseSweepExperiment:
    def __init__(self, canvas_widget):
        self.canvas_widget = canvas_widget
        self.ax = self.canvas_widget.ax
        self.time_data = []
        self.i_data = []
        self.q_data = []
        self.x_data = []

    def init_experiment(self, devices, parameters, sweep, soc):
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

    def read_unprocessed(self, sig, config, soc):
        config['single'] = True
        config['soft_avgs'] = 1
        prog = CPMGProgram(soc, config)
        measure_phase(prog, soc, sig)
        self.update_plot(sig)

    def read_processed(self, sig, config, soc):
        prog = CPMGProgram(soc, config)
        measure_decay(prog, soc, sig)
        self.update_plot(sig, show_fit=True, freq=config['freq'])

    def update_plot(self, sig, show_fit=False, freq=None):
        self.time_data = [sig.time]
        self.i_data = [sig.i]
        self.q_data = [sig.q]
        self.x_data = [sig.x]

        time = np.concatenate(self.time_data)
        i = np.concatenate(self.i_data)
        q = np.concatenate(self.q_data)
        x = np.concatenate(self.x_data)

        if show_fit:
            fig = self.canvas_widget.figure
            fig.clear()
            ax = fig.add_subplot(111)
            fit, err = ps.plot_exp_fit_norange(np.array([sig.time, sig.x]), freq, 1, plt=ax)
            sig.fit = fit
            fitstr = f'A={fit[1]:.3g} V, t={fit[2]:.3g} μs, Q={fit[-1]:.3g}'
            freqstr = f'freq (MHz): {freq}'
            ax.text(sig.time[len(sig.time)//5] / 2, max(sig.x) * 0.75, fitstr)
            ax.text(sig.time[len(sig.time)//5] / 2, max(sig.x) * 0.65, freqstr)
            ax.set_xlabel('Time (μs)')
            ax.set_ylabel('Signal (a.u.)')
            ax.plot(sig.time, sig.i, label='CH1', color='yellow')
            ax.plot(sig.time, sig.q, label='CH2', color='blue')
            ax.plot(sig.time, sig.x, label='AMP', color='green')
            ax.legend()
            self.canvas_widget.canvas.draw()
        else:
            self.canvas_widget.update_canvas(time, i, q, x)

# Main window's CanvasWidget where the plot is drawn
class CanvasWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)

        # Layout for the graphing widget
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)

    def update_canvas(self, time, i, q, x):
        """
        Update the canvas with the given data.
        """
        # Clear the previous plot
        self.ax.clear()

        # Plot the data
        self.ax.plot(time, i, label='CH1', color='yellow')
        self.ax.plot(time, q, label='CH2', color='blue')
        self.ax.plot(time, x, label='AMP', color='green')

        # Set labels and title
        self.ax.set_xlabel('Time (μs)')
        self.ax.set_ylabel('Signal (a.u.)')
        self.ax.legend()

        # Refresh the canvas to show the updated plot
        self.canvas.draw()

# def read_unprocessed(sig, config, soc, fig):
#     """
#     Take and plot a single background-subtracted measurement.

#     Parameters
#     ----------
#     sig : pyscan ItemAttribute
#         Signal object for accessing the data. Updated by this function.
#     parameters : dict
#         Experimental parameters from the controls.
#     devices : pyscan ItemAttribute
#         Devices object for accessing the acquisition equipment.
#     output : ipyWidgets Output
#         Output window.
#     fig : pyplot Figure
#         Figure used to plot the data.

#     Returns
#     -------
#     None.

#     """
#     config['single'] = True
#     config['soft_avgs'] = 1
#     prog = CPMGProgram(soc, config)
#     measure_phase(prog, soc, sig)
    
#     for ax in fig.axes:
#         ax.remove()
#     ax = fig.add_subplot(111)
#     ax.plot(sig.time, sig.i, color='yellow', label='CH1')
#     ax.plot(sig.time, sig.q, color='b', label='CH2')
#     ax.plot(sig.time, sig.x, color='g', label='AMP')
#     ax.set_xlabel('Time (μs)')
#     ax.set_ylabel('Signal (a.u.)')
#     #[ax.axvline(x=w*1e6, color='purple', ls='--') for w in win]
#     ax.legend()
#     #OUTPUT: need to figure this part out
#     # with output:
#     #     clear_output(wait=True)
#     #     display(ax.figure)


# # I need to set up a new way of measuring, using the phase-based subtraction,
# # which might do a better job of showing what is actually coming from the resonator
# def read_processed(sig, config, soc, fig):
#     """
#     Take and plot a single background-subtracted measurement.

#     Parameters
#     ----------
#     sig : pyscan ItemAttribute
#         Signal object for accessing the data. Updated by this function.
#     parameters : dict
#         Experimental parameters from the controls.
#     devices : pyscan ItemAttribute
#         Devices object for accessing the acquisition equipment.
#     output : ipyWidgets Output
#         Output window.
#     fig : pyplot Figure
#         Figure used to plot the data.

#     Returns
#     -------
#     None.

#     """
#     prog = CPMGProgram(soc, config)
#     measure_decay(prog, soc, sig)
#     freq = config['freq']
    
#     for ax in fig.axes:
#         ax.remove()
#     ax = fig.add_subplot(111)
#     fit, err = ps.plot_exp_fit_norange(np.array([sig.time, sig.x]),
#                                        freq, 1, plt=ax)
#     sig.fit = fit
#     fitstr = f'A={fit[1]:.3g} V, t={fit[2]:.3g} μs, Q={fit[-1]:.3g}'
#     freqstr = f'freq (MHz): {freq}'
#     ax.set_xlabel('Time (μs)')
#     ax.set_ylabel('Signal (a.u.)')
#     #[ax.axvline(x=w*1e6, color='purple', ls='--') for w in win]
#     xpt = sig.time[len(sig.time)//5]/2
#     ypt = sig.x.max()*np.array([0.75, 0.65])
#     ax.text(xpt, ypt[0], fitstr)
#     ax.text(xpt, ypt[1], freqstr)
#     # OUTPUT: need to figure this poart out
#     # with output:
#     #     clear_output(wait=True)
#     #     display(ax.figure)
        

# def init_experiment(devices, parameters, sweep, soc):
#     parameters['pulses'] = 0
#     parameters['pulse1_2'] = parameters['pulse1_1']
#     parameters['pi2_phase'] = 0
#     parameters['pi_phase'] = 90
#     parameters['delay'] = 300
#     parameters['cpmg_phase'] = 0
#     channel = 1 if parameters['loopback'] else 0
#     parameters['res_ch'] = channel
#     parameters['ro_chs'] = [channel]
#     parameters['nutation_delay'] = 5000
#     parameters['nutation_length'] = 0
#     parameters['reps'] = 1
#     parameters['sweep2'] = 0
#     if parameters['use_psu']:
#         devices.psu.set_magnet(parameters)
#     setup_experiment(parameters, devices, sweep, soc)