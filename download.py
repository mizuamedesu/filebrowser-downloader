import requests
import os
import json
import time
from requests.exceptions import RequestException

class FileBrowserFetcher:
    def __init__(self, url, username, password, download_path):
        self.url = url
        self.username = username
        self.password = password
        self.token = None
        self.download_path = download_path
        self.max_retries = 3 # 失敗時の再試行回数
        self.retry_delay = 5 # 待機時間(秒)

    def get_token(self):
        print('Requesting access token...')
        for attempt in range(self.max_retries):
            try:
                response = requests.post(f'{self.url}/api/login', json={
                    'username': self.username,
                    'password': self.password
                })
                response.raise_for_status()
                self.token = response.text.strip('"')
                print('Access token received.')
                return
            except RequestException as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    raise

    def fetch_recursively(self, dir_path='/'):
        print(f'Fetching directory: {dir_path}')
        try:
            response = requests.get(
                f'{self.url}/api/resources{dir_path}',
                headers={'X-Auth': self.token}
            )
            response.raise_for_status()
            
            content = response.json()
            if not isinstance(content, dict) or 'items' not in content:
                print(f"Unexpected response format for {dir_path}. Skipping.")
                return

            items = content['items']
            for item in items:
                name = item.get('name')
                if name is None:
                    print(f"Item is missing 'name' field: {item}. Skipping.")
                    continue

                remote_path = os.path.join(dir_path, name)
                local_path = os.path.join(self.download_path, remote_path.lstrip('/').lstrip('\\'))

                if item.get('isDir'):
                    os.makedirs(local_path, exist_ok=True)
                    self.fetch_recursively(remote_path)
                else:
                    self.download_file(remote_path, local_path)

        except RequestException as e:
            print(f"Error fetching directory {dir_path}: {e}")

    def download_file(self, remote_path, local_path):
        if os.path.exists(local_path):
            print(f'File already exists, skipping: {local_path}')
            return

        print(f'Downloading: {remote_path}')
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    f'{self.url}/api/raw{remote_path}',
                    headers={'X-Auth': self.token},
                    stream=True
                )
                response.raise_for_status()
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f'Successfully downloaded: {remote_path}')
                return
            except RequestException as e:
                print(f"Attempt {attempt + 1} failed for {remote_path}: {e}")
                if attempt < self.max_retries - 1:
                    print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    print(f"Failed to download {remote_path} after {self.max_retries} attempts. Skipping.")

def main():
    url = 'http://localhot:8080' #replace
    username = 'admin' #replace
    password = 'admin' #replace
    download_path = r'C:\replace\your\path' #replace

    os.makedirs(download_path, exist_ok=True)

    fetcher = FileBrowserFetcher(url, username, password, download_path)

    try:
        fetcher.get_token()
        fetcher.fetch_recursively()
        print('All files and directories have been processed.')
    except Exception as e:
        print(f'An error occurred: {e}')

if __name__ == '__main__':
    main()
