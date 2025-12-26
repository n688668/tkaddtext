# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
    copy_metadata,
)

block_cipher = None

# ================== DATAS ==================
# Khởi tạo danh sách data với các file tĩnh
datas = [
    ('font.ttf', '.'),
    ('icon.ico', '.'),
    ('version_info.txt', '.'),
]

# Thu thập data cho CustomTkinter (Quan trọng cho GUI)
datas += collect_data_files('customtkinter')

# Playwright Stealth
datas += collect_data_files('playwright_stealth')

# ===== AI & XỬ LÝ MEDIA (NUMPY, MOVIEPY, IMAGEIO) =====
# MoviePy 2.0+ và các thư viện phụ thuộc yêu cầu metadata để chạy đúng
packages_to_collect = [
    'numpy',
    'imageio',
    'imageio_ffmpeg',
    'moviepy',
    'proglog',
    'decorator',
    'tqdm',
    'pillow',
    'google.genai'
]

for pkg in packages_to_collect:
    try:
        datas += collect_data_files(pkg)
        datas += copy_metadata(pkg)
    except:
        pass

# ================== HIDDEN IMPORTS ==================
hiddenimports = [
    'playwright.sync_api',
    'playwright_stealth',
    'google.genai',
    'customtkinter',
    'PIL.ImageResampling', # Thường bị thiếu trong Pillow mới
    'moviepy.video.fx.all',
    'moviepy.audio.fx.all',
    'moviepy.video.compositing.transitions',
]

# Thu thập tất cả submodules để tránh lỗi "ModuleNotFound" khi chạy EXE
hiddenimports += collect_submodules('moviepy')
hiddenimports += collect_submodules('imageio')
hiddenimports += collect_submodules('proglog')
hiddenimports += collect_submodules('google.genai')

# ================== ANALYSIS ==================
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['pytest', 'unittest', 'tkinter.test', 'matplotlib', 'notebook'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ================== PYZ ==================
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ================== EXE ==================
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TikTokVideoAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[
        'vcruntime140.dll',
        'python3.dll',
        'numpy*.pyd',
    ],
    console=False, # Đặt False để không hiện cửa sổ CMD đen khi chạy app
    icon='icon.ico',
    version='version_info.txt',
)

# ================== COLLECT ==================
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'python3.dll'],
    name='TikTokVideoAI',
)
