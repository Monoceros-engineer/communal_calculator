import sys
from cx_Freeze import setup, Executable

base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

build_options = {
    'include_files': [
        'icon.ico', 'icon.png', 'calculator.py', 'communal_calculator.py', 'config.py',
        'file_manager.py', 'main_pyside6.py', 'readme.md', 'help.html', 'paths.py', stats_window.py,
        'assets'
    ],
    'packages': ['PySide6', 'shiboken6', 'tkinter', 'decimal', 'json', 'datetime', 'webbrowser', 'tempfile', 'os', 'sys'],
    'excludes': ['test'],
    'include_msvcr': True,
}

setup(
    name='CommunalCalculator',
    version='1.1',
    description='A tool for calculating communal payments',
    author='Monoceros-engineer',
    options={'build_exe': build_options},
    executables=[
        Executable(
            'main_pyside6.py',
            base=base,
            target_name='CommunalCalculator.exe',
            icon='icon.ico'
        )
    ]
)