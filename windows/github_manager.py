from github import Github
import base64
import time

class GitHubManager:
    def __init__(self, pat, repo_name):
        self.g = Github(pat)
        self.repo = self.g.get_repo(repo_name)
        
    def trigger_download(self, url):
        try:
            try:
                readme = self.repo.get_contents("README.md")
                content = readme.decoded_content.decode('utf-8') + " \n"
                self.repo.update_file(
                    readme.path, 
                    f"download: {url}", 
                    content, 
                    readme.sha, 
                    branch="main"
                )
            except:
                self.repo.create_file(
                    "README.md", 
                    f"download: {url}", 
                    "Init repo", 
                    branch="main"
                )
            return True, "Task sent to GitHub successfully!"
        except Exception as e:
            return False, str(e)

    def get_downloadable_files(self):
        try:
            try:
                contents = self.repo.get_contents("downloads")
            except:
                contents = self.repo.get_contents("")
                
            files = []
            for file in contents:
                if file.type == "file" and file.name != "README.md":
                    files.append({
                        'name': file.name,
                        'download_url': file.download_url,
                        'path': file.path,
                        'sha': file.sha
                    })
            return True, files
        except Exception as e:
            return False, str(e)

    def delete_file(self, path, sha):
        try:
            self.repo.delete_file(path, f"Deleted {path}", sha, branch="main")
            return True
        except:
            return False
