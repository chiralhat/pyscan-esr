# -*- coding: utf-8 -*-
"""
Created on Dec 22 2020

@author: Charles Collett
"""


from .instrumentdriver import InstrumentDriver
from pyscan.general.itemattribute import ItemAttribute
import numpy as np
import struct
from time import sleep
import matplotlib.pyplot as plt
from scipy.fft import rfft, rfftfreq
import utility as ut

plotstyle = '.-'
def_wait = 0.25


class Oscilloscope(InstrumentDriver):
    '''
    Class to control a generic Oscilloscope.

    '''

    tdelay_dict = {
        'ns': 1e-9,
        'us': 1e-6,
        'ms': 1e-3
        }
    plot_size = (8, 6)

    
    def close(self):
        self.instrument.close()

        
    @property
    def average(self):
        return 1 if (self.acquire_mode==self.samplemode) else self.average_num
            
            
    @average.setter
    def average(self, new_value):
        if new_value==1:
            self.acquire_mode = self.samplemode
        else:
            self.acquire_mode = self.avemode
            if new_value in self.aves:
                value = new_value
            else:
                value = self.aves[np.abs(new_value-self.aves).argmin()]
            self.average_num = value

            
    """Functions for reading from the scope"""
    def read_region(self, edges, channel=0, trig_del='Read', **kwargs):
        if trig_del!='Read':
            self.trigger_delay = trig_del
        data = self.read_scope(channel=channel, **kwargs)
    
        region_edgen = [np.abs(data[0][0]-edge).argmin()
                        for edge in edges]
        subdata = [dat.T[region_edgen[0]:region_edgen[1]].T for dat in data]
        return subdata
    
    
    def read_scope_lsection(self, time_window, channel=0, trig_del='Read', **kwargs):
        trdl = self.trigger_delay
        tdiv = self.time_division
        section_edge = [trdl-tdiv*self.screen_width/2+n for n in [0, time_window]]
        return self.read_region(section_edge, channel, trig_del, **kwargs)
    
    
    def scope_plot(self, read_func, channel=0, **kwargs):
        fig, ax = plt.subplots(figsize=self.plot_size)
        ax.set_xlabel('Time (s)'.format())
        ax.set_ylabel('Voltage (V)')
        data = read_func(channel=channel, **kwargs)
        if channel==0:
            chan = [1, 2]
        elif channel==5:
            chan = [1,2,3,4]
        else:
            chan = [channel]
        l_str = 'Channel {}'
        lines = [ax.plot(dat[0], dat[1], plotstyle, label=l_str.format(n))[0]
                 for dat, n in zip(data, chan)]
        ax.legend()
        plt.tight_layout()
        return fig, ax, lines
    
    
    def show_scope(self, channel=0, **kwargs):
        self.scope_plot(self.read_scope, channel, **kwargs)
    
    
    def show_scope_lsection(self, time_window, channel=0, **kwargs):
        self.scope_plot(self.read_scope_lsection, channel, time_window=time_window, **kwargs)


    def fourier_signal(self, d, fstart=3, fstop=100):
        d.fourier = np.array([np.abs(rfft(sig)) for sig in [d.xsub, d.v1sub, d.v2sub]])
        d.ffreqs = rfftfreq(len(d.xsub), d.time[1]-d.time[0])
        d.ffit = np.zeros((3, 4))
        for n in range(3):
            try:
                d.ffit[n] = ut.lor_fit(np.array([d.ffreqs, -d.fourier[n]])[:, fstart:fstop])[0]
            except:
                0
        d.xfamp, d.v1famp, d.v2famp = [-fit[1] for fit in d.ffit]
        d.ffdet = d.ffit[1][-1]
        d.ffdet2 = d.ffit[2][-1]


    def sback(self, sig, backnum=100):
        return sig-np.mean(sig[-backnum:])


    def read_vxy(self, d=0, sltime=0, reps=1, init=False, fstart=3, fstop=100):
        if isinstance(d, int):
            d = ItemAttribute()

        [[d.time, d.volt1], [_, d.volt2]] = self.read_screen(0, init=init)
        if reps>1:
            for n in range(reps-1):
                sleep(sltime)
                [[_, v1], [_, v2]] = self.read_screen(0, init=False)
                d.volt1 = (v1+d.volt1)
                d.volt2 = (v2+d.volt2)
            d.volt1 = d.volt1/reps
            d.volt2 = d.volt2/reps
        d.x = np.sqrt(d.volt1**2+d.volt2**2)
        d.v1sub = self.sback(d.volt1)
        d.v2sub = self.sback(d.volt2)
        d.xsub = np.sqrt(d.v1sub**2+d.v2sub**2)
        
        d.i = d.volt1
        d.q = d.volt2
        d.freq = d.time

        self.fourier_signal(d, fstart, fstop)
        
        return d

        
    def read_vxys(self, d=0, sltime=0, reps=1, init=False, fstart=3, fstop=100):
        if isinstance(d, int):
            d = ItemAttribute()

        [[d.time, d.volt1], [_, d.volt2],
            [_, d.volt3], [_, d.volt4]] = self.read_screen(5, init=init)
        if reps>1:
            for n in range(reps-1):
                sleep(sltime)
                [[_, v1], [_, v2],
                    [_, v3], [_, v4]] = self.read_screen(5, init=False)
                d.volt1 = (v1+d.volt1)
                d.volt2 = (v2+d.volt2)
                d.volt3 = (v3+d.volt3)
                d.volt4 = (v4+d.volt4)
        d.volt1 = self.sback(d.volt1/reps)
        d.volt2 = self.sback(d.volt2/reps)
        d.volt3 = self.sback(d.volt3/reps)
        d.volt4 = self.sback(d.volt4/reps)
        d.x1 = np.sqrt(d.volt1**2+d.volt2**2)
        d.x2 = np.sqrt(d.volt3**2+d.volt4**2)
        
        return d

        
    def read_vxy_onoff(self, devices, init=False, fstart=3, fstop=100):
        d = ItemAttribute()

        [[d.time, d.volt1on], [_, d.volt2on]] = self.read_screen(init=False)
        d.xon = np.sqrt(d.volt1on**2+d.volt2on**2)
        d.v1_subon = d.volt1on-np.mean(d.volt1on[-10:])
        d.v2_subon = d.volt2on-np.mean(d.volt2on[-10:])
        d.x_subon = np.sqrt(d.v1_subon**2+d.v2_subon**2)
        devices.synth.ch[1].rf_enable = False
        sleep(0.02)
        
        [[_, d.volt1off], [_, d.volt2off]] = self.read_screen(init=False)
        d.xoff = np.sqrt(d.volt1off**2+d.volt2off**2)
        d.v1_suboff = d.volt1off-np.mean(d.volt1off[-10:])
        d.v2_suboff = d.volt2off-np.mean(d.volt2off[-10:])
        d.x_suboff = np.sqrt(d.v1_suboff**2+d.v2_suboff**2)
        devices.synth.ch[1].rf_enable = True
        d.x_sub = d.x_subon-d.x_suboff
        
        return d
            
    
    """Functions for setting the scope up for taking data."""
    def auto_scale(self, channel=1, offset=True, wait=def_wait):
        """Read the data on the scope screen, and scale the scope so that the
        sensitivity is maximized given the input data. If the scope is not
        offset, then it makes sure both the minimum and maximum values are
        scaled properly. If it is offset, then only the maximum is checked.

        Parameters
        ----------
        channel: {1, 2}, optional
            The scope channel to scale.
        offset: {True, False}, optional
            Whether or not the trace is offset to the bottom of the screen
            (for data that is expected to be entirely positive).
        wait: float, optional
            The number of seconds to wait between setting the new scale
            and testing the result (defaults to 0.1 s).
        
        Returns:
        float
            The new scale setting (vdiv).
        """
        vdiv = 'channel{}_scale'.format(channel)
        ch_off = 'channel{}_offset'.format(channel)
        ch = channel-1
        old_avg = self.average
        self.average = 1
        vblocks = self.vert_blocks if offset else self.vert_blocks/2
        volt_limits = [(vblocks-n)*self[vdiv] for n in [-.2,0.5]]
        setting_scope = True
        set_offset = -(self.vert_blocks/2-0.5)*self[vdiv] if offset else 0
        self[ch_off] = set_offset
        sleep(wait)
        
        while setting_scope:
            volt_limits = [(vblocks-n)*self[vdiv] for n in [0,1]]
            vread = self.read_scope(channel)[0][1]
            vmax = vread.max()
            vmin = vread.min()
            off_bottom = (vmin < -volt_limits[0])
            if (vmax > volt_limits[0]):
                if (self[vdiv] == volt_limits[1]):
                    setting_scope = False
                else:
                    self[vdiv] = np.abs(vmax)*2/vblocks
            elif (off_bottom and not offset):
                if (self[vdiv] == volt_limits[1]):
                    setting_scope = False
                else:
                    self[vdiv] = np.abs(vmin)*2/vblocks
            elif ((vmax < volt_limits[1]) and
                  (offset or (vmin > -volt_limits[1]))):
                if (self[vdiv] == volt_limits[0]):
                    setting_scope = False
                else:
                    volt_amplitude = vmax if offset else np.abs([vmax, vmin]).max()
                    self[vdiv] = volt_amplitude/vblocks
            else:
                setting_scope = False
            set_offset = -3.5*self.voltage_division[ch] if offset else 0
            self[ch_off] = set_offset
            sleep(wait)
        
        self.average = old_avg
        return self.voltage_division[ch]
    

    def setup_spin_echo(self, p={'pulse1': 100,
                                 'pulse2': 100,
                                 'delay': 500,
                                 'h_offset': 300,
                                 'tdiv': 10e-8,
                                 'scale': 0.002,
                                'ave': 128},
                       offset=False, **kwargs):
        """Set the scope scale and delay for a spin echo measurement.

        Parameters
        ----------
        delay : float
            Time between pi/2 and pi pulses, in us. This is where we expect the
            echo to be
        pre_off : int, optional
            Amount of time in ns separating the screen edge from the end of the
            delay, by default 300 ns
        channel : {1, 2}, optional
            The scope channel to scale, by default 1
        offset : bool, optional
            Whether or not the trace is offset to the bottom of the screen
            (for data that is expected to be entirely positive), by default True
        time_div : float, optional
            Set the horizontal scale of the scope to this value, or if 0 just read the value,
            by default 0
        scale: boolean, optional
            Autoscale the scope, by default True
        """
        delay = p['pulse1']+p['pulse2']+2*p['delay']
        pre_off = p['h_offset']
        time_div = p['tdiv']
        scale = p['scale']
        self.average = 1
        self.trigger_type = 'EDGE'
        self.trigger_source = 'AUX'
        
        if time_div:
            self.time_division = time_div
        else:
            time_div = self.time_division
        screen_start = time_div*self.screen_width/2+(delay+pre_off)/1e9
        self.trigger_delay = screen_start
        if not scale:
            self.auto_scale(offset=offset, **kwargs)
        else:
            self.channel1_scale = scale
            self.channel2_scale = scale
            self.channel3_scale = scale
            self.channel4_scale = scale
        
        self.initialize_waveforms()
        self.xdelay -= delay/1e9
        self.average = p['ave']
        p['ave'] = self.average


    def setup_pulse_decay(self, p={'h_offset': 0,
                                   'pulse1': 100,
                                   'pulse2': 100,
                                   'delay': 500,
                                   'v_offset': False,
                                   'ave': 1,
                                   'scale': 0.1,
                                   'tdiv': 1e-7,}):
        """Set the scope scale and delay for a pulse decay measurement.
        Set the left edge of the screen to be the trigger, plus some offset
        (to move the pre-ringdown transients off the screen).
        Offset the trace so zero is near the bottom of the screen (optional).

        Parameters
        ----------
        h_off : int, optional
            Amount of time in ns separating the screen edge from the trigger,
            by default 300 ns
        channel : {1, 2}, optional
            The scope channel to scale
        offset : bool, optional
            Whether or not the trace is offset to the bottom of the screen
            (for data that is expected to be entirely positive),
            by default False
        time_div : float, optional
            Set the horizontal scale of the scope to this value,
            or if 0 just read the value, by default 0
        scale: boolean, optional
            Autoscale the scope, by default True
        """
        delay = p['pulse1']+p['pulse2']+p['delay']
        h_off = p['h_offset']
        time_div = p['tdiv']
        offset = p['v_offset']
        self.trigger_type = 'EDGE'
        self.trigger_source = 'AUX'

        self.time_division = time_div
        screen_start = delay/1e9+time_div*self.screen_width/2+h_off/1e9
        self.trigger_delay = screen_start
        self.channel1_scale = p['scale']
        self.channel2_scale = p['scale']
        
        self.initialize_waveforms()
        self.xdelay -= delay/1e9
        self.average = p['ave']
        p['ave'] = self.average


    def setup_freq_sweep_nolockin(self, length, ave=1, scale=0.1, offset=False, **kwargs):
        """Set the scope to show a frequency sweep, with optional averaging.

        Parameters
        ----------
        length : float
            Duration of the frequency sweep, in ms
        ave : {1, 4, 16, 32, 64, 128, 256}, optional
            Number of times to average the scope, by default 1 (no averaging)
        scale : float, optional
            Vertical scaling value, in V. If 0, auto-scales the scope
            By default 0.1
        """
        # Reset any averaging
        self.average = 1
        # Set the timebase so that the full sweep appears on the screen.
        length_s = length/1000
        # The scope only allows tdiv to be 1, 2.5, or 5 in each decade, and
        # rounds the scale down, annoyingly. The 2.49 factor helps with that
        self.time_division = length_s/self.screen_width*2.49
        # Set the delay so the sweep starts at the beginning of the screen.
        delay = self.time_division*self.screen_width/2*1.01
        self.trigger_delay = delay
        # If desired, autoscale the scope.
        if not scale:
            self.auto_scale(offset=offset, **kwargs)
        else:
            self.channel1_scale = scale
            self.channel2_scale = scale
        # Set the averaging
        self.average = ave


    def setup_freq_sweep(self, params):
        """Set the scope to show a frequency sweep, with optional averaging.

        Parameters
        ----------
        """
        # Reset any averaging
        self.average = 1
        # Set the scale
        self.channel1_scale = params['scale']
        self.channel2_scale = params['scale']
        # Set the time base and trigger
        self.time_division = 2500e-9
        self.trigger_delay = 0
        self.trigger_type = 'EDGE'
        self.trigger_source = 'CH1'
        self.trigger_level = 0
        
        self.initialize_waveforms()
        # Set the averaging
        self.average = params['ave']
        params['ave'] = self.average


    def read_freq_sweep(self, d=0, ave=1, sltime=0, reps=1, init=True):
        self.average = 1
        sleep(0.1)
        self.average = ave
        sleep(sltime)
        out = self.read_vxy(d=d, sltime=sltime, reps=reps, init=init)
        if isinstance(d, int):
            d = out
        n = np.abs(1e6-d.ffreqs).argmin()
        d.xfour, d.v1four, d.v2four = d.fourier[:, n]
        d.fourmax = d.fourier[:, n].max()
        return d


    def measure_freq_sweep_nolockin(self, params, channel=1, init=True):
        """Read from the scope during a frequency sweep, trimming the output
        to just the sweep range, and changing time to frequency.

        Parameters
        ----------
        params : dict
            length : float
                Duration of the frequency sweep, in ms
            fstart : float
                Starting frequency, in MHz
            fstop : float
                Ending frequency, in MHz
            fstep: float
                Frequency step, in MHz
        channel : {1, 2}
            Scope channel to measure, by default 1
        """
        sweep_names = ['freq_end', 'freq_start', 'freq_step', 'step_length']
        fstop, fstart, fstep, step_length = [params[s] for s in sweep_names]
        length = (fstop-fstart)/fstep*step_length
        data = self.read_scope_lsection(time_window=length/1000, channel=channel, init=init)[0][1]
        nsteps = (fstop-fstart)//fstep+1
        dat_length = len(data)
        sub_length = int(np.ceil(dat_length/nsteps))
        nrange = np.arange(nsteps)

        freqs = np.concatenate([np.ones(sub_length)*fstart+n*fstep for n in nrange])
        return np.array([freqs[:(dat_length)], data])
