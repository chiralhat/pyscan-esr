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

scopes = {'TBS1052C': ps.Tektronix1052B,
          'MSO24': ps.TektronixMSO2}

sweep_list = ['Pulse Sweep',
              'Phase Sweep',
              'Rabi',
              'Inversion Sweep',
              'Period Sweep',
              'Hahn Echo',
              'EDFS',
              'Freq Sweep',
              'CPMG']

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
              'DEER']

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
                            'use_psu': ipw.Checkbox(layout=wwid, description='Use PSU? (No magnet if not)'),
                           'use_temp': ipw.Checkbox(layout=wwid, description='Use Lakeshore?')},
                'rfsoc': {'freq': ipw.BoundedFloatText(min=50, max=14999, step=0.00001, layout=nwid,
                                                       description='Ch1 Freq (MHz)'),
                          'freq2': ipw.BoundedFloatText(min=50, max=14999, step=0.00001, layout=nwid,
                                                       description='Ch2 Freq (MHz)'),
                          'gain': ipw.BoundedIntText(layout=nwid, min=0, max=32500, step=1,
                                                        description='Ch1 Gain'),
                          'gain2': ipw.BoundedIntText(layout=nwid, min=0, max=32500, step=1,
                                                         description='Ch2 Gain'),
                          'phase': ipw.BoundedFloatText(layout=nwid, min=0, max=360, step=0.01,
                                                        description='Phase'),
                         'delay': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=1,
                                                       description='Ch1 Delay (ns)'),
                         'delay2': ipw.BoundedFloatText(layout=nwid, min=10, max=652100, step=1,
                                                       description='Ch2 Delay (ns)'),
                         'pulse1_1': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=1,
                                                        description='Ch1 90 Pulse (ns)'),
                         'pulse1_2': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=1,
                                                        description='Ch1 180 Pulse (ns)'),
                         'mult1': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=0.001,
                                                        description='Ch1 180 Pulse Mult'),
                         'pulse2_1': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=1,
                                                        description='Ch2 90 Pulse (ns)'),
                         'pulse2_2': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=1,
                                                        description='Ch2 180 Pulse (ns)'),
                         'mult2': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=0.001,
                                                        description='Ch2 180 Pulse Mult'),
                         'p2start': ipw.BoundedFloatText(layout=nwid, min=0, max=652100, step=1,
                                                        description='Ch2 Pulse Offset (ns)'),
                         'period': ipw.BoundedFloatText(100, min=0.1, max=20e9, step=0.001,
                                                         description='Repetition Time (us)'),
                         'pulses': ipw.Dropdown(layout=nwid, options=cpmgs, description='# 180 Pulses'),
                         'phase_sub': ipw.Checkbox(layout=nwid, description='Auto Phase Sub'),
                         'nutation_delay': ipw.BoundedFloatText(6e5, layout=nwid, min=0, max=655360, step=1,
                                                                description='Nut. Delay (ns)'),# style=lstyle),
                         'nutation_length': ipw.BoundedFloatText(layout=nwid, min=0, max=655360, step=1,
                                                                description='Nut. Pulse Width'),
                          'soft_avgs': ipw.BoundedIntText(layout=nwid, min=1, max=1e7, step=1,
                                                      description='Ave'),
                          'h_offset': ipw.BoundedFloatText(layout=nwid, min=-1e5, max=1e5,
                                                           description='Time Offset (us)'),
                          'readout_length': ipw.BoundedFloatText(layout=nwid, min=0, max=5, step=0.001,
                                               description='Readout Length (us)'),
                         'loopback': ipw.Checkbox(layout=nwid, description='Loopback')},
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
                                                     options=['Phase', 'Delay', 'Both', 'None', 'Autophase'],
                                                     description='Sub Method'),
                            'ave_reps': ipw.BoundedIntText(layout=nwid, min=1, max=1000,
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
                            'sweep2': ipw.Checkbox(description='Second sweep?'),
                            'expt2': ipw.Dropdown(layout=nwid,
                                                 options=sweep_list,
                                                 description='Experiment 2'),
                            'sweep2_start': ipw.FloatText(layout=nwid, description='Sweep 2 Start'),
                            'sweep2_end': ipw.FloatText(layout=nwid, description='Sweep 2 End'),
                            'sweep2_step': ipw.FloatText(layout=nwid, description='Sweep 2 Step'),
                            'turn_off': ipw.Checkbox(description='Turn off after sweep?'),
                            'integrate': ipw.Checkbox(description='Integral only')}
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
    def gui_function(sig, devices, sweep, soc):
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

            if 'ave_reps' in parameters.keys():
                reps = parameters['ave_reps']
            else:
                reps = 1
            if 'period' in parameters.keys():
                period = parameters['period']
            else:
                period = 500
            tmult = period/1e6*4*reps
            parameters['subtime'] = parameters['soft_avgs']*tmult
            datestr = date.today().strftime('%y%m%d')
            fname = datestr+'_'+str(parameters['file_name'])+'_'
            parameters['outfile'] = str(Path(parameters['save_dir']) / fname)
            with open(default_file, 'wb') as f:
                pickle.dump(parameters, f)
                
            inst = ps.ItemAttribute()
            
            if not hasattr(devices, "psu") and parameters["use_psu"]:
                try:
                    devices.psu = ps.MokuGo()
                except Exception as e:
                    print(f"Error initializing PSU: {e}")
            if not hasattr(devices, 'ls335') and parameters['use_temp']:
                devices.ls335 = ps.Lakeshore335()
                ttemp = devices.ls335.get_temp()
                # while 
            if (parameters['init'] or btn.description=='Initialize'):
                init_expt(devices, parameters, sweep, soc) # TODO: Fix the runinfo, expt bit (put into new dict?)
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
            if parameters['use_psu']:
                devices.psu.output = False
        
        with output:
            fig = plt.figure(figsize=(8, 5))
        #         setup_plot(output, fig)

        with measout:
            mfig = plt.figure(figsize=(8, 5))


        def start_sweep(btn):
            run_ind.value = 1
            set_pars(btn)
            runinfo = sweep['runinfo']
            expt = ps.Sweep(runinfo, devices, sweep['name'])
            sweep['expt'] = expt
            if parameters['expt']=="Hahn Echo":
                sweep['expt'].echo_delay = 2*np.array(runinfo.scan0.scan_dict['delay_sweep'])*runinfo.parameters['pulses']
            elif parameters['expt']=="CPMG":
                sweep['expt'].echo_delay = 2*runinfo.parameters['delay']*runinfo.scan0.scan_dict['cpmg_sweep']
            elif parameters['sweep2'] and parameters['expt2']=="Hahn Echo":
                sweep['expt'].echo_delay = 2*runinfo.scan1.scan_dict['delay_sweep']*runinfo.parameters['pulses']
            elif parameters['sweep2'] and parameters['expt2']=="CPMG":
                sweep['expt'].echo_delay = 2*runinfo.parameters['delay']*runinfo.scan1.scan_dict['cpmg_sweep']
            else:
                sweep['expt'].echo_delay = 2*runinfo.parameters['delay']*runinfo.parameters['pulses']
            run_sweep(sweep, parameters)#, measout, mfig)
            run_ind.value = 0

        
        def read_mon(btn):
            run_ind.value = 1
            set_pars(btn)
            read(sig, parameters, soc, output, fig)
            run_ind.value = 0
        
        
        def monitor(btn):
            run_ind.value = 1
            set_pars(btn)
            single_run(sig, parameters, soc, output, fig)
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
