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

sys.path.append("../../")
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


def plot_mesh(
    x, y, z, xlab="", ylab="", zlab="", bar=True, ax=False, cax=False, **kwargs
):
    A, B = np.meshgrid(x, y)
    if ax:
        c = ax.pcolormesh(A, B, z, shading="auto", **kwargs)
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
        c = plt.pcolormesh(A, B, z, shading="auto", **kwargs)
        plt.xlabel(xlab)
        plt.ylabel(ylab)
        if bar:
            plt.colorbar(c, label=zlab)
        else:
            plt.tight_layout()
    return c


class CPMGProgram(QickRegisterManagerMixin, AveragerProgram):
    def trigger_no_off(
        self, adcs=None, pins=None, adc_trig_offset=0, t=0, rp=0, r_out=31
    ):
        """
        Adapted from qick-dawg.
        Method that is a slight modificaiton of qick.QickProgram.trigger().
        This method does not turn off the PMOD pins, thus also does not require a width parameter

        Parameters
        ----------
        adcs : list of int
            List of readout channels to trigger (index in 'readouts' list) [0], [1], or [0, 1]
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
        if adcs is None:
            adcs = []
        if pins is None:
            pins = []
        if not adcs and not pins:
            raise RuntimeError("must pulse at least one ADC or pin")

        outdict = defaultdict(int)
        for ro in adcs:
            rocfg = self.soccfg["readouts"][ro]
            outdict[rocfg["trigger_port"]] |= 1 << rocfg["trigger_bit"]
            # update trigger count for this readout
            self.ro_chs[ro]["trigs"] += 1
        for pin in pins:
            pincfg = self.soccfg["tprocs"][0]["output_pins"][pin]
            outdict[pincfg[1]] |= 1 << pincfg[2]

        t_start = t
        if adcs:
            t_start += adc_trig_offset
            # update timestamps with the end of the readout window
            for adc in adcs:
                ts = self.get_timestamp(ro_ch=adc)
                if t_start < ts:
                    print(
                        "Readout time %d appears to conflict with previous readout ending at %f?"
                        % (t, ts)
                    )
                # convert from readout clock to tProc clock
                ro_length = self.ro_chs[adc]["length"]
                ro_length *= (
                    self.soccfg["fs_proc"] / self.soccfg["readouts"][adc]["f_fabric"]
                )
                self.set_timestamp(t_start + ro_length, ro_ch=adc)

        for outport, out in outdict.items():
            self.regwi(rp, r_out, out, f"out = 0b{out:>016b}")
            self.seti(outport, rp, r_out, t_start, f"ch =0 out = ${r_out} @t = {t}")
            # self.seti(outport, rp, 0, t_end, f'ch =0 out = 0 @t = {t}')

    def initialize(self):
        cfg = self.cfg
        res_ch = cfg["res_ch"]

        readout_length = [
            self.us2cycles(cfg["readout_length"], ro_ch=ch) for ch in cfg["ro_chs"]
        ]
        length = self.us2cycles(cfg["pulse1_1"] / 1000, gen_ch=res_ch)
        delay = self.us2cycles(cfg["delay"] / 1000 - cfg["pulse1_1"] / 1000)
        tpi2 = self.us2cycles(cfg["pulse1_1"] / 1000)
        tstart = self.us2cycles(cfg["nutation_delay"] / 1000)

        # set the nyquist zone
        self.declare_gen(ch=res_ch, nqz=1)

        # configure the readout lengths and downconversion frequencies (ensuring it is an available DAC frequency)
        for n, ch in enumerate(cfg["ro_chs"]):
            self.declare_readout(
                ch=ch, length=readout_length[n], freq=cfg["freq"], gen_ch=res_ch
            )

        # convert frequency to DAC frequency (ensuring it is an available ADC frequency)
        freq = self.freq2reg(cfg["freq"], gen_ch=res_ch, ro_ch=cfg["ro_chs"][0])

        self.default_pulse_registers(ch=res_ch, style="const", freq=freq)

        self.delay_register = self.new_gen_reg(res_ch, name="delay", init_val=delay)

        self.tpi2_register = self.new_gen_reg(res_ch, name="tpi2", init_val=tpi2)

        self.nutation_register = self.new_gen_reg(
            res_ch, name="tstart", init_val=tstart
        )

        self.synci(200)  # give processor some time to configure pulses

    def cpmg(self, ph1, ph2, phdel=0, pulses=1, tstart=0):
        res_ch = self.cfg["res_ch"]
        tpi2 = self.cfg["pulse1_1"] / 1000
        tpi = self.cfg["pulse1_2"] / 1000
        delay = self.cfg["delay"] / 1000
        delay_pi2 = delay - tpi2
        delay_pi = 2 * delay - tpi
        nutwidth = self.cfg["nutation_length"] / 1000
        nutdelay = self.cfg["nutation_delay"] / 1000
        gain = self.cfg["gain"]
        gain2 = gain if gain < 10000 else gain - 10000
        offset = (
            0 if self.cfg["loopback"] else delay + (2 * pulses - 1) * delay
        )  # +(pulses-1)*(delay_pi)
        trig_offset = self.us2cycles(0.25 + nutwidth + self.cfg["h_offset"] + offset)
        nut_length = self.us2cycles(nutwidth, gen_ch=res_ch)
        if nut_length > 2:
            self.set_pulse_registers(
                ch=self.cfg["res_ch"], gain=gain, phase=90, length=nut_length
            )
            self.pulse(ch=self.cfg["res_ch"])

        # self.sync(self.nutation_register.page, self.nutation_register.addr)
        self.synci(self.us2cycles(nutdelay))

        self.trigger(
            adcs=self.ro_chs,
            # pins=[0],
            adc_trig_offset=trig_offset,
        )

        self.set_pulse_registers(
            ch=res_ch, gain=gain2, phase=ph1, length=self.us2cycles(tpi2, gen_ch=res_ch)
        )
        self.pulse(ch=res_ch)

        # self.sync(self.delay_register.page, self.delay_register.addr)
        self.synci(self.us2cycles(delay_pi2))

        for n in np.arange(pulses):

            # self.sync(self.delay_register.page, self.delay_register.addr)
            self.set_pulse_registers(
                ch=res_ch,
                gain=gain,
                phase=ph2,
                length=self.us2cycles(tpi, gen_ch=res_ch),
            )
            self.pulse(ch=self.cfg["res_ch"])

            self.synci(self.us2cycles(delay_pi))

            # self.trigger(adcs=self.ro_chs)#,
            # pins=[0])#,
            # adc_trig_offset=trig_offset)
            # self.wait_all(
            # self.sync_all(0)#self.us2cycles(2*delay-tpi2-1.2))#-self.cfg['readout_length
            # self.sync(self.delay_register.page, self.delay_register.addr)
            # self.sync(self.tpi2_register.page, self.tpi2_register.addr)

        self.synci(self.us2cycles(delay_pi))

        self.wait_all()
        self.sync_all(self.us2cycles(self.cfg["period"]))

    def body(self):
        phase1 = [
            self.deg2reg(self.cfg["pi2_phase"] + ph, gen_ch=self.cfg["res_ch"])
            for ph in [0, 180, 180, 0]
        ]
        phase2 = [
            self.deg2reg(self.cfg["pi_phase"] + ph, gen_ch=self.cfg["res_ch"])
            for ph in [0, 0, 180, 180]
        ]
        phase_delta = self.deg2reg(self.cfg["cpmg_phase"], gen_ch=self.cfg["res_ch"])

        self.trigger_no_off(pins=[0])
        self.synci(self.us2cycles(0.1))

        if self.cfg["single"]:
            self.cpmg(phase1[0], phase2[0], phase_delta, self.cfg["pulses"])
        else:
            [
                self.cpmg(phase1[n], phase2[n], phase_delta, self.cfg["pulses"])
                for n in np.arange(4)
            ]


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
            x = np.abs(i + 1j * q)
        else:
            # if pulses<2:
            i, q = iq_list[0] + iq_list[3] - iq_list[1] - iq_list[2]
            time = soc.cycles2us(np.arange(len(i)), ro_ch=ro)
            # else:
            #     ns = [[(0+n),(3*pulses+n),(pulses+n),(2*pulses+n)] for n in np.arange(pulses)]
            #     i, q = np.transpose([iq_list[n[0]]+iq_list[n[1]]-iq_list[n[2]]-iq_list[n[3]] for n in ns], axes=(1, 0, 2))
            #     time = soc.cycles2us(np.arange(len(i[0])), ro_ch=ro)
            x = np.abs(i + 1j * q)
        return time, i, q, x
    else:
        # if pulses<2:
        imean, qmean = [
            iqs[0][0] + iqs[0][3] - iqs[0][1] - iqs[0][2] for iqs in iq_list
        ]
        # else:
        #     ns = [[n*pulses, (n+1)*pulses] for n in [0, 3, 1, 2]]
        #     imean, qmean = [iqs[0][ns[0][0]:ns[0][1]]+iqs[0][ns[1][0]:ns[1][1]]-iqs[0][ns[2][0]:ns[2][1]]-iqs[0][ns[3][0]:ns[3][1]]
        #                      for iqs in iq_list]
        xmean = np.abs(imean + 1j * qmean)
        return imean, qmean, xmean


def fourier_signal(d, fstart=1, fstop=50):
    d.fourier = [np.abs(rfft(sig)) for sig in [d.x, d.i, d.q]]
    d.fourier.append(np.sqrt(d.fourier[:][1] ** 2 + d.fourier[:][2] ** 2))
    d.ffreqs = rfftfreq(len(d.x), d.time[1] - d.time[0])
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


def measure_decay(config, soc, d=0, ro=0, progress=False):
    reps = config["ave_reps"]
    pulses = config["pulses"]
    if isinstance(d, int):
        d = ps.ItemAttribute()
    prog = CPMGProgram(soc, parameters)
    iq_list = safe_read(prog, soc, progress)

    d.time, d.i, d.q, d.x = iq_convert(
        soc, iq_list, pulses=pulses, ro=ro, single=prog.cfg["single"], decimated=True
    )

    if reps > 1:
        for n in np.arange(reps - 1):
            iq_list = safe_read(prog, soc, progress)
            _, i, q, x = iq_convert(
                soc,
                iq_list,
                pulses=pulses,
                ro=ro,
                single=prog.cfg["single"],
                decimated=True,
            )
            d.i += i
            d.q += q
            d.x += x
        d.i = d.i / reps
        d.q = d.q / reps
        d.x = d.x / reps

    d.fit, d.fiterr, d.R2b = ps.exp_fit_norange(
        np.array([d.time, d.x]), prog.cfg["freq"], 1
    )
    d.Q = d.fit[-1]
    d.Qerr = d.fiterr[-1]

    fourier_signal(d)

    d.time += prog.cfg["h_offset"]

    return d


def measure_phase(config, soc, d=0, ro=0, progress=False):
    reps = config["ave_reps"]
    pulses = config["pulses"]
    if isinstance(d, int):
        d = ps.ItemAttribute()
    prog = CPMGProgram(soc, parameters)
    iq_list = safe_read(prog, soc, progress)

    d.time, d.i, d.q, d.x = iq_convert(
        soc, iq_list, pulses=pulses, ro=ro, single=prog.cfg["single"], decimated=True
    )

    if reps > 1:
        for n in np.arange(reps - 1):
            iq_list = safe_read(prog, soc, progress)
            _, i, q, x = iq_convert(
                soc,
                iq_list,
                pulses=pulses,
                ro=ro,
                single=prog.cfg["single"],
                decimated=True,
            )
            d.i += i
            d.q += q
            d.x += x
        d.i = d.i / reps
        d.q = d.q / reps
        d.x = d.x / reps

    d.imean, d.qmean, d.xmean = [np.mean(sig) for sig in [d.i, d.q, d.x]]

    d.time += prog.cfg["h_offset"]

    return d


def acquire_phase(config, soc, d=0, ro=0, progress=False):
    reps = config["ave_reps"]
    pulses = config["pulses"]
    config["single"] = False
    nreps = config['soft_avgs']
    config['reps'] = nreps
    config['soft_avgs'] = 1
    if isinstance(d, int):
        d = ps.ItemAttribute()
    prog = CPMGProgram(soc, parameters)
    iq_lists = prog.acquire(soc, progress=progress)

    d.imean, d.qmean, d.xmean = iq_convert(
        soc, iq_lists, pulses=pulses, ro=ro, single=prog.cfg["single"], decimated=False
    )

    if reps > 1:
        for n in np.arange(reps - 1):
            iq_lists = prog.acquire(soc, progress=progress)

            imean, qmean, xmean = iq_convert(
                soc,
                iq_lists,
                pulses=pulses,
                ro=ro,
                single=prog.cfg["single"],
                decimated=False,
            )
            d.imean += imean
            d.qmean += qmean
            d.xmean += xmean
        d.imean = d.imean / reps
        d.qmean = d.qmean / reps
        d.xmean = d.xmean / reps

    config['soft_avgs'] = nreps
    config['reps'] = 1
    return d


def safe_read(prog, soc, progress=False):
    try:
        iq_list = prog.acquire_decimated(soc, progress=progress)[0]
    except RuntimeError:
        soc.__init__()
        iq_list = prog.acquire_decimated(soc, progress=progress)[0]
    return iq_list
