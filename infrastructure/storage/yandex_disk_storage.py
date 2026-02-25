import os
import requests
from typing import Optional

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

    def list_directory(self, path: str, token: str, limit: int = 1000) -> list[dict]:
        if not token:
            return []
            
        headers = {'Authorization': f'OAuth {token}'}
        api_url = 'https://cloud-api.yandex.net/v1/disk/resources'
        items_acc = []
        offset = 0

        try:
            while True:
                params = {'path': path, 'limit': limit, 'offset': offset}
                resp = requests.get(api_url, headers=headers, params=params, timeout=20)
                if resp.status_code != 200:
                    break

                page_items = resp.json().get('_embedded', {}).get('items', [])
                if not page_items:
                    break

                items_acc.extend(page_items)
                if len(page_items) < limit:
                    break
                offset += limit
        except Exception:
            pass
            
        return items_acc

    def download_file_stream(self, file_url: str, token: str) -> Optional[bytes]:
        if not token or not file_url:
            return None
            
        headers = {'Authorization': f'OAuth {token}'}
        try:
            r = requests.get(file_url, headers=headers, timeout=20)
            if r.status_code == 200:
                return r.content
        except Exception:
            pass
        return None
