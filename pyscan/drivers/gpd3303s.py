# -*- coding: utf-8 -*-
"""
Created on Dec 30 2022

@author: Charles Collett
"""


import gpd3303s


class GPD3303S():
    '''
    Class to control GPD 3303S Programmable Power Supply
    '''
    def __init__(self, port='/dev/ttyUSB2'):
        self.instrument = gpd3303s.GPD3303S()
        self.instrument.open(port)
        self.instrument.selectIndependentMode()
        self.instrument.enableBeep(False)
        self.instrument.setVoltage(1, 12)
        self.instrument.setVoltage(2, 0)
#        self.instrument.enableOutput(False)
        self._gauss = 278
        self.c_limit = 3.5


    def close(self):
        self.instrument.close()
    
    
    def __getitem__(cls, x):
        return getattr(cls, x)
    
    
    def __setitem__(cls, x, val):
        return setattr(cls, x, val)
        

    def power_on(self):
        self.instrument.enableOutput(True)


    def power_off(self):
        self.instrument.enableOutput(False)


    @property
    def v1(self):
        return self.instrument.getVoltageOutput(1), self.instrument.getVoltage(1)

    @v1.setter
    def v1(self, value):
        self.instrument.setVoltage(1, value)


    @property
    def v2(self):
        return self.instrument.getVoltageOutput(2), self.instrument.getVoltage(2)

    @v2.setter
    def v2(self, value):
        assert value<self.c_limit, f'Current exceeds limit, limit: {self.c_limit}, current: {value}'
        voltage = 3.5 if value>self.c_limit else value
        self.instrument.setVoltage(2, voltage)


    @property
    def c1(self):
        return self.instrument.getCurrentOutput(1)


    @property
    def c2(self):
        return self.instrument.getCurrentOutput(2)


    @property
    def status(self):
        self.instrument.serial.write(b'STATUS?\n')

        ret = []
        for i in range(3):
            ret.append(self.instrument.serial.readline(eol=self.instrument.eol))
            
        err = self.instrument.getError()
        if err != b'No Error.':
            raise RuntimeError(err)
        return ret


    @property
    def output(self):
        out_byte = self.status[0][12:13]
        out = False if out_byte == b'0' else True
        return out

    @output.setter
    def output(self, out):
        assert type(out) is bool, f'output expected Boolean, got: {out}, of type {type(out)}'
        self.instrument.enableOutput(out)

        
    @property
    def gauss(self):
        return self._gauss
    
    @gauss.setter
    def gauss(self, value):
        self._gauss = value
        
        
    @property
    def field(self):
        return self.v2[0]*self.gauss
    
    @field.setter
    def field(self, value):
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
        self.output = True
        
        
    def set_magnet_sweep(self, p):
        self.gauss = p['gauss_amps']
        self.current_limit = p['current_limit']
        self.field = p['field_start']
        f_end = p['field_end']/self.gauss
        assert f_end<self.c_limit, f'End current exceeds limit, limit: {self.c_limit}, current: {f_end}'
        self.output = True
