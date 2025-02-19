import sys
import pickle
from pathlib import Path

# Bring in your existing logic:
import pulsesweep_scripts
import pulsesweep_gui
import spinecho_gui
import spinecho_scripts
import pyscan as ps
import rfsoc2

import matplotlib.pyplot as plt
from IPython.display import display, clear_output

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QToolBar, QComboBox, QPushButton,
    QLabel, QVBoxLayout, QHBoxLayout, QSplitter, QScrollArea, QToolBox,
    QFrame, QGroupBox, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QPlainTextEdit
)
from PyQt5.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Consolidated Pulsed/Spin Echo UI")

        # ------------------------------------------------------
        # 1) Persistent top toolbar
        # ------------------------------------------------------
        toolbar = self.addToolBar("Top Toolbar")
        toolbar.setMovable(False)

        self.comboExperimentType = QComboBox()
        self.comboExperimentType.addItems(["Pulsed Frequency Sweep", "Spin Echo"])
        toolbar.addWidget(QLabel("Experiment Type: "))
        toolbar.addWidget(self.comboExperimentType)

        self.btnInitialize = QPushButton("Initialize")
        toolbar.addWidget(self.btnInitialize)

        self.btnStartSweep = QPushButton("Start Sweep")
        toolbar.addWidget(self.btnStartSweep)

        self.btnStopSweep = QPushButton("Stop Sweep")
        toolbar.addWidget(self.btnStopSweep)

        self.btnRead = QPushButton("Read")
        toolbar.addWidget(self.btnRead)

        self.btnSingleShot = QPushButton("Single Run (No Save)")
        toolbar.addWidget(self.btnSingleShot)

        toolbar.addSeparator()

        self.btnSaveParams = QPushButton("Save Params")
        toolbar.addWidget(self.btnSaveParams)

        self.btnLoadParams = QPushButton("Load Params")
        toolbar.addWidget(self.btnLoadParams)

        # Hook up signals
        self.comboExperimentType.currentIndexChanged.connect(self.onExperimentTypeChanged)
        self.btnInitialize.clicked.connect(self.onInitialize)
        self.btnStartSweep.clicked.connect(self.onStartSweep)
        self.btnStopSweep.clicked.connect(self.onStopSweep)
        self.btnRead.clicked.connect(self.onRead)
        self.btnSingleShot.clicked.connect(self.onSingleShot)
        self.btnSaveParams.clicked.connect(self.onSaveParams)
        self.btnLoadParams.clicked.connect(self.onLoadParams)

        # ------------------------------------------------------
        # 2) Main Split layout
        # ------------------------------------------------------
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        mainLayout = QHBoxLayout(centralWidget)

        self.hSplitter = QSplitter(Qt.Orientation.Horizontal)
        mainLayout.addWidget(self.hSplitter)

        # 2a) Left side (scroll area) with QToolBox
        self.leftScroll = QScrollArea()
        self.leftScroll.setWidgetResizable(True)
        self.hSplitter.addWidget(self.leftScroll)

        self.leftContainer = QWidget()
        self.leftLayout = QVBoxLayout(self.leftContainer)

        self.toolBox = QToolBox()
        self.leftLayout.addWidget(self.toolBox)

        # -- Build Pulsed Frequency Sweep UI pages --
        self.widgetPulsed = QWidget()
        self.widgetPulsedLayout = QVBoxLayout(self.widgetPulsed)

        # Pulsed: Main Settings
        pulsedMainGroup = QGroupBox("Main Settings")
        pulsedMainForm = QFormLayout(pulsedMainGroup)

        self.pulsed_freq = QDoubleSpinBox()
        self.pulsed_freq.setRange(0, 20000)
        pulsedMainForm.addRow("Frequency (MHz):", self.pulsed_freq)

        self.pulsed_ave = QSpinBox()
        self.pulsed_ave.setRange(1, 999999)
        pulsedMainForm.addRow("Ave:", self.pulsed_ave)

        self.pulsed_dir = QLineEdit()
        pulsedMainForm.addRow("Directory:", self.pulsed_dir)

        self.pulsed_fname = QLineEdit()
        pulsedMainForm.addRow("File Name:", self.pulsed_fname)

        self.pulsed_expt = QComboBox()
        self.pulsed_expt.addItems(["Freq Sweep", "Field Sweep"])
        pulsedMainForm.addRow("Experiment:", self.pulsed_expt)

        self.pulsed_sweep_start = QDoubleSpinBox()
        pulsedMainForm.addRow("Sweep Start:", self.pulsed_sweep_start)
        self.pulsed_sweep_end = QDoubleSpinBox()
        pulsedMainForm.addRow("Sweep End:", self.pulsed_sweep_end)
        self.pulsed_sweep_step = QDoubleSpinBox()
        pulsedMainForm.addRow("Sweep Step:", self.pulsed_sweep_step)

        self.widgetPulsedLayout.addWidget(pulsedMainGroup)

        # Pulsed: Readout Settings
        pulsedReadoutGroup = QGroupBox("Readout Settings")
        pulsedReadoutForm = QFormLayout(pulsedReadoutGroup)

        self.pulsed_timeOffset = QDoubleSpinBox()
        pulsedReadoutForm.addRow("Time Offset (us):", self.pulsed_timeOffset)

        self.pulsed_readLen = QDoubleSpinBox()
        pulsedReadoutForm.addRow("Readout Length (us):", self.pulsed_readLen)

        self.pulsed_loopback = QCheckBox()
        pulsedReadoutForm.addRow("Loopback:", self.pulsed_loopback)

        self.widgetPulsedLayout.addWidget(pulsedReadoutGroup)

        # Pulsed: Uncommon
        pulsedUncommonGroup = QGroupBox("Uncommon Settings")
        pulsedUncommonForm = QFormLayout(pulsedUncommonGroup)

        self.pulsed_repTime = QDoubleSpinBox()
        pulsedUncommonForm.addRow("Repetition Time (us):", self.pulsed_repTime)

        self.pulsed_ch1_90Pulse = QDoubleSpinBox()
        pulsedUncommonForm.addRow("Ch1 90 Pulse (ns):", self.pulsed_ch1_90Pulse)

        self.pulsed_field = QDoubleSpinBox()
        pulsedUncommonForm.addRow("Magnetic Field (G):", self.pulsed_field)

        self.pulsed_scale = QDoubleSpinBox()
        pulsedUncommonForm.addRow("Magnet Scale (G/A):", self.pulsed_scale)

        self.pulsed_currentLimit = QDoubleSpinBox()
        pulsedUncommonForm.addRow("Current Limit (A):", self.pulsed_currentLimit)

        self.pulsed_reps = QSpinBox()
        pulsedUncommonForm.addRow("Reps:", self.pulsed_reps)

        self.pulsed_waitTime = QDoubleSpinBox()
        pulsedUncommonForm.addRow("Wait Time (s):", self.pulsed_waitTime)

        self.pulsed_integralOnly = QCheckBox()
        pulsedUncommonForm.addRow("Integral only:", self.pulsed_integralOnly)

        self.pulsed_initOnRead = QCheckBox()
        pulsedUncommonForm.addRow("Initialize on read:", self.pulsed_initOnRead)

        self.pulsed_turnOffAfter = QCheckBox()
        pulsedUncommonForm.addRow("Turn off after sweep:", self.pulsed_turnOffAfter)

        self.widgetPulsedLayout.addWidget(pulsedUncommonGroup)

        # Pulsed: Utility
        pulsedUtilityGroup = QGroupBox("Utility Settings")
        pulsedUtilityForm = QFormLayout(pulsedUtilityGroup)

        self.pulsed_psuAddr = QLineEdit()
        pulsedUtilityForm.addRow("PSU Address:", self.pulsed_psuAddr)

        self.pulsed_usePSU = QCheckBox()
        pulsedUtilityForm.addRow("Use PSU:", self.pulsed_usePSU)

        self.pulsed_useLS = QCheckBox()
        pulsedUtilityForm.addRow("Use Lakeshore:", self.pulsed_useLS)

        self.widgetPulsedLayout.addWidget(pulsedUtilityGroup)

        self.widgetPulsedLayout.addStretch(1)
        self.toolBox.addItem(self.widgetPulsed, "Pulsed Freq Sweep Settings")

        # -- Build Spin Echo UI pages --
        self.widgetSpinEcho = QWidget()
        self.widgetSELayout = QVBoxLayout(self.widgetSpinEcho)

        # Spin Echo: Main
        seMainGroup = QGroupBox("Main Settings")
        seMainForm = QFormLayout(seMainGroup)

        self.se_ch1Freq = QDoubleSpinBox()
        seMainForm.addRow("Ch1 Freq (MHz):", self.se_ch1Freq)

        self.se_gain = QSpinBox()
        seMainForm.addRow("Gain:", self.se_gain)

        self.se_repTime = QDoubleSpinBox()
        seMainForm.addRow("Repetition Time (us):", self.se_repTime)

        self.se_ave = QSpinBox()
        seMainForm.addRow("Ave:", self.se_ave)

        self.se_dir = QLineEdit()
        seMainForm.addRow("Directory:", self.se_dir)

        self.se_fname = QLineEdit()
        seMainForm.addRow("File Name:", self.se_fname)

        self.se_reps = QSpinBox()
        seMainForm.addRow("Reps:", self.se_reps)

        self.se_expt = QComboBox()
        self.se_expt.addItems(["Hahn Echo", "CPMG"])
        seMainForm.addRow("Experiment:", self.se_expt)

        self.se_sweep_start = QDoubleSpinBox()
        seMainForm.addRow("Sweep Start:", self.se_sweep_start)
        self.se_sweep_end = QDoubleSpinBox()
        seMainForm.addRow("Sweep End:", self.se_sweep_end)
        self.se_sweep_step = QDoubleSpinBox()
        seMainForm.addRow("Sweep Step:", self.se_sweep_step)

        self.widgetSELayout.addWidget(seMainGroup)

        # Spin Echo: Pulse
        sePulseGroup = QGroupBox("Pulse Settings")
        sePulseForm = QFormLayout(sePulseGroup)

        self.se_ch1Delay = QDoubleSpinBox()
        sePulseForm.addRow("Ch1 Delay (ns):", self.se_ch1Delay)

        self.se_ch1_90Pulse = QDoubleSpinBox()
        sePulseForm.addRow("Ch1 90 Pulse (ns):", self.se_ch1_90Pulse)

        self.se_nutDelay = QDoubleSpinBox()
        sePulseForm.addRow("Nutation Delay (ns):", self.se_nutDelay)

        self.se_nutPulse = QDoubleSpinBox()
        sePulseForm.addRow("Nutation Pulse Width (ns):", self.se_nutPulse)

        self.widgetSELayout.addWidget(sePulseGroup)

        # Spin Echo: Second Sweep
        seSecondSweepGroup = QGroupBox("Second Sweep Settings")
        seSecondSweepForm = QFormLayout(seSecondSweepGroup)

        self.se_secondSweep = QCheckBox()
        seSecondSweepForm.addRow("Second sweep?", self.se_secondSweep)

        self.se_expt2 = QComboBox()
        self.se_expt2.addItems(["None", "CPMG", "Hahn Echo"])
        seSecondSweepForm.addRow("Experiment 2:", self.se_expt2)

        self.se_sweep2_start = QDoubleSpinBox()
        seSecondSweepForm.addRow("Sweep2 Start:", self.se_sweep2_start)
        self.se_sweep2_end = QDoubleSpinBox()
        seSecondSweepForm.addRow("Sweep2 End:", self.se_sweep2_end)
        self.se_sweep2_step = QDoubleSpinBox()
        seSecondSweepForm.addRow("Sweep2 Step:", self.se_sweep2_step)

        self.widgetSELayout.addWidget(seSecondSweepGroup)

        # Spin Echo: Readout
        seReadoutGroup = QGroupBox("Readout Settings")
        seReadoutForm = QFormLayout(seReadoutGroup)

        self.se_timeOffset = QDoubleSpinBox()
        seReadoutForm.addRow("Time Offset (us):", self.se_timeOffset)

        self.se_readLen = QDoubleSpinBox()
        seReadoutForm.addRow("Readout Length (us):", self.se_readLen)

        self.se_loopback = QCheckBox()
        seReadoutForm.addRow("Loopback:", self.se_loopback)

        self.widgetSELayout.addWidget(seReadoutGroup)

        # Spin Echo: Uncommon
        seUncommonGroup = QGroupBox("Uncommon Settings")
        seUncommonForm = QFormLayout(seUncommonGroup)

        self.se_ch1_180mult = QDoubleSpinBox()
        seUncommonForm.addRow("Ch1 180 Pulse Mult:", self.se_ch1_180mult)

        self.se_field = QDoubleSpinBox()
        seUncommonForm.addRow("Magnetic Field (G):", self.se_field)

        self.se_scale = QDoubleSpinBox()
        seUncommonForm.addRow("Magnet Scale (G/A):", self.se_scale)

        self.se_currentLimit = QDoubleSpinBox()
        seUncommonForm.addRow("Current Limit (A):", self.se_currentLimit)

        self.se_waitTime = QDoubleSpinBox()
        seUncommonForm.addRow("Wait Time (s):", self.se_waitTime)

        self.se_integralOnly = QCheckBox()
        seUncommonForm.addRow("Integral only:", self.se_integralOnly)

        self.se_initOnRead = QCheckBox()
        seUncommonForm.addRow("Initialize on read:", self.se_initOnRead)

        self.se_turnOffAfter = QCheckBox()
        seUncommonForm.addRow("Turn off after sweep:", self.se_turnOffAfter)

        self.widgetSELayout.addWidget(seUncommonGroup)

        # Spin Echo: Utility
        seUtilityGroup = QGroupBox("Utility Settings")
        seUtilityForm = QFormLayout(seUtilityGroup)

        self.se_psuAddr = QLineEdit()
        seUtilityForm.addRow("PSU Address:", self.se_psuAddr)

        self.se_usePSU = QCheckBox()
        seUtilityForm.addRow("Use PSU:", self.se_usePSU)

        self.se_useLS = QCheckBox()
        seUtilityForm.addRow("Use Lakeshore:", self.se_useLS)

        self.widgetSELayout.addWidget(seUtilityGroup)

        self.widgetSELayout.addStretch(1)
        self.toolBox.addItem(self.widgetSpinEcho, "Spin Echo Settings")

        self.leftScroll.setWidget(self.leftContainer)

        # ------------------------------------------------------
        # 3) Right side: Plots/Indicators/Log
        # ------------------------------------------------------
        self.rightSplitter = QSplitter(Qt.Orientation.Vertical)
        self.hSplitter.addWidget(self.rightSplitter)

        # top area - Plots
        self.plotArea = QWidget()
        self.plotLayout = QVBoxLayout(self.plotArea)
        self.plotLabel = QLabel("Plots or Live Graphs here.")
        self.plotLayout.addWidget(self.plotLabel)
        self.rightSplitter.addWidget(self.plotArea)

        # bottom area - indicators + error log
        self.indicatorArea = QWidget()
        self.indicatorLayout = QVBoxLayout(self.indicatorArea)

        indicatorsGroup = QGroupBox("Indicators")
        indicatorsForm = QFormLayout(indicatorsGroup)

        self.lbl_outfile = QLabel("(none)")
        indicatorsForm.addRow("Filename:", self.lbl_outfile)

        self.lbl_subtime = QLabel("0.0")
        indicatorsForm.addRow("Cycle Time:", self.lbl_subtime)

        self.lbl_field = QLabel("??? G")
        indicatorsForm.addRow("Mag. Field:", self.lbl_field)

        self.lbl_fitParams = QLabel("N/A")
        indicatorsForm.addRow("Final Fit Params:", self.lbl_fitParams)

        self.indicatorLayout.addWidget(indicatorsGroup)

        self.errorLog = QPlainTextEdit()
        self.errorLog.setPlainText("Error Log:\n")
        self.indicatorLayout.addWidget(self.errorLog)

        self.rightSplitter.addWidget(self.indicatorArea)

        # Initialize data objects
        self.devices = ps.ItemAttribute()  # store scope, psu, etc.
        self.sig = ps.ItemAttribute()      # store measurement data
        self.sweep = {}                    # dictionary with 'expt', 'runinfo', etc.
        self.soc = None                   # can store your rfsoc2 object if needed

        # set default indexes, etc.
        self.hSplitter.setStretchFactor(0, 1)
        self.hSplitter.setStretchFactor(1, 2)
        self.resize(1300, 800)

    # ----------------------------------------------------------------
    # Parameter Collections
    # ----------------------------------------------------------------
    def collectPulsedParams(self):
        """Return a dict of parameters from the Pulsed Frequency Sweep controls 
           that pulsesweep_scripts expects.

           ### THESE ARE THE PARAMS THAT SHOULD BE THERE????
           These are all the controls to add for this GUI
pscont_keys = {'devices': [['psu_address', 'use_psu', 'use_temp']],
                'rfsoc': [['freq', 'gain', 'period', 'loopback'],
                            ['pulse1_1','soft_avgs', 'h_offset', 'readout_length']],
             'psu': [['field', 'gauss_amps', 'current_limit']],
             'save': [['save_dir', 'file_name']],
             'measure': [['ave_reps', 'psexpt', 'wait'],
                         ['sweep_start', 'sweep_end', 'sweep_step'],
                         ['integrate', 'init', 'turn_off']],
             }
        """
        p = {}
        p["freq"] = self.pulsed_freq.value()
        p["soft_avgs"] = self.pulsed_ave.value()
        p["save_dir"] = self.pulsed_dir.text()
        p["file_name"] = self.pulsed_fname.text()
        p["psexpt"] = self.pulsed_expt.currentText()  # e.g. 'Freq Sweep' or 'Field Sweep'
        p["sweep_start"] = self.pulsed_sweep_start.value()
        p["sweep_end"] = self.pulsed_sweep_end.value()
        p["sweep_step"] = self.pulsed_sweep_step.value()

        p["h_offset"] = self.pulsed_timeOffset.value()
        p["readout_length"] = self.pulsed_readLen.value()
        p["loopback"] = self.pulsed_loopback.isChecked()

        p["period"] = self.pulsed_repTime.value()
        p["pulse1_1"] = self.pulsed_ch1_90Pulse.value()
        p["field"] = self.pulsed_field.value()
        p["gauss_amps"] = self.pulsed_scale.value()
        p["current_limit"] = self.pulsed_currentLimit.value()
        p["ave_reps"] = self.pulsed_reps.value()
        p["wait"] = self.pulsed_waitTime.value()
        p["integrate"] = self.pulsed_integralOnly.isChecked()
        p["init"] = self.pulsed_initOnRead.isChecked()
        p["turn_off"] = self.pulsed_turnOffAfter.isChecked()

        p["psu_address"] = self.pulsed_psuAddr.text()
        p["use_psu"] = self.pulsed_usePSU.isChecked()
        p["use_temp"] = self.pulsed_useLS.isChecked()

        return p

    def collectSpinEchoParams(self):
        """Return a dict of parameters from the Spin Echo controls 
           that spinecho_scripts expects.
        """
        p = {}
        p["freq"] = self.se_ch1Freq.value()
        p["gain"] = self.se_gain.value()
        p["period"] = self.se_repTime.value()
        p["soft_avgs"] = self.se_ave.value()
        p["save_dir"] = self.se_dir.text()
        p["file_name"] = self.se_fname.text()
        p["reps"] = self.se_reps.value()
        p["expt"] = self.se_expt.currentText()  # e.g. 'Hahn Echo', 'CPMG'
        p["sweep_start"] = self.se_sweep_start.value()
        p["sweep_end"] = self.se_sweep_end.value()
        p["sweep_step"] = self.se_sweep_step.value()

        p["delay"] = self.se_ch1Delay.value()
        p["pulse1_1"] = self.se_ch1_90Pulse.value()
        p["nutation_delay"] = self.se_nutDelay.value()
        p["nutation_length"] = self.se_nutPulse.value()

        p["sweep2"] = self.se_secondSweep.isChecked()
        p["expt2"] = self.se_expt2.currentText()
        p["sweep2_start"] = self.se_sweep2_start.value()
        p["sweep2_end"] = self.se_sweep2_end.value()
        p["sweep2_step"] = self.se_sweep2_step.value()

        p["h_offset"] = self.se_timeOffset.value()
        p["readout_length"] = self.se_readLen.value()
        p["loopback"] = self.se_loopback.isChecked()

        p["mult1"] = self.se_ch1_180mult.value()
        p["field"] = self.se_field.value()
        p["gauss_amps"] = self.se_scale.value()
        p["current_limit"] = self.se_currentLimit.value()
        p["wait"] = self.se_waitTime.value()
        p["integrate"] = self.se_integralOnly.isChecked()
        p["init"] = self.se_initOnRead.isChecked()
        p["turn_off"] = self.se_turnOffAfter.isChecked()

        p["psu_address"] = self.se_psuAddr.text()
        p["use_psu"] = self.se_usePSU.isChecked()
        p["use_temp"] = self.se_useLS.isChecked()

        return p

    # ----------------------------------------------------------------
    # Utility: Save/Load
    # ----------------------------------------------------------------
    def onSaveParams(self):
        experiment = self.comboExperimentType.currentText()
        if experiment == "Pulsed Frequency Sweep":
            params = self.collectPulsedParams()
            default_file = "ps_defaults.pkl"
        else:
            params = self.collectSpinEchoParams()
            default_file = "se_defaults.pkl"

        with open(default_file, "wb") as f:
            pickle.dump(params, f)
        self.errorLog.appendPlainText(f"Parameters saved to {default_file}")

    def onLoadParams(self):
        experiment = self.comboExperimentType.currentText()
        if experiment == "Pulsed Frequency Sweep":
            default_file = "ps_defaults.pkl"
        else:
            default_file = "se_defaults.pkl"

        if Path(default_file).exists():
            with open(default_file, "rb") as f:
                params = pickle.load(f)
            # apply them to the GUI
            self.applyParameters(params, experiment)
            self.errorLog.appendPlainText(f"Parameters loaded from {default_file}")
        else:
            self.errorLog.appendPlainText(f"No {default_file} file found.")

    def applyParameters(self, p, experiment):
        """
        Populate the GUI fields from a dictionary of parameters.
        """
        if experiment == "Pulsed Frequency Sweep":
            self.pulsed_freq.setValue(p.get("freq", 100.0))
            self.pulsed_ave.setValue(p.get("soft_avgs", 1))
            self.pulsed_dir.setText(p.get("save_dir", ""))
            self.pulsed_fname.setText(p.get("file_name", ""))
            self.pulsed_expt.setCurrentText(p.get("psexpt", "Freq Sweep"))
            self.pulsed_sweep_start.setValue(p.get("sweep_start", 0.0))
            self.pulsed_sweep_end.setValue(p.get("sweep_end", 10.0))
            self.pulsed_sweep_step.setValue(p.get("sweep_step", 1.0))

            self.pulsed_timeOffset.setValue(p.get("h_offset", 0.0))
            self.pulsed_readLen.setValue(p.get("readout_length", 0.5))
            self.pulsed_loopback.setChecked(p.get("loopback", False))

            self.pulsed_repTime.setValue(p.get("period", 100.0))
            self.pulsed_ch1_90Pulse.setValue(p.get("pulse1_1", 100.0))
            self.pulsed_field.setValue(p.get("field", 0.0))
            self.pulsed_scale.setValue(p.get("gauss_amps", 1.0))
            self.pulsed_currentLimit.setValue(p.get("current_limit", 1.0))
            self.pulsed_reps.setValue(p.get("ave_reps", 1))
            self.pulsed_waitTime.setValue(p.get("wait", 0.0))
            self.pulsed_integralOnly.setChecked(p.get("integrate", False))
            self.pulsed_initOnRead.setChecked(p.get("init", False))
            self.pulsed_turnOffAfter.setChecked(p.get("turn_off", False))

            self.pulsed_psuAddr.setText(p.get("psu_address", ""))
            self.pulsed_usePSU.setChecked(p.get("use_psu", False))
            self.pulsed_useLS.setChecked(p.get("use_temp", False))

        else:
            self.se_ch1Freq.setValue(p.get("freq", 100.0))
            self.se_gain.setValue(p.get("gain", 10000))
            self.se_repTime.setValue(p.get("period", 500.0))
            self.se_ave.setValue(p.get("soft_avgs", 1))
            self.se_dir.setText(p.get("save_dir", ""))
            self.se_fname.setText(p.get("file_name", ""))
            self.se_reps.setValue(p.get("reps", 1))
            self.se_expt.setCurrentText(p.get("expt", "Hahn Echo"))
            self.se_sweep_start.setValue(p.get("sweep_start", 0.0))
            self.se_sweep_end.setValue(p.get("sweep_end", 10.0))
            self.se_sweep_step.setValue(p.get("sweep_step", 1.0))

            self.se_ch1Delay.setValue(p.get("delay", 300.0))
            self.se_ch1_90Pulse.setValue(p.get("pulse1_1", 400.0))
            self.se_nutDelay.setValue(p.get("nutation_delay", 5000.0))
            self.se_nutPulse.setValue(p.get("nutation_length", 0.0))

            self.se_secondSweep.setChecked(p.get("sweep2", False))
            self.se_expt2.setCurrentText(p.get("expt2", "None"))
            self.se_sweep2_start.setValue(p.get("sweep2_start", 0.0))
            self.se_sweep2_end.setValue(p.get("sweep2_end", 0.0))
            self.se_sweep2_step.setValue(p.get("sweep2_step", 0.0))

            self.se_timeOffset.setValue(p.get("h_offset", 0.0))
            self.se_readLen.setValue(p.get("readout_length", 0.5))
            self.se_loopback.setChecked(p.get("loopback", False))

            self.se_ch1_180mult.setValue(p.get("mult1", 2.0))
            self.se_field.setValue(p.get("field", 0.0))
            self.se_scale.setValue(p.get("gauss_amps", 1.0))
            self.se_currentLimit.setValue(p.get("current_limit", 1.0))
            self.se_waitTime.setValue(p.get("wait", 0.0))
            self.se_integralOnly.setChecked(p.get("integrate", False))
            self.se_initOnRead.setChecked(p.get("init", False))
            self.se_turnOffAfter.setChecked(p.get("turn_off", False))

            self.se_psuAddr.setText(p.get("psu_address", ""))
            self.se_usePSU.setChecked(p.get("use_psu", False))
            self.se_useLS.setChecked(p.get("use_temp", False))

    # ----------------------------------------------------------------
    # Actions
    # ----------------------------------------------------------------
    def onExperimentTypeChanged(self, idx):
        """
        Switch which page is visible in the QToolBox.
        """
        self.toolBox.setCurrentIndex(idx)

    def onInitialize(self):
        """
        Call pulsesweep_scripts.init_experiment or spinecho_scripts.init_experiment
        with the user's parameters.
        """
        experiment = self.comboExperimentType.currentText()
        if experiment == "Pulsed Frequency Sweep":
            p = self.collectPulsedParams()
            pulsesweep_scripts.init_experiment(self.devices, p, self.sweep, self.soc)
            self.errorLog.appendPlainText("Initialized Pulsed Frequency Sweep.")
        else:
            p = self.collectSpinEchoParams()
            spinecho_scripts.init_experiment(self.devices, p, self.sweep, self.soc)
            self.errorLog.appendPlainText("Initialized Spin Echo.")

    def onStartSweep(self):
        """
        Setup the experiment + run_sweep.
        """
        experiment = self.comboExperimentType.currentText()
        if experiment == "Pulsed Frequency Sweep":
            p = self.collectPulsedParams()
            # pulsesweep_scripts.setup_experiment configures the RunInfo, etc.
            pulsesweep_scripts.setup_experiment(p, self.devices, self.sweep, self.soc)

            # Now run it
            ps.run_sweep(self.sweep, p)
            self.errorLog.appendPlainText("Pulsed Frequency Sweep started.")
        else:
            p = self.collectSpinEchoParams()
            spinecho_scripts.setup_experiment(p, self.devices, self.sweep, self.soc)
            ps.run_sweep(self.sweep, p)
            self.errorLog.appendPlainText("Spin Echo sweep started.")

        # If you want to track the "outfile" or "subtime" in the indicators:
        if "outfile" in p:
            self.lbl_outfile.setText(str(p["outfile"]))
        if "subtime" in p:
            self.lbl_subtime.setText(f"{p['subtime']:.4f}")

    def onStopSweep(self):
        """
        Stop a currently running sweep (if any).
        """
        if "expt" in self.sweep:
            self.sweep["expt"].runinfo.running = False
            self.errorLog.appendPlainText("Sweep stopped.")

    def onRead(self):
        """
        Single reading from the scope/FPGA.
        """
        experiment = self.comboExperimentType.currentText()
        if experiment == "Pulsed Frequency Sweep":
            p = self.collectPulsedParams()
            pulsesweep_gui.read(self.sig, p, self.soc, None, None)
            self.errorLog.appendPlainText("Pulsed read performed.")
        else:
            p = self.collectSpinEchoParams()
            spinecho_gui.read(self.sig, p, self.soc, None, None)
            self.errorLog.appendPlainText("Spin Echo read performed.")

        # Potentially display new data in the plot area or update indicators

    def onSingleShot(self):
        """
        Single shot measurement (no saving).
        """
        experiment = self.comboExperimentType.currentText()
        if experiment == "Pulsed Frequency Sweep":
            p = self.collectPulsedParams()
            pulsesweep_gui.single_shot(self.sig, p, self.soc, None, None)
            self.errorLog.appendPlainText("Pulsed single-shot run.")
        else:
            p = self.collectSpinEchoParams()
            pulsesweep_gui.single_shot(self.sig, p, self.soc, None, None)
            self.errorLog.appendPlainText("Spin Echo single-shot run.")

        # If you want to update indicators or show data, do it here.
        # Example: self.plotLabel.setText(f"I: {self.sig.i}, Q: {self.sig.q}")

        # If final fit parameters are available after single shot or after sweep:
        # self.lbl_fitParams.setText("some fit results")




def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
