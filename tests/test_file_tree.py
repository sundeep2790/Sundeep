import os
import tempfile
import shutil
import pytest
from datarescue.engine.file_tree import build_file_tree

def test_build_file_tree_empty_or_nonexistent():
    # Non-existent path
    res = build_file_tree("non_existent_directory_path_12345")
    assert res == {"photos": [], "videos": [], "documents": [], "other": []}

    # Empty path
    with tempfile.TemporaryDirectory() as tmpdir:
        res = build_file_tree(tmpdir)
        assert res == {"photos": [], "videos": [], "documents": [], "other": []}

def test_build_file_tree_with_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create recup_dir.1
        dir1 = os.path.join(tmpdir, "recup_dir.1")
        os.makedirs(dir1)
        
        # Create files in dir1
        img1 = os.path.join(dir1, "image.jpg")
        doc1 = os.path.join(dir1, "document.docx")
        vid1 = os.path.join(dir1, "video.mp4")
        oth1 = os.path.join(dir1, "script.py")
        
        for fpath in [img1, doc1, vid1, oth1]:
            with open(fpath, "w") as f:
                f.write("dummy")
                
        # Create recup_dir.2 with nested subfolder
        dir2 = os.path.join(tmpdir, "recup_dir.2")
        dir2_nested = os.path.join(dir2, "nested")
        os.makedirs(dir2_nested)
        
        img2 = os.path.join(dir2_nested, "photo.PNG")  # upper case extension
        doc2 = os.path.join(dir2, "notes.txt")
        
        for fpath in [img2, doc2]:
            with open(fpath, "w") as f:
                f.write("dummy")
                
        # Create a non-matching directory
        other_dir = os.path.join(tmpdir, "normal_dir")
        os.makedirs(other_dir)
        ignored_file = os.path.join(other_dir, "should_be_ignored.jpg")
        with open(ignored_file, "w") as f:
            f.write("dummy")

        # Run build_file_tree
        res = build_file_tree(tmpdir)
        
        # Verify photos
        expected_photos = sorted([os.path.abspath(img1), os.path.abspath(img2)])
        assert res["photos"] == expected_photos
        
        # Verify videos
        expected_videos = [os.path.abspath(vid1)]
        assert res["videos"] == expected_videos
        
        # Verify documents
        expected_docs = sorted([os.path.abspath(doc1), os.path.abspath(doc2)])
        assert res["documents"] == expected_docs
        
        # Verify other
        expected_other = [os.path.abspath(oth1)]
        assert res["other"] == expected_other
        
        # Verify ignored file is not anywhere in the result
        all_found_files = res["photos"] + res["videos"] + res["documents"] + res["other"]
        assert os.path.abspath(ignored_file) not in all_found_files
