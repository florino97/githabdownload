import os
import requests
import threading

class LocalDownloader:
    def __init__(self):
        self.save_dir = os.path.join(os.path.expanduser('~'), 'Downloads', 'X-Fetch')
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def start_download(self, url, filename, progress_callback, finish_callback):
        def _download_thread():
            try:
                filepath = os.path.join(self.save_dir, filename)
                response = requests.get(url, stream=True, timeout=20)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress_callback(downloaded / total_size)
                                
                finish_callback(True, filepath)
            except Exception as e:
                finish_callback(False, str(e))
                
        threading.Thread(target=_download_thread, daemon=True).start()
