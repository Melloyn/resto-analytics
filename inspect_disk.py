import os
import requests
import json
import auth

def check_yandex_files():
    token = auth.get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
    if not token:
        print("No token found")
        return

    headers = {'Authorization': f'OAuth {token}'}
    try:
        resp = requests.get(
            "https://cloud-api.yandex.net/v1/disk/resources",
            headers=headers,
            params={"path": "RestoAnalytic", "limit": 100}
        )
        if resp.status_code == 200:
            items = resp.json().get("_embedded", {}).get("items", [])
            print("Files in RestoAnalytic:")
            for i in items:
                print(f"- {i['name']} ({i['type']})")
        else:
            print(f"Error: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    check_yandex_files()
