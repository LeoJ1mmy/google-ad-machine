#!/bin/bash

# 廣告替換程式啟動腳本

echo "=========================================="
echo "    廣告替換程式啟動中..."
echo "=========================================="

# 檢查 Python 是否安裝
if ! command -v python3 &> /dev/null; then
    echo "❌ 錯誤：找不到 Python3"
    echo "請先安裝 Python3"
    exit 1
fi

# 檢查 requirements.txt 是否存在
if [ ! -f "requirements.txt" ]; then
    echo "❌ 錯誤：找不到 requirements.txt"
    echo "請確認在正確的目錄中執行此腳本"
    exit 1
fi

# 檢查主程式是否存在
if [ ! -f "ad_replacer.py" ]; then
    echo "❌ 錯誤：找不到 ad_replacer.py"
    echo "請確認在正確的目錄中執行此腳本"
    exit 1
fi

# 檢查 config.py 是否存在
if [ ! -f "config.py" ]; then
    echo "❌ 錯誤：找不到 config.py"
    echo "請確認在正確的目錄中執行此腳本"
    exit 1
fi

echo "✅ 檢查完成，開始安裝依賴包..."

# 安裝依賴包
echo "正在安裝依賴包..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ 依賴包安裝失敗"
    exit 1
fi

echo "✅ 依賴包安裝完成"

# 檢查替換圖片資料夾
if [ ! -d "replace_image" ]; then
    echo "⚠️  警告：找不到 replace_image 資料夾"
    echo "請確認替換圖片已放置在正確位置"
fi

# 創建截圖資料夾（如果不存在）
if [ ! -d "screenshots" ]; then
    echo "創建截圖資料夾..."
    mkdir -p screenshots
fi

echo "=========================================="
echo "    開始執行程式..."
echo "=========================================="

# 執行程式
python3 ad_replacer.py

# 檢查程式執行結果
if [ $? -eq 0 ]; then
    echo "=========================================="
    echo "    程式執行完成！"
    echo "    截圖檔案在 screenshots/ 資料夾中"
    echo "=========================================="
else
    echo "=========================================="
    echo "    程式執行失敗"
    echo "    請檢查錯誤訊息"
    echo "=========================================="
fi 