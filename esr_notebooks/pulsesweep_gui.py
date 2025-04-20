import numpy as np
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QApplication
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from pulsesweep_scripts import *
import pyscan as ps


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

        print(sig)
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
            self.canvas_widget.update_canvas(time, i, q, x)
        else:
            self.canvas_widget.update_canvas(time, i, q, x)