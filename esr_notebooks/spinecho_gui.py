import numpy as np
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QApplication
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
        QApplication.processEvents()

        config['single'] = single
        config['soft_avgs'] = avgs

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