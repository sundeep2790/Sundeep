import os
import tempfile
import pytest
from datetime import datetime
from datarescue.engine.log_parser import parse_photorec_log

def test_parse_empty_log():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as tmp:
        tmp_path = tmp.name
    try:
        # File exists but is empty
        result = parse_photorec_log(tmp_path)
        assert result["files_found"] == 0
        assert result["current_pass"] == 0
        assert result["percent_complete"] == 0.0
        assert isinstance(result["last_updated"], str)
        assert len(result["last_updated"]) > 0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_parse_partial_progress():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log", encoding="utf-8") as tmp:
        tmp.write("Pass 1 - Reading sector 250/1000, 5 files found\n")
        tmp_path = tmp.name
    try:
        result = parse_photorec_log(tmp_path)
        assert result["files_found"] == 5
        assert result["current_pass"] == 1
        assert result["percent_complete"] == 25.0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_parse_pass_1_and_2_complete():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log", encoding="utf-8") as tmp:
        tmp.write("Pass 1 - Reading sector 1000/1000, 10 files found\n")
        tmp.write("Pass 2 - Reading sector 150/500, 12 files found\n")
        # And let's add some actual recovered files format
        tmp.write("123456  jpg  /some/path/recup_dir.1/f123456.jpg\n")
        tmp.write("789012  png  /some/path/recup_dir.1/f789012.png\n")
        tmp_path = tmp.name
    try:
        result = parse_photorec_log(tmp_path)
        # We have 12 files from the progress line, and 2 explicitly listed in the file.
        # Max of 12 and 2 is 12.
        assert result["files_found"] == 12
        assert result["current_pass"] == 2
        # Last percentage parsed from "Reading sector 150/500" -> 150/500 = 30%
        assert result["percent_complete"] == 30.0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_parse_error_states():
    # File does not exist
    result = parse_photorec_log("non_existent_file_path_12345.log")
    assert result["files_found"] == 0
    assert result["current_pass"] == 0
    assert result["percent_complete"] == 0.0
    assert isinstance(result["last_updated"], str)
    assert len(result["last_updated"]) > 0
