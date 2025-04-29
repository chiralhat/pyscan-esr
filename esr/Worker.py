"""
worker.py

This module defines the Worker class, which manages the execution of experiment tasks
(reading data, running sweeps) in a separate thread to keep the GUI responsive.

Key responsibilities:
- Run "read_processed" and "read_unprocessed" tasks in the background
- Manage live sweeping of experiments with real-time plot updates
- Emit signals to update status messages and graphs without freezing the UI
- Handle start, update, and stop requests during experiment runs

Dependencies:
- PyQt5 for threading (QThread, QObject, pyqtSignal, pyqtSlot)
- NumPy for efficient array comparisons
- pyscan.py for hardware interaction and plotting utilities
"""

import matplotlib
matplotlib.use('Qt5Agg')  # Must be done before importing pyplot!
# Do not move the above from the top of the file
                             
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

import sys
sys.path.append('../')
from rfsoc2 import *
import numpy as np
from time import sleep
import pyscan as ps


class Worker(QObject):
    """
    A generic worker that runs one of three tasks in a separate thread:
      - read_processed
      - read_unprocessed
      - start_sweep
    We pass in the current_experiment and which task we want to run.
    """

    finished = pyqtSignal()         # Signal emitted when the worker is completely done
    updateStatus = pyqtSignal(str)  # Emit messages that the main thread can display
    plot_update_signal = pyqtSignal(object)  # to pass colormesh
    dataReady_se = pyqtSignal(object, object)
    dataReady_ps = pyqtSignal(object, object)
    live_plot_2D_update_signal = pyqtSignal(object)   
    live_plot_1D_update_signal = pyqtSignal(object)   


    def __init__(self, experiment, task_name):
        super().__init__()
        self.experiment = experiment
        self.task_name = task_name
        self.stop_requested = False  

    @pyqtSlot()
    def run_snapshot(self):
        """
        Runs the desired method on the experiment in this separate thread
        so the main GUI thread won't freeze.
        """

        if self.task_name == "read_processed":
            self.updateStatus.emit("Reading processed data...\n")

            if self.experiment.type == "Spin Echo":
                single = self.experiment.parameters['single']
                self.experiment.parameters['single'] = self.experiment.parameters['loopback']
                prog = CPMGProgram(self.experiment.soc, self.experiment.parameters)
                measure_phase(prog, self.experiment.soc, self.experiment.sig)
                self.experiment.parameters['single'] = single

            elif self.experiment.type == "Pulse Frequency Sweep":
                self.experiment.parameters['single'] = True
                prog = CPMGProgram(self.experiment.soc, self.experiment.parameters)
                measure_decay(prog, self.experiment.soc, self.experiment.sig)
                freq = self.experiment.parameters['freq']
                self.experiment.sig.freq = freq
            self.updateStatus.emit("Done reading processed data.\n")

        elif self.task_name == "read_unprocessed":
            self.updateStatus.emit("Reading unprocessed data...\n")

            if self.experiment.type == "Spin Echo":
                single = self.experiment.parameters['single']
                avgs = self.experiment.parameters['soft_avgs']
                self.experiment.parameters['single'] = True
                self.experiment.parameters['soft_avgs'] = 1
                prog = CPMGProgram(self.experiment.soc, self.experiment.parameters)
                measure_phase(prog, self.experiment.soc, self.experiment.sig)
                self.experiment.parameters['single'] = single
                self.experiment.parameters['soft_avgs'] = avgs
            
            elif self.experiment.type == "Pulse Frequency Sweep":
                self.experiment.parameters['single'] = True
                self.experiment.parameters['soft_avgs'] = 1
                prog = CPMGProgram(self.experiment.soc, self.experiment.parameters)
                measure_phase(prog, self.experiment.soc, self.experiment.sig)

            self.updateStatus.emit("Done reading unprocessed data.\n")

        if self.experiment.type == "Spin Echo":
            self.dataReady_se.emit(self.experiment.sig, self.task_name)
        elif self.experiment.type == "Pulse Frequency Sweep":
            self.dataReady_ps.emit(self.experiment.sig, self.task_name)

        self.finished.emit()

        
    @pyqtSlot()
    def run_sweep(self):
        self.updateStatus.emit("Starting sweep in worker thread…\n")
        self.stop_requested = False
        self.running = True

        # kick off the hardware sweep
        self.experiment.start_sweep()
        expt = self.experiment.sweep['expt']

        # locals to hold the last arrays
        last_data_2d = None
        last_data_1d = None

        while not self.stop_requested and self.running:
            if not expt.runinfo.running:
                self.running = False
                break

            if expt.runinfo.measured:
                try:
                    # build new PlotGenerators
                    pg_2D = ps.PlotGenerator(
                        expt=expt, d=2,
                        x_name='t',
                        y_name=self.experiment.parameters['y_name'],
                        data_name=self.experiment.parameters['2D Sweep variable'],
                        transpose=1
                    )
                    pg_1D = ps.PlotGenerator(
                        expt=expt, d=1,
                        x_name=self.experiment.parameters['y_name'],
                        data_name=self.experiment.parameters['1D Sweep variable'],
                    )

                    # compare & emit 2D only on change
                    if last_data_2d is None or not np.array_equal(pg_2D.data, last_data_2d):
                        last_data_2d = pg_2D.data.copy()
                        self.live_plot_2D_update_signal.emit(pg_2D)

                    # compare & emit 1D only on change
                    if last_data_1d is None or not np.array_equal(pg_1D.data, last_data_1d):
                        last_data_1d = pg_1D.data.copy()
                        self.live_plot_1D_update_signal.emit(pg_1D)

                except Exception as e:
                    self.updateStatus.emit(f"Error in update loop: {e}\n")

            sleep(1)

        # final draw on normal or early exit
        pg_2D = ps.PlotGenerator(
            expt=expt, d=2,
            x_name='t',
            y_name=self.experiment.parameters['y_name'],
            data_name=self.experiment.parameters['2D Sweep variable'],
            transpose=1
        )
        pg_1D = ps.PlotGenerator(
            expt=expt, d=1,
            x_name=self.experiment.parameters['y_name'],
            data_name=self.experiment.parameters['1D Sweep variable'],
        )
        self.live_plot_2D_update_signal.emit(pg_2D)
        self.live_plot_1D_update_signal.emit(pg_1D)

        if self.stop_requested:
            self.updateStatus.emit("Stop request detected. Exiting sweep early.\n")
        else:
            self.updateStatus.emit("Done sweeping (normal exit).\n")

        self.finished.emit()


    @pyqtSlot()
    def stop_sweep(self):
        """
        Slot to request the worker to stop. Sets a flag that can be checked in the run_sweep method, killing the thread.
        """
        pass
        # self.stop_requested = True
        # if 'expt' in self.experiment.sweep:
        #     self.experiment.sweep['expt'].runinfo.running = False