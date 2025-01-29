@echo off
rem start "Reductus Web GUI" 
call "%~dp0env\Scripts\activate.bat"
start "Reductus Server" "python.exe" "-m" "reductus.web_gui.run"