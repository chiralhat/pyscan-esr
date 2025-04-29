import pickle


def main():
    filename = "se_defaults.pkl" #Pickle file to view
    with open(filename, 'rb') as file:
        data = pickle.load(file)
        for key in data:
            print(key, ":", data[key])



if __name__ == "__main__":
    main()