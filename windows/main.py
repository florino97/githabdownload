import customtkinter as ctk
import threading
import json
import os
from github_manager import GitHubManager
from local_downloader import LocalDownloader

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "config.json"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("X-Fetch | GitHub Downloader")
        self.geometry("900x600")
        self.downloader = LocalDownloader()
        self.gh_manager = None
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # --- Sidebar (Settings) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="X-Fetch", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.pat_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="GitHub PAT Token", show="*")
        self.pat_entry.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.repo_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="username/repo")
        self.repo_entry.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.connect_btn = ctk.CTkButton(self.sidebar_frame, text="Connect & Save", command=self.connect_github)
        self.connect_btn.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Status: Disconnected", text_color="gray")
        self.status_label.grid(row=4, column=0, padx=20, pady=10)
        
        # --- Main Workspace ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)
        
        # Top Bar (Input URL)
        self.input_frame = ctk.CTkFrame(self.main_frame)
        self.input_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.url_entry = ctk.CTkEntry(self.input_frame, placeholder_text="Paste YouTube/Twitter link here...", height=40)
        self.url_entry.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.send_btn = ctk.CTkButton(self.input_frame, text="Send to GitHub", height=40, command=self.send_task)
        self.send_btn.grid(row=0, column=1, padx=(0, 10), pady=10)
        
        # Action Bar (Refresh)
        self.action_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.action_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        self.refresh_btn = ctk.CTkButton(self.action_frame, text="🔄 Refresh Files List", command=self.refresh_files)
        self.refresh_btn.pack(side="left")
        
        # Files Listbox
        self.files_scroll = ctk.CTkScrollableFrame(self.main_frame)
        self.files_scroll.grid(row=2, column=0, sticky="nsew")
        
        # Bottom Progress
        self.progress_bar = ctk.CTkProgressBar(self.main_frame)
        self.progress_bar.grid(row=3, column=0, sticky="ew", pady=(20, 5))
        self.progress_bar.set(0)
        
        self.info_label = ctk.CTkLabel(self.main_frame, text="Ready.")
        self.info_label.grid(row=4, column=0, sticky="w")
        
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.pat_entry.insert(0, data.get('pat', ''))
                    self.repo_entry.insert(0, data.get('repo', ''))
            except: pass

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'pat': self.pat_entry.get(), 'repo': self.repo_entry.get()}, f)

    def connect_github(self):
        pat = self.pat_entry.get()
        repo = self.repo_entry.get()
        if not pat or not repo:
            self.status_label.configure(text="Please fill credentials!", text_color="#ff4a4a")
            return
            
        self.save_config()
        self.status_label.configure(text="Connecting...", text_color="white")
        
        def _connect():
            try:
                self.gh_manager = GitHubManager(pat, repo)
                # Test connection by getting repo name
                _ = self.gh_manager.repo.name
                self.after(0, lambda: self.status_label.configure(text="Status: Connected 🟢", text_color="#2ecc71"))
                self.after(0, self.refresh_files)
            except Exception as e:
                self.after(0, lambda: self.status_label.configure(text="Connection Failed 🔴", text_color="#ff4a4a"))
        
        threading.Thread(target=_connect, daemon=True).start()

    def send_task(self):
        url = self.url_entry.get()
        if not url or not self.gh_manager:
            return
            
        self.send_btn.configure(state="disabled", text="Sending...")
        self.info_label.configure(text="Triggering GitHub Actions...")
        
        def _send():
            success, msg = self.gh_manager.trigger_download(url)
            if success:
                self.after(0, lambda: self.info_label.configure(text="Task sent! GitHub is downloading. Wait a few mins and refresh.", text_color="#2ecc71"))
                self.after(0, lambda: self.url_entry.delete(0, 'end'))
            else:
                self.after(0, lambda: self.info_label.configure(text=f"Error: {msg}", text_color="#ff4a4a"))
            self.after(0, lambda: self.send_btn.configure(state="normal", text="Send to GitHub"))
            
        threading.Thread(target=_send, daemon=True).start()

    def refresh_files(self):
        if not self.gh_manager:
            return
            
        for widget in self.files_scroll.winfo_children():
            widget.destroy()
            
        self.refresh_btn.configure(state="disabled", text="Loading...")
        
        def _fetch():
            success, result = self.gh_manager.get_downloadable_files()
            if success:
                self.after(0, self.display_files, result)
            else:
                self.after(0, lambda: self.info_label.configure(text=f"Failed to load files: {result}", text_color="#ff4a4a"))
            self.after(0, lambda: self.refresh_btn.configure(state="normal", text="🔄 Refresh Files List"))
            
        threading.Thread(target=_fetch, daemon=True).start()

    def display_files(self, files):
        if not files:
            lbl = ctk.CTkLabel(self.files_scroll, text="No files found in repo.", text_color="gray")
            lbl.pack(pady=20)
            return
            
        for file in files:
            frame = ctk.CTkFrame(self.files_scroll, fg_color="#2b2b2b")
            frame.pack(fill="x", pady=5, padx=5)
            
            lbl = ctk.CTkLabel(frame, text=file['name'], font=ctk.CTkFont(weight="bold"))
            lbl.pack(side="left", padx=15, pady=15)
            
            del_btn = ctk.CTkButton(frame, text="Delete", width=60, fg_color="#ff4a4a", hover_color="#c0392b",
                                  command=lambda f=file: self.delete_file_from_github(f))
            del_btn.pack(side="right", padx=(5, 15))
            
            dl_btn = ctk.CTkButton(frame, text="Download to PC", width=120, 
                                 command=lambda f=file: self.download_to_local(f))
            dl_btn.pack(side="right", padx=5)

    def delete_file_from_github(self, file):
        self.info_label.configure(text=f"Deleting {file['name']}...", text_color="white")
        
        def _delete():
            success = self.gh_manager.delete_file(file['path'], file['sha'])
            if success:
                self.after(0, lambda: self.info_label.configure(text=f"Deleted {file['name']}.", text_color="#2ecc71"))
                self.after(0, self.refresh_files)
            else:
                self.after(0, lambda: self.info_label.configure(text="Failed to delete.", text_color="#ff4a4a"))
                
        threading.Thread(target=_delete, daemon=True).start()

    def download_to_local(self, file):
        self.info_label.configure(text=f"Downloading {file['name']} to your PC...", text_color="white")
        self.progress_bar.set(0)
        
        def update_progress(val):
            self.after(0, self.progress_bar.set, val)
            
        def on_finish(success, msg):
            if success:
                self.after(0, lambda: self.info_label.configure(text=f"Saved to: {msg}", text_color="#2ecc71"))
            else:
                self.after(0, lambda: self.info_label.configure(text=f"Download failed: {msg}", text_color="#ff4a4a"))
            self.after(0, self.progress_bar.set, 0)
            
        self.downloader.start_download(file['download_url'], file['name'], update_progress, on_finish)

if __name__ == "__main__":
    app = App()
    app.mainloop()
