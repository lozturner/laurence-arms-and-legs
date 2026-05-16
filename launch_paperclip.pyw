"""Windowless launcher for paperclip.py. Drop a shortcut in shell:startup."""
import runpy, pathlib
runpy.run_path(str(pathlib.Path(__file__).with_name("paperclip.py")), run_name="__main__")
