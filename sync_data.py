import os
import pandas as pd
import requests
from io import BytesIO
import toml
import time

# Load secrets
try:
    secrets = toml.load(".streamlit/secrets.toml")
    YANDEX_TOKEN = secrets["YANDEX_TOKEN"]
except:
    YANDEX_TOKEN = os.getenv("YANDEX_TOKEN")

CACHE_FILE = "data_cache.parquet"
YANDEX_PATH = "Отчеты_Ресторан" # Make sure this matches your Yandex Disk folder

def process_single_file(file_obj, filename):
    # Reuse the logic from app.py or simplified version
    # For now, simplistic read
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(file_obj)
        else:
            df = pd.read_excel(file_obj)
        
        # Add basic preprocessing if needed to match app.py
        # Ideally this code should be shared, but for now we duplicate small logic
        if 'Дата Открытия' in df.columns and 'Дата_Отчета' not in df.columns:
             df['Дата_Отчета'] = pd.to_datetime(df['Дата Открытия'], dayfirst=True)
        return df
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return None

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
        
        # Check if root has subfolders
        items = response.json().get('_embedded', {}).get('items', [])
        
        # We need to distinguish between files in root and folders (Venues)
        # Strategy: 
        # - Files in root -> Venue = 'General'
        # - Files in subfolder -> Venue = Subfolder Name
        
        folders = [i for i in items if i['type'] == 'dir']
        root_files = [i for i in items if i['type'] == 'file' and (i['name'].endswith('.xlsx') or i['name'].endswith('.csv'))]
        
        # Process Root Files
        for item in root_files:
            print(f"⬇️ Downloading {item['name']} (Root)...")
            try:
                file_resp = requests.get(item['file'], headers=headers, timeout=20)
                df = process_single_file(BytesIO(file_resp.content), item['name'])
                if df is not None:
                    df['Venue'] = 'General' # Default tag
                    data_frames.append(df)
            except Exception as e:
                print(f"❌ Error downloading {item['name']}: {e}")

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
                    print(f"   ⬇️ Downloading {item['name']}...")
                    try:
                        file_resp = requests.get(item['file'], headers=headers, timeout=20)
                        df = process_single_file(BytesIO(file_resp.content), item['name'])
                        if df is not None:
                            df['Venue'] = venue_name
                            data_frames.append(df)
                    except Exception as e:
                        print(f"   ❌ Error downloading {item['name']}: {e}")
        
        if data_frames:
            full_df = pd.concat(data_frames, ignore_index=True)
            if 'Дата_Отчета' in full_df.columns:
                full_df = full_df.sort_values(by='Дата_Отчета')
            
            # 3. Save to Parquet Cache
            full_df.to_parquet(CACHE_FILE, index=False)
            print(f"✅ Success! Saved {len(full_df)} rows to {CACHE_FILE}")
        else:
            print("⚠️ No data frames to save.")

    except Exception as e:
        print(f"❌ Sync failed: {e}")

if __name__ == "__main__":
    sync_from_yandex()
