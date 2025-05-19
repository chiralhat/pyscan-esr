# Overview
Software for electron spin resonance experiments

## Frontend
A pyQt app

To build the fontend app run:
```
pyinstaller --onefile --windowed --app_icon=icon.ico gui.py
```
#### How to run:
```
cd esr/frontend
python gui.py
```

#### Frontend Features:
- Settings panel
  - Tooltips
- Graphs panel
  - Toggle graphed variable
  - Save graph with button
  - Right click on graph to copy to clipboard
  - Last saved graph path is displayed
- Error log
  - Displays errors and information about the currently running experiments
- Top menu bar
  - Switch experiment type
  - Initialize and run experiments
- Queue

#### How to edit the code and add an experiment type:
1. Update EXPERIMENT_TEMPLATES dictionary to include the new experiment type and all settings
2. Update gui/init_graphs_panel(), gui/toggle_start_stop_sweep_frontend(), and Worker/run_sweep() to display chosen graphs for your experiment type
3. Update gui/generate_default_display_name() in the queue to abbreviate name of new experiment
4. If adding new types of graphs, add them in graphing.py and adjust update_graph_signal calls in gui/toggle_start_stop_sweep_frontend() to point to these new functions
5. Update Worker/run_snapshot() to add any additional settings

#### How to add tooltips:
Add the key of the setting to the TOOLTIPS dictionary and the tooltip as the value
   
#### Notes
- There are two different pyscan folders, one in the frontend and one in the backend. The frontend version has all imports relating to the hardware commented out.

## Backend
A flask server
#### How to run:
```
cd esr/backend
python server.py
```
