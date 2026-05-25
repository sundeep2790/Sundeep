import sys
import os

# Add parent directory of 'datarescue' to sys.path to resolve absolute imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
import socket
import threading
import logging
from config import load_config
from gui.app import CTkApp

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def check_internet(host="8.8.8.8", port=53, timeout=3) -> bool:
    """
    Check if the device has internet connectivity.
    """
    try:
        # create_connection handles both connect and close cleanly
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def check_macos_disk_access() -> bool:
    """
    Check if the application has Full Disk Access on macOS.
    Returns True if platform is not macOS, or if access is granted.
    """
    if sys.platform != "darwin":
        return True
    try:
        # A standard directory restricted by macOS TCC unless Full Disk Access is granted
        os.listdir("/Library/Application Support/com.apple.TCC")
        return True
    except PermissionError:
        return False
    except Exception:
        return False

def main():
    # 1. Initialize configuration (creates encrypted default config if first run)
    logging.info("Initializing configuration...")
    config = load_config()
    logging.info(f"Configuration loaded. Device Token: {config.get('device_token')}")
    
    # 2. Check for internet connectivity (non-blocking thread)
    logging.info("Checking internet connectivity...")
    is_online = [False]  # Using mutable container to share state with thread
    
    def run_check():
        is_online[0] = check_internet()
        status = "online" if is_online[0] else "offline"
        logging.info(f"Internet check complete: Device is {status}.")
        
    check_thread = threading.Thread(target=run_check, daemon=True)
    check_thread.start()
    
    # Give the thread up to 150ms to do a quick check, but do not block UI
    check_thread.join(timeout=0.15)
    
    # 3. Handle macOS Full Disk Access request
    if sys.platform == "darwin":
        logging.info("Running macOS specific platform checks...")
        if not check_macos_disk_access():
            # Trigger an AppleScript dialog box prompting the user to grant Full Disk Access
            applescript_cmd = [
                'osascript',
                '-e',
                'display dialog "DataRescue requires Full Disk Access to scan disk partitions. '
                'Please add this application to System Settings > Privacy & Security > Full Disk Access." '
                'buttons {"OK"} default button "OK" with icon caution with title "Full Disk Access Required"'
            ]
            try:
                import subprocess
                subprocess.run(applescript_cmd, check=False)
            except Exception as e:
                logging.error(f"Failed to run macOS disk access dialog: {e}")
            
    # 4. Launch CustomTkinter App
    logging.info("Launching GUI application...")
    app = CTkApp(is_online=is_online[0])
    app.run()

if __name__ == "__main__":
    main()
