@echo off
REM Launch combined_experiment_GUI.py using conda env: computer_vision
pushd "%~dp0"
call "C:\Users\investment\miniconda3\Scripts\activate.bat"
call conda activate computer_vision
python "combined_experiment_GUI.py"
popd
