@echo off
chcp 65001 >nul
title Eduvance - sistema compilado
cd /d "%~dp0compilado\eduvance.dist" 2>nul || (echo Ainda nao ha executavel. Rode compilar.bat primeiro.& pause & exit /b 1)
echo Abrindo http://localhost:5000  ^(Ctrl+C para parar^)
start "" http://localhost:5000
eduvance.exe
pause
