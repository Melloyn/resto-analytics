import requests
import toml
import os
import json

def get_token():
    try:
        config = toml.load(".streamlit/secrets.toml")
        return config.get("YANDEX_TOKEN")
    except Exception as e:
        print(f"Error reading secrets: {e}")
        return os.getenv("YANDEX_TOKEN")

def list_files(path):
    token = get_token()
    if not token:
        print("No token found")
        return

    headers = {'Authorization': f'OAuth {token}'}
    params = {'path': path, 'limit': 100}
    
    try:
        resp = requests.get("https://cloud-api.yandex.net/v1/disk/resources", headers=headers, params=params)
        if resp.status_code != 200:
            print(f"Error {resp.status_code}: {resp.text}")
            return

        data = resp.json()
        print(f"📂 Contents of '{path}':")
        if '_embedded' in data:
            items = data['_embedded']['items']
            for item in items:
                type_icon = "📁" if item['type'] == 'dir' else "📄"
                print(f"{type_icon} {item['name']} (Size: {item.get('size', 0)}, Created: {item.get('created')})")
        else:
            print("Empty or not a directory")

    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    list_files("RestoAnalytic")
