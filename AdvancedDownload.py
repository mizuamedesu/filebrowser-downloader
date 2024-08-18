import requests
import os
import json
import time
import hashlib
from requests.exceptions import RequestException
from urllib.parse import quote, unquote

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
        return unquote(path.replace('\\', '/').strip('/'))

    def encode_path(self, path):
        return quote(self.normalize_path(path))

    def check_set_class_b_file(self, dir_path):
        normalized_path = self.normalize_path(dir_path)
        encoded_path = self.encode_path(dir_path)
        try:
            response = requests.get(
                f'{self.url}/api/resources/{encoded_path}',
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
        encoded_path = self.encode_path(dir_path)
        try:
            response = requests.get(
                f'{self.url}/api/resources/{encoded_path}',
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
        encoded_path = self.encode_path(dir_path)
        print(f'Exploring directory: /{normalized_path}')
        try:
            if self.check_set_skip_file(normalized_path):
                print(f'Found set.skip file in /{normalized_path}. Skipping this directory and its contents.')
                return

            if self.check_set_class_b_file(normalized_path):
                print(f'Found set.classB file in /{normalized_path}. Downloading contents...')
                self.download_directory_contents(normalized_path)

            response = requests.get(
                f'{self.url}/api/resources/{encoded_path}',
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

                if item.get('isDir'):
                    sub_dir_path = f"{normalized_path}/{name}"
                    self.explore_and_fetch(sub_dir_path)

        except RequestException as e:
            print(f"Error exploring directory /{normalized_path}: {e}")

    def download_directory_contents(self, dir_path):
        normalized_path = self.normalize_path(dir_path)
        encoded_path = self.encode_path(dir_path)
        try:
            response = requests.get(
                f'{self.url}/api/resources/{encoded_path}',
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

    def calculate_file_hash(self, file_path):
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def get_remote_checksum(self, remote_path):
        encoded_path = self.encode_path(remote_path)
        checksum_url = f'{self.url}/api/resources/{encoded_path}?checksum=sha256'
        response = requests.get(checksum_url, headers={'X-Auth': self.token})
        response.raise_for_status()
        file_info = response.json()
        return file_info['checksums']['sha256']

    def download_file(self, remote_path, local_path):
        normalized_path = self.normalize_path(remote_path)
        encoded_path = self.encode_path(remote_path)
        print(f'Checking: /{normalized_path}')
        
        for attempt in range(self.max_retries):
            try:
                remote_checksum = self.get_remote_checksum(remote_path)
                print(f"Remote checksum: {remote_checksum}")

                if os.path.exists(local_path):
                    local_checksum = self.calculate_file_hash(local_path)
                    if local_checksum == remote_checksum:
                        print(f'File unchanged, skipping: {local_path}')
                        return
                    else:
                        print(f'File changed, updating: {local_path}')

                response = requests.get(
                    f'{self.url}/api/raw/{encoded_path}',
                    headers={'X-Auth': self.token},
                    stream=True
                )
                response.raise_for_status()
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                hash_sha256 = hashlib.sha256()
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        hash_sha256.update(chunk)
                        f.write(chunk)
                
                downloaded_checksum = hash_sha256.hexdigest()
                print(f"Calculated checksum during download: {downloaded_checksum}")
                
                file_checksum = self.calculate_file_hash(local_path)
                print(f"Calculated checksum after download: {file_checksum}")
                
                if file_checksum != remote_checksum:
                    print(f"Checksum mismatch for {local_path}")
                    print(f"Remote checksum: {remote_checksum}")
                    print(f"Local checksum: {file_checksum}")
                    print(f"File size: {os.path.getsize(local_path)} bytes")
                    raise Exception(f"Checksum mismatch for {local_path}")
                
                print(f'Successfully downloaded and verified: /{normalized_path}')
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
    download_path = r'C:\replace\your\path'  # replace
    
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
