import pickle
import json
import os
import numpy as np

DATA_FILE = "landmarks_data.pkl"
RECOGNITION_FILE = "recognition_data.pkl"
OUTPUT_DIR = "data_json"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def convert_to_serializable(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_to_serializable(v) for v in obj]
    return obj

def migrate_landmarks():
    print("Migrating landmarks...")
    if not os.path.exists(DATA_FILE):
        print(f"{DATA_FILE} not found")
        return
    
    with open(DATA_FILE, 'rb') as f:
        data = pickle.load(f)
    
    serializable_data = convert_to_serializable(data)
    with open(os.path.join(OUTPUT_DIR, "landmarks.json"), 'w') as f:
        json.dump(serializable_data, f)
    print("Landmarks migrated to landmarks.json")

def migrate_recognition():
    print("Migrating recognition data...")
    if not os.path.exists(RECOGNITION_FILE):
        print(f"{RECOGNITION_FILE} not found")
        return
    
    with open(RECOGNITION_FILE, 'rb') as f:
        data = pickle.load(f)
    
    # Recognition data is huge, let's process it carefully
    serializable_data = convert_to_serializable(data)
    with open(os.path.join(OUTPUT_DIR, "recognition.json"), 'w') as f:
        json.dump(serializable_data, f)
    print("Recognition data migrated to recognition.json")

migrate_landmarks()
migrate_recognition()
