import os
import sys
import subprocess
import tempfile
import re
import threading
from typing import Callable, List
from dataclasses import dataclass

class TestDiskError(Exception):
    __test__ = False

@dataclass
class PartitionResult:
    status: str          # *, P, L, E, D, K
    type: str            # e.g., HPFS - NTFS, FAT32
    start_cylinder: int
    start_head: int
    start_sector: int
    end_cylinder: int
    end_head: int
    end_sector: int
    size_sectors: int
    label: str = ""

def get_testdisk_binary_path() -> str:
    import shutil
    engine_dir = os.path.dirname(os.path.abspath(__file__))
    datarescue_dir = os.path.dirname(engine_dir)

    if sys.platform == "win32":
        return os.path.join(datarescue_dir, "binaries", "win", "testdisk.exe")
    elif sys.platform == "darwin":
        return os.path.join(datarescue_dir, "binaries", "mac", "testdisk")
    else:
        # BUG-008: On Linux, use the system-installed testdisk if available
        system_bin = shutil.which("testdisk")
        if system_bin:
            return system_bin
        raise TestDiskError(
            "TestDisk binary not found. Please install it via your package manager: "
            "e.g. `sudo apt install testdisk`"
        )

def parse_testdisk_log(log_content: str) -> List[PartitionResult]:
    partitions = []
    # Regex to match the partition layout in testdisk.log
    # Example:
    # 1 * HPFS - NTFS              0  32 33    12 223 19     204800 [System Reserved]
    #   P FAT32                    0   1  1  2432 254 63   39086085 [NO NAME]
    pattern = re.compile(
        r"^\s*(\d*)\s*([\*PLEDKD])\s+([A-Za-z0-9\s-]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)(?:\s+\[(.*?)\])?"
    )
    for line in log_content.splitlines():
        match = pattern.match(line)
        if match:
            status = match.group(2)
            ptype = match.group(3).strip()
            start_c = int(match.group(4))
            start_h = int(match.group(5))
            start_s = int(match.group(6))
            end_c = int(match.group(7))
            end_h = int(match.group(8))
            end_s = int(match.group(9))
            size = int(match.group(10))
            label = match.group(11) or ""
            
            partitions.append(PartitionResult(
                status=status,
                type=ptype,
                start_cylinder=start_c,
                start_head=start_h,
                start_sector=start_s,
                end_cylinder=end_c,
                end_head=end_h,
                end_sector=end_s,
                size_sectors=size,
                label=label
            ))
    # Deduplicate partitions with identical attributes
    unique_partitions = []
    seen = set()
    for p in partitions:
        key = (p.status, p.type, p.start_cylinder, p.start_head, p.start_sector,
               p.end_cylinder, p.end_head, p.end_sector, p.size_sectors, p.label)
        if key not in seen:
            seen.add(key)
            unique_partitions.append(p)
    return unique_partitions

def run_testdisk_analyse(device_path: str, progress_callback: Callable) -> List[PartitionResult]:
    binary = get_testdisk_binary_path()
    if not os.path.exists(binary):
        raise TestDiskError(f"TestDisk binary not found at {binary}")
        
    if sys.platform != "win32":
        try:
            os.chmod(binary, 0o755)
        except Exception:
            pass

    cmd = [
        binary,
        "/log",
        "/cmd",
        device_path,
        "analyse,list"
    ]
    
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE

    # Use a temporary directory to avoid log file conflicts
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "testdisk.log")
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=tmpdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                startupinfo=startupinfo,
                text=True
            )
        except Exception as e:
            raise TestDiskError(f"Failed to start TestDisk process: {e}")

        # Start a thread to report incremental progress
        stop_event = threading.Event()
        
        def report_fake_progress():
            percent = 10.0
            while not stop_event.wait(0.5):
                progress_callback(percent)
                if percent < 90.0:
                    percent += 5.0

        progress_thread = threading.Thread(target=report_fake_progress, daemon=True)
        progress_thread.start()

        try:
            # Wait for TestDisk to finish
            process.wait()
        finally:
            stop_event.set()
            progress_thread.join(timeout=1.0)

        if process.returncode != 0 and process.returncode != 1:
            # Note: TestDisk sometimes returns 1 even when it finishes successfully (or reports warnings)
            # So we only raise error on critical exit codes (e.g. negative or > 1) if log file doesn't exist
            if not os.path.exists(log_path):
                raise TestDiskError(f"TestDisk failed with exit code {process.returncode}")

        progress_callback(100.0)

        # Parse the log file
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    log_content = f.read()
                return parse_testdisk_log(log_content)
            except Exception as e:
                raise TestDiskError(f"Failed to read or parse TestDisk log: {e}")
        else:
            raise TestDiskError("TestDisk did not generate a log file.")

def run_testdisk_write(device_path: str, partition: PartitionResult, safety_confirmed: bool = False) -> bool:
    if not safety_confirmed:
        raise ValueError("Safety confirmation is required to write partition tables.")

    binary = get_testdisk_binary_path()
    if not os.path.exists(binary):
        raise TestDiskError(f"TestDisk binary not found at {binary}")

    if sys.platform != "win32":
        try:
            os.chmod(binary, 0o755)
        except Exception:
            pass

    # Command to write partition table
    # Typically: testdisk /cmd {device_path} write
    cmd = [
        binary,
        "/cmd",
        device_path,
        "write"
    ]

    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            startupinfo=startupinfo,
            text=True
        )
        # Write "Y" to confirm if prompted
        stdout, stderr = process.communicate(input="Y\n", timeout=10.0)
        return process.returncode == 0
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except Exception:
            pass
        raise TestDiskError("TestDisk write timed out.")
    except Exception as e:
        raise TestDiskError(f"TestDisk write failed: {e}") from e
