@echo off
set "CONDA_PREFIX=C:\Users\dmishra\.conda\envs\market_scanner"
set "_OLD_PATH=%PATH%"
set "PATH=C:\Users\dmishra\.conda\envs\market_scanner;C:\Users\dmishra\.conda\envs\market_scanner\Scripts;%PATH%"
set "CONDA_DEFAULT_ENV=market_scanner"
prompt (market_scanner) $P$G

echo Activated Conda environment: market_scanner
echo Type "deactivate" to exit.
goto :eof

:deactivate
if defined _OLD_PATH (
    set "PATH=%_OLD_PATH%"
    set "_OLD_PATH="
)
set "CONDA_PREFIX="
set "CONDA_DEFAULT_ENV="
prompt $P$G
echo Deactivated environment.
