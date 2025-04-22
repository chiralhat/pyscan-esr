# import numpy as np
# from PyQt5.QtWidgets import QApplication
# from pulsesweep_scripts import *  # Your experimental logic
# import pyscan as ps

# class PulseSweepExperiment:

#     def __init__(self, canvas_widget):
#         """
#         Initialize with a reference to the CanvasWidget.
#         """
#         self.canvas_widget = canvas_widget
#         self.time_data = []
#         self.x_data = []

#     def init_experiment(self, devices, parameters, sweep, soc):
#         """
#         Initialize experiment parameters and devices.
#         """
#         parameters['pulses'] = 0
#         parameters['pulse1_2'] = parameters['pulse1_1']
#         parameters['pi2_phase'] = 0
#         parameters['pi_phase'] = 90
#         parameters['delay'] = 300
#         parameters['cpmg_phase'] = 0
#         channel = 1 if parameters['loopback'] else 0
#         parameters['res_ch'] = channel
#         parameters['ro_chs'] = [channel]
#         parameters['nutation_delay'] = 5000
#         parameters['nutation_length'] = 0
#         parameters['reps'] = 1
#         parameters['sweep2'] = 0

#         if parameters['use_psu']:
#             devices.psu.set_magnet(parameters)

#         setup_experiment(parameters, devices, sweep, soc)

#     def get_layout(self):
#         """
#         Optionally return a layout if this is being embedded.
#         """
#         return self.canvas_widget.layout()