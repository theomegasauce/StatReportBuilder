# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = []
hiddenimports += collect_submodules("scipy")
hiddenimports += collect_submodules("scipy.stats")
hiddenimports += collect_submodules("scipy.special")

datas = []
datas += collect_data_files("scipy")
datas += collect_data_files("matplotlib")


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "PyQt5",
        "PyQt6",
        "torch",
        "torchvision",
        "torchaudio",
        "tensorflow",
        "jax",
        "jaxlib",
        "sympy",
        "IPython",
        "jupyter",
        "notebook",
        "pyarrow",
        "sphinx",
        "pytest",
        "pandas.tests",
        "scipy.io.tests",
        "numpy.tests",
        "PIL.ImageQt",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="StatReportBuilder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="StatReportBuilder",
)
