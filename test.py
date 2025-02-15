from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QComboBox, QSpinBox, QSplitter, QScrollArea, QLabel, QFrame, 
                             QGroupBox, QFormLayout, QSizePolicy)
from PyQt5.QtCore import Qt
import sys

class ExperimentUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        main_layout = QVBoxLayout(self)
        
        # Persistent Top Menu
        top_menu = QHBoxLayout()
        top_menu.addWidget(QPushButton("Open Experiment"))
        top_menu.addWidget(QPushButton("Save Experiment"))
        top_menu.addWidget(QPushButton("Save Experiment As"))
        top_menu.addWidget(QPushButton("New Experiment"))
        top_menu.addWidget(QComboBox())  # Experiment Type Dropdown
        top_menu.addWidget(QPushButton("Run/Stop Experiment"))
        top_menu.addWidget(QPushButton("Save All Plot Recordings"))
        
        main_layout.addLayout(top_menu)
        
        # Main Splitter (Settings Input <--> Output Section)
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left: Settings Input Section (Scrollable with Collapsible Sections)
        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)
        
        for i in range(5):  # 5 Collapsible Sections
            section = self.createCollapsibleSection(f"Category {i+1}")
            settings_layout.addWidget(section)
        
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setWidget(settings_container)
        
        # Right: Output Section (Resizable within)
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
    
    def createCollapsibleSection(self, title):
        group = QGroupBox(title)
        layout = QFormLayout()
        
        for i in range(10):
            if i % 2 == 0:
                layout.addRow(f"Setting {i+1}", QComboBox())
            else:
                layout.addRow(f"Setting {i+1}", QSpinBox())
        
        group.setLayout(layout)
        return group

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = ExperimentUI()
    ex.show()
    sys.exit(app.exec_())