@echo off
REM Launch leak_check_GUI.py using conda env: computer_vision
pushd "%~dp0"
call "C:\Users\investment\miniconda3\Scripts\activate.bat"
call conda activate computer_vision
python "..\leak_check_GUI.py"
popd
