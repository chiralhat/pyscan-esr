from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
                             QSplitter, QScrollArea, QLabel, QFrame, QComboBox, QSizePolicy, 
                             QCheckBox, QSpinBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem, 
                             QMessageBox, QLineEdit)
from PyQt5.QtCore import Qt
import sys
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import sys, os
sys.path.append('../')
from rfsoc2 import *
import matplotlib.pyplot as plt
import numpy as np
from time import sleep
from datetime import date, datetime
from pathlib import Path
from pulsesweep_gui import *
from spinecho_gui import *
import pickle
import pyvisa
import pulsesweep_gui as psg
import spinecho_gui as seg

import os

# [ this is stuff that was at the top of gui_setup.py:
lstyle = {'description_width': 'initial'}
cpmgs = range(1, 256)
aves = [1, 4, 16, 64, 128, 256]
voltage_limits = [0.002, 10]
tdivs = []
for n in range(9, -1, -1):
    tdivs += [2*10**-n, 4*10**-n, 10*10**-n]#[2.5*10**-n, 5*10**-n, 10*10**-n]

scopes = {'TBS1052C': ps.Tektronix1052B,
          'MSO24': ps.TektronixMSO2}

if not hasattr(ps, 'rm'):
    ps.rm = pyvisa.ResourceManager('@py')
res_list = ps.rm.list_resources()
# ...]


class PopUpMenu(QMessageBox):
    """ Basic pop-up menu """
    def __init__(self, title="Notification", message="This is a pop-up message"):
        super().__init__()
        self.setWindowTitle(title)
        self.setText(message)
        self.setStandardButtons(QMessageBox.Ok)

    def show_popup(self):
        self.exec_()

class MatplotlibCanvas(FigureCanvas):
    """ Matplotlib canvas to display graphs inside PyQt5 UI """
    def __init__(self):
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.plot_placeholder()

    def plot_placeholder(self):
        """Generate a simple placeholder plot with larger margins."""
        self.ax.clear()
        self.ax.plot([0, 1, 2, 3], [0, 1, 4, 9], marker='o', linestyle='-')
        self.fig.subplots_adjust(left=0.1, right=0.9, top=0.8, bottom=0.3)  # Adjust margins
        self.draw()


class DynamicSettingsPanel(QWidget):
    """ Settings panel with dynamically loaded settings """
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.settings_tree = QTreeWidget()
        self.settings_tree.setHeaderHidden(False)
        self.settings_tree.setColumnCount(2)
        self.settings_tree.setHeaderLabels(["Setting", "Value"])
        
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setWidget(self.settings_tree)
        
        self.main_layout.addWidget(self.settings_scroll)
        
        # Static Bottom Menu Bar
        self.bottom_menu = QHBoxLayout()
        self.save_template_btn = QPushButton("Save Template")
        # self.save_template_btn.clicked.connect(self.show_save_template_popup())

        self.bottom_menu.addStretch()
        self.bottom_menu.addWidget(self.save_template_btn)
        
        self.main_layout.addLayout(self.bottom_menu)

    def load_settings(self, settings):
        """ Populate the settings panel dynamically """
        self.settings_tree.clear()

        for group_name, group_settings in settings.get("groups", {}).items():
            group_item = QTreeWidgetItem([group_name])
            self.settings_tree.addTopLevelItem(group_item)

            for setting in group_settings:
                item = QTreeWidgetItem([setting["name"]])
                group_item.addChild(item)
                widget = self.create_setting_widget(setting)
                if widget:
                    self.settings_tree.setItemWidget(item, 1, widget)

    def create_setting_widget(self, setting):
        """ Create appropriate widget based on setting type """
        if setting["type"] == "spin":
            widget = QSpinBox()
            widget.setMinimum(setting["min"])
            widget.setMaximum(setting["max"])
            widget.setValue(setting["default"])
        elif setting["type"] == "double_spin":
            widget = QDoubleSpinBox()
            widget.setMinimum(setting["min"])
            widget.setMaximum(setting["max"])
            widget.setValue(setting["default"])
        elif setting["type"] == "combo":
            widget = QComboBox()
            widget.addItems(setting["options"])
            widget.setCurrentText(setting["default"])
        elif setting["type"] == "check":
            widget = QCheckBox()
            widget.setChecked(setting["default"])
        else:
            widget = QLabel("N/A")
        return widget

    # def show_save_template_popup(self):
    #     popup = PopUpMenu("Save Template", "Feature coming soon!")
    #     layout = QVBoxLayout()
    #     name_input = QLineEdit()
    #     layout.addWidget(name_input)
    #     widget = QWidget()
    #     widget.setLayout(layout)
    #     popup.layout().addWidget(widget)
    #     popup.show_popup()

class ExperimentSettingsManager:
    """ Handles loading different experiment settings into the UI """
    def __init__(self, settings_panel, experiment_dropdown):
        self.settings_panel = settings_panel
        self.experiment_dropdown = experiment_dropdown
        self.experiment_dropdown.currentTextChanged.connect(self.update_settings_panel)

        # Example Experiment Settings
        self.experiment_templates = {
            "Pulse Frequency Sweep": {
                "main": [],
                "groups": {
                    "Main Settings": [
                        {"name": "Frequency", "type": "double_spin", "min": 0.1, "max": 10.0, "default": 2.4},
                        {"name": "Ave", "type": "spin", "min": 1, "max": 1000, "default": 100},
                        {"name": "Dir and Name", "type": "combo", "options": ["Option 1", "Option 2"], "default": "Option 1"},
                        {"name": "Experiment", "type": "combo", "options": ["Exp A", "Exp B"], "default": "Exp A"},
                        {"name": "Sweep start, end, step", "type": "double_spin", "min": 0.1, "max": 10.0, "default": 2.6}
                    ],
                    "Readout Settings": [
                        {"name": "Time Offset", "type": "double_spin", "min": 0, "max": 100.0, "default": 10.0},
                        {"name": "Readout Length", "type": "spin", "min": 1, "max": 1000, "default": 10},
                        {"name": "Loopback", "type": "combo", "options": ["Enabled", "Disabled"], "default": "Enabled"}
                    ],
                    "Uncommon Settings": [
                        {"name": "Repetition time", "type": "double_spin", "min": 0.1, "max": 100.0, "default": 10.0},
                        {"name": "Ch1 90 Pulse", "type": "double_spin", "min": 0.1, "max": 100.0, "default": 10.0},
                        {"name": "Magnetic Field, Scale, Current limit", "type": "double_spin", "min": 0.1, "max": 100.0, "default": 10.0},
                        {"name": "Reps", "type": "spin", "min": 1, "max": 1000, "default": 10},
                        {"name": "Wait Time", "type": "double_spin", "min": 0.1, "max": 100.0, "default": 10.0},
                        {"name": "Integral only", "type": "check", "default": False},
                        {"name": "Initialize on read", "type": "check", "default": True},
                        {"name": "Turn off after sweep", "type": "check", "default": False}
                    ],
                    "Utility Settings": [
                        {"name": "PSU Addr", "type": "spin", "min": 1, "max": 100, "default": 5},
                        {"name": "Use PSU", "type": "check", "default": True},
                        {"name": "Use Lakeshore", "type": "check", "default": False}
                    ]
                }
            },
            "Spin Echo": {
                "main": [],
                "groups": {
                    "Main Settings": [
                        {"name": "Ch1 Freq, Gain", "type": "double_spin", "min": 0.1, "max": 10.0, "default": 2.4},
                        {"name": "Repetition time", "type": "double_spin", "min": 0.1, "max": 100.0, "default": 10.0},
                        {"name": "Ave", "type": "spin", "min": 1, "max": 1000, "default": 100},
                        {"name": "Dir and Name", "type": "combo", "options": ["Option 1", "Option 2"], "default": "Option 1"},
                        {"name": "Reps", "type": "spin", "min": 1, "max": 1000, "default": 10},
                        {"name": "Sweep start, end, step", "type": "double_spin", "min": 0.1, "max": 10.0, "default": 2.6}
                    ],
                    "Pulse Settings": [
                        {"name": "Ch1 Delay, 90 Pulse", "type": "double_spin", "min": 0.1, "max": 100.0, "default": 10.0},
                        {"name": "Nut. Delay, Pulse Width", "type": "double_spin", "min": 0.1, "max": 100.0, "default": 10.0}
                    ],
                    "Second Sweep Settings": [
                        {"name": "Second sweep?", "type": "check", "default": False},
                        {"name": "Experiment 2", "type": "combo", "options": ["Exp C", "Exp D"], "default": "Exp C"},
                        {"name": "Sweep 2 start, end, step", "type": "double_spin", "min": 0.1, "max": 10.0, "default": 2.6}
                    ],
                    "Readout Settings": [
                        {"name": "Time Offset", "type": "double_spin", "min": 0, "max": 100.0, "default": 10.0},
                        {"name": "Readout Length", "type": "spin", "min": 1, "max": 1000, "default": 10},
                        {"name": "Loopback", "type": "combo", "options": ["Enabled", "Disabled"], "default": "Enabled"}
                    ],
                    "Uncommon Settings": [
                        {"name": "Ch1 180 Pulse Mult", "type": "double_spin", "min": 0.1, "max": 100.0, "default": 10.0},
                        {"name": "Magnetic Field, Scale, Current limit", "type": "double_spin", "min": 0.1, "max": 100.0, "default": 10.0},
                        {"name": "Wait Time", "type": "double_spin", "min": 0.1, "max": 100.0, "default": 10.0},
                        {"name": "Integral only", "type": "check", "default": False},
                        {"name": "Initialize on read", "type": "check", "default": True},
                        {"name": "Turn off after sweep", "type": "check", "default": False}
                    ],
                    "Utility Settings": [
                        {"name": "PSU Addr", "type": "spin", "min": 1, "max": 100, "default": 5},
                        {"name": "Use PSU", "type": "check", "default": True},
                        {"name": "Use Lakeshore", "type": "check", "default": False}
                    ]
                }
            }
        }
        self.update_settings_panel("Pulse Frequency Sweep")

    def update_settings_panel(self, experiment_type):
        self.settings_panel.load_settings(self.experiment_templates.get(experiment_type, {"main": [], "groups": {}}))

class Experiment():
    """
    Stores the actual experiment parameters and the functions that 
    need to get run for the experiment. This basically
    functions as an the jupyter notebook and the init_gui function call
    at the end of the "experimentType_gui.py. Thats why I import those files as 
    seg (Spin Echo GUI) and psg (Pulse Sweep GUI).
    """
    ui = None
    
    parameters = {}
    sweep = {}
    devices = None
    sig = None
    exp_type = None
    soc = None
    soccfg = None
    default_file = None

    # Functions unique to experiments which will be attached to buttons:
    # These will be obtained from experimentType_gui.py
    read_unprocessed_function = None
    read_processed_function = None
    sweep_function = None


    def __init__(self):
        self.ui = ExperimentUI()

        # This was taken from the top of the notebook files, 
        # might need to get looked at more [...
        self.devices = ps.ItemAttribute()
        self.sig = ps.ItemAttribute()
        self.soc = QickSoc()
        self.soccfg = self.soc
        self.parameters = {}
        self.sweep = {}
        #...]
        self.init_experiment() #this will do the rest of the initializion needed
    
    def init_experiment(self, exp_type = "Spin Echo"):
        """
        Initializing the class variables that differ for each experiment
        
        this should also get run every time that we switch an experiment"""
        self.exp_type = exp_type
        if exp_type == "Pulse Frequency Sweep":
            self.default_file = 'ps_defaults.pkl'
            psg.init_experiment(self.devices, self.parameters, self.sweep, self.soc)
            
            self.read_unprocessed_function = psg.read_unprocessed
            self.read_processed_function = psg.read_processed
            self.sweep_function = self.run_sweep
            self.ui.init_gui_button_functions(self.read_unprocessed_function, 
                                              self.read_processed_function,
                                              self.sweep_function)
            
        elif exp_type == "Spin Echo":
            self.default_file = 'se_defaults.pkl'
            seg.init_experiment(self.devices, self.parameters, self.sweep, self.soc)
            
            self.read_unprocessed_function = seg.read_unprocessed
            self.read_processed_function = seg.read_processed
            self.sweep_function = self.run_sweep
            self.ui.init_gui_button_functions(self.read_unprocessed_function, 
                                              self.read_processed_function,
                                              self.sweep_function)
        #TO IMPLEMENT: call function in UI that shows the proper settings in the UI based on the experiment type
        # this is currently happening in the ExperimentSettingsManager class right now, but
        # I need to investigate this further
        

    def run_sweep(self):#, output, fig):
        """Runs a sweep."""
        self.sweep['expt'].start_time = time()
        self.sweep['expt'].start_thread()
    
    #MIGHT WANT TO MOVE SOME FUNCTIONS that are in the bottom of ExperimentUI that 
    #don't really pertain to the UI to here (read_mon, etc)

    
class ExperimentUI(Experiment, QWidget):
    """ Main UI Class """
    experiment = None

    def __init__(self):
        super().__init__()
        self.initUI()
        self.experiment = Experiment()

    def initUI(self):
        main_layout = QVBoxLayout(self)

        # Top Menu Bar
        top_menu = QHBoxLayout()

        # File Action Buttons (Replaces Dropdown)
        file_buttons_widget = QWidget()
        file_buttons_layout = QGridLayout(file_buttons_widget)

        self.save_exp_btn = QPushButton("Save Experiment")
        self.new_exp_btn = QPushButton("New Experiment")
        self.save_exp_as_btn = QPushButton("Save Experiment As")
        self.open_exp_btn = QPushButton("Open Experiment")
        self.open_exp_btn.clicked.connect(self.show_open_experiment_popup)
        self.new_exp_btn.clicked.connect(self.show_new_experiment_popup)
        self.save_exp_as_btn.clicked.connect(self.show_save_experiment_as_popup)

        file_buttons_layout.addWidget(self.save_exp_btn, 0, 0)
        file_buttons_layout.addWidget(self.new_exp_btn, 0, 1)
        file_buttons_layout.addWidget(self.save_exp_as_btn, 1, 0)
        file_buttons_layout.addWidget(self.open_exp_btn, 1, 1)

        top_menu.addWidget(file_buttons_widget)

        # Template Selection
        self.template_dropdown = QComboBox()
        self.template_dropdown.addItems(["Pulse Frequency Sweep", "Spin Echo"])
        self.template_dropdown.currentTextChanged.connect(self.change_experiment_type)

        top_menu.addWidget(self.template_dropdown)


        # Run Experiment and Save Recordings
        self.run_and_save_recordings_widget = QWidget()
        self.run_and_save_recordings_layout = QGridLayout(self.run_and_save_recordings_widget)

        self.run_button = QPushButton("Run Experiment")
        self.run_button.clicked.connect(self.toggle_run_experiment)

        self.plot_menu = QCheckBox("Save All Plot Recordings")

        self.run_and_save_recordings_layout.addWidget(self.run_button, 1, 0)
        self.run_and_save_recordings_layout.addWidget(self.plot_menu, 0, 0)

        top_menu.addWidget(self.run_and_save_recordings_widget)

        main_layout.addLayout(top_menu)

        # Main Splitter (Left: Settings, Right: Output)
        main_splitter = QSplitter(Qt.Horizontal)

        # Settings Panel
        self.settings_panel = DynamicSettingsPanel()
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setWidget(self.settings_panel)

        # Output Section (Graphs & Error Log)
        output_container = QSplitter(Qt.Vertical)
        output_container.setSizes([100, 100])

        # Graphs Panel
        graph_section_widget = QWidget()
        graph_layout = QVBoxLayout(graph_section_widget)
        graph_layout.setContentsMargins(100, 50, 100, 50)

        # Add three Matplotlib Graphs
        self.graphs = [MatplotlibCanvas() for _ in range(3)]
        for graph in self.graphs:
            graph_layout.addWidget(graph)

        output_container.addWidget(graph_section_widget)

        # Error Log Panel
        error_log = QLabel("Error Log")
        error_log.setFrameShape(QFrame.Box)
        error_log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        output_container.addWidget(error_log)

        # Adding to Main Splitter
        main_splitter.addWidget(settings_scroll)
        main_splitter.addWidget(output_container)
        main_layout.addWidget(main_splitter)

        self.setLayout(main_layout)

        # Load initial settings
        self.settings_manager = ExperimentSettingsManager(self.settings_panel, self.template_dropdown)
        self.change_experiment_type("Pulse Frequency Sweep")

    def init_gui_button_functions(self, read_unprocessed_function, read_processed_function, sweep_function):
        """
        Links up each function to each button (for functions that are unique to each experiment).

        NOTE: might just want to have this link up ALL functions functions to the buttons

        This basically does what the gui_function() function does in gui_setup.py"""
        #NEED TO IMPLEMENT
        pass

    def set_pars(self, devices):
        """Read through the settings tree and load them into a parameters dictionary."""
        
        #this used to be the code in gui_setup.py that looped through all
        #the controls and updated the parameters with the values in the controls
        tree = self.settings_panel.settings_tree
        root = tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            # Loop over each setting in the group
            for j in range(group_item.childCount()):
                item = group_item.child(j)
                key = item.text(0)  # The setting name
                widget = tree.itemWidget(item, 1)
                
                # Get the widget's value based on its type
                if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                    value = widget.value()
                elif isinstance(widget, QComboBox):
                    value = widget.currentText()
                elif isinstance(widget, QCheckBox):
                    value = widget.isChecked()
                elif isinstance(widget, QLabel):
                    value = widget.text()
                else:
                    value = None  # Fallback if widget type is not handled
                
                self.parameters[key] = value

        #this stuff below is unchanged from gui_setup.py [...
        if 'ave_reps' in self.parameters.keys():
            reps = self.parameters['ave_reps']
        else:
            reps = 1
        if 'period' in self.parameters.keys():
            period = self.parameters['period']
        else:
            period = 500
        tmult = period/1e6*4*reps
        self.parameters['subtime'] = self.parameters['soft_avgs']*tmult
        datestr = date.today().strftime('%y%m%d')
        fname = datestr+str(self.parameters['file_name'])+'_'
        self.parameters['outfile'] = str(Path(self.parameters['save_dir']) / fname)
        with open(default_file, 'wb') as f:
            pickle.dump(self.parameters, f)
            
        inst = ps.ItemAttribute()
        if not hasattr(devices, 'psu') and self.parameters['use_psu']:
            waddr = self.parameters['psu_address'].split('ASRL')[-1].split('::')[0]
            devices.psu = ps.GPD3303S(waddr)
        if not hasattr(devices, 'ls335') and self.parameters['use_temp']:
            devices.ls335 = ps.Lakeshore335()
            ttemp = devices.ls335.get_temp()
        #...]

        #NEED TO FIGURE THIS OUT
        if (self.parameters['init'] or btn.description=='Initialize'):
            init_expt(devices, parameters, sweep, soc) # TODO: Fix the runinfo, expt bit (put into new dict?)
            conn_ind.value = 1



    def change_experiment_type(self, experiment_type):
        """ Handle changes in experiment selection """
        self.settings_manager.update_settings_panel(experiment_type)

    def toggle_run_experiment(self):
        """ Toggle between Run and Stop Experiment states """
        if self.run_button.text() == "Run Experiment":
            self.run_button.setText("Stop Experiment")
        else:
            self.run_button.setText("Run Experiment")

    def show_open_experiment_popup(self):
        popup = PopUpMenu("Open Experiment", "Feature coming soon!")
        popup.show_popup()
    
    def show_save_experiment_as_popup(self):
        popup = PopUpMenu("Save Experiment As", "Feature coming soon!")
        popup.show_popup()
    
    def show_new_experiment_popup(self):
        popup = PopUpMenu("New Experiment", "Feature coming soon!")
        popup.show_popup()


    #THE FOLLOWING WAS TAKEN FROM GUI_SETUP.PY
    #Haven't looked at it yet, just copy pasted. Need to make this not have errors
    #[...
    def init_btn(btn):
        run_ind.value = 1
        set_pars(btn)
        run_ind.value = 0

    def stopsweep(btn):
        sweep['expt'].runinfo.running = False
    
    def turnoff(btn):
        if 'expt' in sweep.keys():
            sweep['expt'].runinfo.running = False
        if parameters['use_psu']:
            devices.psu.output = False
    
    with output:
        fig = plt.figure(figsize=(8, 5))
    #         setup_plot(output, fig)

    with measout:
        mfig = plt.figure(figsize=(8, 5))


    def start_sweep(btn):
        run_ind.value = 1
        set_pars(btn)
        runinfo = sweep['runinfo']
        expt = ps.Sweep(runinfo, devices, sweep['name'])
        sweep['expt'] = expt
        if parameters['expt']=="Hahn Echo":
            sweep['expt'].echo_delay = 2*np.array(runinfo.scan0.scan_dict['delay_sweep'])*runinfo.parameters['pulses']
        elif parameters['expt']=="CPMG":
            sweep['expt'].echo_delay = 2*runinfo.parameters['delay']*runinfo.scan0.scan_dict['cpmg_sweep']
        elif parameters['sweep2'] and parameters['expt2']=="Hahn Echo":
            sweep['expt'].echo_delay = 2*runinfo.scan1.scan_dict['delay_sweep']*runinfo.parameters['pulses']
        elif parameters['sweep2'] and parameters['expt2']=="CPMG":
            sweep['expt'].echo_delay = 2*runinfo.parameters['delay']*runinfo.scan1.scan_dict['cpmg_sweep']
        else:
            sweep['expt'].echo_delay = 2*runinfo.parameters['delay']*runinfo.parameters['pulses']
        run_sweep(sweep, parameters)#, measout, mfig)
        run_ind.value = 0

    
    def read_mon(btn):
        run_ind.value = 1
        set_pars(btn)
        read(sig, parameters, soc, output, fig)
        run_ind.value = 0
    
    
    def monitor(btn):
        run_ind.value = 1
        set_pars(btn)
        single_run(sig, parameters, soc, output, fig)
        run_ind.value = 0

    
    def disconnect(btn):
        run_ind.value = 1
        turnoff(btn)
        for key in devices.keys():
            devices[key].close()
        devices.__dict__.clear()
        conn_ind.value = 0
        run_ind.value = 0
    
    goButton = ipw.Button(description='Initialize')
    goButton.on_click(init_btn)

    readButton = ipw.Button(description='Read Scope')
    readButton.on_click(read_mon)

    monButton = ipw.Button(description='Run (No Save)')
    monButton.on_click(monitor)

    startButton = ipw.Button(description='Start Sweep')
    startButton.on_click(start_sweep)

    stopButton = ipw.Button(description='Stop Sweep')
    stopButton.on_click(stopsweep)

    offButton = ipw.Button(description='Output Off')
    offButton.on_click(turnoff)

    closeButton = ipw.Button(description='Disconnect')
    closeButton.on_click(disconnect)

    controls += [ipw.HBox([goButton, readButton, monButton, startButton, stopButton, run_ind])]
    controls += [ipw.HBox([offButton, closeButton, conn_ind])]
    
    # mtab = measure_select()
    controls += [ipw.HBox([output, measout])]

    con_panel = ipw.VBox(controls)
    #...]


def main():
    app = QApplication(sys.argv)
    ex = ExperimentUI()
    ex.showFullScreen()
    sys.exit(app.exec_())

    
if __name__ == "__main__":
    main()