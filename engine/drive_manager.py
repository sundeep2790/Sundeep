import os
import sys
import psutil
import ctypes
from dataclasses import dataclass

@dataclass
class DriveInfo:
    device: str
    mountpoint: str
    label: str
    fstype: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    is_removable: bool

def get_volume_label(mountpoint: str) -> str:
    if sys.platform == "win32":
        import ctypes
        path = mountpoint
        if not path.endswith("\\"):
            path += "\\"
        volume_name_buffer = ctypes.create_unicode_buffer(1024)
        res = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(path),
            volume_name_buffer,
            ctypes.sizeof(volume_name_buffer),
            None, None, None, None, 0
        )
        if res:
            return volume_name_buffer.value
        return ""
    elif sys.platform == "darwin":
        try:
            import plistlib
            import subprocess
            result = subprocess.run(
                ["diskutil", "info", "-plist", mountpoint],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            data = plistlib.loads(result.stdout)
            return data.get("VolumeName", "")
        except Exception:
            pass
    return ""

def is_removable_drive(partition) -> bool:
    mountpoint = partition.mountpoint
    if sys.platform == "win32":
        import ctypes
        path = mountpoint
        if not path.endswith("\\"):
            path += "\\"
        drive_type = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(path))
        return drive_type in (2, 5)  # DRIVE_REMOVABLE = 2, DRIVE_CDROM = 5
    elif sys.platform == "darwin":
        if "removable" in partition.opts:
            return True
        if mountpoint.startswith("/Volumes/"):
            return True
        try:
            import plistlib
            import subprocess
            result = subprocess.run(
                ["diskutil", "info", "-plist", mountpoint],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            data = plistlib.loads(result.stdout)
            return bool(data.get("RemovableMedia", False) or data.get("Ejectable", False))
        except Exception:
            pass
    else:
        if "removable" in partition.opts:
            return True
    return False

def list_drives(include_system: bool = False) -> list[DriveInfo]:
    drives = []
    try:
        partitions = psutil.disk_partitions(all=False)
    except Exception:
        partitions = []
    
    # Identify system drive mountpoint
    system_mount = None
    if sys.platform == "win32":
        system_mount = os.environ.get("SystemDrive", "C:").upper().rstrip("\\") + "\\"
    elif sys.platform == "darwin":
        system_mount = "/"
    else:
        system_mount = "/"

    for p in partitions:
        mountpoint = p.mountpoint
        if not mountpoint:
            continue
            
        # Check system drive filtering
        is_system = False
        if sys.platform == "win32":
            if mountpoint.upper().startswith(system_mount.upper()):
                is_system = True
        else:
            if mountpoint == system_mount:
                is_system = True
                
        if is_system and not include_system:
            continue
            
        # Get usage
        total_bytes = 0
        used_bytes = 0
        free_bytes = 0
        try:
            usage = psutil.disk_usage(mountpoint)
            total_bytes = usage.total
            used_bytes = usage.used
            free_bytes = usage.free
        except Exception:
            # Drive might not be ready or access denied
            pass
            
        label = get_volume_label(mountpoint)
        is_removable = is_removable_drive(p)
        
        drives.append(DriveInfo(
            device=p.device,
            mountpoint=mountpoint,
            label=label,
            fstype=p.fstype,
            total_bytes=total_bytes,
            used_bytes=used_bytes,
            free_bytes=free_bytes,
            is_removable=is_removable
        ))
    return drives

def get_raw_device_path(mountpoint: str) -> str:
    if sys.platform == "win32":
        # Extract drive letter (e.g. "D:\\" -> "D")
        drive_letter = os.path.splitdrive(mountpoint)[0].rstrip(":")
        if not drive_letter:
            # If no drive letter, maybe it's already a raw path or UNC path
            return mountpoint
        
        # Try to resolve to physical drive using IOCTL
        import ctypes
        import struct
        drive_path = f"\\\\.\\{drive_letter}:"
        GENERIC_READ = 0x80000000
        FILE_SHARE_READ = 1
        FILE_SHARE_WRITE = 2
        OPEN_EXISTING = 3
        INVALID_HANDLE_VALUE = -1
        
        handle = ctypes.windll.kernel32.CreateFileW(
            drive_path,
            GENERIC_READ,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            0,
            None
        )
        if handle != INVALID_HANDLE_VALUE:
            IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS = 0x560000
            buf = ctypes.create_string_buffer(1024)
            bytes_returned = ctypes.c_ulong()
            
            res = ctypes.windll.kernel32.DeviceIoControl(
                handle,
                IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS,
                None, 0,
                buf, len(buf),
                ctypes.byref(bytes_returned),
                None
            )
            ctypes.windll.kernel32.CloseHandle(handle)
            
            if res:
                num_extents = struct.unpack("<I", buf[:4])[0]
                if num_extents > 0:
                    disk_number = struct.unpack("<I", buf[8:12])[0]
                    return f"\\\\.\\PhysicalDrive{disk_number}"
        return drive_path
        
    elif sys.platform == "darwin":
        try:
            import plistlib
            import subprocess
            result = subprocess.run(
                ["diskutil", "info", "-plist", mountpoint],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            data = plistlib.loads(result.stdout)
            device_node = data.get("DeviceNode")
            if device_node:
                return device_node
            device_id = data.get("DeviceIdentifier")
            if device_id:
                return f"/dev/{device_id}"
        except Exception:
            pass
        return mountpoint
    else:
        # Linux or other POSIX fallback
        return mountpoint
