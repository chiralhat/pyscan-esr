"""
gui.py

This is the main GUI module built using PyQt5. It defines the graphical interface for configuring,
running, and visualizing Spin Echo and Pulse Frequency Sweep experiments. The GUI includes dynamic
settings panels, live graphing tabs, queue-based experiment automation, and threaded background
execution to keep the interface responsive.

Key Interactions:
- Uses `ExperimentType` to manage backend logic for each experiment type.
- Uses `Worker` to execute read and sweep tasks in separate threads.
- Embeds `GraphWidget` and `SweepPlotWidget` from `graphing.py` for live plotting.
- Communicates with a Flask-based backend (see `server.py`) to control hardware and collect data.
"""

import matplotlib

matplotlib.use("Qt5Agg")  # Must be done before importing pyplot!
# Do not move the above from the top of the file
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QSplitter,
    QScrollArea,
    QLabel,
    QFrame,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QTextEdit,
    QLineEdit,
    QFileDialog,
    QListWidgetItem,
    QListWidget,
    QInputDialog,
    QAbstractItemView,
    QDialog,
    QPushButton,
    QTabWidget,
    QDesktopWidget,
)

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QIcon

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import sys, os

sys.path.append("../")
from time import sleep
from datetime import date, datetime
import pickle
import requests
import pyscan_non_soc_version as ps

import globals
from Worker import *
from graphing import *
from ExperimentType import *

lstyle = {"description_width": "initial"}
aves = [1, 4, 16, 64, 128, 256]
voltage_limits = [0.002, 10]
tdivs = []
for n in range(9, -1, -1):
    tdivs += [2 * 10**-n, 4 * 10**-n, 10 * 10**-n]  # [2.5*10**-n, 5*10**-n, 10*10**-n]

scopes = []

# Global setting trees for the Pulse Frequency Sweep and Spin Echo experiment settings
sweep_list = [
    "Pulse Sweep",
    "Phase Sweep",
    "Rabi",
    "Inversion Sweep",
    "Period Sweep",
    "Hahn Echo",
    "EDFS",
    "Freq Sweep",
    "CPMG",
]

bimod_sweep_list = [
    "A Pulse Sweep",
    "B Pulse Sweep",
    "Both Pulse Sweep",
    "B Rabi",
    "Period Sweep",
    "Hahn Echo",
    "EDFS",
    "A Freq Sweep",
    "B Freq Sweep",
    "Both Freq Sweep",
    "DEER",
]

EXPERIMENT_TEMPLATES = {
    "Pulse Frequency Sweep": {
        "groups": {
            "Main Settings": [
                {
                    "display": "Frequency",
                    "key": "freq",
                    "type": "double_spin",
                    "min": 50.0,
                    "max": 14999.0,
                    "default": 3900.0,
                },
                {
                    "display": "Gain",
                    "key": "gain",
                    "type": "spin",
                    "min": 0,
                    "max": 32500,
                    "default": 32500,
                },
                {
                    "display": "Avg",
                    "key": "soft_avgs",
                    "type": "spin",
                    "min": 1,
                    "max": 1000000,
                    "default": 100,
                },
                {
                    "display": "Dir and Name",
                    "key": ["save_dir", "file_name"],
                    "type": "composite",
                    "default": ["", ""],
                },
                {
                    "display": "Experiment",
                    "key": "psexpt",
                    "type": "combo",
                    "options": ["Freq Sweep", "Field Sweep"],
                    "default": "Freq Sweep",
                },
                {
                    "display": "Sweep start, end, step",
                    "key": ["sweep_start", "sweep_end", "sweep_step"],
                    "type": "composite",
                    "default": [3850.0, 3950.0, 2.0],
                },
            ],
            "Readout Settings": [
                {
                    "display": "Time Offset",
                    "key": "h_offset",
                    "type": "double_spin",
                    "min": -10000.0,
                    "max": 10000.0,
                    "default": -0.125,
                },
                {
                    "display": "Readout Length",
                    "key": "readout_length",
                    "type": "double_spin",
                    "min": 0.0,
                    "max": 5.0,
                    "default": 0.2,
                },
                {
                    "display": "Loopback",
                    "key": "loopback",
                    "type": "check",
                    "default": False,
                },
            ],
            "Uncommon Settings": [
                {
                    "display": "Repetition time",
                    "key": "period",
                    "type": "double_spin",
                    "min": 0.1,
                    "max": 2000000000.0,
                    "default": 10.0,
                },
                {
                    "display": "Ch1 90 Pulse",
                    "key": "pulse1_1",
                    "type": "double_spin",
                    "min": 0.0,
                    "max": 652100.0,
                    "default": 50.0,
                },
                {
                    "display": "Magnetic Field, Scale, Current limit",
                    "key": ["field", "gauss_amps", "current_limit"],
                    "type": "composite",
                    "default": [0.0, 276.0, 3.5],
                },
                {
                    "display": "Reps",
                    "key": "ave_reps",
                    "type": "spin",
                    "min": 1,
                    "max": 1000,
                    "default": 1,
                },
                {
                    "display": "Wait Time",
                    "key": "wait",
                    "type": "double_spin",
                    "min": 0.0,
                    "max": 20.0,
                    "default": 0.3,
                },
                {
                    "display": "Integral only",
                    "key": "integrate",
                    "type": "check",
                    "default": True,
                },
            ],
            "Utility Settings": [
                {
                    "display": "Use PSU",
                    "key": "use_psu",
                    "type": "check",
                    "default": False,
                },
                {
                    "display": "Use Lakeshore",
                    "key": "use_temp",
                    "type": "check",
                    "default": False,
                },
            ],
            "Never Change": [
                {
                    "display": "Phase",
                    "key": "phase",
                    "type": "double_spin",
                    "min": 0.0,
                    "max": 360.0,
                    "default": 0.0,
                },
                {
                    "display": "Averaging Time (s)",
                    "key": "sltime",
                    "type": "double_spin",
                    "min": 0.0,
                    "max": 20.0,
                    "default": 0.0,
                },
            ],
        }
    },
    "Spin Echo": {
        "groups": {
            "Main Settings": [
                {
                    "display": "Ch1 Freq",
                    "key": "freq",
                    "type": "double_spin",
                    "min": 50.0,
                    "max": 14999.0,
                    "default": 3902.0,
                    "tool tip": "Helpful information",
                },
                {
                    "display": "Gain",
                    "key": "gain",
                    "type": "spin",
                    "min": 0,
                    "max": 32500,
                    "default": 32500,
                    "tool tip": "Helpful information",
                },
                {
                    "display": "Repetition time",
                    "key": "period",
                    "type": "double_spin",
                    "min": 0.1,
                    "max": 2000000000.0,
                    "default": 200.0,
                    "tool tip": "Helpful information",
                },
                {
                    "display": "Ave",
                    "key": "soft_avgs",
                    "type": "spin",
                    "min": 1,
                    "max": 10000000,
                    "default": 100,
                },
                {
                    "display": "Dir and Name",
                    "key": ["save_dir", "file_name"],
                    "type": "composite",
                    "default": ["", ""],
                },
                {
                    "display": "Reps",
                    "key": "ave_reps",
                    "type": "spin",
                    "min": 1,
                    "max": 1000,
                    "default": 1,
                },
                {
                    "display": "Experiment",
                    "key": "expt",
                    "type": "combo",
                    "options": sweep_list,
                    "default": "Hahn Echo",
                },
                {
                    "display": "Sweep start, end, step",
                    "key": ["sweep_start", "sweep_end", "sweep_step"],
                    "type": "composite",
                    "default": [150.0, 1000.0, 50.0],
                },
            ],
            "Pulse Settings": [
                {
                    "display": "Ch1 Delay",
                    "key": "delay",
                    "type": "double_spin",
                    "min": 0,
                    "max": 652100,
                    "default": 150.0,
                },
                {
                    "display": "90 Pulse",
                    "key": "pulse1_1",
                    "type": "double_spin",
                    "min": 0,
                    "max": 652100,
                    "default": 50.0,
                },
                {
                    "display": "Nut. Delay (ns)",
                    "key": "nutation_delay",
                    "type": "double_spin",
                    "min": 0,
                    "max": 655360,
                    "default": 5000.0,
                },
                {
                    "display": "Nut. Pulse Width",
                    "key": "nutation_length",
                    "type": "double_spin",
                    "min": 0,
                    "max": 655360,
                    "default": 0.0,
                },
            ],
            "Second Sweep Settings": [
                {
                    "display": "Second sweep?",
                    "key": "sweep2",
                    "type": "check",
                    "default": False,
                },
                {
                    "display": "Experiment 2",
                    "key": "expt2",
                    "type": "combo",
                    "options": sweep_list,
                    "default": "Hahn Echo",
                },
                {
                    "display": "Sweep 2 start, end, step",
                    "key": ["sweep2_start", "sweep2_end", "sweep2_step"],
                    "type": "composite",
                    "default": [0, 0, 0],
                },
            ],
            "Readout Settings": [
                {
                    "display": "Time Offset (us)",
                    "key": "h_offset",
                    "type": "double_spin",
                    "min": -1e5,
                    "max": 1e5,
                    "default": -0.025,
                },
                {
                    "display": "Readout Length (us)",
                    "key": "readout_length",
                    "type": "double_spin",
                    "min": 0.0,
                    "max": 5.0,
                    "default": 0.2,
                },
                {
                    "display": "Loopback",
                    "key": "loopback",
                    "type": "check",
                    "default": False,
                },
            ],
            "Uncommon Settings": [
                {
                    "display": "Ch1 180 Pulse Mult",
                    "key": "mult1",
                    "type": "double_spin",
                    "min": 0,
                    "max": 652100,
                    "default": 1.0,
                },
                {
                    "display": "Magnetic Field (G)",
                    "key": "field",
                    "type": "double_spin",
                    "min": 0.0,
                    "max": 0.0,
                    "default": 2500.0,
                },
                {
                    "display": "Magnet Scale (G/A)",
                    "key": "gauss_amps",
                    "type": "double_spin",
                    "min": 0.001,
                    "max": 1000.0,
                    "default": 270.0,
                },
                {
                    "display": "Current limit (A)",
                    "key": "current_limit",
                    "type": "double_spin",
                    "min": 0.0,
                    "max": 10.0,
                    "default": 3.5,
                },
                {
                    "display": "Wait Time (s)",
                    "key": "wait",
                    "type": "double_spin",
                    "min": 0.0,
                    "max": 20.0,
                    "default": 0.2,
                },
                {
                    "display": "Integral only",
                    "key": "integrate",
                    "type": "check",
                    "default": False,
                },
            ],
            "Utility Settings": [
                {
                    "display": "Use PSU? (no magnet if not)",
                    "key": "use_psu",
                    "type": "check",
                    "default": False,
                },
                {
                    "display": "Use Lakeshore?",
                    "key": "use_temp",
                    "type": "check",
                    "default": False,
                },
            ],
            "Never Change": [
                {
                    "display": "# 180 Pulses",
                    "key": "pulses",
                    "type": "spin",
                    "min": 1,
                    "max": 256,
                    "default": 1,
                },
                {
                    "display": "Phase",
                    "key": "phase",
                    "type": "double_spin",
                    "min": 0.0,
                    "max": 360.0,
                    "default": 0.0,
                },
                {
                    "display": "Auto Phase Sub",
                    "key": "phase_sub",
                    "type": "check",
                    "default": False,
                },
                {
                    "display": "Field Start (G)",
                    "key": "field_start",
                    "type": "double_spin",
                    "min": 0.0,
                    "max": 2500.0,
                    "default": 0.0,
                },
                {
                    "display": "Field End (G)",
                    "key": "field_end",
                    "type": "double_spin",
                    "min": 0.0,
                    "max": 2500.0,
                    "default": 50.0,
                },
                {
                    "display": "Field Step (G)",
                    "key": "field_step",
                    "type": "double_spin",
                    "min": 0.01,
                    "max": 2500.0,
                    "default": 1.5,
                },
                {
                    "display": "Sub Method",
                    "key": "subtract",
                    "type": "combo",
                    "options": ["Phase", "Delay", "Both", "None", "Autophase"],
                    "default": "Phase",
                },
                {
                    "display": "Averaging Time (s)",
                    "key": "sltime",
                    "type": "double_spin",
                    "min": 0.0,
                    "max": 20.0,
                    "default": 0.0,
                },
            ],
        }
    },
}

TOOLTIPS = {
    "freq": "freq tooltip",
    "gain": "gain tooltip",
    "soft_avgs": "soft avgs tooltip",
    "save_dir": "save dir tooltip",
    "file_name": "file name tooltip",
    "psexpt": "psexpt tooltip",
    "['sweep_start', 'sweep_end', 'sweep_step']": "sweep start/end/step tooltip",
}


class DualStream:
    """Redirects stdout/stderr to both the terminal and a QTextEdit in the GUI.
    Useful for showing print/debug output inside the application window.
    """

    def __init__(self, text_edit):
        """Initializes with the target QTextEdit and preserves access to the terminal"""
        self.text_edit = text_edit
        self.terminal = sys.__stdout__

    def write(self, text):
        """Appends text to both the QTextEdit log view and the system stdout"""

        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(text)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()

        self.terminal.write(text)
        self.terminal.flush()

    def flush(self):
        """Flushes the terminal stream (used by some buffered outputs)"""
        self.terminal.flush()


class PopUpMenu(QMessageBox):
    """Simple wrapper for a standard pop-up dialog with an OK button."""

    def __init__(self, title="Notification", message="This is a pop-up message"):
        # Initializes a basic message box with the provided title and message
        super().__init__()
        self.setWindowTitle(title)
        self.setText(message)
        self.setStandardButtons(QMessageBox.Ok)

    def show_popup(self):
        # Displays the pop-up dialog (blocking until user presses OK)
        self.exec_()


class DynamicSettingsPanel(QWidget):
    """Tree-based UI panel for dynamically rendering and editing experiment parameters.
    Uses templates from EXPERIMENT_TEMPLATES to auto-generate appropriate input widgets.
    Emits a signal whenever a setting is changed (which is then detected by the Worker class).
    """

    settingChanged = pyqtSignal()

    def __init__(self):
        """Initializes the settings panel with a scrollable QTreeWidget."""
        super().__init__()

        self.settings_tree = QTreeWidget()
        self.settings_tree.setHeaderHidden(False)
        self.settings_tree.setColumnCount(2)
        self.settings_tree.setHeaderLabels(["Setting", "Value"])
        self.settings_tree.setColumnWidth(0, 200)
        self.settings_tree.setColumnWidth(1, 100)

        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setWidget(self.settings_tree)

        layout = QVBoxLayout(self)
        layout.addWidget(self.settings_scroll)

    def load_settings_panel(self, settings, default_file=None):
        """Loads settings into the panel using the experiment template structure.
        If a default file is given, it tries to apply saved parameter values.
        """

        # Create a type lookup map to interpret each setting key
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

        # Clear any existing items in the settings tree
        self.settings_tree.clear()

        # Populate the tree with new items based on groupings
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
                label.setToolTip(TOOLTIPS.get(str(widget._underlying_key), ""))
                self.settings_tree.setItemWidget(item, 0, label)

        # Try to load previously saved defaults if available
        if default_file and os.path.isfile(default_file):
            try:
                with open(default_file, "rb") as f:
                    defaults = pickle.load(f)
            except Exception:
                defaults = {}
        else:
            defaults = {}

        # Apply default values to each widget in the tree
        tree = self.settings_tree
        root = tree.invisibleRootItem()
        for i in range(root.childCount()):
            grp = root.child(i)
            for j in range(grp.childCount()):
                item = grp.child(j)
                w = tree.itemWidget(item, 1)
                key = getattr(w, "_underlying_key", None)

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


         @return A QWidget-based input element appropriate for the setting. For composite widgets, a QWidget containing a layout of sub-widgets is returned.
        """
        stype = setting.get("type")
        widget = None

        # Standard numeric spin box
        if stype == "spin":
            widget = QSpinBox()
            widget.setMinimum(setting.get("min", 0))
            widget.setMaximum(setting.get("max", 1000000))
            widget.setValue(setting.get("default", 0))

        # Double precision spin box (for time, frequency, etc.)
        elif stype == "double_spin":
            widget = QDoubleSpinBox()
            widget.setMinimum(float(setting.get("min", 0.0)))
            widget.setMaximum(float(setting.get("max", 1e9)))
            widget.setValue(float(setting.get("default", 0.0)))

        # Text input field
        elif stype == "line_edit":
            widget = QLineEdit()
            widget.setText(setting.get("default", ""))

        # Drop-down menu for categorical options
        elif stype == "combo":
            widget = QComboBox()
            widget.addItems(setting.get("options", []))
            widget.setCurrentText(setting.get("default", ""))

        # Checkbox
        elif stype == "check":
            widget = QCheckBox()
            widget.setChecked(setting.get("default", False))

        # Composite widget: multiple spinboxes or line edits in a row
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
                """Returns a list of values from all sub-widgets."""
                values = []
                for idx in range(layout.count()):
                    sub_widget = layout.itemAt(idx).widget()
                    if isinstance(sub_widget, (QSpinBox, QDoubleSpinBox)):
                        values.append(sub_widget.value())
                    elif isinstance(sub_widget, QLineEdit):
                        values.append(sub_widget.text())
                return values

            widget.composite_values = composite_values

        # Fallback for unknown types
        else:
            widget = QLabel("N/A")
            widget.setWordWrap(True)

        # Hook up change signals for real-time tracking
        self._connect_setting_signals(widget)
        return widget

    def _connect_setting_signals(self, widget):
        """Connects value-changed signals from the widget (or sub-widgets)
        to the `settingChanged` signal for the panel.

        This ensures UI reacts whenever a user modifies any input.
        """

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

        # For composite widgets: recursively connect children
        elif hasattr(widget, "layout"):
            layout = widget.layout()
            for idx in range(layout.count()):
                subw = layout.itemAt(idx).widget()
                self._connect_setting_signals(subw)


class ExperimentUI(QMainWindow):
    """Main application window for controlling Spin Echo and Pulse Frequency Sweep experiments.

    Handles layout, widget initialization, parameter binding, worker thread execution,
    plotting, and experiment-specific GUI interactions.
    """

    def __init__(self):
        """Initializes the GUI, experiment logic, layout, and stdout redirection."""
        super().__init__()
        self.setWindowIcon(QIcon("icon.png"))

        # Create experiment logic handlers
        self.experiments = {
            "Spin Echo": ExperimentType("Spin Echo"),
            "Pulse Frequency Sweep": ExperimentType("Pulse Frequency Sweep"),
        }

        # Core application state flags
        self.is_process_running = False
        self.settings_changed = False
        self.sweep_already_ran = False

        # Default experiment selection
        self.current_experiment = self.experiments["Spin Echo"]
        self.experiment_templates = EXPERIMENT_TEMPLATES
        self.temp_parameters = {}

        # Initialize key panels
        self.settings_panel = DynamicSettingsPanel()
        self.settings_panel.settingChanged.connect(self.on_setting_changed)

        self.queue_manager = QueueManager(self.toggle_start_stop_sweep_frontend)
        self.graphs_panel = self.init_graphs_panel()
        self.error_log = self.init_error_log_widget()
        self.top_menu_bar = self.init_top_menu_bar()

        # Build UI layout
        self.init_layout()
        self.load_defaults_and_build_ui()

        # Enable/disable buttons initially
        self.read_unprocessed_btn.setEnabled(False)
        self.read_processed_btn.setEnabled(False)
        self.sweep_start_stop_btn.setEnabled(True)
        self.set_parameters_and_initialize_btn.setEnabled(True)

        # Redirect stdout and stderr to GUI log
        dual_stream = DualStream(self.log_text)
        sys.stdout = dual_stream
        sys.stderr = dual_stream

        self.last_saved_graph_path = None
        self.worker_thread = None

    def get_scopes_from_backend(self):
        """Attempts to query available scope devices from the backend server.

        On success: stores the response in the global `scopes` variable and stops polling.
        On failure: logs the error message in the GUI.
        """
        try:
            response = requests.get(
                globals.server_address + "/get_scopes", json=data, timeout=2
            )
            response.raise_for_status()
            data = response.json()
            global scopes
            scopes = data
            self.poll_timer.stop()
        except Exception as e:
            self.label.setText(f"Unable to get scopes from backend... ({e})")

    def load_defaults_and_build_ui(self):
        """Initializes the UI settings panel using the current experiment's template
        and loads default parameter values from the associated pickle file (if exists).
        """
        template = self.experiment_templates[self.current_experiment.type]
        self.settings_panel.load_settings_panel(
            template, default_file=self.current_experiment.default_file
        )

    def on_setting_changed(self):
        """Triggered when any setting in the panel is modified.

        Disables all action buttons and re-enables only the Initialize button,
        signaling that the user must reinitialize before running again.
        """
        self.settings_changed = True
        if not self.is_process_running:
            self.read_unprocessed_btn.setEnabled(False)
            self.read_processed_btn.setEnabled(False)
            self.sweep_start_stop_btn.setEnabled(False)
            self.set_parameters_and_initialize_btn.setEnabled(True)

    def init_layout(self):
        """Builds the full GUI layout structure:

        - Top row: menu bar (buttons and experiment switcher)
        - Left panel: settings + queue
        - Right panel (split vertically): graphs and log area
        """
        # Setup main vertical layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(self.top_menu_bar, 1)

        # Create horizontal splitter dividing settings (left) and output (right)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(5)
        self.main_splitter.setStyleSheet(
            """
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
        """
        )

        # ----- Left: Settings + Queue -----
        left_container = QVBoxLayout()
        left_widget = QWidget()
        left_widget.setLayout(left_container)
        left_container.setContentsMargins(0, 0, 0, 0)
        left_container.setSpacing(10)

        left_container.addWidget(self.settings_panel)

        # Queue widget with fixed height
        queue_wrapper = QWidget()
        queue_layout = QVBoxLayout(queue_wrapper)
        queue_layout.setContentsMargins(0, 0, 0, 0)
        queue_layout.setSpacing(0)
        queue_layout.addWidget(self.queue_manager)
        queue_wrapper.setMaximumHeight(350)

        left_container.addWidget(queue_wrapper)
        self.main_splitter.addWidget(left_widget)

        # ----- Right: Graphs + Log -----
        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_splitter.setHandleWidth(5)
        self.right_splitter.setStyleSheet(
            """
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
        """
        )

        self.right_splitter.addWidget(self.graphs_panel)

        self.error_widget = self.init_error_log_widget()
        self.right_splitter.addWidget(self.error_widget)

        self.main_splitter.addWidget(self.right_splitter)

        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([350, 650])

        # ----- Final layout hookup -----
        main_layout.addWidget(self.main_splitter, 15)
        self.setCentralWidget(central_widget)

        self.setWindowTitle("Experiment UI")
        self.setGeometry(100, 100, 1000, 700)
        self.show()

    def init_graphs_panel(self):
        """Initializes the tabbed panel used to show experiment result plots:

        - Tab 1: Raw unprocessed data
        - Tab 2: Processed data
        - Tab 3: 2D sweep plot (with dropdown selector)
        - Tab 4 (Spin Echo only): 1D sweep plot (with dropdown selector)
        """
        graph_section_widget = QWidget()
        graph_layout = QVBoxLayout(graph_section_widget)

        self.graph_tabs = QTabWidget()

        # ----- Tab 1: Read Unprocessed -----
        graph_tab_1 = QWidget()
        tab1_layout = QVBoxLayout(graph_tab_1)
        tab1_layout.addWidget(self.current_experiment.read_unprocessed_graph)
        self.graph_tabs.addTab(graph_tab_1, "Read Unprocessed")

        # ----- Tab 2: Read Processed -----
        graph_tab_2 = QWidget()
        tab2_layout = QVBoxLayout(graph_tab_2)
        tab2_layout.addWidget(self.current_experiment.read_processed_graph)
        self.graph_tabs.addTab(graph_tab_2, "Read Processed")

        # ----- Tab 3: 2D Sweep Plot -----
        graph_tab_3 = QWidget()
        tab3_layout = QVBoxLayout(graph_tab_3)
        hdr3 = QHBoxLayout()
        hdr3.addWidget(QLabel("Variable:"))
        combo_2d = QComboBox()
        combo_2d.currentTextChanged.connect(self.update_2d_plot)
        combo_2d.addItems(["x", "i", "q"])
        hdr3.addWidget(combo_2d)
        hdr3.addStretch()
        tab3_layout.addLayout(hdr3)
        tab3_layout.addWidget(self.current_experiment.sweep_graph_2D)
        self.graph_tabs.addTab(graph_tab_3, "2D Sweep")
        self.combo_2d = combo_2d

        # ----- Tab 4 (conditional): 1D Sweep Plot -----
        if self.current_experiment.type == "Spin Echo":
            graph_tab_4 = QWidget()
            tab4_layout = QVBoxLayout(graph_tab_4)
            hdr4 = QHBoxLayout()
            hdr4.addWidget(QLabel("Variable:"))
            combo_1d = QComboBox()
            combo_1d.currentTextChanged.connect(self.update_1d_plot)
            combo_1d.addItems(["xmean", "imean", "qmean"])
            hdr4.addWidget(combo_1d)
            hdr4.addStretch()
            tab4_layout.addLayout(hdr4)
            tab4_layout.addWidget(self.current_experiment.sweep_graph_1D)
            self.graph_tabs.addTab(graph_tab_4, "1D Sweep")
            self.combo_1d = combo_1d

        # ----- Bottom Row: Save Button + Path -----
        graph_layout.addWidget(self.graph_tabs)

        graph_bottom_row = QHBoxLayout()

        self.save_graph_btn = QPushButton("Save Graph As...")
        self.save_graph_btn.clicked.connect(self.save_current_graph)
        graph_bottom_row.addWidget(self.save_graph_btn)

        self.last_saved_path_label = QLabel("No graph saved yet.")
        self.last_saved_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.last_saved_path_label.setStyleSheet(
            "color: blue; text-decoration: underline;"
        )
        self.last_saved_path_label.mousePressEvent = self.open_saved_graph_folder
        graph_bottom_row.addWidget(self.last_saved_path_label)

        graph_layout.addLayout(graph_bottom_row)

        return graph_section_widget

    def init_error_log_widget(self):
        """Creates the log display panel that shows all console output in real time."""
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
        """Creates the top button bar for experiment selection and core actions.

        Includes:
        - Dropdown to switch experiment type
        - Buttons: Add to Queue, Initialize, Read (Processed/Unprocessed), Sweep
        """
        top_menu = QHBoxLayout()
        top_menu.setContentsMargins(5, 5, 5, 5)
        top_menu.setSpacing(5)
        top_menu.setAlignment(Qt.AlignTop)

        top_menu_container = QWidget()
        top_menu_container.setLayout(top_menu)

        # ----- Dropdown for experiment type selection -----
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

        # ----- Add to Queue Button -----
        add_queue_btn = QPushButton("Add to Queue")
        add_queue_btn.setMinimumHeight(40)
        add_queue_btn.setStyleSheet("font-size: 10pt; padding: 4px;")
        add_queue_btn.clicked.connect(self.add_to_queue)
        top_menu.addWidget(add_queue_btn)

        # ----- Experiment-specific buttons: Init, Read, Sweep -----
        top_menu = self.init_experiment_specific_buttons(top_menu)
        top_menu.addSpacing(30)

        return top_menu_container

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def init_experiment_specific_buttons(self, top_menu):
        """Adds buttons for experiment control:

        - Initialize
        - Hardware Off
        - Read Unprocessed
        - Read Processed
        - Start/Stop Sweep
        """
        # ----- Initialize -----
        init_widget = QWidget()
        init_layout = QHBoxLayout(init_widget)
        init_layout.setContentsMargins(0, 0, 0, 0)
        self.set_parameters_and_initialize_btn = QPushButton("Initialize")
        self.set_parameters_and_initialize_btn.setMinimumHeight(40)
        self.set_parameters_and_initialize_btn.setStyleSheet(
            "font-size: 10pt; padding: 2px 4px;"
        )
        self.set_parameters_and_initialize_btn.clicked.connect(
            self.initialize_from_settings_panel
        )
        self.set_parameters_and_initialize_btn.setToolTip(
            "Helpful information"
        )  # Tool tip here!
        self.indicator_initialize = QLabel(" ")
        self.indicator_initialize.setFixedSize(10, 10)
        self.indicator_initialize.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )
        init_layout.addWidget(self.set_parameters_and_initialize_btn)
        init_layout.addWidget(self.indicator_initialize)
        top_menu.addWidget(init_widget)

        # ----- Read Unprocessed -----
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

        # ----- Read Processed -----
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

        # ----- Toggle Start/Stop/Resume Sweep -----
        sweep_widget = QWidget()
        sweep_layout = QHBoxLayout(sweep_widget)
        sweep_layout.setContentsMargins(0, 0, 0, 0)
        self.sweep_start_stop_btn = QPushButton("Resume Sweep")
        self.sweep_start_stop_btn.setMinimumHeight(40)
        self.sweep_start_stop_btn.setStyleSheet("font-size: 10pt; padding: 2px 4px;")
        self.sweep_start_stop_btn.clicked.connect(self.toggle_start_stop_sweep_frontend)
        self.sweep_start_stop_btn.setToolTip("Helpful information")  # Tool tip here!
        self.indicator_sweep = QLabel(" ")
        self.indicator_sweep.setFixedSize(10, 10)
        self.indicator_sweep.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )
        top_menu.addWidget(self.sweep_start_stop_btn)
        top_menu.addWidget(self.indicator_sweep)

        # Initial button state
        self.read_unprocessed_btn.setEnabled(False)
        self.read_processed_btn.setEnabled(False)
        #self.sweep_start_stop_btn.setEnabled(True)

        # ----- Hardware Off -----
        off_widget = QWidget()
        off_layout = QHBoxLayout(off_widget)
        off_layout.setContentsMargins(0, 0, 0, 0)
        self.hardware_off_btn = QPushButton("Hardware Off")
        self.hardware_off_btn.setMinimumHeight(40)
        self.hardware_off_btn.setStyleSheet(
            "font-size: 10pt; padding: 2px 4px;"
        )
        self.hardware_off_btn.clicked.connect(
            self.hardware_off_frontend
        )
        self.hardware_off_btn.setToolTip(
            "Helpful information"
        )  # Tool tip here!
        self.indicator_off = QLabel(" ")
        self.indicator_off.setFixedSize(10, 10)
        self.indicator_off.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )
        off_layout.addWidget(self.hardware_off_btn)
        off_layout.addWidget(self.indicator_off)
        top_menu.addWidget(off_widget)

        return top_menu

    def change_experiment_type(self, experiment_type):
        """Handles switching between experiment modes (Spin Echo vs Pulse Frequency Sweep).

        - Stops any running sweep
        - Resets parameters, graphs, and tab views
        - Rebinds the appropriate widgets to the newly selected experiment
        """
        if hasattr(self, "worker"):
            self.worker.stop_sweep()
            self.indicator_sweep.setStyleSheet(
                "background-color: grey; border: 1px solid black; border-radius: 5px;"
            )

        print(f"Changing experiment type to {experiment_type}...\n")

        try:
            # Update backend model
            self.current_experiment = self.experiments[experiment_type]
            self.temp_parameters = {}
            self.init_parameters_from_template()

            # Reload settings panel with new template and defaults
            self.settings_panel.load_settings_panel(
                self.experiment_templates[experiment_type],
                default_file=self.current_experiment.default_file,
            )

            # Remove old "1D Sweep" tab if switching away from Spin Echo
            for i in range(self.graph_tabs.count()):
                if self.graph_tabs.tabText(i) == "1D Sweep":
                    self.graph_tabs.removeTab(i)
                    break

            # If new experiment type is Spin Echo, add back a 1D sweep tab
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

            # Refresh graph contents for the new experiment
            for idx in range(self.graph_tabs.count()):
                tab = self.graph_tabs.widget(idx)
                layout = tab.layout()
                if not layout:
                    layout = QVBoxLayout(tab)
                    tab.setLayout(layout)

                # Clear layout contents
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

                # Rebuild each tab
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

            # Reset button state
            self.read_unprocessed_btn.setEnabled(False)
            self.read_processed_btn.setEnabled(False)
            #self.sweep_start_stop_btn.setEnabled(False)
            self.set_parameters_and_initialize_btn.setEnabled(True)

        except Exception as e:
            print(f"Error switching experiment: {e}")

    def update_2d_plot(self):
        """Redraws the 2D sweep plot using the selected variable from the combo box."""
        try:
            if self.current_experiment.expt:
                data_name_2d = self.combo_2d.currentText()
                pg_2D = ps.PlotGenerator(
                    expt=self.current_experiment.expt,
                    d=2,
                    x_name="t",
                    y_name=self.current_experiment.parameters["y_name"],
                    data_name=data_name_2d,
                    transpose=1,
                )
                self.current_experiment.sweep_graph_2D.on_live_plot_2D((pg_2D))
        except Exception as e:
            print(f"Error updating 2d plot: {e}")

    def update_1d_plot(self):
        """Redraws the 1D sweep plot based on the variable selected in the dropdown.

        Only applicable for Spin Echo experiments, where line plots of sweep data are supported.
        """
        if self.current_experiment.expt:
            data_name_1d = self.combo_1d.currentText()
            pg_1D = ps.PlotGenerator(
                expt=self.current_experiment.expt,
                d=1,
                x_name=self.current_experiment.parameters["y_name"],
                data_name=data_name_1d,
            )
            self.current_experiment.sweep_graph_1D.on_live_plot_1D((pg_1D))

    def init_parameters_from_template(self):
        """Seeds self.temp_parameters using defaults from the current experiment template.

        Ensures every key from the template is represented in the parameter dictionary,
        even before the user opens the settings panel or modifies values.
        """
        template = self.experiment_templates.get(
            self.current_experiment.type, {"groups": {}}
        )
        for group in template["groups"].values():
            for setting in group:
                underlying = setting.get("key")
                default = setting.get("default", "")
                if isinstance(underlying, list):
                    for key, d in zip(
                        underlying, default if isinstance(default, list) else []
                    ):
                        if key not in self.temp_parameters:
                            self.temp_parameters[key] = d
                else:
                    if underlying not in self.temp_parameters:
                        self.temp_parameters[underlying] = default

    def initialize_from_settings_panel(self):
        """Reads all current settings from the UI, sends them to the backend server,
        and stores them in the experiment object. Also enables action buttons.

        Called when the user clicks the "Initialize" button.
        """
        #self.set_parameters_and_initialize_btn.setEnabled(False)
        self.settings_changed = False

        print("Reading and setting parameters...\n")
        self.indicator_initialize.setStyleSheet(
            "background-color: red; border: 1px solid black; border-radius: 5px;"
        )

        # Read values from UI widgets and build a new parameter dictionary
        tree = self.settings_panel.settings_tree
        root = tree.invisibleRootItem()
        new_params = self.current_experiment.parameters.copy()
        for i in range(root.childCount()):
            group_item = root.child(i)
            for j in range(group_item.childCount()):
                item = group_item.child(j)
                widget = tree.itemWidget(item, 1)
                underlying = getattr(widget, "_underlying_key", None)

                # Determine how to extract value from widget
                if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                    value = widget.value()
                elif isinstance(widget, QLineEdit):
                    value = widget.text()
                elif isinstance(widget, QComboBox):
                    value = widget.currentText()
                elif isinstance(widget, QCheckBox):
                    value = widget.isChecked()
                elif isinstance(widget, QWidget) and hasattr(
                    widget, "composite_values"
                ):
                    value = widget.composite_values()

                    if isinstance(value, list):
                        if underlying:
                            for idx, (key, v) in enumerate(zip(underlying, value)):
                                if key == "gain" and isinstance(v, float):
                                    value[idx] = int(v)
                                    print(f"Converting 'gain' value {v} to integer.")
                else:
                    value = None

                # Insert value into parameter dictionary
                if underlying is not None:
                    if isinstance(underlying, list) and isinstance(value, list):
                        for key, v in zip(underlying, value):
                            new_params[key] = v
                    else:
                        new_params[underlying] = value

        # Send new parameters to the experiment backend
        self.current_experiment.set_parameters(new_params)

        # Reset indicator
        self.indicator_initialize.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )

        self.sweep_already_ran = False

        # Enable all action buttons
        self.read_unprocessed_btn.setEnabled(True)
        self.read_processed_btn.setEnabled(True)
        self.sweep_start_stop_btn.setEnabled(True)
        self.sweep_start_stop_btn.setText("Start Sweep")

        print("Initialized experiment with parameters:")
        for k, v in new_params.items():
            print(f"   {k}: {v}")
        print("\n")
        print("Select an action. \n")

    def read_unprocessed_frontend(self):
        """Starts a worker thread to read unprocessed experiment data from the server.

        Disables buttons and highlights the appropriate indicator while running.
        """
        self.indicator_read_unprocessed.setStyleSheet(
            "background-color: red; border: 1px solid black; border-radius: 5px;"
        )

        # Lock down action buttons while worker is running
        self.read_unprocessed_btn.setEnabled(False)
        self.read_processed_btn.setEnabled(False)
        self.sweep_start_stop_btn.setEnabled(False)
        #self.set_parameters_and_initialize_btn.setEnabled(False)
        self.is_process_running = True

        # Focus tab on graph panel
        self.graph_tabs.setCurrentIndex(0)

        # Setup worker thread and task
        self.worker_thread = QThread(self)
        self.worker = Worker(self.current_experiment, "read_unprocessed")
        self.worker.moveToThread(self.worker_thread)

        # Connect signals
        self.worker_thread.started.connect(self.worker.run_snapshot)
        self.worker.updateStatus.connect(self.on_worker_status_update)
        self.worker.dataReady_se.connect(
            self.current_experiment.read_unprocessed_graph.update_canvas_se
        )
        self.worker.dataReady_ps.connect(
            self.current_experiment.read_unprocessed_graph.update_canvas_psweep
        )
        #self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker.finished.connect(self.reset_action_buttons)

        # Launch thread
        self.worker_thread.start()

    def read_processed_frontend(self):
        """Starts a worker thread to retrieve processed experiment data from the backend.

        Disables buttons and updates the visual indicator during execution.
        """
        self.indicator_read_processed.setStyleSheet(
            "background-color: red; border: 1px solid black; border-radius: 5px;"
        )

        # Lock down action buttons while worker is running
        self.read_unprocessed_btn.setEnabled(False)
        self.read_processed_btn.setEnabled(False)
        self.sweep_start_stop_btn.setEnabled(False)
        #self.set_parameters_and_initialize_btn.setEnabled(False)
        self.is_process_running = True

        # Focus on processed graph tab
        self.graph_tabs.setCurrentIndex(1)

        # Setup worker and thread
        self.worker_thread = QThread(self)
        self.worker = Worker(self.current_experiment, "read_processed")
        self.worker.moveToThread(self.worker_thread)

        # Setup worker and thread
        self.worker_thread.started.connect(self.worker.run_snapshot)
        self.worker.updateStatus.connect(self.on_worker_status_update)
        self.worker.dataReady_se.connect(
            self.current_experiment.read_processed_graph.update_canvas_se
        )
        self.worker.dataReady_ps.connect(
            self.current_experiment.read_processed_graph.update_canvas_psweep
        )
        #self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker.finished.connect(self.reset_action_buttons)

        # Setup worker and thread
        self.worker_thread.start()

    def toggle_start_stop_sweep_frontend(self):
        """Toggles between starting and stopping a sweep task in a worker thread.

        - If starting: disables GUI buttons, sets up plotting, and launches the sweep
        - If stopping: flags the worker to exit early and resets indicators
        """
        if self.sweep_start_stop_btn.text() == "Start Sweep":
            # Start sweep mode
            self.read_unprocessed_btn.setEnabled(False)
            self.read_processed_btn.setEnabled(False)
            #self.set_parameters_and_initialize_btn.setEnabled(False)
            self.is_process_running = True

            self.indicator_sweep.setStyleSheet(
                "background-color: red; border: 1px solid black; border-radius: 5px;"
            )
            self.sweep_start_stop_btn.setText("Stop Sweep")

            # Focus on the 2d sweep graph tab
            if self.current_experiment.parameters['integrate']:
                self.graph_tabs.setCurrentIndex(3)
            else:
                self.graph_tabs.setCurrentIndex(2)

            # Choose appropriate worker config depending on experiment type
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
                    combo_1d=self.combo_1d,
                )
            self.worker.moveToThread(self.worker_thread)

            # Connect sweep update signals
            self.worker_thread.started.connect(self.worker.run_sweep)
            self.worker.live_plot_2D_update_signal.connect(
                self.current_experiment.sweep_graph_2D.on_live_plot_2D
            )
            self.worker.live_plot_1D_update_signal.connect(
                self.current_experiment.sweep_graph_1D.on_live_plot_1D
            )
            self.worker.updateStatus.connect(self.on_worker_status_update)
            #self.worker.finished.connect(self.worker_thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.worker_thread.finished.connect(self.worker_thread.deleteLater)
            self.worker.finished.connect(self.on_finished_sweep)

            # Start background sweep
            self.worker_thread.start()

        elif self.sweep_start_stop_btn.text() == "Resume Sweep":
            # Start sweep mode
            self.read_unprocessed_btn.setEnabled(False)
            self.read_processed_btn.setEnabled(False)
            #self.set_parameters_and_initialize_btn.setEnabled(False)
            self.is_process_running = True

            self.indicator_sweep.setStyleSheet(
                "background-color: red; border: 1px solid black; border-radius: 5px;"
            )
            self.sweep_start_stop_btn.setText("Stop Sweep")

            self.graph_tabs.setCurrentIndex(2)

            # Choose appropriate worker config depending on experiment type
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
                    combo_1d=self.combo_1d,
                )
            
            self.worker.moveToThread(self.worker_thread)

            # Connect sweep update signals
            self.worker_thread.started.connect(self.worker.resume_sweep)
            self.worker.live_plot_2D_update_signal.connect(
                self.current_experiment.sweep_graph_2D.on_live_plot_2D
            )
            self.worker.live_plot_1D_update_signal.connect(
                self.current_experiment.sweep_graph_1D.on_live_plot_1D
            )
            self.worker.updateStatus.connect(self.on_worker_status_update)
            #self.worker.finished.connect(self.worker_thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.worker_thread.finished.connect(self.worker_thread.deleteLater)
            self.worker.finished.connect(self.on_finished_sweep)

            # Start background sweep
            self.worker_thread.start()
        else:
            # Stop sweep mode
            if hasattr(self, "worker"):
                print("Stopping sweep…")
                self.current_experiment.stop()
                self.worker.stop_sweep()
                print("Stop requested.")
                self.on_finished_sweep()

    def on_finished_sweep(self):
        """Handles post-sweep cleanup and button resets after worker completes.

        Called when the sweep worker signals completion, either normally or via stop request.
        """
        try:
            self.sweep_already_ran = True
            self.reset_action_buttons()
        except Exception as e:
            print(e)

    def reset_action_buttons(self):
        """Restores GUI button states after a task finishes.

        - Re-enables Read and Initialize buttons
        - Greys out sweep button if a sweep already ran
        - Resets all indicator LEDs to grey
        """
        self.read_unprocessed_btn.setEnabled(True)
        self.read_processed_btn.setEnabled(True)
        self.set_parameters_and_initialize_btn.setEnabled(True)

        # Reset visual indicator dots
        for indicator in (
            self.indicator_read_unprocessed,
            self.indicator_read_processed,
        ):
            indicator.setStyleSheet(
                "background-color: grey; border: 1px solid black; border-radius: 5px;"
            )

        # Sweep can only be restarted if it hasn’t been run yet
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
        """Calls the backend method to turn off experiment hardware.

        Useful for safely shutting down instruments like power supplies or temperature controllers.
        """
        print("Shutting off.")
        try:
            self.current_experiment.hardware_off()
        except Exception as e:
            print(e)
        # finally:
        #     self.close()

    def on_worker_status_update(self, message):
        """Receives status messages emitted from the worker thread and logs them to the console/log pane."""
        print(message)

    def save_current_graph(self):
        """Opens a file dialog and saves the current graph (from the selected tab) as an image file."""
        current_index = self.graph_tabs.currentIndex()

        # Determine which graph figure to save based on current tab
        if current_index == 0:
            fig = self.current_experiment.read_unprocessed_graph.figure
        elif current_index == 1:
            fig = self.current_experiment.read_processed_graph.figure
        elif current_index == 2:
            fig = self.current_experiment.sweep_graph_2D.figure
        elif current_index == 3:
            fig = self.current_experiment.sweep_graph_1D.figure
        else:
            return  # No valid graph to save

        # Show file dialog
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Graph As...",
            "",
            "PNG Files (*.png);;PDF Files (*.pdf);;All Files (*)",
            options=options,
        )

        # Save the figure if path selected
        if file_path:
            fig.savefig(file_path)
            self.last_saved_path_label.setText(file_path)

    def open_saved_graph_folder(self, event):
        """Opens the file explorer to the directory where the last graph was saved."""
        if self.last_saved_graph_path:
            folder = os.path.dirname(self.last_saved_graph_path)
            os.system(
                f'open "{folder}"'
            )  # 'xdg-open' for Linux. Use `open` for macOS, or `start` for Windows.

    def expand_queue_panel(self):
        """Opens a standalone window to view and manage the experiment queue.

        Provides draggable lists for working/active queues and control buttons for queue history,
        clearing, and toggling execution.
        """
        self.queue_window = QWidget()
        self.queue_window.setWindowTitle("Queue Viewer")
        self.queue_window.setGeometry(300, 300, 500, 400)

        # Main vertical layout
        main_layout = QVBoxLayout(self.queue_window)

        # Control bar (History / Clear / Start-Stop)
        control_bar = QHBoxLayout()
        for name in ["History", "Clear", "Start/Stop"]:
            btn = QPushButton(name)
            control_bar.addWidget(btn)
        main_layout.addLayout(control_bar)

        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)

        # Layout inside the scroll area
        scroll_layout = QVBoxLayout(content_widget)

        # Active Queue
        scroll_layout.addWidget(QLabel("Active Queue:"))
        self.active_queue_list = QListWidget()
        self.active_queue_list.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred
        )
        scroll_layout.addWidget(self.active_queue_list)

        # Working Queue (drag-and-drop)
        scroll_layout.addWidget(QLabel("Working Queue:"))
        self.working_queue_list = QListWidget()
        self.working_queue_list.setDragEnabled(True)
        self.working_queue_list.setAcceptDrops(True)
        self.working_queue_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.working_queue_list.setSpacing(2)
        self.working_queue_list.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred
        )
        scroll_layout.addWidget(self.working_queue_list)

        # Add scroll area to the main layout
        main_layout.addWidget(scroll_area)

        self.queue_window.setLayout(main_layout)
        self.queue_window.show()

    def add_to_queue(self):
        """Creates a new queued experiment using the current settings and adds it to the working queue.

        Opens a configuration dialog to customize the experiment’s metadata (e.g., name, graph output).
        """
        try:
            # Clone the current experiment backend logic
            new_experiment = ExperimentType(self.current_experiment.type)

            # Create a QueuedExperiment wrapper (includes settings + metadata)
            queue_item = QueuedExperiment(
                start_stop_sweep_function=self.toggle_start_stop_sweep_frontend,
                experiment=new_experiment,
                queue_manager=self.queue_manager,
                last_used_directory=self.last_saved_graph_path,
            )

            # Only add if the user completed the dialog
            if queue_item.valid:
                self.queue_manager.add_to_working_queue(queue_item)

        except Exception as e:
            print(e)


class QueueRunnerWorker(QThread):
    """Worker thread that runs through the active experiment queue.

    For each experiment:
    - Locks it (greys out)
    - Initializes and runs it
    - Marks it done
    - Handles hardware errors and moves to next in queue
    """

    experiment_locked = pyqtSignal(object)
    experiment_unlocked = pyqtSignal(object)
    queue_stopped = pyqtSignal()
    hardware_error = pyqtSignal(object, str)

    def __init__(self, queue_manager):
        """Initializes the queue runner with a reference to the main queue manager."""
        super().__init__()
        self.queue_manager = queue_manager
        self.stop_requested = False

    def run(self):
        """Main queue execution loop.

        - Pulls next experiment from active queue
        - Initializes and runs it
        - Stops if no experiments remain or if error/stop is triggered
        """
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
        """Starts a background Worker thread to perform a single task
        (e.g., sweep, read_processed, read_unprocessed) for a given experiment.

        Connects appropriate update and plotting signals to the GUI.
        """
        worker = Worker(experiment.experiment, task)
        thread = QThread()

        worker.moveToThread(thread)
        thread.started.connect(worker.run_snapshot)

        # Attach signal handlers to update plots in the background
        worker.dataReady_se.connect(
            experiment.experiment.read_unprocessed_graph.update_canvas_se
        )
        worker.dataReady_ps.connect(
            experiment.experiment.read_unprocessed_graph.update_canvas_psweep
        )

        # Status updates + cleanup
        worker.updateStatus.connect(self.queue_manager.parent().on_worker_status_update)
        #worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        # Start the task
        thread.start()

    def get_next_experiment(self):
        """Retrieves the next experiment item from the active queue, if any."""
        if self.queue_manager.active_queue_list.count() > 0:
            return self.queue_manager.active_queue_list.item(0)
        return None

    def initialize_experiment(self, experiment):
        """Initializes the experiment backend with saved parameters and launches its components.

        Runs selected tasks depending on the experiment’s configured flags.
        """
        experiment.init_experiment()

        if experiment.has_sweep:
            self.run_worker_task(experiment, task="sweep")

        if experiment.has_read_unprocessed:
            self.run_worker_task(experiment, task="read_unprocessed")

        if experiment.has_read_processed:
            self.run_worker_task(experiment, task="read_processed")

    def mark_experiment_done(self, experiment):
        """Marks the experiment as finished and logs it with a timestamp.

        Adds an entry to the experiment history log in the queue manager.
        """
        now = datetime.now()

        # Format timestamp
        if not self.queue_manager.session_started:
            self.queue_manager.session_started = True
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        else:
            timestamp = now.strftime("%H:%M:%S")

        # Get display name and output location
        display_name = experiment.parameters_dict.get(
            "display_name", "Unnamed Experiment"
        )
        save_location = experiment.parameters_dict.get("save_directory", "")

        self.queue_manager.history_log.append((timestamp, display_name, save_location))

        experiment.set_done()

    def move_to_next_experiment(self):
        """Removes the current experiment from the active queue list (visually and logically)."""
        self.queue_manager.active_queue_list.takeItem(0)


class QueueManager(QWidget):
    """Manages the experiment queue (working and active), controls queue execution,
    and handles user interaction with queued experiments (move, duplicate, delete).
    """

    def __init__(self, start_stop_sweep_function=None, parent=None):
        """Initializes the queue manager panel, including:

        - A collapsed/expandable UI
        - Two queues: working (editable) and active (in progress)
        - Buttons for running, clearing, and showing history
        """
        super().__init__(parent)

        self.start_stop_sweep_function = start_stop_sweep_function

        # State tracking
        self.queue_runner = None
        self.queue_running = False
        self.history_log = []
        self.session_started = False

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Collapsed header
        self.collapsed_button = QPushButton("Queue: Currently Running: [None] ▲")
        self.collapsed_button.setMaximumHeight(40)
        self.collapsed_button.setStyleSheet("text-align: left; padding: 8px;")
        self.collapsed_button.clicked.connect(self.toggle_expand)
        self.main_layout.addWidget(self.collapsed_button)

        # Expanded content frame
        self.expanded_frame = QFrame()
        self.expanded_frame.setVisible(False)
        self.expanded_layout = QVBoxLayout(self.expanded_frame)
        self.expanded_layout.setContentsMargins(10, 10, 10, 10)
        self.expanded_layout.setSpacing(10)

        # Header controls (label + buttons)
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

        # Connect control buttons
        self.history_button.clicked.connect(self.show_history)
        self.clear_button.clicked.connect(self.clear_queue)
        self.toggle_run_button.clicked.connect(self.start_stop_queue)

        # Active queue list (non-editable)
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
        """Toggles queue execution.

        - If queue is not running: starts execution of active queue
        - If already running: signals the queue runner to stop
        """
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
        """Starts execution of the next experiment in the active queue.

        If queue is empty, does nothing. Removes the experiment from the list after running.
        """
        try:
            if self.active_queue_list.count != 0:
                next_experiment = self.active_queue_list.takeItem(0)
                self.current_experiment = next_experiment.experiment
                next_experiment.init_experiment()
                next_experiment.start_stop_sweep_function()
        except Exception as e:
            print(e)

    def queue_stopped_due_to_completion_or_error(self):
        """Handles cleanup when the queue finishes naturally or due to an error.

        Resets state flags and button labels.
        """
        self.queue_running = False
        self.toggle_run_button.setText("Start")
        print("Queue has stopped.")

    def handle_hardware_error(self, experiment, error_message):
        """Prints/logs an error message if an experiment failed due to hardware issues.

        Used by the QueueRunnerWorker when catching backend exceptions.
        """
        print(
            f"Hardware error detected in experiment: {experiment.parameters_dict.get('display_name', 'Unknown')}"
        )
        print(f"Error: {error_message}")

    def lock_experiment(self, experiment):
        """Greys out an experiment in the queue to indicate it's currently running.

        Used to visually lock the item (disable interaction).
        """
        if isinstance(experiment, QueuedExperiment):
            experiment.widget.setStyleSheet(
                """
                QWidget {
                    background-color: #cccccc;
                    border: 2px solid #888;
                    border-radius: 6px;
                    padding: 8px;
                }
            """
            )

    def unlock_experiment(self, experiment):
        """Restores visual style for an experiment item after it finishes running."""
        if isinstance(experiment, QueuedExperiment):
            experiment.widget.setStyleSheet(
                """
                QWidget {
                    background-color: #f9f9f9;
                    border: 2px solid #888;
                    border-radius: 6px;
                    padding: 8px;
                }
            """
            )

    def toggle_run_button_text(self):
        """Toggles the Run button text between 'Start' and 'Stop' based on current state."""
        current_text = self.toggle_run_button.text().strip()

        if current_text.lower() == "start" or current_text.lower() == "start/stop":
            self.toggle_run_button.setText("Stop")
        else:
            self.toggle_run_button.setText("Start")

    def toggle_expand(self):
        """Toggles the visibility of the expanded queue view.

        When collapsed, only the header is shown; when expanded, full queue control is visible.
        """
        is_visible = self.expanded_frame.isVisible()
        self.expanded_frame.setVisible(not is_visible)
        arrow = "▼" if not is_visible else "▲"
        self.collapsed_button.setText(
            f"Queue: Currently Running: {self.current_running_text} {arrow}"
        )

    def set_current_running(self, text):
        """Updates the header to show which experiment is currently running."""
        self.current_running_text = text
        if not self.expanded_frame.isVisible():
            self.collapsed_button.setText(f"Queue: Currently Running: {text} ▲")

    def add_to_active_queue(self, widget_item):
        """Adds a queued experiment item to the active queue (for immediate execution)."""
        self.active_queue_list.addItem(widget_item)

    def add_to_working_queue(self, queued_experiment):
        """Adds a queued experiment item to the working queue (editable list).

        Also attaches the experiment’s QWidget display.
        """
        print(
            f"Adding queued experiment: {queued_experiment.parameters_dict['display_name']} to working queue..."
        )
        self.working_queue_list.addItem(queued_experiment)
        self.working_queue_list.setItemWidget(
            queued_experiment, queued_experiment.widget
        )

    def show_history(self):
        """Opens a scrollable dialog showing the log of all completed experiments in the session."""
        if not self.history_log:
            QMessageBox.information(
                self, "History", "No experiments have been run yet."
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Experiment History")
        dialog.setMinimumSize(500, 400)

        layout = QVBoxLayout(dialog)

        history_text = QTextEdit()
        history_text.setReadOnly(True)

        # Format each log entry with timestamp, name, and save path
        log_entries = []
        for timestamp, name, location in self.history_log:
            log_entries.append(
                f"{timestamp}\nExperiment: {name}\nSaved to: {location}\n\n"
            )

        history_text.setText("".join(log_entries))
        layout.addWidget(history_text)

        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.exec_()

    def clear_queue(self):
        """Clears all items from both the working and active queues after user confirmation."""
        if self.working_queue_list.count() == 0 and self.active_queue_list.count() == 0:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Clear Queue",
            "Are you sure you want to clear the queue? Experiments will be lost forever.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # Clear working queue
            while self.working_queue_list.count() > 0:
                item = self.working_queue_list.takeItem(0)
                if isinstance(item, QueuedExperiment):
                    del item.widget
                    del item.experiment
                del item

            # Clear active queue
            while self.active_queue_list.count() > 0:
                item = self.active_queue_list.takeItem(0)
                if isinstance(item, QueuedExperiment):
                    del item.widget
                    del item.experiment
                del item


class ExperimentSetupDialog(QDialog):
    """Wraps an ExperimentType instance with GUI display and metadata for use in the queue.

    Supports editing, moving, duplicating, and deleting queue entries through the interface.
    """

    def __init__(
        self,
        experiment_type,
        parameters,
        last_used_directory=None,
        edit_settings=False,
        parent=None,
        values=None,
    ):
        """
        A configuration dialog for queued experiments.

        This dialog allows the user to:
        - Name the experiment
        - Select which tasks (read processed, read unprocessed, sweep) to run
        - Choose whether to save the resulting graph and where to save it
        - (Optionally) edit the experiment settings panel on the right

        Used when adding a new experiment to the queue or editing an existing one.
        """
        super().__init__(parent)
        self.setWindowTitle("Configure Queued Experiment")
        self.setMinimumSize(600, 400)
        self.edit_settings = edit_settings

        self.display_name = ""
        self.save_graph_output = False
        self.save_directory = last_used_directory or os.getcwd()

        main_layout = QHBoxLayout(self)

        # --- LEFT PANEL: Name, checkboxes, directory, buttons ---
        left_box = QVBoxLayout()

        self.name_label = QLabel("Experiment Name:")
        self.name_input = QLineEdit()
        default_name = "default name"
        self.name_input.setText(default_name)
        left_box.addWidget(self.name_label)
        left_box.addWidget(self.name_input)

        # Checkboxes for task selection
        self.read_processed_checkbox = QCheckBox("Read Processed")
        left_box.addWidget(self.read_processed_checkbox)
        self.read_unprocessed_checkbox = QCheckBox("Read Unprocessed")
        left_box.addWidget(self.read_unprocessed_checkbox)
        self.sweep_checkbox = QCheckBox("Sweep")
        left_box.addWidget(self.sweep_checkbox)

        self.save_checkbox = QCheckBox("Save graph output")
        left_box.addWidget(self.save_checkbox)

        # Directory selector
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

        # OK / Cancel buttons
        button_row = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel")
        self.ok_button = QPushButton("Okay")
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.ok_button)
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button.clicked.connect(self.accept)

        left_box.addStretch()
        left_box.addLayout(button_row)

        # --- RIGHT PANEL: Settings tree view ---
        self.settings_panel = DynamicSettingsPanel()
        self.settings_panel.load_settings_panel(EXPERIMENT_TEMPLATES[experiment_type])

        self._apply_parameters_to_settings(parameters)

        if not self.edit_settings:
            self.settings_panel.setDisabled(True)

        # Assemble layout
        main_layout.addLayout(left_box, 2)
        main_layout.addWidget(self.settings_panel, 3)

        # Pre-fill left panel values if provided
        if values:
            self.name_input.setText(values.get("display_name", "default name"))
            self.read_processed_checkbox.setChecked(values.get("read_processed", False))
            self.read_unprocessed_checkbox.setChecked(
                values.get("read_unprocessed", False)
            )
            self.sweep_checkbox.setChecked(values.get("sweep", False))
            self.save_checkbox.setChecked(values.get("save_graph_output", True))
            self.dir_input.setText(values.get("save_directory", self.save_directory))

    def _apply_parameters_to_settings(self, param_dict):
        """
        Populate the right-side settings panel widgets with values from a saved parameters dictionary.

        This is used to initialize the settings UI with stored values when editing or reviewing a queued experiment.

        @param param_dict -- A dictionary of parameter keys and values used to pre-fill widgets.
        """
        tree = self.settings_panel.settings_tree
        root = tree.invisibleRootItem()
        # Loop through each group in the settings tree
        for i in range(root.childCount()):

            # Loop through each setting item in the group
            grp = root.child(i)
            for j in range(grp.childCount()):
                item = grp.child(j)
                widget = tree.itemWidget(item, 1)
                key = getattr(widget, "_underlying_key", None)

                # Handle composite settings (e.g., multiple spin boxes)
                if isinstance(key, list):
                    layout = widget.layout()
                    for idx, subkey in enumerate(key):
                        if subkey in param_dict:
                            val = param_dict[subkey]
                            sub_widget = layout.itemAt(idx).widget()
                            self._apply_value_to_widget(sub_widget, val)

                # Handle single-key settings
                else:
                    if key in param_dict:
                        val = param_dict[key]
                        self._apply_value_to_widget(widget, val)

    def _apply_value_to_widget(self, widget, value):
        """
        Apply a given value to a corresponding Qt input widget in the settings panel.

        This is a helper method used during parameter loading to set the UI state
        based on previously saved experiment settings.

        @param widget -- The Qt widget instance (e.g., QSpinBox, QCheckBox) to populate.
        @param value -- The value to apply to the widget.
        """
        # Handle numeric inputs
        if isinstance(widget, QSpinBox):
            widget.setValue(int(value))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value))

        # Handle boolean input
        elif isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))

        # Handle string input
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value))

        # Handle dropdown input
        elif isinstance(widget, QComboBox):
            idx = widget.findText(str(value))
            if idx != -1:
                widget.setCurrentIndex(idx)

    def get_updated_parameters(self):
        """
        Collect the current values from the settings panel and return them as a dictionary.

        This function is used when the user confirms the dialog, ensuring that all modified
        parameter values are extracted from their widgets for use in queue setup or execution.

        @return dict -- A dictionary mapping parameter keys to their current values.
        """
        updated_params = {}
        tree = self.settings_panel.settings_tree
        root = tree.invisibleRootItem()

        # Traverse each group in the settings tree
        for i in range(root.childCount()):
            grp = root.child(i)

            # Traverse each setting item within the group
            for j in range(grp.childCount()):
                item = grp.child(j)
                widget = tree.itemWidget(item, 1)
                key = getattr(widget, "_underlying_key", None)

                # Handle multi-key composite widgets (e.g., sweep start/end/step)
                if isinstance(key, list):
                    layout = widget.layout()
                    for idx, subkey in enumerate(key):
                        sub_widget = layout.itemAt(idx).widget()
                        updated_params[subkey] = self._get_widget_value(sub_widget)

                # Handle standard single-key widgets
                else:
                    if key:
                        updated_params[key] = self._get_widget_value(widget)
        return updated_params

    def _get_widget_value(self, widget):
        """
        Retrieve the current value from a given Qt input widget.

        This helper is used to extract values from the settings panel during parameter gathering.

        @param widget -- The widget to read from (QSpinBox, QLineEdit, etc.)
        @return The value currently set in the widget.
        """
        # Numeric inputs
        if isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
            return widget.value()

        # Boolean input
        elif isinstance(widget, QCheckBox):
            return widget.isChecked()

        # Text input
        elif isinstance(widget, QLineEdit):
            return widget.text()

        # Dropdown selector
        elif isinstance(widget, QComboBox):
            return widget.currentText()

        # Fallback for unknown widget types
        else:
            return None

    def get_values(self):
        """
        Retrieve the metadata values from the left side of the dialog.

        This includes experiment name, which actions to perform (read/sweep),
        save preferences, and output directory — separate from the right-side parameter tree.

        @return dict -- Dictionary of UI selections related to queue and file saving.
        """
        return {
            "display_name": self.name_input.text().strip(),
            "read_processed": self.read_processed_checkbox.isChecked(),
            "read_unprocessed": self.read_unprocessed_checkbox.isChecked(),
            "sweep": self.sweep_checkbox.isChecked(),
            "save_graph_output": self.save_checkbox.isChecked(),
            "save_directory": self.dir_input.text().strip(),
        }

    def choose_directory(self):
        """
        Open a folder selection dialog and update the directory input field.

        This is used to let the user choose where graph output files should be saved.
        """
        selected_dir = QFileDialog.getExistingDirectory(
            self, "Select Save Directory", self.save_directory
        )

        # If a directory was selected, update both internal state and UI
        if selected_dir:
            self.save_directory = selected_dir
            self.dir_input.setText(selected_dir)


class QueuedExperiment(QListWidgetItem):
    """
    Represents a single experiment in the working or active queue.

    Stores experiment configuration, user preferences, and metadata.
    Includes a QWidget-based visual representation with action buttons
    for editing, duplicating, moving, or deleting the experiment.
    """

    def __init__(
        self,
        start_stop_sweep_function,
        experiment: ExperimentType,
        queue_manager,
        last_used_directory=None,
        parameters_dict=None,
    ):
        super().__init__()

        self.start_stop_sweep_function = start_stop_sweep_function
        self.experiment = experiment
        self.queue_manager = queue_manager
        self.experiment_type = experiment.type

        # --- Initialize parameters from dictionary or user dialog ---
        if parameters_dict:
            self.parameters_dict = parameters_dict.copy()
            self.valid = True
        else:
            # If no pre-defined dictionary, prompt user for config
            initial_params = experiment.parameters.copy()

            default_name = self.generate_default_display_name()

            dialog = ExperimentSetupDialog(
                self.experiment_type,
                initial_params,
                last_used_directory or os.getcwd(),
                values={"display_name": default_name},
            )

            if dialog.exec_() == QDialog.Rejected:
                self.valid = False
                return

            updated_params = dialog.get_updated_parameters()

            values = dialog.get_values()

            self.parameters_dict = {
                "display_name": values["display_name"],
                "parameters": updated_params,
                "read_processed": values["read_processed"],
                "read_unprocessed": values["read_unprocessed"],
                "sweep": values["sweep"],
                "save_graph_output": values["save_graph_output"],
                "save_directory": values["save_directory"],
                "current_queue": "working_queue",
            }

            self.valid = True

        # --- Build visual queue item widget ---
        self.widget = QWidget()
        self.widget.setStyleSheet(
            """
            QWidget {
                background-color: #f9f9f9;
                border: 2px solid #888;
                border-radius: 6px;
                padding: 8px;
            }
        """
        )
        self.layout = QVBoxLayout(self.widget)
        self.layout.setContentsMargins(4, 4, 4, 4)

        row_layout = QHBoxLayout()
        row_layout.setSpacing(8)

        # Display name label
        self.label = QLabel(f"{self.parameters_dict['display_name']}")
        self.label.setStyleSheet("font-weight: bold;")
        row_layout.addWidget(self.label)
        row_layout.addStretch()

        # Action buttons: Move / Copy / Delete / Edit
        button_size = QSize(48, 24)
        self.change_queue_button = QPushButton("Move")
        self.duplicate_button = QPushButton("Copy")
        self.delete_button = QPushButton("Delete")
        self.info_button = QPushButton("Edit")

        # Hide edit button in the active queue
        if self.parameters_dict.get("current_queue") == "active_queue":
            self.info_button.hide()

        row_layout.addWidget(self.change_queue_button)
        row_layout.addWidget(self.duplicate_button)
        row_layout.addWidget(self.delete_button)
        row_layout.addWidget(self.info_button)

        # Style and connect buttons
        for btn in [
            self.change_queue_button,
            self.duplicate_button,
            self.delete_button,
            self.info_button,
        ]:
            btn.setFixedSize(button_size)
            btn.setStyleSheet(
                """
                QPushButton {
                    padding: 2px;
                    border: 1px solid #aaa;
                    border-radius: 4px;
                    background-color: #e6e6e6;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
            """
            )

        self.delete_button.clicked.connect(self.delete_self)
        self.info_button.clicked.connect(self.show_info_popup)
        self.change_queue_button.clicked.connect(self.move_queues)
        self.duplicate_button.clicked.connect(self.duplicate)

        self.layout.addLayout(row_layout)

        self.widget.setLayout(self.layout)
        self.setSizeHint(self.widget.sizeHint())

    def generate_default_display_name(self):
        """
        Generate a unique default name for the experiment based on its type and sweep name.

        Format:
            - For Spin Echo:   SE:HahnEcho
            - For Pulse Sweep: PFS:FreqSweep
            - Appends a numeric suffix if duplicates already exist in the queues

        @return str -- A unique display name string.
        """
        # Map experiment type to abbreviation
        type_abbr = {"Spin Echo": "SE", "Pulse Frequency Sweep": "PFS"}
        abbr = type_abbr.get(self.experiment_type, "UNK")

        # Extract and sanitize the sweep name
        expt_name = self.experiment.parameters.get("expt", "exp").replace(" ", "")
        base_name = f"{abbr}:{expt_name}"

        # Check for duplicates in both queues
        count = 0
        for list_widget in [
            self.queue_manager.active_queue_list,
            self.queue_manager.working_queue_list,
        ]:
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if isinstance(item, QueuedExperiment):
                    other_name = item.parameters_dict.get("display_name", "")
                    if other_name.startswith(base_name):
                        count += 1
        # Append suffix if necessary
        if count == 0:
            return base_name
        else:
            return f"{base_name}{count}"

    def startDrag(self):
        """
        Placeholder method for enabling drag behavior in the QListWidget.

        This is intended to support reordering or moving queue items,
        but the drag action itself is currently delegated to the QListWidget internals.
        """
        listwidget = self.listWidget()
        if listwidget:
            drag = listwidget.model().supportedDragActions()  # No-op placeholder

    def lock_experiment(self, experiment):
        """
        Visually disables (greys out) the experiment widget in the queue UI.

        Called when a queued experiment is running, to prevent editing or interaction.
        """
        if self == experiment:
            self.widget.setStyleSheet("background-color: #d0d0d0;")

    def unlock_experiment(self, experiment):
        """
        Re-enables (un-greys) the experiment widget, restoring its normal appearance.

        Typically called after an experiment finishes or is aborted early.
        """
        if self == experiment:
            self.widget.setStyleSheet("background-color: #f9f9f9;")

    @property
    def has_sweep(self):
        """
        Check whether the user has enabled the 'Sweep' option for this experiment.

        @return bool -- True if sweep is selected, False otherwise.
        """
        return self.parameters_dict.get("sweep", False)

    @property
    def has_read_unprocessed(self):
        """
        Check whether the user has enabled 'Read Unprocessed' for this experiment.

        @return bool -- True if read unprocessed is selected, False otherwise.
        """
        return self.parameters_dict.get("read_unprocessed", False)

    @property
    def has_read_processed(self):
        """
        Check whether the user has enabled 'Read Processed' for this experiment.

        @return bool -- True if read processed is selected, False otherwise.
        """
        return self.parameters_dict.get("read_processed", False)

    def set_done(self):
        """
        Mark this experiment as completed in the UI.

        Visually greys out the widget and disables all action buttons to prevent further editing.
        Called after the experiment has successfully run in the queue.
        """
        print("Marking experiment done...")

        # Grey out the entire widget
        self.widget.setStyleSheet(
            """
            QWidget {
                background-color: #cccccc;
                border: 2px solid #444;
                border-radius: 6px;
                padding: 8px;
            }
        """
        )

        # Disable all action buttons
        for button in [
            self.change_queue_button,
            self.duplicate_button,
            self.delete_button,
            self.info_button,
        ]:
            button.setEnabled(False)

    def init_experiment(self):
        """
        Load saved parameters into the experiment and reinitialize its state.

        Called before running the experiment to ensure it reflects the most
        recent user-defined settings from the queue entry.
        """
        self.experiment.set_parameters(self.parameters_dict["parameters"])

    def show_info_popup(self):
        """
        Open a dialog allowing the user to review or edit this experiment's settings.

        This allows modification of both the left-hand metadata (name, sweep options, etc.)
        and the right-hand settings panel. Updates the queue entry upon confirmation.
        """
        dialog = ExperimentSetupDialog(
            self.experiment_type,
            self.parameters_dict["parameters"].copy(),
            last_used_directory=self.parameters_dict["save_directory"],
            edit_settings=True,
            values=self.parameters_dict,
        )
        if dialog.exec_() == QDialog.Accepted:
            # Update internal state from dialog
            values = dialog.get_values()
            self.parameters_dict["display_name"] = values["display_name"]
            self.parameters_dict["read_processed"] = values["read_processed"]
            self.parameters_dict["read_unprocessed"] = values["read_unprocessed"]
            self.parameters_dict["sweep"] = values["sweep"]
            self.parameters_dict["save_graph_output"] = values["save_graph_output"]
            self.parameters_dict["save_directory"] = values["save_directory"]
            self.parameters_dict["parameters"] = dialog.get_updated_parameters()

            # Update label text
            self.label.setText(
                f"{self.parameters_dict['display_name']} — {self.experiment_type}"
            )

    def delete_self(self):
        """
        Remove this experiment from the queue and clean up associated resources.

        This deletes the experiment from either the working or active queue,
        depending on its current location. Frees memory used by the widget and experiment.
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
        Move this experiment between the working and active queues.

        Internally duplicates the experiment in the new queue and deletes the original.
        This avoids PyQt ownership issues (e.g., segfaults from reparenting widgets).
        """
        clone_dict = self.parameters_dict.copy()

        # Flip the target queue and label
        if clone_dict["current_queue"] == "working_queue":
            clone_dict["current_queue"] = "active_queue"
            target_queue = self.queue_manager.active_queue_list
        else:
            clone_dict["current_queue"] = "working_queue"
            target_queue = self.queue_manager.working_queue_list

        # Create a new instance with the same config but new queue context
        new_item = QueuedExperiment(
            self.start_stop_sweep_function,
            self.experiment,
            self.queue_manager,
            parameters_dict=clone_dict,
        )

        if not new_item.valid:
            return

        # Add to target queue and remove original
        target_queue.addItem(new_item)
        target_queue.setItemWidget(new_item, new_item.widget)

        self.delete_self()

    def duplicate(self):
        """
        Create a copy of this experiment in the same queue with a new display name.

        Prompts the user for a name for the duplicated experiment.
        Copies all parameter settings and metadata.
        """
        new_name, ok = QInputDialog.getText(
            self.widget,
            "Duplicate Experiment",
            "Enter a name for the duplicated experiment:",
            QLineEdit.Normal,
            self.parameters_dict["display_name"] + " (Copy)",
        )
        if not ok or not new_name.strip():
            return

        # Clone experiment settings and assign new display name
        clone_dict = self.parameters_dict.copy()
        clone_dict["display_name"] = new_name.strip()

        new_item = QueuedExperiment(
            self.start_stop_sweep_function,
            self.experiment,
            self.queue_manager,
            parameters_dict=clone_dict,
        )

        if not new_item.valid:
            return

        # Insert into appropriate queue and attach its widget
        if self.parameters_dict["current_queue"] == "active_queue":
            self.queue_manager.active_queue_list.addItem(new_item)
            self.queue_manager.active_queue_list.setItemWidget(
                new_item, new_item.widget
            )
        else:
            self.queue_manager.working_queue_list.addItem(new_item)
            self.queue_manager.working_queue_list.setItemWidget(
                new_item, new_item.widget
            )


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
