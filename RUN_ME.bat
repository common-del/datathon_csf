@echo off
REM ============================================================
REM  Double-click this. It runs the whole analysis.
REM  If anything goes wrong the window stays open so you can read it.
REM ============================================================
cd /d "%~dp0"
echo.
echo  Running the Datathon 2026 pipeline...
echo  This takes about 1-3 minutes. Do not close this window.
echo.
python src\run_all.py
echo.
echo  ============================================================
echo   Finished. Look in the outputs folder.
echo   Read outputs\tables\qa_flags.csv FIRST.
echo   Open outputs\dashboard.html in your browser.
echo  ============================================================
echo.
pause
