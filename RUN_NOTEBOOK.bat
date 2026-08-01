@echo off
REM ===================================================================
REM  Datathon 2026 - Team datathon_csf
REM  Opens jupyter_notebook.ipynb from the repo root, whatever folder
REM  you double-click it from. Then use Cell > Run All.
REM ===================================================================

REM cd to the folder this .bat lives in, which is the repo root
cd /d "%~dp0"

echo.
echo   Repo root: %CD%
echo.

REM ---- is Python on PATH?
where python >nul 2>&1
if errorlevel 1 (
    echo   [X] Python was not found on your PATH.
    echo       Install Python 3.10 or newer, tick "Add python.exe to PATH",
    echo       then run this file again.
    echo.
    pause
    exit /b 1
)
python --version

REM ---- is the notebook here?
if not exist "jupyter_notebook.ipynb" (
    echo.
    echo   [X] jupyter_notebook.ipynb is not in this folder.
    echo       Keep this .bat file in the repo root, next to the notebook.
    echo.
    pause
    exit /b 1
)

REM ---- is the data there? warn, do not block
set DATA_OK=0
if exist "external_data\datathon_master_appended_new.csv" set DATA_OK=1
if exist "data\primary\std_grade6_2024-25.csv" set DATA_OK=1
if "%DATA_OK%"=="0" (
    echo.
    echo   [!] No assessment data found yet. The notebook will stop at the data check.
    echo       Read DATA_ACCESS.md. Quickest fix: download the zip and unzip it to
    echo       external_data\datathon_master_appended_new.csv
    echo.
    echo       Press any key to open the notebook anyway, or close this window.
    pause >nul
)

REM ---- is Jupyter installed?
python -c "import notebook" >nul 2>&1
if errorlevel 1 (
    echo.
    echo   Jupyter is not installed. Installing the requirements now, one time only.
    echo   This needs internet. Nothing in the analysis itself does.
    echo.
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo   [X] pip install failed. Try running it yourself:
        echo       python -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
)

echo.
echo   Opening jupyter_notebook.ipynb in your browser.
echo   In Jupyter, choose:  Kernel  ^>  Restart Kernel and Run All Cells
echo.
echo   Leave this window open while you work. Closing it stops Jupyter.
echo.

python -m jupyter notebook "jupyter_notebook.ipynb"

REM ---- if Jupyter exits with an error, keep the window open so it can be read
if errorlevel 1 (
    echo.
    echo   [X] Jupyter exited with an error. The message above explains why.
    echo.
    pause
)
