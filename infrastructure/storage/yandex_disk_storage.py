import os
import requests

class YandexDiskStorage:
    def download_file(self, remote_path: str, local_path: str, token: str, force: bool = False) -> bool:
        if not token:
            return False
        if os.path.exists(local_path) and not force:
            return True
            
        headers = {'Authorization': f'OAuth {token}'}
        try:
            resp = requests.get(
                "https://cloud-api.yandex.net/v1/disk/resources/download",
                headers=headers,
                params={'path': remote_path},
                timeout=5
            )
            if resp.status_code == 200:
                href = resp.json().get("href")
                dl = requests.get(href)
                if dl.status_code == 200:
                    with open(local_path, 'wb') as f:
                        f.write(dl.content)
                    return True
        except Exception:
            return False
        return False

    def upload_file(self, local_path: str, remote_path: str, token: str) -> bool:
        if not token or not os.path.exists(local_path):
            return False
            
        headers = {'Authorization': f'OAuth {token}'}
        try:
            resp = requests.get(
                "https://cloud-api.yandex.net/v1/disk/resources/upload",
                headers=headers,
                params={'path': remote_path, 'overwrite': 'true'},
                timeout=5
            )
            if resp.status_code == 200:
                href = resp.json().get("href")
                with open(local_path, 'rb') as f:
                    up = requests.put(href, files={'file': f})
                    return up.status_code in [201, 202]
        except Exception:
            return False
        return False
