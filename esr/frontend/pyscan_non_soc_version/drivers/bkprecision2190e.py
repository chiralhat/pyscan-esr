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

plotstyle = ".-"
def_wait = 0.25
tdivs = []
for n in range(10):
    tdivs += [2.5 * 10**-n, 5 * 10**-n, 10 * 10**-n]


class BKPrecision2190E(Oscilloscope):
    """
    Class to control BK Precision 2190E Oscilloscope.

    """

    def __init__(self, instrument, timeout=1000, debug=False):

        super().__init__(instrument)

        self.instrument.timeout = timeout
        self.scaler = [0, 0]
        self.offset = [0, 0]

        self.debug = debug
        self.initialize_properties()

        self.voltage_division = [self.channel1_scale, self.channel2_scale]
        self.channel_offset = [self.channel1_offset, self.channel2_offset]

    voltage_limits = [0.002, 10]
    trig_limits = [-10, 10]
    aves = np.array([1, 4, 16, 32, 64, 128, 256])
    tdivs = tdivs
    trigs = ["C1", "C2", "EX", "EX5"]
    samplemode = "SAMPLING"
    avemode = "AVERAGE"

    def initialize_properties(self):
        self.add_device_property(
            {
                "name": "time_division",
                "write_string": "TDIV {}s",
                "query_string": "TDIV?",
                "range": [np.min(self.tdivs), np.max(self.tdivs)],
                "return_type": lambda x: float(x.split()[1][:-1]),
            }
        )

        self.add_device_property(
            {
                "name": "trigger_delay",
                "write_string": "TRDL {}s",
                "query_string": "TRDL?",
                "range": [-20, 20],
                "return_type": lambda x: float(x.split()[1][:-2])
                * self.tdelay_dict[x.strip()[-2:]],
            }
        )

        self.add_device_property(
            {
                "name": "acquire_mode",
                "write_string": "ACQW {}",
                "query_string": "ACQW?",
                "values": ["SAMPLING", "AVERAGE"],
                "return_type": lambda x: (x.split()[1].split(",")[0]),
            }
        )

        self.add_device_property(
            {
                "name": "average_num",
                "write_string": "AVGA {}",
                "query_string": "AVGA?",
                "values": self.aves,
                "return_type": lambda x: int(x.split()[1]),
            }
        )

        for i in self.trigs:
            self.add_device_property(
                {
                    "name": "{}_trigger_level".format(i),
                    "write_string": "{}:TRLV {}V".format(i, "{}"),
                    "query_string": "{}:TRLV?".format(i),
                    "range": self.trig_limits,
                    "return_type": lambda x: float(x.split()[1][:-1]),
                }
            )

        self.add_device_property(
            {
                "name": "trigger_source",
                "write_string": "TRSE EDGE,SR,{}",
                "query_string": "TRSE?",
                "values": self.trigs,
                "return_type": lambda x: (x.split(",")[2]),
            }
        )

        for i in [1, 2]:
            self.add_device_property(
                {
                    "name": "channel{}_scale".format(i),
                    "write_string": "C{}:VDIV {}V".format(i, "{}"),
                    "query_string": "C{}:VDIV?".format(i),
                    "range": self.voltage_limits,
                    "return_type": lambda x: float(x.split()[1][:-1]),
                }
            )

            self.add_device_property(
                {
                    "name": "channel{}_offset".format(i),
                    "write_string": "C{}:OFST {}V".format(i, "{}"),
                    "query_string": "C{}:OFST?".format(i),
                    "range": [-30, 30],
                    "return_type": lambda x: float(x.split()[1][:-1]),
                }
            )

    block_start = [148, 152, 168, 172, 338]
    block_length = [4, 4, 4, 8, 20480]

    screen_width = 16
    screen_height = 8

    """Device-specific functions"""

    def initialize_waveforms(self):
        self.read_waveforms()

    # TODO: Something wrong with the time base and delay, need to fix
    def waveform_parameters(self, signal, n):
        blocks = [
            signal[st : st + end]
            for st, end in zip(self.block_start, self.block_length)
        ]
        scaler, offset, time_div = [
            struct.unpack("f", block)[0] for block in blocks[:3]
        ]
        time_start = struct.unpack("d", blocks[3])[0]
        time = np.arange(0, self.block_length[-1]) * time_div + time_start
        self.scaler[n] = scaler
        self.offset[n] = offset
        self.time = time
        return blocks[-1]

    def process_waveform(self, sig):
        n = int(sig[1:2]) - 1
        if len(sig) > 20600:
            signal = sig[29:-2]

            block = self.waveform_parameters(signal, n)
        else:
            block = sig[21:-2]
        volts = (
            np.array([by if by <= 127 else -1 * (256 - by) for by in block])
            * 2
            * self.scaler[n]
            - self.offset[n]
        )
        return np.array([self.time, volts])

    def read_waveform_raw(self, channel=1, init=True):
        rstr = "ALL" if init else "DAT2"
        readstr = ("C{0}:WF? " + rstr).format(channel)
        self.write(readstr)
        #         if init:
        sig = self.instrument.read_raw(12)
        #         else:
        #             sig = self.instrument.read_raw()
        # if sig==b'\n':
        #     sig = self.conn.read_raw(12)
        return sig

    def read_waveforms(self, channel=0, init=True):
        data = []
        if channel == 0:
            chans = [1, 2]
        else:
            chans = [channel]
        for n in chans:
            trastr = "C{0}:TRA?".format(n)
            trace_on = self.query(trastr).rstrip()[7:]
            if trace_on == "ON":
                sig = self.read_waveform_raw(n, init=init)
                data.append(self.process_waveform(sig))
        return data

    def read_scope(self, channel, init=True):
        return self.read_waveforms(channel, init=init)

    def read_screen(self, channel=0, trig_del="Read", init=True):
        trdl = self.trigger_delay
        tdiv = self.time_division
        screen_edge = [self.screen_width / (2 * n) for n in [1, -1]]
        window_edge = [trdl - n * tdiv for n in screen_edge]
        return self.read_region(window_edge, channel, trig_del, init=init)

    def show_screen(self, channel=0, **kwargs):
        self.scope_plot(self.read_screen, channel, **kwargs)

    def show_waveform(self, channel=0, **kwargs):
        self.scope_plot(self.read_waveforms, channel, **kwargs)

    @property
    def trigger_level(self, source="EX"):
        fname = "{}_trigger_level".format(source)
        return getattr(self, fname)

    @trigger_level.setter
    def trigger_level(self, new_value, source="EX"):
        fname = "{}_trigger_level".format(source)
        if new_value in self.trig_limits:
            return setattr(self, fname, new_value)
        else:
            print("Value Error setting {}".format(fname))

    # def time_division(self, time_div=0):
    #     """Set or get the timebase setting (the time division between each grid
    #     on the scope screen).

    #     Parameters
    #     ----------
    #     time_div : Union[int, float], optional
    #         Timebase setting in seconds, by default 0 (read the current value)

    #     Returns
    #     -------
    #     float
    #         The current timebase value in seconds
    #     """
    #     if time_div:
    #         tdiv_str = '{:.1E}s'.format(time_div)
    #         self.write('TDIV '+tdiv_str)
    #     self.tdiv = float(self.query('TDIV?')[5:-2])
    #     return self.tdiv

    # def trigger_delay(self, trig_del='Read'):
    #     """Set or get the horizontal offset of the data on the screen (the
    #     trigger delay). A positive delay moves the trace to the left.

    #     Parameters
    #     ----------
    #     trig_del : Union[str, float], optional
    #         Horizontal offset in seconds, by default 'Read' (read the current
    #         value)

    #     Returns
    #     -------
    #     float
    #         The current horizontal offset in seconds
    #     """
    #     if trig_del!='Read':
    #         trdl_str = '{:.6E}s'.format(trig_del)
    #         self.write('TRDL '+trdl_str)
    #     trdl = (self.query('TRDL?')[5:-1])
    #     self.trdl = float(trdl[:-2])*self.tdelay_dict[trdl[-2:]]
    #     return self.trdl

    # def voltage_division(self, channel, volt_div='Read'):
    #     """Set or get the vertical sensitivity of the data on the screen (the
    #     volts/division)

    #     Parameters
    #     ----------
    #     channel: {1, 2}
    #         The scope channel to use.
    #     volt_div : Union[str, float], optional
    #         Vertical sensitivity in volts/div, by default 'Read' (read the
    #         current value)

    #     Returns
    #     -------
    #     float
    #         The current vertical sensitivity in volts/div
    #     """
    #     chan_str = 'C{:d}:VDIV'.format(channel)
    #     if volt_div!='Read':
    #         vdiv_str = chan_str+' {:.2E}V'.format(volt_div)
    #         self.write(vdiv_str)
    #     self.vdiv[channel-1] = float(self.query(chan_str+'?')[8:-2])
    #     return self.vdiv[channel-1]

    # def channel_offset(self, channel, offset='Read'):
    #     """Set or get the vertical offset of the data on the screen (the
    #     volts away from center). A positive offset moves the trace up.

    #     Parameters
    #     ----------
    #     channel: {1, 2}
    #         The scope channel to use.
    #     offset : Union[str, float], optional
    #         Vertical offset in volts, by default 'Read' (read the
    #         current value)

    #     Returns
    #     -------
    #     float
    #         The current vertical offset in volts
    #     """
    #     chan_str = 'C{:d}:OFST'.format(channel)
    #     if offset!='Read':
    #         offset_str = chan_str+' {:.2E}V'.format(offset)
    #         self.write(offset_str)
    #     self.offset[channel-1] = float(self.query(chan_str+'?')[8:-2])
    #     return self.offset[channel-1]

    # def average(self, ave_num=0):
    #     """Set or get the number of times to average the signal. The allowed
    #     values are 4, 16, 32, 64, 128, 256.

    #     Parameters
    #     ----------
    #     ave_num: {0, 1, 4, 16, 32, 64, 128, 256}
    #         The number of times to average the signal. Defaults to 0,
    #         which just queries the current averaging state. 1 turns
    #         averaging off, setting the scope to sampling mode.

    #     Returns
    #     -------
    #     int
    #         The current average number
    #     """
    #     # Note that this command is not documented in the 2190E Programming
    #     # Manual. I found it in the 2565-MSO Programming Manual.
    #     acq_str = 'ACQW'
    #     if (ave_num==1):
    #         self.write(acq_str+' SAMPLING')
    #     elif (ave_num>1):
    #         set_ave = aves[np.abs(ave_num-aves).argmin()]
    #         ave_str = 'AVGA'+' {}'.format(set_ave)
    #         self.write(acq_str+' AVERAGE')
    #         self.write(ave_str)
    #     acq_state = self.query(acq_str+'?')[5:-1]
    #     if acq_state[:7] == 'AVERAGE':
    #         self.avg = int(acq_state[8:])
    #     else:
    #         self.avg = 1
    #     return self.avg
