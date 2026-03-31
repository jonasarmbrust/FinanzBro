@echo off
title FinanceBro Dashboard
cd /d "%~dp0"
echo Starting FinanceBro...
start "" http://localhost:8000
.\venv\Scripts\python.exe main.py
