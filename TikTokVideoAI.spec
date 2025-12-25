# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.win32.versioninfo import VSVersionInfo
from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
    copy_metadata,
)
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# ================== PATH ==================
USER = os.getlogin()
PLAYWRIGHT_PATH = rf"C:\Users\{USER}\AppData\Local\ms-playwright"

# ================== DATAS ==================
datas = []

# Font
datas += [('font.ttf', '.')]

# input
datas += [('input', 'input')]

datas += collect_data_files(
    'playwright_stealth',
    include_py_files=False
)

# ===== NUMPY (BẮT BUỘC) =====
datas += collect_data_files('numpy')
datas += copy_metadata('numpy')

# ===== IMAGEIO + MOVIEPY =====
datas += collect_data_files('imageio')
datas += collect_data_files('moviepy')
datas += copy_metadata('imageio')
datas += copy_metadata('moviepy')

# ================== HIDDEN IMPORTS ==================
hiddenimports = []

# MoviePy + ImageIO (import động)
hiddenimports += collect_submodules('moviepy')
hiddenimports += collect_submodules('imageio')

# Playwright + stealth + Gemini
hiddenimports += [
    'playwright.sync_api',
    'playwright_stealth',
    'google.genai',
]

# ================== ANALYSIS ==================
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'pytest',
        'unittest',
        'tkinter.test',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    optimize=0,
    noarchive=False,
)

# ================== PYZ ==================
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ================== EXE ==================
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,     # ⭐ ONEFILE
    name='TikTokVideoAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                  # ⭐ giảm size
    upx_exclude=[
        'vcruntime140.dll',
        'python3.dll',
        'numpy*.pyd',
    ],
    console=False,             # ⭐ WINDOWED (ẩn console)
    icon='icon.ico',
    version='version_info.txt',
)

# ================== COLLECT ==================
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'vcruntime140.dll',
        'python3.dll',
    ],
    name='TikTokVideoAI',
)
