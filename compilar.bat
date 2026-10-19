@echo off
chcp 65001 >nul
title Eduvance - compilar com Nuitka (Sprint 07)
cd /d "%~dp0"
set RAIZ=%~dp0
set SAIDA=%RAIZ%docs\evidencias\sprint07\compilacao_pc.txt
set VENV=%RAIZ%.venv-compilar
set DESTINO=%RAIZ%compilado

where python >nul 2>nul || (echo [ERRO] Python nao encontrado.& pause & exit /b 1)
where npm >nul 2>nul || (echo [ERRO] Node.js nao encontrado.& pause & exit /b 1)
if not exist "%RAIZ%docs\evidencias\sprint07" mkdir "%RAIZ%docs\evidencias\sprint07"

echo ================================================
echo   Eduvance - compilando para executavel (Nuitka)
echo   Pode levar de 5 a 20 minutos na primeira vez.
echo   O registro completo vai para:
echo   %SAIDA%
echo ================================================

echo === Eduvance - compilacao com Nuitka === > "%SAIDA%"
echo Data: %date% %time% >> "%SAIDA%"
python --version >> "%SAIDA%" 2>&1
python -c "import struct,platform;print('Python de',struct.calcsize('P')*8,'bits,',platform.machine())" >> "%SAIDA%" 2>&1

REM --- 1) interface (a pasta frontend\dist vai dentro do executavel) ---
echo. >> "%SAIDA%"
echo === 1) npm run build === >> "%SAIDA%"
cd /d "%RAIZ%frontend"
if not exist node_modules call npm install >> "%SAIDA%" 2>&1
call npm run build >> "%SAIDA%" 2>&1
if errorlevel 1 (echo [ERRO] build do front-end falhou. Veja %SAIDA%& pause & exit /b 1)

REM --- 2) ambiente so para compilar (nao mexe no .venv do dia a dia) ---
echo. >> "%SAIDA%"
echo === 2) ambiente de compilacao: Nuitka + dependencias === >> "%SAIDA%"
cd /d "%RAIZ%"
if not exist "%VENV%" python -m venv "%VENV%"
call "%VENV%\Scripts\activate.bat"
python -m pip install -q --upgrade pip >> "%SAIDA%" 2>&1
pip install -q -r backend\requirements.txt waitress nuitka ordered-set zstandard >> "%SAIDA%" 2>&1
if errorlevel 1 (echo [ERRO] instalacao das dependencias falhou. Veja %SAIDA%& pause & exit /b 1)
python -m nuitka --version >> "%SAIDA%" 2>&1

REM --- 3) compilacao. O Nuitka nao usa o MinGW com Python 3.13+, entao usamos o compilador Zig (baixado sozinho) ---
echo. >> "%SAIDA%"
echo === 3) python -m nuitka --standalone --zig ... === >> "%SAIDA%"
if exist "%DESTINO%" rmdir /s /q "%DESTINO%"
set PYTHONPATH=%RAIZ%
cd /d "%RAIZ%backend"
set OPCOES=--standalone --assume-yes-for-downloads --output-dir="%DESTINO%" --output-filename=eduvance --include-package=app --include-module=recomendacao --include-module=recomendacao.motor --nofollow-import-to=recomendacao.servico --nofollow-import-to=recomendacao.tests --include-data-dir=..\database=database --include-data-dir=..\frontend\dist=frontend\dist --noinclude-data-files=database/*.db*
python -m nuitka %OPCOES% --zig eduvance.py >> "%SAIDA%" 2>&1
if errorlevel 1 (
  echo. >> "%SAIDA%"
  echo === 3b - com Zig falhou; tentando com o compilador instalado ^(Visual Studio^) === >> "%SAIDA%"
  python -m nuitka %OPCOES% eduvance.py >> "%SAIDA%" 2>&1
)
if not exist "%DESTINO%\eduvance.dist\eduvance.exe" (
  echo codigo: COMPILACAO FALHOU >> "%SAIDA%"
  echo [ERRO] A compilacao falhou. Veja %SAIDA%
  pause & exit /b 1
)
echo. >> "%SAIDA%"
echo codigo: COMPILACAO OK >> "%SAIDA%"
for %%F in ("%DESTINO%\eduvance.dist\eduvance.exe") do echo eduvance.exe: %%~zF bytes >> "%SAIDA%"

REM --- 4) conferencia do executavel ---
echo. >> "%SAIDA%"
echo === 4) executavel: --versao e --init-db === >> "%SAIDA%"
cd /d "%DESTINO%\eduvance.dist"
eduvance.exe --versao >> "%SAIDA%" 2>&1
eduvance.exe --init-db --reset >> "%SAIDA%" 2>&1
echo. >> "%SAIDA%"
echo === fim === >> "%SAIDA%"

echo.
echo Pronto! Executavel em: %DESTINO%\eduvance.dist\eduvance.exe
echo Para abrir o sistema:  executar_compilado.bat
echo Para a carga de teste: benchmark.bat
pause
