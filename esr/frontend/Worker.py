"""
Worker.py

Defines the `Worker` class and associated utilities to offload experiment tasks (reading, sweeping)
into separate threads, keeping the GUI responsive during long operations.

Key Responsibilities:
- Communicates with `server.py` to run backend tasks like snapshot reads or sweeps.
- Emits Qt signals to update GUI elements and graphs.
- Deserializes experimental signal data returned from the backend using PyScan utilities.

Key Interactions:
- Instantiated and managed by `gui.py` for reading and sweeping.
- Receives experiment instances from `ExperimentType.py`.
"""

import matplotlib

matplotlib.use("Qt5Agg")  # Must be done before importing pyplot!
# Do not move the above from the top of the file

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import requests

import globals

import sys

sys.path.append("../")
# from rfsoc2 import *
import numpy as np
from time import sleep
import pyscan_non_soc_version as ps


def deserialize_obj(data):
    try:
        if isinstance(data, (int, float, str, bool)) or data is None:
            return data

        # If the data is a list, recursively deserialize all items
        if isinstance(data, list):
            return [deserialize_obj(item) for item in data]

        # If the data is a dictionary, process it
        if isinstance(data, dict):
            clsname = data.get("__class__")

            # First, deserialize all values into a temporary dictionary
            temp_data = {
                k: deserialize_obj(v)
                for k, v in data.items()
                if k != "__class__"  # Remove the class name from the dictionary
            }

            # Handle known classes by directly creating objects
            if clsname == "FunctionScan":
                function = temp_data.get(
                    "function", lambda x: x
                )  # fallback if no function
                values = list(temp_data.get("scan_dict", {}).values())[0]
                obj = ps.FunctionScan(function=function, values=values)
                for k, v in temp_data.items():
                    setattr(obj, k, v)
                return obj

            elif clsname == "PropertyScan":
                prop = temp_data.get("prop")
                input_dict = temp_data.get("input_dict", {})

                # Create PropertyScan object with valid arguments
                obj = ps.PropertyScan(prop=prop, input_dict=input_dict)

                for k, v in temp_data.items():
                    if k not in ["prop", "input_dict"]:  # Only pass valid arguments
                        setattr(obj, k, v)

                return obj

            elif clsname == "RunInfo":
                obj = ps.RunInfo()  # Create a new RunInfo object
                for k, v in temp_data.items():
                    # Avoid unexpected arguments that don't belong in the constructor
                    if k not in [
                        "average_d"
                    ]:  # Adjust this based on your RunInfo constructor
                        setattr(obj, k, v)
                return obj

            elif clsname == "ItemAttribute":
                obj = ps.ItemAttribute()  # Instantiate the ItemAttribute object
                for k, v in temp_data.items():
                    setattr(obj, k, v)
                return obj

            elif clsname == "Sweep":
                # Make sure we are deserializing into a Sweep object
                runinfo_data = temp_data.get("runinfo")
                devices_data = temp_data.get("devices")

                # Deserialize runinfo and devices to their respective objects
                runinfo = (
                    deserialize_obj(runinfo_data)
                    if isinstance(runinfo_data, dict)
                    else runinfo_data
                )
                devices = (
                    deserialize_obj(devices_data)
                    if isinstance(devices_data, dict)
                    else devices_data
                )

                # Create the Sweep object directly
                obj = ps.Sweep(runinfo=runinfo, devices=devices)

                # Now set the remaining attributes for the Sweep object
                for k, v in temp_data.items():
                    if k not in [
                        "runinfo",
                        "devices",
                    ]:  # Skip these two as they are already set
                        setattr(obj, k, v)

                return obj  # Directly return the Sweep object

            elif clsname == "Experiment":
                # Handle the Experiment object deserialization
                runinfo_data = temp_data.get("runinfo")
                devices_data = temp_data.get("devices")

                # Deserialize runinfo and devices to their respective objects
                runinfo = (
                    deserialize_obj(runinfo_data)
                    if isinstance(runinfo_data, dict)
                    else runinfo_data
                )
                devices = (
                    deserialize_obj(devices_data)
                    if isinstance(devices_data, dict)
                    else devices_data
                )

                # Create the Experiment object directly
                obj = ps.Experiment(runinfo=runinfo, devices=devices)

                # Now set the remaining attributes for the Experiment object
                for k, v in temp_data.items():
                    if k not in [
                        "runinfo",
                        "devices",
                    ]:  # Skip these two as they are already set
                        setattr(obj, k, v)

                return obj  # Directly return the Experiment object
            elif clsname == "Signal":
                obj = ps.ItemAttribute()  # or however the Signal object is instantiated
                for k, v in temp_data.items():
                    if k in ["x", "time"] and isinstance(v, list):
                        setattr(obj, k, np.array(v, dtype=np.float64))
                    else:
                        setattr(obj, k, deserialize_obj(v))
                return obj
            else:
                # Fallback: if it's an unknown class, return as a plain dictionary
                return temp_data

        return data  # If the data isn't a dict, list, or primitive, return it as is

    except Exception as e:
        print(f"Error deserializing data: {e}")
        raise


class PyscanObject:
    def __init__(self, data_dict):
        for key, value in data_dict.items():
            if isinstance(value, list):
                # Assume lists are originally numpy arrays
                setattr(self, key, np.array(value))
            else:
                setattr(self, key, value)


def recursive_deserialize(data):
    if isinstance(data, dict):
        return Sig(**data)  # If it's a dictionary, deserialize it into a Sig object
    elif isinstance(data, list):
        return [recursive_deserialize(item) for item in data]  # Handle lists
    else:
        return data  # If it's a primitive value, just return it


def deserialize_sig(sig_data):
    return recursive_deserialize(sig_data)


class Worker(QObject):
    """
    A generic worker that runs one of three tasks in a separate thread:
      - read_processed
      - read_unprocessed
      - start_sweep
    We pass in the current_experiment and which task we want to run.
    """

    finished = pyqtSignal()
    updateStatus = pyqtSignal(str)
    plot_update_signal = pyqtSignal(object)
    dataReady_se = pyqtSignal(object, object)
    dataReady_ps = pyqtSignal(object, object)
    live_plot_2D_update_signal = pyqtSignal(object)
    live_plot_1D_update_signal = pyqtSignal(object)

    def __init__(self, experiment, task_name, combo_2d=None, combo_1d=None):
        super().__init__()
        self.experiment = experiment
        self.task_name = task_name
        self.stop_requested = False
        self.combo_2d = combo_2d
        self.combo_1d = combo_1d

    @pyqtSlot()
    def run_snapshot(self):
        """
        Runs the desired method on the experiment in this separate thread
        so the main GUI thread won't freeze.
        """
        try:
            if self.task_name == "read_processed":
                self.updateStatus.emit("Reading processed data...\n")

                # Prepare data and handle specific experiment types
                if self.experiment.type == "Spin Echo":
                    # Change parameters for read
                    single = self.experiment.parameters["single"]
                    self.experiment.parameters["single"] = self.experiment.parameters[
                        "loopback"
                    ]
                    
                    data = {
                        "parameters": self.experiment.parameters,
                        "experiment type": "Spin Echo Read Processed",
                    }

                    print("about to ask server")
                    # Send request to server
                    try:
                        response = requests.post(
                            globals.server_address + "/run_snapshot", json=data
                        )
                    except Exception as e:
                        self.updateStatus.emit(f"Error in connecting to server: {e}\n")
                    print("asked server")

                    # Handle server response
                    if response.ok:
                        response_data = response.json()
                        self.experiment.sig = deserialize_obj(response_data["sig"])
                    else:
                        print("Error:", response.status_code, response.text)
                    self.experiment.parameters["single"] = single

                elif self.experiment.type == "Pulse Frequency Sweep":
                    data = {
                        "parameters": self.experiment.parameters,
                        "experiment type": "Pulse Frequency Sweep Read Processed",
                    }
                    print("about to ask server")
                    # Send request to server
                    response = requests.post(
                        globals.server_address + "/run_snapshot", json=data
                    )
                    print("asked server")
                    # Handle server response
                    if response.ok:
                        response_data = response.json()
                        self.experiment.sig = deserialize_obj(response_data["sig"])
                        self.experiment.sig.x = np.array(self.experiment.sig.x)
                    else:
                        print("Error:", response.status_code, response.text)
                    freq = self.experiment.parameters["freq"]
                    self.experiment.sig.freq = freq
                self.updateStatus.emit("Done reading processed data.\n")

            elif self.task_name == "read_unprocessed":
                self.updateStatus.emit("Reading unprocessed data...\n")

                if self.experiment.type == "Spin Echo":
                    single = self.experiment.parameters["single"]
                    avgs = self.experiment.parameters["soft_avgs"]
                    self.experiment.parameters["single"] = True
                    self.experiment.parameters["soft_avgs"] = 1
                    data = {
                        "parameters": self.experiment.parameters,
                        "experiment type": "Spin Echo Read Unprocessed",
                    }
                    print("about to ask server")
                    response = requests.post(
                        globals.server_address + "/run_snapshot", json=data
                    )
                    print("asked server")
                    if response.ok:
                        response_data = response.json()
                        self.experiment.sig = deserialize_obj(response_data["sig"])
                    else:
                        print("Error:", response.status_code, response.text)

                    self.experiment.parameters["single"] = single
                    self.experiment.parameters["soft_avgs"] = avgs

                elif self.experiment.type == "Pulse Frequency Sweep":
                    self.experiment.parameters["single"] = True
                    self.experiment.parameters["soft_avgs"] = 1
                    data = {
                        "parameters": self.experiment.parameters,
                        "experiment type": "Pulse Frequency Sweep Read Unprocessed",
                    }

                    response = requests.post(
                        globals.server_address + "/run_snapshot", json=data
                    )

                    if response.ok:
                        response_data = response.json()
                        self.experiment.sig = deserialize_obj(response_data["sig"])
                    else:
                        print("Error:", response.status_code, response.text)

                self.updateStatus.emit("Done reading unprocessed data.\n")

            # Emit signals based on experiment type for plotting
            if self.experiment.type == "Spin Echo":
                self.dataReady_se.emit(self.experiment.sig, self.task_name)
            elif self.experiment.type == "Pulse Frequency Sweep":
                self.dataReady_ps.emit(self.experiment.sig, self.task_name)

            self.finished.emit()
        except Exception as e:
            print()
            print("Error when running snapshot:")
            print(e)
            print()

    @pyqtSlot()
    def run_sweep(self):
        try:
            self.updateStatus.emit("Starting sweep in worker thread…\n")
            self.stop_requested = False
            self.running = True

            print("Starting sweep in worker thread…")
            # Initiate sweep on the server
            self.experiment.sweep_running = True
            data = {
                "parameters": self.experiment.parameters,
                "experiment type": self.experiment.type,
                "sweep": self.experiment.sweep,
            }
            response = requests.post(globals.server_address + "/start_sweep", json=data)
            if response.ok:
                self.running = True
            else:
                print("Error:", response.status_code, response.text)
                return

            last_data_2d = None
            last_data_1d = None

            # Continuously fetch data until sweep stops or is requested to stop
            while not self.stop_requested and self.running:
                response = requests.get(globals.server_address + "/get_sweep_data")
                if response.ok:
                    response_data = response.json()
                    self.experiment.expt = deserialize_obj(
                        response_data["expt"]["serialized_experiment"]
                    )
                    print("Deserialized expt")
                else:
                    print("Error:", response.status_code, response.text)

                if not self.experiment.expt.runinfo.running:
                    self.running = False
                    break
                
                # Generate and emit updated plots
                if self.experiment.expt.runinfo.measured:
                    data_name_2d = self.combo_2d.currentText()
                    pg_2D = ps.PlotGenerator(
                        expt=self.experiment.expt,
                        d=2,
                        x_name="t",
                        y_name=self.experiment.parameters["y_name"],
                        data_name=data_name_2d,
                        transpose=1,
                    )

                    if self.experiment.type == "Spin Echo":
                        data_name_1d = self.combo_1d.currentText()
                        pg_1D = ps.PlotGenerator(
                            expt=self.experiment.expt,
                            d=1,
                            x_name=self.experiment.parameters["y_name"],
                            data_name=data_name_1d,
                        )

                    if last_data_2d is None or not np.array_equal(
                        pg_2D.data, last_data_2d
                    ):
                        last_data_2d = pg_2D.data.copy()
                        self.live_plot_2D_update_signal.emit(pg_2D)

                    if self.experiment.type == "Spin Echo":
                        if last_data_1d is None or not np.array_equal(
                            pg_1D.data, last_data_1d
                        ):
                            last_data_1d = pg_1D.data.copy()
                            self.live_plot_1D_update_signal.emit(pg_1D)
                sleep(1)

            # final emitting of plots when sweep is over
            if self.experiment.expt.runinfo.measured:
                try:
                    data_name_2d = self.combo_2d.currentText()
                    pg_2D = ps.PlotGenerator(
                        expt=self.experiment.expt,
                        d=2,
                        x_name="t",
                        y_name=self.experiment.parameters["y_name"],
                        data_name=data_name_2d,
                        transpose=1,
                    )
                    if self.experiment.type == "Spin Echo":
                        data_name_1d = self.combo_1d.currentText()
                        pg_1D = ps.PlotGenerator(
                            expt=self.experiment.expt,
                            d=1,
                            x_name=self.experiment.parameters["y_name"],
                            data_name=data_name_1d,
                        )

                    self.live_plot_2D_update_signal.emit(pg_2D)

                    if self.experiment.type == "Spin Echo":
                        self.live_plot_1D_update_signal.emit(pg_1D)

                except Exception as e:
                    self.updateStatus.emit(f"Error final plot update: {e}\n")

            # Final status update
            if self.stop_requested:
                self.updateStatus.emit("Stop request detected. Exiting sweep early.\n")
            else:
                self.updateStatus.emit("Done sweeping (normal exit).\n")

            self.finished.emit()

        except Exception as e:
            print()
            print("Error running sweep:")
            print(e)
            print()

    @pyqtSlot()
    def stop_sweep(self):
        """
        Slot to request the worker to stop. Sets a flag that can be checked in the run_sweep method, killing the thread.
        """
        try:
            pass
            # self.stop_requested = True
            # if 'expt' in self.experiment.sweep:
            #     self.experiment.sweep['expt'].runinfo.running = False
        except Exception as e:
            print()
            print("Error stopping sweep")
            print(e)
            print()
