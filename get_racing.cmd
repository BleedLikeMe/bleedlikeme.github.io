@echo off
title Ceefax racing results - leave open to keep page 400 up to date
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0get_racing.ps1" -Every 10
pause
