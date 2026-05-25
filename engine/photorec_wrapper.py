import os
import sys
import subprocess
import threading
from typing import Callable
from datarescue.engine.log_parser import parse_photorec_log

class PhotoRecError(Exception):
    pass

_process_lock = threading.Lock()
_current_process = None

def get_photorec_binary_path() -> str:
    import shutil
    engine_dir = os.path.dirname(os.path.abspath(__file__))
    datarescue_dir = os.path.dirname(engine_dir)

    if sys.platform == "win32":
        return os.path.join(datarescue_dir, "binaries", "win", "photorec.exe")
    elif sys.platform == "darwin":
        return os.path.join(datarescue_dir, "binaries", "mac", "photorec")
    else:
        # BUG-008: On Linux, use the system-installed photorec if available
        system_bin = shutil.which("photorec")
        if system_bin:
            return system_bin
        raise PhotoRecError(
            "PhotoRec binary not found. Please install testdisk (which includes photorec) "
            "via your package manager: e.g. `sudo apt install testdisk`"
        )

def is_destination_on_source(device_path: str, dest_path: str) -> bool:
    # Normalize paths
    device_path = device_path.strip().lower()
    dest_path = os.path.abspath(dest_path).lower()
    
    # 1. Check drive letter match (e.g. C: vs C:\path)
    if len(device_path) >= 2 and device_path[1] == ':':
        drive_letter = device_path[:2]
        if dest_path.startswith(drive_letter):
            return True
            
    # Check if raw device path contains a drive letter (e.g. "\\\\.\\c:")
    if "\\\\.\\" in device_path:
        parts = device_path.split("\\\\.\\")
        if len(parts) > 1:
            drive_part = parts[1]
            if len(drive_part) >= 2 and drive_part[1] == ':':
                drive_letter = drive_part[:2]
                if dest_path.startswith(drive_letter):
                    return True
                    
    # 2. Check if device path is exactly the destination path
    if device_path == dest_path:
        return True
        
    # 3. For macOS, if device path is /dev/diskXsY or a volume mount point,
    # we check if the destination path starts with the mountpoint.
    try:
        import psutil
        for partition in psutil.disk_partitions(all=True):
            if partition.device.lower() == device_path or partition.mountpoint.lower() == device_path:
                mp = os.path.abspath(partition.mountpoint).lower()
                if mp != "/" and dest_path.startswith(mp):
                    return True
    except Exception:
        pass
        
    return False

def run_photorec(device_path: str, dest_path: str, progress_callback: Callable):
    global _current_process
    
    if is_destination_on_source(device_path, dest_path):
        raise PhotoRecError("Destination path cannot be on the source drive to prevent data overwriting.")
        
    binary = get_photorec_binary_path()
    if not os.path.exists(binary):
        raise PhotoRecError(f"PhotoRec binary not found at {binary}")
        
    if sys.platform != "win32":
        try:
            os.chmod(binary, 0o755)
        except Exception:
            pass

    os.makedirs(dest_path, exist_ok=True)
    
    cmd = [
        binary,
        "/log",
        "/d",
        dest_path,
        "/cmd",
        device_path,
        "fileopt,everything,enable,search"
    ]
    
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE

    with _process_lock:
        if _current_process is not None:
            raise PhotoRecError("Another PhotoRec scan is already running.")
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=dest_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                startupinfo=startupinfo,
                text=True
            )
            _current_process = process
        except Exception as e:
            raise PhotoRecError(f"Failed to start PhotoRec process: {e}")

    log_path = os.path.join(dest_path, "photorec.log")
    
    # In case a log file already exists from a previous run, delete it
    if os.path.exists(log_path):
        try:
            os.remove(log_path)
        except Exception:
            pass

    stop_event = threading.Event()
    
    def poll_log():
        last_val = None
        while not stop_event.wait(0.5):
            if os.path.exists(log_path):
                try:
                    data = parse_photorec_log(log_path)
                    files_found = data.get("files_found", 0)
                    pass_num = data.get("current_pass", 0)
                    percent = data.get("percent_complete", 0.0)
                    
                    current_val = (files_found, pass_num, percent)
                    if current_val != last_val:
                        progress_callback(files_found, pass_num, percent)
                        last_val = current_val
                except Exception:
                    pass

    polling_thread = threading.Thread(target=poll_log, daemon=True)
    polling_thread.start()

    try:
        # Wait for the process to complete
        process.wait()
    finally:
        # Stop and join the polling thread
        stop_event.set()
        polling_thread.join(timeout=1.0)
        
        # Read final logs one last time
        if os.path.exists(log_path):
            try:
                data = parse_photorec_log(log_path)
                progress_callback(data.get("files_found", 0), data.get("current_pass", 0), data.get("percent_complete", 0.0))
            except Exception:
                pass
        
        # Clean up global process reference
        with _process_lock:
            if _current_process == process:
                _current_process = None

    if process.returncode == 0:
        progress_callback(-1, -1, 100.0)
    else:
        raise PhotoRecError(f"PhotoRec failed with exit code {process.returncode}")


def cancel_scan():
    """Cancel any currently running PhotoRec scan."""
    with _process_lock:
        if _current_process is not None:
            try:
                _current_process.terminate()
            except Exception:
                pass
