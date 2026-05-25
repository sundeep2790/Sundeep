"""
test_log_parser_advanced.py — Advanced edge cases for engine/log_parser.py.
Covers: multi-pass logs, percentage parsing, malformed lines, unicode paths,
very large file counts, concurrent sector progress, and boundary values.
"""
import os
import tempfile
import unittest
from datarescue.engine.log_parser import parse_photorec_log


def _write_log(content: str) -> str:
    """Write content to a temp log file and return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", delete=False,
                                   suffix=".log", encoding="utf-8")
    f.write(content)
    f.close()
    return f.name


def _cleanup(path):
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


class TestMultiPassParsing(unittest.TestCase):
    def test_pass_numbers_increment_correctly(self):
        path = _write_log(
            "Pass 1 - Reading sector 500/1000, 20 files found\n"
            "Pass 2 - Reading sector 200/1000, 35 files found\n"
        )
        try:
            r = parse_photorec_log(path)
            self.assertEqual(r["current_pass"], 2)
            self.assertEqual(r["files_found"], 35)
            self.assertAlmostEqual(r["percent_complete"], 20.0)
        finally:
            _cleanup(path)

    def test_pass_3_detected(self):
        path = _write_log(
            "Pass 1 - Reading sector 1000/1000, 10 files found\n"
            "Pass 2 - Reading sector 1000/1000, 20 files found\n"
            "Pass 3 - Reading sector 50/1000, 22 files found\n"
        )
        try:
            r = parse_photorec_log(path)
            self.assertEqual(r["current_pass"], 3)
            self.assertAlmostEqual(r["percent_complete"], 5.0)
        finally:
            _cleanup(path)

    def test_last_pass_percent_wins(self):
        """Percentage from the last pass should be the final value."""
        path = _write_log(
            "Pass 1 - Reading sector 1000/1000, 5 files found\n"
            "Pass 2 - Reading sector 750/1000, 8 files found\n"
        )
        try:
            r = parse_photorec_log(path)
            self.assertAlmostEqual(r["percent_complete"], 75.0)
        finally:
            _cleanup(path)


class TestPercentageParsing(unittest.TestCase):
    def test_explicit_percentage_in_log(self):
        path = _write_log("Recovering files... 67.5%\n")
        try:
            r = parse_photorec_log(path)
            self.assertAlmostEqual(r["percent_complete"], 67.5)
        finally:
            _cleanup(path)

    def test_percent_capped_at_100(self):
        path = _write_log("Recovering... 120%\n")
        try:
            r = parse_photorec_log(path)
            self.assertLessEqual(r["percent_complete"], 100.0)
        finally:
            _cleanup(path)

    def test_percent_cannot_be_negative(self):
        path = _write_log("some junk -20% data\n")
        try:
            r = parse_photorec_log(path)
            self.assertGreaterEqual(r["percent_complete"], 0.0)
        finally:
            _cleanup(path)

    def test_zero_total_sectors_no_divide_by_zero(self):
        path = _write_log("Pass 1 - Reading sector 0/0, 0 files found\n")
        try:
            r = parse_photorec_log(path)
            # Should not raise ZeroDivisionError
            self.assertGreaterEqual(r["percent_complete"], 0.0)
        finally:
            _cleanup(path)


class TestFileCountParsing(unittest.TestCase):
    def test_large_file_count(self):
        path = _write_log("Pass 1 - Reading sector 500/1000, 99999 files found\n")
        try:
            r = parse_photorec_log(path)
            self.assertEqual(r["files_found"], 99999)
        finally:
            _cleanup(path)

    def test_explicit_file_entries_counted(self):
        """Recovery entry lines (offset ext path) should be counted."""
        path = _write_log(
            "12345  jpg  /dest/recup_dir.1/f12345.jpg\n"
            "67890  png  /dest/recup_dir.1/f67890.png\n"
            "11111  pdf  /dest/recup_dir.1/f11111.pdf\n"
        )
        try:
            r = parse_photorec_log(path)
            self.assertGreaterEqual(r["files_found"], 3)
        finally:
            _cleanup(path)

    def test_progress_line_overrides_when_higher(self):
        """files_found should be max(counted_entries, progress_line_count)."""
        path = _write_log(
            "Pass 1 - Reading sector 500/1000, 50 files found\n"
            "12345  jpg  /recup_dir.1/f1.jpg\n"
            "12346  jpg  /recup_dir.1/f2.jpg\n"
        )
        try:
            r = parse_photorec_log(path)
            # 50 from progress line > 2 counted entries
            self.assertEqual(r["files_found"], 50)
        finally:
            _cleanup(path)


class TestMalformedAndEdgeInput(unittest.TestCase):
    def test_empty_log_returns_zeros(self):
        path = _write_log("")
        try:
            r = parse_photorec_log(path)
            self.assertEqual(r["files_found"], 0)
            self.assertEqual(r["current_pass"], 0)
            self.assertEqual(r["percent_complete"], 0.0)
        finally:
            _cleanup(path)

    def test_log_with_only_comments(self):
        path = _write_log("# This is a comment\n# Another comment\n")
        try:
            r = parse_photorec_log(path)
            self.assertEqual(r["files_found"], 0)
        finally:
            _cleanup(path)

    def test_random_garbage_does_not_crash(self):
        path = _write_log("!!@@##$$%%^^\x00\x01\x02garbage\n" * 50)
        try:
            r = parse_photorec_log(path)
            self.assertIsInstance(r["files_found"], int)
        finally:
            _cleanup(path)

    def test_unicode_paths_do_not_crash(self):
        path = _write_log(
            "12345  jpg  /récupération/日本語/ファイル.jpg\n"
            "Pass 1 - Reading sector 100/500, 1 files found\n"
        )
        try:
            r = parse_photorec_log(path)
            self.assertIsInstance(r, dict)
        finally:
            _cleanup(path)

    def test_very_long_lines_do_not_crash(self):
        long_path = "/dest/" + "a" * 10000 + ".jpg"
        path = _write_log(f"12345  jpg  {long_path}\n")
        try:
            r = parse_photorec_log(path)
            self.assertIsInstance(r, dict)
        finally:
            _cleanup(path)

    def test_nonexistent_file_returns_defaults(self):
        r = parse_photorec_log("/totally/nonexistent/path/logfile.log")
        self.assertEqual(r["files_found"], 0)
        self.assertEqual(r["current_pass"], 0)
        self.assertEqual(r["percent_complete"], 0.0)
        self.assertIsInstance(r["last_updated"], str)
        self.assertGreater(len(r["last_updated"]), 0)


class TestLastUpdatedTimestamp(unittest.TestCase):
    def test_existing_file_has_valid_timestamp(self):
        path = _write_log("Pass 1 - Reading sector 50/100, 5 files found\n")
        try:
            r = parse_photorec_log(path)
            self.assertIsInstance(r["last_updated"], str)
            self.assertGreater(len(r["last_updated"]), 0)
            # Should be parseable as ISO datetime
            from datetime import datetime
            dt = datetime.fromisoformat(r["last_updated"])
            self.assertIsNotNone(dt)
        finally:
            _cleanup(path)

    def test_nonexistent_file_still_has_timestamp(self):
        r = parse_photorec_log("/no/file/here.log")
        self.assertIsInstance(r["last_updated"], str)
        self.assertGreater(len(r["last_updated"]), 0)


class TestSectorMathAccuracy(unittest.TestCase):
    def test_halfway_gives_50_percent(self):
        path = _write_log("Pass 1 - Reading sector 500/1000, 0 files found\n")
        try:
            r = parse_photorec_log(path)
            self.assertAlmostEqual(r["percent_complete"], 50.0, places=1)
        finally:
            _cleanup(path)

    def test_sector_1_of_1_gives_100_percent(self):
        path = _write_log("Pass 1 - Reading sector 1/1, 0 files found\n")
        try:
            r = parse_photorec_log(path)
            self.assertAlmostEqual(r["percent_complete"], 100.0, places=1)
        finally:
            _cleanup(path)

    def test_one_sector_of_million(self):
        path = _write_log("Pass 1 - Reading sector 1/1000000, 0 files found\n")
        try:
            r = parse_photorec_log(path)
            self.assertAlmostEqual(r["percent_complete"], 0.0001, places=4)
        finally:
            _cleanup(path)


if __name__ == "__main__":
    unittest.main()
