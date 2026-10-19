@echo off
chcp 65001 >nul
title Eduvance - carga de teste paralela
set RAIZ=%~dp0
cd /d "%RAIZ%compilado\eduvance.dist" 2>nul || (echo Ainda nao ha executavel. Rode compilar.bat primeiro.& pause & exit /b 1)
if not exist "%RAIZ%docs\evidencias\sprint07" mkdir "%RAIZ%docs\evidencias\sprint07"
echo ================================================================
echo   Abra o Gerenciador de Tarefas ^(Ctrl+Shift+Esc^) na aba
echo   Desempenho ^> CPU e clique com o botao direito no grafico:
echo   "Alterar grafico para" ^> "Processadores logicos".
echo   Depois pressione uma tecla aqui para comecar.
echo ================================================================
pause >nul
echo.
echo ---- Preparando o banco de demonstracao ^(dados reais para a carga^) ----
eduvance.exe --init-db --reset
echo.
echo ---- UM processo ^(linha de base^), 10 segundos ----
eduvance.exe --benchmark-paralelo --processos 1 --segundos 10 --relatorio "%RAIZ%docs\evidencias\sprint07\benchmark_1_processo_pc.txt"
echo.
echo ================================================================
echo   Proximo teste: TODOS os processadores, 30 segundos.
echo   Deixe o Gerenciador de Tarefas visivel; o PRINT deve ser tirado
echo   durante estes 30 segundos ^(tecla Windows + Shift + S^).
echo   Pressione uma tecla para comecar.
echo ================================================================
pause >nul
echo ---- TODOS os processadores ^(auto^), 30 segundos ----
eduvance.exe --benchmark-paralelo --processos auto --segundos 30 --relatorio "%RAIZ%docs\evidencias\sprint07\benchmark_todos_pc.txt"
echo.
echo ---- Recalculo real das recomendacoes de todos os alunos ----
eduvance.exe --recalcular-recomendacoes --processos auto --relatorio "%RAIZ%docs\evidencias\sprint07\recalculo_pc.txt"
echo.
echo Resultados salvos em docs\evidencias\sprint07\  ^(benchmark_*_pc.txt e recalculo_pc.txt^)
echo Tire um print do Gerenciador de Tarefas durante a segunda execucao e salve nessa pasta
echo como gerenciador_tarefas_100.png.
pause
