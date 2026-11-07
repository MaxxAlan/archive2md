@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

rem ============================================================================
rem Cau hinh tat ca Cache tap trung ve thu muc .\cache de de quan ly va toi uu
rem ============================================================================
set "PYTHONPYCACHEPREFIX=%~dp0cache\pycache"
set "TEMP=%~dp0cache\tmp"
set "TMP=%~dp0cache\tmp"
set "CUDA_CACHE_PATH=%~dp0cache\cuda"
set "HF_HOME=%~dp0cache\models\huggingface"
set "TORCH_HOME=%~dp0cache\models\torch"
set "PIP_CACHE_DIR=%~dp0cache\pip"

rem ----------------------------------------------------------------------------
rem Kiem tra moi truong ao .venv. Neu chua co, tu dong hoi chay setup.bat
rem ----------------------------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo =====================================================================
    echo [!] Chua tim thay moi truong .venv!
    echo =====================================================================
    echo.
    set /p "RUN_SETUP=Ban co muon tu dong chay setup.bat de thiet lap ngay bay gio khong? [Y/n]: "
    if /i "%RUN_SETUP%"=="n" exit /b 1
    call "%~dp0setup.bat"
    if not exist ".venv\Scripts\python.exe" (
        echo.
        echo [!] Setup chua hoan tat. Vui long chay setup.bat de kiem tra loi.
        pause
        exit /b 1
    )
)

rem ----------------------------------------------------------------------------
rem Dieu huong che do chay
rem ----------------------------------------------------------------------------
if "%~1"=="" (
    rem Double click hoac chay khong co tham so -> Vao che do tuong tac hoi dap tung buoc
    ".venv\Scripts\python.exe" cli.py --interactive
    echo.
    echo Nhan phim bat ky de thoat...
    pause >nul
) else (
    rem Chay che do truyen tham so dong lenh hoac keo tha file truc tiep vao run.bat
    ".venv\Scripts\python.exe" cli.py %*
    echo.
    echo =====================================================================
    echo Hoan tat xu ly! Nhan phim bat ky de dong cua so...
    echo =====================================================================
    pause >nul
)
