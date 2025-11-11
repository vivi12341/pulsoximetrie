@echo off
echo ============================================================
echo   PORNIRE SERVER MEDICAL - PLATFORMA PULSOXIMETRIE
echo ============================================================
echo.
echo Activare virtual environment...
call .venv\Scripts\activate

echo.
echo Pornire aplicatie medicala...
echo Server disponibil la: http://127.0.0.1:8050/
echo.
echo Functionalitati:
echo   - Tab Admin: Generare link-uri, upload CSV
echo   - Tab Pacient: Acces cu token, explorare CSV
echo   - Tab Vizualizare: Analiza interactiva (original)
echo   - Tab Batch: Procesare in lot (original)
echo.
echo Apasati CTRL+C pentru a opri serverul.
echo ============================================================
echo.

python run_medical.py

pause

