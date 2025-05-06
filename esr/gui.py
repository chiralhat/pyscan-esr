import matplotlib
matplotlib.use('Qt5Agg')  # Must be done before importing pyplot!
# Do not move the above from the top of the file
from PyQt5.QtWidgets import (QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
                             QSplitter, QScrollArea, QLabel, QFrame, QComboBox, 
                             QCheckBox, QSpinBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem, 
                             QMessageBox, QTextEdit, QLineEdit, 
                             QFileDialog, QListWidgetItem,
                             QListWidget,QInputDialog, QAbstractItemView, QDialog, QPushButton, QTabWidget)
                             
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import sys, os
sys.path.append('../')
from rfsoc2 import *
from time import sleep, time
from datetime import date, datetime
import pickle
import pyvisa
import pyscan as ps

from Worker import *
from graphing import *
from ExperimentType import *

lstyle = {'description_width': 'initial'}
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
            "Main Settings": [                                             #ALL OF THESE COMMENTS REFER TO THE control_dict IN gui_setup.py
                {"display": "Frequency", "key": "freq", "type": "double_spin", #Freq is a bounded float between 50 and 14999 (contained in rfsoc controls)
                 "min": 50.0, "max": 14999.0, "default": 3900.0, "tool tip": "Helpful information"}, #CHANGED THESE VALUES FROM 0.1, 10.0, AND 2.4
                {"display": "Gain", "key": "gain", "type": "spin", 
                 "min" : 0, "max" : 32500, "default": 32500, "tool tip": "Helpful information"},
                {"display": "Avg", "key": "soft_avgs", "type": "spin", #Soft_avgs is a bounded int between 1 and 10000000 (contained in rfsoc controls)
                 "min": 1, "max": 1000000, "default": 100, "tool tip": "Helpful information"}, #EXPLICITLY MADE THESE INTS
                {"display": "Dir and Name", "key": ["save_dir", "file_name"], #Both save_dir and file_name are strings (contained in save controls)
                 "type": "composite", "default": ["", ""], "tool tip": "Helpful information"},
                {"display": "Experiment", "key": "psexpt", "type": "combo", #expt is of ipw.Dropdown type (contained in measure)
                 "options": ['Freq Sweep', 'Field Sweep'], "default": 'Freq Sweep'},
                {"display": "Sweep start, end, step",
                 "key": ["sweep_start", "sweep_end", "sweep_step"], #sweep_start, sweep_end, and sweep_step are all unbounded floats (contained in measure)
                 "type": "composite", "default": [3850.0, 3950.0, 2.0]},                
                 {"display": "2D Sweep variable", "key": "2D Sweep variable", "type": "combo",
                 "options": ["x", "i", "q"], "default": "x"},
                 {"display": "1D Sweep variable", "key": "1D Sweep variable", "type": "combo",
                 "options": ["X", "I", "Q"], "default": "Q"}],
            "Readout Settings": [
                {"display": "Time Offset", "key": "h_offset", "type": "double_spin", #h_offset is a bounded float between -10000 and 10000 (contained in rfsoc)
                 "min": -10000.0, "max": 10000.0, "default": -0.125}, #CHANGED THESE VALUES FROM 0, 1000, AND 10.0
                {"display": "Readout Length", "key": "readout_length", "type": "double_spin", #readout_length is a bounded float from 0 to 5 (contained in rfsoc)
                 "min": 0.0, "max": 5.0, "default": 0.2}, #CHANGED THESE VALUES FROM 1, 1000, AND 10 ------------------- THIS ONE WAS SAVED AS AN INTEGER IN THE PICKLE FILE AND COULD HAVE BEEN A CAUSE OF THE ERROR
                {"display": "Loopback", "key": "loopback", "type": "check", #loopback is an ipw.Checkbox (contained in rfsoc)
                 "default": False}],
            "Uncommon Settings": [
                {"display": "Repetition time", "key": "period", "type": "double_spin", #period is a bounded float from 0.1 to 2000000000 (contained in rfsoc)
                 "min": 0.1, "max": 2000000000.0, "default": 10.0}, #EXPLICITLY MADE THESE FLOATS
                {"display": "Ch1 90 Pulse", "key": "pulse1_1", "type": "double_spin", #pulse1_1 is a bounded float from 0 to 652100 (contained in rfsoc)
                 "min": 0.0, "max": 652100.0, "default": 50.0}, #EXPLICITLY MADE THESE FLOATS
                {"display": "Magnetic Field, Scale, Current limit",
                 "key": ["field", "gauss_amps", "current_limit"], #field, gauss_amps, and current_limit are all bounded floats (contained in psu) -- bounds: (0 - 2500), (0.001, 10000), (0, 10))
                 "type": "composite", "default": [0.0, 276.0, 3.5]}, #DEFAULTS CHANGED FROM NONE, NONE, NONE ---------------- THESE WERE WRITTEN TO THE PICKLE FILE AS NONE, WHICH ALSO COULD HAVE BEEN CAUSING THE ERROR
                {"display": "Reps", "key": "ave_reps", "type": "spin", #ave_reps is a bounded int from 1 to 1000 (contained in measure)
                 "min": 1, "max": 1000, "default": 1},
                {"display": "Wait Time", "key": "wait", "type": "double_spin", #wait is a bounded float from 0 to 20 (contained in measure)
                 "min": 0.0, "max": 20.0, "default": 0.3},
                {"display": "Integral only", "key": "integrate", "type": "check", #integrate is an ipw.Checkbox (contained in measure)
                 "default": False}],
            "Utility Settings": [
                {"display": "PSU Addr", "key": "psu_address", "type": "line_edit", #psu_address is an ipw.Dropdown (contained in devices)
                 "default": ""},
                {"display": "Use PSU", "key": "use_psu", "type": "check", #use_psu is an ipw.Checkbox (contained in devices)
                 "default": False},
                {"display": "Use Lakeshore", "key": "use_temp", "type": "check", #use_temp is an ipw.Checkbox (contained in devices)
                 "default": False}],
            "Never Change": [
                # {"display": "# 180 Pulses", "key": "pulses", "type": "spin",
                # "min": 1, "max": 256, "default": 1},
                {"display": "Scope Address", "key": "scope_address",  "type": "combo",
                 "options": res_list, "default": "USB0::1689::261::SGVJ0001055::0::INSTR"},
                {"display": "FPGA Address", "key": "fpga_address",  "type": "combo",
                "options": res_list, "default": "ASRL/dev/ttyUSB4::INSTR"},
                {"display": "Synth Address", "key": "synth_address",  "type": "combo",
                 "options": res_list, "default": "ASRL/dev/ttyACM0::INSTR"},
                # Commenting out any setting having to do with a second sweep because we are implementing a queue
                # also there are more settings related to this that we didn't add / comment out for the same reason
                # {"display": "Ch2 Freq (MHz)", "key": "freq2", "type": "double_spin",
                #  "min": 50.0, "max": 14999.0, "default": 3902.0},
                # {"display": "Ch2 Gain", "key": "gain2", "type": "spin",
                # "min": 0, "max": 32500, "default": 0},
                {"display": "Phase", "key": "phase", "type": "double_spin",
                "min": 0.0, "max": 360.0, "default": 0.0},
                {"display": "Averaging Time (s)", "key": "sltime", "type": "double_spin",
                 "min": 0.0, "max": 20.0, "default": 0.0}
                #freq start, stop, step might be needed here, but we could not find them
               ]
        } #THERE IS A SETTING CALLED "subtime" THAT IS CALCULATED LATER AND ADDED TO THE END OF THE PICKLE FILE. IT IS EQUAL TO (soft_avgs * (period / 400000 * ave_reps))
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
                "default": [150.0, 1000.0, 50.0]},
                {"display": "2D Sweep variable", "key": "2D Sweep variable", "type": "combo",
                 "options": ["x", "i", "q"], "default": "x"},
                 {"display": "1D Sweep variable", "key": "1D Sweep variable", "type": "combo",
                 "options": ["xmean", "imean", "qmean"], "default": "xmean"}],
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
                 "default": [0, 0, 0]}], # Changed to integers
            "Readout Settings": [
                {"display": "Time Offset (us)", "key": "h_offset", "type": "double_spin",
                 "min": -1e5, "max": 1e5, "default": -0.025},
                {"display": "Readout Length (us)", "key": "readout_length", "type": "double_spin",
                 "min": 0.0, "max": 5.0, "default": 0.2}, # Changed to doubles
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
                # Commenting out any setting having to do with a second sweep because we are implementing a queue
                # also there are more settings related to this that we didn't add / comment out for the same reason
                # {"display": "Ch2 Freq (MHz)", "key": "freq2", "type": "double_spin",
                #  "min": 50.0, "max": 14999.0, "default": 3902.0},
                # {"display": "Ch2 Gain", "key": "gain2", "type": "spin",
                # "min": 0, "max": 32500, "default": 0},
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
                # Leaving out bimod_sweep_list bc different type of experiment
                # {"display": "Experiment", "key": "bimod_expt", "type": "combo",
                #  "options": bimod_sweep_list, "default": ""},
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
        # Write to QTextEdit (UI)
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
    # Declare a signal that will fire when any setting changes
    settingChanged = pyqtSignal()

    def __init__(self):
        super().__init__()

        # 1) Create the tree
        self.settings_tree = QTreeWidget()
        self.settings_tree.setHeaderHidden(False)
        self.settings_tree.setColumnCount(2)
        self.settings_tree.setHeaderLabels(["Setting","Value"])
        self.settings_tree.setColumnWidth(0, 200)
        self.settings_tree.setColumnWidth(1, 100)

        # 2) Put it in a scroll area
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setWidget(self.settings_tree)

        # 3) Lay it out
        layout = QVBoxLayout(self)
        layout.addWidget(self.settings_scroll)

    def load_settings_panel(self, settings, default_file=None):
        """Populate settings tree from template and apply typed defaults."""
        # Build a mapping from parameter key to expected widget type
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

        # 1) Clear & build from template
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

        # 2) Load pickle defaults
        if default_file and os.path.isfile(default_file):
            try:
                with open(default_file, 'rb') as f:
                    defaults = pickle.load(f)
            except Exception:
                defaults = {}
        else:
            defaults = {}

        # 3) Apply typed defaults
        tree = self.settings_tree
        root = tree.invisibleRootItem()
        for i in range(root.childCount()):
            grp = root.child(i)
            for j in range(grp.childCount()):
                item = grp.child(j)
                w = tree.itemWidget(item, 1)
                key = getattr(w, '_underlying_key', None)

                def apply_value(widget, raw_val, expected):
                    # Convert and apply based on expected type
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

                # Handle composite widgets
                if isinstance(key, list):
                    # Composite widget holds multiple sub-widgets
                    layout = w.layout()
                    for idx, subkey in enumerate(key):
                        if subkey in defaults:
                            raw = defaults[subkey]
                            expected = type_map.get(subkey)
                            subw = layout.itemAt(idx).widget()
                            apply_value(subw, raw, expected)
                else:
                    # Single widget
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
        # 1) Single-value widgets
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
        # 2) Composite widgets: iterate through child sub-widgets
        elif hasattr(widget, 'layout'):
            layout = widget.layout()
            for idx in range(layout.count()):
                subw = layout.itemAt(idx).widget()
                self._connect_setting_signals(subw)

class ExperimentUI(QMainWindow):
    """ Main UI Class """

    def __init__(self):
        super().__init__()

        # Setup experiments
        self.experiments = {
            "Spin Echo": ExperimentType("Spin Echo"),
            "Pulse Frequency Sweep": ExperimentType("Pulse Frequency Sweep")
        }

        # For button logic
        self.is_process_running = False
        self.settings_changed = False

        # Default experiment
        self.current_experiment = self.experiments["Spin Echo"]
        self.experiment_templates = EXPERIMENT_TEMPLATES
        self.temp_parameters = {}

        # Create main UI elements
        self.settings_panel = DynamicSettingsPanel()
        self.settings_panel.settingChanged.connect(self.on_setting_changed)

        self.queue_manager = QueueManager(self.toggle_start_stop_sweep_frontend, )
        self.graphs_panel = self.init_graphs_panel()
        self.error_log = self.init_error_log_widget()
        self.top_menu_bar = self.init_top_menu_bar()

        # Build the main layout with splitters
        self.init_layout()

        # Load defaults into the settings panel
        self.load_defaults_and_build_ui()

        # After defaults, disable action buttons until initialization
        self.read_unprocessed_btn.setEnabled(False)
        self.read_processed_btn.setEnabled(False)
        self.sweep_start_stop_btn.setEnabled(False)
        self.set_parameters_and_initialize_btn.setEnabled(True)

        # Setup custom stdout/stderr stream
        dual_stream = DualStream(self.log_text)
        sys.stdout = dual_stream
        sys.stderr = dual_stream

        self.last_saved_graph_path = None
        self.worker_thread = None

    def load_defaults_and_build_ui(self):
        # 1) Build the tree from template
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
            # Grey out action buttons
            self.read_unprocessed_btn.setEnabled(False)
            self.read_processed_btn.setEnabled(False)
            self.sweep_start_stop_btn.setEnabled(False)
            # Re-enable Initialize
            self.set_parameters_and_initialize_btn.setEnabled(True)


    def init_layout(self):
        """
        Build the overall layout:
         - A top menu (horizontal layout of buttons)
         - A main splitter horizontally: left = settings, right = a vertical splitter
           top = graphs, bottom = error log
        """

        # Make the window frameless to remove the title bar
        self.setWindowFlags(Qt.FramelessWindowHint)  # This removes the title bar and system buttons

        # Create the central widget and main layout for the window
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # Add top menu 
        main_layout.addWidget(self.top_menu_bar, 1)

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

        # Left side container for settings + queue
        left_container = QVBoxLayout()
        left_widget = QWidget()
        left_widget.setLayout(left_container)
        left_container.setContentsMargins(0, 0, 0, 0)
        left_container.setSpacing(10)  # Small spacing between elements

        # Add settings panel on top
        left_container.addWidget(self.settings_panel)

        # Wrap the queue manager in a wrapper widget to enforce max height when expanded
        queue_wrapper = QWidget()
        queue_layout = QVBoxLayout(queue_wrapper)
        queue_layout.setContentsMargins(0, 0, 0, 0)
        queue_layout.setSpacing(0)
        queue_layout.addWidget(self.queue_manager)

        # Set a max height for the expanded queue view (tweak as needed)
        queue_wrapper.setMaximumHeight(350)  # You can try 250–350 depending on feel

        # Add to the left layout
        left_container.addWidget(queue_wrapper)

        # Add left side to splitter
        self.main_splitter.addWidget(left_widget)

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
        
        # The graph panel
        self.right_splitter.addWidget(self.graphs_panel)

        # The combined error widget
        self.error_widget = self.init_error_log_widget()
        self.right_splitter.addWidget(self.error_widget)

        # Add the right splitter to the main splitter
        self.main_splitter.addWidget(self.right_splitter)

        # Set stretch factors to control resizing behavior
        self.main_splitter.setStretchFactor(0, 1)  # Settings Panel (left side)
        self.main_splitter.setStretchFactor(1, 1)  # Right splitter (graph & error log)
        self.main_splitter.setSizes([1, 1])  # 50% left, 50% right


        main_layout.addWidget(self.main_splitter, 6)

        # Set the layout to the central widget
        self.setCentralWidget(central_widget)

        # Set up window title and default size
        self.setWindowTitle("Experiment UI")
        self.setGeometry(100, 100, 1000, 700)  # Default window size
        self.show()  # Show the window
         
    def init_graphs_panel(self):
        """Creates the graphs panel containing Matplotlib graphs with tabs."""
        # Create the main container widget
        graph_section_widget = QWidget()
        graph_layout = QVBoxLayout(graph_section_widget)
        # graph_layout.setContentsMargins(25, 10, 25, 25)

        # Create a tab widget for the graphs
        self.graph_tabs = QTabWidget()

        # Add tabs for each graph
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
        tab3_layout.addWidget(self.current_experiment.sweep_graph_2D)
        self.graph_tabs.addTab(graph_tab_3, "2D Sweep")

        graph_tab_4 = QWidget()
        tab3_layout = QVBoxLayout(graph_tab_4)
        tab3_layout.addWidget(self.current_experiment.sweep_graph_1D)
        self.graph_tabs.addTab(graph_tab_4, "1D Sweep")

        # Add tabs to layout
        graph_layout.addWidget(self.graph_tabs)

        # Save graph button
        self.save_graph_btn = QPushButton("Save Graph As...")
        self.save_graph_btn.clicked.connect(self.save_current_graph)
        graph_layout.addWidget(self.save_graph_btn)

        # Last saved path label
        self.last_saved_path_label = QLabel("No graph saved yet.")
        self.last_saved_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.last_saved_path_label.setStyleSheet("color: blue; text-decoration: underline;")
        self.last_saved_path_label.mousePressEvent = self.open_saved_graph_folder
        graph_layout.addWidget(self.last_saved_path_label)

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

        self.log_text = QTextEdit()  # Create the text edit for logs
        self.log_text.setReadOnly(True)
        vlayout.addWidget(self.log_text)

        return error_widget

    def init_top_menu_bar(self):
        # Create a horizontal layout for the top menu with some margins
        top_menu = QHBoxLayout()
        top_menu.setContentsMargins(5, 5, 5, 5)
        top_menu.setSpacing(5)
        top_menu.setAlignment(Qt.AlignTop)  # Align everything at the top

        # Wrap the layout in a container widget
        top_menu_container = QWidget()
        top_menu_container.setLayout(top_menu)

        # --- Experiment Type Selection ---
        exp_widget = QWidget()
        exp_layout = QVBoxLayout(exp_widget)
        # Less space between label and dropdown
        exp_layout.setSpacing(0)
        exp_layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("Change Experiment Type")
        label.setStyleSheet("font-size: 10pt;")
        label.setToolTip("Helpful information")
        exp_layout.addWidget(label)

        exp_dropdown = QComboBox()
        exp_dropdown.addItems(list(self.experiments.keys()))
        exp_dropdown.setStyleSheet("font-size: 10pt;")
        exp_dropdown.currentTextChanged.connect(self.change_experiment_type)
        exp_layout.addWidget(exp_dropdown)

        top_menu.addWidget(exp_widget)



        # Add extra horizontal spacing between "Change Experiment Type" and the next section
        top_menu.addSpacing(30)

        # --- Add to Queue Button ---
        add_queue_btn = QPushButton("Add to Queue")
        add_queue_btn.setStyleSheet("font-size: 10pt; padding: 4px;")
        add_queue_btn.clicked.connect(self.add_to_queue)
        top_menu.addWidget(add_queue_btn)

        # --- Experiment-Specific Buttons with Indicators ---
        # We pass top_menu to the function that creates the experiment buttons
        # which adds them to the same layout
        top_menu = self.init_experiment_specific_buttons(top_menu)

        # Add extra horizontal spacing between the experiment buttons and the window controls
        top_menu.addSpacing(30)

        # --- Window Control Buttons ---
        window_controls_widget = QWidget()
        window_controls_layout = QHBoxLayout(window_controls_widget)
        window_controls_layout.setContentsMargins(0, 0, 0, 0)
        window_controls_layout.setSpacing(10)

        minimize_btn = QPushButton("Minimize")
        minimize_btn.setStyleSheet("font-size: 10pt; padding: 2px 4px;")
        minimize_btn.clicked.connect(self.showMinimized)

        fullscreen_btn = QPushButton("Toggle Full Screen")
        fullscreen_btn.setStyleSheet("font-size: 10pt; padding: 2px 4px;")
        fullscreen_btn.clicked.connect(self.toggle_fullscreen)

        off_btn = QPushButton("Hardware Off and Close Software")
        off_btn.setStyleSheet("font-size: 10pt; padding: 2px 4px;")
        off_btn.clicked.connect(self.hardware_off_frontend)
        off_btn.setToolTip("Helpful information")

        window_controls_layout.addWidget(minimize_btn)
        window_controls_layout.addWidget(fullscreen_btn)
        window_controls_layout.addWidget(off_btn)

        top_menu.addWidget(window_controls_widget)

        return top_menu_container
    
    def on_setting_changed(self):
        self.settings_changed = True
        if not self.is_process_running:
            self.set_parameters_and_initialize_btn.setEnabled(True)

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
        self.set_parameters_and_initialize_btn.clicked.connect(self.initialize_from_settings_panel)
        self.set_parameters_and_initialize_btn.setToolTip("Helpful information") #Tool tip here!
        self.indicator_initialize = QLabel(" ")
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
        self.read_unprocessed_btn.setToolTip("Helpful information") #Tool tip here!
        self.indicator_read_unprocessed = QLabel(" ")
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
        self.read_processed_btn.setToolTip("Helpful information") #Tool tip here!
        self.indicator_read_processed = QLabel(" ")
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
        self.sweep_start_stop_btn.setToolTip("Helpful information") #Tool tip here!
        self.indicator_sweep = QLabel(" ")
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

    def change_experiment_type(self, experiment_type):
        # # 0) Clear the old experiment's graphs:
        # old = self.current_experiment
        # # Clear Read Unprocessed
        # old.read_unprocessed_graph.ax.clear()
        # old.read_unprocessed_graph.canvas.draw()
        # # Clear Read Processed
        # old.read_processed_graph.ax.clear()
        # old.read_processed_graph.canvas.draw()
        # # Clear 2D Sweep
        # old.sweep_graph_2D.ax.clear()
        # old.sweep_graph_2D.canvas.draw_idle()
        # # Clear 1D Sweep
        # old.sweep_graph_1D.ax.clear()
        # old.sweep_graph_1D.canvas.draw_idle()

        # If a sweep is in progress, stop it
        if hasattr(self, 'worker'):
            self.worker.stop_sweep()
            self.indicator_sweep.setStyleSheet(
                "background-color: grey; border: 1px solid black; border-radius: 5px;"
            )

        print(f"Changing experiment type to {experiment_type}...\n")

        # 1) Swap in the new ExperimentType
        self.current_experiment = self.experiments[experiment_type]
        self.temp_parameters = {}
        self.init_parameters_from_template()

        # 2) Reload settings panel for the new experiment
        self.settings_panel.load_settings_panel(
            self.experiment_templates[experiment_type],
            default_file=self.current_experiment.default_file
        )

        # 3) Re‐wire the graph tabs to the new experiment's widgets
        for idx in range(self.graph_tabs.count()):
            tab = self.graph_tabs.widget(idx)
            layout = tab.layout()
            # remove old widget
            if layout.count():
                old_w = layout.takeAt(0).widget()
                old_w.setParent(None)
            # insert new widget
            if idx == 0:
                layout.addWidget(self.current_experiment.read_unprocessed_graph)
            elif idx == 1:
                layout.addWidget(self.current_experiment.read_processed_graph)
            elif idx == 2:
                layout.addWidget(self.current_experiment.sweep_graph_2D)
            elif idx == 3:
                layout.addWidget(self.current_experiment.sweep_graph_1D)

        # 4) Reset all action buttons
        self.read_unprocessed_btn.setEnabled(False)
        self.read_processed_btn.setEnabled(False)
        self.sweep_start_stop_btn.setEnabled(False)
        self.set_parameters_and_initialize_btn.setEnabled(True)

        # Update the graphs in the existing tabs
        for i in range(self.graph_tabs.count()):
            tab_widget = self.graph_tabs.widget(i)
            layout = tab_widget.layout()

            # Clear old graph widget in the tab
            if layout.count() > 0:
                old_graph = layout.itemAt(0).widget()
                layout.removeWidget(old_graph)
                old_graph.setParent(None)

            # Add the new graph widget to the tab
            if i == 0:
                layout.addWidget(self.current_experiment.read_unprocessed_graph)
            elif i == 1:
                layout.addWidget(self.current_experiment.read_processed_graph)
            elif i == 2:
                layout.addWidget(self.current_experiment.sweep_graph_2D)
            elif i == 3:
                layout.addWidget(self.current_experiment.sweep_graph_1D)

        # Re-disable action buttons until user clicks "Initialize"
        self.read_unprocessed_btn.setEnabled(False)
        self.read_processed_btn.setEnabled(False)
        self.sweep_start_stop_btn.setEnabled(False)
        self.set_parameters_and_initialize_btn.setEnabled(True)

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
        #Button logic
        self.set_parameters_and_initialize_btn.setEnabled(False)
        self.settings_changed = False

        # Update the Initialize indicator
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
                     
                     # If the value is a list (as in composite), we need to handle individual items.
                    if isinstance(value, list):
                        # Iterate over the composite list and check for 'gain'
                        if underlying:
                            for idx, (key, v) in enumerate(zip(underlying, value)):
                                if key == "gain" and isinstance(v, float):
                                    # Convert only the 'gain' value to an integer
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
        self.current_experiment.init_pyscan_experiment()
        # Enable action buttons after initialization
        self.read_unprocessed_btn.setEnabled(True)
        self.read_processed_btn.setEnabled(True)
        self.sweep_start_stop_btn.setEnabled(True)
        print("Initialized experiment with parameters:")
        for k, v in new_params.items():
            print(f"   {k}: {v}")
        self.indicator_initialize.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )
        print("\n")
        print("Select an action. \n")


    def read_unprocessed_frontend(self):
        # 1) Turn the unprocessed indicator red
        self.indicator_read_unprocessed.setStyleSheet(
            "background-color: red; border: 1px solid black; border-radius: 5px;"
        )

        # 2) Disable all action buttons
        self.read_unprocessed_btn .setEnabled(False)
        self.read_processed_btn   .setEnabled(False)
        self.sweep_start_stop_btn .setEnabled(False)
        self.set_parameters_and_initialize_btn.setEnabled(False)
        self.is_process_running = True

        self.graph_tabs.setCurrentIndex(0)

        # 3) Spin up the worker thread
        self.worker_thread = QThread(self)
        self.worker = Worker(self.current_experiment, "read_unprocessed")
        self.worker.moveToThread(self.worker_thread)

        # 4) Hook up the worker
        self.worker_thread.started.connect(self.worker.run_snapshot)
        self.worker.updateStatus.connect(self.on_worker_status_update)
        self.worker.dataReady_se.connect(self.current_experiment.read_unprocessed_graph.update_canvas_se)
        self.worker.dataReady_ps.connect(self.current_experiment.read_unprocessed_graph.update_canvas_psweep)

        # 5) Clean up and reset UI only when the thread is really done
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker.finished.connect(self.reset_action_buttons)

        # 6) Start!
        self.worker_thread.start()



    def read_processed_frontend(self):
            # 1) Turn the processed indicator red
            self.indicator_read_processed.setStyleSheet(
                "background-color: red; border: 1px solid black; border-radius: 5px;"
            )

            # 2) Disable all action buttons
            self.read_unprocessed_btn .setEnabled(False)
            self.read_processed_btn   .setEnabled(False)
            self.sweep_start_stop_btn .setEnabled(False)
            self.set_parameters_and_initialize_btn.setEnabled(False)
            self.is_process_running = True

            self.graph_tabs.setCurrentIndex(1)

            # 3) Spin up the worker thread
            self.worker_thread = QThread(self)
            self.worker = Worker(self.current_experiment, "read_processed")
            self.worker.moveToThread(self.worker_thread)

            # 4) Hook up the worker
            self.worker_thread.started.connect(self.worker.run_snapshot)
            self.worker.updateStatus.connect(self.on_worker_status_update)
            self.worker.dataReady_se.connect(self.current_experiment.read_processed_graph.update_canvas_se)
            self.worker.dataReady_ps.connect(self.current_experiment.read_processed_graph.update_canvas_psweep)

            # 5) Clean up and reset UI only when the thread is really done
            self.worker.finished.connect(self.worker_thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.worker_thread.finished.connect(self.worker_thread.deleteLater)
            self.worker.finished.connect(self.reset_action_buttons)

            # 6) Start!
            self.worker_thread.start()


    def toggle_start_stop_sweep_frontend(self):
        # If we're not currently sweeping, start:
        if self.sweep_start_stop_btn.text() == "Start Sweep":
            # Disable all action buttons
            self.read_unprocessed_btn.setEnabled(False)
            self.read_processed_btn.setEnabled(False)
            self.set_parameters_and_initialize_btn.setEnabled(False)
            self.is_process_running = True

            # Turn the sweep indicator red and flip the button text
            self.indicator_sweep.setStyleSheet(
                "background-color: red; border: 1px solid black; border-radius: 5px;"
            )
            self.sweep_start_stop_btn.setText("Stop Sweep")

            self.graph_tabs.setCurrentIndex(2)

            # Spin up the worker thread
            self.worker_thread = QThread(self)
            self.worker = Worker(self.current_experiment, "sweep")
            self.worker.moveToThread(self.worker_thread)

            # Connect the sweep logic & live-plot signals
            self.worker_thread.started.connect(self.worker.run_sweep)
            self.worker.live_plot_2D_update_signal.connect(
                self.current_experiment.sweep_graph_2D.on_live_plot_2D
            )
            self.worker.live_plot_1D_update_signal.connect(
                self.current_experiment.sweep_graph_1D.on_live_plot_1D
            )
            self.worker.updateStatus.connect(self.on_worker_status_update)

            # Clean up thread on finish
            self.worker.finished.connect(self.worker_thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.worker_thread.finished.connect(self.worker_thread.deleteLater)

            # ← NEW: reset UI only when sweep really finishes
            self.worker.finished.connect(self.reset_action_buttons)
            #self.worker.finished.connect(self.queue_manager.next_queue_item)

            # Kick it off
            self.worker_thread.start()

        else:
            # If the button read "Stop Sweep", request the worker to halt
            if hasattr(self, 'worker'):
                print("Stopping sweep…")
                self.worker.stop_sweep()
                print("Stop requested.")

    def reset_action_buttons(self):
        """Re-enable all action buttons and turn all three indicators back to grey."""
        # 1) Re-enable the buttons
        self.read_unprocessed_btn .setEnabled(True)
        self.read_processed_btn   .setEnabled(True)
        self.sweep_start_stop_btn .setEnabled(True)
        self.set_parameters_and_initialize_btn.setEnabled(True)

        # 2) Turn the three task-indicators back to grey
        for indicator in (
            self.indicator_read_unprocessed,
            self.indicator_read_processed,
            self.indicator_sweep
        ):
            indicator.setStyleSheet(
                "background-color: grey; border: 1px solid black; border-radius: 5px;"
            )

        # 3) Reset sweep button text (in case it was “Stop Sweep”)
        self.sweep_start_stop_btn.setText("Start Sweep")

        # 4) Clear the “busy” flag
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
   
            
    # def save_current_graph(self):
    #     options = QFileDialog.Options()
    #     file_path, _ = QFileDialog.getSaveFileName(self, "Save Graph As", "", "PNG Files (*.png);;All Files (*)", options=options)
    #     if file_path:
    #         self.current_experiment.graph.figure.savefig(file_path)
    #         self.last_saved_graph_path = file_path
    #         self.last_saved_path_label.setText(f"Last saved to: {file_path}")
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
            return  # Unexpected index, do nothing

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

        # Top control buttons
        control_bar = QHBoxLayout()
        for name in ["History", "Clear", "Start/Stop"]:
            btn = QPushButton(name)
            control_bar.addWidget(btn)
        layout.addLayout(control_bar)

        # Active Queue
        layout.addWidget(QLabel("Active Queue:"))
        self.active_queue_list = QListWidget()
        layout.addWidget(self.active_queue_list)

        # Working Queue
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
        # Create new experiment based on current type
        new_experiment = ExperimentType(self.current_experiment.type)
        # Optional: clone parameters if needed
        # new_experiment.set_parameters(self.current_experiment.parameters.copy())

        # Pass the full QueueManager instance
        queue_item = QueuedExperiment(
            experiment=new_experiment,
            queue_manager=self.queue_manager,
            last_used_directory=self.last_saved_graph_path
        )

        if queue_item.valid:
            self.queue_manager.add_to_working_queue(queue_item)

        # Optionally update the queue’s collapsed display text
        # self.queue_manager.set_current_running(queue_item.display_name)

class QueueRunnerWorker(QThread):
    experiment_locked = pyqtSignal(object)  # To grey out the experiment
    experiment_unlocked = pyqtSignal(object)  # To un-grey it if an error occurs
    queue_stopped = pyqtSignal()  # To stop the queue if needed
    hardware_error = pyqtSignal(object, str)  # To signal hardware error details
    
    def __init__(self, queue_manager):
        super().__init__()
        self.queue_manager = queue_manager
        self.stop_requested = False
    
    def run(self):
        while not self.stop_requested:
            # Get next experiment
            experiment = self.get_next_experiment()
            if not experiment:
                self.queue_stopped.emit()  # No experiments left, stop the queue
                return
            
            self.experiment_locked.emit(experiment)  # Lock (grey out) the experiment
            
            try:
                # Try to initialize and run the experiment
                self.initialize_experiment(experiment)
            except Exception as e:
                self.hardware_error.emit(experiment, str(e))  # Catch hardware error
                self.experiment_unlocked.emit(experiment)  # Un-grey the experiment
                self.queue_stopped.emit()  # Stop the queue
                return

            self.mark_experiment_done(experiment)
            self.move_to_next_experiment()  # Move to next experiment in queue
    
    def run_worker_task(self, experiment, task):
        worker = Worker(experiment.experiment, task)  # Worker needs ExperimentType, not QueuedExperiment
        thread = QThread()

        worker.moveToThread(thread)

        thread.started.connect(worker.run_snapshot)

        worker.dataReady_se.connect(experiment.experiment.read_unprocessed_graph.update_canvas_se)
        worker.dataReady_ps.connect(experiment.experiment.read_unprocessed_graph.update_canvas_psweep)

        worker.updateStatus.connect(self.queue_manager.parent().on_worker_status_update)  # Pipe logs nicely
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        thread.start()
    
    def get_next_experiment(self):
        # Retrieve the next active experiment (first in the active queue)
        if self.queue_manager.active_queue_list.count() > 0:
            return self.queue_manager.active_queue_list.item(0)  # Get first item in the list
        return None
    
    def initialize_experiment(self, experiment):
        # Initialize the experiment hardware
        experiment.init_experiment()

        if experiment.has_sweep:
            self.run_worker_task(experiment, task="sweep")

        if experiment.has_read_unprocessed:
            self.run_worker_task(experiment, task="read_unprocessed")

        if experiment.has_read_processed:
            self.run_worker_task(experiment, task="read_processed")
    
    def mark_experiment_done(self, experiment):

        # Writing to Queue History
        now = datetime.now()

        if not self.queue_manager.session_started:
            self.queue_manager.session_started = True
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")  # First run: full date + time
        else:
            timestamp = now.strftime("%H:%M:%S")           # Later runs: only time

        display_name = experiment.parameters_dict.get("display_name", "Unnamed Experiment")
        save_location = experiment.parameters_dict.get("save_directory", "")

        self.queue_manager.history_log.append((timestamp, display_name, save_location))

        # Mark experiment as done
        experiment.set_done()
    
    def move_to_next_experiment(self):
        # Move to next experiment (remove it from the active queue)
        self.queue_manager.active_queue_list.takeItem(0)

class QueueManager(QWidget):
    def __init__(self, start_stop_sweep_function=None, parent=None):
        super().__init__(parent)

        self.start_stop_sweep_function = start_stop_sweep_function

        # Queue attributes
        self.queue_runner = None  # Don't create QueueRunnerWorker yet
        self.queue_running = False

        self.history_log = []
        self.session_started = False
        
        # UI Setup
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Collapsed Button
        self.collapsed_button = QPushButton("Currently Running: [None] ▼")
        self.collapsed_button.setMaximumHeight(40)
        self.collapsed_button.setStyleSheet("text-align: left; padding: 8px;")
        self.collapsed_button.clicked.connect(self.toggle_expand)
        self.main_layout.addWidget(self.collapsed_button)

        # Expanded Frame (initially hidden)
        self.expanded_frame = QFrame()
        self.expanded_frame.setVisible(False)
        self.expanded_layout = QVBoxLayout(self.expanded_frame)
        self.expanded_layout.setContentsMargins(10, 10, 10, 10)
        self.expanded_layout.setSpacing(10)

        # Active Queue Label + Control Buttons
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

        # Connect button signals
        self.history_button.clicked.connect(self.show_history)
        self.clear_button.clicked.connect(self.clear_queue)
        self.toggle_run_button.clicked.connect(self.start_stop_queue)

        # Queues
        self.active_queue_list = QListWidget()
        self.expanded_layout.addWidget(self.active_queue_list)

        self.expanded_layout.addWidget(QLabel("Working Queue:"))
        self.working_queue_list = QListWidget()
        self.working_queue_list.setDragEnabled(True)
        self.working_queue_list.setAcceptDrops(True)
        self.working_queue_list.setDragDropMode(QListWidget.InternalMove)
        self.expanded_layout.addWidget(self.working_queue_list)

        self.working_queue_list.model().rowsMoved.connect(self._fix_single_item_drag)


        # Add expanded frame
        self.main_layout.addWidget(self.expanded_frame)

        self.current_running_text = "[None]"

    def start_stop_queue(self):
        """Handle the start/stop of the queue"""
        self.toggle_run_button_text()
        if self.queue_runner and self.queue_runner.isRunning():
            self.stop_queue()  # Stop the queue
        else:
            self.queue_running = True
            self.next_queue_item()  # Start the queue
    
    # def start_queue(self):
    #     """Start the queue by launching a QueueRunnerWorker in a new thread."""
    #     if self.queue_runner and self.queue_runner.isRunning():
    #         print("Queue is already running.")
    #         return

    #     # Create a fresh worker
    #     self.queue_runner = QueueRunnerWorker(self)

    #     # Connect core queue signals
    #     self.queue_runner.queue_stopped.connect(self.queue_stopped_due_to_completion_or_error)
    #     self.queue_runner.hardware_error.connect(self.handle_hardware_error)

    #     # Connect worker to existing experiments
    #     for list_widget in [self.active_queue_list, self.working_queue_list]:
    #         for i in range(list_widget.count()):
    #             item = list_widget.item(i)
    #             if isinstance(item, QueuedExperiment):
    #                 self.queue_runner.experiment_locked.connect(item.lock_experiment)
    #                 self.queue_runner.experiment_unlocked.connect(item.unlock_experiment)

    #     # Also make sure any future-added experiments are connected correctly

    #     # Start
    #     self.queue_running = True
    #     self.queue_runner.start()
    
    def stop_queue(self):
        """Request the queue to stop."""
        if self.queue_runner:
            self.queue_runner.stop_requested = True

    def next_queue_item(self):
        "Runs the next queue item and deletes from queue when complete"
        if self.active_queue_list.count != 0:
            next_experiment = self.active_queue_list.takeItem(0)
            next_experiment.init_experiment()
            next_experiment.experiment.experiment_type.toggle_start_stop_sweep_frontend()
            

    def queue_stopped_due_to_completion_or_error(self):
        """Called when the queue runner stops naturally or due to error."""
        self.queue_running = False
        self.toggle_run_button.setText("Start")  # Reset button to Start
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
            # Optionally disable buttons here too

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
            # Optionally re-enable buttons
    
    def _fix_single_item_drag(self, *args):
        """
        After a drag event completes, forcibly re-set the widget for all items.
        This fixes the bug where dragging a single item makes the widget vanish or look 'blued out'.
        """
        for i in range(self.working_queue_list.count()):
            item = self.working_queue_list.item(i)
            if isinstance(item, QueuedExperiment):
                self.working_queue_list.setItemWidget(item, item.widget)

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
        # if queued_experiment.valid:
        #     self.working_queue_list.add_experiment_item(queued_experiment, queued_experiment.widget)
    
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
            return  # Both queues are empty, do nothing

        # if self.working_queue_list.count() == 0 and self.active_queue_list.count() == 0:
        reply = QMessageBox.question(
            self,
            "Confirm Clear Queue",
            "Are you sure you want to clear the queue? Experiments will be lost forever.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Clear working queue
            while self.working_queue_list.count() > 0:
                item = self.working_queue_list.takeItem(0)
                if isinstance(item, QueuedExperiment):
                    del item.widget
                    del item.experiment
                del item  # Make sure to delete the item too

            # Clear active queue
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

        # === Left Input Column ===
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

        # Bottom buttons
        button_row = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel")
        self.ok_button = QPushButton("Okay")
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.ok_button)
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button.clicked.connect(self.accept)

        left_box.addStretch()
        left_box.addLayout(button_row)

        # === Right Scrollable Summary Panel ===
        self.settings_panel = DynamicSettingsPanel()
        self.settings_panel.load_settings_panel(EXPERIMENT_TEMPLATES[experiment_type])

        # Load provided parameter values into settings panel
        self._apply_parameters_to_settings(parameters)

        if not self.edit_settings:
            self.settings_panel.setDisabled(True)  # 🔥 Gray out entire right panel if not editable

        # Combine into main layout
        main_layout.addLayout(left_box, 2)
        main_layout.addWidget(self.settings_panel, 3)


        # Fill left-side fields if values provided
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
                    # Composite keys
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

# class QueueListWidget(QListWidget):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self._item_widgets = {}  # Store widgets here

#     def add_experiment_item(self, item: QListWidgetItem, widget: QWidget):
#         self.addItem(item)
#         self.setItemWidget(item, widget)
#         self._item_widgets[item] = widget  # Save for later recovery

#     def dropEvent(self, event):
#         super().dropEvent(event)
#         # Reassign widgets after drag/drop
#         for i in range(self.count()):
#             item = self.item(i)
#             if item in self._item_widgets:
#                 self.setItemWidget(item, self._item_widgets[item])

class QueuedExperiment(QListWidgetItem):
    def __init__(self, experiment: ExperimentType, queue_manager, last_used_directory=None, parameters_dict=None):
        super().__init__()

        self.experiment = experiment
        self.queue_manager = queue_manager
        self.experiment_type = experiment.type

        # If copying from existing parameters
        if parameters_dict:
            self.parameters_dict = parameters_dict.copy()
            self.valid = True
        else:
            initial_params = experiment.parameters.copy()

            # Generate the better default display name
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

            values = dialog.get_values()

            self.parameters_dict = {
                "display_name": values["display_name"],
                "parameters": initial_params,
                "read_processed": values["read_processed"],
                "read_unprocessed": values["read_unprocessed"],
                "sweep": values["sweep"],
                "save_graph_output": values["save_graph_output"],
                "save_directory": values["save_directory"],
                "current_queue": "working_queue"
            }
            self.valid = True

        # -- UI Setup --
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
        self.setText(self.parameters_dict['display_name'])  # Helps drag preview look normal
        self.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)
        # self.queue_manager.add_to_working_queue(self)

    def generate_default_display_name(self):
        """
        Generates a unique default display name for the queued experiment.
        Format: Abbreviation:expXXX
        """
        type_abbr = {"Spin Echo": "SE", "Pulse Frequency Sweep": "PFS"}
        abbr = type_abbr.get(self.experiment_type, "UNK")  # fallback abbreviation

        # Use self.experiment.parameters directly because parameters_dict not created yet
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
        # This method initiates dragging this item manually
        listwidget = self.listWidget()
        if listwidget:
            drag = listwidget.model().supportedDragActions()

    def lock_experiment(self, experiment):
        """Lock the experiment widget (grey out)"""
        if self == experiment:
            self.widget.setStyleSheet("background-color: #d0d0d0;")  # Grey out the widget

    def unlock_experiment(self, experiment):
        """Unlock the experiment widget (un-grey)"""
        if self == experiment:
            self.widget.setStyleSheet("background-color: #f9f9f9;")  # Un-grey the widget

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
        # Grey out the background
        self.widget.setStyleSheet("""
            QWidget {
                background-color: #cccccc;
                border: 2px solid #444;
                border-radius: 6px;
                padding: 8px;
            }
        """)

        # Disable all buttons
        for button in [self.change_queue_button, self.duplicate_button, self.delete_button, self.info_button]:
            button.setEnabled(False)

    def init_experiment(self):
        """
        Initialize the experiment hardware setup based on saved parameters.
        """
        self.experiment.set_parameters(self.parameters_dict["parameters"])
        self.experiment.init_pyscan_experiment()

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
            # Update left side fields
            values = dialog.get_values()
            self.parameters_dict["display_name"] = values["display_name"]
            self.parameters_dict["read_processed"] = values["read_processed"]
            self.parameters_dict["read_unprocessed"] = values["read_unprocessed"]
            self.parameters_dict["sweep"] = values["sweep"]
            self.parameters_dict["save_graph_output"] = values["save_graph_output"]
            self.parameters_dict["save_directory"] = values["save_directory"]

            # Update right side parameters
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
        # Prepare a full clone of parameters
        clone_dict = self.parameters_dict.copy()

        # Swap the queue type
        if clone_dict["current_queue"] == "working_queue":
            clone_dict["current_queue"] = "active_queue"
            target_queue = self.queue_manager.active_queue_list
        else:
            clone_dict["current_queue"] = "working_queue"
            target_queue = self.queue_manager.working_queue_list

        # Create a new QueuedExperiment using the cloned parameters
        new_item = QueuedExperiment(self.experiment, self.queue_manager, parameters_dict=clone_dict)

        if not new_item.valid:
            return

        # Add to the target queue
        target_queue.addItem(new_item)
        target_queue.setItemWidget(new_item, new_item.widget)

        # Delete the original item
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

        new_item = QueuedExperiment(self.experiment, self.queue_manager, parameters_dict=clone_dict)

        if not new_item.valid:
            return

        if self.parameters_dict["current_queue"] == "active_queue":
            self.queue_manager.active_queue_list.addItem(new_item)
            self.queue_manager.active_queue_list.setItemWidget(new_item, new_item.widget)
        else:
            self.queue_manager.working_queue_list.addItem(new_item)
            self.queue_manager.working_queue_list.setItemWidget(new_item, new_item.widget)
        def init_experiment(self):
            """
            Should be called by the parent list or queue manager.
            Sets up internal state and initializes hardware logic.
            """
            self.experiment.set_parameters(self.parameters)
            self.experiment.init_pyscan_experiment()

def main():
    app = QApplication(sys.argv)
    ex = ExperimentUI()
    ex.showFullScreen()
    sys.exit(app.exec_())
    
if __name__ == "__main__":
    main()