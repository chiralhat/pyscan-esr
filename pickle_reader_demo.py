import pickle
import numpy as np
from PyQt5.QtWidgets import QTreeWidgetItem

def load_pickle_file(file_path):
    try:
        with open(file_path, 'rb') as file:
            data = pickle.load(file)
            return data
    except Exception as e:
        print(f"Error loading pickle file: {e}")
        return None

def display_data(data):
    if isinstance(data, dict):
        for key, value in data.items():
            print(f"{key}: {value}")
    else:
        print("Data is not in expected dictionary format.")

def populate_tree(tree_widget, data):
    tree_widget.clear()
    if isinstance(data, dict):
        for key, value in data.items():
            it