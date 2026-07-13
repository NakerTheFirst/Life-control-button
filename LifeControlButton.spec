# -*- mode: python ; coding: utf-8 -*-
import os

# Qt libraries the app never loads, pruned so Defender has ~27 MB less to
# scan at logon (and the release zip shrinks to match). qpdf.dll is the only
# consumer of Qt6Pdf, qtuiotouchplugin (TUIO touch input over UDP) the only
# consumer of Qt6Network; opengl32sw is the software OpenGL fallback, which a
# raster QWidget app never touches.
PRUNED_BINARIES = {
    'opengl32sw.dll',
    'Qt6Pdf.dll',
    'qpdf.dll',
    'Qt6Network.dll',
    'qtuiotouchplugin.dll',
}

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6.QtNetwork', 'PyQt6.QtPdf'],
    noarchive=False,
    optimize=0,
)
a.binaries = [entry for entry in a.binaries
              if os.path.basename(entry[0]) not in PRUNED_BINARIES]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LifeControlButton',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LifeControlButton',
)
