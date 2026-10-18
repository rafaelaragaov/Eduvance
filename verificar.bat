@echo off
chcp 65001 >nul
title Eduvance - verificacao da Sprint 06
cd /d "%~dp0"
if exist frontend\src\theme.tsx del /q frontend\src\theme.tsx
set RAIZ=%~dp0
set SAIDA=%RAIZ%docs\evidencias\sprint06\verificacao_pc.txt

where python >nul 2>nul || (echo [ERRO] Python nao encontrado.& pause & exit /b 1)
where npm >nul 2>nul || (echo [ERRO] Node.js nao encontrado.& pause & exit /b 1)

echo Gerando %SAIDA% ... ^(leva alguns minutos^)
echo === Eduvance - verificacao da Sprint 06 === > "%SAIDA%"
echo Data: %date% %time% >> "%SAIDA%"
python --version >> "%SAIDA%" 2>&1
node --version >> "%SAIDA%" 2>&1

REM --- 1) npm run typecheck (tsc --noEmit) ---
echo. >> "%SAIDA%"
echo === 1) npm run typecheck === >> "%SAIDA%"
cd /d "%RAIZ%frontend"
if not exist node_modules call npm install >> "%SAIDA%" 2>&1
call npm run typecheck >> "%SAIDA%" 2>&1
echo codigo de saida do typecheck: %errorlevel% >> "%SAIDA%"

REM --- 2) build do frontend ---
echo. >> "%SAIDA%"
echo === 2) npm run build === >> "%SAIDA%"
call npm run build >> "%SAIDA%" 2>&1
echo codigo de saida do build: %errorlevel% >> "%SAIDA%"

REM --- 3) testes do backend ---
cd /d "%RAIZ%backend"
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt >> "%SAIDA%" 2>&1
echo. >> "%SAIDA%"
echo === 3) testes do backend: python -m unittest discover -s tests === >> "%SAIDA%"
python -m unittest discover -s tests >> "%SAIDA%" 2>&1
echo codigo de saida dos testes do backend: %errorlevel% >> "%SAIDA%"

REM --- 4) servico de recomendacao (FastAPI) ---
cd /d "%RAIZ%"
pip install -q -r recomendacao\requirements.txt >> "%SAIDA%" 2>&1
echo. >> "%SAIDA%"
echo === 4) servico de recomendacao: testes do motor e da camada FastAPI === >> "%SAIDA%"
python -c "import fastapi; print('fastapi', fastapi.__version__)" >> "%SAIDA%" 2>&1
python -m unittest discover -v -s recomendacao\tests -t . >> "%SAIDA%" 2>&1
echo codigo de saida dos testes da recomendacao: %errorlevel% >> "%SAIDA%"

REM --- 5) servico no ar: GET /health e POST /recomendar ---
echo. >> "%SAIDA%"
echo === 5) servico no ar ^(uvicorn, porta 8011^) === >> "%SAIDA%"
start "recomendacao-teste" /min cmd /c "cd /d %RAIZ% && call backend\.venv\Scripts\activate.bat && python -m uvicorn recomendacao.servico:app --port 8011"
python -c "import time,urllib.request,json; time.sleep(6); print('GET /health ->', urllib.request.urlopen('http://127.0.0.1:8011/health').read().decode()); rq=urllib.request.Request('http://127.0.0.1:8011/recomendar', data=json.dumps({'disciplinas':[{'nome':'Matematica','media':4.5}],'faltas':3}).encode(), headers={'Content-Type':'application/json'}); print('POST /recomendar ->', urllib.request.urlopen(rq).read().decode()[:400])" >> "%SAIDA%" 2>&1
taskkill /fi "windowtitle eq recomendacao-teste*" /t /f >nul 2>nul

echo. >> "%SAIDA%"
echo === fim === >> "%SAIDA%"
echo.
echo Pronto. Resultado salvo em docs\evidencias\sprint06\verificacao_pc.txt
echo Pode fechar esta janela.
pause
