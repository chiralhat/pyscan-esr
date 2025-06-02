# -*- coding: utf-8 -*-
"""
Created on Dec 22 2020

@author: Charles Collett
"""


from .instrument_driver import InstrumentDriver
import struct
import numpy as np

freq = 0.2
tstep = 1 / freq

# period_shift = 1 << 16
period_shift = 1


class ecp5evn(InstrumentDriver):
    """
    Class to control Lattice ECP5 FPGA (ecp5-evn)

    """

    def __init__(self, instrument):

        super().__init__(instrument)
        self._delay = 200 * tstep
        self._delay2 = 200 * tstep
        self._period = 1 * period_shift * tstep
        self._pulse1 = 30 * tstep
        self._pulse2 = 30 * tstep
        self._pulse2_1 = 30 * tstep
        self._pulse2_2 = 30 * tstep
        self._cpmg = 1
        self._p2start = 0
        self._pump = 1
        self._block = 1
        self._pulse_block = 250
        self._pulse_block_off = 500
        self._nutation_width = 0
        self._nutation_delay = 0
        self._pre_att = 0
        self.se_port = 0
        self._phase_sub = 1

    control_byte = {
        "delay": 0,
        "period": 1,
        "pulse1": 2,
        "pulse2": 3,
        "toggle": 4,
        "cpmg": 5,
        "attenuators": 6,
        "nutation": 7,
    }

    pack_fmt = {1: "B", 2: "H", 4: "I"}

    freq = freq
    tstep = tstep

    def close(self):
        self.instrument.close()

    def readcheck(self, out):
        self.instrument.write(out)
        check = self.read()
        out_check = np.sum(out[:-1])
        if out_check > 255:
            out_check = out_check - 256
        in_check = struct.unpack("B", check)[0]
        assert out_check - in_check == 0, "FPGA write check failed"
        return out

    def intToByte(self, num, nBytes=4):
        unpack_str = "{}B".format(nBytes)
        pack_str = self.pack_fmt[nBytes]
        return struct.unpack(unpack_str, struct.pack(pack_str, num))

    def set_param(self, param, num):
        out = bytearray([self.control_byte[param]])
        [out.insert(0, b) for b in self.intToByte(num)[::-1]]
        return self.readcheck(out)

    def set_time(self, param, t_ns):
        num = int(np.round(t_ns / self.tstep))
        self.set_param(param, num)
        return num * self.tstep

    def set_p2time(self, param, t_ns1, t_ns2):
        num1 = int(np.round(t_ns1 / self.tstep))
        num2 = int(np.round(t_ns2 / self.tstep))
        nums = num1 + (num2 << 16)
        self.set_param(param, nums)
        return (num1 * self.tstep, num2 * self.tstep)

    def set_times(self, pulse1, pulse2, delay, period):
        self.pulse1 = pulse1
        self.pulse2 = pulse2
        self.delay = delay
        self.period = period

    def set_times2(self, pulse1, pulse2, delay, period):
        self.pulse2_1 = pulse1
        self.pulse2_2 = pulse2
        self.delay2 = delay
        self.period = period

    def toggle(self, phase_sub=1, block=1, pulse_block=200, pulse_block_off=1500):
        pblock = int(np.round(pulse_block / self.tstep))
        pblock_off = int(np.round(pulse_block_off / self.tstep))
        out = bytearray([self.control_byte["toggle"]])
        pbo_byte = self.intToByte(pblock_off, 2)
        [out.insert(0, b) for b in pbo_byte[::-1]]
        out.insert(0, self.intToByte(pblock, 1)[0])
        out.insert(0, self.intToByte(block + 2 * phase_sub, 1)[0])
        return self.readcheck(out)

    @property
    def phase_sub(self):
        return self._phase_sub

    @phase_sub.setter
    def phase_sub(self, phase_sub):
        self.toggle(phase_sub, self._block, self._pulse_block, self._pulse_block_off)
        self._phase_sub = phase_sub

    @property
    def block(self):
        return self._block

    @block.setter
    def block(self, block):
        self.toggle(self._phase_sub, block, self._pulse_block, self._pulse_block_off)
        self._block = block

    @property
    def pulse_block(self):
        return self._pulse_block * self.tstep

    @pulse_block.setter
    def pulse_block(self, pulse_block):
        num = int(np.round(pulse_block / self.tstep))
        self.toggle(self._phase_sub, self._block, pulse_block, self._pulse_block_off)
        self._pulse_block = num

    @property
    def pulse_block_off(self):
        return self._pulse_block_off * self.tstep

    @pulse_block_off.setter
    def pulse_block_off(self, pulse_block_off):
        num = int(np.round(pulse_block_off / self.tstep))
        self.toggle(self._phase_sub, self._block, self._pulse_block, pulse_block_off)
        self._pulse_block_off = num

    @property
    def delay(self):
        return self._delay

    @delay.setter
    def delay(self, delay):
        self._delay = self.set_p2time("delay", delay, self._delay2)[0]

    @property
    def delay2(self):
        return self._delay2

    @delay2.setter
    def delay2(self, delay2):
        self._delay2 = self.set_p2time("delay", self._delay, delay2)[1]

    @property
    def period(self):
        return self._period

    @period.setter
    def period(self, period):
        self._period = self.set_time("period", period)

    @property
    def pulse1(self):
        return self._pulse1

    @pulse1.setter
    def pulse1(self, pulse1):
        self._pulse1 = self.set_p2time("pulse1", pulse1, self._pulse2_1)[0]

    @property
    def pulse2(self):
        return self._pulse2

    @pulse2.setter
    def pulse2(self, pulse2):
        self._pulse2 = self.set_p2time("pulse2", pulse2, self.pulse2_2)[0]

    @property
    def pulse2_1(self):
        return self._pulse2_1

    @pulse2_1.setter
    def pulse2_1(self, pulse2_1):
        self._pulse2_1 = self.set_p2time("pulse1", self._pulse1, pulse2_1)[1]

    @property
    def pulse2_2(self):
        return self._pulse2_2

    @pulse2_2.setter
    def pulse2_2(self, pulse2_2):
        self._pulse2_2 = self.set_p2time("pulse2", self._pulse2, pulse2_2)[1]

    @property
    def cpmg(self):
        return self._cpmg

    @cpmg.setter
    def cpmg(self, cpmg):
        out = bytearray([self.control_byte["cpmg"]])
        cpmg_byte = self.intToByte(cpmg, 1)[0]
        p2st_byte = self.intToByte(self._p2start, 2)
        [out.insert(0, b) for b in p2st_byte[::-1]]
        [out.insert(0, b) for b in [0, cpmg_byte]]
        self.readcheck(out)
        self._cpmg = cpmg

    @property
    def p2start(self):
        return self._p2start * self.tstep

    @p2start.setter
    def p2start(self, value):
        p2num = int(np.round(value / self.tstep))
        out = bytearray([self.control_byte["cpmg"]])
        cpmg_byte = self.intToByte(self._cpmg, 1)[0]
        p2st_byte = self.intToByte(p2num, 2)
        [out.insert(0, b) for b in p2st_byte[::-1]]
        [out.insert(0, b) for b in [0, cpmg_byte]]
        self.readcheck(out)
        self._p2start = p2num

    @property
    def nutation_width(self):
        return self._nutation_width

    @nutation_width.setter
    def nutation_width(self, nut_wid):
        out = self.set_p2time("nutation", nut_wid, self._nutation_delay)
        self._nutation_width, self._nutation_delay = out

    @property
    def nutation_delay(self):
        return self._nutation_delay

    @nutation_delay.setter
    def nutation_delay(self, nut_del):
        out = self.set_p2time("nutation", self._nutation_width, nut_del)
        self._nutation_width, self._nutation_delay = out

    @property
    def pre_att(self):
        return self._pre_att

    @pre_att.setter
    def pre_att(self, value):
        assert (
            0 <= value <= 31.5
        ), f"Attenuation must be between 0 and 31.5 Ohms, got {value}"
        self.set_param("attenuators", int(value * 2))

    def freq_sweep(self, length):
        self.cpmg = 0
        self.block = 1
        self.pulse1 = 200
        self.pulse2 = 200
        self.delay = 5000
        self.period = 1.2 * length * 1e6  # Longer to allow for inaccurate scope framing
        return 0

    def pulse_freq_sweep(self, p):
        if p["port"] == 1:
            self.set_times(p["pulse1"], p["pulse2"], p["delay"], p["period"])
            self.set_times2(0, 0, p["delay"], p["period"])
        elif p["port"] == 2:
            dtime = p["delay"] + p["pulse1"] + p["pulse2"]
            self.set_times(0, 0, dtime, p["period"])
            self.set_times2(p["pulse1"], p["pulse2"], p["delay"], p["period"])
        elif p["port"] == 0:
            self.set_times(p["pulse1"], p["pulse2"], p["delay"], p["period"])
            self.set_times2(p["pulse1"], p["pulse2"], p["delay"], p["period"])
        self.cpmg = 1
        self.block = p["block"]
        self.pulse_block = p["pulse_block"]
        return 0

    def spin_echo(self, p):
        self.cpmg = p["cpmg"]
        self.block = p["block"]
        self.pulse_block = p["pulse_block"]
        self.nutation_delay = p["nutation_delay"]
        self.nutation_width = p["nutation_width"]
        self.period = p["period"]
        self.pre_att = p["pre_att"]
        if p["port"] == 1:
            self.pulse1 = p["pulse1"]
            self.pulse2 = p["pulse2"]
            self.delay = p["delay"]
            self.pulse2_1 = 0
            self.pulse2_2 = 0
            self.delay2 = p["delay"]
        else:
            dtime = p["delay"] + p["pulse1"] + p["pulse2"]
            self.pulse1 = 0
            self.pulse2 = 0
            self.delay = dtime
            self.pulse2_1 = p["pulse1"]
            self.pulse2_2 = p["pulse2"]
            self.delay2 = p["delay"]
        self.se_port = p["port"]
        self.phase_sub = int(p["phase_sub"])
        return 0

    def bimodal_spin_echo(self, p):
        self.cpmg = p["cpmg"]
        self.block = p["block"]
        self.pulse_block = p["pulse_block"]
        self.nutation_delay = p["nutation_delay"]
        self.nutation_width = p["nutation_width"]
        self.period = p["period"]
        self.pulse1 = p["pulse1_1"]
        self.pulse2 = p["pulse1_2"]
        self.delay = p["delay1"]
        self.pulse2_1 = p["pulse2_1"]
        self.pulse2_2 = p["pulse2_2"]
        self.delay2 = p["delay2"]
        self.p2start = p["p2start"]
        return 0
