# -*- coding: utf-8 -*-
"""
Created on March 2 2021

@author: Charles Collett
"""


from .instrument_driver import InstrumentDriver
from lakeshore import Model335
from time import sleep, time
import numpy as np


class Lakeshore335():
    '''
    Class to control Lakeshore 335 Temperature Controller

    '''

    def __init__(self, baud=57600):
        
        self.instrument = Model335(baud)
        self.query = self.instrument.query
        self.write = self.instrument.command
        hres = self.instrument.HeaterResistance.HEATER_50_OHM
        hdisp = self.instrument.HeaterOutputDisplay.POWER
        self.t_chan = 1
        self.zone = 0
        self.tolerance = 0.1
        self.timeout = 600
        try:
            self.instrument.set_heater_setup_one(hres, 1.0, hdisp)
        except Exception as e:
            self.instrument.set_heater_setup_one(hres, 1.0, hdisp)
        self.heater(0, 1)
        self.heater(0, 2)
        self.instrument.set_heater_output_mode(1, 1+self.zone, self.t_chan, False)
        tnow = self.get_temp(self.t_chan)
        self.ramp(on=0)
        sleep(0.2)
        self.setpoint(tnow)
        self.ramp()
    
    
    def close(self):
        self.instrument.disconnect_usb()
    
    
    def get_temps(self):
        temps = [0, 0]
        try:
            temps = self.instrument.get_all_kelvin_reading()
        except Exception as e:
            temps = self.instrument.get_all_kelvin_reading()
        return temps

    
    def get_temp(self, ch=1):
        return self.get_temps()[ch-1]
    
    
    def setpoint(self, value=0, output=1):
        if value!=0:
            self.instrument.set_control_setpoint(output, value)
            self.tset = value
        else:
            self.tset = self.instrument.get_control_setpoint(output)
        return self.tset
    
    
    def ramp(self, rate=10, output=1, on=1):
        if rate!=0:
            self.instrument.set_setpoint_ramp_parameter(output, on, rate)
            self.trate = rate if on else 0
        else:
            self.trate = self.instrument.get_setpoint_ramp_parameter(output)['rate_value'] if on else 0
        return self.trate
    
    
    def output(self, mode=1, outp=1, inp=1, powerup=0):
        if mode!='Read':
            self.instrument.set_heater_output_mode(outp, mode+self.zone, inp, powerup)
        self.mode = self.instrument.get_heater_output_mode(outp)
        return self.mode
    
    
    def heater(self, hrange='Read', output=1):
        if hrange!='Read':
            if not hrange:
                hran = self.instrument.HeaterRange.OFF
            elif self.tset<=10:
                hran = self.instrument.HeaterRange.MEDIUM
            else:
                hran = self.instrument.HeaterRange.HIGH
            self.instrument.set_heater_range(output, hran)
            self.hran = hran
        else:
            self.hran = int(self.instrument.get_heater_range(output))
        return self.hran


    def temp(self, tset, output=1):
        """
        Set the temperature controller setpoint and enable the heater at an appropriate range.
        Waits until the temperature has reached the setpoint to exit (TBI)
        """
        assert tset>=1.5, f'Setpoint needs to be between 1.5 K and 320 K, setpoint: {tset}'
        assert tset<=320, f'Setpoint needs to be between 1.5 K and 320 K, setpoint: {tset}'
        tc = self.instrument
        self.setpoint(tset, output)
        self.heater(1, output)
        while tc.get_setpoint_ramp_status(output):
            pass
        start_time = time()
        while np.abs(self.get_temp(output)-tset)>self.tolerance:
            now_time = time()
            if (now_time-start_time)>self.timeout:
                raise AttributeError(f'Failed to reach desired temperature in {self.timeout} seconds.')
            sleep(1)
