import os
import re
from datetime import datetime

def parse_photorec_log(log_path: str) -> dict:
    result = {
        "files_found": 0,
        "current_pass": 0,
        "percent_complete": 0.0,
        "last_updated": ""
    }
    
    # Get last updated timestamp from file modification time
    if os.path.exists(log_path):
        try:
            mtime = os.path.getmtime(log_path)
            result["last_updated"] = datetime.fromtimestamp(mtime).isoformat()
        except Exception:
            result["last_updated"] = datetime.utcnow().isoformat()
    else:
        result["last_updated"] = datetime.utcnow().isoformat()
        return result
        
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        # If we can't read it (e.g., permission error or deleted midway)
        return result

    counted_files = 0
    max_parsed_files = 0
    max_pass = 0
    percent = 0.0
    
    # Patterns
    # 1. Recovery entry: offset (digits) \s+ ext (word) \s+ path
    # E.g. "12345678  jpg  /dest/recup_dir.1/f12345678.jpg"
    rec_pattern = re.compile(r"^\s*(\d+)\s+([a-zA-Z0-9_-]+)\s+(.+)$")
    
    # 2. Pass and sector progress
    # E.g. "Pass 1 - Reading sector 100/1000, 10 files found"
    # E.g. "Pass 2 - Reading sector 500/1000"
    pass_sector_pattern = re.compile(r"Pass\s+(\d+)\s*-\s*Reading\s+sector\s+(\d+)\s*/\s*(\d+)", re.IGNORECASE)
    
    # 3. Simple pass pattern: E.g. "Pass 1"
    pass_simple_pattern = re.compile(r"Pass\s+(\d+)", re.IGNORECASE)
    
    # 4. Files found pattern: E.g. "10 files found"
    files_found_pattern = re.compile(r"(\d+)\s+files?\s+(?:found|recovered)", re.IGNORECASE)
    
    # 5. Percentage pattern: E.g. "50%" or "50.0%"
    percent_pattern = re.compile(r"(\d+(?:\.\d+)?)%")

    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
            
        # Count recovered files
        # Skip lines starting with # (comments/header)
        if not line_str.startswith("#"):
            match_rec = rec_pattern.match(line_str)
            if match_rec:
                counted_files += 1
                
        # Parse pass and sector progress
        match_ps = pass_sector_pattern.search(line_str)
        if match_ps:
            p_num = int(match_ps.group(1))
            current_sec = int(match_ps.group(2))
            total_sec = int(match_ps.group(3))
            if p_num > max_pass:
                max_pass = p_num
            if total_sec > 0:
                percent = (current_sec / total_sec) * 100.0
                
        # Parse simple pass
        match_p = pass_simple_pattern.search(line_str)
        if match_p:
            p_num = int(match_p.group(1))
            if p_num > max_pass:
                max_pass = p_num
                
        # Parse files found from progress lines
        match_files = files_found_pattern.search(line_str)
        if match_files:
            f_num = int(match_files.group(1))
            if f_num > max_parsed_files:
                max_parsed_files = f_num
                
        # Parse percent directly if present
        match_pct = percent_pattern.search(line_str)
        if match_pct:
            percent = float(match_pct.group(1))
            
    # Set final results
    result["files_found"] = max(counted_files, max_parsed_files)
    result["current_pass"] = max_pass
    result["percent_complete"] = min(max(percent, 0.0), 100.0)
    
    return result
