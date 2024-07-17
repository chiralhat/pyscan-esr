import sys
sys.path.append('../')
from spinecho_scripts import *

defwin = [[1e-1, 4e-1], [1e-1, 4e-1]]



def change_delays(devices, delays, ave=4, sltime=0.3, **kwargs):
    old_delay = devices.fpga.delay1
    devices.fpga.delay = delays[0]
    devices.fpga.delay2 = delays[1]
    change_trigger_delta(devices, old_delay, delays[0])
    devices.scope.average = 1
    sleep(0.1)
    devices.scope.average = ave
    sleep(sltime)

    
def invert_scope(devices, arg, ave=4, sltime=0.3, **kwargs):
    devices.scope.toggle_invert(arg)
    devices.scope.average = 1
    sleep(0.1)
    devices.scope.average = ave
    sleep(sltime)


def fourier_signals(d, fstart=3, fstop=100):
    # TODO: Make this work for all 4 channels
    # Calculate the fourier transform of each signal
    fourier = [np.abs(rfft(sig)) for sig in [d.x1sub, d.v1sub, d.v2sub]]
    # Combine the individual channel ffts
    fourier.append(np.sqrt(fourier[1]**2+fourier[2]**2))
    d.fourier = fourier + [np.abs(rfft(sig)) for sig in [d.x2sub, d.v3sub, d.v4sub]]
    d.fourier.append(np.sqrt(d.fourier[-1]**2+d.fourier[-2]**2))
    d.ffreqs = rfftfreq(len(d.x1sub), d.time[1]-d.time[0])
    flen = len(d.fourier)
    d.ffit = np.zeros((flen, 4))
    for n in range(flen):
        try:
            lordat = np.array([d.ffreqs, -d.fourier[n]])[:, fstart:fstop]
            d.ffit[n] = ut.lor_fit(lordat)[0]
        except:
            0
    d.x1famp, d.v1famp, d.v2famp, d.x1xfamp = [-fit[1] for fit in d.ffit[:4]]
    d.ffdet1 = d.ffit[1][-1]
    d.ffdet2 = d.ffit[2][-1]
    d.ffdetx1 = d.ffit[3][-1]
    d.x2famp, d.v3famp, d.v4famp, d.x2xfamp = [-fit[1] for fit in d.ffit[4:]]
    d.ffdet3 = d.ffit[5][-1]
    d.ffdet4 = d.ffit[6][-1]
    d.ffdetx2 = d.ffit[7][-1]
    fwin = list(d.ffreqs[[fstart, fstop]])
    int_out = integrate_echo(d.ffreqs, d.fourier,
                                backsub='linear', prewin=fwin)
    [d.x1fint, d.v1fint, d.v2fint, d.x1xfint,
     d.x2fint, d.v3fint, d.v4fint, d.x2xfint] = int_out
    return d
    
    
def process_ses(d, win, backnum=100, detune=0):
    v1usub = sback(d.v1up)
    v1dsub = sback(d.v1down)
    v2usub = sback(d.v2up)
    v2dsub = sback(d.v2down)
    d.v1sub = v1usub-v1dsub
    d.v2sub = v2usub-v2dsub
    d.x1up = np.sqrt(v1usub**2+v2usub**2)
    d.x1down = np.sqrt(v1dsub**2+v2dsub**2)
    d.x1sub = np.sqrt(d.v1sub**2+d.v2sub**2)
    d.x1sub1 = d.x1up-d.x1down

    int_out = integrate_echo(d.time, [d.v1sub, d.v2sub, d.x1sub, d.x1sub1],
                                backsub='linear', prewin=win[0])
    [d.v1int, d.v2int, d.x1int, d.x1int1] = int_out
    
    v3usub = sback(d.v3up)
    v3dsub = sback(d.v3down)
    v4usub = sback(d.v4up)
    v4dsub = sback(d.v4down)
    d.v3sub = v3usub-v3dsub
    d.v4sub = v4usub-v4dsub
    d.x2up = np.sqrt(v3usub**2+v4usub**2)
    d.x2down = np.sqrt(v3dsub**2+v4dsub**2)
    d.x2sub = np.sqrt(d.v3sub**2+d.v4sub**2)

    d.x2sub1 = d.x2up-d.x2down

    int_out = integrate_echo(d.time, [d.v3sub, d.v4sub, d.x2sub, d.x2sub1],
                                backsub='linear', prewin=win[1])
    [d.v3int, d.v4int, d.x2int, d.x2int1] = int_out
    d = fourier_signals(d)
    
    return d


def subback(subfunc, args, devices, ave,
            sltime=0, lims=defwin, reps=1, detune=0, d=0,
            **kwargs):
    if isinstance(d, int):
        d = ps.ItemAttribute()
    period = devices.fpga.period/1e9
    delays = np.array([devices.fpga[dstr]/1e9 for dstr in ['delay', 'delay2']])
    win = [[lim[0]/1e6, lim[1]/1e6]
            for lim in lims]
    
    if not sltime:
        sltime = ave/1000 if period<0.001 else period*ave
    subfunc(devices, args[0], ave=ave, sltime=sltime, **kwargs)
    [[d.time, d.v1down], [_, d.v2down],
     [_, d.v3down], [_, d.v4down]] = devices.scope.read_screen(5, init=False)
    if reps>1:
        for n in range(reps-1):
            sleep(sltime)
            [[_, v1d], [_, v2d], 
             [_, v3d], [_, v4d]] = devices.scope.read_screen(5, init=False)
            d.v1down = (v1d+d.v1down)
            d.v2down = (v2d+d.v2down)
            d.v3down = (v3d+d.v3down)
            d.v4down = (v4d+d.v4down)
        d.v1down = d.v1down/reps
        d.v2down = d.v2down/reps
        d.v3down = d.v3down/reps
        d.v4down = d.v4down/reps
    subfunc(devices, args[1], ave=ave, sltime=sltime, **kwargs)
    [[_, d.v1up], [_, d.v2up],
     [_, d.v3up], [_, d.v4up]] = devices.scope.read_screen(5, init=False)
    if reps>1:
        for n in range(reps-1):
            sleep(sltime)
            [[_, v1u], [_, v2u], 
             [_, v3u], [_, v4u]] = devices.scope.read_screen(5, init=False)
            d.v1up = (v1u+d.v1up)
            d.v2up = (v2u+d.v2up)
            d.v3up = (v3u+d.v3up)
            d.v4up = (v4u+d.v4up)
        d.v1up = d.v1up/reps
        d.v2up = d.v2up/reps
        d.v3up = d.v3up/reps
        d.v4up = d.v4up/reps
    
    d = process_ses(d, win, detune=detune)
    #d.xsub, d.v1sub, d.v2sub = [sig/2 for sig in [d.xsub, d.v1sub, d.v2sub]]
    d.win = win
    
    return d


def subback_delays(devices, ave=128, delay1=1000, delay2=1000,
                  sltime=0, lims=defwin, reps=1, d=0, detune=0, **kwargs):
    func = change_delays
    del_chs = [delay1, delay2]
    back_delay = [del_ch+5000 if del_ch<10000 else del_ch-5000 
                  for del_ch in del_chs]
    args = [back_delay, del_chs]
    d = subback(func, args, devices, ave=ave, sltime=sltime,
                lims=lims, reps=reps, d=d, detune=detune, **kwargs)
    
    return d


def subback_nones(devices, ave=128, phase=0, dphase=180,
                 sltime=0, lims=defwin, reps=1, detune=0, d=0, port=1,
                 **kwargs):
    func = invert_scope
    args = [1, 0]
    d = subback(func, args, devices, ave, sltime, lims, reps, d=d,
                detune=detune, port=port, **kwargs)
    
    return d


def measure_echos(expt):
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
    ave = devices.scope.average
    b_off = runinfo.parameters['p2start']/1000
    int_start = -runinfo.parameters['int_start']
    int_end = runinfo.parameters['int_end']
    int_start2 = -runinfo.parameters['int_start2']
    int_end2 = runinfo.parameters['int_end2']
    lims = [[-int_start, int_end], [b_off-int_start, b_off+int_end]]

    d = runinfo.sub_func(devices, ave,
                         delay1=delay,
                         delay2=delay2,
                         sltime=sltime,
                         reps=runinfo.parameters['reps'],
                         lims=lims)
    d.delay = delay
    d.delay2 = delay2
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
    return d


def pulse_change(devices, tpi2, port, mult):
    time_delta = tpi2*(1+mult) - devices.fpga.pulse1-devices.fpga.pulse2
    if port==0:
        devices.fpga.pulse1 = tpi2
        devices.fpga.pulse2 = tpi2*mult
        devices.fpga.pulse2_1 = tpi2
        devices.fpga.pulse2_2 = tpi2*mult
    elif port==1:
        devices.fpga.pulse1 = tpi2
        devices.fpga.pulse2 = tpi2*mult
    elif port==2:
        time_delta = 0
        devices.fpga.pulse2_1 = tpi2
        devices.fpga.pulse2_2 = tpi2*mult
    devices.scope.trigger_delay += time_delta/1e9


bifunction_select = {'Delay': subback_delays,
    'None': subback_nones}


def setup_bimod_experiment(parameters, devices, sweep):
    '''Initialize the desired experimental parameters, and set up the sweep.
    Needs to define any necessary functions for function sweeps.
    Choose the experiment, the background subtraction method, and then
    populate the sweep parameters from the chosen inputs.
    '''
    def pulse_a_time(tpi2):
        pulse_change(devices, tpi2, 1, parameters['mult1'])
    def pulse_b_time(tpi2):
        pulse_change(devices, tpi2, 2, parameters['mult2'])
    def pulse_time(tpi2):
        pulse_change(devices, tpi2, 0, parameters['mult1'])
    def delay_sweep(delay):
        devices.fpga.delay = delay
        devices.fpga.delay2 = delay
    expt_select = {'A Pulse Sweep': 0,
        'B Pulse Sweep': 1,
        'Both Pulse Sweep': 2,
        'B Rabi': 3,
        'Period Sweep': 4,
        'Hahn Echo': 5,
        'EDFS': 6,
        'A Freq Sweep': 7,
        'B Freq Sweep': 8,
        'Both Freq Sweep': 9,
        'DEER': 10}
    func = bifunction_select[parameters['subtract']]
    wait = parameters['wait']
    sweep_range = ps.drange(parameters['sweep_start'],
        parameters['sweep_step'],
        parameters['sweep_end'])
    setup_vars = {'y_name': ['pulse_a_time',
                             'pulse_b_time',
                             'pulse_time',
                             'fpga_nutation_width',
                             'fpga_period',
                             'delay_sweep',
                             'psu_field',
                             'synth_c1_freq',
                             'synth_c2_freq',
                             'synth_c_freqs',
                             'fpga_p2start'],
                  'loop': [ps.FunctionScan(pulse_a_time, sweep_range, dt=wait),
                           ps.FunctionScan(pulse_b_time, sweep_range, dt=wait),
                           ps.FunctionScan(pulse_time, sweep_range, dt=wait),
                           ps.PropertyScan({'fpga': sweep_range},
                                           prop='nutation_width', dt=wait),
                           ps.PropertyScan({'fpga': sweep_range},
                                           prop='period', dt=wait),
                           ps.FunctionScan(delay_sweep, sweep_range, dt=wait),
                           ps.PropertyScan({'psu': sweep_range},
                                           prop='field', dt=wait),
                           ps.PropertyScan({'synth': sweep_range},
                                           prop='c1_freq', dt=wait),
                           ps.PropertyScan({'synth': sweep_range},
                                           prop='c2_freq', dt=wait),
                           ps.PropertyScan({'synth': sweep_range},
                                           prop='c_freqs', dt=wait),
                           ps.PropertyScan({'fpga': sweep_range},
                                           prop='p2start', dt=wait)],
                  'file': ['PASweep',
                           'PBSweep',
                           'PSweep',
                           'Rabi',
                           'T1',
                           'Hahn',
                           'EDFS',
                           'EDFreqAS',
                           'EDFreqBS',
                           'EDFreqS',
                           'DEER']
                  }
    run_n = expt_select[parameters['bimod_expt']]
    parameters['y_name'] = setup_vars['y_name'][run_n]
    fname = setup_vars['file'][run_n]
    runinfo = ps.RunInfo()
    runinfo.loop0 = setup_vars['loop'][run_n]
    runinfo.measure_function = measure_echos
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


