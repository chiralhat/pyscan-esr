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

from PyQt5.QtCore import QObject, pyqtSignal

import sys, os
sys.path.append('../')
#from rfsoc2 import *

from pathlib import Path

class ExperimentType(QObject):
    """Handles backend logic, configuration, and hardware interaction for a specific experiment type.
    This class manages the lifecycle of an experiment (e.g., Spin Echo, Pulse Frequency Sweep),
    including setting parameters, initializing hardware, running sweeps, and reading results."""
    plot_update_signal = pyqtSignal()  # signal with no arguments
    def __init__(self, exp_type):
        super().__init__()
        self.type = exp_type #The name of the experiment type (e.g., 'Spin Echo'). NONE by default
        
        #harware releated:
        #self.soc = QickSoc() #Hardware interface for the RFSoC system.
        # self.soccfg = self.soc #Alias for soc, used for compatibility.
        # self.devices = ps.ItemAttribute() #Container for hardware components (e.g., PSU, temperature controller).
        # self.sig = ps.ItemAttribute() #Container for storing acquired signal data.
        
        self.parameters = {} #Settings used to configure the experiment (input).
        self.sweep = {} #Stores sweep-related objects and state (output).

        #for saving the parameters you entered into the settings panel
        if self.type == "Spin Echo":
            self.default_file = "se_defaults.pkl" #Default filename used for storing results from se experiments
        elif self.type == "Pulse Frequency Sweep":
            self.default_file = "ps_defaults.pkl" #Default filename used for storing results from ps experiments
            
        # NEW current experiment graph
        self.read_unprocessed_graph = GraphWidget() #Widget used for plotting experiment results in the graph panel of the UI.
        self.read_processed_graph = GraphWidget()
        self.sweep_graph_2D= SweepPlotWidget()
        self.sweep_graph_1D= SweepPlotWidget()

        #Experiment objects that will be initialized later in self.init_pyscan_experiment
        self.spinecho_gui = None

    def set_parameters(self, parameters):
        """Takes in parameters read from the settings panel in the UI, 
        copies them into the parameters dictionary, and then modifies them slightly
        so they are ready for the experiment
        
        @param parameters -- dictionary of settings used to configure the experiment taken from EXPERIMENT_TEMPLATES"""
        print("setting Parameters")
        self.parameters = parameters

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

        # Save parameters to default file
        with open(self.default_file, 'wb') as f:
            pickle.dump(self.parameters, f)
        print(self.parameters)
        print()
        print(self.sweep)
        print()
        print(self.type)
        data = {
            "parameters": self.parameters,
            "sweep": self.sweep,
            "experiment type": self.type
        }
        print("about to ask server!")
        response = requests.post("http://150.209.47.102:5000/initialize_experiment", json=data)
        print("asked server")
        if response.ok:
            print("1")
            response_data = response.json()
            print("2")
            self.parameters = response_data.get('parameters')
            print("3")
            print("4")
        else:
            print("Error:", response.status_code, response.text)
        print(response.json())

    
    # def start_sweep(self):
    #     """starts up the hardware to run a sweep and runs a sweep"""
    #     self.set_parameters(self.parameters)
    #     self.sweep_running = True
    #     runinfo = self.sweep['runinfo']
    #     expt = ps.Sweep(runinfo, self.devices, self.sweep['name'])
    #     self.sweep['expt'] = expt

    #     if self.type == "Spin Echo":  
    #         if self.parameters['expt']=="Hahn Echo":
    #             self.sweep['expt'].echo_delay = 2*np.array(runinfo.scan0.scan_dict['delay_sweep'])*runinfo.parameters['pulses']
    #         elif self.parameters['expt']=="CPMG":
    #             self.sweep['expt'].echo_delay = 2*runinfo.parameters['delay']*runinfo.scan0.scan_dict['cpmg_sweep']
    #         elif self.parameters['sweep2'] and self.parameters['expt2']=="Hahn Echo":
    #             self.sweep['expt'].echo_delay = 2*runinfo.scan1.scan_dict['delay_sweep']*runinfo.parameters['pulses']
    #         elif self.parameters['sweep2'] and self.parameters['expt2']=="CPMG":
    #             self.sweep['expt'].echo_delay = 2*runinfo.parameters['delay']*runinfo.scan1.scan_dict['cpmg_sweep']
    #         else:
    #             self.sweep['expt'].echo_delay = 2*runinfo.parameters['delay']*runinfo.parameters['pulses']

    #     self.sweep['expt'].start_time = time()
    #     self.sweep['expt'].start_thread()

          
    def hardware_off(self):
        """
        turns off the hardware 
        """
        if 'expt' in self.sweep.keys():
            self.sweep['expt'].runinfo.running = False
        if self.parameters['use_psu']:
            self.devices.psu.output = False
