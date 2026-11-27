@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if not errorlevel 1 goto runpython
where py >nul 2>nul
if not errorlevel 1 goto runpy
echo Python topilmadi. https://www.python.org/downloads/ dan o'rnating (Add to PATH belgisini qo'ying).
goto end
:runpython
python app.py
goto end
:runpy
py app.py
:end
pause
