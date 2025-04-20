import matplotlib
matplotlib.use('Qt5Agg')  # Must be done before importing pyplot!
import matplotlib.pyplot as plt
# Do not move the above from the top of the file
from PyQt5.QtWidgets import (QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
                             QSplitter, QScrollArea, QLabel, QFrame, QComboBox, QSizePolicy, 
                             QCheckBox, QSpinBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem, 
                             QMessageBox, QTextEdit, QLineEdit, QStyledItemDelegate, QPushButton, 
                             QFileDialog, QStyledItemDelegate, QStyleOptionViewItem, QMenu)
from PyQt5.QtCore import Qt, QRect, QTextStream, QObject, QThread, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtGui import QPainter, QTextOption, QClipboard, QPixmap


import shutil
import sys
import h5py
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import sys, os
sys.path.append('../')
from rfsoc2 import *
import numpy as np
from time import sleep, time
from datetime import date, datetime
import io
from pathlib import Path
from pulsesweep_gui import *
from spinecho_gui import *
import pickle
import pyvisa
import pulsesweep_gui as psg
import spinecho_gui as seg
import pyscan as ps
import os


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
                 "min": 1, "max": 1000000, "default": 1000, "tool tip": "Helpful information"}, #EXPLICITLY MADE THESE INTS
                {"display": "Dir and Name", "key": ["save_dir", "file_name"], #Both save_dir and file_name are strings (contained in save controls)
                 "type": "composite", "default": ["", ""], "tool tip": "Helpful information"},
                {"display": "Experiment", "key": "expt", "type": "combo", #expt is of ipw.Dropdown type (contained in measure)
                 "options": sweep_list, "default": "Pulse Sweep"},
                {"display": "Sweep start, end, step",
                 "key": ["sweep_start", "sweep_end", "sweep_step"], #sweep_start, sweep_end, and sweep_step are all unbounded floats (contained in measure)
                 "type": "composite", "default": [3850.0, 3950.0, 2.0]}],
            "Readout Settings": [
                {"display": "Time Offset", "key": "h_offset", "type": "double_spin", #h_offset is a bounded float between -10000 and 10000 (contained in rfsoc)
                 "min": -10000.0, "max": 10000.0, "default": -0.125}, #CHANGED THESE VALUES FROM 0, 1000, AND 10.0
                {"display": "Readout Length", "key": "readout_length", "type": "double_spin", #readout_length is a bounded float from 0 to 5 (contained in rfsoc)
                 "min": 1.0, "max": 5.0, "default": 0.2}, #CHANGED THESE VALUES FROM 1, 1000, AND 10 ------------------- THIS ONE WAS SAVED AS AN INTEGER IN THE PICKLE FILE AND COULD HAVE BEEN A CAUSE OF THE ERROR
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
                 "default": False},
                {"display": "Initialize on read", "key": "init", "type": "check", #init is an ipw.Checkbox
                 "default": True},
                {"display": "Turn off after sweep", "key": "turn_off", "type": "check", #turn_off is an ipw.Checkbox
                 "default": False}],
            "Utility Settings": [
                {"display": "PSU Addr", "key": "psu_address", "type": "line_edit", #psu_address is an ipw.Dropdown (contained in devices)
                 "default": ""},
                {"display": "Use PSU", "key": "use_psu", "type": "check", #use_psu is an ipw.Checkbox (contained in devices)
                 "default": False},
                {"display": "Use Lakeshore", "key": "use_temp", "type": "check", #use_temp is an ipw.Checkbox (contained in devices)
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
                {"display": "Averaging Time (s)", "key": "sltime", "type": "double_spin",
                 "min": 0.0, "max": 20.0, "default": 0.0},
                {"display": "Experiment", "key": "psexpt", "type": "combo",
                "options" : ['Freq Sweep', 'Field Sweep'], "default": "Freq Sweep"}
                # freq start, stop, step might be needed here, but we could not find them
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
                 "min": 1, "max": 10000000, "default": 10000}, 
                {"display": "Dir and Name", "key": ["save_dir", "file_name"], "type": "composite",
                 "default": ["", ""]}, 
                {"display": "Reps", "key": "ave_reps", "type": "spin",
                 "min": 1, "max": 1000, "default": 1},
                {"display": "Experiment", "key": "expt", "type": "combo",
                 "options": sweep_list, "default": "Hahn Echo"},
                {"display": "Sweep start, end, step",
                 "key": ["sweep_start", "sweep_end", "sweep_step"], "type": "composite",
                 "default": [150.0, 1000.0, 50.0]}],
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
                 "default": False},
                {"display": "Initialize on read", "key": "init", "type": "check", #COULD REMOVE
                 "default": True},
                {"display": "Turn off after sweep", "key": "turn_off", "type": "check",
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
                {"display": "Sub Method", "key": "field_step", "type": "combo",
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


class Worker(QObject):
    """
    A generic worker that runs one of three tasks in a separate thread:
      - read_processed
      - read_unprocessed
      - start_sweep
    We pass in the current_experiment and which task we want to run.
    """

    finished = pyqtSignal()         # Signal emitted when the worker is completely done
    updateStatus = pyqtSignal(str)  # Emit messages that the main thread can display
    plot_update_signal = pyqtSignal(object)  # to pass colormesh

    def __init__(self, experiment, task_name):
        super().__init__()
        self.experiment = experiment
        self.task_name = task_name
        self._stop_requested = False  

    @pyqtSlot()
    def run_snapshot(self):
        """
        Runs the desired method on the experiment in this separate thread
        so the main GUI thread won't freeze.
        """
        if self.task_name == "read_processed":
            self.updateStatus.emit("Reading processed data...\n")
            self.experiment.read_processed()
            self.updateStatus.emit("Done reading processed data.\n")
        elif self.task_name == "read_unprocessed":
            self.updateStatus.emit("Reading unprocessed data...\n")
            self.experiment.read_unprocessed()  
            self.updateStatus.emit("Done reading unprocessed data.\n")

        self.finished.emit()
    
    @pyqtSlot()
    def run_sweep(self):
        """
        Called when we want to do the 'start_sweep' process in a separate thread. Starts a swweep in a QT Thread, and checks every 15 seconds
        if the sweep is over (killing the QT thread if so). 
        """
        self.updateStatus.emit("Starting sweep in worker thread...\n")
        self._stop_requested = False

        self.experiment.start_sweep()
        self.updateStatus.emit("Sweeping...\n")

        for i in range(1000000):
            if self.experiment.sweep['expt'].runinfo.running == False:
                self._stop_requested = True

            if self._stop_requested:
                break  

            sleep(1)  

        if self._stop_requested:
            self.updateStatus.emit("Stop request detected. Exiting sweep early.\n")
        else:
            self.updateStatus.emit("Done sweeping (normal exit).\n")

        self.finished.emit()

    @pyqtSlot()
    def stop_sweep(self):
        """
        Slot to request the worker to stop. Sets a flag that can be checked in the run_sweep method, killing the thread.
        """
        self._stop_requested = True
    
#     @pyqtSlot(object)
#     def update_plot(self, colormesh):
#         self.sweep_graph.ax.clear()
#         self.sweep_graph.ax.set_title("Sweep Result")

#         # Plot new data
#         mesh = colormesh  # already a QuadMesh from ps.plot2D

#         # Add colorbar safely
#         self.sweep_graph.figure.colorbar(mesh, ax=self.sweep_graph.ax)

#         # Redraw canvas
#         self.sweep_graph.canvas.draw()



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

        
class GraphWidget(QWidget):
    """ A QWidget subclass that embeds a Matplotlib figure for real-time plotting.
        This widget provides a graphical interface for visualizing experimental data,
        such as I/Q signals and amplitude over time. It contains a Matplotlib figure
        canvas and a vertical layout to integrate smoothly with PyQt5-based GUIs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)

        # Create the Figure and Axes safely without using pyplot
        self.figure = Figure()
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)

        # Layout for the graphing widget
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)

        # Enable custom context menu
        self.canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        # You can implement this if needed
        pass

    def update_canvas_se(self, time, i, q, x):
        """Clears the current plot and renders new data traces for CH1, CH2, and amplitude."""
        self.ax.clear()
        self.ax.plot(time, i, label='CH1', color='yellow')
        self.ax.plot(time, q, label='CH2', color='blue')
        self.ax.plot(time, x, label='AMP', color='green')
        self.ax.set_xlabel('Time (μs)')
        self.ax.set_ylabel('Signal (a.u.)')
        self.ax.legend()
        self.canvas.draw()
    
    def update_canvas_psweep(self, time, x, fit=None, freq=None):
        print("drawing the graph now")
        print("Matplotlib backend:", matplotlib.get_backend())  # should say 'Qt5Agg'
        self.ax.clear()

        # Plot raw signal
        self.ax.plot(time, x, color='g', label='AMP')

        if fit is not None:
            fit_curve = fit[0](time, *fit[1:])
            self.ax.plot(time, fit_curve, 'r--', label='Exp Fit')

            A, T, Q = fit[1], fit[2], fit[-1]
            xpt = time[len(time) // 5] / 2
            ypt = max(x) * np.array([0.75, 0.65])
            self.ax.text(xpt, ypt[0], f"A={A:.3g} V, T={T:.3g} μs, Q={Q:.3g}")
            if freq is not None:
                self.ax.text(xpt, ypt[1], f"freq (MHz): {freq:.3f}")

        self.ax.set_xlabel('Time (μs)')
        self.ax.set_ylabel('Signal (a.u.)')
        self.ax.legend()
        self.canvas.draw()
    
    def show_context_menu(self, pos):
        menu = QMenu()
        copy_action = menu.addAction("Copy graph to clipboard")
        action = menu.exec_(self.canvas.mapToGlobal(pos))
        if action == copy_action:
            self.copy_to_clipboard()

    def copy_to_clipboard(self):
        # Save current canvas to QPixmap
        buf = io.BytesIO()
        self.figure.savefig(buf, format='png')
        buf.seek(0)
        image = QPixmap()
        image.loadFromData(buf.getvalue())

        # Copy to clipboard
        QApplication.clipboard().setPixmap(image)
        print("📋 Copied graph to clipboard.")

        
class SweepPlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        self.xdata = []
        self.ydata = []
        self.line, = self.ax.plot([], [], 'o-')

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        

class DynamicSettingsPanel(QWidget):
    """A QWidget-based panel that dynamically generates a settings tree from a configuration template.
        This class is responsible for rendering a scrollable, two-column tree view of
        experiment settings. It supports various input types such as spin boxes,
        combo boxes, checkboxes, line edits, and composite widgets, allowing for
        flexible experiment configuration. t"""
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self) #The main layout of the panel.

        self.settings_tree = QTreeWidget() #The tree structure displaying setting names and editable widgets.
        self.settings_tree.setHeaderHidden(False)
        self.settings_tree.setColumnCount(2)
        self.settings_tree.setHeaderLabels(["Setting", "Value"])
        self.settings_tree.setColumnWidth(0, 200)
        self.settings_tree.setColumnWidth(1, 100)

        self.settings_scroll = QScrollArea() #Scrollable area containing the settings tree.
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setWidget(self.settings_tree)
        self.main_layout.addWidget(self.settings_scroll)

    def load_settings_panel(self, settings):
        """Populates the settings panel using a structured dictionary of grouped settings.
            This method clears the current tree and rebuilds it based on the provided
            template, organizing settings into collapsible groups. Each setting is rendered
            with an appropriate input widget (e.g., spin box, combo box, checkbox).

            @param settings -- A triply nested dictionary containing setting groups and items, typically
                                in the format:
                                {
                                    "groups": {
                                        "Group Name": [
                                            {"display": ..., "key": ..., "type": ..., ...},
                                            ...
                                        ]
                                    }
                                }"""
        self.settings_tree.clear() #reset settings tree

        for group_name, group_settings in settings.get("groups", {}).items(): #iterate through the setting groups and load each one
            group_item = QTreeWidgetItem([group_name])
            self.settings_tree.addTopLevelItem(group_item)
            group_item.setExpanded(group_name == "Main Settings")

            for setting in group_settings: #iterate through the individual settings for each setting group and load each setting
                item = QTreeWidgetItem()
                group_item.addChild(item)
                widget = self.create_setting_widget(setting)
                widget._underlying_key = setting.get("key")
                self.settings_tree.setItemWidget(item, 1, widget)
                label_widget = QLabel(setting.get("display", setting.get("name", "N/A")))
                label_widget.setWordWrap(True)
                label_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
                label_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                if "tool tip" in setting.keys():
                    label_widget.setToolTip(setting["tool tip"]) #This references each individual setting's tool tip (see EXPERIMENT_TEMPLATES below)    
                
                #update settings tree 
                self.settings_tree.setItemWidget(item, 0, label_widget)

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
        return widget



class ExperimentType(QObject):
    """Handles backend logic, configuration, and hardware interaction for a specific experiment type.
    This class manages the lifecycle of an experiment (e.g., Spin Echo, Pulse Frequency Sweep),
    including setting parameters, initializing hardware, running sweeps, and reading results."""
    plot_update_signal = pyqtSignal()  # signal with no arguments
    def __init__(self, type):
        super().__init__()
        self.type = type #The name of the experiment type (e.g., 'Spin Echo').
        
        #harware releated:
        self.soc = QickSoc() #Hardware interface for the RFSoC system.
        self.soccfg = self.soc #Alias for soc, used for compatibility.
        self.devices = ps.ItemAttribute() #Container for hardware components (e.g., PSU, temperature controller).
        self.sig = ps.ItemAttribute() #Container for storing acquired signal data.
        
        self.parameters = {} #Settings used to configure the experiment (input).
        self.sweep = {} #Stores sweep-related objects and state (output).

        #for saving the parameters you entered into the settings panel
        if self.type == "Spin Echo":
            self.default_file = "se_defaults.pkl" #Default filename used for storing results from se experiments
        elif self.type == "Pulse Frequency Sweep":
            self.default_file = "ps_defaults.pkl" #Default filename used for storing results from ps experiments
            
        # NEW current experiment graph
        self.graph = GraphWidget() #Widget used for plotting experiment results in the graph panel of the UI.
        self.sweep_graph= SweepPlotWidget()

        #Experiment objects that will be initialized later in self.init_pyscan_experiment
        self.spinecho_gui = None
        self.pulsesweep_gui = None
        

    def init_pyscan_experiment(self):
        """This initializes a pyscan experiment with functions from the correct 
        experiment type scripts and GUI files."""
        if self.type == "Spin Echo":
            # NEW: created spinecho_gui objects from updated spinecho gui file
            self.spinecho_gui = seg.SpinechoExperiment(self.graph)
            self.spinecho_gui.init_experiment(self.devices, self.parameters, self.sweep, self.soc)
        elif self.type == "Pulse Frequency Sweep":
            self.pulsesweep_gui = psg.PulseSweepExperiment(self.graph)
            self.pulsesweep_gui.init_experiment(self.devices, self.parameters, self.sweep, self.soc)

    def set_parameters(self, parameters):
        """Takes in parameters read from the settings panel in the UI, 
        copies them into the parameters dictionary, and then modifies them slightly
        so they are ready for the experiment
        
        @param parameters -- dictionary of settings used to configure the experiment taken from EXPERIMENT_TEMPLATES"""

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
            temp = self.devices.ls335.get_temp()

        # Initialize pyscan experiment if necessary
        #NEED TO REVISIT THIS
        if not self.parameters.get('init', False):
            pass  # No action required if 'init' is False
        else:
            self.init_pyscan_experiment()

    def read_processed(self):
        """"
        Takes a snapshot of the current state and processes it before displaying it
        """
        if self.type == "Spin Echo":
            self.spinecho_gui.read_processed(self.sig, self.parameters, self.soc)
        elif self.type == "Pulse Frequency Sweep":
            self.pulsesweep_gui.read_processed(self.sig, self.parameters, self.soc)
            
    def read_unprocessed(self):
        """"
        Takes a snapshot of the current state and doesn't process it before display it
        """
        if self.type == "Spin Echo":
            self.spinecho_gui.read_unprocessed(self.sig, self.parameters, self.soc)
        elif self.type == "Pulse Frequency Sweep":
            self.pulsesweep_gui.read_unprocessed(self.sig, self.parameters, self.soc)

    def emit_plot_update(self):
        try:
            colormesh = ps.plot2D(self.sweep['expt'], x_name='t', transpose=1)
            self.plot_update_signal.emit(colormesh)
        except Exception as e:
            print("Plot update failed:", e)
            
    def run_sweep(self):#, output, fig):
        """actually runs a sweep"""
        self.sweep['expt'].start_time = time()
        self.sweep['expt'].start_thread()
        
        # Use a QTimer or separate thread to wait before plotting
        QTimer.singleShot(20000, self.emit_plot_update)  # wait 20s
        
    
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
            
#     def copy_hdf5_safely(source_path, dest_path):
#         try:
#             shutil.copy2(source_path, dest_path)
#             return True
#         except Exception as e:
#             print("Copy error:", e)
#             return False
            
#     def update_sweep_plot(self):
#         print("Sweep is running — updating plot")

#         # Find latest file
#         original = get_latest_hdf5_file("250415_Hahn_looptest")
#         if original is None:
#             print("No HDF5 file found yet")
#             return

#         # Copy to temp
#         temp_copy = "temp_sweep_copy.hdf5"
#         if copy_hdf5_safely(original, temp_copy):
#             # Plot from the temp file
#         try:
#             with h5py.File(file_path, 'r') as f:
#                 x = np.array(f['delay_sweep'])   # y-axis
#                 y = np.array(f['time'])          # x-axis
#                 z = np.array(f['x'])             # data

#             # Clean data
#             z = np.ma.masked_invalid(z)

#             ax.clear()
#             im = ax.imshow(
#                 z.T,  # transpose to match live_plot2D
#                 extent=[x.min(), x.max(), y.min(), y.max()],
#                 aspect='auto',
#                 origin='lower'
#             )
#             ax.set_xlabel('delay_sweep')
#             ax.set_ylabel('time')
#             canvas.draw()
#         except Exception as e:
#             print("Live plot HDF5 error:", e)
            
          
        
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

        #For button logic
        self.is_process_running = False
        self.settings_changed = False

        # Default experiment
        self.current_experiment = self.experiments["Spin Echo"]
        self.experiment_templates = EXPERIMENT_TEMPLATES
        self.temp_parameters = {}

        # Create main UI elements
        self.settings_panel = DynamicSettingsPanel() 
        self.graphs_panel = self.init_graphs_panel()
        self.error_log = self.init_error_log_widget()
        self.top_menu_bar = self.init_top_menu_bar()

        # Build the main layout with splitters
        self.init_layout()
        self.read_unprocessed_btn.setEnabled(False)
        self.read_processed_btn.setEnabled(False)
        self.sweep_start_stop_btn.setEnabled(False)
        self.set_parameters_and_initialize_btn.setEnabled(True)

        # Load some default experiment into the settings panel
        self.current_experiment = self.experiments["Spin Echo"]
        self.temp_parameters = {}
        
        # Set up the custom stream for stdout and stderr
        dual_stream = DualStream(self.log_text)  # Create the custom stream object
        sys.stdout = dual_stream  # Redirect stdout to the dual stream
        sys.stderr = dual_stream  # Redirect stderr to the dual stream

        #change function assigned to each button
        self.settings_panel.load_settings_panel(self.experiment_templates.get("Spin Echo", {"main": [], "groups": {}}))

        #setup for graph saving
        self.last_saved_graph_path = None
        
        self.current_experiment.plot_update_signal.connect(self.update_plot)
#         # Create a timer to refresh the sweep plot so it plots live
#         self.plot_timer = QTimer(self)
#         self.plot_timer.timeout.connect(self.refresh_sweep_plot)

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

        main_layout.addWidget(self.main_splitter, 6)

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
        graph_layout.addWidget(self.current_experiment.sweep_graph)

        # Save graph button
        self.save_graph_btn = QPushButton("Save Graph As...")
        self.save_graph_btn.clicked.connect(self.save_current_graph)
        graph_layout.addWidget(self.save_graph_btn)

        # Directory label (clickable path)
        self.last_saved_path_label = QLabel("No graph saved yet.")
        self.last_saved_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.last_saved_path_label.setStyleSheet("color: blue; text-decoration: underline;")
        self.last_saved_path_label.mousePressEvent = self.open_saved_graph_folder
        graph_layout.addWidget(self.last_saved_path_label)

        return graph_section_widget

    def init_error_log_widget(self):
        """Creates a small widget with an 'Error Log' label and the log text area below it."""
        error_widget = QWidget()
        vlayout = QVBoxLayout(error_widget)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.setSpacing(5)

        label = QLabel("Error Log")
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
        self.set_parameters_and_initialize_btn.clicked.connect(self.read_and_set_parameters)
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

    def init_settings_panel(self):
        # Settings Panel
        self.settings_panel = DynamicSettingsPanel()
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setWidget(self.settings_panel)

        # Load initial settings
        self.current_experiment = self.experiments["Spin Echo"]
        self.temp_parameters = {}
        self.settings_panel.load_settings_panel(self.experiment_templates.get("Spin Echo", {"main": [], "groups": {}}))
        
        return settings_scroll

    def change_experiment_type(self, experiment_type):
        self.current_experiment.stop_sweep()
        print("Changing experiment type to " + experiment_type + "...\n")
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

    def read_and_set_parameters(self):
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
        print("✅ Initialized experiment with parameters:")
        for k, v in new_params.items():
            print(f"   {k}: {v}")
        self.indicator_initialize.setStyleSheet(
            "background-color: grey; border: 1px solid black; border-radius: 5px;"
        )
        print("\n")
        print("Select an action. \n")


    def read_unprocessed_frontend(self):
        # Update indicator color
        self.indicator_read_unprocessed.setStyleSheet(
            "background-color: red; border: 1px solid black; border-radius: 5px;"
        )
        #Button logic
        self.read_unprocessed_btn.setEnabled(False)
        self.read_processed_btn.setEnabled(False)
        self.sweep_start_stop_btn.setEnabled(False)
        self.set_parameters_and_initialize_btn.setEnabled(False)
        self.is_process_running = True

        # --- Create a QThread and Worker ---
        self.thread = QThread(self)  # Store reference to avoid garbage collection
        self.worker = Worker(self.current_experiment, "read_unprocessed")
        self.worker.moveToThread(self.thread)

        # --- Connect signals and slots ---
        self.thread.started.connect(self.worker.run_snapshot)
        # Worker sends us status messages
        self.worker.updateStatus.connect(self.on_worker_status_update)
        # When finished, the worker signals us to stop the thread
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # --- Start the thread ---
        self.thread.start()

        # Reset indicator color once we know it's done:
        # Option 1: do it immediately, but that won't show "busy"
        # Option 2: connect it to self.worker.finished
        def reset_indicator():
            self.read_unprocessed_btn.setEnabled(True)
            self.read_processed_btn.setEnabled(True)
            self.sweep_start_stop_btn.setEnabled(True)
            self.set_parameters_and_initialize_btn.setEnabled(True)
            self.indicator_read_unprocessed.setStyleSheet(
                "background-color: grey; border: 1px solid black; border-radius: 5px;"
            )

            # Reactivate initialize only if settings were changed during the process
            if self.settings_changed:
                self.set_parameters_and_initialize_btn.setEnabled(True)

            self.is_process_running = False
        
        self.worker.finished.connect(reset_indicator)


    def read_processed_frontend(self):
        self.indicator_read_processed.setStyleSheet(
            "background-color: red; border: 1px solid black; border-radius: 5px;"
        )

        #Button logic
        self.read_unprocessed_btn.setEnabled(False)
        self.read_processed_btn.setEnabled(False)
        self.sweep_start_stop_btn.setEnabled(False)
        self.set_parameters_and_initialize_btn.setEnabled(False)
        self.is_process_running = True
        
        self.thread = QThread(self)
        self.worker = Worker(self.current_experiment, "read_processed")
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run_snapshot)
        self.worker.updateStatus.connect(self.on_worker_status_update)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

        def reset_indicator():
            self.read_unprocessed_btn.setEnabled(True)
            self.read_processed_btn.setEnabled(True)
            self.sweep_start_stop_btn.setEnabled(True)
            self.set_parameters_and_initialize_btn.setEnabled(True)
            self.indicator_read_processed.setStyleSheet(
                "background-color: grey; border: 1px solid black; border-radius: 5px;"
            )

            # Reactivate initialize only if settings were changed during the process
            if self.settings_changed:
                self.set_parameters_and_initialize_btn.setEnabled(True)

            self.is_process_running = False

        self.worker.finished.connect(reset_indicator)


    def toggle_start_stop_sweep_frontend(self):
        #Start the process
        if self.sweep_start_stop_btn.text() == "Start Sweep":
            #Button logic
            self.read_unprocessed_btn.setEnabled(False)
            self.read_processed_btn.setEnabled(False)
            self.set_parameters_and_initialize_btn.setEnabled(False)
            self.is_process_running = True
            
            # We want to start
            self.indicator_sweep.setStyleSheet("background-color: red; border: 1px solid black; border-radius: 5px;")
            self.sweep_start_stop_btn.setText("Stop Sweep")

            # Create QThread
            self.thread = QThread(self)
            # Create Worker, pass in experiment
            self.worker = Worker(self.current_experiment, "sweep")
            # Move worker to thread
            self.worker.moveToThread(self.thread)

            # Connect signals
            # When thread starts, call worker.run_sweep
            self.thread.started.connect(self.worker.run_sweep)
            # If the worker emits updateStatus, call on_worker_status_update
            self.worker.updateStatus.connect(self.on_worker_status_update)
            # Worker emits finished -> kill thread
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)

            # Optionally reset indicator color after finishing
            def reset_indicator():
                self.read_unprocessed_btn.setEnabled(True)
                self.read_processed_btn.setEnabled(True)
                self.set_parameters_and_initialize_btn.setEnabled(True)
                self.set_parameters_and_initialize_btn.setEnabled(True)
                self.indicator_read_unprocessed.setStyleSheet(
                    "background-color: grey; border: 1px solid black; border-radius: 5px;"
                )

                # Reactivate initialize only if settings were changed during the process
                if self.settings_changed:
                    self.set_parameters_and_initialize_btn.setEnabled(True)

                self.is_process_running = False

            self.worker.finished.connect(reset_indicator)

            # Start the thread
            self.thread.start()
            
#             # Start the plot update timer AFTER sweep starts
#             if not hasattr(self, 'plot_timer'):
#                 self.plot_timer = QTimer()
#                 self.plot_timer.timeout.connect(self.refresh_sweep_plot)

#             self.plot_timer.start(1000)  # Update every 1 second

        else:
            self.sweep_start_stop_btn.setText("Start Sweep")
            if hasattr(self, 'worker'):
                self.worker.stop_sweep()
            
                self.indicator_sweep.setStyleSheet("background-color: grey; border: 1px solid black; border-radius: 5px;")


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
        
#     @pyqtSlot()
#     def refresh_sweep_plot(self):
#         if self.current_experiment.sweep["expt"].runinfo.running:
#             self.current_experiment.update_sweep_plot()
#             print("Sweep is running — updating plot")
#         else:
#             print("Sweep not running — stopping timer")
#             self.plot_timer.stop()
#     def refresh_sweep_plot(self):
#         print("Timer fired")
#         expt = self.current_experiment.sweep.get('expt')
#         if expt and hasattr(expt, 'runinfo') and expt.runinfo.running:
#             print("Sweep is running — updating plot")
#             self.current_experiment.update_sweep_plot(expt)
#         else:
#             print("Sweep not running — stopping timer")
#             self.plot_timer.stop()
   
    def update_plot(self):
        """Slot to update the sweep plot when the experiment emits a signal."""
        if hasattr(self.current_experiment, 'sweep') and 'expt' in self.current_experiment.sweep:
            self.sweep_graph.ax.clear()
            try:
                colormesh = ps.plot2D(
                    self.current_experiment.sweep['expt'],
                    x_name='t',
                    transpose=1,
                    ax=self.sweep_graph.ax
                )
                self.sweep_graph.colorbar(colormesh, ax=self.sweep_graph.ax)
                self.canvas.draw()
            except Exception as e:
                print(f"Live plot update error: {e}")
            
    def save_current_graph(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Graph As", "", "PNG Files (*.png);;All Files (*)", options=options)
        if file_path:
            self.current_experiment.graph.figure.savefig(file_path)
            self.last_saved_graph_path = file_path
            self.last_saved_path_label.setText(f"Last saved to: {file_path}")

    def open_saved_graph_folder(self, event):
        if self.last_saved_graph_path:
            folder = os.path.dirname(self.last_saved_graph_path)
            os.system(f'open "{folder}"')  # 'xdg-open' for Linux. Use `open` for macOS, or `start` for Windows.


def main():
    app = QApplication(sys.argv)
    ex = ExperimentUI()
    ex.showFullScreen()
    sys.exit(app.exec_())

    
if __name__ == "__main__":
    main()