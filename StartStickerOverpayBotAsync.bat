@echo off

REM Путь к вашему виртуальному окружению (venv)
set VENV_PATH=.\venv

REM Путь к скрипту 
set SCRIPT_PATH=.\StickerOverpayBotAsync.py

REM Активация виртуального окружения
call %VENV_PATH%\Scripts\activate

REM Запуск Python скрипта
python %SCRIPT_PATH%