import sys
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from pulsesweep_gui import pulsesweep_gui  # Assuming pulsesweep_gui is a module for GUI controls
from rfsoc2 import QickSoc  # Assuming this class exists in rfsoc2.py (adjust import as needed)
import gui_setup as gs  # Assuming this is the setup module for GUI controls
from pulsesweep_scripts import *  # Assuming this contains your experiment functions like CPMGProgram

# Example Signal class (simulated structure)
class Signal:
    def __init__(self):
        self.time = np.linspace(0, 10, 100)
        self.i = np.sin(self.time)
        self.q = np.cos(self.time)
        self.x = np.abs(np.sin(self.time))

class ExperimentApp(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize GUI components
        self.setWindowTitle('Experiment with PyQt and Plot')

        # Create QickSoc instance and initial settings
        self.soc = QickSoc()  # Assuming QickSoc is your hardware interface
        self.soccfg = self.soc  # Assuming you might want to keep a config object
        self.sig = Signal()  # Example signal object
        self.devices = None  # Assuming you will set devices based on your hardware
        self.sweep = {}  # Sweep settings

        # Setup GUI layout
        self.initUI()

    def initUI(self):
        # Layouts
        layout = QVBoxLayout()
        control_layout = QHBoxLayout()

        # Add Plot Canvas
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvas(self.fig)  # Convert figure to canvas for PyQt
        layout.addWidget(self.canvas)

        # Add Start Experiment Button
        self.start_button = QPushButton('Start Experiment', self)
        self.start_button.clicked.connect(self.start_experiment)
        control_layout.addWidget(self.start_button)

        # Add additional controls if needed (e.g., stop button, parameters)
        layout.addLayout(control_layout)

        # Set the layout for the window
        self.setLayout(layout)
        self.show()

    def start_experiment(self):
        """ Start the experiment and plot the results """
        config = {}  # Define your config settings for the experiment
        soc = self.soc  # Hardware control
        devices = self.devices  # Device control (set appropriately)
        sweep = self.sweep  # Sweep control (set appropriately)

        # Call your pulsesweep_gui function to get controls and parameters
        controls, parameters = pulsesweep_gui(self.sig, devices, sweep, soc)

        # Run the experiment and plot the results using the read function
        self.read(self.sig, config, soc, None, self.fig)

        # Update the canvas with new data
        self.canvas.draw()

    def read(self, sig, config, soc, output, fig):
        """
        Take and plot a single background-subtracted measurement.
        """
        config['single'] = True
        config['soft_avgs'] = 1
        prog = CPMGProgram(soc, config)  # Assuming this is a function defined elsewhere
        measure_phase(prog, soc, sig)  # Assuming this function is used for measurement
        
        # Remove previous axes and plot the new data
        for ax in fig.axes:
            ax.remove()
        ax = fig.add_subplot(111)
        ax.plot(sig.time, sig.i, color='yellow', label='CH1')
        ax.plot(sig.time, sig.q, color='b', label='CH2')
        ax.plot(sig.time, sig.x, color='g', label='AMP')
        ax.set_xlabel('Time (μs)')
        ax.set_ylabel('Signal (a.u.)')
        ax.legend()

        # Update the plot
        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ExperimentApp()
    sys.exit(app.exec_())
