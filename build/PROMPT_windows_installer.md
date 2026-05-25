# Prompt — DataRescue Windows Installer Setup

## Task
Set up a Windows installation package for the DataRescue application so it can be installed on a Windows machine and tested.

## What was done
1. **Fixed `datarescue_win.spec`** — added correct hidden imports (tkinter, PIL.ImageTk, cryptography.fernet, etc.), switched to folder-based dist (faster startup), excluded server-side deps (fastapi, uvicorn, sqlalchemy).
2. **Created `build_win.bat`** — one-click build script that runs PyInstaller and smoke-tests the output.
3. **Created `datarescue_installer.iss`** — Inno Setup script that wraps the PyInstaller output into a professional `.exe` installer (Program Files, Start Menu, Desktop shortcut, Uninstaller, Windows 10 min version check).
4. **Created `make_icon.py`** — generates a placeholder `assets/icon.ico`; replace with real brand icon before release.
5. **Generated `assets/icon.ico`** — 256×256 RGBA placeholder icon.

## Files created/modified
- `datarescue/build/datarescue_win.spec`   (modified)
- `datarescue/build/build_win.bat`          (new)
- `datarescue/build/datarescue_installer.iss` (new)
- `datarescue/build/make_icon.py`           (new)
- `datarescue/assets/icon.ico`              (new)

## How to build step-by-step (on Windows)

### Prerequisites
- Python 3.11 (https://python.org/downloads) — install with "Add to PATH" ticked
- Git (optional, just to get the repo)

### Step 1 — Install dependencies
```cmd
cd "F:\Recovery tool\datarescue"
pip install -r requirements.txt
```

### Step 2 — Build the EXE bundle
```cmd
cd build
build_win.bat
```
Output: `datarescue\build\dist\DataRescue\DataRescue.exe`

You can run `DataRescue.exe` directly from that folder to test it — no install needed.

### Step 3 — Create the installer (optional but recommended for distribution)
1. Download and install **Inno Setup 6** from https://jrsoftware.org/isdl.php (free)
2. Open `datarescue/build/datarescue_installer.iss` in the Inno Setup Compiler
3. Click **Build → Compile** (or press F9)
4. Output: `datarescue/build/installer/DataRescue_Setup_1.0.0.exe`

### Step 4 — Test the installer
Run `DataRescue_Setup_1.0.0.exe` → installs to `C:\Program Files\DataRescue\` → creates Start Menu entry + optional Desktop shortcut.

## Notes
- The app runs in **offline/mock mode** by default (no credits server needed for MVP testing).
- For production with a real backend, set the env var before launching: `DATARESCUE_API_URL=https://your-api.domain.com`
- Replace `assets/icon.ico` with your real brand icon before final release (run `python build/make_icon.py` to regenerate the placeholder).
- If tests fail locally due to `__pycache__` issues, delete all `__pycache__` folders and rerun: `find . -name __pycache__ -type d -exec rmdir /s /q {} +` (Windows) or `find . -name __pycache__ -exec rm -rf {} +` (bash).
