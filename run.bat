@echo off
REM 卡牌價格監控系統 - Windows 快速啟動腳本

REM 檢查虛擬環境是否存在
if not exist "venv" (
    echo 🔧 創建虛擬環境...
    python -m venv venv
)

REM 激活虛擬環境
echo 🚀 激活虛擬環境...
call venv\Scripts\activate.bat

REM 檢查依賴是否已安裝
pip show flask > nul 2>&1
if errorlevel 1 (
    echo 📦 安裝依賴項...
    pip install -r requirements.txt
)

REM 啟動應用
echo 🎉 啟動應用...
echo 📍 訪問地址: http://localhost:5000
python app.py

pause
