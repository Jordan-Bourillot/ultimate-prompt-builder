# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for AlphaBeast.

Build:  pyinstaller alphabeast.spec --noconfirm
Output: dist/UltimatePromptBuilder/UltimatePromptBuilder.exe
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Files to embed in the build
datas = [
    ("mega_prompts.json", "."),
    ("assets", "assets"),
]

# CustomTkinter ships theme JSONs that must follow into the bundle
for pkg in ("customtkinter",):
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass

# Hidden imports (avoid runtime ModuleNotFoundError)
hiddenimports = [
    "customtkinter",
    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "requests",
    "tkinter",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "tkinter.font",
]
for pkg in ("customtkinter",):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "matplotlib", "scipy", "numpy.testing"],
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
    exclude_binaries=True,
    name="UltimatePromptBuilder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="UltimatePromptBuilder",
)
