import os
import shutil
import urllib.request
import zipfile
import tarfile
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

WIN_URLS = [
    "https://www.cgsecurity.org/testdisk-7.2.win64.zip",
    "https://www.cgsecurity.org/Download_and_donate.php/testdisk-7.2.win64.zip"
]
MAC_URLS = [
    "https://www.cgsecurity.org/testdisk-7.2.mac_intel_x86_64.tar.bz2",
    "https://www.cgsecurity.org/Download_and_donate.php/testdisk-7.2.mac_intel_x86_64.tar.bz2",
    "https://www.cgsecurity.org/testdisk-7.2.mac_intel.tar.bz2"
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WIN_BIN_DIR = os.path.join(BASE_DIR, "binaries", "win")
MAC_BIN_DIR = os.path.join(BASE_DIR, "binaries", "mac")

def ensure_dirs():
    os.makedirs(WIN_BIN_DIR, exist_ok=True)
    os.makedirs(MAC_BIN_DIR, exist_ok=True)
    # Also create the other directories requested in the scaffold to be sure:
    os.makedirs(os.path.join(BASE_DIR, "assets"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "tests"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "build"), exist_ok=True)
    logging.info("Created binary and other required directories.")

def download_file(urls, dest_path):
    if isinstance(urls, str):
        urls = [urls]
    
    last_error = None
    for url in urls:
        logging.info(f"Attempting download from {url} to {dest_path}...")
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            logging.info(f"Download complete: {dest_path}")
            return
        except Exception as e:
            logging.warning(f"Failed to download from {url}: {e}")
            last_error = e
            
    if last_error:
        raise last_error


def extract_win(zip_path):
    logging.info(f"Extracting Windows binaries from {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for member in zip_ref.infolist():
            filename = os.path.basename(member.filename)
            if not filename:
                continue
            
            is_target = False
            target_name = filename
            
            if filename == "photorec_win.exe":
                is_target = True
                target_name = "photorec.exe"
            elif filename == "testdisk_win.exe":
                is_target = True
                target_name = "testdisk.exe"
            elif filename.lower().endswith(".dll"):
                is_target = True
                
            if is_target:
                dest_file_path = os.path.join(WIN_BIN_DIR, target_name)
                logging.info(f"Extracting {member.filename} -> {dest_file_path}")
                with zip_ref.open(member) as source, open(dest_file_path, "wb") as target:
                    shutil.copyfileobj(source, target)
            
            # Also extract the '63/cygwin' terminfo directory structure required by PhotoRec
            if "63/cygwin" in member.filename:
                dest_dir = os.path.join(WIN_BIN_DIR, "63")
                os.makedirs(dest_dir, exist_ok=True)
                dest_file_path = os.path.join(dest_dir, "cygwin")
                logging.info(f"Extracting {member.filename} -> {dest_file_path}")
                with zip_ref.open(member) as source, open(dest_file_path, "wb") as target:
                    shutil.copyfileobj(source, target)
    logging.info("Windows binary extraction complete.")

def extract_mac(tar_path):
    logging.info(f"Extracting macOS binaries from {tar_path}...")
    with tarfile.open(tar_path, "r:bz2") as tar_ref:
        for member in tar_ref.getmembers():
            if not member.isfile():
                continue
            filename = os.path.basename(member.name)
            
            if filename in ["photorec", "testdisk"]:
                dest_file_path = os.path.join(MAC_BIN_DIR, filename)
                logging.info(f"Extracting {member.name} -> {dest_file_path}")
                fileobj = tar_ref.extractfile(member)
                if fileobj:
                    with open(dest_file_path, "wb") as target:
                        shutil.copyfileobj(fileobj, target)
                    try:
                        os.chmod(dest_file_path, 0o755)
                    except Exception as e:
                        logging.warning(f"Could not set execute permissions on {dest_file_path}: {e}")
    logging.info("macOS binary extraction complete.")

def verify():
    win_files = os.listdir(WIN_BIN_DIR)
    logging.info(f"Windows files extracted: {win_files}")
    assert "photorec.exe" in win_files, "Missing photorec.exe"
    assert "testdisk.exe" in win_files, "Missing testdisk.exe"
    
    mac_files = os.listdir(MAC_BIN_DIR)
    logging.info(f"macOS files extracted: {mac_files}")
    assert "photorec" in mac_files, "Missing photorec on mac"
    assert "testdisk" in mac_files, "Missing testdisk on mac"
    
    logging.info("Verification successful. All required binaries exist!")

def main():
    ensure_dirs()
    
    temp_dir = os.path.join(BASE_DIR, "temp_downloads")
    os.makedirs(temp_dir, exist_ok=True)
    
    win_zip = os.path.join(temp_dir, "testdisk_win.zip")
    mac_tar = os.path.join(temp_dir, "testdisk_mac.tar.bz2")
    
    try:
        download_file(WIN_URLS, win_zip)
        extract_win(win_zip)
    except Exception as e:
        logging.error(f"Failed processing Windows binaries: {e}")
        raise
        
    try:
        download_file(MAC_URLS, mac_tar)
        extract_mac(mac_tar)
    except Exception as e:
        logging.error(f"Failed processing macOS binaries: {e}")
        raise
        
    try:
        shutil.rmtree(temp_dir)
        logging.info("Cleaned up temporary downloads.")
    except Exception as e:
        logging.warning(f"Failed to cleanup temp directory: {e}")
        
    verify()

if __name__ == "__main__":
    main()
