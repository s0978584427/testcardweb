#!/bin/bash
# 卡牌價格監控系統 - Linux/Mac 快速啟動腳本

# 檢查虛擬環境是否存在
if [ ! -d "venv" ]; then
    echo "🔧 創建虛擬環境..."
    python3 -m venv venv
fi

# 激活虛擬環境
echo "🚀 激活虛擬環境..."
source venv/bin/activate

# 檢查依賴是否已安裝
if ! pip show flask > /dev/null 2>&1; then
    echo "📦 安裝依賴項..."
    pip install -r requirements.txt
fi

# 啟動應用
echo "🎉 啟動應用..."
echo "📍 訪問地址: http://localhost:5000"
python app.py
