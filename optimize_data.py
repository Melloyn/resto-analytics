import pandas as pd
import numpy as np
import time
import os

FILE_PATH = 'data.xlsx'
OUTPUT_PATH = 'data.parquet'

def optimize():
    print(f"📉 Loading {FILE_PATH}...")
    start_time = time.time()
    
    # Load Excel
    df = pd.read_excel(FILE_PATH)
    load_time = time.time() - start_time
    print(f"✅ Excel Loaded in {load_time:.2f} sec")
    
    # Save as Parquet
    print(f"💾 Saving to {OUTPUT_PATH}...")
    df.to_parquet(OUTPUT_PATH, index=False)
    print(f"✅ Saved!")

    # Verify formatting
    print(f"📉 Loading {OUTPUT_PATH}...")
    start_time = time.time()
    df_new = pd.read_parquet(OUTPUT_PATH)
    parquet_time = time.time() - start_time
    
    print(f"🚀 Parquet Loaded in {parquet_time:.2f} sec")
    print(f"⚡ Speedup: {load_time / parquet_time:.1f}x")
    
    # Check if dataframes are equal (basic check)
    print(f"Shape: {df.shape} -> {df_new.shape}")

if __name__ == "__main__":
    if os.path.exists(FILE_PATH):
        optimize()
    else:
        print(f"❌ File {FILE_PATH} not found.")
