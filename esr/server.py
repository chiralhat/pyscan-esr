from flask import Flask, request, jsonify
import spinecho_scripts
import pulsesweep_scripts
import pyscan as ps

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

@app.route('/start', methods=['POST'])
def start():
    global running
    running = True
    print("Starting up server...")

    # insert your real code here to start sweep
    return jsonify({"status": "started"})

@app.route('/initialize_experiment', methods=['POST'])
def initialize_experiment():
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

    # Step 2: Extract data and handle it accordingly
    return jsonify({"parameters": parameters})

def serialize_sig(sig):
    result = {}
    for key in dir(sig):
        if key.startswith("_"):
            continue  # Skip private/internal
        try:
            value = getattr(sig, key)
            if callable(value):
                continue  # Skip methods
            if isinstance(value, np.ndarray):
                result[key] = value.tolist()  # Convert ndarray to list
            else:
                json.dumps(value)  # Test serializability
                result[key] = value
        except Exception:
            result[key] = str(value)  # Fallback: convert to string
    return result

@app.route('/run_snapshot', methods=['POST'])
def run_snapshot():
    # Get the data from the request
    data = request.get_json()  # Assuming the data sent is in JSON format
    print("Received data:", data)
    parameters = data.get('parameters')
    experiment_type = data.get('experiment type')

    prog = CPMGProgram(soc, parameters)
    measure_phase(prog, soc, sig)

    # if experiment_type == "Pulse Frequency Sweep Read Processed":
    #     # Freq for processed pulse frequency sweep
    #     freq = parameters['freq']

    #     fit, err = ps.plot_exp_fit_norange(np.array([sig.time, sig.x]), freq, 1)
    #     sig.fit = fit
    #     sig.freq = freq


    # Serialize all public attributes of `sig`
    serialized_sig = serialize_sig(sig)

    return jsonify({"sig": serialized_sig})

# prog = CPMGProgram(self.experiment.soc, self.experiment.parameters)
                # measure_phase(prog, self.experiment.soc, self.experiment.sig)
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

@app.route('/data', methods=['GET'])
def get_data():
    # Return dummy data for now
    data = {
        "time": [0, 1, 2, 3],
        "signal": [0.1, 0.5, 0.3, 0.9]
    }
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
