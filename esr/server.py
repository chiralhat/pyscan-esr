from flask import Flask, request, jsonify
import spinecho_scripts
import pulsesweep_scripts
import pyscan as ps
from time import sleep, time

import sys, os
sys.path.append('../')
from rfsoc2 import *

app = Flask(__name__)

# Example experiment runner
running = False
soc = QickSoc() #Hardware interface for the RFSoC system.
soccfg = soc #Alias for soc, used for compatibility.
devices = ps.ItemAttribute() #Container for hardware components (e.g., PSU, temperature controller).
sig = ps.ItemAttribute() #Container for storing acquired signal data.
expt = None
sweep = None
scopes = {'TBS1052C': ps.Tektronix1052B,
          'MSO24': ps.TektronixMSO2}

@app.route('/start', methods=['POST'])
def start():
    global running
    running = True
    print("Starting up server...")

    # insert your real code here to start sweep
    return jsonify({"status": "started"})

@app.route('/initialize_experiment', methods=['POST'])
def initialize_experiment():
    global sweep
    # Step 1: Get the data from the request
    data = request.get_json()  # Assuming the data sent is in JSON format
    print("Received data:", data)
    parameters = data.get('parameters')
    sweep = data.get('sweep')
    experiment_type = data.get("experiment type")

    inst = ps.ItemAttribute()

    # Initialize PSU if necessary
    if not hasattr(devices, 'psu') and parameters['use_psu']:
        psu_address = parameters.get('psu_address', '').strip()
        if psu_address:
            waddr = psu_address.split('ASRL')[-1].split('::')[0]
            try:
                devices.psu = ps.GPD3303S(waddr)
            except Exception as e:
                print(f"Error initializing PSU: {e}")
        else:
            print("Error: PSU address is not provided or invalid.")

    # Initialize temperature device if necessary
    if not hasattr(devices, 'ls335') and parameters['use_temp']:
        devices.ls335 = ps.Lakeshore335()
        temp = devices.ls335.get_temp()

    """This initializes a pyscan experiment with functions from the correct 
        experiment type scripts and GUI files."""
    if experiment_type == "Spin Echo":
        # Initialize the experiment by setting up the parameters and devices.
        parameters['pulse1_2'] = parameters['pulse1_1'] * parameters['mult1']
        parameters['pi2_phase'] = 0
        parameters['pi_phase'] = 90
        parameters['cpmg_phase'] = 0
        channel = 1 if parameters['loopback'] else 0
        parameters['res_ch'] = channel
        parameters['ro_chs'] = [channel]
        parameters['reps'] = 1
        parameters['single'] = parameters['loopback']
        
        if parameters['use_psu'] and not parameters['loopback']:
            devices.psu.set_magnet(parameters)

        spinecho_scripts.setup_experiment(parameters, devices, sweep, soc) #From ______scripts.py

    elif experiment_type == "Pulse Frequency Sweep":
        #self.pulsesweep_gui = psg.PulseSweepExperiment(self.graph)
        # Initialize experiment parameters and devices.
        parameters['pulses'] = 0
        parameters['pulse1_2'] = parameters['pulse1_1']
        parameters['pi2_phase'] = 0
        parameters['pi_phase'] = 90
        parameters['delay'] = 300
        parameters['cpmg_phase'] = 0
        channel = 1 if parameters['loopback'] else 0
        parameters['res_ch'] = channel
        parameters['ro_chs'] = [channel]
        parameters['nutation_delay'] = 5000
        parameters['nutation_length'] = 0
        parameters['reps'] = 1
        parameters['sweep2'] = 0
        parameters['single'] = parameters['loopback'] # ADDED THIS LINE
        if parameters['use_psu']:
            devices.psu.set_magnet(parameters)

        pulsesweep_scripts.setup_experiment(parameters, devices, sweep, soc)

    print(sweep)
    # if 'runinfo' in sweep:
    #     sweep['runinfo'] = serialize_object(sweep['runinfo'])
    # Step 2: Extract data and handle it accordingly
    return jsonify({"parameters": parameters})

def serialize_object(obj, max_depth=5, _depth=0):
    if _depth > max_depth:
        return str(obj)  # Prevent deep recursion

    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj

    if isinstance(obj, dict):
        return {k: serialize_object(v, max_depth, _depth+1) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [serialize_object(v, max_depth, _depth+1) for v in obj]

    # Handle common serializable NumPy-like containers
    try:
        import numpy as np
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except ImportError:
        pass

    # For known serializable classes (like PyScan's scans), use their attributes
    if hasattr(obj, '__dict__'):
        return {
            '__class__': obj.__class__.__name__,
            **{k: serialize_object(v, max_depth, _depth+1)
               for k, v in vars(obj).items()
               if not k.startswith('_') and not callable(v)}
        }

    return str(obj)  # Fallback for anything else
    # result = {}
    # for key in dir(object):
    #     if key.startswith("_"):
    #         continue  # Skip private/internal
    #     try:
    #         value = getattr(object, key)
    #         if callable(value):
    #             continue  # Skip methods
    #         if isinstance(value, np.ndarray):
    #             result[key] = value.tolist()  # Convert ndarray to list
    #         else:
    #             json.dumps(value)  # Test serializability
    #             result[key] = value
    #     except Exception:
    #         result[key] = str(value)  # Fallback: convert to string
    # return result

@app.route('/run_snapshot', methods=['POST'])
def run_snapshot():
    # Get the data from the request
    data = request.get_json()  # Assuming the data sent is in JSON format
    print("Received data:", data)
    parameters = data.get('parameters')
    experiment_type = data.get('experiment type')

    prog = CPMGProgram(soc, parameters)
    measure_phase(prog, soc, sig)

    # Serialize all public attributes of `sig`
    serialized_sig = serialize_object(sig)
    print(serialized_sig)

    return jsonify({"sig": serialized_sig})

@app.route('/start_sweep', methods=['POST'])
def start_sweep():
    global sweep
    global expt
    if expt and expt.runinfo.running:
        print("sweep in progress, try again later")
        return jsonify({"status": "sweep in progress, try again later"})
    else:
        """starts up the hardware to run a sweep and runs a sweep"""
        # Get the data from the request
        data = request.get_json()  # Assuming the data sent is in JSON format
        print("Received data:", data)
        parameters = data.get('parameters')
        experiment_type = data.get('experiment type')
        #sweep = data.get('sweep')

        runinfo = sweep['runinfo']
        expt = ps.Sweep(runinfo, devices, sweep['name'])

        if experiment_type == "Spin Echo":  
            if parameters['expt']=="Hahn Echo":
                expt.echo_delay = 2*np.array(runinfo.scan0.scan_dict['delay_sweep'])*runinfo.parameters['pulses']
            elif parameters['expt']=="CPMG":
                expt.echo_delay = 2*runinfo.parameters['delay']*runinfo.scan0.scan_dict['cpmg_sweep']
            elif parameters['sweep2'] and parameters['expt2']=="Hahn Echo":
                expt.echo_delay = 2*runinfo.scan1.scan_dict['delay_sweep']*runinfo.parameters['pulses']
            elif parameters['sweep2'] and parameters['expt2']=="CPMG":
                expt.echo_delay = 2*runinfo.parameters['delay']*runinfo.scan1.scan_dict['cpmg_sweep']
            else:
                expt.echo_delay = 2*runinfo.parameters['delay']*runinfo.parameters['pulses']

        print(expt)
        expt.start_time = time()
        expt.start_thread()
        return jsonify({"status": "sweep started"})

@app.route('/get_sweep_data', methods=['GET'])
def get_sweep_data():
    global expt
    print("returning experiment data")
    response = {
        "serialized_experiment": serialize_object(expt),
    }
    print(expt.runinfo.measured)
    return jsonify({"expt": serialize_object(response)})

@app.route('/get_scopes', methods=['GET'])
def get_scopes():
    return jsonify(scopes)

#### I THINK THIS WILL TURN OFF THE SERVER
@app.route('/stop', methods=['POST'])
def stop():
    global running
    running = False
    print("Stopping experiment...")
    # insert your real code here to stop sweep
    return jsonify({"status": "stopped"})

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"running": running})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
