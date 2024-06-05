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

prefix_ns = [-2, -3, -4, -6, -8]
prefix_names = ['yoff', 'yzero', 'ymult', 'xzero', 'xincr']
tdivs = []
for n in range(10):
    tdivs += [2.5*10**-n, 5*10**-n, 10*10**-n]


class Tektronix2022B(Oscilloscope):
    '''
    Class to control Tektronix 2022B Oscilloscope.

    '''

    def __init__(self, instrument, timeout=1000, debug=False):

        super().__init__(instrument)

        self.instrument.timeout = timeout
        self.wprefix = {
            'yoff': [0, 0],
            'yzero': [0, 0],
            'ymult': [0, 0],
            'xzero': [0, 0],
            'xincr': [0, 0]
        }
        self.xdelay = 0

        self.debug = debug
        self.initialize_properties()

        
    voltage_limits = [0.002, 10]
    aves = np.array([1, 4, 16, 64, 128])
    tdivs = tdivs

        
    def initialize_properties(self):
        self.add_device_property({
            'name': 'time_division',
            'write_string': 'HOR:SCA {}',
            'query_string': 'HOR:SCA?',
            'range': [np.min(self.tdivs), np.max(self.tdivs)],
            'return_type': float})

        self.add_device_property({
            'name': 'trigger_delay',
            'write_string': 'HOR:MAI:POS {}',
            'query_string': 'HOR:MAI:POS?',
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
            'values': self.aves,
            'return_type': int})
            
        self.add_device_property({
            'name': 'trigger_level',
            'write_string': 'TRIG:MAI:LEV {}',
            'query_string': 'TRIG:MAI:LEV?',
            'range': [-10, 10],
            'return_type': float})#lambda x: float(x.split()[1][:-1])})

        for i in [1, 2]:
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

    block_start = [148, 152, 168, 172, 338]
    block_length = [4, 4, 4, 8, 20480]

    screen_width = 10
    screen_height = 8
    

    """Device-specific functions"""
    def initialize_waveform(self, channel):
#         for channel in [1, 2]:
        ch_str = 'dat:sou ch'+str(channel)
        self.write(ch_str)
        try:
            prefix = self.query('wfmp?')
        except:
            prefix = self.query('wfmp?')
        for n, var in enumerate(prefix_names):
             self.wprefix[var][channel-1] = float(prefix.split(';')[prefix_ns[n]])
        self.xdelay = self.trigger_delay
    

    def initialize_waveforms(self):
        self.initialize_waveform(1)
        self.initialize_waveform(2)

        
    def read_waveform_raw(self, channel=1, init=True):
        if init:
            self.initialize_waveform(channel)
        ch_str = 'dat:sou ch'+str(channel)
        self.write(ch_str)
        yoff, yzero, ymult, xzero, xincr = [v[channel-1] 
                                            for v in self.wprefix.values()]
        self.write('curve?')
        data = self.instrument.read_raw()
        headerlen = 2 + int(data[1:2])
        header = data[:headerlen]
        ADC_wave = data[headerlen:-1]
        ADC_wave = np.array(struct.unpack('>{0}h'.format(len(ADC_wave)//2),ADC_wave))
        Volts = (ADC_wave - yoff) * ymult  + yzero
        Time = np.arange(0, (xincr * len(Volts)), xincr)-((xincr * len(Volts))/2-self.trigger_delay)
        return np.array([Time, Volts])
    
    
    def read_waveforms(self, channel=0, init=True):
        if channel==0:
            chans = [1, 2]
            data = []
            for n in chans:
                data.append(self.read_waveform_raw(n, init))
#                 if n==1:
#                     sleep(0.15)
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
        
        
    @property
    def average(self):
        return 1 if (self.acquire_mode=='SAMPLE') else self.average_num
            
            
    @average.setter
    def average(self, new_value):
        if new_value==1:
            self.acquire_mode = 'SAMPLE'
        else:
            self.acquire_mode = 'AVERAGE'
            self.average_num = new_value
            
    
#     def time_division(self, time_div=0):
#         """Set or get the timebase setting (the time division between each grid
#         on the scope screen).

#         Parameters
#         ----------
#         time_div : Union[int, float], optional
#             Timebase setting in seconds, by default 0 (read the current value)

#         Returns
#         -------
#         float
#             The current timebase value in seconds
#         """
#         if time_div:
#             tdiv_str = '{:.1E}'.format(time_div)
#             self.write('HOR:SCA '+tdiv_str)
#         self.tdiv = float(self.query('HOR:SCA?'))
#         return self.tdiv
    

#     def trigger_delay(self, trig_del='Read'):
#         """Set or get the horizontal offset of the data on the screen (the
#         trigger delay). A positive delay moves the trace to the left.

#         Parameters
#         ----------
#         trig_del : Union[str, float], optional
#             Horizontal offset in seconds, by default 'Read' (read the current
#             value)

#         Returns
#         -------
#         float
#             The current horizontal offset in seconds
#         """
#         if trig_del!='Read':
#             trdl_str = '{:.6E}'.format(trig_del)
#             self.write('hor:mai:pos '+trdl_str)
#         self.trdl = float(self.query('hor:mai:pos?'))
#         return self.trdl


#     def voltage_division(self, channel, volt_div='Read'):
#         """Set or get the vertical sensitivity of the data on the screen (the
#         volts/division)

#         Parameters
#         ----------
#         channel: {1, 2}
#             The scope channel to use.
#         volt_div : Union[str, float], optional
#             Vertical sensitivity in volts/div, by default 'Read' (read the
#             current value)

#         Returns
#         -------
#         float
#             The current vertical sensitivity in volts/div
#         """
#         chan_str = 'CH{:d}:SCA'.format(channel)
#         if volt_div!='Read':
#             vdiv_str = chan_str+' {:.2E}'.format(volt_div)
#             self.write(vdiv_str)
#         self.vdiv[channel-1] = float(self.query(chan_str+'?'))
#         return self.vdiv[channel-1]
    

#     def channel_offset(self, channel, offset='Read'):
#         """Set or get the vertical offset of the data on the screen (the
#         volts away from center). A positive offset moves the trace up.

#         Parameters
#         ----------
#         channel: {1, 2}
#             The scope channel to use.
#         offset : Union[str, float], optional
#             Vertical offset in volts, by default 'Read' (read the
#             current value)

#         Returns
#         -------
#         float
#             The current vertical offset in volts
#         """
#         chan_str = 'CH{:d}:POS'.format(channel)
#         if offset!='Read':
#             offset_str = chan_str+' {:.2E}'.format(offset)
#             self.write(offset_str)
#         self.offset[channel-1] = float(self.query(chan_str+'?'))
#         return self.offset[channel-1]


#     def average(self, ave_num=0):
#         """Set or get the number of times to average the signal. The allowed
#         values are 4, 16, 32, 64, 128, 256.

#         Parameters
#         ----------
#         ave_num: {0, 1, 4, 16, 32, 64, 128, 256}
#             The number of times to average the signal. Defaults to 0,
#             which just queries the current averaging state. 1 turns
#             averaging off, setting the scope to sampling mode.

#         Returns
#         -------
#         int
#             The current average number
#         """
#         # Note that this command is not documented in the 2190E Programming
#         # Manual. I found it in the 2565-MSO Programming Manual.
#         acq_str = 'ACQ:MOD'
#         ave_str = 'ACQ:NUMAV'
#         if (ave_num==1):
#             self.write(acq_str+' SAM')
#         elif (ave_num>1):
#             avg_str = ave_str+' {}'.format(ave_num)
#             self.write(acq_str+' AVE')
#             self.write(avg_str)
#         acq_state = self.query(acq_str+'?')
#         if acq_state[:7] == 'AVERAGE':
#             self.avg = int(self.query(ave_str+'?'))
#         else:
#             self.avg = 1
#         return self.avg