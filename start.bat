@echo off
title FinanzBro Dashboard
cd /d "%~dp0"
echo Starting FinanzBro...
start "" http://localhost:8000
.\venv\Scripts\python.exe main.py
