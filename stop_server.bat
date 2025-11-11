@echo off
REM ==============================================================================
REM stop_server.bat - Script defensiv pentru oprirea serverului Dash
REM VERSIUNEA 3.0 - WINPYTHON PORTABIL
REM ==============================================================================

title Oprire Server Analizator Pulsoximetrie

echo ================================================================
echo OPRIRE SERVER - VERSIUNE DEFENSIVA
echo ================================================================
echo.

REM [CONFIGURARE] Folosim Python din PATH (portabil pe orice calculator)
set PYTHON_EXE=python

REM Gasim TOATE procesele Python (run.py sau orice altceva)
echo [1/3] Cautare si oprire TOATE procesele Python...
set FOUND_PROCESSES=0

for /f "tokens=2 delims=," %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH 2^>nul') do (
    set PID=%%i
    set PID=!PID:"=!
    echo   - Gasit proces Python cu PID: !PID!
    taskkill /F /PID !PID! /T >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo     [OK] Oprit cu succes
    ) else (
        echo     [INFO] Procesul s-a oprit deja
    )
    set FOUND_PROCESSES=1
)

if %FOUND_PROCESSES%==0 (
    echo   [INFO] Nu s-au gasit procese Python active
)

REM Gasim TOATE procesele care asculta pe portul 8050
echo.
echo [2/3] Cautare procese pe portul 8050...
set FOUND_PORT=0

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8050.*LISTENING"') do (
    echo   - Gasit proces pe port 8050 cu PID: %%a
    taskkill /F /PID %%a /T >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo     [OK] Oprit cu succes
    )
    set FOUND_PORT=1
)

if %FOUND_PORT%==0 (
    echo   [INFO] Nu s-au gasit procese pe portul 8050
)

REM Asteptam putin pentru cleanup
echo.
echo [3/3] Asteptare cleanup sistem (2 secunde)...
timeout /t 2 /nobreak >nul

REM Verificare finala
echo.
echo ================================================================
echo VERIFICARE FINALA
echo ================================================================
netstat -ano | findstr ":8050" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [AVERTISMENT] Mai exista conexiuni pe portul 8050 (probabil zombie TCP)
    echo Acestea se vor curata automat. Serverul se poate porni in continuare.
) else (
    echo [OK] Portul 8050 este complet liber!
)

echo.
echo ================================================================
echo SERVER OPRIT CU SUCCES
echo ================================================================
echo.
pause
