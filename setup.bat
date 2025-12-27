@echo off
color 0B
title Cai Dat Moi Truong cho Ung Dung VideoAI

echo =======================================================
echo "|----- KICH HOAT CAI DAT MOI TRUONG UNG DUNG -----|"
echo =======================================================
echo.

REM 1. KIEM TRA PYTHON CO TRONG PATH KHONG
echo 1. Kiem tra su ton tai cua Python...
python --version >nul 2>&1
if errorlevel 1 goto error_no_python
echo Phat hien Python: OK
echo Hay chac chan phien ban Python 3.11.
echo.

REM 2. TAO VA KICH HOAT MOI TRUONG AO
echo 2. Tao va kich hoat moi truong ao (.venv)...
python -m venv .venv
if errorlevel 1 goto error_venv

REM SU DUNG CALL DE DAM BAO SCRIPT QUAY LAI THUC HIEN TIEP
CALL .venv\Scripts\activate.bat

IF NOT EXIST .venv\Scripts\pip.exe (
    goto error_venv_activate
)

echo Kich hoat moi truong ao thanh cong!
echo.

REM 3. NANG CAP PIP (trong moi truong ao)
echo 3. Kiem tra va nang cap PIP len phien ban moi nhat...
REM SU DUNG python -m pip de dam bao tinh tin cay
python -m pip install --upgrade pip
if errorlevel 1 goto error_pip_upgrade
echo Nang cap PIP thanh cong!
echo.

REM 4. CAI DAT TAT CA CAC THU VIEN TU REQUIREMENTS.TXT (trong moi truong ao)
echo 4. Cai dat cac thu vien Python tu requirements.txt...
python -m pip install -r requirements.txt
if errorlevel 1 goto error_requirements_install
echo Cai dat thu vien thanh cong!
echo.

REM 5. CAI DAT TRINH DUYET CHROMIUM (Tai khoang 150MB) (trong moi truong ao)
echo 5. Tai va cai dat trinh duyet Chromium cho Playwright...
python -m playwright install chromium
if errorlevel 1 goto error_chromium_install
echo Tai Chromium thanh cong!
echo.

REM 6. KIEM TRA VA TAO FILE .env MAU (QUAN TRONG)
echo 6. Kiem tra file .env...
if not exist .env (
    echo GEMINI_API_KEY=YOUR_KEY_HERE >> .env
    echo Tao file .env mau thanh cong.
) else (
    echo File .env da ton tai. Bo qua.
)
echo.

echo =======================================================
echo "|----- CAI DAT MOI TRUONG HOAN TAT! -----|"
echo =======================================================
echo.
echo BUOC CUOI CUNG QUAN TRONG:
echo 1. Mo file .env (cung thu muc nay).
echo 2. Thay the YOUR_KEY_HERE bang GEMINI_API_KEY cua ban.
echo.
echo LUU Y: De chay ung dung, ban can kich hoat moi truong ao truoc:
echo .venv\Scripts\activate.bat
echo Sau do moi chay App.py (hoac App.exe).
pause
goto end

REM --- Xu ly loi ---

:error_no_python
color 0C
echo.
echo -------------------------------------------------------
echo [LOI: THIEU PYTHON] Khong the tim thay lenh python.
echo -------------------------------------------------------
echo Yeu cau: Ung dung can Python 3.11 de chay.
echo.
echo => Buoc 1: Vui long tai va cai dat Python tu trang web chinh thuc:
echo https://www.python.org/downloads/
echo.
echo => Buoc 2 (RAT QUAN TRONG): Khi cai dat, ban PHAI TICH CHON:
echo     "Add Python to PATH"
echo.
echo Sau khi cai dat Python, hay chay lai file setup.bat nay.
echo -------------------------------------------------------
pause
goto end

:error_venv
color 0C
echo.
echo -------------------------------------------------------
echo [LOI TAO MOI TRUONG AO] Khong the tao moi truong ao.
echo LUU Y: Thu chay lai file setup.bat bang quyen Admin.
echo -------------------------------------------------------
pause
goto end

:error_venv_activate
color 0C
echo.
echo -------------------------------------------------------
echo [LOI KICH HOAT] Khong the kich hoat moi truong ao.
echo Kiem tra xem thu muc .venv\Scripts\ co ton tai khong.
echo -------------------------------------------------------
pause
goto end

:error_pip_upgrade
color 0C
echo.
echo -------------------------------------------------------
echo [LOI NANG CAP PIP] Khong the nang cap PIP. Kiem tra ket noi mang hoac thu chay lai.
echo -------------------------------------------------------
pause
goto end

:error_requirements_install
color 0C
echo.
echo -------------------------------------------------------
echo [LOI CAI DAT THU VIEN] Khong the cai dat cac thu vien trong requirements.txt.
echo -------------------------------------------------------
pause
goto end

:error_chromium_install
color 0C
echo.
echo -------------------------------------------------------
echo [LOI TAI CHROMIUM] Qua trinh tai trinh duyet that bai.
echo Giai phap: Kiem tra ket noi internet hoac thu chay file nay bang quyen Admin.
echo -------------------------------------------------------
pause
goto end

:end