@echo off
rem Windows'ta kurulum (setup) dosyasini uretir.
rem Gerekenler: Python 3.8+ (tkinter dahil) ve Inno Setup 6 (https://jrsoftware.org/isdl.php)
python -m pip install -r requirements.txt pyinstaller || exit /b 1
python -m PyInstaller --noconfirm --clean --windowed --name MusteriTakip --icon assets\icon.ico --add-data "assets;assets" main.py || exit /b 1
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
%ISCC% installer\kurulum.iss || exit /b 1
echo.
echo Kurulum dosyasi: installer\Output\YildizYapi_MusteriTakip_Kurulum.exe
