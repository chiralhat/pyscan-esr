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

# this is stuff that was at the top of gui_setup.py:
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

        
class GraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)

        # Layout for the graphing widget
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)


    def update_canvas(self, time, i, q, x):
        """
        Update the canvas with the given data.
        """
        # Clear the previous plot
        self.ax.clear()

        # Plot the data
        self.ax.plot(time, i, label='CH1', color='yellow')
        self.ax.plot(time, q, label='CH2', color='blue')
        self.ax.plot(time, x, label='AMP', color='green')

        # Set labels and title
        self.ax.set_xlabel('Time (μs)')
        self.ax.set_ylabel('Signal (a.u.)')
        self.ax.legend()

        # Refresh the canvas to show the updated plot
        self.canvas.draw()

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
                {"display": "Ave", "key": "soft_avgs", "type": "double_spin",
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
                 "default": [10, 10]},
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
                {"display": "PSU Addr", "key": "psu_address", "type": "line_edit",
                 "default": ""},
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
            
        # NEW current experiment graph
        self.graph = GraphWidget()


    def init_pyscan_experiment(self):
        """
        This initializes a pyscan experiment with functions from the correct 
        experiment type scripts and GUI files.
        """
        if self.type == "Spin Echo":
            # NEW: created spinecho_gui objects from updated spinecho gui file
            self.spinecho_gui = seg.SpinechoExperiment(self.graph)
            self.spinecho_gui.init_experiment(self.devices, self.parameters, self.sweep, self.soc)
        elif self.type == "Pulse Frequency Sweep":
            # TO DO: update psg file
            psg.init_experiment(self.devices, self.parameters, self.sweep, self.soc)

    def set_parameters(self, parameters):
        """
        Takes in parameters read from the settings panel in the UI, 
        copies them into the parameters dictionary, and then modifies them slightly
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
            ttemp = self.devices.ls335.get_temp()

        # Initialize pyscan experiment if necessary
        if not self.parameters.get('init', False):
            pass  # No action required if 'init' is False
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
            
    #### NEW: Changed self.config to self.parameters
        # Initialized a current experiment object spinecho_gui in init_pyscan_experiment, 
        # put a graph object in __init__, and changed seg.read_unprocessed(...) to 
        # self.spinecho_gui.read_unprocessed(self.sig, self.parameters, self.soc)
        # TO DO: repeat all steps for any function involving pulse frequency sweep
    def read_unprocessed(self):
        """"
        Takes a snapshot of the current state and doesn't process it before display it
        """
        if self.type == "Spin Echo":
            self.spinecho_gui.read_unprocessed(self.sig, self.parameters, self.soc)
        elif self.type == "Pulse Frequency Sweep":
            psg.read_unprocessed(self.sig, self.parameters, self.soc)

    # TO DO: change these functions to mimic changes in read_unprocessed
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
        self.current_experiment = self.experiments["Spin Echo"]
        self.temp_parameters = {}
        print("FINISH IMPLEMENTING")
        
        # Set up the custom stream for stdout and stderr
        dual_stream = DualStream(self.log_text)  # Create the custom stream object
        sys.stdout = dual_stream  # Redirect stdout to the dual stream
        sys.stderr = dual_stream  # Redirect stderr to the dual stream

        #change function assigned to each button
        self.settings_panel.load_settings_panel(self.experiment_templates.get("Spin Echo", {"main": [], "groups": {}}))

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

        # Add top menu 
        main_layout.addWidget(self.top_menu_bar)

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
        
        # NEW: adds the current experiment graph to the layout
        graph_layout.addWidget(self.current_experiment.graph)

        return graph_section_widget


    def init_error_log(self):
        """Creates the error log panel."""
        error_log = QLabel("Error Log")
        error_log.setFrameShape(QFrame.Box)
        error_log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return error_log
    

    def init_top_menu_bar(self):
        # Create a horizontal layout for the top menu with reduced margins and spacing
        top_menu = QHBoxLayout()
        top_menu.setContentsMargins(5, 5, 5, 5)
        top_menu.setSpacing(10)

        # Wrap the layout in a container widget and set a fixed (smaller) height
        top_menu_container = QWidget()
        top_menu_container.setLayout(top_menu)
        #top_menu_container.setFixedHeight(40)  # Smaller top menu height

        # --- Experiment Type Selection ---
        exp_widget = QWidget()
        exp_layout = QVBoxLayout(exp_widget)
        exp_layout.setContentsMargins(0, 0, 0, 0)
        exp_layout.setSpacing(2)
        label = QLabel("Change Experiment Type")
        label.setStyleSheet("font-size: 10pt;")
        exp_layout.addWidget(label)
        exp_dropdown = QComboBox()
        exp_dropdown.addItems(list(self.experiments.keys()))
        exp_dropdown.setStyleSheet("font-size: 10pt;")
        exp_dropdown.currentTextChanged.connect(self.change_experiment_type)
        exp_layout.addWidget(exp_dropdown)
        top_menu.addWidget(exp_widget)

        # --- Experiment-Specific Buttons with Indicators ---
        top_menu = self.init_experiment_specific_buttons(top_menu)

        # --- Window Control Buttons ---
        window_controls_widget = QWidget()
        window_controls_layout = QHBoxLayout(window_controls_widget)
        window_controls_layout.setContentsMargins(0, 0, 0, 0)
        window_controls_layout.setSpacing(5)
        minimize_btn = QPushButton("Minimize")
        minimize_btn.setStyleSheet("font-size: 10pt; padding: 2px 4px;")
        minimize_btn.clicked.connect(self.showMinimized)
        fullscreen_btn = QPushButton("Toggle Full Screen")
        fullscreen_btn.setStyleSheet("font-size: 10pt; padding: 2px 4px;")
        fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        off_btn = QPushButton("Hardware Off and Close Software")
        off_btn.setStyleSheet("font-size: 10pt; padding: 2px 4px;")
        off_btn.clicked.connect(self.hardware_off_frontend)
        window_controls_layout.addWidget(minimize_btn)
        window_controls_layout.addWidget(fullscreen_btn)
        window_controls_layout.addWidget(off_btn)
        top_menu.addWidget(window_controls_widget)

        return top_menu_container

    def toggle_fullscreen(self):
        # Toggle between full screen and normal window states
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def init_experiment_specific_buttons(self, top_menu):
        experiment_buttons_widget = QWidget()
        experiment_buttons_layout = QGridLayout(experiment_buttons_widget)
        experiment_buttons_layout.setContentsMargins(0, 0, 0, 0)
        experiment_buttons_layout.setSpacing(5)

        # --- Initialize Button ---
        init_widget = QWidget()
        init_layout = QHBoxLayout(init_widget)
        init_layout.setContentsMargins(0, 0, 0, 0)
        self.set_parameters_and_initialize_btn = QPushButton("Initialize")
        self.set_parameters_and_initialize_btn.setStyleSheet("font-size: 10pt; padding: 2px 4px;")
        self.set_parameters_and_initialize_btn.clicked.connect(self.read_and_set_parameters)
        self.indicator_initialize = QLabel("•")
        self.indicator_initialize.setFixedSize(10, 10)
        self.indicator_initialize.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )
        init_layout.addWidget(self.set_parameters_and_initialize_btn)
        init_layout.addWidget(self.indicator_initialize)
        experiment_buttons_layout.addWidget(init_widget, 0, 0)

        # --- Read Unprocessed Button ---
        read_unprocessed_widget = QWidget()
        read_unprocessed_layout = QHBoxLayout(read_unprocessed_widget)
        read_unprocessed_layout.setContentsMargins(0, 0, 0, 0)
        self.read_unprocessed_btn = QPushButton("Read Unprocessed")
        self.read_unprocessed_btn.setStyleSheet("font-size: 10pt; padding: 2px 4px;")
        self.read_unprocessed_btn.clicked.connect(self.read_unprocessed_frontend)
        self.indicator_read_unprocessed = QLabel("•")
        self.indicator_read_unprocessed.setFixedSize(10, 10)
        self.indicator_read_unprocessed.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )
        read_unprocessed_layout.addWidget(self.read_unprocessed_btn)
        read_unprocessed_layout.addWidget(self.indicator_read_unprocessed)
        experiment_buttons_layout.addWidget(read_unprocessed_widget, 0, 1)

        # --- Read Processed Button ---
        read_processed_widget = QWidget()
        read_processed_layout = QHBoxLayout(read_processed_widget)
        read_processed_layout.setContentsMargins(0, 0, 0, 0)
        self.read_processed_btn = QPushButton("Read Processed")
        self.read_processed_btn.setStyleSheet("font-size: 10pt; padding: 2px 4px;")
        self.read_processed_btn.clicked.connect(self.read_processed_frontend)
        self.indicator_read_processed = QLabel("•")
        self.indicator_read_processed.setFixedSize(10, 10)
        self.indicator_read_processed.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )
        read_processed_layout.addWidget(self.read_processed_btn)
        read_processed_layout.addWidget(self.indicator_read_processed)
        experiment_buttons_layout.addWidget(read_processed_widget, 1, 1)

        # --- Start/Stop Sweep Button ---
        sweep_widget = QWidget()
        sweep_layout = QHBoxLayout(sweep_widget)
        sweep_layout.setContentsMargins(0, 0, 0, 0)
        self.sweep_start_stop_btn = QPushButton("Start Sweep")
        self.sweep_start_stop_btn.setStyleSheet("font-size: 10pt; padding: 2px 4px;")
        self.sweep_start_stop_btn.clicked.connect(self.toggle_start_stop_sweep_frontend)
        self.indicator_sweep = QLabel("•")
        self.indicator_sweep.setFixedSize(10, 10)
        self.indicator_sweep.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )
        sweep_layout.addWidget(self.sweep_start_stop_btn)
        sweep_layout.addWidget(self.indicator_sweep)
        experiment_buttons_layout.addWidget(sweep_widget, 2, 1)

        # Disable the three buttons until "Initialize" is pressed
        self.read_unprocessed_btn.setEnabled(False)
        self.read_processed_btn.setEnabled(False)
        self.sweep_start_stop_btn.setEnabled(False)

        experiment_buttons_widget.setLayout(experiment_buttons_layout)
        top_menu.addWidget(experiment_buttons_widget)
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

        # Re-disable action buttons until user clicks "Initialize"
        self.read_unprocessed_btn.setEnabled(False)
        self.read_processed_btn.setEnabled(False)
        self.sweep_start_stop_btn.setEnabled(False)

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
        # Update the Initialize indicator
        self.indicator_initialize.setStyleSheet(
            "background-color: red; border: 1px solid black; border-radius: 5px;"
        )
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
        self.current_experiment.init_pyscan_experiment()
        # Enable action buttons after initialization
        self.read_unprocessed_btn.setEnabled(True)
        self.read_processed_btn.setEnabled(True)
        self.sweep_start_stop_btn.setEnabled(True)
        print("✅ Initialized experiment with parameters:")
        for k, v in new_params.items():
            print(f"   {k}: {v}")
        self.indicator_initialize.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )
        self.read_unprocessed_btn.setEnabled(True)
        self.read_processed_btn.setEnabled(True)
        self.sweep_start_stop_btn.setEnabled(True)

    def read_unprocessed_frontend(self):
        self.indicator_read_unprocessed.setStyleSheet(
            "background-color: red; border: 1px solid black; border-radius: 5px;"
        )
        self.read_and_set_parameters()
        self.current_experiment.read_unprocessed()
        self.indicator_read_unprocessed.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )

    def read_processed_frontend(self):
        self.indicator_read_processed.setStyleSheet(
            "background-color: red; border: 1px solid black; border-radius: 5px;"
        )
        self.read_and_set_parameters()
        self.current_experiment.read_processed()
        self.indicator_read_processed.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )

    def toggle_start_stop_sweep_frontend(self):
        if self.sweep_start_stop_btn.text() == "Start Sweep":
            self.indicator_sweep.setStyleSheet(
                "background-color: red; border: 1px solid black; border-radius: 5px;"
            )
            self.read_and_set_parameters()
            self.sweep_start_stop_btn.setText("Stop Sweep")
            self.current_experiment.start_sweep()
            # (Optional) You may add code here to turn the indicator back off when the sweep completes.
        else:
            self.current_experiment.stop_sweep()
            self.sweep_start_stop_btn.setText("Start Sweep")
            self.indicator_sweep.setStyleSheet(
                "background-color: grey; border: 1px solid black; border-radius: 5px;"
            )

    def hardware_off_frontend(self):
        """calls a backend function that turns off the harware for the experiment"""
        print("Shutting off")
        try:
            self.current_experiment.hardware_off()
        finally:
            self.close()



def main():
    app = QApplication(sys.argv)
    ex = ExperimentUI()
    ex.showFullScreen()
    sys.exit(app.exec_())

    
if __name__ == "__main__":
    main()