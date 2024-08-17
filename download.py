import requests
import os
import json

class FileBrowserFetcher:
    def __init__(self, url, username, password, download_path):
        self.url = url
        self.username = username
        self.password = password
        self.token = None
        self.download_path = download_path

    def get_token(self):
        print('Requesting access token...')
        response = requests.post(f'{self.url}/api/login', json={
            'username': self.username,
            'password': self.password
        })
        response.raise_for_status()
        self.token = response.text.strip('"')
        print('Access token received.')

    def fetch_recursively(self, dir_path='/'):
        print(f'Fetching directory: {dir_path}')
        response = requests.get(
            f'{self.url}/api/resources{dir_path}',
            headers={'X-Auth': self.token}
        )
        response.raise_for_status()
        
        print(f"Response content: {response.text[:200]}...") 
        
        try:
            content = response.json()
        except json.JSONDecodeError:
            print(f"Failed to parse JSON. Raw response: {response.text}")
            return

        if not isinstance(content, dict) or 'items' not in content:
            print(f"Unexpected response format. Expected a dict with 'items' key, got: {type(content)}")
            return

        items = content['items']
        for item in items:
            if not isinstance(item, dict):
                print(f"Unexpected item format. Expected a dict, got: {type(item)}")
                continue

            name = item.get('name')
            if name is None:
                print(f"Item is missing 'name' field: {item}")
                continue

            remote_path = os.path.join(dir_path, name)
            local_path = os.path.join(self.download_path, remote_path.lstrip('/').lstrip('\\'))

            if item.get('isDir'):
                os.makedirs(local_path, exist_ok=True)
                self.fetch_recursively(remote_path)
            else:
                print(f'Downloading: {remote_path}')
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

def main():
    url = 'http://localhost:8080'
    username = 'admin' # replace your username
    password = 'admin' # replace your username
    download_path = r'C:\Users\replace\your\path' # replace your path

    os.makedirs(download_path, exist_ok=True)

    fetcher = FileBrowserFetcher(url, username, password, download_path)

    try:
        fetcher.get_token()
        fetcher.fetch_recursively()
        print('All files and directories have been fetched successfully.')
    except Exception as e:
        print(f'An error occurred: {e}')

if __name__ == '__main__':
    main()