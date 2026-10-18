@echo off
chcp 65001 >nul
title Eduvance - preparar e iniciar (projeto local)
cd /d "%~dp0"
if exist frontend\src\theme.tsx del /q frontend\src\theme.tsx

echo ================================================
echo   Eduvance - preparando o ambiente local
echo ================================================

where python >nul 2>nul || (echo.& echo [ERRO] Python nao encontrado. Instale em https://www.python.org/downloads/ e marque "Add python.exe to PATH".& pause & exit /b 1)
where npm >nul 2>nul || (echo.& echo [ERRO] Node.js nao encontrado. Instale a versao LTS em https://nodejs.org/ & pause & exit /b 1)

REM --- 2) backend ---
cd backend
if not exist .venv (
  echo Criando ambiente Python...
  python -m venv .venv || (pause & exit /b 1)
)
call .venv\Scripts\activate.bat
echo Instalando dependencias do backend...
pip install -q -r requirements.txt || (pause & exit /b 1)

REM --- 3) banco: cria se nao existe; recria se for de uma Sprint anterior (sem as colunas da Sprint 06 em recomendacao_ia) ---
set PRECISA_BANCO=0
if not exist "..\database\eduvance.db" set PRECISA_BANCO=1
if "%PRECISA_BANCO%"=="0" (
  python -c "import sqlite3,sys; c=sqlite3.connect('../database/eduvance.db'); cols=[r[1] for r in c.execute('pragma table_info(recomendacao_ia)')]; t=c.execute(\"select 1 from sqlite_master where name='preferencia_usuario'\").fetchone(); sys.exit(0 if ('justificativa' in cols and t) else 1)"
  if errorlevel 1 set PRECISA_BANCO=1
)
if "%PRECISA_BANCO%"=="1" (
  echo Criando banco de dados com os dados de demonstracao...
  python -m app.init_db --reset || (pause & exit /b 1)
)

REM --- 3b) servico de recomendacao (FastAPI, opcional): se as dependencias instalarem, ele sobe em http://localhost:8001 ---
set EDUVANCE_RECOMENDACAO_URL=
pip install -q -r ..\recomendacao\requirements.txt >nul 2>nul
python -c "import fastapi, uvicorn" >nul 2>nul
if not errorlevel 1 (
  echo Iniciando o servico de recomendacao ^(FastAPI^) na porta 8001...
  start "Eduvance - servico de recomendacao" /min cmd /c "cd /d %~dp0 && call backend\.venv\Scripts\activate.bat && python -m uvicorn recomendacao.servico:app --port 8001"
  set EDUVANCE_RECOMENDACAO_URL=http://127.0.0.1:8001
) else (
  echo FastAPI indisponivel: as recomendacoes usarao o motor embutido no backend.
)

REM --- 4) frontend ---
cd ..\frontend
if not exist node_modules (
  echo Instalando dependencias do frontend ^(pode demorar na primeira vez^)...
  call npm install || (pause & exit /b 1)
)
echo Compilando a interface...
call npm run build || (pause & exit /b 1)

REM --- 5) iniciar ---
cd ..\backend
echo.
echo ================================================
echo   Pronto! Abrindo http://localhost:5000
echo   Feche esta janela (ou Ctrl+C) para parar.
echo.
echo   paula@eduvance.com    senha123  (coordenadora)
echo   ricardo@eduvance.com  senha123  (professor)
echo   20260001              senha123  (aluno Lucas)
echo   maria@eduvance.com    senha123  (responsavel)
echo   admin@eduvance.com    admin123  (administrador)
echo ================================================
start "" http://localhost:5000
python run.py
pause
