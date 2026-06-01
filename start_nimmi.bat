@echo off
title NIMMI Shop Server
echo ========================================
echo    Запуск NIMMI Shop Server
echo ========================================
echo.

cd /d C:\Users\LENOVO GAMING\PyCharmMiscProject

if not exist ".venv\Scripts\activate.bat" (
    echo Виртуальное окружение не найдено! Создаю...
    python -m venv .venv
)

echo Активация виртуального окружения...
call .venv\Scripts\activate.bat

echo Установка зависимостей...
pip install -r requirements.txt

echo.
echo ========================================
echo Сервер запускается...
echo Откройте браузер и перейдите по адресу: http://localhost:8000
echo Для остановки сервера закройте это окно или нажмите Ctrl+C
echo ========================================
echo.

python script.py

pause