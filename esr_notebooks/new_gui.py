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

import os

## SYDNEY CONSTRUCTION ZONE

# import time
# import importlib
# import mymodule
# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler

# class ReloadHandler(FileSystemEventHandler):
#     def on_modified(self, event):
#         if event.src_path.endswith("mymodule.py"):
#             print("Module changed, reloading...")
#             importlib.reload(mymodule)

# event_handler = ReloadHandler()
# observer = Observer()
# observer.schedule(event_handler, path=".", recursive=False)
# observer.start()

# try:
#     while True:
#         time.sleep(1)
# except KeyboardInterrupt:
#     observer.stop()
# observer.join()


####

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


class ExperimentUI(QWidget):
    """ Main UI Class """
    def __init__(self):
        super().__init__()
        self.initUI()

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
        
def init_app():
        if 'devices' not in globals():
            devices = ps.ItemAttribute()
            sig = ps.ItemAttribute()
            sweep = {}

        soc = QickSoc()
        soccfg = soc
        print("it worked!")

def main():
    init_app()
#     app = QApplication(sys.argv)
#     ex = ExperimentUI()
#     ex.showFullScreen()
#     sys.exit(app.exec_())

    
if __name__ == "__main__":
    main()