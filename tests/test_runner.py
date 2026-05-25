import sys
import os
import unittest
import queue
import tempfile
import shutil
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datarescue.engine.runner import PhotoRecRunner

class TestPhotoRecRunnerArgs(unittest.TestCase):
    def setUp(self):
        self.progress_queue = queue.Queue()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @patch("subprocess.Popen")
    def test_run_real_scan_logical_drive_win32(self, mock_popen):
        # On Windows, a logical volume handle (e.g. \\.\E:) should NOT include the partition index '1'
        mock_process = MagicMock()
        mock_process.poll.return_value = 0 # finish immediately
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        drive = {
            'device': 'E:\\',
            'mountpoint': 'E:\\',
            'fstype': 'NTFS',
            'label': 'Local Disk (E:)'
        }
        
        runner = PhotoRecRunner(drive, self.temp_dir, self.progress_queue)
        
        # We need os.path.exists to return True for the photorec binary,
        # but let other paths behave normally.
        original_exists = os.path.exists
        def side_effect_exists(path):
            if "photorec" in path:
                return True
            return original_exists(path)

        with patch("sys.platform", "win32"), \
             patch("os.path.exists", side_effect=side_effect_exists), \
             patch("time.sleep"):
            runner.run_real_scan()

        # Check what arguments were passed to Popen
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        cmd = args[0]
        
        # Verify that the cmd does NOT contain "1"
        assert "1" not in cmd
        assert cmd[-2] == "\\\\.\\E:"
        assert cmd[-1] == "wholespace,search"

    @patch("subprocess.Popen")
    def test_run_real_scan_physical_drive_win32(self, mock_popen):
        # On Windows, a physical drive (e.g. \\.\PhysicalDrive0) SHOULD include the partition index '1'
        mock_process = MagicMock()
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        drive = {
            'device': '\\\\.\\PhysicalDrive0',
            'mountpoint': '',
            'fstype': 'NTFS',
            'label': 'Physical Disk 0'
        }
        
        runner = PhotoRecRunner(drive, self.temp_dir, self.progress_queue)
        
        original_exists = os.path.exists
        def side_effect_exists(path):
            if "photorec" in path:
                return True
            return original_exists(path)

        with patch("sys.platform", "win32"), \
             patch("os.path.exists", side_effect=side_effect_exists), \
             patch("time.sleep"):
            runner.run_real_scan()

        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        cmd = args[0]
        
        # Verify that the cmd DOES contain "1"
        assert "1" in cmd
        assert cmd[-3] == "\\\\.\\PhysicalDrive0"
        assert cmd[-2] == "1"
        assert cmd[-1] == "wholespace,search"

if __name__ == "__main__":
    unittest.main()
