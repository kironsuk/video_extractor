# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for building a standalone dvdrip executable."""

a = Analysis(
    ["src/video_extractor/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=[
        "video_extractor",
        "video_extractor.cli",
        "video_extractor.deps",
        "video_extractor.drive",
        "video_extractor.models",
        "video_extractor.ripper",
        "video_extractor.scanner",
        "video_extractor.ui",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Scientific / data libraries
        "numpy",
        "PIL",
        "Pillow",
        "matplotlib",
        "pandas",
        "scipy",
        # Jupyter / IPython ecosystem
        "IPython",
        "jupyter",
        "notebook",
        "tornado",
        "zmq",
        "traitlets",
        # GUI toolkits
        "tkinter",
        "_tkinter",
        # Build / packaging tools
        "setuptools",
        "pkg_resources",
        "distutils",
        "pip",
        # Test frameworks
        "unittest",
        "pytest",
        "test",
        # Other unneeded packages
        "psutil",
        "pycparser",
        "cffi",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="dvdrip",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)
