import sys
sys.path.append('../')
from scipy.integrate import simps
from time import sleep, time
from scipy.fft import rfft, rfftfreq
import numpy as np
import pyscan as ps

defwin = [1e-1, 4e-1]


def change_trigger_delta(devices, old_time, new_time):#, delay_change=0):
    time_delta = (new_time-old_time)/1e9
    devices.scope.trigger_delay += time_delta
    # devices.scope.xdelay -= delay_change


def nochange(devices, phase, ave=4, sltime=0.3, offset=[False, 0],
             **kwargs):
    return 0
    
    
def change_phase(devices, phase, ave=4, sltime=0.3, offset=[False, 0],
                 **kwargs):
    devices.synth.instrument[1].phase = (phase)
    if offset[0]:
        n = offset[1]
        devices.scope.channel1_offset = offset[0][n]
#         devices.scope.channel1_scale = offset[1]
    devices.scope.average = 1
    sleep(0.1)
    devices.scope.average = ave
    sleep(sltime)
    
    
def change_delay(devices, delay, ave=4, sltime=0.3, port=1, **kwargs):
    if port==2:
        old_delay = devices.fpga.delay2
        devices.fpga.delay = delay+devices.fpga.pulse2_1+devices.fpga.pulse2_2
        devices.fpga.delay2 = delay
    else:
        old_delay = devices.fpga.delay
        devices.fpga.delay = delay
        devices.fpga.delay2 = delay
    change_trigger_delta(devices, old_delay, delay)
    devices.scope.average = 1
    sleep(0.1)
    devices.scope.average = ave
    sleep(sltime)

    
def delay_change(devices, delay, port):
    if port==2:
        old_delay = devices.fpga.delay2
        devices.fpga.delay = delay+devices.fpga.pulse2_1+devices.fpga.pulse2_2
        devices.fpga.delay2 = delay
    else:
        old_delay = devices.fpga.delay
        devices.fpga.delay = delay
        devices.fpga.delay2 = delay
    change_trigger_delta(devices, 2*old_delay, 2*delay)


def change_nutation(devices, width, ave=4, sltime=0.3):
    devices.fpga.nutation_width = (width)
    devices.scope.average = 1
    sleep(0.1)
    devices.scope.average = ave
    sleep(sltime)


def integrate_echo(times, data, alldat=False, backsub=False, prewin=False):
    """Prompts for the integration window, and then integrates all the data
    in that window. If 'alldat' is True, all the datasets are shown in the
    integration prompt, otherwise only the first is shown. If 'backsub' is
    'linear', a linear fit is made between the integration endpoints and
    subtracted from the data before integrating; if it is 'end', the last 50
    points are averaged and subtracted from the data before integrating.
    If 'prewin' is not false it needs to be a two-element list with the
    window limits, in which case the integration prompt doesn't run."""
    # Pick the integration window values by inspecting the data and seeing
    # what window works
    lower_limit, upper_limit = prewin or int_window(times, data, alldat)
    # Check if the limits are entirely outside of our times, and if so
    # set them to be the existing time boundaries
    if lower_limit>times[-1] or upper_limit<times[0]:
        lower_limit, upper_limit = times[[0, -1]]
    lims = [np.abs(times-n).argmin() for n in [lower_limit, upper_limit]]
    tlim = times[lims[0]:lims[1]]
    
    # Integrate the data over the window
    if backsub=='linear':
        tdiff = tlim[-1]-tlim[0]
        limrange = [np.arange(lims[0], lims[0]+10),
                    np.arange(lims[1]-10, lims[1])]
        slope = np.array([(np.mean(dat[limrange[1]])-
                           np.mean(dat[limrange[0]]))/tdiff
                          for dat in data])
        intercept = np.array([np.mean(data[n][limrange[0]])-
                              slope[n]*tlim[0] for n in np.arange(len(slope))])
        dat_sub = np.array([data[n]-(slope[n]*times+intercept[n])
                            for n in np.arange(len(slope))])
        se_area = [simps(d[lims[0]:lims[1]], tlim)
                            for d in dat_sub]
        # se_mean = [np.mean(d[lims[0]:lims[1]]) for d in dat_sub]
    elif backsub=='end':
        dat_sub = np.array([dat-np.mean(dat[50:]) for dat in data])
        se_area = [simps(d[lims[0]:lims[1]], tlim)
                            for d in dat_sub]
        # se_mean = [np.mean(d[lims[0]:lims[1]]) for d in dat_sub]
    else:
        se_area = [simps(d[lims[0]:lims[1]], tlim)
                            for d in data]
        # se_mean = [np.mean(d[lims[0]:lims[1]]) for d in data]
    return np.array(se_area)
    
    
def fourier_signal(d, fstart=3, fstop=100):
    d.fourier = [np.abs(rfft(sig)) for sig in [d.xsub, d.v1sub, d.v2sub]]
    d.fourier.append(np.sqrt(d.fourier[:][1]**2+d.fourier[:][2]**2))
    d.ffreqs = rfftfreq(len(d.xsub), d.time[1]-d.time[0])
    flen = len(d.fourier)
    d.ffit = np.zeros((flen, 4))
    for n in range(flen):
        try:
            lordat = np.array([d.ffreqs, -d.fourier[n]])[:, fstart:fstop]
            d.ffit[n] = lor_fit(lordat)[0]
        except:
            0
    d.xfamp, d.v1famp, d.v2famp, d.xxfamp = [-fit[1] for fit in d.ffit]
    d.ffdet = d.ffit[1][-1]
    d.ffdet2 = d.ffit[2][-1]
    d.ffdetx = d.ffit[3][-1]
    fwin = list(d.ffreqs[[fstart, fstop]])
    int_out = integrate_echo(d.ffreqs, d.fourier,
                                backsub='linear', prewin=fwin)
    [d.xfint, d.v1fint, d.v2fint, d.xxfint] = int_out
     # d.xfmean, d.v1fmean, d.v2fmean, d.xxfmean] = int_out
    return d
    
    
def fourier_signals(d, fstart=3, fstop=100):
    ns = range(len(d.xsub))
    d.fourier = np.array([[np.abs(rfft(sig))
                           for sig in [d.xsub[n], d.v1sub[n], d.v2sub[n]]]
                          for n in ns])
    d.ffreqs = np.array([rfftfreq(len(d.xsub[n]), d.time[n][1]-d.time[n][0])
                         for n in ns])
    d.ffit = np.zeros((len(d.xsub), 3, 4))
    for n in ns:
        for i in range(3):
            try:
                lordat = np.array([d.ffreqs[n], -d.fourier[n][i]])[:,
                                                                   fstart:fstop]
                d.ffit[n][i] = lor_fit(lordat)[0]
            except:
                d.ffit[n][i] = np.zeros(4)
    d.xfamp = np.array([-fit[0][1] for fit in d.ffit])
    d.v1famp = np.array([-fit[1][1] for fit in d.ffit])
    d.v2famp = np.array([-fit[2][1] for fit in d.ffit])
    d.ffdet = np.array([fit[1][-1] for fit in d.ffit])
    d.ffdet2 = np.array([fit[2][-1] for fit in d.ffit])
    return d


def sback(sig, backnum=100):
    return sig-np.mean(sig[-backnum:])


def process_se(d, win, backnum=100, detune=0):
    v1usub = sback(d.v1up)
    v1dsub = sback(d.v1down)
    v2usub = sback(d.v2up)
    v2dsub = sback(d.v2down)
    d.v1sub = v1usub-v1dsub
    d.v2sub = v2usub-v2dsub
#     v1int = simps(v1sub, time)
    d.xup = np.sqrt(v1usub**2+v2usub**2)
    d.xdown = np.sqrt(v1dsub**2+v2dsub**2)
    d.xsub = np.sqrt(d.v1sub**2+d.v2sub**2)
    
#     d.xup1 = np.sqrt((d.v1up)**2+(d.v2up)**2)
#     d.xdown1 = np.sqrt((d.v1down)**2+(d.v2down)**2)
#     d.xup1 = d.xup1-np.mean(d.xup1[-20:])
#     d.xdown1 = d.xdown1-np.mean(d.xdown1[-20:])
    d.xsub1 = d.xup-d.xdown

    int_out = integrate_echo(d.time, [d.v1sub, d.v2sub, d.xsub, d.xsub1],
                                backsub='linear', prewin=win)
    [d.v1int, d.v2int, d.xint, d.xint1] = int_out
     # d.v1mean, d.v2mean, d.xmean, d.x1mean] = int_out
    d = fourier_signal(d)
    
    return d


def subback(subfunc, args, devices, ave,
            sltime=0, lims=defwin, reps=1, detune=0, d=0, port=1,
            **kwargs):
    if isinstance(d, int):
        d = ps.ItemAttribute()
    period = devices.fpga.period/1e9
    delay = devices.fpga.delay2/1e9 if port==2 else devices.fpga.delay/1e9
    # win = [delay+lims[0]/1e6, delay+lims[1]/1e6]
    win = [lims[0]/1e6, lims[1]/1e6]
    
    if not sltime:
#        sltime = period*ave if period>0.1 else 2*period*ave
        sltime = ave/1000 if period<0.001 else period*ave
#    sltime = sltime if sltime>=0.01 else 0
    subfunc(devices, args[0], ave=ave, sltime=sltime, port=port, **kwargs)
    [[d.time, d.v1down],
     [_, d.v2down]] = devices.scope.read_screen(0, init=False)
    if reps>1:
        for n in range(reps-1):
            sleep(sltime)
            [[_, v1d], [_, v2d]] = devices.scope.read_screen(0, init=False)
            d.v1down = (v1d+d.v1down)
            d.v2down = (v2d+d.v2down)
        d.v1down = d.v1down/reps
        d.v2down = d.v2down/reps
    subfunc(devices, args[1], ave=ave, sltime=sltime, port=port, **kwargs)
    [[_, d.v1up], [_, d.v2up]] = devices.scope.read_screen(0, init=False)
    if reps>1:
        for n in range(reps-1):
            sleep(sltime)
            [[_, v1u], [_, v2u]] = devices.scope.read_screen(0, init=False)
            d.v1up = (v1u+d.v1up)
            d.v2up = (v2u+d.v2up)
        d.v1up = d.v1up/reps
        d.v2up = d.v2up/reps
    
    d = process_se(d, win, detune=detune)
    #d.xsub, d.v1sub, d.v2sub = [sig/2 for sig in [d.xsub, d.v1sub, d.v2sub]]
    d.win = win
    
    return d


def subback_phase(devices, ave=128, phase=0, dphase=180,
                  sltime=0, lims=defwin, reps=1, detune=0, d=0, port=1,
                  **kwargs):
    func = change_phase
    args = [(phase+dphase) % 360, phase]
    d = subback(func, args, devices, ave, sltime, lims, reps, d=d,
                detune=detune, port=port, **kwargs)
    
    return d


def subback_none(devices, ave=128, phase=0, dphase=180,
                 sltime=0, lims=defwin, reps=1, detune=0, d=0, port=1,
                 **kwargs):
    func = nochange
    args = [0, 0]
    d = subback(func, args, devices, ave, sltime, lims, reps, d=d,
                detune=detune, port=port, **kwargs)
    
    return d


def subback_phasedelay(devices, ave=128, phase=0, delay=1000, offset=False,
                       dphase=180, sltime=0, lims=defwin, reps=1, detune=0, d=0,
                       **kwargs):
    if isinstance(d, int):
        d = ps.ItemAttribute()
    period = devices.fpga.period/1e9
#     delay = devices.fpga.delay/1e9
    win = [delay/1e9+lims[0]/1e6, delay/1e9+lims[1]/1e6]
    
    if not sltime:
        sltime = period*ave if period>0.1 else 2*period*ave
    change_delay(devices, 10*delay, ave, 0)
    change_phase(devices, (phase+dphase) % 360, ave, sltime, [offset, 0])
    [[d.time, d.v1downno],
     [_, d.v2downno]] = devices.scope.read_screen(0, init=False)
    if reps>1:
        for n in range(reps-1):
            sleep(sltime)
            [[_, v1dn], [_, v2dn]] = devices.scope.read_screen(0, init=False)
            d.v1downno = (v1dn+d.v1downno)
            d.v2downno = (v2dn+d.v2downno)
        d.v1downno = d.v1downno/reps
        d.v2downno = d.v2downno/reps
    change_phase(devices, phase, ave, sltime, [offset, 1])
    [[d.time, d.v1upno],
     [_, d.v2upno]] = devices.scope.read_screen(0, init=False)
    if reps>1:
        for n in range(reps-1):
            sleep(sltime)
            [[_, v1d], [_, v2d]] = devices.scope.read_screen(0, init=False)
            d.v1upno = (v1d+d.v1upno)
            d.v2upno = (v2d+d.v2upno)
        d.v1upno = d.v1upno/reps
        d.v2upno = d.v2upno/reps
    change_delay(devices, delay, ave, 0)
    change_phase(devices, (phase+dphase) % 360, ave, sltime, [offset, 0])
    [[d.time, d.v1downyes],
     [_, d.v2downyes]] = devices.scope.read_screen(0, init=False)
    if reps>1:
        for n in range(reps-1):
            sleep(sltime)
            [[_, v1d], [_, v2d]] = devices.scope.read_screen(0, init=False)
            d.v1downyes = (v1d+d.v1downyes)
            d.v2downyes = (v2d+d.v2downyes)
        d.v1downyes = d.v1downyes/reps
        d.v2downyes = d.v2downyes/reps
    change_phase(devices, phase, ave, sltime, [offset, 1])
    [[_, d.v1upyes], [_, d.v2upyes]] = devices.scope.read_screen(0, init=False)
    if reps>1:
        for n in range(reps-1):
            sleep(sltime)
            [[_, v1d], [_, v2d]] = devices.scope.read_screen(0, init=False)
            d.v1upyes = (v1d+d.v1upyes)
            d.v2upyes = (v2d+d.v2upyes)
        d.v1upyes = d.v1upyes/reps
        d.v2upyes = d.v2upyes/reps
    d.v1up = (d.v1upyes-d.v1upno)
    d.v2up = (d.v2upyes-d.v2upno)
    d.v1down = (d.v1downyes-d.v1downno)
    d.v2down = (d.v2downyes-d.v2downno)
    
    d = process_se(d, win, detune)
    d.xsub, d.v1sub, d.v2sub = [sig/2 for sig in [d.xsub, d.v1sub, d.v2sub]]
    
    
    return d


def subback_delay(devices, ave=128, delay=1000, delay2=1000, port=1,
                  sltime=0, lims=defwin, reps=1, d=0, detune=0, **kwargs):
    func = change_delay
    del_ch = delay if port==1 else delay2
    back_delay = del_ch+5000 if del_ch<10000 else del_ch-5000
    args = [back_delay, del_ch]
    d = subback(func, args, devices, ave=ave, port=port, sltime=sltime,
                lims=lims, reps=reps, d=d, detune=detune, **kwargs)
    
    return d


def max_phase(devices, ave=4, ch=1):
    phs = np.zeros(3)
    dph = 5
    change_phase(devices, int(phs[0]), ave)
    tva = np.mean(devices.scope.read_screen(ch, init=False)[0][1])
    if tva<0:
        phs[0] = 180
        tva = -tva
    phs[1] = phs[0] + dph
    change_phase(devices, int(phs[1]), ave)
    tvb = np.mean(devices.scope.read_screen(ch, init=False)[0][1])
    phs[2] = phs[1] + dph
    change_phase(devices, int(phs[2]), ave)
    tvc = np.mean(devices.scope.read_screen(ch, init=False)[0][1])
    tar = [tva, tvb, tvc]
#     tcomp = np.argmax(tar)
    tcomp = np.abs(tar).argmin()
    tva = np.abs(tar[tcomp])
    ph = phs[tcomp]
    if tcomp!=1:
        if tcomp == 0:
            tmult = -1
            if phs[0]==0:
                ph = 360
        else:
            tmult = 1
        while True:
            ph = (ph + tmult*dph) % 360
            change_phase(devices, int(ph), ave)
            nsig = devices.scope.read_screen(ch, init=False)[0][1]
            tvb = np.abs(np.mean(nsig))
            if tvb<tva:
                tva = tvb
            else:
                if ch==1:
                    ph = (ph - tmult*dph + 90) % 360
                else:
                    ph = ph - tmult*dph
                    if ph<0:
                        ph = ph + 360
                break
    devices.synth.instrument[0].phase = (ph)
    return ph


def measure_echo(expt):
    """
    """
     
    runinfo = expt.runinfo
    devices = expt.devices

#     d = ps.ItemAttribute()
    
    if 'sltime' in runinfo.keys():
        sltime = runinfo.sltime
    else:
        sltime = 0
    if 'reps' in runinfo.keys():
        reps = runinfo.reps
    else:
        reps = 1
        
    delay = devices.fpga.delay
    delay2 = devices.fpga.delay2
    phase = devices.synth.c2_phase#runinfo.parameters['phase']
    ave = devices.scope.average
    port = runinfo.parameters['port']
    lims = [-runinfo.parameters['int_start'], runinfo.parameters['int_end']]

    d = runinfo.sub_func(devices, ave,
                         phase=phase,
                         delay=delay,
                         delay2=delay2,
                         sltime=sltime,
                         reps=runinfo.parameters['reps'],
                         port=port,
                         lims=lims)
    d.delay = delay
    d.delay2 = delay2
    d.phase = phase
    d.sltime = sltime
    if 'ls335' in devices.keys():
        d.temp = devices.ls335.get_temp()
    
    expt.t = d.time

    d.current_time = time()

    if runinfo._indicies[0]==(runinfo._dims[0]-1):
        expt.elapsed_time = expt.current_time-expt.start_time
        if runinfo.parameters['turn_off']:
            devices.synth.power_off()
            devices.psu.output = False
        if runinfo.parameters['expt']=='Phase Sweep':
            sigs = list(expt.v1int[:-1])+[d.v1int]
            expt.maxphase = phase_fit(expt.phase_sweep, sigs)
    return d


def pulse_change(devices, tpi2, port, mult):
    old_time = devices.fpga.pulse1
    if port==0:
        devices.fpga.pulse1 = tpi2
        devices.fpga.pulse2 = tpi2*mult
        devices.fpga.pulse2_1 = tpi2
        devices.fpga.pulse2_2 = tpi2*mult
    elif port==1:
        devices.fpga.pulse1 = tpi2
        devices.fpga.pulse2 = tpi2*mult
    elif port==2:
        old_time = devices.fpga.pulse2_1
        devices.fpga.pulse2_1 = tpi2
        devices.fpga.pulse2_2 = tpi2*mult
        devices.fpga.delay = devices.fpga.delay2 + (1+mult)*tpi2
    change_trigger_delta(devices, old_time*(1+mult), tpi2*(1+mult))
        
        
def frequency_change(devices, f, find_phase=False):
    devices.scope.average = 1
    devices.synth.c_freqs = f
    if find_phase:
        max_phase(devices)


def rabifit(x, a, t, T, b):
    return a*np.exp(-x/t)*np.cos(2*np.pi/T*x)+b


def plot_fit_rabi(t_nut, vdat, guess=[1, 200, 100, 0.3]):
    rfit = plot_func_fit(rabifit, np.array([t_nut, vdat/vdat.max()]), guess)
    return rfit


def setup_experiment(parameters, devices, sweep):
    def pulse_time(tpi2):
        pulse_change(devices, tpi2, parameters['port'], parameters['mult'])
    def delay_sweep(delay):
        delay_change(devices, delay, parameters['port'])
    def phase_sweep(phase):
        change_phase(devices, phase, parameters['ave'], parameters['sltime'])
    expt_select = {'Pulse Sweep': 0,
                   'Rabi': 1,
                   'Period Sweep': 2,
                   'Hahn Echo': 3,
                   'EDFS': 4,
                   'Freq Sweep': 5,
                    'Phase Sweep': 6,
                  'Inversion Sweep': 7}
    function_select = {'Phase': subback_phase,
                       'Delay': subback_delay,
                       'Both': subback_phasedelay,
                           'None': subback_none}
    func = function_select[parameters['subtract']]
    wait = parameters['wait']
    sweep_range = ps.drange(parameters['sweep_start'],
                            parameters['sweep_step'],
                            parameters['sweep_end'])
    setup_vars = {'y_name': ['pulse_time',
                             'fpga_nutation_width',
                             'fpga_period',
                             'delay_sweep',
                             'psu_field',
                             'synth_c_freqs',
                                 'phase_sweep',
                            'fpga_nutation_delay'],
                  'loop': [ps.FunctionScan(pulse_time, sweep_range, dt=wait),
                           ps.PropertyScan({'fpga': sweep_range},
                                           prop='nutation_width', dt=wait),
                           ps.PropertyScan({'fpga': sweep_range},
                                           prop='period', dt=wait),
                           ps.FunctionScan(delay_sweep, sweep_range, dt=wait),
                           ps.PropertyScan({'psu': sweep_range},
                                           prop='field', dt=wait),
                           ps.PropertyScan({'synth': sweep_range},
                                           prop='c_freqs', dt=wait),
                           ps.FunctionScan(phase_sweep, sweep_range, dt=wait),
                           ps.PropertyScan({'fpga': sweep_range},
                                           prop='nutation_delay', dt=wait)],
                  'file': ['PSweep',
                           'Rabi',
                           'T1',
                           'Hahn',
                           'EDFS',
                           'EFSweep',
                               'PhiSweep',
                          'T1']
                  }
    run_n = expt_select[parameters['expt']]
    parameters['y_name'] = setup_vars['y_name'][run_n]
    fname = setup_vars['file'][run_n]
    runinfo = ps.RunInfo()
    runinfo.loop0 = setup_vars['loop'][run_n]
    runinfo.measure_function = measure_echo
    runinfo.sub_func = func
    runinfo.sltime = parameters['sltime']
    # devices.scope.read_scope()

    runinfo.parameters = parameters
    runinfo.wait_time = parameters['wait']

    # TODO: Move the actual intialization of the sweep to Run
    # so we don't get so many empty directories
    # expt = ps.Sweep(runinfo, devices, parameters['outfile']+fname)
    # sweep['expt'] = expt
    sweep['name'] = parameters['outfile']+fname
    sweep['runinfo'] = runinfo


def pulse_length_sweep():
    runinfo = ps.RunInfo()
    def pulse_time(tpi2):
        pulse_change(devices, tpi2, parameters['port'])
    runinfo.loop0 = ps.FunctionScan(pulse_time, ps.drange(60, 10, 200), dt=wait)

    runinfo.measure_function = measure_echo
    runinfo.sub_func = subback_phase
    devices.scope.read_scope()

    runinfo.current = 0
    runinfo.parameters = parameters
    # runinfo.sltime = .02*2*runinfo.average

    runinfo.wait_time = .1 # devices.fpga.period*runinfo.average/1e9*1.1

    expt = ps.Sweep(runinfo, devices, parameters['outfile']+'PSweep')
    expt.start_thread()

    ps.live_plot2D(expt, x_name='t', y_name='pulse_time', data_name='xsub',
                   transpose=1)


def phase_fit(phase, sig):
    guess = [0, np.max(sig), np.pi/180, 0]
    fit = func_fit(sinefit, np.array([phase, sig]), guess)[0]
    return (90-fit[-1]*180/np.pi+90*(1-np.sign(fit[1]))) % 360


def setup_sweep_sequence(parameters, devices, sweep):
    """Function to prepare (and possibly run) multiple consecutive sweeps,
    possibly using information from one sweep in the following sweeps.
    An example of this would be to run a pulse sweep, then pick the length
    corresponding to the maximum signal. Then run a phase sweep, picking the
    phase corresponding to the maximum Ch1 signal. Then run a Rabi sweep,
    a Hahn echo sweep, and an EDFS.

    Requirements:
    * Need to be able to specify the order of the sweeps.
    * Should be able to specify whether to apply the maxphase, etc.
    * Should create different save files for each sweep (as normal)
    * Should maybe be a new tab in the GUI

    """
    return 0
