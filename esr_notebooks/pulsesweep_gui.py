import numpy as np
from PyQt5.QtWidgets import QApplication
from pulsesweep_scripts import *  # Your experimental logic
import pyscan as ps

class PulseSweepExperiment:

    def __init__(self, canvas_widget):
        """
        Initialize with a reference to the CanvasWidget.
        """
        self.canvas_widget = canvas_widget
        self.time_data = []
        self.x_data = []

    def init_experiment(self, devices, parameters, sweep, soc):
        """
        Initialize experiment parameters and devices.
        """
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

    def read_processed(self, sig, config, soc):
        """
        Run a single decay experiment and plot the result with exponential fit.
        """
        prog = CPMGProgram(soc, config)
        measure_decay(prog, soc, sig)
        freq = config['freq']
        sig.freq = freq

        # Fit the decay and annotate
        ax = self.canvas_widget.figure.add_subplot(111)
        fit, err = ps.plot_exp_fit_norange(np.array([sig.time, sig.x]), freq, 1, plt=ax)
        sig.fit = fit

        # Update plot with fitting overlay
        #self.canvas_widget.update_canvas(sig, fit=fit, freq=freq)

        #QApplication.processEvents()

    def read_unprocessed(self, sig, config, soc):
        """
        Run one measurement and plot just the raw data (no fit).
        """
        config['single'] = True
        config['soft_avgs'] = 1
        prog = CPMGProgram(soc, config)
        measure_phase(prog, soc, sig)
        sig.fit = None
        sig.freq = None
        #self.canvas_widget.update_canvas(sig)
        #QApplication.processEvents()

    # def update_plot(self, sig, fit=None, freq=None):
    #     """
    #     Update canvas plot: raw or with fitted curve.
    #     """
    #     self.time_data.append(sig.time)
    #     self.x_data.append(sig.x)

    #     time = np.concatenate(self.time_data)
    #     x = np.concatenate(self.x_data)

    #     self.canvas_widget.update_canvas_psweep(time, x, fit=fit, freq=freq)

    def get_layout(self):
        """
        Optionally return a layout if this is being embedded.
        """
        return self.canvas_widget.layout()