@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo ERRO: .venv nao encontrado nesta pasta.
  echo Crie com: py -3.11 -m venv .venv
  echo Depois:   .venv\Scripts\activate
  echo           pip install -r requirements-audio.txt
  pause
  exit /b 1
)

".venv\Scripts\python.exe" audio_gui.py
if errorlevel 1 (
  echo.
  echo A interface encerrou com erro.
  pause
)
