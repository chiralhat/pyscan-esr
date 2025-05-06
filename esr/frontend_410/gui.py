import matplotlib
matplotlib.use('Qt5Agg')  # Must be done before importing pyplot!
# Do not move the above from the top of the file
from PyQt5.QtWidgets import (QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
                             QSplitter, QScrollArea, QLabel, QFrame, QComboBox, 
                             QCheckBox, QSpinBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem, 
                             QMessageBox, QTextEdit, QLineEdit, 
                             QFileDialog, QListWidgetItem,
                             QListWidget,QInputDialog, QAbstractItemView, QDialog, QPushButton, QTabWidget, QDesktopWidget)
                             
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QIcon

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import sys, os
sys.path.append('../')
from rfsoc2 import *
from time import sleep, time
from datetime import date, datetime
import pickle
import pyvisa
import requests
import pyscan as ps

import globals
from Worker import *
from graphing import *
from ExperimentType import *

lstyle = {'description_width': 'initial'}
aves = [1, 4, 16, 64, 128, 256]
voltage_limits = [0.002, 10]
tdivs = []
for n in range(9, -1, -1):
    tdivs += [2*10**-n, 4*10**-n, 10*10**-n]#[2.5*10**-n, 5*10**-n, 10*10**-n]

scopes = []

if not hasattr(ps, 'rm'):
    ps.rm = pyvisa.ResourceManager('@py')
res_list = ps.rm.list_resources()

#Global setting trees for the Pulse Frequency Sweep and Spin Echo experiment settings
sweep_list = ['Pulse Sweep',
              'Phase Sweep',
              'Rabi',
              'Inversion Sweep',
              'Period Sweep',
              'Hahn Echo',
              'EDFS',
              'Freq Sweep',
              'CPMG']

bimod_sweep_list = ['A Pulse Sweep',
              'B Pulse Sweep',
              'Both Pulse Sweep',
              'B Rabi',
              'Period Sweep',
              'Hahn Echo',
              'EDFS',
              'A Freq Sweep',
              'B Freq Sweep',
              'Both Freq Sweep',
              'DEER']

EXPERIMENT_TEMPLATES = {
    "Pulse Frequency Sweep": {
        "groups": {
            "Main Settings": [                                             
                {"display": "Frequency", "key": "freq", "type": "double_spin", 
                 "min": 50.0, "max": 14999.0, "default": 3900.0, "tool tip": "Helpful information"},
                {"display": "Gain", "key": "gain", "type": "spin", 
                 "min" : 0, "max" : 32500, "default": 32500, "tool tip": "Helpful information"},
                {"display": "Avg", "key": "soft_avgs", "type": "spin",
                 "min": 1, "max": 1000000, "default": 100, "tool tip": "Helpful information"}, 
                {"display": "Dir and Name", "key": ["save_dir", "file_name"], 
                 "type": "composite", "default": ["", ""], "tool tip": "Helpful information"},
                {"display": "Experiment", "key": "psexpt", "type": "combo", 
                 "options": ['Freq Sweep', 'Field Sweep'], "default": 'Freq Sweep'},
                {"display": "Sweep start, end, step",
                 "key": ["sweep_start", "sweep_end", "sweep_step"], 
                 "type": "composite", "default": [3850.0, 3950.0, 2.0]}],
            "Readout Settings": [
                {"display": "Time Offset", "key": "h_offset", "type": "double_spin",
                 "min": -10000.0, "max": 10000.0, "default": -0.125}, 
                {"display": "Readout Length", "key": "readout_length", "type": "double_spin", 
                 "min": 0.0, "max": 5.0, "default": 0.2}, 
                {"display": "Loopback", "key": "loopback", "type": "check", 
                 "default": False}],
            "Uncommon Settings": [
                {"display": "Repetition time", "key": "period", "type": "double_spin", 
                 "min": 0.1, "max": 2000000000.0, "default": 10.0}, 
                {"display": "Ch1 90 Pulse", "key": "pulse1_1", "type": "double_spin", 
                 "min": 0.0, "max": 652100.0, "default": 50.0}, 
                {"display": "Magnetic Field, Scale, Current limit",
                 "key": ["field", "gauss_amps", "current_limit"], 
                 "type": "composite", "default": [0.0, 276.0, 3.5]}, 
                {"display": "Reps", "key": "ave_reps", "type": "spin", 
                 "min": 1, "max": 1000, "default": 1},
                {"display": "Wait Time", "key": "wait", "type": "double_spin", 
                 "min": 0.0, "max": 20.0, "default": 0.3},
                {"display": "Integral only", "key": "integrate", "type": "check", 
                 "default": False}],
            "Utility Settings": [
                {"display": "PSU Addr", "key": "psu_address", "type": "line_edit", 
                 "default": ""},
                {"display": "Use PSU", "key": "use_psu", "type": "check", 
                 "default": False},
                {"display": "Use Lakeshore", "key": "use_temp", "type": "check", 
                 "default": False}],
            "Never Change": [
                {"display": "Scope Address", "key": "scope_address",  "type": "combo",
                 "options": res_list, "default": "USB0::1689::261::SGVJ0001055::0::INSTR"},
                {"display": "FPGA Address", "key": "fpga_address",  "type": "combo",
                "options": res_list, "default": "ASRL/dev/ttyUSB4::INSTR"},
                {"display": "Synth Address", "key": "synth_address",  "type": "combo",
                 "options": res_list, "default": "ASRL/dev/ttyACM0::INSTR"},
                {"display": "Phase", "key": "phase", "type": "double_spin",
                "min": 0.0, "max": 360.0, "default": 0.0},
                {"display": "Averaging Time (s)", "key": "sltime", "type": "double_spin",
                 "min": 0.0, "max": 20.0, "default": 0.0}
               ]
        } 
    },
    "Spin Echo": {
        "groups": {
            "Main Settings": [
                {"display": "Ch1 Freq", "key": "freq", "type": "double_spin", 
                 "min" : 50.0, "max" : 14999.0, "default": 3902.0, "tool tip": "Helpful information"},
                {"display": "Gain", "key": "gain", "type": "spin", 
                 "min" : 0, "max" : 32500, "default": 32500, "tool tip": "Helpful information"},
                {"display": "Repetition time", "key": "period", "type": "double_spin", 
                 "min": 0.1, "max": 2000000000.0, "default": 200.0, "tool tip": "Helpful information"}, #CHANGED THESE FROM 0.0, 100.0, AND 10.0
                {"display": "Ave", "key": "soft_avgs", "type": "spin",
                 "min": 1, "max": 10000000, "default": 100}, 
                {"display": "Dir and Name", "key": ["save_dir", "file_name"], "type": "composite",
                 "default": ["", ""]}, 
                {"display": "Reps", "key": "ave_reps", "type": "spin",
                 "min": 1, "max": 1000, "default": 1},
                {"display": "Experiment", "key": "expt", "type": "combo",
                 "options": sweep_list, "default": "Hahn Echo"},
                {"display": "Sweep start, end, step",
                 "key": ["sweep_start", "sweep_end", "sweep_step"], "type": "composite",
                "default": [150.0, 1000.0, 50.0]},],
            "Pulse Settings": [
                {"display": "Ch1 Delay", "key": "delay", "type": "double_spin",
                 "min": 0, "max": 652100, "default": 150.0},
                {"display": "90 Pulse", "key": "pulse1_1", "type": "double_spin",
                "min": 0, "max": 652100, "default": 50.0},
                {"display": "Nut. Delay (ns)", "key": "nutation_delay", "type": "double_spin",
                "min": 0, "max": 655360, "default": 5000.0},
                {"display": "Nut. Pulse Width", "key": "nutation_length", "type": "double_spin",
                "min": 0, "max": 655360, "default": 0.0}],
            "Second Sweep Settings": [
                {"display": "Second sweep?", "key": "sweep2", "type": "check",
                 "default": False},
                {"display": "Experiment 2", "key": "expt2", "type": "combo",
                 "options": sweep_list, "default": "Hahn Echo"},
                {"display": "Sweep 2 start, end, step",
                 "key": ["sweep2_start", "sweep2_end", "sweep2_step"], "type": "composite",
                 "default": [0, 0, 0]}], 
            "Readout Settings": [
                {"display": "Time Offset (us)", "key": "h_offset", "type": "double_spin",
                 "min": -1e5, "max": 1e5, "default": -0.025},
                {"display": "Readout Length (us)", "key": "readout_length", "type": "double_spin",
                 "min": 0.0, "max": 5.0, "default": 0.2}, 
                {"display": "Loopback", "key": "loopback", "type": "check",
                "default": False}],
            "Uncommon Settings": [
                {"display": "Ch1 180 Pulse Mult", "key": "mult1", "type": "double_spin",
                 "min": 0, "max": 652100, "default": 1.0},
                {"display": "Magnetic Field (G)", "key": "field", "type": "double_spin",
                "min": 0.0, "max": 0.0, "default": 2500.0},
                {"display": "Magnet Scale (G/A)", "key": "gauss_amps", "type": "double_spin",
                "min": 0.001, "max": 1000.0, "default": 270.0},
                {"display": "Current limit (A)", "key": "current_limit", "type": "double_spin",
                "min": 0.0, "max": 10.0, "default": 3.5},
                {"display": "Wait Time (s)", "key": "wait", "type": "double_spin",
                 "min": 0.0, "max": 20.0, "default": 0.2},
                {"display": "Integral only", "key": "integrate", "type": "check",
                 "default": False}],
            "Utility Settings": [
                {"display": "PSU Addr", "key": "psu_address", "type": "line_edit",
                 "default": ""},
                {"display": "Use PSU? (no magnet if not)", "key": "use_psu", "type": "check",
                 "default": False},
                {"display": "Use Lakeshore?", "key": "use_temp", "type": "check",
                 "default": False}],
            "Never Change": [
                {"display": "# 180 Pulses", "key": "pulses", "type": "spin",
                "min": 1, "max": 256, "default": 1},
                {"display": "Scope Address", "key": "scope_address",  "type": "combo",
                 "options": res_list, "default": "USB0::1689::261::SGVJ0001055::0::INSTR"},
                {"display": "FPGA Address", "key": "fpga_address",  "type": "combo",
                "options": res_list, "default": "ASRL/dev/ttyUSB4::INSTR"},
                {"display": "Synth Address", "key": "synth_address",  "type": "combo",
                 "options": res_list, "default": "ASRL/dev/ttyACM0::INSTR"},
                {"display": "Phase", "key": "phase", "type": "double_spin",
                "min": 0.0, "max": 360.0, "default": 0.0},
                {"display": "Auto Phase Sub", "key": "phase_sub", "type": "check",
                "default": False},
                {"display": "Field Start (G)", "key": "field_start", "type": "double_spin",
                "min": 0.0, "max": 2500.0, "default": 0.0},
                {"display": "Field End (G)", "key": "field_end", "type": "double_spin",
                "min": 0.0, "max": 2500.0, "default": 50.0},
                {"display": "Field Step (G)", "key": "field_step", "type": "double_spin",
                "min": 0.01, "max": 2500.0, "default": 1.5},
                {"display": "Sub Method", "key": "subtract", "type": "combo",
                "options": ['Phase', 'Delay', 'Both', 'None', 'Autophase'], "default": "Phase"},
                {"display": "Averaging Time (s)", "key": "sltime", "type": "double_spin",
                 "min": 0.0, "max": 20.0, "default": 0.0}
                ]      
        }
    }
}

class DualStream:
    """ A custom stream handler that writes output to both the terminal and a QTextEdit widget.
    This class is used to capture and display stdout/stderr in a PyQt GUI application,
    while also preserving terminal output. """

    def __init__(self, text_edit):
        self.text_edit = text_edit
        self.terminal = sys.__stdout__  

    def write(self, text):
        """ Writes the provided text to both the QTextEdit widget and the terminal.
        This method is used to mirror standard output (or error) to a GUI text display
        while still maintaining the original terminal output. It ensures that text is
        appended at the end of the QTextEdit and that the view auto-scrolls to show the latest entry.

        @param text -- The text string to be written to both outputs.
        """
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.End)  
        cursor.insertText(text)  
        self.text_edit.setTextCursor(cursor) 
        self.text_edit.ensureCursorVisible() 

        self.terminal.write(text)  
        self.terminal.flush()  

    def flush(self):
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

class DynamicSettingsPanel(QWidget):
    settingChanged = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.settings_tree = QTreeWidget()
        self.settings_tree.setHeaderHidden(False)
        self.settings_tree.setColumnCount(2)
        self.settings_tree.setHeaderLabels(["Setting","Value"])
        self.settings_tree.setColumnWidth(0, 200)
        self.settings_tree.setColumnWidth(1, 100)

        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setWidget(self.settings_tree)

        layout = QVBoxLayout(self)
        layout.addWidget(self.settings_scroll)

    def load_settings_panel(self, settings, default_file=None):
        """Populate settings tree from template and apply typed defaults."""
        type_map = {}
        for group in settings.get("groups", {}).values():
            for setting in group:
                stype = setting.get("type")
                key = setting.get("key")
                if isinstance(key, list):
                    for subkey in key:
                        type_map[subkey] = stype
                else:
                    type_map[key] = stype

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
                label = QLabel(setting.get("display", "N/A"))
                label.setToolTip(setting.get("tool tip", ""))
                self.settings_tree.setItemWidget(item, 0, label)

        if default_file and os.path.isfile(default_file):
            try:
                with open(default_file, 'rb') as f:
                    defaults = pickle.load(f)
            except Exception:
                defaults = {}
        else:
            defaults = {}

        tree = self.settings_tree
        root = tree.invisibleRootItem()
        for i in range(root.childCount()):
            grp = root.child(i)
            for j in range(grp.childCount()):
                item = grp.child(j)
                w = tree.itemWidget(item, 1)
                key = getattr(w, '_underlying_key', None)

                def apply_value(widget, raw_val, expected):
                    if isinstance(widget, QSpinBox):
                        widget.setValue(int(raw_val))
                    elif isinstance(widget, QDoubleSpinBox):
                        widget.setValue(float(raw_val))
                    elif isinstance(widget, QComboBox):
                        widget.setCurrentText(str(raw_val))
                    elif isinstance(widget, QCheckBox):
                        widget.setChecked(bool(raw_val))
                    elif isinstance(widget, QLineEdit):
                        widget.setText(str(raw_val))

                if isinstance(key, list):
                    layout = w.layout()
                    for idx, subkey in enumerate(key):
                        if subkey in defaults:
                            raw = defaults[subkey]
                            expected = type_map.get(subkey)
                            subw = layout.itemAt(idx).widget()
                            apply_value(subw, raw, expected)
                else:
                    if key in defaults:
                        raw = defaults[key]
                        expected = type_map.get(key)
                        apply_value(w, raw, expected)

    def create_setting_widget(self, setting):
        """Creates and returns an input widget based on the setting's type definition.
           This method interprets the 'type' field of a setting dictionary and constructs the
           appropriate Qt input widget (e.g., QSpinBox, QDoubleSpinBox, QLineEdit, etc.).
           It also handles composite widgets composed of multiple input fields.

           @param setting -- A dictionary describing a single setting. Expected keys include:
                                - 'type': Type of widget to create (e.g., 'spin', 'double_spin', 'line_edit', 'combo', 'check', 'composite')
                                - 'default': Default value(s) for the widget
                                - 'min', 'max': Numeric bounds (for spin types)
                                - 'options': List of string options (for combo boxes)
                                - 'key': Underlying key(s) to associate with this widget


            @return A QWidget-based input element appropriate for the setting. For composite widgets, a QWidget containing a layout of sub-widgets is returned."""
        stype = setting.get("type")
        widget = None
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
        self._connect_setting_signals(widget)
        return widget

    def _connect_setting_signals(self, widget):
        """
        Connects the appropriate Qt signal on `widget` (or its children, for composites)
        to emit self.settingChanged.
        """
        from PyQt5.QtWidgets import QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox, QCheckBox
        if isinstance(widget, QSpinBox):
            widget.valueChanged.connect(self.settingChanged.emit)
        elif isinstance(widget, QDoubleSpinBox):
            widget.valueChanged.connect(self.settingChanged.emit)
        elif isinstance(widget, QLineEdit):
            widget.textChanged.connect(self.settingChanged.emit)
        elif isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(self.settingChanged.emit)
        elif isinstance(widget, QCheckBox):
            widget.stateChanged.connect(self.settingChanged.emit)
        elif hasattr(widget, 'layout'):
            layout = widget.layout()
            for idx in range(layout.count()):
                subw = layout.itemAt(idx).widget()
                self._connect_setting_signals(subw)

class ExperimentUI(QMainWindow):
    """ Main UI Class """

    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("icon.png"))  

        self.experiments = {
            "Spin Echo": ExperimentType("Spin Echo"),
            "Pulse Frequency Sweep": ExperimentType("Pulse Frequency Sweep")
        }
        self.is_process_running = False
        self.settings_changed = False
        self.sweep_already_ran = False

        self.current_experiment = self.experiments["Spin Echo"]
        self.experiment_templates = EXPERIMENT_TEMPLATES
        self.temp_parameters = {}

        self.settings_panel = DynamicSettingsPanel()
        self.settings_panel.settingChanged.connect(self.on_setting_changed)

        self.queue_manager = QueueManager(self.toggle_start_stop_sweep_frontend)
        self.graphs_panel = self.init_graphs_panel()
        self.error_log = self.init_error_log_widget()
        self.top_menu_bar = self.init_top_menu_bar()

        self.init_layout()

        self.load_defaults_and_build_ui()

        self.read_unprocessed_btn.setEnabled(False)
        self.read_processed_btn.setEnabled(False)
        self.sweep_start_stop_btn.setEnabled(False)
        self.set_parameters_and_initialize_btn.setEnabled(True)

        dual_stream = DualStream(self.log_text)
        sys.stdout = dual_stream
        sys.stderr = dual_stream

        self.last_saved_graph_path = None
        self.worker_thread = None

    def get_scopes_from_backend(self):
        try:
            response = requests.get(globals.server_address + "/get_scopes", json=data, timeout=2)
            response.raise_for_status()
            data = response.json()
            global scopes
            scopes = data
            self.poll_timer.stop()  
        except Exception as e:
            self.label.setText(f"Unable to get scopes from backend... ({e})")

    def load_defaults_and_build_ui(self):
        template = self.experiment_templates[self.current_experiment.type]
        self.settings_panel.load_settings_panel(
            template,
            default_file=self.current_experiment.default_file
        )
        
    def on_setting_changed(self):
        """
        Called whenever any setting widget is edited.
        Greys out the three action buttons and re-enables "Initialize".
        """
        self.settings_changed = True
        if not self.is_process_running:
            self.read_unprocessed_btn.setEnabled(False)
            self.read_processed_btn.setEnabled(False)
            self.sweep_start_stop_btn.setEnabled(False)
            self.set_parameters_and_initialize_btn.setEnabled(True)


    def init_layout(self):
        """
        Build the overall layout:
         - A top menu (horizontal layout of buttons)
         - A main splitter horizontally: left = settings, right = a vertical splitter
           top = graphs, bottom = error log
        """
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        main_layout.addWidget(self.top_menu_bar, 1)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(5)  
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

        left_container = QVBoxLayout()
        left_widget = QWidget()
        left_widget.setLayout(left_container)
        left_container.setContentsMargins(0, 0, 0, 0)
        left_container.setSpacing(10)  

        left_container.addWidget(self.settings_panel)

        queue_wrapper = QWidget()
        queue_layout = QVBoxLayout(queue_wrapper)
        queue_layout.setContentsMargins(0, 0, 0, 0)
        queue_layout.setSpacing(0)
        queue_layout.addWidget(self.queue_manager)

        queue_wrapper.setMaximumHeight(350)  

        left_container.addWidget(queue_wrapper)

        self.main_splitter.addWidget(left_widget)

        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_splitter.setHandleWidth(5)  
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

        self.error_widget = self.init_error_log_widget()
        self.right_splitter.addWidget(self.error_widget)

        self.main_splitter.addWidget(self.right_splitter)

        self.main_splitter.setStretchFactor(0, 1)  
        self.main_splitter.setStretchFactor(1, 1)  
        self.main_splitter.setSizes([350, 650])  

        main_layout.addWidget(self.main_splitter, 15)

        self.setCentralWidget(central_widget)

        self.setWindowTitle("Experiment UI")
        self.setGeometry(100, 100, 1000, 700)  
        self.show()  
         
    def init_graphs_panel(self):
        """Creates the graphs panel containing Matplotlib graphs with tabs."""
        graph_section_widget = QWidget()
        graph_layout = QVBoxLayout(graph_section_widget)

        self.graph_tabs = QTabWidget()

        graph_tab_1 = QWidget()
        tab1_layout = QVBoxLayout(graph_tab_1)
        tab1_layout.addWidget(self.current_experiment.read_unprocessed_graph)
        self.graph_tabs.addTab(graph_tab_1, "Read Unprocessed")

        graph_tab_2 = QWidget()
        tab2_layout = QVBoxLayout(graph_tab_2)
        tab2_layout.addWidget(self.current_experiment.read_processed_graph)
        self.graph_tabs.addTab(graph_tab_2, "Read Processed")

        graph_tab_3 = QWidget()
        tab3_layout = QVBoxLayout(graph_tab_3)
        hdr3 = QHBoxLayout()
        hdr3.addWidget(QLabel("Variable:"))
        combo_2d = QComboBox()
        combo_2d.currentTextChanged.connect(self.update_2d_plot)
        combo_2d.addItems(["x","i","q"])
        hdr3.addWidget(combo_2d)
        hdr3.addStretch()
        tab3_layout.addLayout(hdr3)
        tab3_layout.addWidget(self.current_experiment.sweep_graph_2D)
        self.graph_tabs.addTab(graph_tab_3, "2D Sweep")
        self.combo_2d = combo_2d

        if self.current_experiment.type == "Spin Echo":
            graph_tab_4 = QWidget()
            tab4_layout = QVBoxLayout(graph_tab_4)
            hdr4 = QHBoxLayout()
            hdr4.addWidget(QLabel("Variable:"))
            combo_1d = QComboBox()
            combo_1d.currentTextChanged.connect(self.update_1d_plot)
            combo_1d.addItems(["xmean","imean","qmean"])  
            hdr4.addWidget(combo_1d)
            hdr4.addStretch()
            tab4_layout.addLayout(hdr4)
            tab4_layout.addWidget(self.current_experiment.sweep_graph_1D)
            self.graph_tabs.addTab(graph_tab_4, "1D Sweep")
            self.combo_1d = combo_1d

        graph_layout.addWidget(self.graph_tabs)

        graph_bottom_row = QHBoxLayout()

        self.save_graph_btn = QPushButton("Save Graph As...")
        self.save_graph_btn.clicked.connect(self.save_current_graph)
        graph_bottom_row.addWidget(self.save_graph_btn)

        self.last_saved_path_label = QLabel("No graph saved yet.")
        self.last_saved_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.last_saved_path_label.setStyleSheet("color: blue; text-decoration: underline;")
        self.last_saved_path_label.mousePressEvent = self.open_saved_graph_folder
        graph_bottom_row.addWidget(self.last_saved_path_label)

        graph_layout.addLayout(graph_bottom_row)

        return graph_section_widget

    def init_error_log_widget(self):
        """Creates a small widget with an ' Log' label and the log text area below it."""
        error_widget = QWidget()
        vlayout = QVBoxLayout(error_widget)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.setSpacing(5)

        label = QLabel("Log")
        label.setStyleSheet("font-weight: bold;")
        vlayout.addWidget(label)

        self.log_text = QTextEdit()  
        self.log_text.setReadOnly(True)
        vlayout.addWidget(self.log_text)

        return error_widget

    def init_top_menu_bar(self):
        top_menu = QHBoxLayout()
        top_menu.setContentsMargins(5, 5, 5, 5)
        top_menu.setSpacing(5)
        top_menu.setAlignment(Qt.AlignTop)  

        top_menu_container = QWidget()
        top_menu_container.setLayout(top_menu)

        exp_widget = QWidget()
        exp_layout = QVBoxLayout(exp_widget)
        exp_layout.setSpacing(0)
        exp_layout.setContentsMargins(0, 0, 0, 0)

        exp_dropdown = QComboBox()
        exp_dropdown.addItems(list(self.experiments.keys()))
        exp_dropdown.setStyleSheet("font-size: 10pt;")
        exp_dropdown.currentTextChanged.connect(self.change_experiment_type)
        exp_dropdown.setMinimumHeight(40)
        exp_layout.addWidget(exp_dropdown)

        top_menu.addWidget(exp_widget)

        top_menu.addSpacing(30)

        add_queue_btn = QPushButton("Add to Queue")
        add_queue_btn.setMinimumHeight(40)
        add_queue_btn.setStyleSheet("font-size: 10pt; padding: 4px;")
        add_queue_btn.clicked.connect(self.add_to_queue)
        top_menu.addWidget(add_queue_btn)

        top_menu = self.init_experiment_specific_buttons(top_menu)

        top_menu.addSpacing(30)

        return top_menu_container


    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def init_experiment_specific_buttons(self, top_menu):
        init_widget = QWidget()
        init_layout = QHBoxLayout(init_widget)
        init_layout.setContentsMargins(0, 0, 0, 0)
        self.set_parameters_and_initialize_btn = QPushButton("Initialize")
        self.set_parameters_and_initialize_btn.setMinimumHeight(40)
        self.set_parameters_and_initialize_btn.setStyleSheet("font-size: 10pt; padding: 2px 4px;")
        self.set_parameters_and_initialize_btn.clicked.connect(self.initialize_from_settings_panel)
        self.set_parameters_and_initialize_btn.setToolTip("Helpful information") #Tool tip here!
        self.indicator_initialize = QLabel(" ")
        self.indicator_initialize.setFixedSize(10, 10)
        self.indicator_initialize.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )
        init_layout.addWidget(self.set_parameters_and_initialize_btn)
        init_layout.addWidget(self.indicator_initialize)
        top_menu.addWidget(init_widget)


        read_unprocessed_widget = QWidget()
        read_unprocessed_layout = QHBoxLayout(read_unprocessed_widget)
        read_unprocessed_layout.setContentsMargins(0, 0, 0, 0)
        self.read_unprocessed_btn = QPushButton("Read Unprocessed")
        self.read_unprocessed_btn.setMinimumHeight(40)
        self.read_unprocessed_btn.setStyleSheet("font-size: 10pt; padding: 2px 4px;")
        self.read_unprocessed_btn.clicked.connect(self.read_unprocessed_frontend)
        self.read_unprocessed_btn.setToolTip("Helpful information")
        self.indicator_read_unprocessed = QLabel(" ")
        self.indicator_read_unprocessed.setFixedSize(10, 10)
        self.indicator_read_unprocessed.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )
        read_unprocessed_layout.addWidget(self.read_unprocessed_btn)
        read_unprocessed_layout.addWidget(self.indicator_read_unprocessed)
        top_menu.addWidget(read_unprocessed_widget)

        read_processed_widget = QWidget()
        read_processed_layout = QHBoxLayout(read_processed_widget)
        read_processed_layout.setContentsMargins(0, 0, 0, 0)
        self.read_processed_btn = QPushButton("Read Processed")
        self.read_processed_btn.setMinimumHeight(40)
        self.read_processed_btn.setStyleSheet("font-size: 10pt; padding: 2px 4px;")
        self.read_processed_btn.clicked.connect(self.read_processed_frontend)
        self.read_processed_btn.setToolTip("Helpful information") 
        self.indicator_read_processed = QLabel(" ")
        self.indicator_read_processed.setFixedSize(10, 10)
        self.indicator_read_processed.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )
        read_processed_layout.addWidget(self.read_processed_btn)
        read_processed_layout.addWidget(self.indicator_read_processed)
        top_menu.addWidget(read_processed_widget)

        sweep_widget = QWidget()
        sweep_layout = QHBoxLayout(sweep_widget)
        sweep_layout.setContentsMargins(0, 0, 0, 0)
        self.sweep_start_stop_btn = QPushButton("Start Sweep")
        self.sweep_start_stop_btn.setMinimumHeight(40)
        self.sweep_start_stop_btn.setStyleSheet("font-size: 10pt; padding: 2px 4px;")
        self.sweep_start_stop_btn.clicked.connect(self.toggle_start_stop_sweep_frontend)
        self.sweep_start_stop_btn.setToolTip("Helpful information") #Tool tip here!
        self.indicator_sweep = QLabel(" ")
        self.indicator_sweep.setFixedSize(10, 10)
        self.indicator_sweep.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )
        top_menu.addWidget(self.sweep_start_stop_btn)
        top_menu.addWidget(self.indicator_sweep)

        self.read_unprocessed_btn.setEnabled(False)
        self.read_processed_btn.setEnabled(False)
        self.sweep_start_stop_btn.setEnabled(False)

        return top_menu

    def change_experiment_type(self, experiment_type):
        if hasattr(self, 'worker'):
            self.worker.stop_sweep()
            self.indicator_sweep.setStyleSheet(
                "background-color: grey; border: 1px solid black; border-radius: 5px;"
            )

        print(f"Changing experiment type to {experiment_type}...\n")

        try:
            self.current_experiment = self.experiments[experiment_type]
            self.temp_parameters = {}
            self.init_parameters_from_template()

            self.settings_panel.load_settings_panel(
                self.experiment_templates[experiment_type],
                default_file=self.current_experiment.default_file
            )

            for i in range(self.graph_tabs.count()):
                if self.graph_tabs.tabText(i) == "1D Sweep":
                    self.graph_tabs.removeTab(i)
                    break

            if self.current_experiment.type == "Spin Echo":
                graph_tab_4 = QWidget()
                tab4_layout = QVBoxLayout(graph_tab_4)
                hdr4 = QHBoxLayout()
                hdr4.addWidget(QLabel("Variable:"))
                combo_1d = QComboBox()
                combo_1d.addItems(["xmean", "imean", "qmean"])
                hdr4.addWidget(combo_1d)
                hdr4.addStretch()
                tab4_layout.addLayout(hdr4)
                tab4_layout.addWidget(self.current_experiment.sweep_graph_1D)
                self.graph_tabs.addTab(graph_tab_4, "1D Sweep")
                self.combo_1d = combo_1d

            for idx in range(self.graph_tabs.count()):
                tab = self.graph_tabs.widget(idx)
                layout = tab.layout()
                if not layout:
                    layout = QVBoxLayout(tab)
                    tab.setLayout(layout)

                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().setParent(None)
                    elif item.layout(): 
                        nested_layout = item.layout()
                        while nested_layout.count():
                            sub_item = nested_layout.takeAt(0)
                            if sub_item.widget():
                                sub_item.widget().setParent(None)
                        layout.removeItem(nested_layout)

                if idx == 0:
                    layout.addWidget(self.current_experiment.read_unprocessed_graph)
                elif idx == 1:
                    layout.addWidget(self.current_experiment.read_processed_graph)
                elif idx == 2:
                    hdr3 = QHBoxLayout()
                    hdr3.addWidget(QLabel("Variable:"))
                    combo_2d = QComboBox()
                    combo_2d.currentTextChanged.connect(self.update_2d_plot)
                    combo_2d.addItems(["x", "i", "q"])
                    hdr3.addWidget(combo_2d)
                    hdr3.addStretch()
                    layout.addLayout(hdr3)
                    layout.addWidget(self.current_experiment.sweep_graph_2D)
                    self.combo_2d = combo_2d
                elif self.graph_tabs.tabText(idx) == "1D Sweep":
                    hdr4 = QHBoxLayout()
                    hdr4.addWidget(QLabel("Variable:"))
                    combo_1d = QComboBox()
                    combo_1d.currentTextChanged.connect(self.update_1d_plot)
                    combo_1d.addItems(["xmean", "imean", "qmean"])
                    hdr4.addWidget(combo_1d)
                    hdr4.addStretch()
                    layout.addLayout(hdr4)
                    layout.addWidget(self.current_experiment.sweep_graph_1D)
                    self.combo_1d = combo_1d

            self.read_unprocessed_btn.setEnabled(False)
            self.read_processed_btn.setEnabled(False)
            self.sweep_start_stop_btn.setEnabled(False)
            self.set_parameters_and_initialize_btn.setEnabled(True)

        except Exception as e:
            print(f"Error switching experiment: {e}")

    def update_2d_plot(self):
        try:
            if self.current_experiment.expt:
                data_name_2d = self.combo_2d.currentText()
                pg_2D = ps.PlotGenerator(
                    expt=self.current_experiment.expt, d=2,
                    x_name='t',
                    y_name=self.current_experiment.parameters['y_name'],
                    data_name=data_name_2d,
                    transpose=1
                )
                self.current_experiment.sweep_graph_2D.on_live_plot_2D((pg_2D))
        except Exception as e:
            print(f"Error updating 2d plot: {e}")
  
    
    def update_1d_plot(self):
        if self.current_experiment.expt:
            data_name_1d = self.combo_1d.currentText()
            pg_1D = ps.PlotGenerator(   
                                expt=self.current_experiment.expt, d=1,
                                x_name=self.current_experiment.parameters['y_name'],
                                data_name=data_name_1d,
                            )
            self.current_experiment.sweep_graph_1D.on_live_plot_1D((pg_1D))

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

    def initialize_from_settings_panel(self):
        self.set_parameters_and_initialize_btn.setEnabled(False)
        self.settings_changed = False

        print("Reading and setting parameters...\n")
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
                     
                    if isinstance(value, list):
                        if underlying:
                            for idx, (key, v) in enumerate(zip(underlying, value)):
                                if key == "gain" and isinstance(v, float):
                                    value[idx] = int(v)
                                    print(f"Converting 'gain' value {v} to integer.")
                else:
                    value = None
                if underlying is not None:
                    if isinstance(underlying, list) and isinstance(value, list):
                        for key, v in zip(underlying, value):
                            new_params[key] = v
                    else:
                        new_params[underlying] = value

        self.current_experiment.set_parameters(new_params) 

        self.indicator_initialize.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )

        self.sweep_already_ran = False

        self.read_unprocessed_btn.setEnabled(True)
        self.read_processed_btn.setEnabled(True)
        self.sweep_start_stop_btn.setEnabled(True)

        print("Initialized experiment with parameters:")
        for k, v in new_params.items():
            print(f"   {k}: {v}")

        print("\n")
        print("Select an action. \n")


    def read_unprocessed_frontend(self):
        self.indicator_read_unprocessed.setStyleSheet(
            "background-color: red; border: 1px solid black; border-radius: 5px;"
        )

        self.read_unprocessed_btn.setEnabled(False)
        self.read_processed_btn.setEnabled(False)
        self.sweep_start_stop_btn.setEnabled(False)
        self.set_parameters_and_initialize_btn.setEnabled(False)
        self.is_process_running = True

        self.graph_tabs.setCurrentIndex(0)

        self.worker_thread = QThread(self)
        self.worker = Worker(self.current_experiment, "read_unprocessed")
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run_snapshot)
        self.worker.updateStatus.connect(self.on_worker_status_update)
        self.worker.dataReady_se.connect(self.current_experiment.read_unprocessed_graph.update_canvas_se)
        self.worker.dataReady_ps.connect(self.current_experiment.read_unprocessed_graph.update_canvas_psweep)

        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker.finished.connect(self.reset_action_buttons)

        self.worker_thread.start()



    def read_processed_frontend(self):
            self.indicator_read_processed.setStyleSheet(
                "background-color: red; border: 1px solid black; border-radius: 5px;"
            )

            self.read_unprocessed_btn.setEnabled(False)
            self.read_processed_btn.setEnabled(False)
            self.sweep_start_stop_btn.setEnabled(False)
            self.set_parameters_and_initialize_btn.setEnabled(False)
            self.is_process_running = True

            self.graph_tabs.setCurrentIndex(1)

            self.worker_thread = QThread(self)
            self.worker = Worker(self.current_experiment, "read_processed")
            self.worker.moveToThread(self.worker_thread)

            self.worker_thread.started.connect(self.worker.run_snapshot)
            self.worker.updateStatus.connect(self.on_worker_status_update)
            self.worker.dataReady_se.connect(self.current_experiment.read_processed_graph.update_canvas_se)
            self.worker.dataReady_ps.connect(self.current_experiment.read_processed_graph.update_canvas_psweep)

            self.worker.finished.connect(self.worker_thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.worker_thread.finished.connect(self.worker_thread.deleteLater)
            self.worker.finished.connect(self.reset_action_buttons)

            self.worker_thread.start()


    def toggle_start_stop_sweep_frontend(self):
        if self.sweep_start_stop_btn.text() == "Start Sweep":
            self.read_unprocessed_btn.setEnabled(False)
            self.read_processed_btn.setEnabled(False)
            self.set_parameters_and_initialize_btn.setEnabled(False)
            self.is_process_running = True

            self.indicator_sweep.setStyleSheet(
                "background-color: red; border: 1px solid black; border-radius: 5px;"
            )
            self.sweep_start_stop_btn.setText("Stop Sweep")

            self.graph_tabs.setCurrentIndex(2)

            if self.current_experiment.type == "Pulse Frequency Sweep":
                self.worker_thread = QThread(self)
                self.worker = Worker(
                    self.current_experiment,
                    "sweep",
                    combo_2d=self.combo_2d,
                )
            elif self.current_experiment.type == "Spin Echo":
                self.worker_thread = QThread(self)
                self.worker = Worker(
                    self.current_experiment,
                    "sweep",
                    combo_2d=self.combo_2d,
                    combo_1d=self.combo_1d
                )
            self.worker.moveToThread(self.worker_thread)

            self.worker_thread.started.connect(self.worker.run_sweep)
            self.worker.live_plot_2D_update_signal.connect(
                self.current_experiment.sweep_graph_2D.on_live_plot_2D
            )
            self.worker.live_plot_1D_update_signal.connect(
                self.current_experiment.sweep_graph_1D.on_live_plot_1D
            )
            self.worker.updateStatus.connect(self.on_worker_status_update)

            self.worker.finished.connect(self.worker_thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.worker_thread.finished.connect(self.worker_thread.deleteLater)

            self.worker.finished.connect(self.on_finished_sweep)

            self.worker_thread.start()

        else:
            if hasattr(self, 'worker'):
                print("Stopping sweep…")
                self.worker.stop_sweep()
                print("Stop requested.")
                self.on_finished_sweep()
    
    def on_finished_sweep(self):
        try:
            self.sweep_already_ran = True
            self.reset_action_buttons()
        except Exception as e:
            print(e)

    def reset_action_buttons(self):
        """Re-enable all action buttons except for sweep and turn all three indicators back to grey."""
        self.read_unprocessed_btn.setEnabled(True)
        self.read_processed_btn.setEnabled(True)
        self.set_parameters_and_initialize_btn.setEnabled(True)
        for indicator in (
            self.indicator_read_unprocessed,
            self.indicator_read_processed,
        ):
            indicator.setStyleSheet(
                "background-color: grey; border: 1px solid black; border-radius: 5px;"
            )
        if self.sweep_already_ran == False:
            self.sweep_start_stop_btn.setEnabled(True)
            self.indicator_sweep.setStyleSheet(
                    "background-color: grey; border: 1px solid black; border-radius: 5px;"
                )
            self.sweep_start_stop_btn.setText("Start Sweep")

        else:
            self.sweep_start_stop_btn.setEnabled(False)
            self.indicator_sweep.setStyleSheet(
                    "background-color: grey; border: 1px solid black; border-radius: 5px;"
                )
            self.sweep_start_stop_btn.setText("Start Sweep")
        
        self.is_process_running = False


    def hardware_off_frontend(self):
        """calls a backend function that turns off the harware for the experiment"""
        print("Shutting off.")
        try:
            self.current_experiment.hardware_off()
        finally:
            self.close()

    def on_worker_status_update(self, message):
        """
        This slot receives status messages from the worker thread
        and can display them in the log area or console.
        """
        print(message) 
   

    def save_current_graph(self):
        """Saves the graph from the currently selected tab."""
        current_index = self.graph_tabs.currentIndex()

        if current_index == 0:
            fig = self.current_experiment.read_unprocessed_graph.figure
        elif current_index == 1:
            fig = self.current_experiment.read_processed_graph.figure
        elif current_index == 2:
            fig = self.current_experiment.sweep_graph_2D.figure
        elif current_index == 3:
            fig = self.current_experiment.sweep_graph_1D.figure
        else:
            return  

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Graph As...", "", "PNG Files (*.png);;PDF Files (*.pdf);;All Files (*)", options=options
        )

        if file_path:
            fig.savefig(file_path)
            self.last_saved_path_label.setText(file_path)

    def open_saved_graph_folder(self, event):
        if self.last_saved_graph_path:
            folder = os.path.dirname(self.last_saved_graph_path)
            os.system(f'open "{folder}"')  # 'xdg-open' for Linux. Use `open` for macOS, or `start` for Windows.

    def expand_queue_panel(self):
        self.queue_window = QWidget()
        self.queue_window.setWindowTitle("Queue Viewer")
        self.queue_window.setGeometry(300, 300, 500, 400)

        layout = QVBoxLayout()

        control_bar = QHBoxLayout()
        for name in ["History", "Clear", "Start/Stop"]:
            btn = QPushButton(name)
            control_bar.addWidget(btn)
        layout.addLayout(control_bar)

        layout.addWidget(QLabel("Active Queue:"))
        self.active_queue_list = QListWidget()
        layout.addWidget(self.active_queue_list)

        layout.addWidget(QLabel("Working Queue:"))
        self.working_queue_list = QListWidget()
        self.working_queue_list.setDragEnabled(True)
        self.working_queue_list.setAcceptDrops(True)
        self.working_queue_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.working_queue_list.setSpacing(2)
        layout.addWidget(self.working_queue_list)

        self.queue_window.setLayout(layout)
        self.queue_window.show()
    
    def add_to_queue(self):
        try:
            new_experiment = ExperimentType(self.current_experiment.type)

            queue_item = QueuedExperiment(
                start_stop_sweep_function = self.toggle_start_stop_sweep_frontend,
                experiment=new_experiment,
                queue_manager=self.queue_manager,
                last_used_directory=self.last_saved_graph_path
            )

            if queue_item.valid:
                self.queue_manager.add_to_working_queue(queue_item)
        except Exception as e:
            print(e)

class QueueRunnerWorker(QThread):
    experiment_locked = pyqtSignal(object)  
    experiment_unlocked = pyqtSignal(object)  
    queue_stopped = pyqtSignal()  
    hardware_error = pyqtSignal(object, str) 
    
    def __init__(self, queue_manager):
        super().__init__()
        self.queue_manager = queue_manager
        self.stop_requested = False
    
    def run(self):
        while not self.stop_requested:
            experiment = self.get_next_experiment()
            if not experiment:
                self.queue_stopped.emit()  
                return
            
            self.experiment_locked.emit(experiment)
            
            try:
                self.initialize_experiment(experiment)
            except Exception as e:
                self.hardware_error.emit(experiment, str(e))  
                self.experiment_unlocked.emit(experiment)  
                self.queue_stopped.emit()  
                return

            self.mark_experiment_done(experiment)
            self.move_to_next_experiment()  
    
    def run_worker_task(self, experiment, task):
        worker = Worker(experiment.experiment, task)  
        thread = QThread()

        worker.moveToThread(thread)

        thread.started.connect(worker.run_snapshot)

        worker.dataReady_se.connect(experiment.experiment.read_unprocessed_graph.update_canvas_se)
        worker.dataReady_ps.connect(experiment.experiment.read_unprocessed_graph.update_canvas_psweep)

        worker.updateStatus.connect(self.queue_manager.parent().on_worker_status_update) 
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        thread.start()
    
    def get_next_experiment(self):
        if self.queue_manager.active_queue_list.count() > 0:
            return self.queue_manager.active_queue_list.item(0)  
        return None
    
    def initialize_experiment(self, experiment):
        experiment.init_experiment()

        if experiment.has_sweep:
            self.run_worker_task(experiment, task="sweep")

        if experiment.has_read_unprocessed:
            self.run_worker_task(experiment, task="read_unprocessed")

        if experiment.has_read_processed:
            self.run_worker_task(experiment, task="read_processed")
    
    def mark_experiment_done(self, experiment):
        now = datetime.now()

        if not self.queue_manager.session_started:
            self.queue_manager.session_started = True
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")  
        else:
            timestamp = now.strftime("%H:%M:%S")           

        display_name = experiment.parameters_dict.get("display_name", "Unnamed Experiment")
        save_location = experiment.parameters_dict.get("save_directory", "")

        self.queue_manager.history_log.append((timestamp, display_name, save_location))

        experiment.set_done()
    
    def move_to_next_experiment(self):
        self.queue_manager.active_queue_list.takeItem(0)

class QueueManager(QWidget):
    def __init__(self, start_stop_sweep_function=None, parent=None):
        super().__init__(parent)

        self.start_stop_sweep_function = start_stop_sweep_function

        self.queue_runner = None  
        self.queue_running = False

        self.history_log = []
        self.session_started = False
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.collapsed_button = QPushButton("Currently Running: [None] ▼")
        self.collapsed_button.setMaximumHeight(40)
        self.collapsed_button.setStyleSheet("text-align: left; padding: 8px;")
        self.collapsed_button.clicked.connect(self.toggle_expand)
        self.main_layout.addWidget(self.collapsed_button)

        self.expanded_frame = QFrame()
        self.expanded_frame.setVisible(False)
        self.expanded_layout = QVBoxLayout(self.expanded_frame)
        self.expanded_layout.setContentsMargins(10, 10, 10, 10)
        self.expanded_layout.setSpacing(10)

        active_queue_bar = QHBoxLayout()
        active_label = QLabel("Active Queue:")
        active_label.setStyleSheet("font-weight: bold;")
        self.history_button = QPushButton("History")
        self.clear_button = QPushButton("Clear")
        self.toggle_run_button = QPushButton("Start")

        for btn in [self.history_button, self.clear_button, self.toggle_run_button]:
            btn.setFixedHeight(28)
            btn.setFixedWidth(70)
            btn.setStyleSheet("font-size: 10pt; padding: 2px;")

        active_queue_bar.addWidget(active_label)
        active_queue_bar.addStretch()
        active_queue_bar.addWidget(self.history_button)
        active_queue_bar.addWidget(self.clear_button)
        active_queue_bar.addWidget(self.toggle_run_button)

        self.expanded_layout.addLayout(active_queue_bar)

        self.history_button.clicked.connect(self.show_history)
        self.clear_button.clicked.connect(self.clear_queue)
        self.toggle_run_button.clicked.connect(self.start_stop_queue)

        self.active_queue_list = QListWidget()
        self.expanded_layout.addWidget(self.active_queue_list)

        self.expanded_layout.addWidget(QLabel("Working Queue:"))
        self.working_queue_list = QListWidget()
        self.working_queue_list.setDragEnabled(True)
        self.working_queue_list.setAcceptDrops(True)
        self.working_queue_list.setDragDropMode(QListWidget.InternalMove)
        self.expanded_layout.addWidget(self.working_queue_list)

        self.main_layout.addWidget(self.expanded_frame)

        self.current_running_text = "[None]"

    def start_stop_queue(self):
        """Handle the start/stop of the queue"""
        self.toggle_run_button_text()
        if self.queue_runner and self.queue_runner.isRunning():
            self.stop_queue()  
        else:
            self.queue_running = True
            print("Calling next queue item()")
            self.next_queue_item()  
    
    def stop_queue(self):
        """Request the queue to stop."""
        if self.queue_runner:
            self.queue_runner.stop_requested = True

    def next_queue_item(self):
        "Runs the next queue item and deletes from queue when complete"
        try:
            if self.active_queue_list.count != 0:
                next_experiment = self.active_queue_list.takeItem(0)
                self.current_experiment = next_experiment.experiment
                next_experiment.init_experiment()
                next_experiment.start_stop_sweep_function()
        except Exception as e:
            print(e)

    def queue_stopped_due_to_completion_or_error(self):
        """Called when the queue runner stops naturally or due to error."""
        self.queue_running = False
        self.toggle_run_button.setText("Start")  
        print("Queue has stopped.")

    def handle_hardware_error(self, experiment, error_message):
        """Handle hardware error by printing/logging."""
        print(f"Hardware error detected in experiment: {experiment.parameters_dict.get('display_name', 'Unknown')}")
        print(f"Error: {error_message}")

    def lock_experiment(self, experiment):
        """Grey out an experiment item."""
        if isinstance(experiment, QueuedExperiment):
            experiment.widget.setStyleSheet("""
                QWidget {
                    background-color: #cccccc;
                    border: 2px solid #888;
                    border-radius: 6px;
                    padding: 8px;
                }
            """)

    def unlock_experiment(self, experiment):
        """Un-grey an experiment item."""
        if isinstance(experiment, QueuedExperiment):
            experiment.widget.setStyleSheet("""
                QWidget {
                    background-color: #f9f9f9;
                    border: 2px solid #888;
                    border-radius: 6px;
                    padding: 8px;
                }
            """)
    
    def toggle_run_button_text(self):
        """
        Toggles the text between 'Start' and 'Stop' when the button is clicked.
        """
        current_text = self.toggle_run_button.text().strip()

        if current_text.lower() == "start" or current_text.lower() == "start/stop":
            self.toggle_run_button.setText("Stop")
        else:
            self.toggle_run_button.setText("Start")

    def toggle_expand(self):
        is_visible = self.expanded_frame.isVisible()
        self.expanded_frame.setVisible(not is_visible)
        arrow = "▲" if not is_visible else "▼"
        self.collapsed_button.setText(f"Currently Running: {self.current_running_text} {arrow}")

    def set_current_running(self, text):
        self.current_running_text = text
        if not self.expanded_frame.isVisible():
            self.collapsed_button.setText(f"Currently Running: {text} ▼")

    def add_to_active_queue(self, widget_item):
        self.active_queue_list.addItem(widget_item)

    def add_to_working_queue(self, queued_experiment):
        print(f"Adding queued experiment: {queued_experiment.parameters_dict['display_name']} to working queue...")
        self.working_queue_list.addItem(queued_experiment)
        self.working_queue_list.setItemWidget(queued_experiment, queued_experiment.widget)
    
    def show_history(self):
        """""""""
        Creates a new panel that shows Queue history in a scrollable pop-up
        """
        if not self.history_log:
            QMessageBox.information(self, "History", "No experiments have been run yet.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Experiment History")
        dialog.setMinimumSize(500, 400)

        layout = QVBoxLayout(dialog)

        history_text = QTextEdit()
        history_text.setReadOnly(True)

        log_entries = []
        for timestamp, name, location in self.history_log:
            log_entries.append(f"{timestamp}\nExperiment: {name}\nSaved to: {location}\n\n")

        history_text.setText(''.join(log_entries))

        layout.addWidget(history_text)

        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.exec_()

    def clear_queue(self):
        """
        Clears both the working and active queues after user confirmation.
        """

        if self.working_queue_list.count() == 0 and self.active_queue_list.count() == 0:
            return  

        reply = QMessageBox.question(
            self,
            "Confirm Clear Queue",
            "Are you sure you want to clear the queue? Experiments will be lost forever.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            while self.working_queue_list.count() > 0:
                item = self.working_queue_list.takeItem(0)
                if isinstance(item, QueuedExperiment):
                    del item.widget
                    del item.experiment
                del item  

            while self.active_queue_list.count() > 0:
                item = self.active_queue_list.takeItem(0)
                if isinstance(item, QueuedExperiment):
                    del item.widget
                    del item.experiment
                del item

class ExperimentSetupDialog(QDialog):
    def __init__(self, experiment_type, parameters, last_used_directory=None, edit_settings=False, parent=None, values=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Queued Experiment")
        self.setMinimumSize(600, 400)
        self.edit_settings = edit_settings

        self.display_name = ""
        self.save_graph_output = False
        self.save_directory = last_used_directory or os.getcwd()

        main_layout = QHBoxLayout(self)

        left_box = QVBoxLayout()

        self.name_label = QLabel("Experiment Name:")
        self.name_input = QLineEdit()
        default_name = "default name"
        self.name_input.setText(default_name)
        left_box.addWidget(self.name_label)
        left_box.addWidget(self.name_input)

        self.read_processed_checkbox = QCheckBox("Read Processed")
        left_box.addWidget(self.read_processed_checkbox)
        self.read_unprocessed_checkbox = QCheckBox("Read Unprocessed")
        left_box.addWidget(self.read_unprocessed_checkbox)
        self.sweep_checkbox = QCheckBox("Sweep")
        left_box.addWidget(self.sweep_checkbox)

        self.save_checkbox = QCheckBox("Save graph output")
        left_box.addWidget(self.save_checkbox)

        self.dir_label = QLabel("Save to:")
        self.dir_input = QLineEdit()
        self.dir_input.setText(self.save_directory)
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.choose_directory)

        dir_row = QHBoxLayout()
        dir_row.addWidget(self.dir_input)
        dir_row.addWidget(self.browse_button)

        left_box.addWidget(self.dir_label)
        left_box.addLayout(dir_row)

        button_row = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel")
        self.ok_button = QPushButton("Okay")
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.ok_button)
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button.clicked.connect(self.accept)

        left_box.addStretch()
        left_box.addLayout(button_row)

        self.settings_panel = DynamicSettingsPanel()
        self.settings_panel.load_settings_panel(EXPERIMENT_TEMPLATES[experiment_type])

        self._apply_parameters_to_settings(parameters)

        if not self.edit_settings:
            self.settings_panel.setDisabled(True) 

        main_layout.addLayout(left_box, 2)
        main_layout.addWidget(self.settings_panel, 3)

        if values:
            self.name_input.setText(values.get("display_name", "default name"))
            self.read_processed_checkbox.setChecked(values.get("read_processed", False))
            self.read_unprocessed_checkbox.setChecked(values.get("read_unprocessed", False))
            self.sweep_checkbox.setChecked(values.get("sweep", False))
            self.save_checkbox.setChecked(values.get("save_graph_output", True))
            self.dir_input.setText(values.get("save_directory", self.save_directory))

    def _apply_parameters_to_settings(self, param_dict):
        """
        Fill the right-side settings panel with current experiment parameters.
        """
        tree = self.settings_panel.settings_tree
        root = tree.invisibleRootItem()
        for i in range(root.childCount()):
            grp = root.child(i)
            for j in range(grp.childCount()):
                item = grp.child(j)
                widget = tree.itemWidget(item, 1)
                key = getattr(widget, '_underlying_key', None)

                if isinstance(key, list):
                    layout = widget.layout()
                    for idx, subkey in enumerate(key):
                        if subkey in param_dict:
                            val = param_dict[subkey]
                            sub_widget = layout.itemAt(idx).widget()
                            self._apply_value_to_widget(sub_widget, val)
                else:
                    if key in param_dict:
                        val = param_dict[key]
                        self._apply_value_to_widget(widget, val)

    def _apply_value_to_widget(self, widget, value):
        if isinstance(widget, QSpinBox):
            widget.setValue(int(value))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value))
        elif isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value))
        elif isinstance(widget, QComboBox):
            idx = widget.findText(str(value))
            if idx != -1:
                widget.setCurrentIndex(idx)

    def get_updated_parameters(self):
        """
        Read all settings from the settings panel and return as a dictionary.
        """
        updated_params = {}
        tree = self.settings_panel.settings_tree
        root = tree.invisibleRootItem()
        for i in range(root.childCount()):
            grp = root.child(i)
            for j in range(grp.childCount()):
                item = grp.child(j)
                widget = tree.itemWidget(item, 1)
                key = getattr(widget, '_underlying_key', None)

                if isinstance(key, list):
                    layout = widget.layout()
                    for idx, subkey in enumerate(key):
                        sub_widget = layout.itemAt(idx).widget()
                        updated_params[subkey] = self._get_widget_value(sub_widget)
                else:
                    if key:
                        updated_params[key] = self._get_widget_value(widget)
        return updated_params

    def _get_widget_value(self, widget):
        if isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
            return widget.value()
        elif isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QLineEdit):
            return widget.text()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        else:
            return None

    def get_values(self):
        """
        Return the left side values (not the right panel parameters).
        """
        return {
            "display_name": self.name_input.text().strip(),
            "read_processed": self.read_processed_checkbox.isChecked(),
            "read_unprocessed": self.read_unprocessed_checkbox.isChecked(),
            "sweep": self.sweep_checkbox.isChecked(),
            "save_graph_output": self.save_checkbox.isChecked(),
            "save_directory": self.dir_input.text().strip()
        }
    
    def choose_directory(self):
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.save_directory)
        if selected_dir:
            self.save_directory = selected_dir
            self.dir_input.setText(selected_dir)

class QueuedExperiment(QListWidgetItem):
    def __init__(self, start_stop_sweep_function, experiment: ExperimentType, queue_manager, last_used_directory=None, parameters_dict=None):
        super().__init__()

        self.start_stop_sweep_function = start_stop_sweep_function
        self.experiment = experiment
        self.queue_manager = queue_manager
        self.experiment_type = experiment.type

        if parameters_dict:
            self.parameters_dict = parameters_dict.copy()
            self.valid = True
        else:
            initial_params = experiment.parameters.copy()

            default_name = self.generate_default_display_name()

            dialog = ExperimentSetupDialog(
                self.experiment_type,
                initial_params,
                last_used_directory or os.getcwd(),
                values={"display_name": default_name}
            )

            if dialog.exec_() == QDialog.Rejected:
                self.valid = False
                return

            updated_params = dialog.get_updated_parameters()

            values = dialog.get_values()

            self.parameters_dict = {
                "display_name":    values["display_name"],
                "parameters":      updated_params,      
                "read_processed":  values["read_processed"],
                "read_unprocessed":values["read_unprocessed"],
                "sweep":           values["sweep"],
                "save_graph_output": values["save_graph_output"],
                "save_directory":  values["save_directory"],
                "current_queue":   "working_queue"
            }
            
            self.valid = True

        self.widget = QWidget()
        self.widget.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                border: 2px solid #888;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        self.layout = QVBoxLayout(self.widget)
        self.layout.setContentsMargins(4, 4, 4, 4)

        row_layout = QHBoxLayout()
        row_layout.setSpacing(8)

        self.label = QLabel(f"{self.parameters_dict['display_name']}")
        self.label.setStyleSheet("font-weight: bold;")
        row_layout.addWidget(self.label)
        row_layout.addStretch()

        button_size = QSize(48, 24)
        self.change_queue_button = QPushButton("Move")
        self.duplicate_button = QPushButton("Copy")
        self.delete_button = QPushButton("Delete")
        self.info_button = QPushButton("Edit")

        if self.parameters_dict.get("current_queue") == "active_queue":
            self.info_button.hide()

        row_layout.addWidget(self.change_queue_button)
        row_layout.addWidget(self.duplicate_button)
        row_layout.addWidget(self.delete_button)
        row_layout.addWidget(self.info_button)

        for btn in [self.change_queue_button, self.duplicate_button, self.delete_button, self.info_button]:
            btn.setFixedSize(button_size)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 2px;
                    border: 1px solid #aaa;
                    border-radius: 4px;
                    background-color: #e6e6e6;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
            """)

        self.delete_button.clicked.connect(self.delete_self)
        self.info_button.clicked.connect(self.show_info_popup)
        self.change_queue_button.clicked.connect(self.move_queues)
        self.duplicate_button.clicked.connect(self.duplicate)

        self.layout.addLayout(row_layout)

        self.widget.setLayout(self.layout)
        self.setSizeHint(self.widget.sizeHint())

    def generate_default_display_name(self):
        """
        Generates a unique default display name for the queued experiment.
        Format: Abbreviation:expXXX
        """
        type_abbr = {"Spin Echo": "SE", "Pulse Frequency Sweep": "PFS"}
        abbr = type_abbr.get(self.experiment_type, "UNK") 

        expt_name = self.experiment.parameters.get("expt", "exp").replace(" ", "")

        base_name = f"{abbr}:{expt_name}"

        count = 0

        for list_widget in [self.queue_manager.active_queue_list, self.queue_manager.working_queue_list]:
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if isinstance(item, QueuedExperiment):
                    other_name = item.parameters_dict.get("display_name", "")
                    if other_name.startswith(base_name):
                        count += 1

        if count == 0:
            return base_name
        else:
            return f"{base_name}{count}"

    def startDrag(self):
        listwidget = self.listWidget()
        if listwidget:
            drag = listwidget.model().supportedDragActions()

    def lock_experiment(self, experiment):
        """Lock the experiment widget (grey out)"""
        if self == experiment:
            self.widget.setStyleSheet("background-color: #d0d0d0;")  

    def unlock_experiment(self, experiment):
        """Unlock the experiment widget (un-grey)"""
        if self == experiment:
            self.widget.setStyleSheet("background-color: #f9f9f9;")  

    @property
    def has_sweep(self):
        return self.parameters_dict.get("sweep", False)

    @property
    def has_read_unprocessed(self):
        return self.parameters_dict.get("read_unprocessed", False)

    @property
    def has_read_processed(self):
        return self.parameters_dict.get("read_processed", False)

    def set_done(self):
        """Grey out the widget and disable all buttons after experiment finishes."""
        print("Marking experiment done...")
        self.widget.setStyleSheet("""
            QWidget {
                background-color: #cccccc;
                border: 2px solid #444;
                border-radius: 6px;
                padding: 8px;
            }
        """)

        for button in [self.change_queue_button, self.duplicate_button, self.delete_button, self.info_button]:
            button.setEnabled(False)

    def init_experiment(self):
        """
        Initialize the experiment hardware setup based on saved parameters.
        """
        self.experiment.set_parameters(self.parameters_dict["parameters"])

    def show_info_popup(self):
        """
        Allows the user to review and optionally edit the saved settings.
        """
        dialog = ExperimentSetupDialog(
            self.experiment_type,
            self.parameters_dict["parameters"].copy(),
            last_used_directory=self.parameters_dict["save_directory"],
            edit_settings=True,
            values=self.parameters_dict
        )
        if dialog.exec_() == QDialog.Accepted:
            values = dialog.get_values()
            self.parameters_dict["display_name"] = values["display_name"]
            self.parameters_dict["read_processed"] = values["read_processed"]
            self.parameters_dict["read_unprocessed"] = values["read_unprocessed"]
            self.parameters_dict["sweep"] = values["sweep"]
            self.parameters_dict["save_graph_output"] = values["save_graph_output"]
            self.parameters_dict["save_directory"] = values["save_directory"]

            self.parameters_dict["parameters"] = dialog.get_updated_parameters()

            self.label.setText(f"{self.parameters_dict['display_name']} — {self.experiment_type}")

    def delete_self(self):
        """
        Removes this item from the QListWidget and deletes its resources.
        """
        if self.parameters_dict["current_queue"] == "working_queue":
            row = self.queue_manager.working_queue_list.row(self)
            if row != -1:
                self.queue_manager.working_queue_list.takeItem(row)
                del self.widget
                del self.experiment
        else:
            row = self.queue_manager.active_queue_list.row(self)
            if row != -1:
                self.queue_manager.active_queue_list.takeItem(row)
                del self.widget
                del self.experiment

    def move_queues(self):
        """
        Moves this experiment to the opposite queue (working <-> active) safely.
        This duplicates the experiment and deletes the original to avoid segmentation faults.
        """
        clone_dict = self.parameters_dict.copy()

        if clone_dict["current_queue"] == "working_queue":
            clone_dict["current_queue"] = "active_queue"
            target_queue = self.queue_manager.active_queue_list
        else:
            clone_dict["current_queue"] = "working_queue"
            target_queue = self.queue_manager.working_queue_list

        new_item = QueuedExperiment(self.start_stop_sweep_function, self.experiment, self.queue_manager, parameters_dict=clone_dict)
        
        if not new_item.valid:
            return

        target_queue.addItem(new_item)
        target_queue.setItemWidget(new_item, new_item.widget)

        self.delete_self()
        
    def duplicate(self):
        """
        Duplicates this experiment in the same queue with a new name.
        """
        new_name, ok = QInputDialog.getText(
            self.widget, "Duplicate Experiment", "Enter a name for the duplicated experiment:",
            QLineEdit.Normal, self.parameters_dict["display_name"] + " (Copy)"
        )
        if not ok or not new_name.strip():
            return

        clone_dict = self.parameters_dict.copy()
        clone_dict["display_name"] = new_name.strip()

        new_item = QueuedExperiment(self.start_stop_sweep_function, self.experiment, self.queue_manager, parameters_dict=clone_dict)

        if not new_item.valid:
            return

        if self.parameters_dict["current_queue"] == "active_queue":
            self.queue_manager.active_queue_list.addItem(new_item)
            self.queue_manager.active_queue_list.setItemWidget(new_item, new_item.widget)
        else:
            self.queue_manager.working_queue_list.addItem(new_item)
            self.queue_manager.working_queue_list.setItemWidget(new_item, new_item.widget)

def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icon.png")) 
    ex = ExperimentUI()
    ex.show()
    screen = QDesktopWidget().screenGeometry()
    screen_width = screen.width()
    screen_height = screen.height()
    ex.setGeometry(0, 0, int(screen_width), int(screen_height))
    ex.setWindowIcon(QIcon("icon.png"))
    sys.exit(app.exec_())
    
if __name__ == "__main__":
    main()