from PyQt5.QtWidgets import (QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
                             QSplitter, QScrollArea, QLabel, QFrame, QComboBox, QSizePolicy, 
                             QCheckBox, QSpinBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem, 
                             QMessageBox, QTextEdit, QLineEdit, QStyledItemDelegate, QPushButton, QStyledItemDelegate, QStyleOptionViewItem)
from PyQt5.QtCore import Qt, QRect, QTextStream
from PyQt5.QtGui import QPainter, QTextOption

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


class DualStream:
    def __init__(self, text_edit):
        self.text_edit = text_edit
        self.terminal = sys.__stdout__  # Store the original stdout (for terminal output)

    def write(self, text):
        # Write to QTextEdit (UI)
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.End)  # Move the cursor to the end
        cursor.insertText(text)  # Insert the new text
        self.text_edit.setTextCursor(cursor)  # Ensure the cursor stays at the end
        self.text_edit.ensureCursorVisible()  # Make sure the text is always visible

        # Write to terminal (standard output)
        self.terminal.write(text)  # Print to terminal
        self.terminal.flush()  # Ensure it flushes to terminal immediately

    def flush(self):
        # No need to do anything for flush in this case
        self.terminal.flush()


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

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QScrollArea, QLabel, QHBoxLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QSizePolicy, QPushButton

class DynamicSettingsPanel(QWidget):
    """Settings panel with dynamically loaded settings."""
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.settings_tree = QTreeWidget()
        self.settings_tree.setHeaderHidden(False)
        self.settings_tree.setColumnCount(2)
        self.settings_tree.setHeaderLabels(["Setting", "Value"])
        self.settings_tree.setColumnWidth(0, 200)
        self.settings_tree.setColumnWidth(1, 100)
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setWidget(self.settings_tree)
        self.main_layout.addWidget(self.settings_scroll)

    def load_settings_panel(self, settings):
        """Populate the settings panel dynamically from the template."""
        self.settings_tree.clear()
        for group_name, group_settings in settings.get("groups", {}).items():
            group_item = QTreeWidgetItem([group_name])
            self.settings_tree.addTopLevelItem(group_item)
            group_item.setExpanded(group_name == "Main Settings")
            for setting in group_settings:
                item = QTreeWidgetItem()
                group_item.addChild(item)
                widget = self.create_setting_widget(setting)
                widget._underlying_key = setting.get("key")
                self.settings_tree.setItemWidget(item, 1, widget)
                label_widget = QLabel(setting.get("display", setting.get("name", "N/A")))
                label_widget.setWordWrap(True)
                label_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
                label_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self.settings_tree.setItemWidget(item, 0, label_widget)

    def create_setting_widget(self, setting):
        """Create a widget based on the setting type."""
        stype = setting.get("type")
        if stype == "spin":
            widget = QSpinBox()
            widget.setMinimum(setting.get("min", 0))
            widget.setMaximum(setting.get("max", 1000000))
            widget.setValue(setting.get("default", 0))
        elif stype == "double_spin":
            widget = QDoubleSpinBox()
            widget.setMinimum(float(setting.get("min", 0.0)))
            widget.setMaximum(float(setting.get("max", 1e9)))
            widget.setValue(float(setting.get("default", 0.0)))
        elif stype == "line_edit":
            widget = QLineEdit()
            widget.setText(setting.get("default", ""))
        elif stype == "combo":
            widget = QComboBox()
            widget.addItems(setting.get("options", []))
            widget.setCurrentText(setting.get("default", ""))
        elif stype == "check":
            widget = QCheckBox()
            widget.setChecked(setting.get("default", False))
        elif stype == "composite":
            widget = QWidget()
            layout = QHBoxLayout(widget)
            defaults = setting.get("default", [])
            for val in defaults:
                if isinstance(val, (int, float)):
                    spin = QDoubleSpinBox()
                    spin.setMinimum(setting.get("min", 0.0))
                    spin.setMaximum(setting.get("max", 1e9))
                    spin.setValue(val)
                    layout.addWidget(spin)
                else:
                    line = QLineEdit()
                    line.setText(str(val) if val is not None else "")
                    layout.addWidget(line)
            def composite_values():
                values = []
                for idx in range(layout.count()):
                    sub_widget = layout.itemAt(idx).widget()
                    if isinstance(sub_widget, (QSpinBox, QDoubleSpinBox)):
                        values.append(sub_widget.value())
                    elif isinstance(sub_widget, QLineEdit):
                        values.append(sub_widget.text())
                return values
            widget.composite_values = composite_values
        else:
            widget = QLabel("N/A")
            widget.setWordWrap(True)
        return widget


EXPERIMENT_TEMPLATES = {
    "Pulse Frequency Sweep": {
        "groups": {
            "Main Settings": [
                {"display": "Frequency", "key": "freq", "type": "double_spin",
                 "min": 0.1, "max": 10.0, "default": 2.4},
                {"display": "Avg", "key": "soft_avgs", "type": "double_spin",
                 "min": 1, "max": 1e7, "default": 1},
                {"display": "Dir and Name", "key": ["save_dir", "file_name"],
                 "type": "composite", "default": ["", ""]},
                {"display": "Experiment", "key": "expt", "type": "combo",
                 "options": ["Hahn Echo", "CPMG"], "default": "Hahn Echo"},
                {"display": "Sweep start, end, step",
                 "key": ["sweep_start", "sweep_end", "sweep_step"],
                 "type": "composite", "default": [2.6, 3.0, 0.1]}
            ],
            "Readout Settings": [
                {"display": "Time Offset", "key": "h_offset", "type": "double_spin",
                 "min": 0, "max": 100.0, "default": 10.0},
                {"display": "Readout Length", "key": "readout_length", "type": "spin",
                 "min": 1, "max": 1000, "default": 10},
                {"display": "Loopback", "key": "loopback", "type": "combo",
                 "options": ["Enabled", "Disabled"], "default": "Enabled"}
            ],
            "Uncommon Settings": [
                {"display": "Repetition time", "key": "period", "type": "double_spin",
                 "min": 0.1, "max": 20e9, "default": 500.0},
                {"display": "Ch1 90 Pulse", "key": "pulse1_1", "type": "double_spin",
                 "min": 0, "max": 652100, "default": 10.0},
                {"display": "Magnetic Field, Scale, Current limit",
                 "key": ["field", "gauss_amps", "current_limit"],
                 "type": "composite", "default": [None, None, None]},
                {"display": "Reps", "key": "ave_reps", "type": "spin",
                 "min": 1, "max": 1000, "default": 1},
                {"display": "Wait Time", "key": "wait", "type": "double_spin",
                 "min": 0.1, "max": 20.0, "default": 10.0},
                {"display": "Integral only", "key": "integrate", "type": "check",
                 "default": False},
                {"display": "Initialize on read", "key": "init", "type": "check",
                 "default": True},
                {"display": "Turn off after sweep", "key": "turn_off", "type": "check",
                 "default": False}
            ],
            "Utility Settings": [
                {"display": "PSU Addr", "key": "psu_address", "type": "line_edit",
                 "default": ""},
                {"display": "Use PSU", "key": "use_psu", "type": "check",
                 "default": True},
                {"display": "Use Lakeshore", "key": "use_temp", "type": "check",
                 "default": False}
            ]
        }
    },
    "Spin Echo": {
        "groups": {
            "Main Settings": [
                {"display": "Ch1 Freq, Gain", "key": ["freq", "gain"], "type": "composite",
                 "default": [2.4, 1]},
                {"display": "Repetition time", "key": "period", "type": "double_spin",
                 "min": 0.1, "max": 100.0, "default": 10.0},
                {"display": "Ave", "key": "soft_avgs", "type": "spin",
                 "min": 1, "max": 1e7, "default": 1},
                {"display": "Dir and Name", "key": ["save_dir", "file_name"], "type": "composite",
                 "default": ["", ""]},
                {"display": "Reps", "key": "pulses", "type": "spin",
                 "min": 1, "max": 256, "default": 10},
                {"display": "Experiment", "key": "expt", "type": "combo",
                 "options": ["Hahn Echo", "CPMG"], "default": "Hahn Echo"},
                {"display": "Sweep start, end, step",
                 "key": ["sweep_start", "sweep_end", "sweep_step"], "type": "composite",
                 "default": [2.6, 3.0, 0.1]}
            ],
            "Pulse Settings": [
                {"display": "Ch1 Delay, 90 Pulse", "key": ["delay", "pulse1_1"], "type": "composite",
                 "default": [10.0, 10.0]},
                {"display": "Nut. Delay, Pulse Width", "key": ["nutation_delay", "nutation_length"],
                 "type": "composite", "default": [600000, 10.0]}
            ],
            "Second Sweep Settings": [
                {"display": "Second sweep?", "key": "sweep2", "type": "check",
                 "default": False},
                {"display": "Experiment 2", "key": "expt2", "type": "combo",
                 "options": ["Hahn Echo", "CPMG"], "default": "Hahn Echo"},
                {"display": "Sweep 2 start, end, step",
                 "key": ["sweep2_start", "sweep2_end", "sweep2_step"], "type": "composite",
                 "default": [2.6, 3.0, 0.1]}
            ],
            "Readout Settings": [
                {"display": "Time Offset", "key": "h_offset", "type": "double_spin",
                 "min": -1e5, "max": 1e5, "default": 10.0},
                {"display": "Readout Length", "key": "readout_length", "type": "spin",
                 "min": 0, "max": 5, "default": 10},
                {"display": "Loopback", "key": "loopback", "type": "combo",
                 "options": ["Enabled", "Disabled"], "default": "Enabled"}
            ],
            "Uncommon Settings": [
                {"display": "Ch1 180 Pulse Mult", "key": "mult1", "type": "double_spin",
                 "min": 0, "max": 652100, "default": 10.0},
                {"display": "Magnetic Field, Scale, Current limit",
                 "key": ["field", "gauss_amps", "current_limit"], "type": "composite",
                 "default": [None, None, None]},
                {"display": "Wait Time", "key": "wait", "type": "double_spin",
                 "min": 0, "max": 20, "default": 10.0},
                {"display": "Integral only", "key": "integrate", "type": "check",
                 "default": False},
                {"display": "Initialize on read", "key": "init", "type": "check", #COULD REMOVE
                 "default": True},
                {"display": "Turn off after sweep", "key": "turn_off", "type": "check",
                 "default": False}
            ],
            "Utility Settings": [
                {"display": "PSU Addr", "key": "psu_address", "type": "spin",
                 "min": 1, "max": 100, "default": 5},
                {"display": "Use PSU", "key": "use_psu", "type": "check",
                 "default": True},
                {"display": "Use Lakeshore", "key": "use_temp", "type": "check",
                 "default": False}
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
        self.sweep_running = True
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
        self.run_sweep()

    def stop_sweep(self):
        """Stops a sweep that is currently running"""
        if 'expt' in self.sweep.keys():
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
        self.top_menu_bar = self.init_top_menu_bar()

        # Build the main layout with splitters
        self.init_layout()

        # Load some default experiment into the settings panel
        self.current_experiment = self.experiments["Pulse Frequency Sweep"]
        self.temp_parameters = {}
        print("FINISH IMPLEMENTING")
        
        # Set up the custom stream for stdout and stderr
        dual_stream = DualStream(self.log_text)  # Create the custom stream object
        sys.stdout = dual_stream  # Redirect stdout to the dual stream
        sys.stderr = dual_stream  # Redirect stderr to the dual stream

        #change function assigned to each button
        self.settings_panel.load_settings_panel(self.experiment_templates.get("Pulse Frequency Sweep", {"main": [], "groups": {}}))

    def init_layout(self):
        """
        Build the overall layout:
         - A top menu (horizontal layout of buttons)
         - A main splitter horizontally: left = settings, right = a vertical splitter
           top = graphs, bottom = error log
        """

        # Set up the error log
        # Create a QTextEdit widget to show the logs
        self.log_text = QTextEdit(self)
        self.log_text.setReadOnly(True)  # Make the text edit read-only

        # Make the window frameless to remove the title bar
        self.setWindowFlags(Qt.FramelessWindowHint)  # This removes the title bar and system buttons

        # Create the central widget and main layout for the window
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # Add top menu (adjust layout as needed)
        main_layout.addLayout(self.top_menu_bar)

        # -- main splitter (horizontal)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(5)  # Increase grab area
        self.main_splitter.setStyleSheet("""
            QSplitter::handle {
                background: transparent;
            }
            QSplitter::handle:horizontal {
                padding-left: 4px; padding-right: 4px;
                background-color: darkgray;
            }
            QSplitter::handle:vertical {
                padding-top: 4px; padding-bottom: 4px;
                background-color: darkgray;
            }
        """)

        # Left side: settings
        self.main_splitter.addWidget(self.settings_panel)

        # Right side: a vertical splitter for graphs vs. error log
        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_splitter.setHandleWidth(5)  # Increase grab area for vertical splitter
        self.right_splitter.setStyleSheet("""
            QSplitter::handle {
                background: transparent;
            }
            QSplitter::handle:horizontal {
                padding-left: 4px; padding-right: 4px;
                background-color: darkgray;
            }
            QSplitter::handle:vertical {
                padding-top: 4px; padding-bottom: 4px;
                background-color: darkgray;
            }
        """)
        self.right_splitter.addWidget(self.graphs_panel)
        self.right_splitter.addWidget(self.log_text)
        self.main_splitter.addWidget(self.right_splitter)

        # Set stretch factors to control resizing behavior
        self.main_splitter.setStretchFactor(0, 1)  # Settings Panel (left side)
        self.main_splitter.setStretchFactor(1, 1)  # Right splitter (graph & error log)

        main_layout.addWidget(self.main_splitter)

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
        graph_layout.setContentsMargins(75, 50, 75, 50)

        # Add three Matplotlib graphs to the layout
        self.graphs = [MatplotlibCanvas() for _ in range(3)]
        for graph in self.graphs:
            graph_layout.addWidget(graph)

        return graph_section_widget


    def init_error_log(self):
        """Creates the error log panel."""
        error_log = QLabel("Error Log")
        error_log.setFrameShape(QFrame.Box)
        error_log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return error_log
    

    def init_top_menu_bar(self):
        top_menu = QHBoxLayout()
        
        # NEW: Create a vertical container for the label and dropdown.
        exp_widget = QWidget()
        exp_layout = QVBoxLayout(exp_widget)
        label = QLabel("Change Experiment Type")
        exp_layout.addWidget(label)
        exp_dropdown = QComboBox()
        exp_dropdown.addItems(list(self.experiments.keys()))
        exp_dropdown.currentTextChanged.connect(self.change_experiment_type)
        exp_layout.addWidget(exp_dropdown)
        top_menu.addWidget(exp_widget)
        
        # NEW: Create and add the indicator with a black border.
        self.running_indicator = QLabel("•")
        self.running_indicator.setFixedSize(10, 10)
        self.running_indicator.setStyleSheet("background-color: white; border: 1px solid black;")
        top_menu.addWidget(self.running_indicator)
        
        # Experiment-specific buttons remain separate.
        top_menu = self.init_experiment_specific_buttons(top_menu)
        
        # Window control buttons
        window_controls_widget = QWidget()
        window_controls_layout = QHBoxLayout(window_controls_widget)
        window_controls_layout.setContentsMargins(0, 0, 0, 0)
        minimize_btn = QPushButton("Minimize")
        minimize_btn.clicked.connect(self.showMinimized)
        fullscreen_btn = QPushButton("Toggle Full Screen")
        fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        off_btn = QPushButton("Hardware Off and Close Software")
        off_btn.clicked.connect(self.hardware_off_frontend)
        
        window_controls_layout.addWidget(minimize_btn)
        window_controls_layout.addWidget(fullscreen_btn)
        window_controls_layout.addWidget(off_btn)
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
        
        self.set_parameters_and_initialize_btn = QPushButton("Initialize")
        self.set_parameters_and_initialize_btn.clicked.connect(self.read_and_set_parameters)
        
        # Create buttons and assign them to instance variables
        self.read_unprocessed_btn = QPushButton("Read Unprocessed")
        self.read_unprocessed_btn.clicked.connect(self.read_unprocessed_frontend)
        
        self.read_processed_btn = QPushButton("Read Processed")
        self.read_processed_btn.clicked.connect(self.read_processed_frontend)
        
        self.sweep_start_stop_btn = QPushButton("Start Sweep")
        self.sweep_start_stop_btn.clicked.connect(self.toggle_start_stop_sweep_frontend)

        # Disable the action buttons initially; they will be enabled after initialization
        self.read_unprocessed_btn.setEnabled(False)
        self.read_processed_btn.setEnabled(False)
        self.sweep_start_stop_btn.setEnabled(False)
        
        experiment_buttons_layout.addWidget(self.set_parameters_and_initialize_btn, 0, 0)
        experiment_buttons_layout.addWidget(self.read_unprocessed_btn, 0, 1)
        experiment_buttons_layout.addWidget(self.read_processed_btn, 1, 1)
        experiment_buttons_layout.addWidget(self.sweep_start_stop_btn, 2, 1)

        top_menu.addWidget(experiment_buttons_widget)
        
        # Template Selection remains unchanged
        template_dropdown = QComboBox()
        template_dropdown.addItems(["Pulse Frequency Sweep", "Spin Echo"])
        template_dropdown.currentTextChanged.connect(self.change_experiment_type)
        
        # Create the indicator for running sweep
        running_indicator = QLabel("•")
        running_indicator.setFixedSize(10, 10)
        running_indicator.setStyleSheet("background-color: white;")
        
        # Run Experiment and Save Recordings widget
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
        self.init_parameters_from_template()
        self.settings_panel.load_settings_panel(
            self.experiment_templates.get(experiment_type, {"groups": {}})
        )


    def init_parameters_from_template(self):
        """Seed self.temp_parameters with every key from the current template."""
        template = self.experiment_templates.get(self.current_experiment.type, {"groups": {}})
        for group in template["groups"].values():
            for setting in group:
                underlying = setting.get("key")
                default = setting.get("default", "")
                if isinstance(underlying, list):
                    for key, d in zip(underlying, default if isinstance(default, list) else []):
                        if key not in self.temp_parameters:
                            self.temp_parameters[key] = d
                else:
                    if underlying not in self.temp_parameters:
                        self.temp_parameters[underlying] = default

    def read_and_set_parameters(self):
        tree = self.settings_panel.settings_tree
        root = tree.invisibleRootItem()
        new_params = self.current_experiment.parameters.copy()
        for i in range(root.childCount()):
            group_item = root.child(i)
            for j in range(group_item.childCount()):
                item = group_item.child(j)
                widget = tree.itemWidget(item, 1)
                underlying = getattr(widget, "_underlying_key", None)
                if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                    value = widget.value()
                elif isinstance(widget, QLineEdit):
                    value = widget.text()
                elif isinstance(widget, QComboBox):
                    value = widget.currentText()
                elif isinstance(widget, QCheckBox):
                    value = widget.isChecked()
                elif isinstance(widget, QWidget) and hasattr(widget, "composite_values"):
                    value = widget.composite_values()
                else:
                    value = None
                if underlying is not None:
                    if isinstance(underlying, list) and isinstance(value, list):
                        for key, v in zip(underlying, value):
                            new_params[key] = v
                    else:
                        new_params[underlying] = value
        self.current_experiment.set_parameters(new_params)
        
        # Enable the action buttons now that parameters have been read.
        self.read_unprocessed_btn.setEnabled(True)
        self.read_processed_btn.setEnabled(True)
        self.sweep_start_stop_btn.setEnabled(True)


        

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
        print("Shutting off")
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