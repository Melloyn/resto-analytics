import os
import requests
import logging
from typing import Optional

log = logging.getLogger(__name__)

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
                timeout=10
            )
            if resp.status_code == 200:
                href = resp.json().get("href")
                dl = requests.get(href, timeout=15)
                if dl.status_code == 200:
                    with open(local_path, 'wb') as f:
                        f.write(dl.content)
                    log.info(f"✅ Successfully downloaded {remote_path} to {local_path} ({len(dl.content)} bytes)")
                    return True
                else:
                    log.error(f"❌ Failed to download file bits from Yandex: {dl.status_code}")
                    raise RuntimeError(f"Yandex Disk download failed: HTTP {dl.status_code}")
            elif resp.status_code == 404:
                log.info(f"⚠️ Remote file {remote_path} not found on Yandex Disk (404).")
                return False
            else:
                log.error(f"❌ Failed to get download link from Yandex: {resp.status_code} {resp.text}")
                raise RuntimeError(f"Yandex Disk API error: HTTP {resp.status_code}")
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            log.error(f"❌ Network error while downloading {remote_path}: {e}")
            raise RuntimeError(f"Yandex Disk Network Error: {e}") from e

    def upload_file(self, local_path: str, remote_path: str, token: str) -> bool:
        if not token or not os.path.exists(local_path):
            return False
            
        headers = {'Authorization': f'OAuth {token}'}
        try:
            resp = requests.get(
                "https://cloud-api.yandex.net/v1/disk/resources/upload",
                headers=headers,
                params={'path': remote_path, 'overwrite': 'true'},
                timeout=10
            )
            
            # Auto-create directory structure if it is a fresh deployment
            if resp.status_code == 409:
                parent_dir = os.path.dirname(remote_path)
                log.info(f"⚠️ Upload returned 409 Conflict. Attempting to create directory: {parent_dir}")
                mkdir_resp = requests.put(
                    "https://cloud-api.yandex.net/v1/disk/resources",
                    headers=headers,
                    params={'path': parent_dir},
                    timeout=5
                )
                if mkdir_resp.status_code in [201, 409]:
                    resp = requests.get(
                        "https://cloud-api.yandex.net/v1/disk/resources/upload",
                        headers=headers,
                        params={'path': remote_path, 'overwrite': 'true'},
                        timeout=5
                    )
            
            if resp.status_code == 200:
                href = resp.json().get("href")
                with open(local_path, 'rb') as f:
                    # FIX: Use data=f for raw body upload, NOT files={'file': f} which injects multipart headers inside SQLite binary!
                    up = requests.put(href, data=f, timeout=15)
                    if up.status_code in [201, 202]:
                        log.info(f"✅ Successfully uploaded {local_path} to {remote_path}")
                        return True
                    else:
                        log.error(f"❌ Upload PUT failed: {up.status_code} {up.text}")
                        return False
            else:
                log.error(f"❌ Failed to get upload link: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            log.error(f"❌ Network error while uploading {local_path}: {e}")
            return False

    def get_file_info(self, remote_path: str, token: str) -> Optional[dict]:
        if not token: return None
        headers = {'Authorization': f'OAuth {token}'}
        try:
            resp = requests.get(
                "https://cloud-api.yandex.net/v1/disk/resources",
                headers=headers,
                params={'path': remote_path},
                timeout=5
            )
            if resp.status_code == 200:
                item = resp.json()
                if item.get("type") == "file":
                    return {"size": item.get("size", 0), "modified": item.get("modified")}
        except Exception as e:
            log.error(f"❌ Failed to get file info for {remote_path}: {e}")
        return None

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
