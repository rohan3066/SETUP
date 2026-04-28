import pickle
import json
import os

DATA_FILE = "landmarks_data.pkl"
RECOGNITION_FILE = "recognition_data.pkl"

def explore_pkl(file_path, limit=2):
    if not os.path.exists(file_path):
        print(f"{file_path} not found")
        return
    
    with open(file_path, 'rb') as f:
        data = pickle.load(f)
        
    print(f"\n--- Exploring {file_path} ---")
    print(f"Type: {type(data)}")
    
    if isinstance(data, dict):
        print(f"Keys count: {len(data.keys())}")
        keys = list(data.keys())[:limit]
        for k in keys:
            val = data[k]
            if isinstance(val, dict):
                print(f"Key: {k}, Value Type: dict, Sub-keys: {list(val.keys())[:limit]}")
                if val:
                    first_sub_k = list(val.keys())[0]
                    sample = val[first_sub_k]
                    print(f"  Sample from {k}['{first_sub_k}']: Length={len(sample)}, First frame pts={len(sample[0]) if sample and len(sample)>0 else 'N/A'}")
            else:
                print(f"Key: {k}, Value Type: {type(val)}, Length/Size: {len(val) if hasattr(val, '__len__') else 'N/A'}")

explore_pkl(DATA_FILE)
explore_pkl(RECOGNITION_FILE)
