"""
ExperimentType.py

Defines the `ExperimentType` class, which encapsulates backend logic and state for Spin Echo or
Pulse Frequency Sweep experiments. Handles parameter parsing, hardware initialization, graph setup,
and communication with the backend server for initialization and control.

Key Interactions:
- Called by `gui.py` to manage experiment state.
- Sends requests to `server.py` for initializing experiments and starting sweeps.
- Uses `graphing.py` widgets for displaying real-time data.
- Works with `Worker.py` for threaded experiment control.
"""

from graphing import *
from datetime import date
import pickle
from time import sleep, time
import requests
from Worker import PyscanObject

import globals

from PyQt5.QtCore import QObject, pyqtSignal

import sys, os

sys.path.append("../")

from pathlib import Path


class ExperimentType(QObject):
    """Handles backend logic, configuration, and hardware interaction for a specific experiment type.
    This class manages the lifecycle of an experiment (e.g., Spin Echo, Pulse Frequency Sweep),
    including setting parameters, initializing hardware, running sweeps, and reading results.
    """

    # Signal emitted when data is ready to be plotted (used to notify GUI)
    plot_update_signal = pyqtSignal()

    def __init__(self, exp_type):
        super().__init__()
        self.type = exp_type  # Experiment type string

        # Parameter dictionaries to be populated by the UI or script
        self.parameters = {}
        self.sweep = {}
        self.expt = None  # Handle during sweep

        # Default parameter files for different experiment types
        if self.type == "Spin Echo":
            self.default_file = "se_defaults.pkl"
        elif self.type == "Pulse Frequency Sweep":
            self.default_file = "ps_defaults.pkl"

        # Initialize graphs for processed and unprocessed reads and sweeps
        self.read_unprocessed_graph = GraphWidget()
        self.read_processed_graph = GraphWidget()
        self.sweep_graph_2D = SweepPlotWidget()
        self.sweep_graph_1D = SweepPlotWidget()

        # Placeholder for a reference to the GUI
        self.spinecho_gui = None

    def set_parameters(self, parameters):
        """Takes in parameters read from the settings panel in the UI,
        copies them into the parameters dictionary, and then modifies them slightly
        so they are ready for the experiment

        @param parameters -- dictionary of settings used to configure the experiment taken from EXPERIMENT_TEMPLATES
        """
        print("Setting Parameters")
        self.parameters = parameters

        try:
            # Determine number of repetitions and period for timing calculations
            if "ave_reps" in self.parameters.keys():
                reps = self.parameters["ave_reps"]
            else:
                reps = 1
            if "period" in self.parameters.keys():
                period = self.parameters["period"]
            else:
                period = 500

            # Compute subtime for each acquisition
            tmult = period / 1e6 * 4 * reps
            self.parameters["subtime"] = self.parameters["soft_avgs"] * tmult

            # Build output file name with today's date
            datestr = date.today().strftime("%y%m%d")
            fname = datestr + str(self.parameters["file_name"]) + "_"
            self.parameters["outfile"] = str(Path(self.parameters["save_dir"]) / fname)

            # Save default parameters locally
            with open(self.default_file, "wb") as f:
                pickle.dump(self.parameters, f)

            # Package data to send to server for initialization
            data = {
                "parameters": self.parameters,
                "sweep": self.sweep,
                "experiment type": self.type,
            }

            print("about to send parameters to the server")
            response = requests.post(
                globals.server_address + "/initialize_experiment", json=data
            )
            print("parameters sent to server")
            print()
            # Update parameters based on server response
            if response.ok:
                response_data = response.json()
                self.parameters = response_data.get("parameters")
            else:
                print("Error:", response.status_code, response.text)
        except Exception as e:
            print("error in set_parameters:")
            print(e)

    def hardware_off(self):
        """
        turns off the hardware
        """
        # Stop experiment loop
        if "expt" in self.sweep.keys():
            self.sweep["expt"].runinfo.running = False

        # Turn off power supply unit if enabled
        if self.parameters["use_psu"]:
            self.devices.psu.output = False
