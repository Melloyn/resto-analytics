import os
import pandas as pd
import requests
from io import BytesIO
import toml
import time
import data_engine

# Load secrets
try:
    secrets = toml.load(".streamlit/secrets.toml")
    YANDEX_TOKEN = secrets["YANDEX_TOKEN"]
except:
    YANDEX_TOKEN = os.getenv("YANDEX_TOKEN")

CACHE_FILE = "data_cache.parquet"
YANDEX_PATH = "Отчеты_Ресторан" # Make sure this matches your Yandex Disk folder

def sync_from_yandex():
    print(f"🔄 Starting Yandex Sync at {time.ctime()}")
    if not YANDEX_TOKEN:
        print("❌ No Yandex Token found.")
        return

    headers = {'Authorization': f'OAuth {YANDEX_TOKEN}'}
    api_url = 'https://cloud-api.yandex.net/v1/disk/resources'
    params = {'path': YANDEX_PATH, 'limit': 2000}
    
    try:
        # 1. List files
        response = requests.get(api_url, headers=headers, params=params, timeout=20)
        if response.status_code != 200:
            print(f"❌ Yandex API Error: {response.status_code}")
            return

        # 2. Recursive Scan
        data_frames = []
        dropped_summary = {'count': 0, 'cost': 0.0}
        
        # Check if root has subfolders
        items = response.json().get('_embedded', {}).get('items', [])
        
        folders = [i for i in items if i['type'] == 'dir']
        root_files = [i for i in items if i['type'] == 'file' and (i['name'].endswith('.xlsx') or i['name'].endswith('.csv'))]
        
        # Helper to process file using data_engine
        def process_and_collect(file_url, filename, venue):
            try:
                r = requests.get(file_url, headers=headers, timeout=20)
                df, err, warns, dropped = data_engine.process_single_file(BytesIO(r.content), filename)
                
                if dropped:
                    dropped_summary['count'] += dropped['count']
                    dropped_summary['cost'] += dropped['cost']

                if df is not None:
                    df['Venue'] = venue
                    data_frames.append(df)
                    print(f"   ✅ {filename} processed.")
                elif err:
                    print(f"   ⚠️ {filename}: {err}")
            except Exception as e:
                print(f"   ❌ Error {filename}: {e}")

        # Process Root Files
        for item in root_files:
            print(f"⬇️ Downloading {item['name']} (Root)...")
            process_and_collect(item['file'], item['name'], 'Mesto')

        # Process Subfolders
        for folder in folders:
            venue_name = folder['name']
            print(f"📂 Scanning Venue: {venue_name}...")
            
            # List files in subfolder
            sub_params = {'path': folder['path'], 'limit': 1000}
            sub_resp = requests.get(api_url, headers=headers, params=sub_params, timeout=20)
            if sub_resp.status_code == 200:
                sub_items = sub_resp.json().get('_embedded', {}).get('items', [])
                sub_files = [i for i in sub_items if i['type'] == 'file' and (i['name'].endswith('.xlsx') or i['name'].endswith('.csv'))]
                
                for item in sub_files:
                     process_and_collect(item['file'], item['name'], venue_name)
        
        if data_frames:
            full_df = pd.concat(data_frames, ignore_index=True)
            if 'Дата_Отчета' in full_df.columns:
                full_df = full_df.sort_values(by='Дата_Отчета')
            
            # 3. Save to Parquet Cache
            full_df.to_parquet(CACHE_FILE, index=False)
            print(f"✅ Success! Saved {len(full_df)} rows to {CACHE_FILE}")
            print(f"ℹ️ Dropped {dropped_summary['count']} rows (Total Cost: {dropped_summary['cost']:.2f})")
        else:
            print("⚠️ No data frames to save.")

    except Exception as e:
        print(f"❌ Sync failed: {e}")

if __name__ == "__main__":
    sync_from_yandex()
