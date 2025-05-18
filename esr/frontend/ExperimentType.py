"""
experiment_type.py

This module defines the ExperimentType class, which handles the backend logic, parameter management, 
hardware setup, and data flow for Spin Echo and Pulse Frequency Sweep experiments. 
It manages experiment settings, initializes devices (e.g., RFSoC, PSU, temperature controller), 
generates default save files, controls sweeps, and connects to real-time graphing widgets.

Dependencies:
- Custom experiment setup scripts (spinecho_scripts.py, pulsesweep_scripts.py)
- PyScan backend for hardware control
- PyQt5 for signal handling and graphical elements
- GraphWidget and SweepPlotWidget from graphing.py for live visualization
"""

#import spinecho_scripts
#import pulsesweep_scripts
#import pyscan as ps
from graphing import *
from datetime import date
import pickle
from time import sleep, time
import requests
from Worker import PyscanObject

import globals

from PyQt5.QtCore import QObject, pyqtSignal

import sys, os
sys.path.append('../')
#from rfsoc2 import *

from pathlib import Path

class ExperimentType(QObject):
    """Handles backend logic, configuration, and hardware interaction for a specific experiment type.
    This class manages the lifecycle of an experiment (e.g., Spin Echo, Pulse Frequency Sweep),
    including setting parameters, initializing hardware, running sweeps, and reading results."""
    plot_update_signal = pyqtSignal()  
    def __init__(self, exp_type):
        super().__init__()
        self.type = exp_type 

        
        self.parameters = {} 
        self.sweep = {} 
        self.expt = None

        if self.type == "Spin Echo":
            self.default_file = "se_defaults.pkl" 
        elif self.type == "Pulse Frequency Sweep":
            self.default_file = "ps_defaults.pkl" 
            
        self.read_unprocessed_graph = GraphWidget() 
        self.read_processed_graph = GraphWidget()
        self.sweep_graph_2D= SweepPlotWidget()
        self.sweep_graph_1D= SweepPlotWidget()

        self.spinecho_gui = None

    def set_parameters(self, parameters):
        """Takes in parameters read from the settings panel in the UI, 
        copies them into the parameters dictionary, and then modifies them slightly
        so they are ready for the experiment
        
        @param parameters -- dictionary of settings used to configure the experiment taken from EXPERIMENT_TEMPLATES"""
        print("Setting Parameters")
        self.parameters = parameters

        try:
            if 'ave_reps' in self.parameters.keys():
                reps = self.parameters['ave_reps']
            else:
                reps = 1
            if 'period' in self.parameters.keys():
                period = self.parameters['period']
            else:
                period = 500
            tmult = period / 1e6 * 4 * reps
            self.parameters['subtime'] = self.parameters['soft_avgs'] * tmult
            datestr = date.today().strftime('%y%m%d')
            fname = datestr + str(self.parameters['file_name']) + '_'
            self.parameters['outfile'] = str(Path(self.parameters['save_dir']) / fname)

            with open(self.default_file, 'wb') as f:
                pickle.dump(self.parameters, f)
            data = {
                "parameters": self.parameters,
                "sweep": self.sweep,
                "experiment type": self.type
            }

            print("about to send parameters to the server")
            response = requests.post(globals.server_address + "/initialize_experiment", json=data)
            print("parameters sent to server")
            print()
            if response.ok:
                response_data = response.json()
                self.parameters = response_data.get('parameters')
            else:
                print("Error:", response.status_code, response.text)
        except Exception as e:
            print("error in set_parameters:")
            print(e)
          
    def hardware_off(self):
        """
        turns off the hardware 
        """
        if 'expt' in self.sweep.keys():
            self.sweep['expt'].runinfo.running = False
        if self.parameters['use_psu']:
            self.devices.psu.output = False
