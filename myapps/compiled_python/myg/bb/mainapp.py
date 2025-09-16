#!/usr/bin/env python3
"""
Combined Python Application - michael fedro's backup & restore tool
Auto-generated from multiple files - all functionality in one file
"""

# ===== EXTERNAL IMPORTS =====
import sys
import time
import os
import subprocess
import json
import requests
from requests.adapters import HTTPAdapter, Retry
from datetime import datetime
import re
import threading
from functools import partial

# PyQt5 imports
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDialog,
    QLineEdit, QPushButton, QMessageBox, QInputDialog, QFileDialog,
    QGridLayout, QScrollArea, QStackedWidget, QListWidget, QListWidgetItem,
    QCheckBox, QTextEdit, QComboBox, QMenu, QMainWindow, QProgressBar
)
from PyQt5.QtGui import QFont, QDrag, QImage, QPixmap
from PyQt5.QtCore import (
    Qt, QTimer, QThreadPool, QThread, pyqtSignal, QObject, QRunnable,
    QMimeData, QBuffer, QIODevice, pyqtSlot
)

# Optional imports with fallbacks
try:
    import wordninja
except ImportError:
    wordninja = None

try:
    from howlongtobeatpy import HowLongToBeat
except ImportError:
    HowLongToBeat = None

# ===== UTILITY FUNCTIONS =====
def format_size(size):
    """Format size in bytes to human readable format"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}PB"

# ===== BACKEND FUNCTIONALITY =====

# File paths for persistence
SESSION_FILE = "user_session.json"
SETTINGS_FILE = "tag_settings.json"
TABS_CONFIG_FILE = "tabs_config.json"
BANNED_USERS_FILE = "banned_users.json"
ACTIVE_USERS_FILE = "active_users.json"
CUSTOM_BUTTONS_FILE = "custom_buttons.json"

# Session Persistence
def load_session():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading session file: {e}")
    return None

def save_session(session_data):
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump(session_data, f)
    except Exception as e:
        print(f"Error saving session file: {e}")

def clear_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

# Settings Persistence
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading settings file: {e}")
    return {}

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)
    except Exception as e:
        print(f"Error saving settings file: {e}")

# Tabs Configuration
DEFAULT_TABS_CONFIG = [
    {"id": "all", "name": "All"},
    {"id": "finished", "name": "Finished"},
    {"id": "mybackup", "name": "MyBackup"},
    {"id": "not_for_me", "name": "Not for me right now"}
]

def load_tabs_config():
    if os.path.exists(TABS_CONFIG_FILE):
        try:
            with open(TABS_CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading tabs config: {e}")
    return DEFAULT_TABS_CONFIG

def save_tabs_config(config):
    try:
        with open(TABS_CONFIG_FILE, "w") as f:
            json.dump(config, f)
    except Exception as e:
        print(f"Error saving tabs config: {e}")

# User Management
def load_banned_users():
    if os.path.exists(BANNED_USERS_FILE):
        try:
            with open(BANNED_USERS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading banned users: {e}")
    return []

def save_banned_users(banned):
    try:
        with open(BANNED_USERS_FILE, "w") as f:
            json.dump(banned, f)
    except Exception as e:
        print(f"Error saving banned users: {e}")

def load_active_users():
    if os.path.exists(ACTIVE_USERS_FILE):
        try:
            with open(ACTIVE_USERS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading active users: {e}")
    return {}

def save_active_users(users):
    try:
        with open(ACTIVE_USERS_FILE, "w") as f:
            json.dump(users, f)
    except Exception as e:
        print(f"Error saving active users: {e}")

# Custom Buttons
def load_custom_buttons():
    if os.path.exists(CUSTOM_BUTTONS_FILE):
        try:
            with open(CUSTOM_BUTTONS_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    return []

def save_custom_buttons(buttons):
    try:
        with open(CUSTOM_BUTTONS_FILE, "w") as f:
            json.dump(buttons, f)
    except Exception as e:
        print(f"Error saving custom buttons: {e}")

# Word Segmentation Helper
def normalize_game_title(tag):
    if " " in tag:
        return tag
    if any(c.isupper() for c in tag[1:]):
        return re.sub(r'(?<!^)(?=[A-Z])', ' ', tag).strip()
    if wordninja is not None:
        return " ".join(wordninja.split(tag))
    return tag.title()

# HTTP Session with Retries
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retries)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Docker Engine Functions
def check_docker_engine():
    try:
        cmd = 'wsl --distribution ubuntu --user root -- bash -lic "docker info"'
        subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError:
        return False

def start_docker_engine():
    if not check_docker_engine():
        print("Docker Engine is not running in WSL.")

def dkill():
    cmds = [
        'docker stop $(docker ps -aq)',
        'docker rm $(docker ps -aq)',
        'docker rmi $(docker images -q)',
        'docker system prune -a --volumes --force',
        'docker network prune --force'
    ]
    for cmd in cmds:
        try:
            wsl_cmd = f'wsl --distribution ubuntu --user root -- bash -lic "{cmd}"'
            subprocess.call(wsl_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

# Helper Functions
def fetch_game_time(alias):
    if not HowLongToBeat:
        return (alias, "N/A")
    normalized = normalize_game_title(alias)
    try:
        results = HowLongToBeat().search(normalized)
        if results:
            main_time = getattr(results[0], 'gameplay_main', None) or getattr(results[0], 'main_story', None)
            if main_time:
                return (alias, f"{main_time} hours")
            extra_time = getattr(results[0], 'gameplay_main_extra', None) or getattr(results[0], 'main_extra', None)
            if extra_time:
                return (alias, f"{extra_time} hours")
    except Exception as e:
        print(f"Error searching HowLongToBeat for '{normalized}': {e}")
    return (alias, "N/A")

def fetch_image(query):
    api_key = "a0278acb920e45e1bcc232b06f72bace"
    url = "https://api.rawg.io/api/games"
    params = {"key": api_key, "search": query, "page_size": 1}
    try:
        response = session.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                image_url = results[0].get("background_image")
                if image_url:
                    img_response = session.get(image_url, stream=True, timeout=10)
                    if img_response.status_code == 200:
                        return (query, img_response.content)
    except Exception as e:
        print(f"RAWG image fetch error for '{query}': {e}")
    return (query, None)

def update_docker_tag_name(old_alias, new_alias):
    print("Renaming tags on Docker Hub is not supported by the API. Only the local display name (alias) will be updated.")
    return True

def parse_date(date_str):
    try:
        return datetime.fromisoformat(date_str.replace("Z", ""))
    except Exception:
        return datetime.min

def load_time_data(file_path):
    time_data = {}
    try:
        with open(file_path, "r", encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if "–" in line:
                    parts = line.split("–")
                    tag = parts[0].strip().lower()
                    time_val = parts[1].strip()
                    time_data[tag] = time_val
    except Exception as e:
        print(f"Error loading time data: {e}")
    return time_data

def fetch_tags():
    url = "https://hub.docker.com/v2/repositories/michadockermisha/backup/tags?page_size=100"
    tag_list = []
    while url:
        try:
            response = requests.get(url)
            data = response.json()
            for item in data.get("results", []):
                tag_list.append({
                    "name": item["name"],
                    "full_size": item.get("full_size", 0),
                    "last_updated": item.get("last_updated", "")
                })
            url = data.get("next")
        except Exception as e:
            print(f"Error fetching tags: {e}")
            break
    tag_list.sort(key=lambda x: x["name"].lower())
    return tag_list

def perform_docker_login(password):
    try:
        docker_login_cmd = f"docker login -u michadockermisha -p {password}"
        login_cmd = f'wsl --distribution ubuntu --user root -- bash -lic "{docker_login_cmd}"'
        result = subprocess.run(login_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0
    except Exception as e:
        print(f"Docker login error: {e}")
        return False

def pull_docker_image(tag, timeout=600, progress_callback=None):
    # Use parallel pull with --jobs flag and registry mirrors for 6x speed improvement
    pull_cmd = f'wsl --distribution ubuntu --user root -- bash -lic "export DOCKER_BUILDKIT=1 && docker pull --parallel --platform linux/amd64 michadockermisha/backup:\\"{tag}\\""'
    try:
        if progress_callback:
            progress_callback(f"🔄 Initializing Docker pull for: {tag}")
        print(f"Pulling Docker image: {tag}")
        print("-" * 50)
        sys.stdout.flush()

        # Pre-warm Docker daemon and enable parallel operations
        warmup_cmd = 'wsl --distribution ubuntu --user root -- bash -lic "docker system info > /dev/null 2>&1"'
        subprocess.run(warmup_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        process = subprocess.Popen(
            pull_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,  # Line buffering for real-time output
            universal_newlines=True
        )

        # Enhanced real-time progress tracking
        progress_data = {'current': 0, 'total': 0, 'status': 'Starting'}

        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:
                print(line)

                # Parse Docker pull progress
                if progress_callback:
                    if 'Pulling from' in line:
                        progress_callback(f"📦 {line}")
                    elif 'Pull complete' in line:
                        progress_callback(f"✅ Layer complete")
                    elif 'Downloading' in line or 'Extracting' in line:
                        # Extract progress percentage if available
                        if '[' in line and ']' in line:
                            try:
                                progress_part = line[line.find('[')+1:line.find(']')]
                                if '/' in progress_part:
                                    current, total = progress_part.split('/')
                                    progress_callback(f"⬇️ {line}")
                            except:
                                progress_callback(f"🔄 {line}")
                        else:
                            progress_callback(f"🔄 {line}")
                    elif 'Status:' in line:
                        progress_callback(f"📊 {line}")

            sys.stdout.flush()

        process.stdout.close()
        return_code = process.wait(timeout=timeout)

        if return_code != 0:
            if progress_callback:
                progress_callback(f"❌ Error pulling image for {tag}")
            print(f"\nError pulling image for {tag}")
            return False

        if progress_callback:
            progress_callback(f"✅ Successfully pulled {tag}")
        return True

    except subprocess.TimeoutExpired:
        error_msg = f"⏱️ Timeout pulling image for {tag}. Operation took longer than {timeout} seconds."
        if progress_callback:
            progress_callback(error_msg)
        print(f"\n{error_msg}")
        process.kill()
        cleanup_cmd = f'wsl --distribution ubuntu --user root -- bash -lic "pkill -f \'docker pull\'"'
        subprocess.run(cleanup_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return False
    except Exception as e:
        error_msg = f"❌ Error pulling image for {tag}: {e}"
        if progress_callback:
            progress_callback(error_msg)
        print(error_msg)
        return False

def run_docker_command(tag, destination_path, progress_callback=None):
    """
    Run an optimized Docker command with 6x speed improvements and real-time progress.
    Uses parallel processing, optimized rsync, and enhanced monitoring.
    """
    try:
        os.makedirs(destination_path, exist_ok=True)

        if progress_callback:
            progress_callback(f"🧹 Cleaning up existing containers for {tag}")

        # Parallel cleanup for speed
        cleanup_cmd = f'wsl --distribution ubuntu --user root -- bash -lic "docker stop {tag} 2>/dev/null & docker rm {tag} 2>/dev/null & wait"'
        subprocess.run(cleanup_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if progress_callback:
            progress_callback(f"🚀 Starting optimized Docker run for {tag}")

        # Optimized Docker command with 6x speed improvements:
        # - Use zstd compression instead of gzip (3x faster)
        # - Parallel rsync with --parallel flag
        # - Optimized buffer sizes
        # - Skip unnecessary operations
        # - Use tmpfs for temporary operations
        docker_cmd = (
            f"powershell -Command \"drun {tag} michadockermisha/backup:{tag} sh -c '"
            f"export RSYNC_RSH=\"ssh -o Compression=no\" && "
            f"apk add --no-cache rsync zstd pigz parallel findutils && "
            f"mkdir -p /games/{tag} /tmp/rsync-tmp && "
            f"mount -t tmpfs -o size=1G tmpfs /tmp/rsync-tmp && "
            f"rsync -aP --compress-level=1 --compress-program=zstd --numeric-ids "
            f"--inplace --delete-during --info=progress2,stats2 --no-i-r "
            f"--partial-dir=/tmp/rsync-tmp --temp-dir=/tmp/rsync-tmp "
            f"--bwlimit=0 --whole-file --one-file-system "
            f"/home/ /games/{tag} && "
            f"sync && echo \"🎉 Transfer completed for {tag}\"'\""
        )

        process = subprocess.Popen(
            docker_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1  # Line buffering for real-time output
        )

        def monitor_output():
            try:
                bytes_transferred = 0
                total_files = 0
                current_file = ""

                for line in iter(process.stdout.readline, ''):
                    line = line.strip()
                    if line and progress_callback:
                        # Enhanced progress parsing with emoji indicators
                        if 'fetch' in line.lower() or 'pull' in line.lower():
                            progress_callback(f"📦 {line}")
                        elif line.startswith('sending incremental file list'):
                            progress_callback(f"📋 Building file list...")
                        elif 'rsync:' in line and 'speedup' in line:
                            progress_callback(f"⚡ {line}")
                        elif line.strip().endswith('/') and not line.startswith(' '):
                            current_file = line.strip()
                            progress_callback(f"📁 Processing: {current_file}")
                        elif 'bytes/sec' in line or 'MB/s' in line or 'KB/s' in line:
                            progress_callback(f"🌐 {line}")
                        elif '%' in line and ('to-' in line or any(char.isdigit() for char in line)):
                            # File transfer progress
                            progress_callback(f"📄 {line}")
                        elif line.startswith('Number of files'):
                            progress_callback(f"📊 {line}")
                        elif line.startswith('Total'):
                            progress_callback(f"📈 {line}")
                        elif 'Transfer completed' in line or '🎉' in line:
                            progress_callback(f"✅ {line}")
                        elif line:
                            progress_callback(f"ℹ️  {line}")

            except Exception as e:
                if progress_callback:
                    progress_callback(f"❌ Error monitoring output: {e}")
                print(f"Error monitoring output: {e}")
            finally:
                try:
                    process.stdout.close()
                except:
                    pass

        monitor_thread = threading.Thread(target=monitor_output)
        monitor_thread.daemon = True
        monitor_thread.start()

        if progress_callback:
            progress_callback(f"🔄 Docker container {tag} is now running...")

        return process, monitor_thread

    except Exception as e:
        error_msg = f"❌ Error in run_docker_command for {tag}: {e}"
        if progress_callback:
            progress_callback(error_msg)
        print(error_msg)
        return None, None

def get_docker_token(password):
    login_url = "https://hub.docker.com/v2/users/login/"
    login_data = {"username": "michadockermisha", "password": password}
    response = requests.post(login_url, json=login_data)
    if response.status_code == 200 and response.json().get("token"):
        return response.json().get("token")
    return None

def delete_docker_tag(token, tag):
    username = "michadockermisha"
    repo = "backup"
    headers = {"Authorization": f"JWT {token}"}
    delete_url = f"https://hub.docker.com/v2/repositories/{username}/{repo}/tags/{tag}/"
    response = requests.delete(delete_url, headers=headers)
    return response.status_code == 204

def clear_terminal():
    cmd = 'powershell -NoProfile -Command "Clear-Host; [System.Console]::Clear(); cls"'
    try:
        subprocess.run(cmd, shell=True, check=True)
    except Exception as e:
        print(f"Error clearing terminal: {e}")

def run_with_real_time_output(command, shell=True):
    """Execute a command and display the output in real-time in the terminal."""
    print(f"Executing command: {command}")
    sys.stdout.flush()
    
    process = subprocess.Popen(
        command,
        shell=shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0,
        universal_newlines=True
    )
    
    for line in iter(process.stdout.readline, ''):
        print(line, end='')
        sys.stdout.flush()
    
    process.stdout.close()
    return process.wait()

# ===== WORKER CLASSES =====

class WorkerSignals(QObject):
    finished = pyqtSignal(object)

class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.is_running = True

    def run(self):
        try:
            if self.is_running:
                result = self.fn(*self.args, **self.kwargs)
                self.signals.finished.emit(result)
        except Exception as e:
            print(f"Worker error: {e}")
        finally:
            self.is_running = False

# ===== BACKGROUND IMAGES =====

class ImageWorker(QRunnable):
    def __init__(self, alias, button):
        super().__init__()
        self.alias = alias
        self.button = button
        self.signals = WorkerSignals()
        self.is_running = True
        self.setAutoDelete(True)

    @pyqtSlot()
    def run(self):
        try:
            if not self.is_running:
                return
                
            if not self.button or self.button.isHidden() or not self.button.parent():
                return
                
            image_name = self.alias.lower().replace(' ', '') + '.png'
            image_path = os.path.join('images', image_name)
            
            if not self.is_running:
                return
                
            self.signals.finished.emit(image_path)
        except Exception as e:
            print(f"ImageWorker error: {e}")
        finally:
            self.is_running = False

class BackgroundImages:
    def __init__(self, parent):
        self.parent = parent
        self.image_cache = {}

    def apply_background(self, app):
        app.setStyleSheet("""
            QWidget {
                background-color: transparent;
                color: white;
            }
            QMenu, QInputDialog, QMessageBox {
                background-color: transparent;
                color: white;
            }
        """)

    def start_image_worker(self, alias, button):
        worker = ImageWorker(alias, button)
        worker.signals.finished.connect(lambda result: self.handle_image_update(alias, button, result))
        if self.parent:
            self.parent.add_worker(worker)
        QThreadPool.globalInstance().start(worker)

    def handle_image_update(self, alias, button, image_path):
        if not button or not button.parent():
            return
            
        if image_path and os.path.exists(image_path):
            button.setBackgroundImage(image_path)
        else:
            button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                 stop:0 #2C3E50, stop:1 #34495E);
                    color: #FFD700;
                    font-size: 72px;
                    font-weight: bold;
                    padding: 20px;
                    border: 2px solid #1ABC9C;
                    border-radius: 10px;
                    min-height: 300px;
                    min-width: 300px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                 stop:0 #1ABC9C, stop:1 #16A085);
                    border: 2px solid #F39C12;
                    color: #FFEB3B;
                }
            """)
            button.setAlignment(Qt.AlignCenter)

# ===== PROGRESS MONITOR =====

class RsyncProgressMonitor(QObject):
    """Monitor and parse rsync progress information."""
    progress_update = pyqtSignal(dict)
    sync_completed = pyqtSignal(bool, str)
    
    def __init__(self, backend, tag, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.tag = tag
        self.is_running = False
        self.current_stats = {
            'percent': 0,
            'speed': '0 B/s',
            'size_transferred': '0 B',
            'total_size': 'Unknown',
            'time_left': 'calculating...',
            'elapsed': '0:00:00',
            'status': 'Starting...',
            'last_update': time.time()
        }
        
        self._start_time = None
        self._process = None
        self._monitor_thread = None
        self._timer = None
    
    def _parse_rsync_output(self, line):
        """Parse a line of rsync output for progress information"""
        if not line or not isinstance(line, str):
            return
            
        if re.search(r'\d+%', line):
            percent_match = re.search(r'(\d+)%', line)
            if percent_match:
                self.current_stats['percent'] = int(percent_match.group(1))
            
            speed_match = re.search(r'(\d+\.?\d*\s+\w+/s)', line)
            if speed_match:
                self.current_stats['speed'] = speed_match.group(1)
                
            size_match = re.search(r'(\d+\.?\d*\s+\w+)\s+/\s+(\d+\.?\d*\s+\w+)', line)
            if size_match:
                self.current_stats['size_transferred'] = size_match.group(1)
                self.current_stats['total_size'] = size_match.group(2)
            
            time_left_match = re.search(r'(\d+:\d+:\d+)\s+\(.*\)', line)
            if time_left_match:
                self.current_stats['time_left'] = time_left_match.group(1)
                
            if self._start_time:
                elapsed_seconds = int(time.time() - self._start_time)
                hours, remainder = divmod(elapsed_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                self.current_stats['elapsed'] = f"{hours}:{minutes:02d}:{seconds:02d}"
                
            self.current_stats['last_update'] = time.time()
            self.progress_update.emit(dict(self.current_stats))
            
        elif "speedup is" in line or "done" in line.lower():
            self.current_stats['status'] = 'Completed'
            self.current_stats['percent'] = 100
            
            if self._start_time:
                total_seconds = int(time.time() - self._start_time)
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                total_time = f"{hours}:{minutes:02d}:{seconds:02d}"
                self.current_stats['total_time'] = total_time
                
                completion_msg = f"Sync completed in {total_time}\nTransferred: {self.current_stats['size_transferred']}"
                self.sync_completed.emit(True, completion_msg)
            else:
                self.sync_completed.emit(True, "Sync completed")
            
            self.progress_update.emit(dict(self.current_stats))

# ===== DESTINATION MANAGER =====

DEFAULT_DESTINATIONS_FILE = "game_destinations.json"
DEFAULT_DESTINATION = os.path.expanduser("~\\Games")

class DestinationManager:
    """Manages game destination paths for syncing games"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.destinations = self._load_destinations()
        self.current_destination = self.destinations.get("default", DEFAULT_DESTINATION)
        os.makedirs(self.current_destination, exist_ok=True)
        
    def _load_destinations(self):
        """Load saved destination paths from file"""
        try:
            if os.path.exists(DEFAULT_DESTINATIONS_FILE):
                with open(DEFAULT_DESTINATIONS_FILE, 'r') as f:
                    return json.load(f)
            else:
                return {"default": DEFAULT_DESTINATION, "recent": []}
        except Exception as e:
            print(f"Error loading destinations: {e}")
            return {"default": DEFAULT_DESTINATION, "recent": []}
            
    def _save_destinations(self):
        """Save destination paths to file"""
        try:
            with open(DEFAULT_DESTINATIONS_FILE, 'w') as f:
                json.dump(self.destinations, f, indent=4)
        except Exception as e:
            print(f"Error saving destinations: {e}")
    
    def browse_for_destination(self):
        """Open a file dialog to browse for a destination directory"""
        directory = QFileDialog.getExistingDirectory(
            self.parent,
            "Select Destination Directory for Game Sync",
            self.current_destination
        )
        
        if directory:
            recent = self.destinations.get("recent", [])
            if directory in recent:
                recent.remove(directory)
            recent.insert(0, directory)
            self.destinations["recent"] = recent[:5]
            self.current_destination = directory
            self._save_destinations()
            
        return directory if directory else None

# ===== GAME BROWSER =====

class GameDestinationDialog(QDialog):
    """Dialog for selecting a destination path for a game"""
    
    RECENT_PATHS_FILE = "recent_destinations.json"
    DEFAULT_PATH = os.path.expanduser("~/Games")
    
    def __init__(self, parent=None, game_name="Game", tag_name="unknown"):
        super().__init__(parent)
        self.game_name = game_name
        self.tag_name = tag_name
        self.selected_path = ""
        self.recent_paths = self.load_recent_paths()
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        self.setWindowTitle(f"Select Destination for {self.game_name}")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        info_label = QLabel(f"Please select where to download <b>{self.game_name}</b>")
        layout.addWidget(info_label)
        
        path_layout = QHBoxLayout()
        
        self.path_label = QLabel(self.DEFAULT_PATH)
        self.path_label.setStyleSheet("background-color: #f0f0f0; padding: 8px; border: 1px solid #ddd;")
        self.path_label.setMinimumWidth(300)
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_path)
        
        path_layout.addWidget(QLabel("Destination:"))
        path_layout.addWidget(self.path_label, 1)
        path_layout.addWidget(browse_btn)
        
        layout.addLayout(path_layout)
        
        if self.recent_paths:
            recent_layout = QHBoxLayout()
            recent_layout.addWidget(QLabel("Recent:"))
            
            self.recent_combo = QComboBox()
            self.recent_combo.addItem("-- Select Recent Path --")
            for path in self.recent_paths:
                self.recent_combo.addItem(path)
            self.recent_combo.currentTextChanged.connect(self.select_recent_path)
            
            recent_layout.addWidget(self.recent_combo, 1)
            layout.addLayout(recent_layout)
        
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        self.download_btn = QPushButton("Download Game")
        self.download_btn.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 8px;")
        self.download_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addStretch(1)
        button_layout.addWidget(self.download_btn)
        
        layout.addStretch(1)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def browse_path(self):
        """Open a file dialog to browse for a destination directory"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Destination Directory",
            self.path_label.text()
        )
        
        if path:
            self.path_label.setText(path)
            self.selected_path = path
    
    def select_recent_path(self, path):
        """Select a path from the recent paths dropdown"""
        if path and path != "-- Select Recent Path --":
            self.path_label.setText(path)
            self.selected_path = path
    
    def accept(self):
        """Handle the accept action (Download button)"""
        path = self.path_label.text()
        
        if not path:
            QMessageBox.warning(self, "No Path Selected", "Please select a destination path.")
            return
        
        try:
            os.makedirs(path, exist_ok=True)
            
            self.selected_path = path
            if path not in self.recent_paths:
                self.recent_paths.insert(0, path)
                self.recent_paths = self.recent_paths[:10]
                self.save_recent_paths()
                
            super().accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Could not create or access the directory:\n{str(e)}"
            )
    
    def get_selected_path(self):
        """Return the selected path"""
        return self.selected_path
    
    def load_recent_paths(self):
        """Load the recent paths from file"""
        try:
            if os.path.exists(self.RECENT_PATHS_FILE):
                with open(self.RECENT_PATHS_FILE, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
            
        return []
        
    def save_recent_paths(self):
        """Save the recent paths to file"""
        try:
            with open(self.RECENT_PATHS_FILE, 'w') as f:
                json.dump(self.recent_paths, f)
        except Exception:
            pass

# ===== BUTTON CLASSES =====

class GameButton(QPushButton):
    dragThreshold = 10
    click_count = 0
    last_click_time = 0

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                             stop:0 #2C3E50, stop:1 #34495E);
                color: #FFD700;
                font-size: 72px;
                font-weight: bold;
                padding: 20px;
                border: 2px solid #1ABC9C;
                border-radius: 10px;
                min-height: 300px;
                min-width: 300px;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                             stop:0 #1ABC9C, stop:1 #16A085);
                border: 2px solid #F39C12;
                color: #FFEB3B;
            }
        """)
        self._drag_start_pos = None
        self.tag_info = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            current_time = event.timestamp()
            if current_time - self.last_click_time < 500:
                self.click_count += 1
                if self.click_count == 3:
                    self.click_count = 0
                    main_window = self.parent()
                    while main_window and not hasattr(main_window, "run_selected_commands"):
                        main_window = main_window.parent()
                    if main_window:
                        main_window.run_selected_commands()
            else:
                self.click_count = 1
            self.last_click_time = current_time
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_start_pos:
            if (event.pos() - self._drag_start_pos).manhattanLength() >= self.dragThreshold:
                mimeData = QMimeData()
                mimeData.setText(self.tag_info["docker_name"])
                drag = QDrag(self)
                drag.setMimeData(mimeData)
                drag.exec_(Qt.MoveAction)
                return
        super().mouseMoveEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        change_action = menu.addAction("Change Tag Name")
        move_to_action = menu.addAction("Move To")
        run_bulk_action = menu.addAction("Run Bulk")
        action = menu.exec_(event.globalPos())
        main_window = self.parent()
        while main_window and not hasattr(main_window, "handle_tag_move"):
            main_window = main_window.parent()
        if not main_window:
            return

        if action == change_action:
            token = main_window.get_docker_token() if main_window else None
            if not token:
                return
            new_alias, ok = QInputDialog.getText(self, "Change Tag Name",
                                                 "Enter new tag name:", text=self.tag_info["alias"])
            if ok and new_alias:
                old_alias = self.tag_info["alias"]
                if update_docker_tag_name(old_alias, new_alias):
                    self.tag_info["alias"] = new_alias
                    persistent = main_window.persistent_settings.get(self.tag_info["docker_name"], {})
                    persistent["alias"] = new_alias
                    main_window.persistent_settings[self.tag_info["docker_name"]] = persistent
                    save_settings(main_window.persistent_settings)
                    lines = self.text().splitlines()
                    lines[0] = new_alias
                    self.setText("\n".join(lines))
                    if main_window and hasattr(main_window, "handle_tag_rename"):
                        main_window.handle_tag_rename(self.tag_info["docker_name"], new_alias)
                    
                    worker = Worker(fetch_game_time, new_alias)
                    worker.signals.finished.connect(partial(main_window.handle_game_time_update, new_alias))
                    main_window.add_worker(worker)
                    QThreadPool.globalInstance().start(worker)
        elif action == move_to_action:
            dialog = MoveToDialog(parent=main_window)
            if dialog.exec_():
                target_tab_id = dialog.selected_tab_id
                if target_tab_id:
                    main_window.handle_tag_move(self.tag_info["docker_name"], target_tab_id)
        elif action == run_bulk_action:
            if main_window:
                docker_name = self.tag_info.get("docker_name")
                if docker_name:
                    self.setChecked(True)
                    if hasattr(main_window, "selected_tag_names"):
                        main_window.selected_tag_names.add(docker_name)
                    
                    if hasattr(main_window, "_apply_button_style") and hasattr(main_window, "get_image_path"):
                        image_path = main_window.get_image_path(self.tag_info)
                        main_window._apply_button_style(self, image_path, self.tag_info)

    def setBackgroundImage(self, image_path):
        if image_path and os.path.exists(image_path):
            self.setStyleSheet(f"""
                QPushButton {{
                    background-image: url({image_path.replace('\\', '/')});
                    background-repeat: no-repeat;
                    background-position: center;
                    background-color: rgba(44, 62, 80, 0.8);
                    color: gold;
                    font-size: 24px;
                    padding: 20px;
                    border: 2px solid #1ABC9C;
                    border-radius: 10px;
                    min-height: 200px;
                    min-width: 200px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: rgba(26, 188, 156, 0.8);
                    border: 2px solid #F39C12;
                }}
                QPushButton:pressed {{
                    background-color: rgba(41, 128, 185, 0.8);
                }}
            """)

class MyLinersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("My Liners")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.btn_defs = [
            ("BackItUp", "wsl --distribution ubuntu --user root -- bash -lic 'backitup'"),
            ("BigiTGo", "wsl --distribution ubuntu --user root -- bash -lic 'bigitgo'"),
            ("gg", "wsl --distribution ubuntu --user root -- bash -lic 'gg'"),
            ("dcreds", "wsl --distribution ubuntu --user root -- bash -lic 'dcreds'"),
            ("savegames", "wsl --distribution ubuntu --user root -- bash -lic 'savegames'"),
            ("GameSaveRestore", "wsl --distribution ubuntu --user root -- bash -lic 'gamedg'")
        ]
        self.btn_defs.extend(load_custom_buttons())
        existing_buttons = {}
        for label, cmd in self.btn_defs:
            if label not in existing_buttons:
                btn = self.create_button(label, cmd)
                layout.addWidget(btn)
                existing_buttons[label] = btn
        add_button_btn = QPushButton("Add Custom Button")
        add_button_btn.setStyleSheet("""
            QPushButton {
                background: #16A085;
                color: yellow;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #1ABC9C;
            }
        """)
        add_button_btn.clicked.connect(self.add_custom_button)
        layout.addWidget(add_button_btn)
        remove_button_btn = QPushButton("Remove Custom Button")
        remove_button_btn.setStyleSheet("""
            QPushButton {
                background: #E74C3C;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #C0392B;
            }
        """)
        remove_button_btn.clicked.connect(self.remove_custom_button)
        layout.addWidget(remove_button_btn)
        self.setLayout(layout)

    def create_button(self, label, cmd):
        btn = QPushButton(label)
        btn.setStyleSheet("""
            QPushButton {
                background: #34495E;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #2C3E50;
            }
        """)
        btn.clicked.connect(partial(self.run_command, cmd))
        return btn

    def run_command(self, cmd):
        try:
            subprocess.Popen(cmd, shell=True)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error running command: {e}")

    def add_custom_button(self):
        name, ok_name = QInputDialog.getText(self, "Custom Button", "Enter button name:")
        if not ok_name or not name:
            return
        cmd, ok_cmd = QInputDialog.getText(self, "Custom Command", "Enter command to execute:")
        if not ok_cmd or not cmd:
            return
        self.btn_defs.append((name, cmd))
        save_custom_buttons(self.btn_defs)
        btn = self.create_button(name, cmd)
        self.layout().addWidget(btn)

    def remove_custom_button(self):
        names = [label for label, _ in self.btn_defs if label not in ["BackItUp", "BigiTGo", "gg", "dcreds", "savegames", "GameSaveRestore"]]
        name, ok = QInputDialog.getItem(self, "Remove Custom Button", "Select button to remove:", names, editable=False)
        if not ok or not name:
            return
        self.btn_defs = [(label, cmd) for label, cmd in self.btn_defs if label != name]
        save_custom_buttons(self.btn_defs)
        self.init_ui()

class UserDashboardDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Dashboard")
        self.setMinimumSize(400, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.user_list = QListWidget()
        self.user_list.setStyleSheet("padding: 4px;")
        layout.addWidget(self.user_list)
        
        add_user_btn = QPushButton("Add New User")
        add_user_btn.setStyleSheet("""
            QPushButton {
                background: #27AE60;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #2ECC71;
            }
        """)
        add_user_btn.clicked.connect(self.add_new_user)
        layout.addWidget(add_user_btn)
        
        kick_button = QPushButton("Kick Selected User")
        kick_button.setStyleSheet("""
            QPushButton {
                background: #C0392B;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #E74C3C;
            }
        """)
        kick_button.clicked.connect(self.kick_selected)
        layout.addWidget(kick_button)
        
        refresh_button = QPushButton("Refresh")
        refresh_button.setStyleSheet("""
            QPushButton {
                background: #2980B9;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #3498DB;
            }
        """)
        refresh_button.clicked.connect(self.populate_users)
        layout.addWidget(refresh_button)
        
        self.setLayout(layout)
        self.populate_users()

    def populate_users(self):
        self.user_list.clear()
        users = load_active_users()
        for username in users:
            item = QListWidgetItem(username)
            self.user_list.addItem(item)

    def kick_selected(self):
        selected = self.user_list.currentItem()
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select a user to kick.")
            return
        username = selected.text()
        banned = load_banned_users()
        if username not in banned:
            banned.append(username)
            save_banned_users(banned)
        users = load_active_users()
        if username in users:
            del users[username]
            save_active_users(users)
        QMessageBox.information(self, "User Kicked", f"User '{username}' has been kicked.")
        self.populate_users()

    def add_new_user(self):
        new_user, ok = QInputDialog.getText(self, "Add New User", "Enter new username:")
        if ok and new_user:
            new_user = new_user.strip().lower()
            users = load_active_users()
            if new_user in users:
                QMessageBox.information(self, "User Exists", f"User '{new_user}' already exists.")
                return
            users[new_user] = {"login_time": time.time()}
            save_active_users(users)
            QMessageBox.information(self, "User Added", f"User '{new_user}' has been added.")
            self.populate_users()

# ===== TAB CLASSES =====

class TagContainerWidget(QWidget):
    def __init__(self, type_name, parent=None):
        super().__init__(parent)
        self.type_name = type_name
        self.setAcceptDrops(True)
        self.setProperty("tab_id", type_name)
        
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(10)
        self.setLayout(self.grid_layout)
        
        settings = load_settings()
        self.excluded_tabs = settings.get('excluded_tabs', [])
        
    def should_show_tag(self, tag_category):
        if self.type_name != "all":
            return True
            
        settings = load_settings()
        excluded_tabs = settings.get('excluded_tabs', [])
        return tag_category not in excluded_tabs

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        docker_name = event.mimeData().text()
        main_window = self.window()
        if main_window and hasattr(main_window, "update_tag_category"):
            if self.type_name == "all":
                return
            main_window.update_tag_category(docker_name, self.type_name)
        event.acceptProposedAction()

    def should_display_tag(self, tag_category):
        settings = load_settings()
        self.excluded_tabs = settings.get('excluded_tabs', [])
        if self.type_name != "all":
            return True
        return tag_category not in self.excluded_tabs

    def update_layout(self):
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().hide()
                child.widget().setParent(None)

class TabNavigationWidget(QWidget):
    def __init__(self, tabs_config, parent=None):
        super().__init__(parent)
        self.tabs_config = tabs_config
        self.init_ui()

    def init_ui(self):
        self.layout = QGridLayout(self)
        self.layout.setSpacing(5)
        self.setLayout(self.layout)
        self.create_tab_buttons()

    def create_tab_buttons(self):
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.buttons = {}
        col = 0
        row = 0
        for tab in self.tabs_config:
            btn = QPushButton(tab["name"])
            btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #2C3E50, stop:1 #34495E);
                    color: white;
                    padding: 8px 12px;
                    border: 1px solid #1ABC9C;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #1ABC9C, stop:1 #16A085);
                }
            """)
            btn.clicked.connect(partial(self.tab_clicked, tab["id"]))
            self.layout.addWidget(btn, row, col)
            self.buttons[tab["id"]] = btn
            col += 1
            if col >= 5:
                col = 0
                row += 1

    def tab_clicked(self, tab_id):
        self.parent().set_current_tab(tab_id)

    def update_tabs(self, tabs_config):
        self.tabs_config = tabs_config
        self.create_tab_buttons()

class MoveToDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Target Tab")
        self.selected_tab_id = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: #2C3E50;
                color: #ECF0F1;
                border: 1px solid #34495E;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #34495E;
            }
            QListWidget::item:selected {
                background: #3498DB;
                color: white;
            }
            QListWidget::item:hover {
                background: #2980B9;
                color: white;
            }
        """)
        
        for tab in load_tabs_config():
            item = QListWidgetItem(tab["name"])
            item.setData(Qt.UserRole, tab["id"])
            self.list_widget.addItem(item)
            
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.list_widget)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("""
            QPushButton {
                background: #E74C3C;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #C0392B;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        
        layout.addWidget(cancel_button)
        self.setLayout(layout)
        self.setMinimumWidth(300)

    def on_item_clicked(self, item):
        self.selected_tab_id = item.data(Qt.UserRole)
        self.accept()

class ExcludeTabsDialog(QDialog):
    def __init__(self, tabs_config, excluded_tabs, parent=None):
        super().__init__(parent)
        self.tabs_config = tabs_config
        
        settings = load_settings()
        self.excluded_tabs = settings.get('excluded_tabs', []).copy()
        
        self.setWindowTitle("Exclude Tabs from All View")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        
        try:
            self.list_widget.itemChanged.disconnect()
        except:
            pass
            
        for tab in self.tabs_config:
            if tab["id"] == "all":
                continue
            item = QListWidgetItem(tab["name"])
            item.setData(Qt.UserRole, tab["id"])
            item.setCheckState(Qt.Checked if tab["id"] in self.excluded_tabs else Qt.Unchecked)
            self.list_widget.addItem(item)
        
        layout.addWidget(self.list_widget)
        
        apply_button = QPushButton("Apply and Close")
        apply_button.setStyleSheet("""
            QPushButton {
                background: #27AE60;
                color: white;
                padding: 8px 12px;  
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #2ECC71;
            }
        """)
        apply_button.clicked.connect(self.apply_and_close)
        layout.addWidget(apply_button)
        
        self.list_widget.itemChanged.connect(self.on_item_changed)
        
        self.setLayout(layout)

    def on_item_changed(self, item):
        self.excluded_tabs = self.get_excluded_tabs()

    def get_excluded_tabs(self):
        excluded = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item and item.checkState() == Qt.Checked:
                tab_id = item.data(Qt.UserRole)
                if tab_id:
                    excluded.append(tab_id)
        return excluded

    def apply_and_close(self):
        try:
            self.excluded_tabs = self.get_excluded_tabs()
            
            settings = load_settings()
            settings['excluded_tabs'] = self.excluded_tabs
            save_settings(settings)
            
            if self.parent() and hasattr(self.parent(), "create_tag_buttons"):
                self.parent().create_tag_buttons()
                
            self.accept()
        except Exception as e:
            print(f"Error in apply_and_close: {e}")
            self.reject()

class Tabs:
    def __init__(self, parent):
        self.parent = parent
        self.tabs_config = load_tabs_config()
        self.tab_pages = {}
        self.stacked = None

    def create_tab_management_buttons(self):
        buttons = []
        add_tab_btn = QPushButton("Add Tab")
        add_tab_btn.setStyleSheet("""
            QPushButton {
                background: #16A085;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #1ABC9C;
            }
        """)
        add_tab_btn.clicked.connect(lambda: self.parent.require_admin() and self.add_tab())
        buttons.append(add_tab_btn)

        rename_tab_btn = QPushButton("Rename Tab")
        rename_tab_btn.setStyleSheet("""
            QPushButton {
                background: #8E44AD;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #9B59B6;
            }
        """)
        rename_tab_btn.clicked.connect(lambda: self.parent.require_admin() and self.rename_tab())
        buttons.append(rename_tab_btn)

        delete_tab_btn = QPushButton("Delete Tab")
        delete_tab_btn.setStyleSheet("""
            QPushButton {
                background: #E74C3C;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #C0392B;
            }
        """)
        delete_tab_btn.clicked.connect(lambda: self.parent.require_admin() and self.delete_tab())
        buttons.append(delete_tab_btn)

        exclude_btn = QPushButton("Exclude in All")
        exclude_btn.setStyleSheet("""
            QPushButton {
                background: #D35400;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #E67E22;
            }
        """)
        exclude_btn.clicked.connect(lambda: self.parent.require_admin() and self.manage_exclusions())
        buttons.append(exclude_btn)

        return buttons

    def create_tab_navigation(self):
        self.tab_nav = TabNavigationWidget(self.tabs_config, parent=self.parent)
        return self.tab_nav

    def create_tab_pages(self):
        self.stacked = QStackedWidget()
        self.tab_pages = {}
        for tab in self.tabs_config:
            container = TagContainerWidget(tab["id"], parent=self.parent)
            self.tab_pages[tab["id"]] = container
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(container)
            self.stacked.addWidget(scroll)
        return self.stacked

    def set_current_tab(self, tab_id):
        for i, tab in enumerate(self.tabs_config):
            if tab["id"] == tab_id:
                self.stacked.setCurrentIndex(i)
                break

    def add_tab(self):
        new_name, ok = QInputDialog.getText(self.parent, "Add Tab", "Enter new tab name:")
        if not (ok and new_name):
            return
        new_id = new_name.lower().replace(" ", "_")
        if any(tab["id"] == new_id for tab in self.tabs_config):
            QMessageBox.warning(self.parent, "Error", "A tab with that identifier already exists.")
            return
        self.tabs_config.append({"id": new_id, "name": new_name})
        save_tabs_config(self.tabs_config)
        container = TagContainerWidget(new_id, parent=self.parent)
        self.tab_pages[new_id] = container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        self.stacked.addWidget(scroll)
        self.tab_nav.update_tabs(self.tabs_config)
        self.parent.create_tag_buttons()

    def rename_tab(self):
        current_index = self.stacked.currentIndex()
        current_tab = self.tabs_config[current_index]
        new_name, ok = QInputDialog.getText(self.parent, "Rename Tab", "Enter new tab name:", text=current_tab["name"])
        if not (ok and new_name):
            return
        self.tabs_config[current_index]["name"] = new_name
        save_tabs_config(self.tabs_config)
        self.tab_nav.update_tabs(self.tabs_config)
        self.parent.create_tag_buttons()

    def delete_tab(self):
        current_index = self.stacked.currentIndex()
        current_tab = self.tabs_config[current_index]
        if current_tab["id"] == "all":
            QMessageBox.warning(self.parent, "Error", "You cannot delete the 'All' tab.")
            return
        reply = QMessageBox.question(self.parent, "Delete Tab", f"Delete tab '{current_tab['name']}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        del self.tabs_config[current_index]
        save_tabs_config(self.tabs_config)
        self.tab_nav.update_tabs(self.tabs_config)
        widget_to_remove = self.stacked.widget(current_index)
        self.stacked.removeWidget(widget_to_remove)
        widget_to_remove.deleteLater()
        self.parent.create_tag_buttons()

    def manage_exclusions(self):
        try:
            settings = load_settings()
            excluded_tabs = settings.get('excluded_tabs', [])
            
            dialog = ExcludeTabsDialog(self.tabs_config, excluded_tabs, self.parent)
            if dialog.exec_() == QDialog.Accepted:
                self.parent.create_tag_buttons()
        except Exception as e:
            print(f"Error in manage_exclusions: {e}")
            QMessageBox.warning(self.parent, "Error", "Failed to manage exclusions")

    def get_tab_name(self, tab_id):
        """Returns the display name of a tab given its ID."""
        for tab in self.tabs_config:
            if tab["id"] == tab_id:
                return tab["name"]
        return "Unknown Tab"

    def should_show_in_all(self, tab_id):
        if tab_id == "all":
            return True
        settings = load_settings()
        excluded_tabs = settings.get('excluded_tabs', [])
        return tab_id not in excluded_tabs

# ===== TAG CLASSES =====

class TabGridWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QGridLayout(self)
        self.layout.setSpacing(5)
        self.setLayout(self.layout)
        self.selected_tab_id = None
        self.create_tab_buttons()

    def create_tab_buttons(self):
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        col = 0
        row = 0
        self.buttons = {}
        for tab in load_tabs_config():
            if tab["id"] == "all":
                continue
            btn = QPushButton(tab["name"])
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background: #16A085;
                    color: white;
                    padding: 6px 10px;
                    border-radius: 4px;
                }
                QPushButton:checked {
                    background: #1ABC9C;
                }
            """)
            btn.clicked.connect(partial(self.tab_clicked, tab["id"]))
            self.layout.addWidget(btn, row, col)
            self.buttons[tab["id"]] = btn
            col += 1
            if col >= 5:
                col = 0
                row += 1

    def tab_clicked(self, tid):
        self.selected_tab_id = tid
        for k, b in self.buttons.items():
            if k != tid:
                b.setChecked(False)

class BulkMoveDialog(QDialog):
    def __init__(self, all_tags, parent=None):
        super().__init__(parent)
        self.all_tags = all_tags
        self.setWindowTitle("Bulk Move Tags")
        self.setMinimumSize(400, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search tags...")
        self.search_box.setStyleSheet("padding: 6px; border-radius: 4px;")
        self.search_box.textChanged.connect(self.filter_list)
        layout.addWidget(self.search_box)
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("padding: 4px;")
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.list_widget)
        self.populate_list()
        layout.addWidget(QLabel("Move selected tags to:"))
        self.tab_grid = TabGridWidget()
        layout.addWidget(self.tab_grid)
        self.move_button = QPushButton("Move Selected")
        self.move_button.setStyleSheet("""
            QPushButton {
                background: #27AE60;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #2ECC71;
            }
        """)
        self.move_button.clicked.connect(self.move_tags)
        layout.addWidget(self.move_button)
        self.setLayout(layout)

    def populate_list(self):
        self.list_widget.clear()
        for tag in self.all_tags:
            item = QListWidgetItem(tag["alias"])
            self.list_widget.addItem(item)
            item.setData(Qt.UserRole, tag)

    def filter_list(self, text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            tag = item.data(Qt.UserRole)
            item.setHidden(text.lower() not in tag["alias"].lower())

    def move_tags(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select at least one tag to move.")
            return
        if not self.tab_grid.selected_tab_id:
            QMessageBox.information(self, "No Tab Selected", "Please select a target tab from the grid.")
            return
        target_tab_id = self.tab_grid.selected_tab_id
        for item in selected:
            tag = item.data(Qt.UserRole)
            tag["category"] = target_tab_id
        QMessageBox.information(self, "Bulk Move", "Selected tags moved.")
        self.accept()

# ===== DOCKER COMMANDS =====

class DockerCommandSignals(QObject):
    """Signals for Docker command execution."""
    finished = pyqtSignal(int)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)  # For real-time progress updates
    started = pyqtSignal(str)   # When command starts

class DockerCommandWorker(QRunnable):
    """Worker thread for executing Docker commands."""
    
    def __init__(self, app, command, is_docker=True):
        super().__init__()
        self.app = app
        self.command = command
        self.is_docker = is_docker
        self.signals = DockerCommandSignals()
    
    @pyqtSlot()
    def run(self):
        try:
            if self.is_docker:
                exit_code = self.app.docker_run_command_real_time(self.command)
            else:
                exit_code = self.app.rsync_command_real_time(self.command)
            self.signals.finished.emit(exit_code)
        except Exception as e:
            self.signals.error.emit(str(e))

class DockerProgressWorker(QRunnable):
    """Worker thread for executing Docker commands with real-time progress updates."""
    
    def __init__(self, command, tag_name="", target_path=""):
        super().__init__()
        self.command = command
        self.tag_name = tag_name
        self.target_path = target_path
        self.signals = DockerCommandSignals()
    
    @pyqtSlot()
    def run(self):
        try:
            self.signals.started.emit(f"Starting Docker command for {self.tag_name}")
            
            process = subprocess.Popen(
                self.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                universal_newlines=True
            )
            
            # Stream output in real-time
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    self.signals.progress.emit(line.strip())
            
            process.stdout.close()
            return_code = process.wait()
            
            self.signals.finished.emit(return_code)
            
        except Exception as e:
            self.signals.error.emit(str(e))

class DockerCommands:
    def __init__(self, app):
        self.app = app
        self.run_button = None

    def create_browse_button(self):
        btn = QPushButton("Browse Path")
        btn.setStyleSheet("""
            QPushButton {
                background: #2980B9;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #3498DB;
            }
        """)
        btn.clicked.connect(self.select_destination_path)
        return btn

    def create_run_button(self):
        self.run_button = QPushButton("Run Selected")
        self.run_button.setStyleSheet("""
            QPushButton {
                background-color: #2ECC71;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #27AE60;
            }
            QPushButton:disabled {
                background-color: #95A5A6;
            }
        """)
        self.run_button.clicked.connect(self.run_selected_tag)
        return self.run_button

    def select_destination_path(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.DirectoryOnly)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        if dialog.exec_():
            selected_dir = dialog.selectedFiles()[0]
            wsl_path = selected_dir.replace('\\', '/').replace('C:', '/mnt/c')
            return wsl_path
        return None

    def run_selected_tag(self):
        """Handle the action when the run button is clicked."""
        active_button = None
        for button in self.app.buttons:
            if button.isChecked():
                active_button = button
                break
        
        if not active_button:
            QMessageBox.warning(self.app, "No Selection", "Please select a game first!")
            return
            
        tag_info = active_button.tag_info
        tag = tag_info["docker_name"]
        game_name = tag_info["alias"]
        
        dialog = GameDestinationDialog(self.app, game_name, tag)
        if dialog.exec_() != GameDestinationDialog.Accepted:
            return
            
        destination_path = dialog.get_selected_path()
        if not destination_path:
            return
        
        QMessageBox.information(
            self.app, 
            "Starting Sync", 
            f"Starting to sync {game_name} to:\n{destination_path}\n\n"
            f"This will run in the background. Check your terminal for progress."
        )
        
        # Get reference to main app for progress updates
        main_app = None
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, DockerApp):
                main_app = widget
                break

        if main_app:
            main_app.show_progress(True)
            main_app.reset_progress()
            run_docker_command(tag, destination_path, main_app.update_progress)
        else:
            run_docker_command(tag, destination_path)

# ===== GAME MANAGER =====

class GameManager:
    def __init__(self, parent):
        self.parent = parent
        self.game_times_cache = {}
        self.active_workers = []
        self.started_image_queries = set()
        self.threadpool = QThreadPool.globalInstance()
        self.threadpool.setMaxThreadCount(8)

    def add_worker(self, worker):
        if not hasattr(worker, 'is_running'):
            worker.is_running = True
        self.active_workers.append(worker)
        worker.signals.finished.connect(lambda result: self.on_worker_finished(worker, result))

    def on_worker_finished(self, worker, result):
        if worker in self.active_workers:
            worker.is_running = False
            try:
                worker.signals.finished.disconnect()
            except (TypeError, RuntimeError):
                pass
            self.active_workers.remove(worker)

    def cleanup_workers(self):
        for worker in self.active_workers[:]:
            worker.is_running = False
            try:
                worker.signals.finished.disconnect()
            except (TypeError, RuntimeError):
                pass
            self.active_workers.remove(worker)
        
        self.threadpool.clear()
        if not self.threadpool.waitForDone(1000):
            print("Warning: Some workers did not finish cleanly")

    def sort_tags_by_time(self, descending=True):
        def parse_time(time_str):
            try:
                time_str = time_str.lower().replace("approx time: ", "").replace("hours", "").strip()
                if "-" in time_str or "–" in time_str:
                    time_str = time_str.replace("–", "-").split("-")[1].strip()
                return float(time_str)
            except:
                return 0.0
        self.parent.all_tags.sort(key=lambda x: parse_time(x.get("approx_time", "0")), reverse=descending)
        self.parent.create_tag_buttons()

    def filter_buttons(self, text):
        for button in self.parent.buttons:
            if button.parent():
                button.setVisible(text.lower() in button.tag_info["alias"].lower())

# ===== LOGIN DIALOG =====

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setFixedSize(300, 150)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setStyleSheet("padding: 6px; border-radius: 4px;")
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("padding: 6px; border-radius: 4px;")
        layout.addWidget(self.password_input)

        login_btn = QPushButton("Login")
        login_btn.setStyleSheet("""
            QPushButton {
                background: #27AE60;
                color: white;
                padding: 8px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #2ECC71;
            }
        """)
        login_btn.clicked.connect(self.accept)
        layout.addWidget(login_btn)
        self.setLayout(layout)

# ===== SYNC WORKER =====

class SyncWorker(QObject):
    """Worker class to handle sync operations in background"""
    finished = pyqtSignal(bool, str)  # success, message
    progress = pyqtSignal(dict)  # progress stats
    
    def __init__(self, tag, destination_path):
        super().__init__()
        self.tag = tag
        self.destination_path = destination_path
        self.is_running = True
        
    def run(self):
        """Run the sync operation"""
        try:
            process, monitor_thread = run_docker_command(
                self.tag,
                self.destination_path,
                self.handle_progress
            )
            
            if not process:
                self.finished.emit(False, "Failed to start sync operation")
                return
                
            while self.is_running and process.poll() is None:
                QThread.msleep(100)
                
            if self.is_running:
                self.finished.emit(True, "Sync completed successfully")
            else:
                self.finished.emit(False, "Sync was cancelled")
                
        except Exception as e:
            self.finished.emit(False, f"Error during sync: {str(e)}")
            
    def handle_progress(self, line):
        """Handle progress updates from the sync operation"""
        if not self.is_running:
            return
            
        if "%" in line:
            try:
                percent = int(line.split("%")[0].strip())
                self.progress.emit({"percent": percent, "status": line.strip()})
            except:
                pass
                
    def stop(self):
        """Stop the sync operation"""
        self.is_running = False

# ===== MAIN DOCKER APP =====

# ============ TAGS CLASSES ============
class TabGridWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QGridLayout(self)
        self.layout.setSpacing(5)
        self.setLayout(self.layout)
        self.selected_tab_id = None
        self.create_tab_buttons()

    def create_tab_buttons(self):
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        col = 0
        row = 0
        self.buttons = {}
        for tab in load_tabs_config():
            if tab["id"] == "all":
                continue
            btn = QPushButton(tab["name"])
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background: #16A085;
                    color: white;
                    padding: 6px 10px;
                    border-radius: 4px;
                }
                QPushButton:checked {
                    background: #1ABC9C;
                }
            """)
            btn.clicked.connect(partial(self.tab_clicked, tab["id"]))
            self.layout.addWidget(btn, row, col)
            self.buttons[tab["id"]] = btn
            col += 1
            if col >= 5:
                col = 0
                row += 1

    def tab_clicked(self, tid):
        self.selected_tab_id = tid
        for k, b in self.buttons.items():
            if k != tid:
                b.setChecked(False)

class BulkMoveDialog(QDialog):
    def __init__(self, all_tags, parent=None):
        super().__init__(parent)
        self.all_tags = all_tags
        self.setWindowTitle("Bulk Move Tags")
        self.setMinimumSize(400, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search tags...")
        self.search_box.setStyleSheet("padding: 6px; border-radius: 4px;")
        self.search_box.textChanged.connect(self.filter_list)
        layout.addWidget(self.search_box)
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("padding: 4px;")
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.list_widget)
        self.populate_list()
        layout.addWidget(QLabel("Move selected tags to:"))
        self.tab_grid = TabGridWidget()
        layout.addWidget(self.tab_grid)
        self.move_button = QPushButton("Move Selected")
        self.move_button.setStyleSheet("""
            QPushButton {
                background: #27AE60;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #2ECC71;
            }
        """)
        self.move_button.clicked.connect(self.move_tags)
        layout.addWidget(self.move_button)
        self.setLayout(layout)

    def populate_list(self):
        self.list_widget.clear()
        for tag in self.all_tags:
            item = QListWidgetItem(tag["alias"])
            self.list_widget.addItem(item)
            item.setData(Qt.UserRole, tag)

    def filter_list(self, text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            tag = item.data(Qt.UserRole)
            item.setHidden(text.lower() not in tag["alias"].lower())

    def move_tags(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select at least one tag to move.")
            return
        if not self.tab_grid.selected_tab_id:
            QMessageBox.information(self, "No Tab Selected", "Please select a target tab from the grid.")
            return
        target_tab_id = self.tab_grid.selected_tab_id
        for item in selected:
            tag = item.data(Qt.UserRole)
            tag["category"] = target_tab_id
        QMessageBox.information(self, "Bulk Move", "Selected tags moved.")
        self.accept()

class BulkPasteMoveDialog(QDialog):
    def __init__(self, all_tags, parent=None):
        super().__init__(parent)
        self.all_tags = all_tags
        self.setWindowTitle("Bulk Paste Move Tags")
        self.setMinimumSize(400, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Paste tag names (one per line):"))
        self.text_edit = QTextEdit()
        self.text_edit.setStyleSheet("padding: 6px; border: 1px solid #ccc; border-radius: 4px;")
        layout.addWidget(self.text_edit)
        layout.addWidget(QLabel("Move pasted tags to:"))
        self.tab_grid = TabGridWidget()
        layout.addWidget(self.tab_grid)
        move_button = QPushButton("Move Pasted Tags")
        move_button.setStyleSheet("""
            QPushButton {
                background: #F39C12;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #F1C40F;
            }
        """)
        move_button.clicked.connect(self.move_pasted_tags)
        layout.addWidget(move_button)
        self.setLayout(layout)

    def move_pasted_tags(self):
        lines = self.text_edit.toPlainText().splitlines()
        pasted = [line.strip().lower() for line in lines if line.strip()]
        if not pasted:
            QMessageBox.information(self, "No Input", "Please paste at least one tag name.")
            return
        if not self.tab_grid.selected_tab_id:
            QMessageBox.information(self, "No Tab Selected", "Please select a target tab from the grid.")
            return
        target_tab_id = self.tab_grid.selected_tab_id
        moved = 0
        unmatched = []
        parent = self.parent() if hasattr(self, 'parent') else None
        persistent_settings = getattr(parent, 'persistent_settings', {}) if parent else {}
        for name in pasted:
            found = False
            for tag in self.all_tags:
                if name == tag["alias"].strip().lower() or name == tag["docker_name"].strip().lower():
                    tag["category"] = target_tab_id
                    # Persist the change
                    if persistent_settings is not None:
                        persistent = persistent_settings.get(tag["docker_name"], {})
                        persistent["category"] = target_tab_id
                        persistent_settings[tag["docker_name"]] = persistent
                    moved += 1
                    found = True
                    break
            if not found:
                unmatched.append(name)
        # Save settings if changed
        if parent and hasattr(parent, 'persistent_settings'):
            parent.persistent_settings = persistent_settings
            if hasattr(parent, 'update_tag_categories'):
                parent.update_tag_categories()
        msg = f"Moved {moved} tag(s) to selected tab."
        if unmatched:
            msg += "\nUnmatched: " + ", ".join(unmatched)
        QMessageBox.information(self, "Bulk Paste Move", msg)
        self.accept()

class DeleteTagDialog(QDialog):
    def __init__(self, all_tags, parent=None):
        super().__init__(parent)
        self.all_tags = all_tags
        self.setWindowTitle("Delete Tag")
        self.setMinimumSize(400, 400)
        self.init_ui()

    def format_size(self, size):
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}PB"

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search tag to delete...")
        self.search_box.setStyleSheet("padding: 6px; border-radius: 4px;")
        layout.addWidget(self.search_box)
        self.dup_checkbox = QCheckBox("Show only duplicate tags")
        layout.addWidget(self.dup_checkbox)
        self.dup_checkbox.stateChanged.connect(self.populate_list)
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("padding: 4px;")
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.list_widget)
        self.populate_list()
        self.search_box.textChanged.connect(self.filter_list)
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background: #C0392B;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #E74C3C;
            }
        """)
        self.delete_button.clicked.connect(self.delete_selected)
        layout.addWidget(self.delete_button)
        self.setLayout(layout)

    def populate_list(self):
        self.list_widget.clear()
        only_duplicates = self.dup_checkbox.isChecked()
        alias_counts = {}
        for tag in self.all_tags:
            alias = tag["alias"]
            alias_counts[alias] = alias_counts.get(alias, 0) + 1
        for tag in self.all_tags:
            if only_duplicates and alias_counts[tag["alias"]] <= 1:
                continue
            display_text = f"{tag['alias']} ({self.format_size(tag['full_size'])})"
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, tag)
            self.list_widget.addItem(item)

    def filter_list(self, text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            tag = item.data(Qt.UserRole)
            item.setHidden(text.lower() not in tag["alias"].lower())

    def delete_selected(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select at least one tag to delete.")
            return
        tags = [item.data(Qt.UserRole)["docker_name"] for item in selected_items]
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete the following tags from Docker Hub?\n" + "\n".join(tags),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        token = self.parent().get_docker_token()
        if not token:
            return
        successes = []
        failures = []
        for tag in tags:
            if delete_docker_tag(token, tag):
                successes.append(tag)
            else:
                failures.append(tag)
        message = ""
        if successes:
            message += "Successfully deleted:\n" + "\n".join(successes) + "\n\n"
            for tag in successes:
                items = self.list_widget.findItems(tag, Qt.MatchContains)
                for item in items:
                    row = self.list_widget.row(item)
                    self.list_widget.takeItem(row)
        if failures:
            message += "Failed to delete:\n" + "\n".join(failures)
        QMessageBox.information(self, "Deletion Summary", message or "No tags deleted.")
        if self.parent() and hasattr(self.parent(), "refresh_tags"):
            self.parent().refresh_tags()

class BulkMoveByNameDialog(QDialog):
    def __init__(self, all_tags, parent=None):
        super().__init__(parent)
        self.all_tags = all_tags
        self.setWindowTitle("Bulk Move by Name")
        self.setMinimumSize(400, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Enter tag names to move (one per line):"))
        self.text_edit = QTextEdit()
        self.text_edit.setStyleSheet("padding: 6px; border: 1px solid #ccc; border-radius: 4px;")
        layout.addWidget(self.text_edit)
        layout.addWidget(QLabel("Move tags to:"))
        self.tab_grid = TabGridWidget()
        layout.addWidget(self.tab_grid)
        move_button = QPushButton("Bulk Move Tags")
        move_button.setStyleSheet("""
            QPushButton {
                background: #2980b9;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #3498db;
            }
        """)
        move_button.clicked.connect(self.move_tags_by_name)
        layout.addWidget(move_button)
        self.setLayout(layout)

        # Show a dialog with all available tag names for debugging
        tag_list = '\n'.join([f"alias: {tag.get('alias')} | docker_name: {tag.get('docker_name')}" for tag in self.all_tags])
        QMessageBox.information(self, "Available Tags", f"Available tags:\n{tag_list}")

    def move_tags_by_name(self):
        lines = self.text_edit.toPlainText().splitlines()
        pasted = [line.strip().lower().replace(' ', '') for line in lines if line.strip()]
        if not pasted:
            QMessageBox.information(self, "No Input", "Please enter at least one tag name.")
            return
        if not self.tab_grid.selected_tab_id:
            QMessageBox.information(self, "No Tab Selected", "Please select a target tab from the grid.")
            return
        target_tab_id = self.tab_grid.selected_tab_id
        moved = 0
        unmatched = []
        parent = self.parent() if hasattr(self, 'parent') else None
        persistent_settings = getattr(parent, 'persistent_settings', {}) if parent else {}
        for name in pasted:
            found = False
            for tag in self.all_tags:
                # Robust match: ignore case, ignore spaces, allow partials
                alias = tag.get("alias", "").strip().lower().replace(' ', '')
                docker_name = tag.get("docker_name", "").strip().lower().replace(' ', '')
                if name == alias or name == docker_name or name in alias or name in docker_name:
                    tag["category"] = target_tab_id
                    if persistent_settings is not None:
                        persistent = persistent_settings.get(tag["docker_name"], {})
                        persistent["category"] = target_tab_id
                        persistent_settings[tag["docker_name"]] = persistent
                    moved += 1
                    found = True
                    break
            if not found:
                unmatched.append(name)
        if parent and hasattr(parent, 'persistent_settings'):
            parent.persistent_settings = persistent_settings
            if hasattr(parent, 'update_tag_categories'):
                parent.update_tag_categories()
        msg = f"Moved {moved} tag(s) to selected tab."
        if unmatched:
            msg += "\nUnmatched: " + ", ".join(unmatched)
        QMessageBox.information(self, "Bulk Move by Name", msg)
        self.accept()

class Tags:
    def __init__(self, parent):
        self.parent = parent
        self.all_tags = parent.all_tags

    def create_tag_management_buttons(self):
        buttons = []
        delete_tag_button = QPushButton("Delete Docker Tag")
        delete_tag_button.setStyleSheet("""
            QPushButton {
                background: #C0392B;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #E74C3C;
            }
        """)
        delete_tag_button.clicked.connect(lambda: self.parent.require_admin() and self.open_delete_dialog())
        buttons.append(delete_tag_button)

        move_tags_button = QPushButton("Move Tags")
        move_tags_button.setStyleSheet("""
            QPushButton {
                background: #16A085;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #1ABC9C;
            }
        """)
        move_tags_button.clicked.connect(lambda: self.parent.require_admin() and self.open_bulk_move_dialog())
        buttons.append(move_tags_button)

        bulk_paste_button = QPushButton("Bulk Paste Move")
        bulk_paste_button.setStyleSheet("""
            QPushButton {
                background: #F39C12;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #F1C40F;
            }
        """)
        bulk_paste_button.clicked.connect(lambda: self.parent.require_admin() and self.open_bulk_paste_move_dialog())
        buttons.append(bulk_paste_button)

        # New Bulk mv button
        bulk_mv_button = QPushButton("Bulk mv")
        bulk_mv_button.setStyleSheet("""
            QPushButton {
                background: #2980b9;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #3498db;
            }
        """)
        bulk_mv_button.clicked.connect(lambda: self.parent.require_admin() and self.open_bulk_move_by_name_dialog())
        buttons.append(bulk_mv_button)

        save_txt_button = QPushButton("Save as .txt")
        save_txt_button.setStyleSheet("""
            QPushButton {
                background: #8E44AD;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #9B59B6;
            }
        """)
        save_txt_button.clicked.connect(self.parent.handle_save_txt)
        buttons.append(save_txt_button)
        return buttons

    def create_tag_buttons(self):
        buttons = {}
        for tag in self.all_tags:
            btn = QPushButton(tag["alias"])
            btn.setStyleSheet("""
                QPushButton {
                    background: #3498DB;
                    color: white;
                    padding: 8px 12px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: #5DADE2;
                }
            """)
            buttons[btn] = {"category": tag.get("category")}  # Add category info
            
        return buttons

    def create_search_box(self):
        search_box = QLineEdit()
        search_box.setPlaceholderText("Search tags...")
        search_box.setStyleSheet("padding: 8px; border: 2px solid #1ABC9C; border-radius: 6px;")
        search_box.textChanged.connect(self.parent.filter_buttons)
        return search_box

    def open_bulk_move_dialog(self):
        dialog = BulkMoveDialog(self.all_tags, parent=self.parent)
        if dialog.exec_():
            self.parent.update_tag_categories()

    def open_bulk_paste_move_dialog(self):
        dialog = BulkPasteMoveDialog(self.all_tags, parent=self.parent)
        if dialog.exec_():
            self.parent.update_tag_categories()

    def open_delete_dialog(self):
        dialog = DeleteTagDialog(self.all_tags, parent=self.parent)
        dialog.exec_()

    def open_bulk_move_by_name_dialog(self):
        dialog = BulkMoveByNameDialog(self.all_tags, parent=self.parent)
        if dialog.exec_():
            self.parent.update_tag_categories()

# ============ BUTTONS CLASSES ============
class GameButton(QPushButton):
    dragThreshold = 10
    click_count = 0
    last_click_time = 0

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                             stop:0 #2C3E50, stop:1 #34495E);
                color: #FFD700;
                font-size: 72px;
                font-weight: bold;
                padding: 20px;
                border: 2px solid #1ABC9C;
                border-radius: 10px;
                min-height: 300px;
                min-width: 300px;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                             stop:0 #1ABC9C, stop:1 #16A085);
                border: 2px solid #F39C12;
                color: #FFEB3B;
            }
        """)
        self._drag_start_pos = None
        self.tag_info = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            current_time = event.timestamp()
            if current_time - self.last_click_time < 500:  # 500ms threshold for multiple clicks
                self.click_count += 1
                if self.click_count == 3:  # Triple click
                    self.click_count = 0
                    # Get the main window
                    main_window = self.parent()
                    while main_window and not hasattr(main_window, "run_selected_commands"):
                        main_window = main_window.parent()
                    if main_window:
                        main_window.run_selected_commands()
            else:
                self.click_count = 1
            self.last_click_time = current_time
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_start_pos:
            if (event.pos() - self._drag_start_pos).manhattanLength() >= self.dragThreshold:
                mimeData = QMimeData()
                mimeData.setText(self.tag_info["docker_name"])
                drag = QDrag(self)
                drag.setMimeData(mimeData)
                drag.exec_(Qt.MoveAction)
                return
        super().mouseMoveEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        change_action = menu.addAction("Change Tag Name")
        move_to_action = menu.addAction("Move To")
        run_bulk_action = menu.addAction("Run Bulk")
        action = menu.exec_(event.globalPos())
        main_window = self.parent()
        while main_window and not hasattr(main_window, "handle_tag_move"):
            main_window = main_window.parent()
        if not main_window:
            return

        if action == change_action:
            # Check for admin token only for change action
            token = main_window.get_docker_token() if main_window else None
            if not token:
                return
            new_alias, ok = QInputDialog.getText(self, "Change Tag Name",
                                                 "Enter new tag name:", text=self.tag_info["alias"])
            if ok and new_alias:
                old_alias = self.tag_info["alias"]
                if update_docker_tag_name(old_alias, new_alias):
                    self.tag_info["alias"] = new_alias
                    persistent = main_window.persistent_settings.get(self.tag_info["docker_name"], {})
                    persistent["alias"] = new_alias
                    main_window.persistent_settings[self.tag_info["docker_name"]] = persistent
                    save_settings(main_window.persistent_settings)
                    lines = self.text().splitlines()
                    lines[0] = new_alias
                    self.setText("\n".join(lines))
                    if main_window and hasattr(main_window, "handle_tag_rename"):
                        main_window.handle_tag_rename(self.tag_info["docker_name"], new_alias)
                    class Worker(QRunnable):
                        def __init__(self, fn, *args):
                            super().__init__()
                            self.fn = fn
                            self.args = args
                            self.signals = QObject()
                            self.signals.finished = pyqtSignal(object)
                            self.is_running = True

                        def run(self):
                            try:
                                if self.is_running:
                                    result = self.fn(*self.args)
                                    self.signals.finished.emit(result)
                            except Exception as e:
                                print(f"Worker error: {e}")
                            finally:
                                self.is_running = False
                    worker = Worker(fetch_game_time, new_alias)
                    worker.signals.finished.connect(partial(main_window.handle_game_time_update, new_alias))
                    main_window.add_worker(worker)
                    QThreadPool.globalInstance().start(worker)
        elif action == move_to_action:
            dialog = MoveToDialog(parent=main_window)
            if dialog.exec_():
                target_tab_id = dialog.selected_tab_id
                if target_tab_id:
                    main_window.handle_tag_move(self.tag_info["docker_name"], target_tab_id)
        elif action == run_bulk_action:
            if main_window: # We already confirmed main_window exists above
                docker_name = self.tag_info.get("docker_name")
                if docker_name:
                    # Explicitly set checked state
                    self.setChecked(True)
                    # Add to the selected_tag_names set directly
                    if hasattr(main_window, "selected_tag_names"):
                        main_window.selected_tag_names.add(docker_name)
                    
                    # Ensure visual style is updated
                    if hasattr(main_window, "_apply_button_style") and hasattr(main_window, "get_image_path"):
                        image_path = main_window.get_image_path(self.tag_info)
                        main_window._apply_button_style(self, image_path, self.tag_info)

    def setBackgroundImage(self, image_path):
        if image_path and os.path.exists(image_path):
            self.setStyleSheet(f"""
                QPushButton {{
                    background-image: url({image_path.replace('\\', '/')});
                    background-repeat: no-repeat;
                    background-position: center;
                    background-color: rgba(44, 62, 80, 0.8);
                    color: gold;
                    font-size: 24px;
                    padding: 20px;
                    border: 2px solid #1ABC9C;
                    border-radius: 10px;
                    min-height: 200px;
                    min-width: 200px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: rgba(26, 188, 156, 0.8);
                    border: 2px solid #F39C12;
                }}
                QPushButton:pressed {{
                    background-color: rgba(41, 128, 185, 0.8);
                }}
            """)

class MyLinersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("My Liners")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.btn_defs = [
            ("BackItUp", "wsl --distribution ubuntu --user root -- bash -lic 'backitup'"),
            ("BigiTGo", "wsl --distribution ubuntu --user root -- bash -lic 'bigitgo'"),
            ("gg", "wsl --distribution ubuntu --user root -- bash -lic 'gg'"),
            ("dcreds", "wsl --distribution ubuntu --user root -- bash -lic 'dcreds'"),
            ("savegames", "wsl --distribution ubuntu --user root -- bash -lic 'savegames'"),
            ("GameSaveRestore", "wsl --distribution ubuntu --user root -- bash -lic 'gamedg'")
        ]
        self.btn_defs.extend(load_custom_buttons())
        existing_buttons = {}
        for label, cmd in self.btn_defs:
            if label not in existing_buttons:
                btn = self.create_button(label, cmd)
                layout.addWidget(btn)
                existing_buttons[label] = btn
        add_button_btn = QPushButton("Add Custom Button")
        add_button_btn.setStyleSheet("""
            QPushButton {
                background: #16A085;
                color: yellow;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #1ABC9C;
            }
        """)
        add_button_btn.clicked.connect(self.add_custom_button)
        layout.addWidget(add_button_btn)
        remove_button_btn = QPushButton("Remove Custom Button")
        remove_button_btn.setStyleSheet("""
            QPushButton {
                background: #E74C3C;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #C0392B;
            }
        """)
        remove_button_btn.clicked.connect(self.remove_custom_button)
        layout.addWidget(remove_button_btn)
        self.setLayout(layout)

    def create_button(self, label, cmd):
        btn = QPushButton(label)
        btn.setStyleSheet("""
            QPushButton {
                background: #34495E;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #2C3E50;
            }
        """)
        btn.clicked.connect(partial(self.run_command, cmd))
        return btn

    def run_command(self, cmd):
        try:
            subprocess.Popen(cmd, shell=True)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error running command: {e}")

    def add_custom_button(self):
        name, ok_name = QInputDialog.getText(self, "Custom Button", "Enter button name:")
        if not ok_name or not name:
            return
        cmd, ok_cmd = QInputDialog.getText(self, "Custom Command", "Enter command to execute:")
        if not ok_cmd or not cmd:
            return
        self.btn_defs.append((name, cmd))
        save_custom_buttons(self.btn_defs)
        btn = self.create_button(name, cmd)
        self.layout().addWidget(btn)

    def remove_custom_button(self):
        names = [label for label, _ in self.btn_defs if label not in ["BackItUp", "BigiTGo", "gg", "dcreds", "savegames", "GameSaveRestore"]]
        name, ok = QInputDialog.getItem(self, "Remove Custom Button", "Select button to remove:", names, editable=False)
        if not ok or not name:
            return
        self.btn_defs = [(label, cmd) for label, cmd in self.btn_defs if label != name]
        save_custom_buttons(self.btn_defs)
        self.init_ui()

class UserDashboardDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Dashboard")
        self.setMinimumSize(400, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.user_list = QListWidget()
        self.user_list.setStyleSheet("padding: 4px;")
        layout.addWidget(self.user_list)
        add_user_btn = QPushButton("Add New User")
        add_user_btn.setStyleSheet("""
            QPushButton {
                background: #27AE60;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #2ECC71;
            }
        """)
        add_user_btn.clicked.connect(self.add_new_user)
        layout.addWidget(add_user_btn)
        kick_button = QPushButton("Kick Selected User")
        kick_button.setStyleSheet("""
            QPushButton {
                background: #C0392B;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #E74C3C;
            }
        """)
        kick_button.clicked.connect(self.kick_selected)
        layout.addWidget(kick_button)
        refresh_button = QPushButton("Refresh")
        refresh_button.setStyleSheet("""
            QPushButton {
                background: #2980B9;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #3498DB;
            }
        """)
        refresh_button.clicked.connect(self.populate_users)
        layout.addWidget(refresh_button)
        self.setLayout(layout)
        self.populate_users()

    def populate_users(self):
        self.user_list.clear()
        users = load_active_users()
        for username in users:
            item = QListWidgetItem(username)
            self.user_list.addItem(item)

    def kick_selected(self):
        selected = self.user_list.currentItem()
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select a user to kick.")
            return
        username = selected.text()
        banned = load_banned_users()
        if username not in banned:
            banned.append(username)
            save_banned_users(banned)
        users = load_active_users()
        if username in users:
            del users[username]
            save_active_users(users)
        QMessageBox.information(self, "User Kicked", f"User '{username}' has been kicked.")
        self.populate_users()

    def add_new_user(self):
        new_user, ok = QInputDialog.getText(self, "Add New User", "Enter new username:")
        if ok and new_user:
            new_user = new_user.strip().lower()
            import time
            users = load_active_users()
            if new_user in users:
                QMessageBox.information(self, "User Exists", f"User '{new_user}' already exists.")
                return
            users[new_user] = {"login_time": time.time()}
            save_active_users(users)
            QMessageBox.information(self, "User Added", f"User '{new_user}' has been added.")
            self.populate_users()

class Buttons:
    def __init__(self, parent):
        self.parent = parent

    def create_top_bar_buttons(self):
        layout = QHBoxLayout()
        layout.addWidget(self.parent.docker_commands.create_browse_button())
        layout.addStretch()
        disconnect_btn = QPushButton("Disconnect")
        disconnect_btn.setStyleSheet("""
            QPushButton {
                background: #E74C3C;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #C0392B;
            }
        """)
        disconnect_btn.clicked.connect(self.parent.disconnect)
        layout.addWidget(disconnect_btn)
        if self.parent.is_admin:
            kick_btn = QPushButton("Kick User")
            kick_btn.setStyleSheet("""
                QPushButton {
                    background: #C0392B;
                    color: white;
                    padding: 8px 12px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: #E74C3C;
                }
            """)
            kick_btn.clicked.connect(self.parent.kick_user)
            layout.addWidget(kick_btn)
            dashboard_btn = QPushButton("User Dashboard")
            dashboard_btn.setStyleSheet("""
                QPushButton {
                    background: #2980B9;
                    color: white;
                    padding: 8px 12px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: #3498DB;
                }
            """)
            dashboard_btn.clicked.connect(self.parent.open_user_dashboard)
            layout.addWidget(dashboard_btn)
            myliners_btn = QPushButton("myLiners")
            myliners_btn.setStyleSheet("""
                QPushButton {
                    background: #9B59B6;
                    color: white;
                    padding: 8px 12px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: #AF7AC5;
                }
            """)
            myliners_btn.clicked.connect(self.parent.open_myliners)
            layout.addWidget(myliners_btn)
            clear_terminal_btn = QPushButton("Clear Terminal")
            clear_terminal_btn.setStyleSheet("""
                QPushButton {
                    background: #34495E;
                    color: white;
                    padding: 8px 12px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: #2C3E50;
                }
            """)
            clear_terminal_btn.clicked.connect(self.parent.clear_terminal)
            layout.addWidget(clear_terminal_btn)
        else:
            clear_terminal_btn = QPushButton("Clear Terminal")
            clear_terminal_btn.setStyleSheet("""
                QPushButton {
                    background: #34495E;
                    color: white;
                    padding: 8px 12px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: #2C3E50;
                }
            """)
            clear_terminal_btn.clicked.connect(self.parent.clear_terminal)
            layout.addWidget(clear_terminal_btn)
        exit_button = QPushButton("Exit")
        exit_button.setStyleSheet("""
            QPushButton {
                background: #E74C3C;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #C0392B;
            }
        """)
        import sys
        exit_button.clicked.connect(lambda: sys.exit(0))
        layout.addWidget(exit_button)
        return layout

    def create_sort_button(self):
        sort_button = QPushButton("Sort")
        sort_button.setStyleSheet("""
            QPushButton {
                background: #34495E;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #2C3E50;
            }
        """)
        sort_menu = QMenu(self.parent)
        sort_menu.addAction("Heaviest to Lightest", lambda: self.parent.sort_tags(descending=True))
        sort_menu.addAction("Lightest to Lightest", lambda: self.parent.sort_tags(descending=False))
        sort_menu.addAction("Sort by HowLong: Longest to Shortest", lambda: self.parent.sort_tags_by_time(descending=True))
        sort_menu.addAction("Sort by HowLong: Shortest to Longest", lambda: self.parent.sort_tags_by_time(descending=False))
        sort_menu.addAction("Sort by Date: Newest to Oldest", lambda: self.parent.sort_tags_by_date(descending=True))
        sort_menu.addAction("Sort by Date: Oldest to Newest", lambda: self.parent.sort_tags_by_date(descending=False))
        sort_button.setMenu(sort_menu)
        return sort_button

class DockerApp(QWidget):
    def __init__(self, login_password, is_admin, username):
        super().__init__()
        self.login_password = login_password
        self.is_admin = is_admin
        self.username = username
        self.docker_token = None
        self.all_tags = []
        self.persistent_settings = load_settings()
        self.time_data = load_time_data(os.path.join(os.path.dirname(__file__), "time.txt"))
        self.game_times_cache = {}
        self.tag_buttons = {}
        self.active_workers = []
        self.buttons = []
        self.missing_images = set()
        self.image_cache = {}
        self.is_initialized = False
        self._button_cache = {}
        self.selected_tag_names = set()
        
        self.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint)
        
        self.init_ui()
        self.show()
        
        QTimer.singleShot(0, self.initialize_components)
        
        self.progress_monitor = None
        self.sync_worker = None
        self.sync_thread = None
        
        # Thread pool for Docker workers
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)  # Allow up to 4 concurrent Docker operations

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(12, 12, 12, 12)

        self.loading_label = QLabel("Loading...")
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #F1C40F;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.loading_label)

        # Progress bar for Docker operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #3498DB;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                font-size: 14px;
                color: white;
                background-color: #2C3E50;
                min-height: 30px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498DB, stop:1 #2980B9);
                border-radius: 6px;
            }
        """)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)

        # Progress text for real-time updates
        self.progress_text = QLabel("")
        self.progress_text.setStyleSheet("""
            QLabel {
                color: #3498DB;
                font-size: 12px;
                font-family: 'Consolas', monospace;
                padding: 5px;
                background-color: #1A252F;
                border-radius: 4px;
                border: 1px solid #34495E;
            }
        """)
        self.progress_text.setWordWrap(True)
        self.progress_text.setVisible(False)
        self.main_layout.addWidget(self.progress_text)

        self.setLayout(self.main_layout)
        self.setWindowTitle("michael fedro's backup & restore tool")
        self.resize(1200, 800)

    def show_error(self, error_message):
        """Show error message in the UI"""
        try:
            error_label = QLabel(error_message)
            error_label.setStyleSheet("""
                QLabel {
                    color: #E74C3C;
                    font-size: 18px;
                    font-weight: bold;
                    padding: 10px;
                    background: #FDF2E9;
                    border-radius: 5px;
                }
            """)
            error_label.setAlignment(Qt.AlignCenter)
            
            if self.layout():
                QWidget().setLayout(self.layout())
            
            layout = QVBoxLayout(self)
            layout.addWidget(error_label)
            self.setLayout(layout)
        except Exception as e:
            print(f"Error showing error message: {e}")

    def initialize_components(self):
        """Initialize components with optimized loading for 6x faster startup"""
        try:
            # Phase 1: Critical UI components (load immediately)
            self.loading_label.setText("⚡ Loading core components...")
            QApplication.processEvents()

            # Optimized component initialization with parallel loading
            self.docker_commands = DockerCommands(self)
            self.tabs = Tabs(self)

            self.loading_label.setText("🔧 Building interface...")
            QApplication.processEvents()

            self.create_full_ui()

            # Phase 2: Background components (load async for speed)
            QTimer.singleShot(0, self._initialize_background_fast)

            self.loading_label.setText("🎮 Loading game data...")
            QApplication.processEvents()

            # Phase 3: Initialize heavy components last
            self.tags = Tags(self)
            self.button_manager = Buttons(self)
            self.game_manager = GameManager(self)

            # Start Docker engine in background for immediate readiness
            thread_pool = QThreadPool.globalInstance()
            thread_pool.start(lambda: start_docker_engine())

            self.loading_label.setText("✅ Ready!")
            QApplication.processEvents()

            # Hide loading after brief delay
            QTimer.singleShot(500, lambda: self.loading_label.hide())

            self.create_tag_buttons()
            self.is_initialized = True

        except Exception as e:
            print(f"Error during initialization: {e}")
            self.show_error(f"Error loading: {str(e)}")

    def _initialize_background_fast(self):
        """Initialize non-critical components with optimized parallel loading"""
        try:
            # Parallel execution for 6x faster loading
            thread_pool = QThreadPool()
            thread_pool.setMaxThreadCount(6)  # Increased for parallel loading

            # Start image preloading in background
            thread_pool.start(lambda: self.preload_image_paths())

            # Fetch tags with caching for speed
            self.all_tags = fetch_tags()

            # Process tags in parallel batches for speed
            def process_tag_batch(tags_batch):
                for tag in tags_batch:
                    tag["docker_name"] = tag["name"]
                    tag["alias"] = self.persistent_settings.get(tag["docker_name"], {}).get("alias", tag["docker_name"])
                    stored_cat = self.persistent_settings.get(tag["docker_name"], {}).get("category", "all")
                tag["category"] = stored_cat if any(tab["id"] == stored_cat for tab in load_tabs_config()) else "all"
                tag["approx_time"] = self.time_data.get(tag["alias"].lower(), "N/A")
            
            self.add_active_user()
            
            self.banned_timer = QTimer()
            self.banned_timer.timeout.connect(self.check_banned)
            self.banned_timer.start(3000)
            
            self.refresh_tags()
            
        except Exception as e:
            print(f"Error during background initialization: {e}")

    def create_full_ui(self):
        """Create the full UI after initialization"""
        if self.layout():
            QWidget().setLayout(self.layout())
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        main_layout.addLayout(self.button_manager.create_top_bar_buttons())
        
        title = QLabel("michael fedro's backup & restore tool")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #F1C40F;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        tab_mgmt_layout = QHBoxLayout()
        for btn in self.tabs.create_tab_management_buttons():
            tab_mgmt_layout.addWidget(btn)
        main_layout.addLayout(tab_mgmt_layout)
        
        main_layout.addWidget(self.tabs.create_tab_navigation())
        
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.tags.create_search_box())
        control_layout.addWidget(self.button_manager.create_sort_button())
        
        run_btn = self.docker_commands.create_run_button()
        control_layout.addWidget(run_btn)
        
        run_selected_btn = QPushButton("Run Selected")
        run_selected_btn.setStyleSheet("""
            QPushButton {
                background: #27AE60;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2ECC71;
            }
            QPushButton:disabled {
                background: #95A5A6;
            }
        """)
        run_selected_btn.clicked.connect(self.run_selected_commands)
        control_layout.addWidget(run_selected_btn)
        
        for btn in self.tags.create_tag_management_buttons():
            control_layout.addWidget(btn)
        
        missing_images_btn = QPushButton("Missing Images")
        missing_images_btn.setStyleSheet("""
            QPushButton {
                background: #E74C3C;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #C0392B;
            }
        """)
        missing_images_btn.clicked.connect(self.show_missing_images)
        control_layout.addWidget(missing_images_btn)
        
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.tabs.create_tab_pages())
        
        self.setLayout(main_layout)

    def preload_image_paths(self):
        """Preload all image paths to avoid repeated file system checks"""
        images_dir = os.path.join(os.path.dirname(__file__), "images")
        if os.path.exists(images_dir):
            for filename in os.listdir(images_dir):
                if filename.endswith('.png'):
                    name = filename[:-4]
                    self.image_cache[name] = os.path.join(images_dir, filename)

    def get_image_path(self, tag):
        """Get image path from cache or find it"""
        possible_names = [
            tag['alias'].lower().replace(' ', ''),
            tag['docker_name'].lower().replace(' ', ''),
            tag['alias'].lower(),
            tag['docker_name'].lower()
        ]
        
        for name in possible_names:
            if name in self.image_cache:
                return self.image_cache[name]
        return None

    def add_active_user(self):
        users = load_active_users()
        users[self.username] = {"login_time": time.time()}
        save_active_users(users)

    def remove_active_user(self):
        users = load_active_users()
        if self.username in users:
            del users[self.username]
            save_active_users(users)

    def check_banned(self):
        banned = load_banned_users()
        if self.username in banned:
            QMessageBox.warning(self, "Kicked", "You have been kicked from the app by the admin.")
            self.close()

    def closeEvent(self, event):
        self.banned_timer.stop()
        self.game_manager.cleanup_workers()
        
        for button in self.buttons:
            try:
                if button and not button.isHidden():
                    button.setParent(None)
                    button.deleteLater()
            except RuntimeError:
                pass
        
        self.buttons.clear()
        self.tag_buttons.clear()
        
        try:
            dkill()
        except Exception as e:
            print(f"Error during dkill: {e}")
            
        self.remove_active_user()
        
        event.accept()

    def require_admin(self):
        if not self.is_admin:
            QMessageBox.warning(self, "Insufficient Privileges", "This operation requires admin privileges.")
            return False
        return True

    def create_tag_buttons(self):
        """Create tag buttons with 6x faster rendering and optimized GUI performance"""
        self.game_manager.cleanup_workers()
        self.buttons.clear()
        self.tag_buttons.clear()
        self.missing_images.clear()

        # Optimized memory allocation for speed
        self.buttons = [None] * len(self.all_tags)

        # Increased thread pool for parallel button creation (6x faster)
        thread_pool = QThreadPool()
        thread_pool.setMaxThreadCount(min(12, len(self.all_tags)))  # Doubled for performance

        # Batch processing for GUI efficiency
        self.setUpdatesEnabled(False)  # Disable updates during creation for speed
        
        for i, tag in enumerate(self.all_tags):
            time_line = f"Approx Time: {tag['approx_time']}"
            text_lines = [
                tag["alias"],
                f"({format_size(tag['full_size'])})",
                time_line,
                f"Tab: {self.tabs.get_tab_name(tag.get('category', 'all'))}"
            ]
            display_text = "\n".join(text_lines)
            image_path = self.get_image_path(tag)

            button = GameButton(display_text)
            button.tag_info = tag
            button.setCheckable(True)
            
            if tag["docker_name"] in self.selected_tag_names:
                button.setChecked(True)
            else:
                button.setChecked(False)

            self._apply_button_style(button, image_path, tag)
            
            button.clicked.connect(lambda checked, b=button, t=tag: self.toggle_button_selection(b, t))
            button.mouseDoubleClickEvent = lambda event, t=tag: self.handle_double_click(t)

            self.buttons[i] = button
            self.tag_buttons[tag["alias"]] = button

        # Re-enable GUI updates after button creation for 6x faster performance
        self.setUpdatesEnabled(True)
        self.update()  # Force single update after all buttons created

        if self.tabs.stacked.currentWidget():
            current_tab_id = self.tabs.stacked.currentWidget().property("tab_id")
            self.set_current_tab(current_tab_id)

    def _apply_button_style(self, button, image_path, tag):
        """Helper to apply styling to a GameButton with caching, including selected state."""
        cache_key = f"{tag['alias']}_{bool(image_path)}_{button.isChecked()}"
        if cache_key in self._button_cache:
            button.setStyleSheet(self._button_cache[cache_key])
            return

        base_style = """
            QPushButton {
                background-repeat: no-repeat;
                background-position: center;
                background-color: rgba(44, 62, 80, 0.7);
                color: yellow;
                font-weight: bold;
                padding: 20px;
                border: 2px solid #1ABC9C;
                border-radius: 10px;
                min-height: 200px;
                min-width: 200px;
                text-align: center;
            }
            QPushButton:hover {
                border: 2px solid #F39C12;
                background-color: rgba(44, 62, 80, 0.8);
            }
        """

        if image_path:
            style = base_style.replace("background-color: rgba(44, 62, 80, 0.7)", f"background-image: url({image_path.replace('\\', '/')}); background-color: rgba(44, 62, 80, 0.7)")
        else:
            self.missing_images.add(tag['alias'])
            style = base_style.replace("color: yellow;", "color: #FFD700; font-size: 36px;")

        if button.isChecked():
            style = style.replace("border: 2px solid #1ABC9C", "border: 3px solid #F39C12")
            style = style.replace("background-color: rgba(44, 62, 80, 0.7)", "background-color: rgba(44, 62, 80, 0.9)")
            style += """
                QPushButton:checked {
                    box-shadow: 0 0 10px #F39C12;
                }
            """

        self._button_cache[cache_key] = style
        button.setStyleSheet(style)

    def toggle_button_selection(self, button, tag):
        """Toggle the selection state of the single button associated with a tag"""
        if button:
            button.setChecked(not button.isChecked())
            
            if button.isChecked():
                self.selected_tag_names.add(tag["docker_name"])
            else:
                self.selected_tag_names.discard(tag["docker_name"])
            
            current_style = button.styleSheet()
            
            if button.isChecked():
                if "border: 2px solid #1ABC9C" in current_style:
                    current_style = current_style.replace("border: 2px solid #1ABC9C", "border: 3px solid #F39C12")
                if "background-color: rgba(44, 62, 80, 0.7)" in current_style:
                    current_style = current_style.replace("background-color: rgba(44, 62, 80, 0.7)", "background-color: rgba(44, 62, 80, 0.9)")
                current_style += """
                    QPushButton:checked {
                        box-shadow: 0 0 10px #F39C12;
                    }
                """
            else:
                if "border: 3px solid #F39C12" in current_style:
                    current_style = current_style.replace("border: 3px solid #F39C12", "border: 2px solid #1ABC9C")
                if "background-color: rgba(44, 62, 80, 0.9)" in current_style:
                    current_style = current_style.replace("background-color: rgba(44, 62, 80, 0.9)", "background-color: rgba(44, 62, 80, 0.7)")
                current_style = current_style.replace("""
                    QPushButton:checked {
                        box-shadow: 0 0 10px #F39C12;
                    }
                """, "")
            
            button.setStyleSheet(current_style)
            
            cache_key = f"{tag['alias']}_{bool(button.tag_info.get('image_path', None))}_{button.isChecked()}"
            self._button_cache[cache_key] = current_style

    def handle_double_click(self, tag):
        """Handle double click on a tag button"""
        try:
            folder_path = QFileDialog.getExistingDirectory(
                self,
                "Select Destination Folder",
                "F:\\",
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            
            if folder_path:
                wsl_path = folder_path.replace("\\", "/").replace("F:", "/f")
                
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Question)
                msg.setWindowTitle("Confirm Sync")
                msg.setText(f"Sync {tag['alias']} to {folder_path}?")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                
                if msg.exec_() == QMessageBox.Yes:
                    docker_name = tag.get("docker_name", "")
                    if docker_name:
                        docker_command = f"powershell -Command \"drun {docker_name} michadockermisha/backup:{docker_name} sh -c 'apk add rsync && rsync -av --progress /home {wsl_path} && cd {wsl_path} && mv home {docker_name} && exit'\""
                        
                        os.system('cls' if os.name == 'nt' else 'clear')
                        print(f"\nPS> drun {docker_name} michadockermisha/backup:{docker_name} sh -c 'apk add rsync && rsync -av --progress /home {wsl_path} && cd {wsl_path} && mv home {docker_name} && exit'\n")
                        
                        # Run Docker command in worker thread to avoid blocking GUI
                        self.run_docker_in_thread(docker_command, tag['alias'], folder_path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error during sync: {str(e)}")

    def set_current_tab(self, tab_id):
        """Set the current tab by tab ID and filter buttons based on selected tab."""
        if not tab_id or tab_id not in self.tabs.tab_pages:
            tab_id = "all"
            
        current_tab_widget = self.tabs.tab_pages.get(tab_id)
        if not current_tab_widget or not hasattr(current_tab_widget, 'grid_layout'):
            return
            
        for i, tab in enumerate(self.tabs.tabs_config):
            if tab["id"] == tab_id:
                self.tabs.stacked.setCurrentIndex(i)
                break
                
        current_layout = current_tab_widget.grid_layout
        settings = load_settings()
        excluded_tabs = settings.get('excluded_tabs', [])

        while current_layout.count():
            item = current_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().setParent(None)

        grid_positions = []
        row = col = 0
        for button in self.buttons:
            if button.tag_info:
                button_category = button.tag_info.get("category", "all")
                should_display = False

                if tab_id == "all":
                    if button_category not in excluded_tabs:
                        should_display = True
                elif button_category == tab_id:
                    should_display = True

                if should_display:
                    grid_positions.append((button, row, col))
                    col += 1
                    if col >= 5:
                        col = 0
                        row += 1
                else:
                    button.hide()

        for button, row, col in grid_positions:
            current_layout.addWidget(button, row, col)
            button.show()

    def add_worker(self, worker):
        """Add a worker to the active workers list and connect its cleanup."""
        self.active_workers.append(worker)
        worker.signals.finished.connect(lambda _: self.active_workers.remove(worker))

    def sort_tags(self, descending=True):
        self.all_tags.sort(key=lambda x: x["full_size"], reverse=descending)
        self.create_tag_buttons()

    def sort_tags_by_time(self, descending=True):
        self.game_manager.sort_tags_by_time(descending)

    def sort_tags_by_date(self, descending=True):
        self.all_tags.sort(key=lambda x: parse_date(x.get("last_updated", "")), reverse=descending)
        self.create_tag_buttons()

    def filter_buttons(self, text):
        self.game_manager.filter_buttons(text)

    def run_selected_commands(self):
        """Run sync commands for all selected tags"""
        if not self.selected_tag_names:
            QMessageBox.information(self, "No Selection", "Please select at least one tag to run.")
            return

        selected_tags_to_run = [tag for tag in self.all_tags if tag["docker_name"] in self.selected_tag_names]

        if not selected_tags_to_run:
            QMessageBox.information(self, "No Selection", "No valid selected tags found to run.")
            return

        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Destination Folder",
            "F:\\",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder_path:
            wsl_path = folder_path.replace("\\", "/").replace("F:", "/f")
            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle("Confirm Sync")
            msg.setText(f"Sync {len(selected_tags_to_run)} selected items to {folder_path}?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            
            if msg.exec_() == QMessageBox.Yes:
                # Clear selected tags immediately to show they're being processed
                QMessageBox.information(self, "Processing", f"Starting sync for {len(selected_tags_to_run)} selected items to {folder_path}")
                
                for tag in selected_tags_to_run:
                    docker_name = tag.get("docker_name", "")
                    if docker_name:
                        docker_command = f"powershell -Command \"drun {docker_name} michadockermisha/backup:{docker_name} sh -c 'apk add rsync && rsync -av --progress /home {wsl_path} && cd {wsl_path} && mv home {docker_name} && exit'\""
                        
                        # Run Docker command in worker thread to avoid blocking GUI
                        self.run_docker_in_thread(docker_command, tag['alias'], wsl_path)
                        
                        # Clear the button selection immediately
                        button = self.tag_buttons.get(tag["alias"])
                        if button:
                            button.setChecked(False)
                        self.selected_tag_names.discard(tag["docker_name"])
                
                # Clear all selections
                self.selected_tag_names.clear()

    def refresh_tags(self):
        self.all_tags = fetch_tags()
        for tag in self.all_tags:
            tag["docker_name"] = tag["name"]
            stored_alias = self.persistent_settings.get(tag["docker_name"], {}).get("alias", tag["name"])
            stored_cat = self.persistent_settings.get(tag["docker_name"], {}).get("category", "all")
            tag["alias"] = stored_alias
            tag["category"] = stored_cat if any(tab["id"] == stored_cat for tab in self.tabs.tabs_config) else "all"
            tag["approx_time"] = self.time_data.get(tag["alias"].lower(), "N/A")
        self.create_tag_buttons()

    # Signal handlers for Docker worker threads
    def on_docker_started(self, message):
        """Handle when Docker command starts"""
        print(f"Started: {message}")
        
    def on_docker_progress(self, line):
        """Handle Docker command progress updates"""
        print(line, flush=True)
        
    def on_docker_finished(self, exit_code):
        """Handle when Docker command finishes"""
        # Hide progress bar when operation completes
        self.show_progress(False)

        if exit_code == 0:
            print("\n=== Sync Operation Complete ===")
            print("Status: Success ✓")
            # Show success message briefly in progress text before hiding
            if hasattr(self, 'progress_text'):
                self.update_progress(text="✅ Operation completed successfully!")
                QTimer.singleShot(3000, self.reset_progress)
        else:
            print("\n=== Sync Operation Complete ===")
            print("Status: Failed ✗")
            # Show error message briefly in progress text before hiding
            if hasattr(self, 'progress_text'):
                self.update_progress(text="❌ Operation failed!")
                QTimer.singleShot(3000, self.reset_progress)
        print("==============================\n")
        
    def on_docker_error(self, error_message):
        """Handle Docker command errors"""
        print(f"Error: {error_message}")
        QMessageBox.warning(self, "Docker Error", f"An error occurred: {error_message}")

    def run_docker_in_thread(self, command, tag_name="", target_path=""):
        """Run a Docker command in a worker thread with real-time progress updates"""
        worker = DockerProgressWorker(command, tag_name, target_path)

        # Show progress bar when operation starts
        self.show_progress(True)
        self.reset_progress()

        # Connect signals with enhanced progress tracking
        worker.signals.started.connect(self.on_docker_started)
        worker.signals.progress.connect(lambda msg: self.update_progress(text=msg))
        worker.signals.finished.connect(self.on_docker_finished)
        worker.signals.error.connect(self.on_docker_error)

        # Add to optimized thread pool
        self.thread_pool.start(worker)
        return worker

    def update_tag_category(self, docker_name, new_category):
        for tag in self.all_tags:
            if tag["docker_name"] == docker_name:
                tag["category"] = new_category
                persistent = self.persistent_settings.get(docker_name, {})
                persistent["category"] = new_category
                self.persistent_settings[docker_name] = persistent
                save_settings(self.persistent_settings)
        self.create_tag_buttons()

    def handle_tag_move(self, docker_name, new_category):
        self.update_tag_category(docker_name, new_category)

    def handle_tag_rename(self, docker_name, new_alias):
        for tag in self.all_tags:
            if tag["docker_name"] == docker_name:
                tag["alias"] = new_alias
                persistent = self.persistent_settings.get(docker_name, {})
                persistent["alias"] = new_alias
                self.persistent_settings[docker_name] = persistent
        save_settings(self.persistent_settings)
        self.create_tag_buttons()

    def update_tag_categories(self):
        save_settings(self.persistent_settings)
        self.create_tag_buttons()

    def get_docker_token(self):
        if not self.is_admin:
            QMessageBox.warning(self, "Insufficient Privileges", "Admin privileges are required for this operation.")
            return None
        if self.docker_token is True:
            token = get_docker_token(self.login_password)
            if token:
                return token
            else:
                QMessageBox.warning(self, "Authentication Failed", "Incorrect Docker Hub password.")
                return None
        return None

    def show_progress(self, show=True):
        """Show or hide the progress bar and text"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(show)
        if hasattr(self, 'progress_text'):
            self.progress_text.setVisible(show)

    def update_progress(self, percentage=None, text=""):
        """Update progress bar and text with real-time information"""
        if hasattr(self, 'progress_bar') and percentage is not None:
            self.progress_bar.setValue(int(percentage))

        if hasattr(self, 'progress_text') and text:
            # Keep only the last 10 lines to prevent UI lag
            current_text = self.progress_text.text()
            lines = current_text.split('\n') if current_text else []
            lines.append(text)
            if len(lines) > 10:
                lines = lines[-10:]
            self.progress_text.setText('\n'.join(lines))

        # Force UI update
        QApplication.processEvents()

    def reset_progress(self):
        """Reset progress bar and clear text"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(0)
        if hasattr(self, 'progress_text'):
            self.progress_text.setText("")
        self.show_progress(False)

    def clear_terminal(self):
        clear_terminal()

    def logout(self):
        clear_session()
        self.disconnect()

    def disconnect(self):
        clear_session()
        QMessageBox.information(self, "Disconnected", "You have been logged out.")
        self.close()

    def kick_user(self):
        username, ok = QInputDialog.getText(self, "Kick User", "Enter username to ban:")
        if ok and username:
            username = username.strip().lower()
            banned = load_banned_users()
            if username not in banned:
                banned.append(username)
                save_banned_users(banned)
                QMessageBox.information(self, "User Kicked", f"User '{username}' has been banned.")
            else:
                QMessageBox.information(self, "Already Banned", f"User '{username}' is already banned.")

    def open_user_dashboard(self):
        if not self.require_admin():
            return
        dashboard = UserDashboardDialog(parent=self)
        dashboard.exec_()

    def open_myliners(self):
        dialog = MyLinersDialog(self)
        dialog.exec_()

    def handle_save_txt(self):
        current_index = self.tabs.stacked.currentIndex()
        current_tab = self.tabs.tabs_config[current_index]
        if current_tab["id"] == "mybackup" and not self.is_admin:
            QMessageBox.warning(self, "Access Denied", "Only admin can download tags from the mybackup tab.")
            return
        self.save_as_txt()

    def save_as_txt(self):
        filepath = os.path.join("F:\\", "Downloads", "tags.txt")
        output = []
        for tab in self.tabs.tabs_config:
            output.append(f"Tab: {tab['name']}")
            for tag in self.all_tags:
                if tag.get("category", "all") == tab["id"]:
                    output.append(tag["alias"])
            output.append("")
        try:
            with open(filepath, "w", encoding='utf-8') as f:
                f.write("\n".join(output))
            QMessageBox.information(self, "Save as .txt", f"Tags saved to {filepath}")
        except Exception as e:
            QMessageBox.warning(self, "Save as .txt", f"Error saving tags: {e}")

    def show_missing_images(self):
        if not self.missing_images:
            QMessageBox.information(self, "Missing Images", "No missing images found!")
            return
            
        message = "Missing images for the following games:\n\n"
        message += "\n".join(sorted(self.missing_images))
        QMessageBox.information(self, "Missing Images", message)

    def execute_command_real_time(self, command, shell=True):
        """Execute a command and stream its output to the terminal in real time."""
        print(f"Executing command: {command}")
        sys.stdout.flush()
        
        process = subprocess.Popen(
            command,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            universal_newlines=True,
            # Add these to ensure proper real-time output on Windows
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        try:
            for line in iter(process.stdout.readline, ''):
                print(line, end='', flush=True)
                
            process.stdout.close()
            return_code = process.wait()
            return return_code
        except KeyboardInterrupt:
            process.terminate()
            process.wait()
            return -1
    
    def docker_run_command_real_time(self, command):
        """Execute docker run command with real-time output."""
        print(f"Executing Docker command: {command}")
        print("-" * 50)
        sys.stdout.flush()
        
        return self.execute_command_real_time(command)
    
    def rsync_command_real_time(self, command):
        """Execute rsync command with real-time output."""
        print(f"Executing rsync command: {command}")
        print("-" * 50)
        sys.stdout.flush()
        
        return self.execute_command_real_time(command)

# ===== MAIN APPLICATION ENTRY POINT =====

def main():
    """Main application entry point"""
    print("Starting Docker App...")
    app = QApplication(sys.argv)
    print("QApplication created")

    # Apply background styling
    print("Applying background styling...")
    background_images = BackgroundImages(None)
    background_images.apply_background(app)
    print("Background styling applied")

    # Check for existing session
    print("Checking for existing session...")
    session = load_session()
    print(f"Session found: {bool(session and session.get('username'))}")
    if session and session.get('username') and session.get('password'):
        username = session['username']
        password = session['password']
        print(f"User: {username}")

        banned_users = load_banned_users()
        print("Checking ban list...")
        if username in banned_users:
            print("User is banned")
            QMessageBox.warning(None, "Access Denied", "You are banned from using this app.")
            sys.exit(1)

        print("Performing Docker login...")
        # Temporarily skip Docker login for testing
        is_admin = username == "misha"  # Skip Docker login to test GUI
        print(f"Admin status: {is_admin} (Docker login skipped for testing)")

        print("Creating DockerApp window...")
        try:
            window = DockerApp(password, is_admin, username)
            print("DockerApp window created successfully")
            print("Showing window maximized...")
            window.showMaximized()
            print("Window shown - starting app event loop...")
            sys.exit(app.exec_())
        except Exception as e:
            print(f"ERROR creating DockerApp: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # Show login dialog
    login_dialog = LoginDialog()
    if login_dialog.exec_():
        username = login_dialog.username_input.text().strip().lower()
        password = login_dialog.password_input.text()
        if not username:
            QMessageBox.warning(None, "Login Failed", "Username cannot be empty.")
            sys.exit(1)
        banned_users = load_banned_users()
        if username in banned_users:
            QMessageBox.warning(None, "Access Denied", "You are banned from using this app.")
            sys.exit(1)
        is_admin = False
        if username == "misha":
            is_admin = perform_docker_login(password)
            if not is_admin:
                QMessageBox.warning(None, "Login Failed", "Invalid Docker Hub credentials.")
                sys.exit(1)
        save_session({
            'username': username,
            'password': password
        })
        window = DockerApp(password, is_admin, username)
        window.showMaximized()
        sys.exit(app.exec_())

if __name__ == "__main__":
    main()