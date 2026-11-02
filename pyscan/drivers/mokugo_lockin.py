# -*- coding: utf-8 -*-
"""
Created on June 30 2025

@author: Charles Collett
"""

from moku.instruments import LockInAmp
from .mokugo import MokuGo
import numpy as np
from time import sleep

maxF = 800e3
bitstream = "moku_switch.tar"
clk_freq = 31.25e-3
tstep = 1/clk_freq

address = {'Cryostat': 'mokugo-005419.hamilton.edu',
             'Bench': 'mokugo-005059.hamilton.edu'}

class MokuGoLI(MokuGo):
    '''
    Class to control Moku:Go AWG and programmable power supply
    '''
    def __init__(self, moku='Cryostat', laser_port=3):
        self.instrument = LockInAmp(address[moku], force_connect=True)
        
        self.instrument.set_demodulation('Internal', frequency=1e6, phase=0)
        self.instrument.set_filter(1e3, slope='Slope6dB')
        self.instrument.set_outputs('None', 'Aux')
        self.instrument.set_monitor(1, 'MainOutput')
        self.instrument.set_gain(10, 0)
        self.instrument.set_aux_output(1e6, 6.33)
        self.instrument.set_timebase(5e-3, 10e-3)
        self.psu_setup(moku, laser_port)
    
    def read_lin(self):
        data = self.instrument.get_data()
        return np.mean(data['ch1'])