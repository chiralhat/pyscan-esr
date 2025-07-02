# -*- coding: utf-8 -*-
"""
Created on June 30 2025

@author: Charles Collett
"""


from moku.instruments import ArbitraryWaveformGenerator
import numpy as np
from time import sleep


class MokuGo():
    '''
    Class to control Moku:Go AWG and programmable power supply
    '''
    def __init__(self, address='mokugo-005419.hamilton.edu'):
        self.instrument = ArbitraryWaveformGenerator(address, force_connect=True)
        self.instrument.set_power_supply(id=3, enable=True, voltage=5, current=0.15)
        self.instrument.set_power_supply(id=2, enable=True, voltage=0, current=0.15)
        self.instrument.set_power_supply(id=1, enable=False, voltage=0, current=0.15)
#        self.instrument.enableOutput(False)
        self._gauss = 278
        self.c_limit = 3.5
        self.ramp = 50


    def close(self):
        pass
    
    
    def __getitem__(cls, x):
        return getattr(cls, x)
    
    
    def __setitem__(cls, x, val):
        return setattr(cls, x, val)
    
    
    def field_ramp(self, target):
        current_field = self.field
        target = float(target)
        step = self.gauss*0.001
        rate = self.ramp
        assert rate>0, f'Ramp rate needs to be a positive integer, rate: {rate}'
        while np.abs(current_field-target)>2*step:
            delta = target-current_field
            if delta>rate:
                delta = rate
            elif delta<-rate:
                delta = -rate
            self.v2 = (current_field+delta)/self.gauss
            sleep(1)
            current_field = self.field


    @property
    def v1(self):
        return self.instrument.get_power_supply(1)['actual_voltage']

    @v1.setter
    def v1(self, value):
        self.instrument.set_power_supply(1, voltage=value)


    @property
    def v2(self):
        return self.instrument.get_power_supply(2)['actual_voltage']

    @v2.setter
    def v2(self, value):
        assert value<self.c_limit, f'Current exceeds limit, limit: {self.c_limit}, current: {value}'
        voltage = 3.5 if value>self.c_limit else value
        self.instrument.set_power_supply(2, voltage=value)


    @property
    def c1(self):
        return self.instrument.get_power_supply(1)['actual_current']


    @property
    def c2(self):
        return self.instrument.get_power_supply(2)['actual_current']

        
    @property
    def gauss(self):
        return self._gauss
    
    @gauss.setter
    def gauss(self, value):
        self._gauss = value
        
        
    @property
    def field(self):
        return self.v2*self.gauss
    
    @field.setter
    def field(self, value):
        if self.ramp:
            self.field_ramp(value)
        else:
            self.v2 = value/self.gauss
        
        
    @property
    def current_limit(self):
        return not self.c_limit
    
    @current_limit.setter
    def current_limit(self, limit):
        self.c_limit = limit
        
        
    def set_magnet(self, p):
        self.gauss = p['gauss_amps']
        self.current_limit = p['current_limit']
        self.field = p['field']
        
        
    def set_magnet_sweep(self, p):
        self.gauss = p['gauss_amps']
        self.current_limit = p['current_limit']
        self.field = p['field_start']
        f_end = p['field_end']/self.gauss
        assert f_end<self.c_limit, f'End current exceeds limit, limit: {self.c_limit}, current: {f_end}'
        self.output = True
