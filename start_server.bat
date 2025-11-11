@echo off
REM ==============================================================================
REM start_server.bat - Script defensiv pentru pornirea serverului Dash
REM VERSIUNEA 3.0 - WINPYTHON PORTABIL
REM ==============================================================================

title Analizator Pulsoximetrie - Server

echo ================================================================
echo PORNIRE SERVER - VERSIUNE DEFENSIVA
echo ================================================================
echo.

REM [CONFIGURARE] Folosim Python din virtual environment (.venv)
set PYTHON_EXE=.venv\Scripts\python.exe

REM [STEP 1] Verificam daca Python virtual environment este disponibil
echo [1/4] Verificare Python virtual environment...
if not exist "%PYTHON_EXE%" (
    echo [EROARE] Virtual environment nu a fost gasit!
    echo Rulati: uv venv
    echo Apoi: uv pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo   [OK] Python venv gasit: %PYTHON_EXE%

REM [STEP 2] Oprim orice server vechi pe baza de python.exe
echo.
echo [2/4] Oprire servere vechi...
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST 2^>nul ^| findstr /I "PID:"') do (
    echo   - Oprire proces Python PID: %%i
    taskkill /F /PID %%i /T >nul 2>&1
)
timeout /t 1 /nobreak >nul
echo   [OK] Cleanup complet

REM [STEP 3] Verificam ca portul 8050 este disponibil (warning, nu blocare)
echo.
echo [3/4] Verificare port 8050...
netstat -ano | findstr ":8050.*LISTENING" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   [AVERTISMENT] Portul 8050 pare ocupat, dar incercam pornirea...
    echo   Conexiunile zombie TCP se vor curata automat.
) else (
    echo   [OK] Portul 8050 este liber
)

REM [STEP 4] Pornim serverul
echo.
echo [4/4] Pornire server Dash...
echo ================================================================
echo.
echo Server va porni la adresa: http://127.0.0.1:8050/
echo Apasati CTRL+C pentru oprire.
echo.
echo ================================================================
echo.

REM Pornim aplicatia Python cu calea completa
"%PYTHON_EXE%" run.py

REM Daca ajungem aici, serverul s-a oprit
echo.
echo ================================================================
echo SERVERUL S-A OPRIT
echo ================================================================
echo.
pause
