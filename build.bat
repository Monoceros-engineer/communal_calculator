@echo off
echo Generating help.html from README.md...
python generate_help.py
if errorlevel 1 (
    echo ERROR: help.html generation failed
    pause
    exit /b
)
echo Building executable...
python setup.py build_exe
if errorlevel 1 (
    echo ERROR: build failed
    pause
    exit /b
)
echo Build completed successfully.
pause