# -*- coding: utf-8 -*-
"""
Created on Dec 22 2020

@author: Charles Collett
Significant portions of this code are taken from the
windfreak package at
https://github.com/christian-hahn/windfreak-python
"""


from .instrument_driver import InstrumentDriver
from windfreak import SynthHD

phase_compression = 1#0.55


class WindfreakSynthHD():
    '''
    Class to control Windfreaktech SynthHD RF source

    '''

    def __init__(self, port='/dev/ttyACM0'):

        self.synth = SynthHD(port)
        self.synth.init()
        self.ch = self.synth
        
        # Need to set the Feedback to 'Divided'
        self.synth.API['feedback'] = (int, 'b{}', 'b?')
        self.synth.write('feedback', 0)
#         self.synth.close()
    

    def __getitem__(cls, x):
        return getattr(cls, x)
    
    
    def __setitem__(cls, x, val):
        return setattr(cls, x, val)
    
    
    def open(self):
        if not self.synth._dev:
            self.synth.open()
    

    def close(self):
        self.synth.close()
    
    
    def power_on(self, channel=0, close=True):
#         self.open()
        if self.synth.sweep_enable == True:
            self.synth.sweep_cont = False
        chans = [channel-1] if channel else [0, 1]
        for chan in chans:
            if not self.ch[chan].enable:
                self.ch[chan].enable = True
#         if close:
#             self.close()
    

    def power_off(self, channel=0):
#         self.open()
        chans = [channel-1] if channel else [0, 1]
        for chan in chans:
            self.ch[chan].enable = False
#         self.close()


    def set_freq(self, freq, channel=0):
        """Set frequency in MHz.

        Args:
            value (float / int): frequency in MHz.
        """
        chans = [channel-1] if channel else [0, 1]
        for chan in chans:
            self.ch[chan].frequency = freq*1e6


    def get_freq(self, channel=1):
        """Get frequency in MHz.

        Returns:
            float: frequency in MHz.
        """
        chan = self.ch[channel-1]
        return chan.frequency/1e6


    def set_power(self, pow, channel=1):
        """Set power in dBm.

        Args:
            float: power in dBm
        """
        chan = self.ch[channel-1]
        chan.power = pow


    def get_power(self, pow, channel=1):
        """Get power in dBm.

        Returns:
            float: power in dBm
        """
        chan = self.ch[channel-1]
        return chan.power


    def shift_phase(self, phi, channel=1):
        """Shift phase by degrees.

        Args:
            value (float / int): phase shift in degrees
        """
#         self.open()
        chan = self.ch[channel-1]
        chan.phase = phi
#         self.close()


    def cw(self, freq, power, channel=0):
        """Set up and output a CW signal.

        Parameters
        ----------
        freq : float / int
            Frequency in MHz.
        power : float / int
            Power in dBm.
        channel : 0, 1, 2
            Channel to output, with 0 meaning both. Defaults to 0.
        """
#         self.open()
        chan = [channel] if channel else [1, 2]
        for ch in chan:
            self.set_power(power, ch)
            self.set_freq(freq, ch)
            self.power_on(ch, close=False)
#         self.close()
        return chan

    @property
    def c1_freq(self):
        return self.ch[0].frequency
    
    @c1_freq.setter
    def c1_freq(self, new_value):
        self.ch[0].frequency = new_value*1e6
    
    @property
    def c2_freq(self):
        return self.ch[1].frequency
    
    @c2_freq.setter
    def c2_freq(self, new_value):
        self.ch[1].frequency = new_value*1e6
        
    @property
    def c_freqs(self):
        return self.c1_freq
    
    @c_freqs.setter
    def c_freqs(self, new_value):
        self.ch[0].frequency = new_value*1e6
        self.ch[1].frequency = new_value*1e6
        
    @property
    def c1_phase(self):
        return self.ch[0].phase/phase_compression
    
    @c1_phase.setter
    def c1_phase(self, new_value):
        self.ch[0].phase = new_value*phase_compression
        
    @property
    def c2_phase(self):
        return self.ch[1].phase/phase_compression
    
    @c2_phase.setter
    def c2_phase(self, new_value):
        self.ch[1].phase = new_value*phase_compression
        
    @property
    def c1_power(self):
        return self.ch[0].power
    
    @c1_power.setter
    def c1_power(self, new_value):
        self.ch[0].power = new_value
        
    @property
    def c2_power(self):
        return self.ch[1].power
    
    @c2_power.setter
    def c2_power(self, new_value):
        self.ch[1].power = new_value
    
    @property
    def sweep_freq_low(self):
        self.synth.write('channel', 0)
        return self.synth.read('sweep_freq_low')

    @sweep_freq_low.setter
    def sweep_freq_low(self, new_value):
        self.synth.write('channel', 0)
        self.synth.write('sweep_freq_low', new_value)

    @property
    def sweep_freq_low2(self):
        self.synth.write('channel', 1)
        return self.synth.read('sweep_freq_low')

    @sweep_freq_low.setter
    def sweep_freq_low2(self, new_value):
        self.synth.write('channel', 1)
        self.synth.write('sweep_freq_low', new_value)

    @property
    def sweep_freq_high(self):
        self.synth.write('channel', 0)
        return self.synth.read('sweep_freq_high')

    @sweep_freq_high.setter
    def sweep_freq_high(self, new_value):
        self.synth.write('channel', 0)
        self.synth.write('sweep_freq_high', new_value)

    @property
    def sweep_freq_high2(self):
        self.synth.write('channel', 1)
        return self.synth.read('sweep_freq_high')

    @sweep_freq_high.setter
    def sweep_freq_high2(self, new_value):
        self.synth.write('channel', 1)
        self.synth.write('sweep_freq_high', new_value)

    @property
    def sweep_freq_step(self):
        self.synth.write('channel', 0)
        return self.synth.read('sweep_freq_step')

    @sweep_freq_step.setter
    def sweep_freq_step(self, new_value):
        self.synth.write('channel', 0)
        self.synth.write('sweep_freq_step', new_value)

    @property
    def sweep_freq_step2(self):
        self.synth.write('channel', 1)
        return self.synth.read('sweep_freq_step')

    @sweep_freq_step.setter
    def sweep_freq_step2(self, new_value):
        self.synth.write('channel', 1)
        self.synth.write('sweep_freq_step', new_value)

    @property
    def sweep_time_step(self):
        self.synth.write('channel', 0)
        return self.synth.read('sweep_time_step')

    @sweep_time_step.setter
    def sweep_time_step(self, new_value):
        self.synth.write('channel', 0)
        self.synth.write('sweep_time_step', new_value)

    @property
    def sweep_time_step2(self):
        self.synth.write('channel', 1)
        return self.synth.read('sweep_time_step')

    @sweep_time_step.setter
    def sweep_time_step2(self, new_value):
        self.synth.write('channel', 1)
        self.synth.write('sweep_time_step', new_value)

    @property
    def sweep_power(self):
        self.synth.write('channel', 0)
        return self.synth.read('sweep_power_low')

    @sweep_power.setter
    def sweep_power(self, new_value):
        self.synth.write('channel', 0)
        self.synth.write('sweep_power_low', new_value)
        self.synth.write('sweep_power_high', new_value)

    @property
    def sweep_power2(self):
        self.synth.write('channel', 1)
        return self.synth.read('sweep_power_low')

    @sweep_power.setter
    def sweep_power2(self, new_value):
        self.synth.write('channel', 1)
        self.synth.write('sweep_power_low', new_value)
        self.synth.write('sweep_power_high', new_value)

    def freq_sweep_nolockin(self, params):
        """Set up and start a frequency sweep.

        Parameters
        ----------
        params : dict of float or int
            A dictionary including the starting, ending, and step
            frequencies (in MHz).
        """
#         self.open()

#        par_keys = ['freq_start', 'freq_end', 'freq_step', 'step_length', 'power']
#        start, stop, step, step_length, power = [params.get(k)
#                                            for k in params if k in par_keys]
        # num_steps = (stop-start)//step
        # step_length = length/num_steps
#        print(start, stop, step, step_length, power)
        self.synth.trigger_mode = 'full frequency sweep'
        self.sweep_freq_low = params['freq_start']
        self.sweep_freq_high = params['freq_end']
        self.sweep_freq_step = params['freq_step']
        self.sweep_time_step = params['step_length'] # In ms. Should be 4-10000.
        self.sweep_power = params['power']
        self.ch[0].enable = True


    def freq_sweep(self, params):

        self.c1_power = 19
        self.c2_power = params['power2']
        self.c1_freq = params['freq_start']+1
        self.c2_freq = params['freq_start']
        self.ch[0].enable = True
        self.ch[1].enable = True
        

    def freq_sweep_stop(self):
#         self.open()
        self.synth.trigger_mode = 'disabled'
        self.ch[0].enable = False
        self.ch[1].enable = False
#         self.close()


    def pulse_freq_sweep(self, p):
        if 'freq' in p.keys():
            self.c_freqs = p['freq']
        else:
            self.c_freqs = p['freq_start']
        self.ch[0].power = p['power']
        self.ch[1].power = p['power2']
        self.synth.write('feedback', 0)
        self.power_on()
        
        
    def spin_echo(self, p):
        if not self.c_freqs/1e6==p['freq']:
            self.c_freqs = p['freq']
        self.ch[0].power = p['power']
        self.ch[1].power = p['power2']
        self.c2_phase = p['phase']
        self.power_on()
        self.synth.write('feedback', 0)

        
    def bimodal_spin_echo(self, p):
        if not self.c1_freq/1e6==p['freq1']:
            self.c1_freq = p['freq1']
        if not self.c2_freq/1e6==p['freq2']:
            self.c2_freq = p['freq2']
        self.ch[0].power = p['power']
        self.ch[1].power = p['power2']
        self.power_on()
        self.synth.write('feedback', 0)
