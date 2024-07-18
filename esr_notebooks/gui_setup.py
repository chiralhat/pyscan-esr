import sys, os
sys.path.append('../')
import pyscan as ps
import numpy as np
import matplotlib.pyplot as plt
from datetime import date, datetime
from time import time, sleep
from IPython.display import display, clear_output
from pathlib import Path
import pickle
import pyvisa
import ipywidgets as ipw

# Define some useful defaults for various properties
nwid = ipw.Layout(width='200px')
wwid = ipw.Layout(width='350px')
lstyle = {'description_width': 'initial'}
cpmgs = range(1, 256)
aves = [1, 4, 16, 64, 128, 256]
voltage_limits = [0.002, 10]
tdivs = []
for n in range(9, -1, -1):
    tdivs += [2*10**-n, 4*10**-n, 10*10**-n]#[2.5*10**-n, 5*10**-n, 10*10**-n]

scopes = {'MSO24': ps.TektronixMSO2}

sweep_list = ['Pulse Sweep',
              'Phase Sweep',
              'Rabi',
              'Period Sweep',
              'Hahn Echo',
              'EDFS',
              'Freq Sweep',
              'Inversion Sweep']

bimod_sweep_list = ['A Pulse Sweep',
              'B Pulse Sweep',
              'Both Pulse Sweep',
              'B Rabi',
              'Period Sweep',
              'Hahn Echo',
              'EDFS',
              'A Freq Sweep',
              'B Freq Sweep',
              'Both Freq Sweep',
              'DEER',
              'A Power Sweep',
                'B Power Sweep',
        'Hole Burning']

# Load the Resource Manager if it hasn't been done yet
if not hasattr(ps, 'rm'):
    ps.rm = pyvisa.ResourceManager('@py')
res_list = ps.rm.list_resources()

# This indicator shows whether a process is running.
run_ind = ipw.IntProgress(value=0, min=0, max=1,
                          description='Running:',
                          layout=ipw.Layout(width='110px'),
                          style={'bar_color': 'red'})

# This indicator shows whether the devices are connected.
conn_ind = ipw.IntProgress(value=0, min=0, max=1,
                          description='Connected:',
                          layout=ipw.Layout(width='110px'),
                          style={'bar_color': 'green'})

# The complete list of controls for every GUI. Not all will be used in any given script
control_dict = {'devices': {'scope_address': ipw.Dropdown(options=res_list, layout=wwid,
                                                          description='Scope Addr'),
                            'fpga_address': ipw.Dropdown(options=res_list,
                                                         description='FPGA Addr'),
                            'synth_address': ipw.Dropdown(options=res_list,
                                                          description='RF Addr'),
                            'psu_address': ipw.Dropdown(options=res_list,
                                                          description='PSU Addr'),
                            'use_psu': ipw.Checkbox(layout=wwid, description='Use PSU? (No magnet if not)')},
                'synth': {'freq': ipw.BoundedFloatText(min=50, max=14999, step=0.00001, layout=nwid,
                                                       description='Freq (MHz)'),
                          'freq1': ipw.BoundedFloatText(min=50, max=14999, step=0.00001, layout=nwid,
                                                       description='Ch1 Freq (MHz)'),
                          'freq2': ipw.BoundedFloatText(min=50, max=14999, step=0.00001, layout=nwid,
                                                       description='Ch2 Freq (MHz)'),
                          'freq_start': ipw.BoundedFloatText(min=50, max=14999, step=0.00001, layout=nwid,
                                                       description='Freq Start (MHz)'),
                          'freq_end': ipw.BoundedFloatText(min=50, max=14999, step=0.00001, layout=nwid,
                                                       description='Freq End (MHz)'),
                          'freq_step': ipw.BoundedFloatText(min=0.00001, max=14999, step=0.00001, layout=nwid,
                                                       description='Freq Step (MHz)'),
                          'detune': ipw.BoundedFloatText(layout=nwid, min=-5000, max=5000, step=0.00001,
                                                         description='Detuning'),
                          'port': ipw.Dropdown(layout=nwid, options=[('1', 1), ('2', 2), ('Both', 0)],
                                               description='Output Port'),
                          'power': ipw.BoundedFloatText(layout=nwid, min=-50, max=19, step=0.01,
                                                        description='Ch1 Power (dBm)'),
                          'power2': ipw.BoundedFloatText(layout=nwid, min=-50, max=19, step=0.01,
                                                         description='Ch2 Power'),
                          'phase': ipw.BoundedFloatText(layout=nwid, min=0, max=360, step=0.01,
                                                        description='Phase'),
                          'att': ipw.Checkbox(layout=nwid, description='Attenuator?'),
                          'att1': ipw.Checkbox(layout=nwid, description='Ch1 Attenuator?'),
                          'att2': ipw.Checkbox(layout=nwid, description='Ch2 Attenuator?')},
                'fpga': {'delay': ipw.BoundedFloatText(layout=nwid, min=10, max=652100, step=10,
                                                       description='Delay (ns)'),
                         'delay1': ipw.BoundedFloatText(layout=nwid, min=10, max=652100, step=10,
                                                       description='Ch1 Delay (ns)'),
                         'delay2': ipw.BoundedFloatText(layout=nwid, min=10, max=652100, step=10,
                                                       description='Ch2 Delay (ns)'),
                         'pulse1': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=10,
                                                        description='90 Pulse (ns)'),
                         'pulse2': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=10,
                                                        description='180 Pulse (ns)'),
                         'mult': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=0.001,
                                                        description='180 Pulse Mult'),
                         'pulse1_1': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=10,
                                                        description='Ch1 90 Pulse (ns)'),
                         'pulse1_2': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=10,
                                                        description='Ch1 180 Pulse (ns)'),
                         'mult1': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=0.001,
                                                        description='Ch1 180 Pulse Mult'),
                         'pulse2_1': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=10,
                                                        description='Ch2 90 Pulse (ns)'),
                         'pulse2_2': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=10,
                                                        description='Ch2 180 Pulse (ns)'),
                         'mult2': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=0.001,
                                                        description='Ch2 180 Pulse Mult'),
                         'p2start': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=10,
                                                        description='Ch2 Pulse Offset (ns)'),
                         'period': ipw.BoundedFloatText(10e6, min=10, max=20e9, step=10,
                                                         description='Period'),
                         'cpmg': ipw.Dropdown(layout=nwid, options=cpmgs, description='# 180 Pulses'),
                         'block': ipw.Checkbox(layout=nwid, description='Block Pulses'),
                         'phase_sub': ipw.Checkbox(layout=nwid, description='Auto Phase Sub'),
                         'pulse_block': ipw.BoundedFloatText(layout=nwid, min=0, max=2560, step=10,
                                                    description='Block Delay (ns)'),
                         'nutation_delay': ipw.BoundedFloatText(6e5, min=0, max=655360, step=10,
                                                                description='Nut. Delay (ns)'),# style=lstyle),
                         'nutation_width': ipw.BoundedFloatText(layout=nwid, min=0, max=655360, step=10,
                                                                description='Nut. Pulse Width'),
                         'pre_att': ipw.BoundedFloatText(layout=nwid, min=0, max=31.5, step=0.5,
                                                         description='Input Attenuation (Ω)')},
                'scope': {'ave': ipw.BoundedFloatText(layout=nwid, min=0, max=10240, step=1,
                                                      description='Ave'),#'ave': ipw.Dropdown(layout=nwid, options=aves, description='Ave'),
                          'scale': ipw.BoundedFloatText(layout=nwid, min=0, max=voltage_limits[-1],
                                                        step=0.002, description='Scale (V)'),
                          'h_offset': ipw.BoundedFloatText(layout=nwid, min=-1e5, max=1e5,
                                                           description='Time Offset (ns)'),
                          'tdiv': ipw.Dropdown(layout=nwid, options=tdivs,
                                               description='Time Scale (s)'),
                          'v_offset': ipw.Checkbox(description='Vert Offset?')},
                'psu': {'field': ipw.BoundedFloatText(min=0, max=2500, step=0.1, layout=nwid,
                                                       description='Magnetic Field (G)'),
                        'field_start': ipw.BoundedFloatText(min=0, max=2500, step=0.1, layout=nwid,
                                                       description='Field Start (G)'),
                        'field_end': ipw.BoundedFloatText(min=0, max=2500, step=0.1, layout=nwid,
                                                       description='Field End (G)'),
                        'field_step': ipw.BoundedFloatText(min=0.1, max=2500, step=0.1, layout=nwid,
                                                       description='Field Step (G)'),
                        'gauss_amps': ipw.BoundedFloatText(min=0.001, max=10000, step=0.001, layout=nwid,
                                                       description='Magnet Scale (G/A)'),
                        'current_limit': ipw.BoundedFloatText(min=0, max=10, step=0.001, layout=nwid,
                                                       description='Current Limit (A)')},
                'save': {'save_dir': ipw.Text(layout=wwid, description='Data Dir'),
                         'file_name': ipw.Text(layout=wwid, description='File Name')},
                'measure': {'subtract': ipw.Dropdown(layout=nwid, 
                                                     options=['Phase', 'Delay', 'Both', 'None'],
                                                     description='Sub Method'),
                            'reps': ipw.BoundedIntText(layout=nwid, min=1, max=1000,
                                                       description='Reps'),
                            'expt': ipw.Dropdown(layout=nwid,
                                                 options=sweep_list,
                                                 description='Experiment'),
                            'bimod_expt': ipw.Dropdown(layout=nwid,
                                                 options=bimod_sweep_list,
                                                 description='Experiment'),
                            'psexpt': ipw.Dropdown(layout=nwid,
                                                 options=['Freq Sweep',
                                                          'Field Sweep'],
                                                 description='Experiment'),
                            'wait': ipw.BoundedFloatText(min=0, max=20, step=0.001, layout=nwid,
                                                         description='Wait Time (s)'),
                            'sltime': ipw.BoundedFloatText(min=0, max=20, step=1e-9, layout=nwid,
                                                         description='Averaging Time (s)'),
                            'init': ipw.Checkbox(description='Initialize on read?'),
                            'sweep_start': ipw.FloatText(layout=nwid, description='Sweep Start'),
                            'sweep_end': ipw.FloatText(layout=nwid, description='Sweep End'),
                            'sweep_step': ipw.FloatText(layout=nwid, description='Sweep Step'),
                            'int_start': ipw.FloatText(layout=nwid, description='Int. Window (μs): Pre'),
                            'int_end': ipw.FloatText(layout=nwid, description='Post Delay'),
                            'int_start2': ipw.FloatText(layout=nwid, description='Int. Window 2 (μs): Pre'),
                            'int_end2': ipw.FloatText(layout=nwid, description='Post Delay 2'),
                            'turn_off': ipw.Checkbox(description='Turn off after sweep?'),}
                }
                


# def setup_plot(output, fig):
#     """
    

#     Parameters
#     ----------
#     output : TYPE
#         DESCRIPTION.
#     fig : TYPE
#         DESCRIPTION.

#     Returns
#     -------
#     None.

#     """
#     ax = fig.add_subplot(111)
#     ax.set_xlabel('Time (μs)')
#     ax.set_ylabel('Voltage (V)')
#     with output:
#         clear_output(wait=True)
#         display(ax.figure)


def read(sig, devices, output, fig):
    """
    Read the oscilloscope and plot it in the output window.

    Parameters
    ----------
    sig : pyscan ItemAttribute
        Signal object for accessing the scope data. Updated by this function.
    devices : pyscan ItemAttribute
        Devices object for accessing the acquisition equipment.
    output : ipyWidgets Output
        Output window.
    fig : pyplot Figure
        Figure used to plot the scope data.

    Returns
    -------
    None.

    """
    devices.scope.read_vxy(d=sig)
    for ax in fig.axes:
        ax.remove()
    ax = fig.add_subplot(111)
    ax.plot(sig.time*1e6, sig.volt1, color='yellow', label='CH1')
    ax.plot(sig.time*1e6, sig.volt2, color='b', label='CH2')
    ax.plot(sig.time*1e6, sig.x, color='g', label='AMP')
    ax.set_xlabel('Time (μs)')
    ax.set_ylabel('Subtracted Signal (V)')
    ax.legend()
    with output:
        clear_output(wait=True)
        display(ax.figure)


def run_sweep(sweep, parameters):#, output, fig):
    sweep['expt'].start_time = time()
    sweep['expt'].start_thread()
    

def cont_update(controls, parcont, lcont, defaults, sty=True):
    """
    Add a set of control widgets to the main list to define the GUI.

    Parameters
    ----------
    controls : list
        Main list of control widgets. Updated by this function.
    parcont : dict
        Setup parameters for the controls. Updated by this function.
    lcont : dict
        Controls to be added to the main list.
    defaults : dict
        Default parameters.
    sty : bool, optional
        Set the widget description widths to the width of the text.
        The default is True.

    Returns
    -------
    None.

    """
    for k, v in lcont.items():
        if k in defaults.keys():
            try:
                v.value = defaults[k]
            except:
                0
        if sty:
            v.style = lstyle
    controls += [ipw.HBox([lcont[k] for k in lcont])]
    parcont.update(lcont)


def init_controls(controls, parcont, parameters, cdict):
    """
    Initialize all the control widgets for the GUI.

    Parameters
    ----------
    controls : list
        Main list of control widgets. Updated by this function.
    parcont : dict
        Setup parameters for the controls. Updated by this function.
    parameters : dict
        Default parameters.
    cdict : dict
        Names of the controls to add from the complete list.

    Returns
    -------
    None.

    """
    for k, v in cdict.items():
        for cs in v:
            lcont = {}
            for c in cs:
                lcont[c] = control_dict[k][c]
            cont_update(controls, parcont, lcont, parameters)


def init_gui(cont_keys, init_expt, default_file, single_run, run_sweep, read):
    def gui_function(sig, devices, sweep):
        """
        

    Parameters
        ----------
        sig : pyscan ItemAttribute
        Signal object for accessing single-shot data. Updated by this function.
        devices : pyscan ItemAttribute
        Devices object for accessing the acquisition equipment.
        sweep : dictionary
        Contains a pyscan Sweep (expt) and a pyscan RunInfo (runinfo)
        Updated by this function.

    Returns
        -------
        con_panel : ipyWidgets VBox
        Full GUI object.
        parameters : dict
        Experimental parameters from the controls.
        """
        runinfo = ps.RunInfo()
        
        output = ipw.Output()
        measout = ipw.Output()
    
        controls = []
        try:
            with open(default_file, 'rb') as f:
                parameters = pickle.load(f)
        except:
            parameters = {}
        val_controls = {}
        init_controls(controls, val_controls, parameters, cont_keys)
        
    
        def set_pars(btn):
            for k, v in val_controls.items():
                parameters[k] = v.value

            if 'reps' in parameters.keys():
                reps = parameters['reps']
            else:
                reps = 1
            if 'period' in parameters.keys():
                period = parameters['period']
            else:
                period = 500
            tmult = period/1e9*2*reps if period>1e6 else 2*reps
            parameters['subtime'] = parameters['ave']*tmult
            datestr = date.today().strftime('%y%m%d')
            fname = datestr+str(parameters['file_name'])+'_'
            parameters['outfile'] = str(Path(parameters['save_dir']) / fname)
            with open(default_file, 'wb') as f:
                pickle.dump(parameters, f)
                
            inst = ps.ItemAttribute()
            if not hasattr(devices, 'scope'):
                saddr = parameters['scope_address']
                inst.scope = ps.new_instrument(visa_string=saddr)
                model = inst.scope.query('*IDN?').split(',')[1]
                sleep(0.25)
                devices.scope = scopes[model](inst.scope)
                # inst.bk2190e = ps.new_instrument(visa_string=saddr)
                # devices.scope = ps.BKPrecision2190E(inst.bk2190e)
                devices.scope.initialize_waveforms()
            if not hasattr(devices, 'fpga'):
                faddr = parameters['fpga_address'].split('ASRL')[-1].split('::')[0]
                inst.ecp5 = ps.new_instrument(serial_string=faddr)
                devices.fpga = ps.ecp5evn(inst.ecp5)
            if not hasattr(devices, 'synth'):
                waddr = parameters['synth_address'].split('ASRL')[-1].split('::')[0]
                devices.synth = ps.WindfreakSynthHD(waddr)
            if not hasattr(devices, 'psu') and parameters['use_psu']:
                waddr = parameters['psu_address'].split('ASRL')[-1].split('::')[0]
                devices.psu = ps.GPD3303S(waddr)
            if not hasattr(devices, 'ls335'):
                devices.ls335 = ps.Lakeshore335()
            if (parameters['init'] or btn.description=='Initialize'):
                init_expt(devices, parameters, sweep) # TODO: Fix the runinfo, expt bit (put into new dict?)
                conn_ind.value = 1


        def init_btn(btn):
            run_ind.value = 1
            set_pars(btn)
            run_ind.value = 0

        def stopsweep(btn):
            sweep['expt'].runinfo.running = False
        
        def turnoff(btn):
            if 'expt' in sweep.keys():
                sweep['expt'].runinfo.running = False
            devices.synth.power_off()
            devices.psu.output = False
        
        with output:
            fig = plt.figure(figsize=(8, 5))
        #         setup_plot(output, fig)

        with measout:
            mfig = plt.figure(figsize=(8, 5))


        def start_sweep(btn):
            run_ind.value = 1
            set_pars(btn)
            expt = ps.Sweep(sweep['runinfo'], devices, sweep['name'])
            sweep['expt'] = expt
            run_sweep(sweep, parameters)#, measout, mfig)
            run_ind.value = 0

        
        def read_mon(btn):
            run_ind.value = 1
            set_pars(btn)
            read(sig, devices, output, fig)
            run_ind.value = 0
        
        
        def monitor(btn):
            run_ind.value = 1
            set_pars(btn)
            single_run(sig, parameters, devices, output, fig)
            run_ind.value = 0

        
        def disconnect(btn):
            run_ind.value = 1
            turnoff(btn)
            for key in devices.keys():
                devices[key].close()
            devices.__dict__.clear()
            conn_ind.value = 0
            run_ind.value = 0

        
        goButton = ipw.Button(description='Initialize')
        goButton.on_click(init_btn)
    
        readButton = ipw.Button(description='Read Scope')
        readButton.on_click(read_mon)
    
        monButton = ipw.Button(description='Run (No Save)')
        monButton.on_click(monitor)

        startButton = ipw.Button(description='Start Sweep')
        startButton.on_click(start_sweep)
    
        stopButton = ipw.Button(description='Stop Sweep')
        stopButton.on_click(stopsweep)
    
        offButton = ipw.Button(description='Output Off')
        offButton.on_click(turnoff)

        closeButton = ipw.Button(description='Disconnect')
        closeButton.on_click(disconnect)
    
        controls += [ipw.HBox([goButton, readButton, monButton, startButton, stopButton, run_ind])]
        controls += [ipw.HBox([offButton, closeButton, conn_ind])]
        
        # mtab = measure_select()
        controls += [ipw.HBox([output, measout])]

        con_panel = ipw.VBox(controls)
    
        return con_panel, parameters

    return gui_function
