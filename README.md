# DataRescue v1.0 - Professional File Recovery Tool

DataRescue is a high-performance, secure local file and partition recovery application built on top of the industry-standard `PhotoRec` and `TestDisk` engines. It features a modern, user-friendly graphical interface powered by CustomTkinter, local config encryption, and credit-based license management.

---

## Directory Structure

The project has been scaffolded with the following architecture:

```text
datarescue/
├── assets/                  # Graphical and static assets (icons, images)
├── api/                     # Backend API client handlers (licensing, credits)
├── backend/                 # Local FastAPI server endpoints
│   └── routes/              # Modular backend routes
│   └── requirements.txt     # Pinned backend dependencies
├── binaries/                # Platform-specific engine binaries
│   ├── win/                 # PhotoRec & TestDisk for Windows (64-bit)
│   └── mac/                 # PhotoRec & TestDisk for macOS (Intel/Universal)
├── build/                   # Compilation and bundling outputs
├── engine/                  # PhotoRec & TestDisk process runners and parsers
├── gui/                     # CustomTkinter interface
│   └── components/          # Reusable GUI widgets and layouts
├── payments/                # Stripe integration and processing logic
├── tests/                   # Pytest suite
├── config.py                # AES-256 encrypted local configuration manager
├── download_binaries.py     # Binary download and extraction helper script
├── main.py                  # Entry point for the application
└── requirements.txt         # Pinned frontend and library dependencies
```

---

## Installation & Setup

### Prerequisites
- Python 3.10 or 3.11 (Python 3.11 is recommended).
- Full Disk Access (on macOS) or Administrator privileges (on Windows) to scan physical drive partitions.

### 1. Install Dependencies

You can install all dependencies for both frontend GUI and backend services:

```bash
# Install frontend GUI dependencies
pip install -r requirements.txt

# Install backend dependencies
pip install -r backend/requirements.txt
```

### 2. Download Engine Binaries

DataRescue leverages pre-built binaries of PhotoRec and TestDisk. Run the automated script to download and extract them:

```bash
python download_binaries.py
```

This script retrieves:
- **Windows**: TestDisk/PhotoRec 7.2 (64-bit) and extracts the executables and DLL dependencies to `datarescue/binaries/win/`.
- **macOS**: TestDisk/PhotoRec 7.2 (Intel) and extracts binaries to `datarescue/binaries/mac/`.

---

## Configuration & Security

The local configurations (`config.enc`) are encrypted using **AES-256 (Fernet)** to prevent tampering.
- **Location**:
  - **Windows**: `%APPDATA%/DataRescue/config.enc`
  - **macOS**: `~/Library/Application Support/DataRescue/config.enc`
- **Key Derivation**: Keys are derived from a unique `device_token` (generated on first boot) using **PBKDF2HMAC** with SHA-256 and 100,000 iterations.
- **Offline Grace Period**: If the license API is unreachable, cached credits remain valid for up to **72 hours** before falling back to restricted mode.

---

## Running the Application

To run the application in development mode:

```bash
python main.py
```

---

## Building Executables

To bundle the application into a standalone executable using `PyInstaller`:

```bash
pyinstaller --clean --noconfirm --onedir --windowed --name="DataRescue" main.py
```

Make sure to bundle the assets and engine binaries from `binaries/` into your PyInstaller configuration/spec file.
