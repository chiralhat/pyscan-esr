# -*- coding: utf-8 -*-
"""
Created on Dec 22 2020

@author: Charles Collett
"""


from .oscilloscope import Oscilloscope
import numpy as np
import struct
from time import sleep
import matplotlib.pyplot as plt

plotstyle = '.-'
def_wait = 0.25

trigger_types = ['EDGE', 'WIDTH', 'RISE', 'FALL', 'TIMEOUT',
                 'RUNT', 'LOGIC', 'SETHOLD', 'BUS']
trigger_sources = ['CH1', 'CH2', 'CH3', 'CH4', 'INT', 'AUX']
prefix_ns = [-2, -3, -4, -6, -8]
prefix_names = ['yoff', 'yzero', 'ymult', 'xzero', 'xincr']
tdivs = []
for n in range(10):
    tdivs += [2*10**-n, 4*10**-n, 10*10**-n]
channels = [1,2,3,4]

class TektronixMSO2(Oscilloscope):
    '''
    Class to control Tektronix MSO2 Oscilloscope.

    '''

    def __init__(self, instrument, timeout=2000, debug=False):

        super().__init__(instrument)

        self.instrument.timeout = timeout
        self.write('*cls') # clear ESR
        self.write('header 0')
        self.write('data:encdg RIBINARY')
        self.write(f'sel:ch1 1')
        self.write(f'sel:ch2 1')
        self.write('hor:mai:del:mod 1')
        self.wprefix = {
            'yoff': [0, 0, 0, 0],
            'yzero': [0, 0, 0, 0],
            'ymult': [0, 0, 0, 0],
            'xzero': [0, 0, 0, 0],
            'xincr': [0, 0, 0, 0],
            'record': [0, 0, 0, 0]
        }
        self.xdelay = 0
        self.screen_width = int(self.query('hor:div?').split('.')[0])
        
        self.debug = debug
        self.initialize_properties()
        self.tdiv = self.time_division

        
    voltage_limits = [0.001, 10]
    aves = np.arange(1, 10241)
    channels = channels
    tdivs = tdivs
    samplemode = 'SAMPLE'
    avemode = 'AVERAGE'

        
    def initialize_properties(self):
        self.add_device_property({
            'name': 'time_division',
            'write_string': 'HOR:SCA {}',
            'query_string': 'HOR:SCA?',
            'range': [np.min(self.tdivs), np.max(self.tdivs)],
            'return_type': float})

        self.add_device_property({
            'name': 'trigger_delay',
            'write_string': 'HOR:MAI:DEL:TIM {}',
            'query_string': 'HOR:MAI:DEL:TIM?',
            'range': [-20, 20],
            'return_type': float})

        self.add_device_property({
            'name': 'acquire_mode',
            'write_string': 'ACQ:MOD {}',
            'query_string': 'ACQ:MOD?',
            'values': ['SAMPLE', 'AVERAGE'],
            'return_type': str})

        self.add_device_property({
            'name': 'average_num',
            'write_string': 'ACQ:NUMAV {}',
            'query_string': 'ACQ:NUMAV?',
            'range': [1, 10240],
            'return_type': int})

        self.add_device_property({
            'name': 'trigger_type',
            'write_string': 'trig:a:typ {}',
            'query_string': 'trig:a:typ?',
            'values': trigger_types,
            'return_type': lambda x: x.strip()})

        for i in channels:
            self.add_device_property({
                'name': 'channel{}_scale'.format(i),
                'write_string': 'CH{}:SCA {}'.format(i, '{}'),
                'query_string': 'CH{}:SCA?'.format(i),
                'range': self.voltage_limits,
                'return_type': float})

            self.add_device_property({
                'name': 'channel{}_offset'.format(i),
                'write_string': 'CH{}:POS {}'.format(i, '{}'),
                'query_string': 'CH{}:POS?'.format(i),
                'range': [-30, 30],
                'return_type': float})

            self.add_device_property({
                'name': 'channel{}_invert'.format(i),
                'write_string': 'CH{}:INV {}'.format(i, '{}'),
                'query_string': 'CH{}:INV?'.format(i),
                'values': [1, 0],
                'return_type': int})


    """More complicated properties"""
    @property
    def trigger_source(self):
        ttype = self.trigger_type
        if ttype=="WIDTH":
            ttype = "PULSEWIDTH"
        source = self.query('trig:a:'+ttype+':sou?').strip()
        return source, ttype


    @trigger_source.setter
    def trigger_source(self, source):
        if source in trigger_sources:
            ttype = self.trigger_type
            if ttype=='WIDTH':
                if not source[:2]=="CH":
                    print('Value Error:')
                    print('Pulse width trigger source must be one of:')
                    for string in trigger_sources[:-2]:
                        print('{}'.format(string))
                else:
                    self.write('trig:a:pulsew:sou '+source)
            else:
                self.write('trig:a:'+ttype+':sou '+source)
        else:
            print('Value Error:')
            print('Trigger source must be one of:')
            for string in trigger_sources:
                print('{}'.format(string))
    

    @property
    def trigger_level(self):
        source = self.trigger_source[0]
        if source[:2]=="CH":
            level = self.query('trig:a:lev:'+source+'?')
        else:
            level = self.query('trig:auxl?')
        return level


    @trigger_source.setter
    def trigger_level(self, new_level):
        if -10 <= new_level <= 10:
            source = self.trigger_source[0]
            if source[:2]=="CH":
                self.write('trig:a:lev:'+source+' '+str(new_level))
            else:
                self.write('trig:auxl '+str(new_level))
        else:
            print('Value Error:')
            print('Trigger source must be between -10 and 10 V')
    

    """Device-specific functions"""
    def initialize_waveform(self, channel):
#         for channel in [1, 2]:
        ch_str = 'data:source ch'+str(channel)
        self.write(ch_str)
        
        for var in prefix_names:
            self.wprefix[var][channel-1] = float(self.query('wfmpre:'+var+'?'))
        self.wprefix['record'][channel-1] = int(self.query('wfmpre:nr_pt?'))
        self.xdelay = float(self.query('hor:mai:del:tim?'))
        self.tdiv = self.time_division
    

    def initialize_waveforms(self):
        self.initialize_waveform(1)
        self.initialize_waveform(2)
        self.initialize_waveform(3)
        self.initialize_waveform(4)

        
    def read_waveform_raw(self, channel=1, init=True):
        if init:
            self.initialize_waveform(channel)
        ch_str = 'data:source ch'+str(channel)
        self.write(ch_str)
        yoff, yzero, ymult, xzero, xincr, record = [v[channel-1] 
                                            for v in self.wprefix.values()]
        # try:
        #     while not self.query('*OPC?'):
        #         0
        #     self.write('curve?')
        #     data = self.instrument.read_raw(20)
        # except:
        #     while not self.query('*OPC?'):
        #         0
        #     self.write('curve?')
        #     data = self.instrument.read_raw(20)
        bin_wave = self.instrument.query_binary_values('curve?', datatype='b',
                                                        container=np.array, chunk_size = 1024**2)
        unscaled_wave = np.array(bin_wave, dtype='double') # data type conversion
        Volts = (unscaled_wave - yoff) * ymult + yzero
        total_time = xincr * record
        xstart = self.xdelay-5*self.tdiv
        tstop = xstart + total_time
        Time = np.linspace(xstart, tstop, num=record, endpoint=False)
        return np.array([Time, Volts])
    
    
    def read_waveforms(self, channel=0, init=True):
        if channel==0:
            chans = [1, 2]
            data = []
            for n in chans:
                data.append(self.read_waveform_raw(n, init))
        elif channel==5:
            chans = channels
            data = []
            for n in chans:
                data.append(self.read_waveform_raw(n, init))
        else:
            data = [self.read_waveform_raw(channel, init)]
        return data


    def read_scope(self, channel=0, init=True):
        return self.read_waveforms(channel, init)
    
    
    def read_screen(self, channel=0, trig_del='Read', init=True):
        return self.read_waveforms(channel, init)
    
    
    def show_screen(self, channel=0, init=True):
        self.scope_plot(self.read_screen, channel, init=init)
    
    
    def show_waveform(self, channel=0, init=True):
        self.scope_plot(self.read_waveforms, channel, init=init)        
            
    
    def toggle_invert(self, toggle):
        self.channel1_invert = toggle
        self.channel2_invert = toggle
        self.channel3_invert = toggle
        self.channel4_invert = toggle
