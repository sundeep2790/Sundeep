import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from datarescue.engine.photorec_wrapper import run_photorec, cancel_scan, PhotoRecError
from datarescue.engine.testdisk_wrapper import run_testdisk_analyse, run_testdisk_write, TestDiskError, PartitionResult

def test_run_photorec_success():
    # Mock subprocess.Popen
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.wait.return_value = 0
    
    # We will simulate log file creation in a callback or mock os.path.exists
    log_exists_mock = MagicMock(return_value=True)
    
    # Mock parse_photorec_log
    mock_log_data = {
        "files_found": 42,
        "current_pass": 1,
        "percent_complete": 75.0,
        "last_updated": "2026-05-25T00:00:00"
    }

    progress_calls = []
    def progress_callback(files_found, pass_num, percent):
        progress_calls.append((files_found, pass_num, percent))

    with patch("datarescue.engine.photorec_wrapper.get_photorec_binary_path", return_value="/usr/bin/photorec"), \
         patch("subprocess.Popen", return_value=mock_process), \
         patch("os.path.exists", return_value=True), \
         patch("datarescue.engine.photorec_wrapper.parse_photorec_log", return_value=mock_log_data), \
         patch("os.makedirs"):

        run_photorec("fake_device", "fake_dest", progress_callback)
        
        # Verify the progress callback received the success state (-1, -1, 100.0) at the end
        assert (-1, -1, 100.0) in progress_calls

def test_run_photorec_failure():
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.wait.return_value = 1

    progress_callback = MagicMock()

    with patch("datarescue.engine.photorec_wrapper.get_photorec_binary_path", return_value="/usr/bin/photorec"), \
         patch("subprocess.Popen", return_value=mock_process), \
         patch("os.path.exists", return_value=True), \
         patch("os.makedirs"):

        with pytest.raises(PhotoRecError):
            run_photorec("fake_device", "fake_dest", progress_callback)

def test_run_testdisk_analyse_success():
    # Mock process
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.wait.return_value = 0

    mock_log_content = """
Analyse Disk \\\\.\\PhysicalDrive0 - 1000 GB - CHS 121601 255 63
Current partition structure:
 1 * HPFS - NTFS              0  32 33    12 223 19     204800 [System Reserved]
 2 P FAT32                   12 223 20  2432 254 63   39086085 [NO NAME]
"""

    progress_calls = []
    def progress_callback(percent):
        progress_calls.append(percent)

    # We mock open to read mock_log_content when testdisk.log is read
    mock_open = MagicMock()
    mock_open.return_value.__enter__.return_value.read.return_value = mock_log_content

    with patch("datarescue.engine.testdisk_wrapper.get_testdisk_binary_path", return_value="/usr/bin/testdisk"), \
         patch("subprocess.Popen", return_value=mock_process), \
         patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open):

        partitions = run_testdisk_analyse("fake_device", progress_callback)
        
        assert len(partitions) == 2
        assert partitions[0].status == "*"
        assert partitions[0].type == "HPFS - NTFS"
        assert partitions[0].size_sectors == 204800
        assert partitions[0].label == "System Reserved"
        
        assert partitions[1].status == "P"
        assert partitions[1].type == "FAT32"
        assert partitions[1].size_sectors == 39086085
        assert partitions[1].label == "NO NAME"
        
        assert 100.0 in progress_calls

def test_run_testdisk_write_safety():
    # Calling write without safety confirmation should raise ValueError
    with pytest.raises(ValueError):
        run_testdisk_write("fake_device", PartitionResult("*", "FAT32", 0,0,0,0,0,0,0), safety_confirmed=False)

def test_run_testdisk_write_success():
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = ("Success", "")

    partition = PartitionResult("*", "FAT32", 0, 0, 0, 0, 0, 0, 1000)

    with patch("datarescue.engine.testdisk_wrapper.get_testdisk_binary_path", return_value="/usr/bin/testdisk"), \
         patch("subprocess.Popen", return_value=mock_process), \
         patch("os.path.exists", return_value=True):
        res = run_testdisk_write("fake_device", partition, safety_confirmed=True)
        assert res is True
        mock_process.communicate.assert_called_with(input="Y\n", timeout=10.0)
