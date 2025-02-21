import pickle
import numpy as np
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QSpinBox, QSplitter, QScrollArea, QLabel, QFrame, QComboBox, 
                             QGroupBox, QFormLayout, QSizePolicy, QCheckBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt

# Function to load pickle file
def load_pickle_file(file_path):
    try:
        with open(file_path, 'rb') as file:
            data = pickle.load(file)
            return data
    except Exception as e:
        print(f"Error loading pickle file: {e}")
        return None

# Function to populate the settings tree with appropriate widgets
def populate_tree(tree_widget, data):
    tree_widget.clear()
    if isinstance(data, dict):
        for category, settings in data.items():
            category_item = QTreeWidgetItem([category])
            tree_widget.addTopLevelItem(category_item)
            if isinstance(settings, dict):
                for key, value in settings.items():
                    item = QTreeWidgetItem([key])
                    category_item.addChild(item)
                    widget = create_setting_widget(value)
                    if widget:
                        tree_widget.setItemWidget(item, 1, widget)

# Function to create the appropriate input field based on value type
def create_setting_widget(value):
    if isinstance(value, int):
        widget = QSpinBox()
        widget.setValue(value)
    elif isinstance(value, float):
        widget = QDoubleSpinBox()
        widget.setValue(value)
    elif isinstance(value, bool):
        widget = QCheckBox()
        widget.setChecked(value)
    elif isinstance(value, str):
        widget = QComboBox() if value in ["Enabled", "Disabled"] else QLabel(value)
    elif isinstance(value, list):
        widget = QLabel(", ".join(map(str, value)))  # Display lists as comma-separated text
    else:
        widget = QLabel("N/A")
    return widget

class ExperimentSettingsManager:
    def __init__(self, settings_panel, experiment_dropdown):
        self.settings_panel = settings_panel
        self.experiment_dropdown = experiment_dropdown
        self.templates = {
            "Pulse Frequency Sweep": "esr_notebooks/cw_defaults.pkl",
            "Spin Echo": "esr_notebooks/se_defaults.pkl"
        }
        self.experiment_dropdown.addItems(self.templates.keys())
        self.experiment_dropdown.currentTextChanged.connect(self.update_settings_panel)
        self.update_settings_panel("Pulse Frequency Sweep")

    def update_settings_panel(self, experiment_type):
        file_path = self.templates.get(experiment_type)
        if file_path:
            experiment_settings = load_pickle_file(file_path) or {}
            populate_tree(self.settings_panel.settings_tree, experiment_settings)

class DynamicSettingsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.settings_tree = QTreeWidget()
        self.settings_tree.setHeaderHidden(False)
        self.settings_tree.setColumnCount(2)
        self.settings_tree.setHeaderLabels(["Setting", "Value"])
        self.main_layout.addWidget(self.settings_tree)

class ExperimentUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        top_menu = QHBoxLayout()
        
        self.experiment_dropdown = QComboBox()
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
        self.experiment_dropdown.currentTextChanged.connect(self.change_experiment_type)

    def change_experiment_type(self, experiment_type):
        self.settings_manager.update_settings_panel(experiment_type)

if __name__ == "__main__":
    app = QApplication([])
    ex = ExperimentUI()
    ex.show()
    app.exec_()
