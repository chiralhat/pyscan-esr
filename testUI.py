from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QSpinBox, QSplitter, QScrollArea, QLabel, QFrame, QComboBox, 
                             QGroupBox, QFormLayout, QSizePolicy, QCheckBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt

import sys
class ExperimentSettingsManager:
    def __init__(self, settings_panel, experiment_dropdown):
        self.settings_panel = settings_panel
        self.experiment_dropdown = experiment_dropdown
        self.experiment_dropdown.addItems(["Pulse Frequency Sweep", "Spin Echo"])
        self.experiment_dropdown.currentTextChanged.connect(self.update_settings_panel)

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

class DynamicSettingsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.settings_tree = QTreeWidget()
        self.settings_tree.setHeaderHidden(False)
        self.settings_tree.setColumnCount(2)
        self.settings_tree.setHeaderLabels(["Setting", "Value"])
        self.main_layout.addWidget(self.settings_tree)
    
    def load_settings(self, settings):
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


class ExperimentUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        top_menu = QHBoxLayout()
        
        self.experiment_dropdown = QComboBox()
        self.experiment_dropdown.addItems(["Pulse Frequency Sweep"])
        self.experiment_dropdown.currentTextChanged.connect(self.change_experiment_type)

        self.file_menu = QComboBox()
        self.file_menu.addItems(["Open Experiment", "Save Experiment", "Save Experiment As", "New Experiment"])
        
        self.run_menu = QComboBox()
        self.run_menu.addItems(["Run Experiment", "Stop Experiment"])
        
        self.plot_menu = QComboBox()
        self.plot_menu.addItems(["Save All Plot Recordings"])
        
        top_menu.addWidget(QLabel("File:"))
        top_menu.addWidget(self.file_menu)
        top_menu.addWidget(QLabel("Experiment:"))
        top_menu.addWidget(self.experiment_dropdown)
        top_menu.addWidget(QLabel("Run:"))
        top_menu.addWidget(self.run_menu)
        top_menu.addWidget(QLabel("Plots:"))
        top_menu.addWidget(self.plot_menu)
        
        main_layout.addLayout(top_menu)
        
        main_splitter = QSplitter(Qt.Horizontal)
        self.settings_panel = DynamicSettingsPanel()
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setWidget(self.settings_panel)

        output_container = QSplitter(Qt.Vertical)
        graph_section = QLabel("Graphs Area")
        graph_section.setFrameShape(QFrame.Box)
        graph_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        error_log = QLabel("Error Log")
        error_log.setFrameShape(QFrame.Box)
        error_log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        output_container.addWidget(graph_section)
        output_container.addWidget(error_log)
        
        main_splitter.addWidget(settings_scroll)
        main_splitter.addWidget(output_container)
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)

        self.settings_manager = ExperimentSettingsManager(self.settings_panel, self.experiment_dropdown)
        self.change_experiment_type("Pulse Frequency Sweep")

    def change_experiment_type(self, experiment_type):
        self.settings_manager.update_settings_panel(experiment_type)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = ExperimentUI()
    ex.show()
    sys.exit(app.exec_())
