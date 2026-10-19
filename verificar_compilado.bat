@echo off
chcp 65001 >nul
title Eduvance - conferir o executavel compilado
cd /d "%~dp0"
set RAIZ=%~dp0
set SAIDA=%RAIZ%docs\evidencias\sprint07\compilacao_pc.txt
set DIST=%RAIZ%compilado\eduvance.dist

if not exist "%DIST%\eduvance.exe" (echo [ERRO] eduvance.exe nao encontrado. Rode compilar.bat primeiro.& pause & exit /b 1)

echo. >> "%SAIDA%"
echo codigo: COMPILACAO OK >> "%SAIDA%"
for %%F in ("%DIST%\eduvance.exe") do echo eduvance.exe: %%~zF bytes >> "%SAIDA%"
echo. >> "%SAIDA%"
echo === 4) executavel: --versao e --init-db === >> "%SAIDA%"
cd /d "%DIST%"
eduvance.exe --versao >> "%SAIDA%" 2>&1
eduvance.exe --init-db --reset >> "%SAIDA%" 2>&1
echo. >> "%SAIDA%"
echo === fim === >> "%SAIDA%"

echo.
echo === Resultado ===
type "%SAIDA%" | findstr /i /c:"execu" /c:"COMPILACAO" /c:"banco" /c:"Erro"
echo.
echo Pronto. Agora rode benchmark.bat (carga de teste) e depois me avise.
pause
