@echo off
pip install flask pynput pystray pillow -q
start pythonw "%~dp0mousecmd.py"
