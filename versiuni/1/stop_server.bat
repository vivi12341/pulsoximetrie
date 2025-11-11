@echo off
title Oprire Server Analizator

echo Cautare proces care ruleaza pe portul 8050...

:: Cauta PID-ul (Process ID) al aplicatiei care foloseste portul 8050
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8050"') do (
    set PID=%%a
)

:: Daca un PID a fost gasit, opreste procesul respectiv
if defined PID (
    echo Proces gasit cu PID: %PID%. Se incearca oprirea...
    taskkill /F /PID %PID%
    echo Server oprit cu succes.
) else (
    echo Nu a fost gasit niciun server care sa ruleze pe portul 8050.
)

echo.
pause 