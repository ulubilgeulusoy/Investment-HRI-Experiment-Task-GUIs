@echo off
REM Launch visual_inspection_GUI.py using conda env: computer_vision
pushd "%~dp0"
call "C:\Users\investment\miniconda3\Scripts\activate.bat"
call conda activate computer_vision
python "..\visual_inspection_GUI.py"
popd
