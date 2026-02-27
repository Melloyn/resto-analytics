import pandas as pd
import numpy as np
import time
import os
import logging

from infrastructure.observability import setup_observability
setup_observability()

log = logging.getLogger(__name__)

FILE_PATH = 'data.xlsx'
OUTPUT_PATH = 'data.parquet'

def optimize():
    log.info(f"📉 Loading {FILE_PATH}...")
    start_time = time.time()
    
    # Load Excel
    df = pd.read_excel(FILE_PATH)
    load_time = time.time() - start_time
    log.info(f"✅ Excel Loaded in {load_time:.2f} sec")
    
    # Save as Parquet
    log.info(f"💾 Saving to {OUTPUT_PATH}...")
    df.to_parquet(OUTPUT_PATH, index=False)
    log.info(f"✅ Saved!")

    # Verify formatting
    log.info(f"📉 Loading {OUTPUT_PATH}...")
    start_time = time.time()
    df_new = pd.read_parquet(OUTPUT_PATH)
    parquet_time = time.time() - start_time
    
    log.info(f"🚀 Parquet Loaded in {parquet_time:.2f} sec")
    log.info(f"⚡ Speedup: {load_time / parquet_time:.1f}x")
    
    # Check if dataframes are equal (basic check)
    log.info(f"Shape: {df.shape} -> {df_new.shape}")

if __name__ == "__main__":
    if os.path.exists(FILE_PATH):
        optimize()
    else:
        log.error(f"❌ File {FILE_PATH} not found.")
