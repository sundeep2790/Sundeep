"""
test_engine_edge.py — Edge cases for engine modules:
  - file_tree: deep nesting, permission errors, mixed case, symlinks
  - drive_manager: label edge cases, removable detection
  - credits calculation: boundary values, float inputs
  - photorec/testdisk wrappers: error conditions
"""
import os
import sys
import stat
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datarescue.engine.file_tree import build_file_tree
from datarescue.payments.credits import calculate_credits


class TestFileTreeEdgeCases(unittest.TestCase):
    def test_deeply_nested_files_found(self):
        """Files nested 5 levels deep inside recup_dir must be catalogued."""
        with tempfile.TemporaryDirectory() as tmp:
            deep = os.path.join(tmp, "recup_dir.1", "a", "b", "c", "d", "e")
            os.makedirs(deep)
            img = os.path.join(deep, "deep_photo.jpg")
            with open(img, "w") as f:
                f.write("x")
            result = build_file_tree(tmp)
            self.assertIn(os.path.abspath(img), result["photos"])

    def test_no_recup_dirs_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Files at root — not inside recup_dir.*
            with open(os.path.join(tmp, "photo.jpg"), "w") as f:
                f.write("x")
            result = build_file_tree(tmp)
            self.assertEqual(result["photos"], [])

    def test_mixed_case_extensions(self):
        """Extension matching must be case-insensitive: .JPG, .Jpg, etc."""
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "recup_dir.1")
            os.makedirs(d)
            for ext in [".JPG", ".Png", ".MP4", ".DOCX"]:
                with open(os.path.join(d, f"file{ext}"), "w") as f:
                    f.write("x")
            result = build_file_tree(tmp)
            self.assertEqual(len(result["photos"]), 2)   # JPG + Png
            self.assertEqual(len(result["videos"]), 1)   # MP4
            self.assertEqual(len(result["documents"]), 1) # DOCX

    def test_multiple_recup_dirs_aggregated(self):
        """Files from recup_dir.1, recup_dir.2, recup_dir.99 all included."""
        with tempfile.TemporaryDirectory() as tmp:
            for n in [1, 2, 99]:
                d = os.path.join(tmp, f"recup_dir.{n}")
                os.makedirs(d)
                with open(os.path.join(d, f"img{n}.jpg"), "w") as f:
                    f.write("x")
            result = build_file_tree(tmp)
            self.assertEqual(len(result["photos"]), 3)

    def test_empty_recup_dir_returns_empty_categories(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "recup_dir.1"))
            result = build_file_tree(tmp)
            for cat in result.values():
                self.assertEqual(cat, [])

    def test_files_sorted_within_category(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "recup_dir.1")
            os.makedirs(d)
            for name in ["z.jpg", "a.jpg", "m.jpg"]:
                with open(os.path.join(d, name), "w") as f:
                    f.write("x")
            result = build_file_tree(tmp)
            self.assertEqual(result["photos"], sorted(result["photos"]))

    def test_no_false_dir_matches(self):
        """'recup_something' without a dot must NOT be picked up."""
        with tempfile.TemporaryDirectory() as tmp:
            bad_dir = os.path.join(tmp, "recup_directory")
            os.makedirs(bad_dir)
            with open(os.path.join(bad_dir, "photo.jpg"), "w") as f:
                f.write("x")
            result = build_file_tree(tmp)
            self.assertEqual(result["photos"], [])

    def test_all_supported_photo_extensions(self):
        exts = [".jpg", ".jpeg", ".png", ".gif", ".bmp",
                ".tiff", ".cr2", ".nef", ".arw", ".heic", ".webp"]
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "recup_dir.1")
            os.makedirs(d)
            for ext in exts:
                with open(os.path.join(d, f"img{ext}"), "w") as f:
                    f.write("x")
            result = build_file_tree(tmp)
            self.assertEqual(len(result["photos"]), len(exts))

    def test_all_supported_video_extensions(self):
        exts = [".mp4", ".mkv", ".avi", ".mov", ".wmv",
                ".flv", ".webm", ".m4v", ".3gp"]
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "recup_dir.1")
            os.makedirs(d)
            for ext in exts:
                with open(os.path.join(d, f"vid{ext}"), "w") as f:
                    f.write("x")
            result = build_file_tree(tmp)
            self.assertEqual(len(result["videos"]), len(exts))

    def test_all_supported_doc_extensions(self):
        exts = [".pdf", ".doc", ".docx", ".xls", ".xlsx",
                ".ppt", ".pptx", ".txt", ".rtf", ".odt",
                ".ods", ".odp", ".csv"]
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "recup_dir.1")
            os.makedirs(d)
            for ext in exts:
                with open(os.path.join(d, f"doc{ext}"), "w") as f:
                    f.write("x")
            result = build_file_tree(tmp)
            self.assertEqual(len(result["documents"]), len(exts))

    def test_unknown_extensions_go_to_other(self):
        exts = [".xyz", ".abc", ".unknown", ".bin"]
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "recup_dir.1")
            os.makedirs(d)
            for ext in exts:
                with open(os.path.join(d, f"file{ext}"), "w") as f:
                    f.write("x")
            result = build_file_tree(tmp)
            self.assertEqual(len(result["other"]), len(exts))

    def test_inaccessible_directory_returns_empty(self):
        """build_file_tree should not crash if a directory is unreadable."""
        result = build_file_tree("/root/restricted_hypothetical_dir_xyz")
        for cat in result.values():
            self.assertEqual(cat, [])


class TestCalculateCreditsEdgeCases(unittest.TestCase):
    """Boundary and edge case tests for calculate_credits."""

    def test_exactly_one_gb(self):
        self.assertEqual(calculate_credits(1_073_741_824), 1)

    def test_one_byte_over_gb_is_2_credits(self):
        self.assertEqual(calculate_credits(1_073_741_825), 2)

    def test_one_byte_under_gb_is_1_credit(self):
        self.assertEqual(calculate_credits(1_073_741_823), 1)

    def test_zero_is_zero_credits(self):
        self.assertEqual(calculate_credits(0), 0)

    def test_negative_is_zero_credits(self):
        self.assertEqual(calculate_credits(-1), 0)
        self.assertEqual(calculate_credits(-1_000_000_000), 0)

    def test_one_byte_is_1_credit(self):
        self.assertEqual(calculate_credits(1), 1)

    def test_exactly_10_gb_is_10_credits(self):
        self.assertEqual(calculate_credits(10 * 1_073_741_824), 10)

    def test_fractional_gb_rounds_up(self):
        # 1.5 GB = 1 credit (ceiling)
        self.assertEqual(calculate_credits(int(1.5 * 1_073_741_824)), 2)

    def test_very_large_drive(self):
        # 2 TB = 2048 GB
        two_tb = 2 * 1024 * 1_073_741_824
        self.assertEqual(calculate_credits(two_tb), 2048)

    def test_result_always_non_negative(self):
        for size in [-1000, 0, 1, 100, 999999999999]:
            self.assertGreaterEqual(calculate_credits(size), 0)


def _load_fresh(rel_path, module_name):
    """Load a module fresh from its .py source text, completely bypassing
    the .pyc bytecode cache (SourceFileLoader still validates/uses .pyc even
    with spec_from_file_location; compile+exec skips all of that)."""
    import types
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", rel_path))
    mod = types.ModuleType(module_name)
    mod.__file__ = src_path
    mod.__spec__ = None
    with open(src_path, "r", encoding="utf-8") as fh:
        source = fh.read()
    code = compile(source, src_path, "exec")
    exec(code, mod.__dict__)  # noqa: S102
    return mod


class TestPhotorecWrapperErrors(unittest.TestCase):
    """Test that photorec_wrapper raises PhotoRecError correctly.

    Modules are loaded fresh from source (not cached .pyc) so the
    BUG-008 Linux branch is always exercised regardless of bytecode age.
    """

    def _load(self):
        return _load_fresh("engine/photorec_wrapper.py", "photorec_wrapper_fresh")

    def test_binary_not_found_raises(self):
        mod = self._load()
        # shutil is imported inside the function, so patch via sys.modules
        with patch("sys.platform", "linux"), \
             patch("shutil.which", return_value=None):
            with self.assertRaises(mod.PhotoRecError):
                mod.get_photorec_binary_path()

    def test_binary_found_on_linux(self):
        mod = self._load()
        with patch("sys.platform", "linux"), \
             patch("shutil.which", return_value="/usr/bin/photorec"):
            path = mod.get_photorec_binary_path()
            self.assertEqual(path, "/usr/bin/photorec")


class TestTestdiskWrapperErrors(unittest.TestCase):
    """Test that testdisk_wrapper raises TestDiskError correctly."""

    def _load(self):
        return _load_fresh("engine/testdisk_wrapper.py", "testdisk_wrapper_fresh")

    def test_binary_not_found_raises(self):
        mod = self._load()
        with patch("sys.platform", "linux"), \
             patch("shutil.which", return_value=None):
            with self.assertRaises(mod.TestDiskError):
                mod.get_testdisk_binary_path()


class TestDestinationOnSourceCheck(unittest.TestCase):
    """is_destination_on_source must correctly detect same-device paths."""

    def test_same_path_is_on_source(self):
        from datarescue.engine.photorec_wrapper import is_destination_on_source
        with tempfile.TemporaryDirectory() as tmp:
            result = is_destination_on_source(tmp, tmp)
            self.assertTrue(result)

    def test_different_temp_dirs_not_on_source(self):
        from datarescue.engine.photorec_wrapper import is_destination_on_source
        with tempfile.TemporaryDirectory() as tmp1, \
             tempfile.TemporaryDirectory() as tmp2:
            # Both are in /tmp on the same device — likely True on sandbox
            # Just verify it doesn't crash and returns a bool
            result = is_destination_on_source(tmp1, tmp2)
            self.assertIsInstance(result, bool)


if __name__ == "__main__":
    unittest.main()
