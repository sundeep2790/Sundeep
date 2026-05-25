import os
import sys
import shutil
import subprocess

def log(msg):
    print(f"\n=== {msg} ===")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    spec_file = os.path.join(script_dir, "datarescue_win.spec")
    dist_dir = os.path.join(script_dir, "dist")
    work_dir = os.path.join(script_dir, "work")

    # Force working directory to script directory so relative spec file paths resolve correctly
    os.chdir(script_dir)

    log("DataRescue for Windows - Python Build Pipeline")
    print(f"Repo root : {repo_root}")
    print(f"Spec file : {spec_file}")
    print(f"Output    : {dist_dir}\\DataRescue\\")

    # 1. Clean previous build artifacts
    log("[1/4] Cleaning previous build artifacts...")
    for folder in [dist_dir, work_dir]:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"Removed {folder}")
            except Exception as e:
                print(f"Warning: Could not remove {folder}: {e}")
    print("Clean complete.")

    # 2. Run PyInstaller
    log("[2/4] Running PyInstaller...")
    cmd = [
        sys.executable, "-m", "PyInstaller", spec_file,
        "--distpath", dist_dir,
        "--workpath", work_dir,
        "--clean",
        "--noconfirm"
    ]
    print(f"Running command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"ERROR: PyInstaller failed with exit code {result.returncode}")
        sys.exit(1)
    print("PyInstaller completed successfully.")

    # 3. Verify PyInstaller output
    log("[3/4] Verifying PyInstaller output...")
    exe_path = os.path.join(dist_dir, "DataRescue", "DataRescue.exe")
    if not os.path.exists(exe_path):
        print(f"ERROR: DataRescue.exe not found at {exe_path}")
        sys.exit(1)
    print(f"DataRescue.exe verified at {exe_path}")

    # Check for photorec.exe
    photorec_paths = [
        os.path.join(dist_dir, "DataRescue", "_internal", "binaries", "win", "photorec.exe"),
        os.path.join(dist_dir, "DataRescue", "binaries", "win", "photorec.exe")
    ]
    if not any(os.path.exists(p) for p in photorec_paths):
        print("WARNING: photorec.exe not found in packaged output folder structure!")
    else:
        print("photorec.exe verified in packaged output.")

    # 4. Find Inno Setup Compiler (ISCC.exe) and compile
    log("[4/4] Checking for Inno Setup compiler (ISCC.exe)...")
    
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    user_profile = os.environ.get("USERPROFILE", "")
    
    iscc_search_paths = [
        "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe",
        "C:\\Program Files\\Inno Setup 6\\ISCC.exe",
        os.path.join(local_app_data, "Programs", "Inno Setup 6", "ISCC.exe"),
        os.path.join(user_profile, "AppData", "Local", "Programs", "Inno Setup 6", "ISCC.exe"),
    ]

    iscc_path = None
    for path in iscc_search_paths:
        if path and os.path.exists(path):
            iscc_path = path
            break

    if not iscc_path:
        iscc_path = shutil.which("ISCC.exe")

    if not iscc_path:
        print("WARNING: Inno Setup compiler (ISCC.exe) not found.")
        print("To package the installer, please run Inno Setup manually on:")
        print(f"  {os.path.join(script_dir, 'datarescue_installer.iss')}")
        sys.exit(0)

    print(f"Found Inno Setup at: {iscc_path}")
    print("Compiling installer setup wizard...")

    iss_file = os.path.join(script_dir, "datarescue_installer.iss")
    iscc_cmd = [iscc_path, iss_file]
    print(f"Running command: {' '.join(iscc_cmd)}")

    iscc_result = subprocess.run(iscc_cmd, check=False)
    if iscc_result.returncode != 0:
        print(f"ERROR: Inno Setup compiler failed with exit code {iscc_result.returncode}")
        sys.exit(1)

    installer_output = os.path.join(script_dir, "installer", "DataRescue_Setup_1.0.0.exe")
    if os.path.exists(installer_output):
        print(f"\nSUCCESS! Installer generated successfully at:\n{installer_output}")
    else:
        print("\nWARNING: Compilation finished but installer output was not found at standard path.")

if __name__ == "__main__":
    main()
