from cx_Freeze import setup, Executable

build_exe_options = {
    "build_exe": "dist/ea-app-downloader",
    "excludes": ["tkinter", "PyQt5"],
    "replace_paths": [("*", "")]
}

setup(
    name = "EA App Downloader",
    version = "0.1.0",
    options = {"build_exe": build_exe_options},
    executables = [Executable("main.py",target_name="EA_App_Downloader", icon="steamdl.ico",uac_admin=False, base = "console"),
    ]
)
