import os
import pandas as pd
from io import BytesIO
import toml
import time
from services import data_loader
from infrastructure.storage.yandex_disk_storage import YandexDiskStorage
import toml
import time
from services import data_loader

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

    storage = YandexDiskStorage()
    
    try:
        # 1. List files
        # 2. Recursive Scan
        data_frames = []
        dropped_summary = {'count': 0, 'cost': 0.0}
        
        # Check if root has subfolders
        items = storage.list_directory(YANDEX_PATH, YANDEX_TOKEN, limit=1000)
        if not items:
            print("⚠️ No files found or failed to read root folder.")
            return
        
        folders = [i for i in items if i['type'] == 'dir']
        root_files = [i for i in items if i['type'] == 'file' and (i['name'].endswith('.xlsx') or i['name'].endswith('.csv'))]
        
        # Helper to process file using data_engine
        def process_and_collect(file_url, filename, venue):
            try:
                content = storage.download_file_stream(file_url, YANDEX_TOKEN)
                if not content:
                    print(f"   ❌ Network Error {filename}")
                    return
                    
                df, err, warns, dropped = data_loader.process_single_file(BytesIO(content), filename)
                
                if dropped:
                    dropped_summary['count'] += dropped['count']
                    dropped_summary['cost'] += dropped['cost']

                for warn in warns:
                    print(f"   ℹ️ {filename}: {warn}")

                if df is not None:
                    df['Точка'] = venue
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

            def get_files_recursive(path):
                all_files = []
                path_items = storage.list_directory(path, YANDEX_TOKEN, limit=1000)
                if not path_items:
                    return all_files

                files = [i for i in path_items if i['type'] == 'file' and (i['name'].endswith('.xlsx') or i['name'].endswith('.csv'))]
                dirs = [i for i in path_items if i['type'] == 'dir']
                all_files.extend(files)
                for d in dirs:
                    all_files.extend(get_files_recursive(d['path']))
                return all_files

            venue_files = get_files_recursive(folder['path'])
            for item in venue_files:
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
