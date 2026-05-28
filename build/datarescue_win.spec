# -*- mode: python ; coding: utf-8 -*-
# DataRescue Windows build spec
# Produces a one-folder distribution wrapped by Inno Setup into a .exe installer.
# Run from the repo root:  pyinstaller build\datarescue_win.spec

import os
block_cipher = None

a = Analysis(
    ['../main.py'],
    pathex=['..'],          # repo root on sys.path so bare imports resolve
    binaries=[],
    datas=[
        ('../binaries/win/photorec.exe', 'binaries/win'),
        ('../binaries/win/testdisk.exe', 'binaries/win'),
        ('../binaries/win/*.dll',        'binaries/win'),
        ('../binaries/win/63/cygwin',    'binaries/win/63'),
        ('../assets/',                   'assets'),
        ('../THIRD_PARTY_NOTICES.txt',   '.'),
    ],
    hiddenimports=[
        # GUI / imaging
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
        'PIL.Image',
        'PIL.ImageTk',
        # Tkinter (customtkinter depends on these)
        'tkinter',
        'tkinter.ttk',
        'tkinter.font',
        'tkinter.messagebox',
        'tkinter.filedialog',
        # System / crypto / network
        'psutil',
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'requests',
        'urllib3',
        'charset_normalizer',
        # Packaging metadata often needed at runtime
        'pkg_resources.py2_warn',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy test / server deps that are not needed in the GUI exe
        'pytest', 'fastapi', 'uvicorn', 'sqlalchemy', 'aiosqlite',
        'asyncpg', 'stripe', 'httpx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,      # folder-based dist (faster startup, easier debugging)
    name='DataRescue',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[
        # Don't compress the PhotoRec/TestDisk binaries — they have their own compression
        'photorec.exe',
        'testdisk.exe',
    ],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../assets/icon.ico' if os.environ.get('GITHUB_ACTIONS') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['photorec.exe', 'testdisk.exe'],
    name='DataRescue',
)
