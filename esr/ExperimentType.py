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

import spinecho_scripts
import pulsesweep_scripts
import pyscan as ps
from graphing import *
from datetime import date
import pickle
from time import sleep, time

from PyQt5.QtCore import QObject, pyqtSignal

import sys, os
sys.path.append('../')
from rfsoc2 import *


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
        self.soc = QickSoc() #Hardware interface for the RFSoC system.
        self.soccfg = self.soc #Alias for soc, used for compatibility.
        self.devices = ps.ItemAttribute() #Container for hardware components (e.g., PSU, temperature controller).
        self.sig = ps.ItemAttribute() #Container for storing acquired signal data.
        
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
        

    def init_pyscan_experiment(self):
        """This initializes a pyscan experiment with functions from the correct 
        experiment type scripts and GUI files."""
        if self.type == "Spin Echo":
           # Initialize the experiment by setting up the parameters and devices.
            self.parameters['pulse1_2'] = self.parameters['pulse1_1'] * self.parameters['mult1']
            self.parameters['pi2_phase'] = 0
            self.parameters['pi_phase'] = 90
            self.parameters['cpmg_phase'] = 0
            channel = 1 if self.parameters['loopback'] else 0
            self.parameters['res_ch'] = channel
            self.parameters['ro_chs'] = [channel]
            self.parameters['reps'] = 1
            self.parameters['single'] = self.parameters['loopback']
            
            if self.parameters['use_psu'] and not self.parameters['loopback']:
                self.devices.psu.set_magnet(self.parameters)
            
            spinecho_scripts.setup_experiment(self.parameters, self.devices, self.sweep, self.soc) #From ______scripts.py
            #self.spinecho_gui = seg.SpinechoExperiment(self.graph)
            #self.spinecho_gui.init_experiment(self.devices, self.parameters, self.sweep, self.soc)
        elif self.type == "Pulse Frequency Sweep":
            #self.pulsesweep_gui = psg.PulseSweepExperiment(self.graph)
            # Initialize experiment parameters and devices.
            self.parameters['pulses'] = 0
            self.parameters['pulse1_2'] = self.parameters['pulse1_1']
            self.parameters['pi2_phase'] = 0
            self.parameters['pi_phase'] = 90
            self.parameters['delay'] = 300
            self.parameters['cpmg_phase'] = 0
            channel = 1 if self.parameters['loopback'] else 0
            self.parameters['res_ch'] = channel
            self.parameters['ro_chs'] = [channel]
            self.parameters['nutation_delay'] = 5000
            self.parameters['nutation_length'] = 0
            self.parameters['reps'] = 1
            self.parameters['sweep2'] = 0
            self.parameters['single'] = self.parameters['loopback'] # ADDED THIS LINE
            if self.parameters['use_psu']:
                self.devices.psu.set_magnet(self.parameters)

            pulsesweep_scripts.setup_experiment(self.parameters, self.devices, self.sweep, self.soc)
            #self.pulsesweep_gui.init_experiment(self.devices, self.parameters, self.sweep, self.soc)

    def set_parameters(self, parameters):
        """Takes in parameters read from the settings panel in the UI, 
        copies them into the parameters dictionary, and then modifies them slightly
        so they are ready for the experiment
        
        @param parameters -- dictionary of settings used to configure the experiment taken from EXPERIMENT_TEMPLATES"""

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

        inst = ps.ItemAttribute()

        # Initialize PSU if necessary
        if not hasattr(self.devices, 'psu') and self.parameters['use_psu']:
            psu_address = self.parameters.get('psu_address', '').strip()
            if psu_address:
                waddr = psu_address.split('ASRL')[-1].split('::')[0]
                try:
                    self.devices.psu = ps.GPD3303S(waddr)
                except Exception as e:
                    print(f"Error initializing PSU: {e}")
            else:
                print("Error: PSU address is not provided or invalid.")

        # Initialize temperature device if necessary
        if not hasattr(self.devices, 'ls335') and self.parameters['use_temp']:
            self.devices.ls335 = ps.Lakeshore335()
            temp = self.devices.ls335.get_temp()

        self.init_pyscan_experiment()

    
    def start_sweep(self):
        """starts up the hardware to run a sweep and runs a sweep"""
        self.set_parameters(self.parameters)
        self.sweep_running = True
        runinfo = self.sweep['runinfo']
        expt = ps.Sweep(runinfo, self.devices, self.sweep['name'])
        self.sweep['expt'] = expt

        if self.type == "Spin Echo":  
            if self.parameters['expt']=="Hahn Echo":
                self.sweep['expt'].echo_delay = 2*np.array(runinfo.scan0.scan_dict['delay_sweep'])*runinfo.parameters['pulses']
            elif self.parameters['expt']=="CPMG":
                self.sweep['expt'].echo_delay = 2*runinfo.parameters['delay']*runinfo.scan0.scan_dict['cpmg_sweep']
            elif self.parameters['sweep2'] and self.parameters['expt2']=="Hahn Echo":
                self.sweep['expt'].echo_delay = 2*runinfo.scan1.scan_dict['delay_sweep']*runinfo.parameters['pulses']
            elif self.parameters['sweep2'] and self.parameters['expt2']=="CPMG":
                self.sweep['expt'].echo_delay = 2*runinfo.parameters['delay']*runinfo.scan1.scan_dict['cpmg_sweep']
            else:
                self.sweep['expt'].echo_delay = 2*runinfo.parameters['delay']*runinfo.parameters['pulses']

        self.sweep['expt'].start_time = time()
        self.sweep['expt'].start_thread()

          
    def hardware_off(self):
        """
        turns off the hardware 
        """
        if 'expt' in self.sweep.keys():
            self.sweep['expt'].runinfo.running = False
        if self.parameters['use_psu']:
            self.devices.psu.output = False
