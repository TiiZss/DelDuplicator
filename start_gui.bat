@echo off
REM Script de inicio rápido para DelDuplicator GUI
pushd "%~dp0"
echo Iniciando DelDuplicator GUI...
python delduplicator_gui.py
if errorlevel 1 pause
