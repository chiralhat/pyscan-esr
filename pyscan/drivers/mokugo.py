# -*- coding: utf-8 -*-
"""
Created on June 30 2025

@author: Charles Collett
"""

from .instrument_driver import InstrumentDriver
from moku.instruments import ArbitraryWaveformGenerator
import numpy as np
from time import sleep

maxF = 800e3


class MokuGo(InstrumentDriver):
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
        self.set_switch_1pulse()


    def close(self):
        pass
    
    
    def __getitem__(cls, x):
        return getattr(cls, x)
    
    
    def __setitem__(cls, x, val):
        return setattr(cls, x, val)
    
    
    def set_switch_1pulse(self, time=10000, freq=800e3):
        assert freq<=maxF, f'Frequency exceeds limit, limit: {maxF}, freq: {freq}'
        ready = False
        while not ready:
            t = int(1/freq/100*1e9)

            num_zeros = int(time//t)
            if num_zeros<100:
                ready=True
            else:
                freq = freq/2

        pulse = np.concatenate((np.zeros(1), -np.ones(num_zeros),np.zeros(99-num_zeros)))
        pulse2 = (pulse+1)*-1
        mgo = self.instrument
        
        mgo.generate_waveform(channel=1, sample_rate='Auto', lut_data=list(pulse), frequency=freq, amplitude=10)
        mgo.generate_waveform(channel=2, sample_rate='Auto', lut_data=list(pulse2), frequency=freq, amplitude=10)
        mgo.burst_modulate(channel=1, trigger_source='Input1', trigger_mode='NCycle', burst_cycles=1, trigger_level=3)
        mgo.burst_modulate(channel=2, trigger_source='Input1', trigger_mode='NCycle', burst_cycles=1, trigger_level=3)
    
    
    def field_ramp(self, target):
        current_field = self.field
        target = float(target)
        step = self.gauss*0.001
        rate = self.ramp
        assert rate>0, f'Ramp rate needs to be a positive integer, rate: {rate}'
        while np.abs(current_field-target)>2*step:
            getout = False
            delta = target-current_field
            if delta>rate:
                delta = rate
            elif delta<-rate:
                delta = -rate
            else:
                getout = True
            self.v2 = (current_field+delta)/self.gauss
            if getout:
                break
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
