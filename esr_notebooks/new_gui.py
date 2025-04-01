from PyQt5.QtWidgets import (QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
                             QSplitter, QScrollArea, QLabel, QFrame, QComboBox, QSizePolicy, 
                             QCheckBox, QSpinBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem, 
                             QMessageBox, QLineEdit, QSizeGrip)
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
import pyscan as ps
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
         # Set custom column widths: Setting column is wider
        self.settings_tree.setColumnWidth(0, 200)  # Set the 'Setting' column width to 200px
        self.settings_tree.setColumnWidth(1, 100)  # Set the 'Value' column width to 100px
        
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

    def load_settings_panel(self, settings):
        """ Populate the settings panel dynamically """
        self.settings_tree.clear()

        for group_name, group_settings in settings.get("groups", {}).items():
            group_item = QTreeWidgetItem([group_name])
            self.settings_tree.addTopLevelItem(group_item)

            # Expand "Main Settings" group only (modify this logic as per your group name)
            if group_name == "Main Settings":
                group_item.setExpanded(True)

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

EXPERIMENT_TEMPLATES = {
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


class ExperimentType:
    def __init__(self, type):
        self.type = type #string indicating experiment type

        #harware releated:
        self.soc = QickSoc()
        self.soccfg = self.soc
        self.devices = ps.ItemAttribute()
        self.sig = ps.ItemAttribute()
        
        self.parameters = {} #input
        self.sweep = {} #output 

        #for saving the parameters you entered into the settings panel
        if self.type == "Spin Echo":
            self.default_file = "se_defaults.pkl"
        elif self.type == "Pulse Frequency Sweep":
            self.default_file = "ps_defaults.pkl"


    def init_pyscan_experiment(self):
        """
        This initializes a pyscan experiment with functions from the correct 
        experiment type scripts and GUI files.
        """
        if self.type == "Spin Echo":
            seg.init_experiment(self.devices, self.parameters, self.sweep, self.soc)
        elif self.type == "Pulse Frequency Sweep":
            psg.init_experiment(self.devices, self.parameters, self.sweep, self.soc)

    def set_parameters(self, parameters):
        """
        Takes in parameters read from the settings panel in the UI, 
        copies them into the paremeters dictionary, and then modifies them sligthly
        so they are ready for the experiment
        """
        self.parameters = parameters

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
        
        #NOTE: this is logic that he had: this makes it so that the defaults are 
        #updated with whatever the parameters that the user just entered:
        with open(self.default_file, 'wb') as f:
            pickle.dump(self.parameters, f)
            
        inst = ps.ItemAttribute()
        if not hasattr(self.devices, 'psu') and self.parameters['use_psu']:
            waddr = self.parameters['psu_address'].split('ASRL')[-1].split('::')[0]
            self.devices.psu = ps.GPD3303S(waddr)
        if not hasattr(self.devices, 'ls335') and self.parameters['use_temp']:
            self.devices.ls335 = ps.Lakeshore335()
            ttemp = self.devices.ls335.get_temp()

        #NOTE: this is the checkbox that say "if i've clicked initialize on read processed/read unprocessed/or on start sweep"
        #then initialize the pyscan experiment
        #I think we probably can get rid of this
        if not self.parameters['init']: #presumably in his original code, this gets set to false if the user doesn't click the initialize on read checkbox in his code
            pass
        else:
            self.init_pyscan_experiment() 
    
    def read_processed(self):
        """"
        Takes a snapshot of the current state and processes it before displaying it
        """
        if self.type == "Spin Echo":
            seg.read_processed(self.sig, self.config, self.soc, self.fig)
        elif self.type == "Pulse Frequency Sweep":
            psg.read_processed(self.sig, self.config, self.soc, self.fig)

    def read_unprocessed(self):
        """"
        Takes a snapshot of the current state and doesn't process it before display it
        """
        if self.type == "Spin Echo":
            seg.read_unprocessed(self.sig, self.config, self.soc, self.fig)
        elif self.type == "Pulse Frequency Sweep":
            psg.read_unprocessed(self.sig, self.config, self.soc, self.fig)

    def run_sweep(self):#, output, fig):
        """actually runs a sweep"""
        self.sweep['expt'].start_time = time()
        self.sweep['expt'].start_thread()
    
    def start_sweep(self):
        """starts up the hardware to run a sweep and runs a sweep"""
        runinfo = self.sweep['runinfo']
        expt = ps.Sweep(runinfo, self.devices, self.sweep['name'])
        self.sweep['expt'] = expt
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
        self.run_sweep(self.sweep, self.parameters)

    def stop_sweep(self):
        """Stops a sweep that is currently running"""
        self.sweep['expt'].runinfo.running = False
        
    def hardware_off(self):
        """
        turns off the hardware 
        """
        if 'expt' in self.sweep.keys():
            self.sweep['expt'].runinfo.running = False
        if self.parameters['use_psu']:
            self.devices.psu.output = False

class ExperimentUI(QMainWindow):
    """ Main UI Class """

    def __init__(self):
        super().__init__()
        
        # Setup experiments
        self.experiments = {
            "Spin Echo": ExperimentType("Spin Echo"), 
            "Pulse Frequency Sweep": ExperimentType("Pulse Frequency Sweep")
        }
        # Default experiment
        self.current_experiment = self.experiments["Spin Echo"]
        self.experiment_templates = EXPERIMENT_TEMPLATES
        self.temp_parameters = {}

        # Create main UI elements
        self.settings_panel = DynamicSettingsPanel() 
        self.graphs_panel = self.init_graphs_panel()
        self.error_log = self.init_error_log()
        self.bottom_menu_bar = self.init_bottom_menu_bar() 
        self.top_menu_bar = self.init_top_menu_bar()

        # Build the main layout with splitters
        self.init_layout()

        # Load some default experiment into the settings panel
        self.current_experiment = self.experiments["Pulse Frequency Sweep"]
        self.temp_parameters = {}
        print("FINISH IMPLEMENTING")
        #change function assigned to each button
        self.settings_panel.load_settings_panel(self.experiment_templates.get("Pulse Frequency Sweep", {"main": [], "groups": {}}))

    def init_layout(self):
        """
        Build the overall layout:
         - A top menu (horizontal layout of buttons)
         - A main splitter horizontally: left = settings, right = a vertical splitter
           top = graphs, bottom = error log
         - A bottom menu (horizontal layout of buttons).
        """

        # Make the window frameless to remove the title bar
        self.setWindowFlags(Qt.FramelessWindowHint)  # This removes the title bar and system buttons

        # Create the central widget and main layout for the window
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # Add top menu (adjust layout as needed)
        main_layout.addLayout(self.top_menu_bar)

        # -- main splitter (horizontal)
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Left side: settings
        self.main_splitter.addWidget(self.settings_panel)

        # Right side: a vertical splitter for graphs vs. error log
        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_splitter.addWidget(self.graphs_panel)
        self.right_splitter.addWidget(self.error_log)

        self.main_splitter.addWidget(self.right_splitter)

        # Set stretch factors to control resizing behavior
        self.main_splitter.setStretchFactor(0, 1)  # Settings Panel (left side)
        self.main_splitter.setStretchFactor(1, 1)  # Right splitter (graph & error log)

        main_layout.addWidget(self.main_splitter)

        # Customizing the size of the resize grip by adding a larger widget at the bottom-right corner
        size_grip = QSizeGrip(self)
        size_grip.setStyleSheet("background-color: red; width: 20px; height: 200px;")  # Customize the grip
        self.main_splitter.addWidget(size_grip)

        # Add bottom menu
        main_layout.addLayout(self.bottom_menu_bar)

        # Set the layout to the central widget
        self.setCentralWidget(central_widget)

        # Set up window title and default size
        self.setWindowTitle("Experiment UI")
        self.setGeometry(100, 100, 1000, 700)  # Default window size
        self.show()  # Show the window
         
    
    def init_graphs_panel(self):
        """Creates the graphs panel containing Matplotlib graphs."""
        # Create a container widget for the graphs
        graph_section_widget = QWidget()
        graph_layout = QVBoxLayout(graph_section_widget)
        graph_layout.setContentsMargins(100, 50, 100, 50)

        # Add three Matplotlib graphs to the layout
        self.graphs = [MatplotlibCanvas() for _ in range(3)]
        for graph in self.graphs:
            graph_layout.addWidget(graph)

        return graph_section_widget

    
    def init_bottom_menu_bar(self):
        """Creates the bottom menu bar."""
        print("NEED TO FINISH IMPLEMENTING")
        bottom_layout = QHBoxLayout()
        # Add buttons or other widgets as needed.
        btn1 = QPushButton("Button 1")
        btn2 = QPushButton("Button 2")
        bottom_layout.addWidget(btn1)
        bottom_layout.addWidget(btn2)
        return bottom_layout

    def init_error_log(self):
        """Creates the error log panel."""
        error_log = QLabel("Error Log")
        error_log.setFrameShape(QFrame.Box)
        error_log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return error_log
    
    def init_top_menu_bar(self):
        top_menu = QHBoxLayout()

        # THESE FUNCTIONS DON'T DO ANYTHING RIGHT NOW, NEED TO IMPLEMENT
        file_buttons_widget = QWidget()
        file_buttons_layout = QGridLayout(file_buttons_widget)
        save_exp_btn = QPushButton("Save Experiment")
        new_exp_btn = QPushButton("New Experiment")
        save_exp_as_btn = QPushButton("Save Experiment As")
        open_exp_btn = QPushButton("Open Experiment")
        open_exp_btn.clicked.connect(self.show_open_experiment_popup)
        new_exp_btn.clicked.connect(self.show_new_experiment_popup)
        save_exp_as_btn.clicked.connect(self.show_save_experiment_as_popup)

        file_buttons_layout.addWidget(save_exp_btn, 0, 0)
        file_buttons_layout.addWidget(new_exp_btn, 0, 1)
        file_buttons_layout.addWidget(save_exp_as_btn, 1, 0)
        file_buttons_layout.addWidget(open_exp_btn, 1, 1)
        #########

        top_menu.addWidget(file_buttons_widget)

        # Add experiment-specific buttons
        top_menu = self.init_experiment_specific_buttons(top_menu)

        # Window Control Buttons:
        window_controls_widget = QWidget()
        window_controls_layout = QHBoxLayout(window_controls_widget)
        window_controls_layout.setContentsMargins(0, 0, 0, 0)

        # Create window control buttons
        minimize_btn = QPushButton("_")
        minimize_btn.clicked.connect(self.showMinimized)
        fullscreen_btn = QPushButton("Toggle Full Screen")
        fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        off_btn = QPushButton("Hardware Off and Close Software")
        off_btn.clicked.connect(self.hardware_off_frontend)

        window_controls_layout.addWidget(minimize_btn)
        window_controls_layout.addWidget(fullscreen_btn)
        window_controls_layout.addWidget(off_btn)

        # Add the window controls to the top menu layout
        top_menu.addWidget(window_controls_widget)

        return top_menu

    def toggle_fullscreen(self):
        # Toggle between full screen and normal window states
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def init_experiment_specific_buttons(self, top_menu):
        """
        This section creates buttons, assigns the proper functions to them, and then
        adds them to the top menu bar.
        """
        experiment_buttons_widget = QWidget()
        experiment_buttons_layout = QGridLayout(experiment_buttons_widget)
        
        set_parameters_btn = QPushButton("Push Parameters")
        set_parameters_btn.clicked.connect(self.read_and_set_parameters)        
        read_unprocessed_btn = QPushButton("Read Unprocessed")
        read_unprocessed_btn.clicked.connect(self.read_unprocessed_frontend)
        read_processed_btn = QPushButton("Read Processed")
        read_processed_btn.clicked.connect(self.read_processed_frontend)
        sweep_start_stop_btn = QPushButton("Start Sweep")
        sweep_start_stop_btn.clicked.connect(self.toggle_start_stop_sweep_frontend)

        experiment_buttons_layout.addWidget(set_parameters_btn, 0, 0)
        experiment_buttons_layout.addWidget(read_unprocessed_btn, 0, 1)
        experiment_buttons_layout.addWidget(read_processed_btn, 1, 1)
        experiment_buttons_layout.addWidget(sweep_start_stop_btn, 2, 1)

        top_menu.addWidget(experiment_buttons_widget)
    
        # Template Selection
        template_dropdown = QComboBox()
        template_dropdown.addItems(["Pulse Frequency Sweep", "Spin Echo"])
        template_dropdown.currentTextChanged.connect(self.change_experiment_type)

        # Create the indicator for running sweep
        running_indicator = QLabel("•")
        running_indicator.setFixedSize(10, 10)  # Set the size of the indicator
        running_indicator.setStyleSheet("background-color: white;")  # Set initial color to red

        #Run Experiment and Save Recordings
        self.run_and_save_recordings_widget = QWidget()
        run_and_save_recordings_layout = QGridLayout(self.run_and_save_recordings_widget)

        plot_menu = QCheckBox("Save All Plot Recordings")

        run_and_save_recordings_layout.addWidget(running_indicator)
        run_and_save_recordings_layout.addWidget(plot_menu, 0, 0)

        top_menu.addWidget(self.run_and_save_recordings_widget)

        return top_menu

    def init_settings_panel(self):
        # Settings Panel
        self.settings_panel = DynamicSettingsPanel()
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setWidget(self.settings_panel)

        # Load initial settings
        self.current_experiment = self.experiments["Pulse Frequency Sweep"]
        self.temp_parameters = {}
        print("FINISH IMPLEMENTING")
        #NEED change function assigned to each button
        self.settings_panel.load_settings_panel(self.experiment_templates.get("Pulse Frequency Sweep", {"main": [], "groups": {}}))
        
        return settings_scroll

    def change_experiment_type(self, experiment_type):
        self.current_experiment.stop_sweep()
        self.current_experiment = self.experiments[experiment_type]
        self.temp_parameters = {}
        print("FINISH IMPLEMENTING")
        #change function assigned to each button
        self.settings_panel.load_settings_panel(self.experiment_templates.get(experiment_type, {"main": [], "groups": {}}))

    def read_and_set_parameters(self): 
        #this used to be the code in gui_setup.py that looped through all
        #the controls and updated the parameters with the values in the controls
        tree = self.settings_panel.settings_tree #This is the triply-nested dictionary
        root = tree.invisibleRootItem() #This retrieves the leaves of the tree (the subdictionaries with each indivifual setting)
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
                    raise Exception("Widget in Setttings panel is not of a known type") 
                
                self.temp_parameters[key] = value
        self.current_experiment.set_parameters(self.temp_parameters)

    def read_unprocessed_frontend(self):
        self.running_indicator.setStyleSheet("background-color: red;")
        self.read_and_set_parameters()
        self.current_experiment.read_unprocessed()
        self.running_indicator.setStyleSheet("background-color: grey;")

    def read_processed_frontend(self):
        """calls the read processed function. If initialize on read is checked, then the experiment is also initialized"""
        self.running_indicator.setStyleSheet("background-color: red;")
        self.read_and_set_parameters()
        self.current_experiment.read_processed()
        self.running_indicator.setStyleSheet("background-color: grey;")

    def toggle_start_stop_sweep_frontend(self):
        """ Toggle between Run and Stop Sweep states """
        if self.sweep_start_stop_btn.text() == "Start Sweep":
            self.running_indicator.setStyleSheet("background-color: red;")
            self.read_and_set_parameters()
            self.sweep_start_stop_btn.setText("Stop Sweep")
            self.current_experiment.start_sweep()
            #currently, the running indicator won't turn off when the sweep is done. Need to figure this out.
        else:
            self.current_experiment.stop_sweep()
            self.sweep_start_stop_btn.setText("Start Sweep")
            self.running_indicator.setStyleSheet("background-color: grey;")
    
    def hardware_off_frontend(self):
        """calls a backend function that turns off the harware for the experiment"""
        try:
            self.current_experiment.hardware_off()
        finally:
            self.close()

    def show_open_experiment_popup(self):
        popup = PopUpMenu("Open Experiment", "Feature coming soon!")
        popup.show_popup()
    
    def show_save_experiment_as_popup(self):
        popup = PopUpMenu("Save Experiment As", "Feature coming soon!")
        popup.show_popup()
    
    def show_new_experiment_popup(self):
        popup = PopUpMenu("New Experiment", "Feature coming soon!")
        popup.show_popup()


def main():
    app = QApplication(sys.argv)
    ex = ExperimentUI()
    ex.showFullScreen()
    sys.exit(app.exec_())

    
if __name__ == "__main__":
    main()