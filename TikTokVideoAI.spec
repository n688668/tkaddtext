# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
    copy_metadata,
)

block_cipher = None

# ================== DATAS ==================
datas = [
    ('font.ttf', '.'),
    ('icon.ico', '.'),
    ('version_info.txt', '.'),
    ('config.env.template', '.'),
    ('input/bg001.mp4', 'input'),
]

datas += collect_data_files('customtkinter')
datas += collect_data_files('playwright_stealth')

# ===== AI & XỬ LÝ MEDIA (NUMPY, MOVIEPY, IMAGEIO) =====
packages_to_collect = [
    'numpy', 'imageio', 'imageio_ffmpeg', 'moviepy',
    'proglog', 'decorator', 'pillow', 'google.genai'
]

for pkg in packages_to_collect:
    try:
        if pkg in ['numpy', 'imageio', 'moviepy']:
            datas += copy_metadata(pkg)

        if pkg == 'pillow':
            datas += collect_data_files('PIL')
        else:
            datas += collect_data_files(pkg)
    except:
        pass

# ================== HIDDEN IMPORTS ==================
hiddenimports = [
    'playwright.sync_api',
    'playwright_stealth',
    'google.genai',
    'customtkinter',
    'PIL.ImageResampling',
    'moviepy.video.fx.all',
    'moviepy.audio.fx.all',
    'moviepy.video.compositing.transitions',
]

hiddenimports += collect_submodules('moviepy')
hiddenimports += collect_submodules('imageio')
hiddenimports += collect_submodules('proglog')
hiddenimports += collect_submodules('google.genai')

# **************************************************
# Bổ sung: Thêm Playwright Submodules để kích hoạt hook thu thập driver.exe
hiddenimports += collect_submodules('playwright')
# **************************************************

# ================== ANALYSIS ==================
a = Analysis(
    ['main.py'],
    pathex=[],
    # Để trống binaries, dựa vào hook tự động của Playwright
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
    console=False,
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