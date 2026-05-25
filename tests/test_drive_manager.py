import sys
from unittest.mock import MagicMock, patch
import pytest

from datarescue.engine.drive_manager import DriveInfo, list_drives, get_raw_device_path

def test_list_drives_windows():
    mock_partition_c = MagicMock()
    mock_partition_c.device = "C:\\"
    mock_partition_c.mountpoint = "C:\\"
    mock_partition_c.fstype = "NTFS"
    mock_partition_c.opts = "rw,fixed"
    
    mock_partition_d = MagicMock()
    mock_partition_d.device = "D:\\"
    mock_partition_d.mountpoint = "D:\\"
    mock_partition_d.fstype = "FAT32"
    mock_partition_d.opts = "rw,removable"

    mock_partitions = [mock_partition_c, mock_partition_d]

    def mock_usage(path):
        usage = MagicMock()
        if path == "C:\\":
            usage.total = 100_000_000_000
            usage.used = 60_000_000_000
            usage.free = 40_000_000_000
        else:
            usage.total = 16_000_000_000
            usage.used = 4_000_000_000
            usage.free = 12_000_000_000
        return usage

    with patch("psutil.disk_partitions", return_value=mock_partitions), \
         patch("psutil.disk_usage", side_effect=mock_usage), \
         patch("datarescue.engine.drive_manager.get_volume_label", side_effect=lambda path: "System" if path == "C:\\" else "USB"), \
         patch("datarescue.engine.drive_manager.is_removable_drive", side_effect=lambda p: p.mountpoint == "D:\\"), \
         patch("sys.platform", "win32"), \
         patch.dict("os.environ", {"SystemDrive": "C:"}):
         
        # Test default listing (exclude system drive C:\)
        drives = list_drives(include_system=False)
        assert len(drives) == 1
        d = drives[0]
        assert d.device == "D:\\"
        assert d.mountpoint == "D:\\"
        assert d.label == "USB"
        assert d.fstype == "FAT32"
        assert d.total_bytes == 16_000_000_000
        assert d.used_bytes == 4_000_000_000
        assert d.free_bytes == 12_000_000_000
        assert d.is_removable is True

        # Test listing including system drive
        drives_all = list_drives(include_system=True)
        assert len(drives_all) == 2
        mountpoints = [drv.mountpoint for drv in drives_all]
        assert "C:\\" in mountpoints
        assert "D:\\" in mountpoints

def test_list_drives_macos():
    mock_partition_root = MagicMock()
    mock_partition_root.device = "/dev/disk1s1"
    mock_partition_root.mountpoint = "/"
    mock_partition_root.fstype = "apfs"
    mock_partition_root.opts = "rw,journaled"
    
    mock_partition_vol = MagicMock()
    mock_partition_vol.device = "/dev/disk2s1"
    mock_partition_vol.mountpoint = "/Volumes/Backup"
    mock_partition_vol.fstype = "hfs"
    mock_partition_vol.opts = "rw,nodev,nosuid,removable"

    mock_partitions = [mock_partition_root, mock_partition_vol]

    def mock_usage(path):
        usage = MagicMock()
        if path == "/":
            usage.total = 500_000_000_000
            usage.used = 300_000_000_000
            usage.free = 200_000_000_000
        else:
            usage.total = 2_000_000_000_000
            usage.used = 500_000_000_000
            usage.free = 1_500_000_000_000
        return usage

    with patch("psutil.disk_partitions", return_value=mock_partitions), \
         patch("psutil.disk_usage", side_effect=mock_usage), \
         patch("datarescue.engine.drive_manager.get_volume_label", side_effect=lambda path: "Macintosh HD" if path == "/" else "Backup"), \
         patch("datarescue.engine.drive_manager.is_removable_drive", side_effect=lambda p: p.mountpoint.startswith("/Volumes")), \
         patch("sys.platform", "darwin"):
         
        # Exclude system drive (/)
        drives = list_drives(include_system=False)
        assert len(drives) == 1
        assert drives[0].mountpoint == "/Volumes/Backup"
        assert drives[0].is_removable is True

        # Include system drive
        drives_all = list_drives(include_system=True)
        assert len(drives_all) == 2
        mountpoints = [drv.mountpoint for drv in drives_all]
        assert "/" in mountpoints
        assert "/Volumes/Backup" in mountpoints

def test_get_raw_device_path_windows():
    # Patch ctypes at the module level so this test runs cross-platform.
    # The Windows-specific path falls back to "\\\\.\\D:" when CreateFileW returns
    # INVALID_HANDLE_VALUE (-1).
    mock_ctypes = MagicMock()
    mock_ctypes.windll.kernel32.CreateFileW.return_value = -1  # INVALID_HANDLE_VALUE

    with patch("sys.platform", "win32"), \
         patch("datarescue.engine.drive_manager.ctypes", mock_ctypes):
        res = get_raw_device_path("D:\\")
        assert res == "\\\\.\\D:"

def test_get_raw_device_path_macos():
    mock_plist = {
        "DeviceNode": "/dev/disk3s2",
        "DeviceIdentifier": "disk3s2"
    }
    mock_proc = MagicMock()
    mock_proc.stdout = b"some xml plist"
    mock_proc.returncode = 0
    
    with patch("sys.platform", "darwin"), \
         patch("subprocess.run", return_value=mock_proc), \
         patch("plistlib.loads", return_value=mock_plist):
        res = get_raw_device_path("/Volumes/USB")
        assert res == "/dev/disk3s2"
