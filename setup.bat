@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"

rem ============================================================================
rem Cau hinh tat ca Cache tap trung ve thu muc .\cache de de quan ly va toi uu
rem ============================================================================
if not exist "cache\tmp" mkdir "cache\tmp" >nul 2>&1
if not exist "cache\pycache" mkdir "cache\pycache" >nul 2>&1
if not exist "cache\cuda" mkdir "cache\cuda" >nul 2>&1
if not exist "cache\pip" mkdir "cache\pip" >nul 2>&1
if not exist "models" mkdir "models" >nul 2>&1

set "PYTHONPYCACHEPREFIX=%~dp0cache\pycache"
set "TEMP=%~dp0cache\tmp"
set "TMP=%~dp0cache\tmp"
set "CUDA_CACHE_PATH=%~dp0cache\cuda"
set "HF_HOME=%~dp0cache\models\huggingface"
set "TORCH_HOME=%~dp0cache\models\torch"
set "PIP_CACHE_DIR=%~dp0cache\pip"

echo =====================================================================
echo                Archive2MD — Setup ^& Environment Init
echo         (Cai dat tu dong 1-Click cho moi may Windows moi tinh)
echo =====================================================================
echo.

rem ----------------------------------------------------------------------------
rem Buoc 1: Kiem tra hoac tu dong cai dat Python 3.10+
rem ----------------------------------------------------------------------------
set "SYS_PYTHON="

if exist ".venv\Scripts\python.exe" (
    echo [*] Da ton tai moi truong ao .venv. Bo qua buoc tao venv moi.
    set "VENV_PYTHON=.venv\Scripts\python.exe"
    goto install_deps
)

echo [*] Dang kiem tra trinh thong dich Python tren he thong...

:: Thu tim Python Launcher (py.exe)
py -3.12 --version >nul 2>&1 && set "SYS_PYTHON=py -3.12"
if not defined SYS_PYTHON py -3.11 --version >nul 2>&1 && set "SYS_PYTHON=py -3.11"
if not defined SYS_PYTHON py -3.10 --version >nul 2>&1 && set "SYS_PYTHON=py -3.10"
if not defined SYS_PYTHON py -3 --version >nul 2>&1 && set "SYS_PYTHON=py -3"

:: Thu lenh python thong thuong (loai tru redirect gia cua WindowsApps)
if not defined SYS_PYTHON (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
    if not errorlevel 1 set "SYS_PYTHON=python"
)

:: Kiem tra vi tri cai dat tieu chuan cua nguoi dung
if not defined SYS_PYTHON (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "SYS_PYTHON="%LOCALAPPDATA%\Programs\Python\Python312\python.exe""
    ) else if exist "%ProgramFiles%\Python312\python.exe" (
        set "SYS_PYTHON="%ProgramFiles%\Python312\python.exe""
    )
)

:: Neu van chua tim thay Python -> Tu dong tai va cai dat Python 3.12 chinh thuc
if not defined SYS_PYTHON (
    echo.
    echo [!] May tinh cua ban chua co Python ^>= 3.10.
    echo [*] Dang tu dong tai va cai dat Python 3.12.8 (64-bit) tu python.org...
    echo     (Vui long cho trong giay lat, qua trinh dien ra tu dong...)
    
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; " ^
        "Write-Host ' -> Dang tai Python 3.12.8 Installer...'; " ^
        "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile 'cache\tmp\python-installer.exe'; " ^
        "Write-Host ' -> Dang cai dat Python vao he thong...'; " ^
        "Start-Process -FilePath 'cache\tmp\python-installer.exe' -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0' -Wait; " ^
        "Remove-Item 'cache\tmp\python-installer.exe' -Force -ErrorAction SilentlyContinue"

    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "SYS_PYTHON="%LOCALAPPDATA%\Programs\Python\Python312\python.exe""
        echo [✓] Da cai dat Python 3.12 thanh cong!
    ) else (
        echo [X] Khong the tu dong cai dat Python. Vui long cai dat Python 3.10+ tu python.org
        pause
        exit /b 1
    )
)

echo [*] Su dung trinh thong dich: %SYS_PYTHON%
echo [*] Dang tao moi truong ao .venv...
%SYS_PYTHON% -m venv .venv
if errorlevel 1 (
    echo [X] Loi khi tao moi truong ao .venv.
    pause
    exit /b 1
)

set "VENV_PYTHON=.venv\Scripts\python.exe"

:install_deps
rem ----------------------------------------------------------------------------
rem Buoc 2: Cai dat tat ca thu vien tu requirements.txt
rem ----------------------------------------------------------------------------
echo.
echo [*] Dang cap nhat pip, setuptools va wheel...
%VENV_PYTHON% -m pip install --upgrade pip setuptools wheel

echo.
echo [*] Dang cai dat toan bo thu vien (MarkItDown, Office, Archive, NVIDIA CUDA)...
echo     (Tat ca goi duoc cache gon gang trong .\cache\pip de tai nhanh)
%VENV_PYTHON% -m pip install -r requirements.txt
if errorlevel 1 (
    echo [X] Co loi xay ra trong qua trinh cai dat thu vien.
    pause
    exit /b 1
)

rem ----------------------------------------------------------------------------
rem Buoc 3: Kiem tra va tai mo hinh Vision AI Qwen2.5-VL-3B neu thieu
rem ----------------------------------------------------------------------------
echo.
echo [*] Kiem tra mo hinh Vision AI OCR (models/)...
%VENV_PYTHON% -m services.download_models

rem ----------------------------------------------------------------------------
rem Buoc 4: Kiem tra trang thai toan bo he thong
rem ----------------------------------------------------------------------------
echo.
echo [*] Kiem tra trang thai cac bo chuyen doi va thu muc cache...
%VENV_PYTHON% cli.py --status

echo.
echo =====================================================================
echo [✓] SETUP HOAN TAT 100%!
echo.
echo Cach su dung cong cu:
echo   1. Nhap dup chuot vao 'run.bat' de mo che do hoi dap Interactive
echo   2. Hoac KEO THA truc tiep file (.zip, .rar, .7z, .pdf...) vao 'run.bat'
echo   3. Hoac chay dong lenh: .venv\Scripts\python cli.py ^<duong_dan_file^>
echo =====================================================================
echo.
pause
