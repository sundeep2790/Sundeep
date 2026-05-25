import os
import fnmatch

def build_file_tree(dest_path: str) -> dict:
    tree = {
        "photos": [],
        "videos": [],
        "documents": [],
        "other": []
    }
    
    if not os.path.exists(dest_path):
        return tree
        
    PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".cr2", ".nef", ".arw", ".heic", ".webp"}
    VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp"}
    DOC_EXTS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf", ".odt", ".ods", ".odp", ".csv"}
    
    try:
        entries = os.listdir(dest_path)
    except Exception:
        return tree

    for entry in entries:
        entry_path = os.path.join(dest_path, entry)
        if os.path.isdir(entry_path) and fnmatch.fnmatch(entry, "recup_dir.*"):
            for root, _, files in os.walk(entry_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    abs_path = os.path.abspath(file_path)
                    
                    ext = os.path.splitext(file)[1].lower()
                    if ext in PHOTO_EXTS:
                        tree["photos"].append(abs_path)
                    elif ext in VIDEO_EXTS:
                        tree["videos"].append(abs_path)
                    elif ext in DOC_EXTS:
                        tree["documents"].append(abs_path)
                    else:
                        tree["other"].append(abs_path)
                        
    # Sort files in each category for consistency
    for cat in tree:
        tree[cat].sort()
        
    return tree
