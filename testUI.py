from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QComboBox, QSpinBox, QSplitter, QScrollArea, QLabel, QFrame, 
                             QGroupBox, QFormLayout, QSizePolicy, QCheckBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt

import sys

class ExperimentSettingsManager:
    def __init__(self, settings_panel):
        self.settings_panel = settings_panel
        self.experiment_templates = {
            "Pulse Frequency Sweep": {
                "main": [
                    {"name": "Start Frequency (GHz)", "type": "double_spin", "min": 0.1, "max": 10.0, "default": 2.4},
                    {"name": "End Frequency (GHz)", "type": "double_spin", "min": 0.1, "max": 10.0, "default": 2.6},
                    {"name": "Number of Points", "type": "spin", "min": 1, "max": 1000, "default": 100}
                ],
                "groups": {
                    "Pulse Parameters": [
                        {"name": "Pulse Width (ns)", "type": "double_spin", "min": 0.1, "max": 100.0, "default": 10.0},
                        {"name": "Pulse Power (dBm)", "type": "spin", "min": -30, "max": 30, "default": 0}
                    ],
                    "Detection Settings": [
                        {"name": "Detection Mode", "type": "combo", "options": ["Phase", "Amplitude"], "default": "Phase"},
                        {"name": "Averaging Count", "type": "spin", "min": 1, "max": 1000, "default": 10}
                    ]
                }
            }
        }
    
    def update_settings_panel(self, experiment_type):
        self.settings_panel.load_settings(self.experiment_templates.get(experiment_type, {"main": [], "groups": {}}))


class DynamicSettingsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.settings_sections = []

        self.settings_container = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_container)
        self.settings_container.setLayout(self.settings_layout)
        
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setWidget(self.settings_container)

        self.main_layout.addWidget(self.settings_scroll)
    
    def load_settings(self, settings):
        for section in self.settings_sections:
            section.setParent(None)
        self.settings_sections.clear()
        
        for setting in settings["main"]:
            widget = self.create_setting_widget(setting)
            self.settings_layout.addWidget(QLabel(setting["name"]))
            self.settings_layout.addWidget(widget)

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

        self.settings_manager = ExperimentSettingsManager(self.settings_panel)
        self.change_experiment_type("Pulse Frequency Sweep")

    def change_experiment_type(self, experiment_type):
        self.settings_manager.update_settings_panel(experiment_type)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = ExperimentUI()
    ex.show()
    sys.exit(app.exec_())
