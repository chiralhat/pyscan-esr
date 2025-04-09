import numpy as np
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from spinecho_scripts import *  # Assuming this contains relevant functions like CPMGProgram, measure_phase
import gui_setup as gs

class SpinechoExperiment:
    def __init__(self, canvas_widget):
        """
        Initialize with a reference to the CanvasWidget.
        """
        # Store the reference to the CanvasWidget for later updates
        self.canvas_widget = canvas_widget
        self.time_data = []
        self.i_data = []
        self.q_data = []
        self.x_data = []

    def init_experiment(self, devices, parameters, sweep, soc):
        """
        Initialize the experiment by setting up the parameters and devices.
        """
        parameters['pulse1_2'] = parameters['pulse1_1'] * parameters['mult1']
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
        
        setup_experiment(parameters, devices, sweep, soc) #From spinecho_scripts.py

    def read_unprocessed(self, sig, config, soc):
#TO DO: THIS IS HAVING ISSUES WITH A PARAMETER THAT IS A FLOAT AND NEEDS TO BE AN INT
        """
        Take and plot a single background-subtracted measurement (unprocessed).
        """
        single = config['single']
        avgs = config['soft_avgs']
        config['single'] = True
        config['soft_avgs'] = 1
        prog = CPMGProgram(soc, config)
        measure_phase(prog, soc, sig)

        # Update data for plotting
        self.update_plot(sig)

        config['single'] = single
        config['soft_avgs'] = avgs
        # """
        # Simulate an experiment and update the plot with fake data.
        # """
        # # Generate fake signal data
        # time = np.linspace(0, 10, 200)
        # i = np.sin(time)
        # q = np.cos(time)
        # x = np.sqrt(i**2 + q**2)

        # # Create a fake signal-like object
        # class FakeSignal:
        #     pass

        # fake_sig = FakeSignal()
        # fake_sig.time = time
        # fake_sig.i = i
        # fake_sig.q = q
        # fake_sig.x = x

        # # Update the plot with the fake signal
        # self.update_plot(fake_sig)

    def read_processed(self, sig, config, soc):
        """
        Take and plot a single background-subtracted measurement (processed).
        """
        single = config['single']
        config['single'] = config['loopback']
        prog = CPMGProgram(soc, config)
        measure_phase(prog, soc, sig)

        # Update data for plotting
        self.update_plot(sig)

        config['single'] = single

    def update_plot(self, sig):
        """
        Update the plot with the data from the experiment.
        """
        # Append new data from the current experiment
        self.time_data.append(sig.time)
        self.i_data.append(sig.i)
        self.q_data.append(sig.q)
        self.x_data.append(sig.x)

        # Flatten the lists for plotting
        time = np.concatenate(self.time_data)
        i = np.concatenate(self.i_data)
        q = np.concatenate(self.q_data)
        x = np.concatenate(self.x_data)

        # Update the canvas with the new data
        self.canvas_widget.update_canvas(time, i, q, x)

    def get_layout(self):
        """
        Return the layout for the widget to be added to the PyQt window.
        """
        return self.layout


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




# import matplotlib.pyplot as plt
# from IPython.display import display, clear_output
# from spinecho_scripts import *
# import gui_setup as gs

# # function_select = {'Phase': subback_phase,
# #                    'Delay': subback_delay,
# #                    'Both': subback_phasedelay,
# #                        'None': subback_none,
# #                        'Autophase': subback_autophase}

# # These are all the controls to add for this GUI
# secont_keys = {'devices': [['psu_address', 'use_psu', 'use_temp']],
#                 'rfsoc': [['freq', 'gain', 'period'],
#                             ['delay', 'pulse1_1', 'mult1'],
#                             ['nutation_delay', 'nutation_length'],
#                             ['soft_avgs', 'h_offset', 'readout_length'],
#                             ['phase', 'pulses', 'loopback']],
#              'psu': [['field', 'gauss_amps', 'current_limit']],
#              'save': [['save_dir', 'file_name']],
#              'measure': [['ave_reps', 'wait', 'sweep2'],
#                          ['expt', 'sweep_start', 'sweep_end', 'sweep_step'],
#                          ['expt2', 'sweep2_start', 'sweep2_end', 'sweep2_step'],
#                          ['integrate', 'init', 'turn_off']],
#              }


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
#     single = config['single']
#     avgs = config['soft_avgs']
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
#     # OUTPUT: need to figure this part out
#     # with output:
#     #     clear_output(wait=True)
#     #     display(ax.figure)
#     config['single'] = single
#     config['soft_avgs'] = avgs


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
#     single = config['single']
#     config['single'] = config['loopback']
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
#     config['single'] = single
        

# def init_experiment(devices, parameters, sweep, soc):
#     parameters['pulse1_2'] = parameters['pulse1_1']*parameters['mult1']
#     parameters['pi2_phase'] = 0
#     parameters['pi_phase'] = 90
#     parameters['cpmg_phase'] = 0
#     channel = 1 if parameters['loopback'] else 0
#     parameters['res_ch'] = channel
#     parameters['ro_chs'] = [channel]
#     parameters['reps'] = 1
#     parameters['single'] = parameters['loopback']
#     if parameters['use_psu'] and not parameters['loopback']:
#         devices.psu.set_magnet(parameters)
#     setup_experiment(parameters, devices, sweep, soc)