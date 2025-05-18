# -*- coding: utf-8 -*-
"""
Created on Dec 22 2020

@author: Charles Collett
"""


from .instrument_driver import InstrumentDriver
import struct
import numpy as np

freq = .1005
tstep = 1/freq

# period_shift = 1 << 16
period_shift = 1


class ice40HX8K(InstrumentDriver):
    '''
    Class to control Lattice ice40HX8K FPGA (iceboard)

    '''

    def __init__(self, instrument):

        super().__init__(instrument)

#         self.instrument.close()
        self._delay = 200*tstep
        self._period = 1*period_shift*tstep
        self._pulse1 = 30*tstep
        self._pulse2 = 30*tstep
        self._cpmg = 1
        self._pump = 1
        self._block = 1
        self._pulse_block = 250
        self._pulse_block_off = 500
        
    control_byte = {
        'delay': 0,
        'period': 1,
        'pulse1': 2,
        'pulse2': 3,
        'toggle': 4,
        'cpmg': 5,
        'attenuators': 6
        }
    
    pack_fmt = {
        1: 'B',
        2: 'H',
        4: 'I'
    }

    freq = freq
    tstep = tstep


    def readcheck(self, out):
#         self.instrument.open()
        self.instrument.write(out)
        check = self.read()
#         self.instrument.close()
        out_check = np.sum(out[:-1])
        if out_check > 255:
            out_check = out_check - 256
        in_check = struct.unpack('B', check)[0]
        assert out_check-in_check==0
        return out
    

    def intToByte(self, num, nBytes=4):
        unpack_str="{}B".format(nBytes)
        pack_str = self.pack_fmt[nBytes]
        return struct.unpack(unpack_str, struct.pack(pack_str, num))


    def set_param(self, param, num):
        out = bytearray([self.control_byte[param]])
        # if (param=='period'):
        #     num = int(np.round(num/period_shift))
        #     ret = num*period_shift
        # else:
        #     ret = num
        ret = num
        [out.insert(0, b) for b in self.intToByte(num)[::-1]]
        return self.readcheck(out)


    def set_time(self, param, t_ns):
        num = int(np.round(t_ns/self.tstep))
        self.set_param(param, num)
        return num*self.tstep


    def set_p2time(self, param, t_ns1, t_ns2):
        num1 = int(np.round(t_ns1/self.tstep))
        num2 = int(np.round(t_ns2/self.tstep))
        nums = num1 + (num2 << 16)
        self.set_param(param, nums)
        return (num1*self.tstep, num2*self.tstep)
    
    
    def set_times(self, pulse1, pulse2, delay, period):
        self.pulse1 = pulse1
        self.pulse2 =pulse2
        self.delay = delay
        self.period = period
    

    def toggle(self, pump=1, block=1,
               pulse_block=200, pulse_block_off=1500):
        pblock = int(np.round(pulse_block/self.tstep))
        pblock_off = int(np.round(pulse_block_off/self.tstep))
        out = bytearray([self.control_byte['toggle']])
        pbo_byte = self.intToByte(pblock_off, 2)
        [out.insert(0, b) for b in pbo_byte[::-1]]
        out.insert(0, self.intToByte(pblock, 1)[0])
        out.insert(0, self.intToByte(block, 1)[0])
        return self.readcheck(out)

    @property
    def pump(self):
        return self._pump

    @pump.setter
    def pump(self, pump):
        self.toggle(pump, self._block, self._pulse_block, self._pulse_block_off)
        self._pump = pump

    @property
    def block(self):
        return self._block

    @block.setter
    def block(self, block):
        self.toggle(self._pump, block, self._pulse_block, self._pulse_block_off)
        self._block = block

    @property
    def pulse_block(self):
        return self._pulse_block*self.tstep

    @pulse_block.setter
    def pulse_block(self, pulse_block):
        num = int(np.round(pulse_block/self.tstep))
        self.toggle(self._pump, self._block, pulse_block, self._pulse_block_off)
        self._pulse_block = num

    @property
    def pulse_block_off(self):
        return self._pulse_block_off*self.tstep

    @pulse_block_off.setter
    def pulse_block_off(self, pulse_block_off):
        num = int(np.round(pulse_block_off/self.tstep))
        self.toggle(self._pump, self._block, self._pulse_block, pulse_block_off)
        self._pulse_block_off = num

    @property
    def delay(self):
        return self._delay

    @delay.setter
    def delay(self, delay):
        self._delay = self.set_time('delay', delay)

    @property
    def period(self):
        return self._period

    @period.setter
    def period(self, period):
        self._period = self.set_time('period', period)

    @property
    def pulse1(self):
        return self._pulse1

    @pulse1.setter
    def pulse1(self, pulse1):
        self._pulse1 = self.set_time('pulse1', pulse1)

    @property
    def pulse2(self):
        return self._pulse2

    @pulse2.setter
    def pulse2(self, pulse2):
        self._pulse2 = self.set_time('pulse2', pulse2)
    
    @property
    def cpmg(self):
        return self._cpmg

    @cpmg.setter
    def cpmg(self, cpmg):
        out = bytearray([self.control_byte['cpmg']])
        cpmg_byte = self.intToByte(cpmg, 1)[0]
        [out.insert(0, b) for b in [0, 0, 0, cpmg_byte]]
        self.readcheck(out)
        self._cpmg = cpmg


    def freq_sweep(self, length):
        self.cpmg = 0
        self.block = 1
        self.pulse1 = 200
        self.pulse2 = 200
        self.delay = 5000
        self.period = 1.2*length*1e6 # Longer to allow for inaccurate scope framing 
