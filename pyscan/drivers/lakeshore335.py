# -*- coding: utf-8 -*-
"""
Created on March 2 2021

@author: Charles Collett
"""


from .instrument_driver import InstrumentDriver
from lakeshore import Model335
from time import sleep
import numpy as np


class Lakeshore335():
    '''
    Class to control Lakeshore 335 Temperature Controller

    '''

    def __init__(self, baud=57600):

        self.tcon = Model335(baud)
        self.query = self.tcon.query
        self.write = self.tcon.command
        # self.setpoint(self.get_temp(), track=0)
        self.ramp()
        self.output()
        self.heater('Read')

    
    def get_temp(self):
        tstr = self.query('KRDG?', check_errors=False)
        return float(tstr[1:])
    
    
    def setpoint(self, value=0, track=1, output=1):
        if value!=0:
            self.write('SETP {0},{1}'.format(output, value))
            sleep(.005)
        if track:
            self.output()
        self.track = track
        self.tset = float(self.query('SETP?', check_errors=False))
        return self.tset
    
    
    def ramp(self, rate=10, output=1, on=1):
        if rate!=0:
            self.write('RAMP {0},{1},{2}'.format(output, on, rate))
            sleep(.005)
        self.trate = self.query('RAMP?', check_errors=False) if on else 0
        return self.trate
    
    
    def output(self, mode=1, outp=1, inp=1, powerup=0):
        if mode!='Read':
            self.write('OUTMODE {0},{1},{2},{3}'.format(outp, mode, inp, powerup))
            sleep(.005)
        self.mode = int(self.query('OUTMODE?', check_errors=False)[:1])
        return self.mode
    
    
    def heater(self, hrange=3, output=1):
        if hrange!='Read':
            self.write('RANGE {0},{1}'.format(output, hrange))
            sleep(.005)
        self.hran = int(self.query('RANGE?', check_errors=False))
        return self.hran