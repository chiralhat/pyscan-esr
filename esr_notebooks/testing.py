import pickle

# Replace 'filename.pkl' with the path to your pickle file
with open('se_defaults.pkl', 'rb') as f:
    data = pickle.load(f)

# Now `data` contains the unpickled Python object
for item in data:
    print(item)