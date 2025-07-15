"""
rfsoc2.py

Provides the low-level RFSoC pulse programming logic via Qick/QickASM. Includes experiment
program definitions like CPMG sequences, data acquisition routines, and signal post-processing.

Key Responsibilities:
- Define `CPMGProgram` class for building pulse programs with configurable delays and pulses.
- Run and decode RFSoC signal acquisitions.
- Perform Fourier and exponential fitting on time-domain signal data.

Key Interactions:
- Used by both `spinecho_scripts.py` and `pulsesweep_scripts.py` for measurement routines.
- Called from `server.py` to interact with real hardware.
"""

import sys
sys.path.append('../../')
import pyscan as ps
import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import rfft, rfftfreq
from qick import *
from qick.asm_v1 import QickRegisterManagerMixin
from collections import defaultdict

"""
I need to implement running each different kind of experiment. Can probably move everything into one class.
Make the delay, pulse length, nutation length, nutation delay all configurable (registers?). Look at how
qick-dawg does it.
"""

pi2_phase_list = [0, 180, 180, 0]
pi_phase_list = [90, 90, 270, 270]

def plot_mesh(x, y, z, xlab='', ylab='', zlab='', bar=True, ax=False, cax=False, **kwargs):
    A, B = np.meshgrid(x, y)
    if ax:
        c = ax.pcolormesh(A,  B, z, shading='auto', **kwargs)
        ax.set_xlabel(xlab)
        ax.set_ylabel(ylab)
        if bar:
            if isinstance(bar, type(ax)):
                ax.get_figure().colorbar(c, label=zlab, cax=bar)
            else:
                ax.get_figure().colorbar(c, label=zlab)
        else:
            plt.tight_layout()
    else:
        c = plt.pcolormesh(A,  B, z, shading='auto', **kwargs)
        plt.xlabel(xlab)
        plt.ylabel(ylab)
        if bar:
            plt.colorbar(c, label=zlab)
        else:
            plt.tight_layout()
    return c


pi2_phase_list = [0, 180, 180, 0]
pi_phase_list = [90, 90, 270, 270]

class CPMGProgram(QickRegisterManagerMixin, AveragerProgram):
    def trigger_no_off(self, pins=None, t=0, rp=0, r_out=31, width=0):
        """
        Adapted from qick-dawg. Currently only used for digital I/O pins, so I removed the rest.
        Sets the specified pin high starting at time t, lasting until the end of the cycle.
        
        Method that is a slight modification of qick.QickProgram.trigger().
        This method does not turn off the PMOD pins, thus also does not require a width parameter

        Parameters
        ----------
        pins : list of int
            List of marker pins to pulsem, i.e. PMOD channels.
            Use the pin numbers in the QickConfig printout.
        adc_trig_offset : int, optional
            Offset time at which the ADC is triggered (in tProc cycles)
        t : int, optional
            The number of tProc cycles at which the ADC trigger starts
        rp : int, optional
            Register page
        r_out : int, optional
            Register number
        """
        if pins is None:
            pins = []
        if not pins:
            raise RuntimeError("must pulse at least one pin")
            
        outdict = defaultdict(int)
        for pin in pins:
            pincfg = self.soccfg['tprocs'][0]['output_pins'][pin]
            outdict[pincfg[1]] |= (1 << pincfg[2])

        t_start = t
        if width:
            t_end = t_start + width

        for outport, out in outdict.items():
            self.regwi(rp, r_out, out, f'out = 0b{out:>016b}')
            self.seti(outport, rp, r_out, t_start, f'ch =0 out = ${r_out} @t = {t}')
            if width:
                self.seti(outport, rp, 0, t_end, f'ch =0 out = 0 @t = {t}')


    def initialize(self):
        cfg=self.cfg   
        res_ch = cfg["res_ch"]
        
        # Convert frequently-used times from us to cycles
        readout_length = [self.us2cycles(cfg["readout_length"], ro_ch=ch) for ch in cfg["ro_chs"]]
        length = self.us2cycles(cfg["pulse1_1"]/1000, gen_ch=res_ch)
        delay = self.us2cycles(cfg['delay']/1000-cfg['pulse1_1']/1000)
        tpi2 = self.us2cycles(cfg['pulse1_1']/1000)
        tstart = self.us2cycles(cfg['nutation_delay']/1000)

        # set the nyquist zone
        self.declare_gen(ch=res_ch, nqz=1)
        
        # configure the readout lengths and downconversion frequencies (ensuring it is an available DAC frequency)
        for n, ch in enumerate(cfg["ro_chs"]):
            self.declare_readout(ch=ch, length=readout_length[n],
                                 freq=cfg["freq"], gen_ch=res_ch)

        # convert frequency to DAC frequency (ensuring it is an available ADC frequency)
        freq = self.freq2reg(cfg["freq"],gen_ch=res_ch, ro_ch=cfg["ro_chs"][0])

        # set our output to be the default pulse register
        self.default_pulse_registers(ch=res_ch, style="const", freq=freq, phase=0)
        
        self.res_r_phase = self.get_gen_reg(res_ch, "phase")
        self.res_r_ph_pi2 = self.new_gen_reg(res_ch, init_val=pi2_phase_list[0], name="pi2_phase") 
        self.res_r_ph_pi = self.new_gen_reg(res_ch, init_val=pi_phase_list[0], name="pi_phase") 
        
        self.synci(200)  # give processor some time to configure pulses


    def cpmg(self, pulses=1, cycle=0, tstart=0):
        """
        Runs a Carr-Purcell pulse sequence with optional nutation pulse
        """
        # Set relevant times
        period = self.us2cycles(self.cfg["period"])
        res_ch = self.cfg["res_ch"]
        tpi2 = self.cfg["pulse1_1"]/1000
        tpi = self.cfg["pulse1_2"]/1000
        delay = self.cfg["delay"]/1000
        delay_pi2 = delay-tpi2
        delay_pi = 2*delay-tpi
        nutwidth = self.cfg["nutation_length"]/1000
        nutdelay = self.us2cycles(self.cfg["nutation_delay"]/1000)
        gain = self.cfg["gain"]
        
        # We want half the power for our pi/2 pulse, and this achieves that
        gain2 = gain if gain<10000 else gain-10000
        
        # In Loopback mode we want to start readout at the beginning of the pi/2 pulse
        # Otherwise we want to delay readout until the echo location
        offset = 0 if self.cfg["loopback"] else delay+(2*pulses-1)*delay#+(pulses-1)*(delay_pi)
        # Actually set the trigger offset, including empirically-determined delay of 0.25 us
        trig_offset = self.us2cycles(0.25+nutwidth+self.cfg["h_offset"]+offset)
        
        # If the nutation pulse width is greater than the minimum number of cycles, add it in
        nut_length = self.us2cycles(nutwidth, gen_ch=res_ch)
        if nut_length>2:
            self.set_pulse_registers(ch=self.cfg["res_ch"], gain=gain, phase=self.deg2reg(90), length=nut_length)
            self.pulse(ch=self.cfg["res_ch"])
        
        self.res_r_phase.set_to(self.deg2reg(pi2_phase_list[cycle], gen_ch=res_ch))
        
        # Wait the nutation delay time
        self.synci(nutdelay)
        
        # Tell the ADC when to trigger readout, based on the trigger offset defined above
        # If you uncomment the pins argument, it will also send a pulse on an I/O pin
        self.trigger(adcs=self.ro_chs,
                    # pins=[0],
                    adc_trig_offset=trig_offset)

        # pi/2 pulse
        self.set_pulse_registers(ch=res_ch, gain=gain2,
                                 length=self.us2cycles(tpi2, gen_ch=res_ch))
        self.pulse(ch=res_ch)
        
        self.res_r_phase.set_to(self.deg2reg(pi_phase_list[cycle], gen_ch=res_ch))
        
        # Delay between pi/2 and pi pulses
        self.synci(self.us2cycles(delay_pi2))
        
        # Add a configurable number of pi pulses, along with delays.
        # delay_pi is roughly twice delay_pi2, as the delay between pi pulses should be
        for n in np.arange(pulses):
            self.set_pulse_registers(ch=res_ch, gain=gain,
                                     length=self.us2cycles(tpi, gen_ch=res_ch))
            self.pulse(ch=self.cfg["res_ch"])

            self.synci(self.us2cycles(delay_pi))

        self.synci(self.us2cycles(delay_pi))
        
        self.wait_all()
        self.sync_all(period-trig_offset-nutdelay)
        

    def body(self):
        res_ch = self.cfg["res_ch"]
        nutwidth = self.cfg["nutation_length"]/1000
        nutdelay = self.cfg["nutation_delay"]/1000
        delay = self.cfg["delay"]/1000
        tpi = self.cfg["pulse1_2"]/1000
        tpi2 = self.cfg["pulse1_1"]/1000

        offset = 0 if self.cfg["loopback"] else (tpi2+delay+self.cfg["pulses"]*tpi+2*self.cfg["pulses"]-1)*(delay)
        # Actually set the trigger offset, including empirically-determined delay of 0.25 us
        trig_offset = self.us2cycles(nutwidth+nutdelay+self.cfg["h_offset"]+offset)
        
        # Trigger the switch-controlling pulse
        self.trigger_no_off(pins=[0])
        # Trigger the scope sync pulse
        self.trigger_no_off(t=trig_offset, pins=[1])
        self.synci(self.us2cycles(0.1))
        
        if self.cfg["single"]:
            self.cpmg(self.cfg["pulses"])
        else:
            for n in np.arange(4):
                self.cpmg(self.cfg["pulses"], n)


class DEERProgram(CPMGProgram):
    """
    Program to perform four-pulse DEER pulse sequences.
    I'm going to try to write it first with all pulses occurring on a single output,
    and if that doesn't work I'll use the second DAQ for the second frequency.
    """
    def initialize(self):
        cfg=self.cfg   
        res_ch = cfg["res_ch"]
        
        # Convert frequently-used times from us to cycles
        readout_length = [self.us2cycles(cfg["readout_length"], ro_ch=ch) for ch in cfg["ro_chs"]]
        length = self.us2cycles(cfg["pulse1_1"]/1000, gen_ch=res_ch)
        delay = self.us2cycles(cfg['delay']/1000-cfg['pulse1_1']/1000)
        tpi2 = self.us2cycles(cfg['pulse1_1']/1000)
        tstart = self.us2cycles(cfg['nutation_delay']/1000)

        # set the nyquist zone
        self.declare_gen(ch=res_ch, nqz=1)
        
        # configure the readout lengths and downconversion frequencies (ensuring it is an available DAC frequency)
        for n, ch in enumerate(cfg["ro_chs"]):
            self.declare_readout(ch=ch, length=readout_length[n],
                                 freq=cfg["freq"], gen_ch=res_ch)

        # convert frequency to DAC frequency (ensuring it is an available ADC frequency)
        freq1 = self.freq2reg(cfg["freq1"],gen_ch=res_ch, ro_ch=cfg["ro_chs"][0])
        freq2 = self.freq2reg(cfg["freq2"],gen_ch=res_ch, ro_ch=cfg["ro_chs"][0])

        # set our output to be the default pulse register
        self.default_pulse_registers(ch=res_ch, style="const", freq=freq1)
        
        self.synci(200)  # give processor some time to configure pulses


    def deer(self, ph1, ph2, tstart=0):
        """
        Runs a four-pulse DEER sequence with optional nutation pulse
        """
        # Set relevant times
        res_ch = self.cfg["res_ch"]
        tpi2 = self.cfg["pulse1_1"]/1000
        tpi = self.cfg["pulse1_2"]/1000
        delay = self.cfg["delay"]/1000
        delay_pi2 = delay-tpi2
        delay_pi = 2*delay-tpi
        tau = self.cfg["tau"]/1000-tpi
        gain = self.cfg["gain"]

        T = self.cfg["DEER_delay"]/1000
        first_tau = tau-T
        
        # convert second frequency to DAC frequency (ensuring it is an available ADC frequency)
        freq2 = self.freq2reg(cfg["freq2"],gen_ch=res_ch, ro_ch=cfg["ro_chs"][0])

        # We want half the power for our pi/2 pulse, and this achieves that
        gain2 = gain if gain<10000 else gain-10000
        
        # In Loopback mode we want to start readout at the beginning of the pi/2 pulse
        # Otherwise we want to delay readout until the second echo location
        offset = 0 if self.cfg["loopback"] else 2*delay+(2*tau)
        # Actually set the trigger offset, including empirically-determined delay of 0.25 us
        trig_offset = self.us2cycles(0.25+self.cfg["h_offset"]+offset)
        
        # Tell the ADC when to trigger readout, based on the trigger offset defined above
        # If you uncomment the pins argument, it will also send a pulse on an I/O pin
        self.trigger(adcs=self.ro_chs,
                    # pins=[0],
                    adc_trig_offset=trig_offset)

        # pi/2 pulse
        self.set_pulse_registers(ch=res_ch, gain=gain2, phase=ph1,
                                 length=self.us2cycles(tpi2, gen_ch=res_ch))
        self.pulse(ch=res_ch)
        
        # Delay between pi/2 and pi pulses
        self.synci(self.us2cycles(delay_pi2))
        
        # First pi pulse
        self.set_pulse_registers(ch=res_ch, gain=gain, phase=ph2,
                                 length=self.us2cycles(tpi, gen_ch=res_ch))
        self.pulse(ch=self.cfg["res_ch"])

        # Wait until first echo
        self.synci(self.us2cycles(delay_pi))

        # Send DEER pulse for second spin
        self.set_pulse_registers(ch=res_ch, gain=gain, phase=ph2, freq=freq2,
                                 length=self.us2cycles(tpi, gen_ch=res_ch))
        self.pulse(ch=self.cfg["res_ch"])

        # Delay between DEER pulse and second pi pulse
        self.synci(self.us2cycles(first_tau))

        # Second pi pulse
        self.set_pulse_registers(ch=res_ch, gain=gain, phase=ph2, freq=freq1,
                                 length=self.us2cycles(tpi, gen_ch=res_ch))
        self.pulse(ch=self.cfg["res_ch"])

        # Wait until second echo
        self.synci(self.us2cycles(tau))
        
        self.wait_all()
        self.sync_all(self.us2cycles(self.cfg["period"]))
        

    def body(self):
        self.trigger_no_off(pins=[0])
        self.synci(self.us2cycles(0.1))
        
        #if self.cfg['single']:
        self.deer(0, 0)


def iq_convert(soc, iq_list, pulses=1, ro=0, single=False, decimated=True):
    """
    When doing phase subtraction with multiple triggers, the subsequent pulse triggers
    are consecutive in the datastream, so we need to separately add the phase pulses
    for each trigger. For instance, with one pulse, the phase subtraction is
    0+3-1-2. With two, it would be [0+6-2-4, 1+7-3-5]. This simplifies to
    [(0+n)+(3*pulses+n)-(pulses+n)-(2*pulses+n) for n in np.arange(pulses)]
    """
    if decimated:
        if single:
            # if pulses<2:
            i, q = iq_list[:2]
            time = soc.cycles2us(np.arange(len(i)), ro_ch=ro)
            # else:
            #     i, q = iq_list[:][:2]
            #     time = soc.cycles2us(np.arange(len(i[0])), ro_ch=ro)
            x = np.abs(i+1j*q)
        else:
            # if pulses<2:
            i, q = iq_list[0]+iq_list[3]-iq_list[1]-iq_list[2]
            time = soc.cycles2us(np.arange(len(i)), ro_ch=ro)
            # else:
            #     ns = [[(0+n),(3*pulses+n),(pulses+n),(2*pulses+n)] for n in np.arange(pulses)]
            #     i, q = np.transpose([iq_list[n[0]]+iq_list[n[1]]-iq_list[n[2]]-iq_list[n[3]] for n in ns], axes=(1, 0, 2))
            #     time = soc.cycles2us(np.arange(len(i[0])), ro_ch=ro)
            x = np.abs(i+1j*q)
        return time, i, q, x
    else:
        # if pulses<2:
        imean, qmean = [iqs[0][0]+iqs[0][3]-iqs[0][1]-iqs[0][2] for iqs in iq_list]
        # else:
        #     ns = [[n*pulses, (n+1)*pulses] for n in [0, 3, 1, 2]]
        #     imean, qmean = [iqs[0][ns[0][0]:ns[0][1]]+iqs[0][ns[1][0]:ns[1][1]]-iqs[0][ns[2][0]:ns[2][1]]-iqs[0][ns[3][0]:ns[3][1]]
        #                      for iqs in iq_list]
        xmean = np.abs(imean+1j*qmean)
        return imean, qmean, xmean
    
    
def fourier_signal(d, fstart=1, fstop=50):
    d.fourier = [np.abs(rfft(sig)) for sig in [d.x, d.i, d.q]]
    d.fourier.append(np.sqrt(d.fourier[:][1]**2+d.fourier[:][2]**2))
    d.ffreqs = rfftfreq(len(d.x), d.time[1]-d.time[0])
    flen = len(d.fourier)
    d.ffit = np.zeros((flen, 4))
    for n in range(flen):
        try:
            lordat = np.array([d.ffreqs, -d.fourier[n]])[:, fstart:fstop]
            d.ffit[n] = ps.lor_fit(lordat)[0]
        except:
            0
    d.xfamp, d.ifamp, d.qfamp, d.xxfamp = [-fit[1] for fit in d.ffit]
    d.ffdet = d.ffit[1][-1]
    d.ffdet2 = d.ffit[2][-1]
    d.ffdetx = d.ffit[3][-1]
    # fwin = list(d.ffreqs[[fstart, fstop]])
    # int_out = integrate_echo(d.ffreqs, d.fourier,
    #                             backsub='linear', prewin=fwin)
    # [d.xfint, d.ifint, d.qfint, d.xxfint] = int_out
     # d.xfmean, d.v1fmean, d.v2fmean, d.xxfmean] = int_out
    return d


def measure_decay(parameters, soc, d=0, ro=0, progress=False):
    reps = parameters['ave_reps']
    pulses = parameters['pulses']
    if isinstance(d, int):
        d = ps.ItemAttribute()
    iq_list = sread(parameters, soc, progress)

    d.time, d.i, d.q, d.x = iq_convert(soc, iq_list,
                                     pulses=pulses,
                                     ro=ro,
                                     single=True,
                                     decimated=True)

    if reps>1:
        for n in np.arange(reps-1):
            iq_list = safe_read(parameters, soc, progress)
            _, i, q, x = iq_convert(soc, iq_list,
                                     pulses=pulses,
                                     ro=ro,
                                     single=True,
                                     decimated=True)
            d.i += i
            d.q += q
            d.x += x
        d.i = d.i/reps
        d.q = d.q/reps
        d.x = d.x/reps
    
    d.fit, d.fiterr, d.R2b = ps.exp_fit_norange(np.array([d.time, d.x]),
                                         parameters['freq'], 1)
    d.Q = d.fit[-1]
    d.Qerr = d.fiterr[-1]
    
    fourier_signal(d)

    d.time += parameters['h_offset']

    return d


def measure_phase(parameters, soc, d=0, ro=0, progress=False):
    reps = parameters['ave_reps']
    pulses = parameters['pulses']
    if isinstance(d, int):
        d = ps.ItemAttribute()
    iq_list = safe_read(parameters, soc, progress)

    d.time, d.i, d.q, d.x = iq_convert(soc, iq_list,
                                     pulses=pulses,
                                     ro=ro,
                                     single=parameters['single'],
                                     decimated=True)

    if reps>1:
        for n in np.arange(reps-1):
            iq_list = safe_read(parameters, soc, progress)
            _, i, q, x = iq_convert(soc, iq_list,
                                     pulses=pulses,
                                     ro=ro,
                                     single=parameters['single'],
                                     decimated=True)
            d.i += i
            d.q += q
            d.x += x
        d.i = d.i/reps
        d.q = d.q/reps
        d.x = d.x/reps

    d.imean, d.qmean, d.xmean = [np.mean(sig) for sig in [d.i, d.q, d.x]]

    d.time += parameters['h_offset']
    
    return d


def acquire_phase(parameters, soc, d=0, ro=0, progress=False):
    reps = parameters['ave_reps']
    pulses = parameters['pulses']
    parameters['single'] = False
    nreps = parameters['soft_avgs']
    parameters['reps'] = nreps
    parameters['soft_avgs'] = 1
    if isinstance(d, int):
        d = ps.ItemAttribute()
    prog = CPMGProgram(soc, parameters)
    iq_lists = prog.acquire(soc, progress=progress)

    d.imean, d.qmean, d.xmean = iq_convert(soc, iq_lists,
                                     pulses=pulses,
                                     ro=ro,
                                     single=prog.cfg['single'],
                                     decimated=False)

    if reps>1:
        for n in np.arange(reps-1):
            iq_lists = prog.acquire(soc, progress=progress)

            imean, qmean, xmean = iq_convert(soc, iq_lists,
                                     pulses=pulses,
                                     ro=ro,
                                     single=prog.cfg['single'],
                                     decimated=False)
            d.imean += imean
            d.qmean += qmean
            d.xmean += xmean
        d.imean = d.imean/reps
        d.qmean = d.qmean/reps
        d.xmean = d.xmean/reps

    parameters['soft_avgs'] = nreps
    parameters['reps'] = 1
    return d


def sread(parameters, soc, progress):
    prog = CPMGProgram(soc, parameters)
    try:
        iq_list = prog.acquire_decimated(soc, progress=progress)[0]
    except RuntimeError:
        soc.__init__()
        iq_list = prog.acquire_decimated(soc, progress=progress)[0]
    return iq_list


# def safe_read(prog, soc, progress=False):
def safe_read(parameters, soc, progress=False):
    if parameters['single']:
        iq_list = sread(parameters, soc, progress)
    else:
        iq_list = []
        # TODO: Look into using a QickSweep object for doing this phase sweeping
        for n in np.arange(4):
            parameters['pi2_phase'] = pi2_phase_list[n]
            parameters['pi_phase'] = pi_phase_list[n]
            iq_list.append(sread(parameters, soc, progress))
    return iq_list
