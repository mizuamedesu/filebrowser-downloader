import requests
import os
import json
import time
from requests.exceptions import RequestException
from urllib.parse import quote

class FileBrowserFetcher:
    def __init__(self, url, username, password, download_path):
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.token = None
        self.download_path = download_path
        self.max_retries = 3
        self.retry_delay = 5

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

    def normalize_path(self, path):
        return path.replace('\\', '/').strip('/')

    def check_set_class_b_file(self, dir_path):
        normalized_path = self.normalize_path(dir_path)
        try:
            response = requests.get(
                f'{self.url}/api/resources/{quote(normalized_path)}',
                headers={'X-Auth': self.token}
            )
            response.raise_for_status()
            content = response.json()
            if isinstance(content, dict) and 'items' in content:
                for item in content['items']:
                    if item.get('name') == 'set.classB':
                        return True
            return False
        except RequestException:
            return False

    def check_set_skip_file(self, dir_path):
        normalized_path = self.normalize_path(dir_path)
        try:
            response = requests.get(
                f'{self.url}/api/resources/{quote(normalized_path)}',
                headers={'X-Auth': self.token}
            )
            response.raise_for_status()
            content = response.json()
            if isinstance(content, dict) and 'items' in content:
                for item in content['items']:
                    if item.get('name') == 'set.skip':
                        return True
            return False
        except RequestException:
            return False

    def explore_and_fetch(self, dir_path='/'):
        normalized_path = self.normalize_path(dir_path)
        print(f'Exploring directory: /{normalized_path}')
        try:
            if self.check_set_skip_file(normalized_path):
                print(f'Found set.skip file in /{normalized_path}. Skipping this directory and its contents.')
                return False

            if self.check_set_class_b_file(normalized_path):
                print(f'Found set.classB file in /{normalized_path}. Downloading contents...')
                self.download_directory_contents(normalized_path)
                return True
            
            response = requests.get(
                f'{self.url}/api/resources/{quote(normalized_path)}',
                headers={'X-Auth': self.token}
            )
            response.raise_for_status()
            
            content = response.json()
            if not isinstance(content, dict) or 'items' not in content:
                print(f"Unexpected response format for /{normalized_path}. Skipping.")
                return False

            items = content['items']
            for item in items:
                name = item.get('name')
                if name is None:
                    print(f"Item is missing 'name' field: {item}. Skipping.")
                    continue

                if item.get('isDir'):
                    sub_dir_path = f"{normalized_path}/{name}"
                    if self.explore_and_fetch(sub_dir_path):
                        return True

            return False

        except RequestException as e:
            print(f"Error exploring directory /{normalized_path}: {e}")
            return False

    def download_directory_contents(self, dir_path):
        normalized_path = self.normalize_path(dir_path)
        try:
            response = requests.get(
                f'{self.url}/api/resources/{quote(normalized_path)}',
                headers={'X-Auth': self.token}
            )
            response.raise_for_status()
            
            content = response.json()
            if not isinstance(content, dict) or 'items' not in content:
                print(f"Unexpected response format for /{normalized_path}. Skipping.")
                return

            items = content['items']
            for item in items:
                name = item.get('name')
                if name is None:
                    print(f"Item is missing 'name' field: {item}. Skipping.")
                    continue

                remote_path = f"{normalized_path}/{name}"
                local_path = os.path.join(self.download_path, remote_path)

                if item.get('isDir'):
                    if not self.check_set_skip_file(remote_path):
                        os.makedirs(local_path, exist_ok=True)
                        self.download_directory_contents(remote_path)
                    else:
                        print(f'Skipping directory due to set.skip file: /{remote_path}')
                else:
                    self.download_file(remote_path, local_path)

        except RequestException as e:
            print(f"Error downloading directory contents /{normalized_path}: {e}")

    def download_file(self, remote_path, local_path):
        if os.path.exists(local_path):
            print(f'File already exists, skipping: {local_path}')
            return

        normalized_path = self.normalize_path(remote_path)
        print(f'Downloading: /{normalized_path}')
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    f'{self.url}/api/raw/{quote(normalized_path)}',
                    headers={'X-Auth': self.token},
                    stream=True
                )
                response.raise_for_status()
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f'Successfully downloaded: /{normalized_path}')
                return
            except RequestException as e:
                print(f"Attempt {attempt + 1} failed for /{normalized_path}: {e}")
                if attempt < self.max_retries - 1:
                    print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    print(f"Failed to download /{normalized_path} after {self.max_retries} attempts. Skipping.")

def main():
    url = 'http://localhost:8080'  # replace
    username = 'admin'  # replace
    password = 'admin'  # replace
    download_path = r'C:\replace'  # replace
    
    os.makedirs(download_path, exist_ok=True)

    fetcher = FileBrowserFetcher(url, username, password, download_path)

    try:
        fetcher.get_token()
        fetcher.explore_and_fetch()
        print('All files and directories have been processed.')
    except Exception as e:
        print(f'An error occurred: {e}')

if __name__ == '__main__':
    main()
