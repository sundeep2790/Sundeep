import os
import sys
import shutil
import subprocess

def log(msg):
    print(f"\n=== {msg} ===")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    spec_file = os.path.join(script_dir, "datarescue_mac.spec")
    dist_dir = os.path.join(script_dir, "dist")
    work_dir = os.path.join(script_dir, "work")

    # Force working directory to script directory so relative spec file paths resolve correctly
    os.chdir(script_dir)

    log("DataRescue for macOS - Build Pipeline")
    print(f"Repo root : {repo_root}")
    print(f"Spec file : {spec_file}")
    
    # 1. Cross-platform validation check
    if sys.platform != "darwin":
        log("CROSS-COMPILATION WARNING")
        print("ERROR: PyInstaller only supports compiling macOS applications on a native macOS machine.")
        print(f"Your current platform is: {sys.platform}")
        print("\nTo generate the macOS DMG installer package, follow these instructions:")
        print("  1. Copy this repository to a macOS machine.")
        print("  2. Open Terminal, change directories to the repository root.")
        print("  3. Install dependencies: pip install -r requirements.txt")
        print("  4. Download macOS binaries: python download_binaries.py")
        print("  5. Run this build script: python build/build_mac.py")
        print("\nWe have saved the full packaging automation pipeline script for you below.")
        print("Once executed on macOS, it will generate a standalone 'DataRescue_Setup_1.0.0.dmg' disk image.")
        sys.exit(1)

    # 2. Clean previous build artifacts
    log("[1/4] Cleaning previous build artifacts...")
    for folder in [dist_dir, work_dir]:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"Removed {folder}")
            except Exception as e:
                print(f"Warning: Could not remove {folder}: {e}")
    
    dmg_output_dir = os.path.join(script_dir, "installer")
    os.makedirs(dmg_output_dir, exist_ok=True)
    dmg_path = os.path.join(dmg_output_dir, "DataRescue_Setup_1.0.0.dmg")
    if os.path.exists(dmg_path):
        try:
            os.remove(dmg_path)
            print(f"Removed existing DMG: {dmg_path}")
        except Exception as e:
            print(f"Warning: Could not remove existing DMG: {e}")
            
    print("Clean complete.")

    # 3. Run PyInstaller
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

    # 4. Verify PyInstaller output
    log("[3/4] Verifying PyInstaller output...")
    app_path = os.path.join(dist_dir, "DataRescue.app")
    if not os.path.exists(app_path):
        print(f"ERROR: DataRescue.app bundle not found at {app_path}")
        sys.exit(1)
    print(f"DataRescue.app verified at {app_path}")

    # Check for photorec
    photorec_path = os.path.join(app_path, "Contents", "Resources", "binaries", "mac", "photorec")
    if not os.path.exists(photorec_path):
        print(f"WARNING: Native macOS photorec binary not found at: {photorec_path}")
    else:
        print("Native macOS photorec binary verified inside app bundle resources.")

    # 5. Build DMG Package using hdiutil
    log("[4/4] Creating macOS DMG Installer Image...")
    
    # Create temp directory for DMG layout
    temp_dmg_layout = os.path.join(script_dir, "dmg_temp_layout")
    if os.path.exists(temp_dmg_layout):
        shutil.rmtree(temp_dmg_layout)
    os.makedirs(temp_dmg_layout, exist_ok=True)
    
    try:
        # Copy the .app bundle to the layout folder
        print(f"Copying app bundle to temporary layout: {temp_dmg_layout}")
        shutil.copytree(app_path, os.path.join(temp_dmg_layout, "DataRescue.app"), symlinks=True)
        
        # Create a symbolic link to /Applications
        print("Creating symbolic link to /Applications...")
        os.symlink("/Applications", os.path.join(temp_dmg_layout, "Applications"))
        
        # Run hdiutil to compile the DMG
        hdiutil_cmd = [
            "hdiutil", "create",
            "-volname", "DataRescue",
            "-srcfolder", temp_dmg_layout,
            "-ov",
            "-format", "UDZO",
            dmg_path
        ]
        print(f"Running command: {' '.join(hdiutil_cmd)}")
        hdiutil_result = subprocess.run(hdiutil_cmd, check=False)
        
        if hdiutil_result.returncode != 0:
            print(f"ERROR: hdiutil failed with exit code {hdiutil_result.returncode}")
            sys.exit(1)
            
        print(f"\nSUCCESS! macOS DMG installer generated successfully at:\n{dmg_path}")
        
    finally:
        # Clean up temp layout directory
        if os.path.exists(temp_dmg_layout):
            shutil.rmtree(temp_dmg_layout)

if __name__ == "__main__":
    main()
