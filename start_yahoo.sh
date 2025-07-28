#!/bin/bash

# Yahoo 新聞廣告替換器啟動腳本
# 作者：AI Assistant
# 版本：1.0
# 日期：2025年

echo "=========================================="
echo "Yahoo 新聞廣告替換器啟動腳本"
echo "=========================================="

# 檢查 Python 是否安裝
if ! command -v python3 &> /dev/null; then
    echo "❌ 錯誤：找不到 Python3"
    echo "請先安裝 Python3"
    exit 1
fi

# 檢查必要檔案是否存在
if [ ! -f "yahoo_replace.py" ]; then
    echo "❌ 錯誤：找不到 yahoo_replace.py"
    echo "請確保 yahoo_replace.py 檔案存在於當前目錄"
    exit 1
fi

if [ ! -f "config.py" ]; then
    echo "❌ 錯誤：找不到 config.py"
    echo "請確保 config.py 檔案存在於當前目錄"
    exit 1
fi

# 檢查替換圖片資料夾
if [ ! -d "replace_image" ]; then
    echo "❌ 錯誤：找不到 replace_image 資料夾"
    echo "請確保 replace_image 資料夾存在於當前目錄"
    exit 1
fi

# 檢查替換圖片檔案
image_count=$(find replace_image -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" | wc -l)
if [ $image_count -eq 0 ]; then
    echo "❌ 錯誤：replace_image 資料夾中沒有找到圖片檔案"
    echo "請確保資料夾中包含替換用的圖片檔案"
    exit 1
fi

echo "✅ 檢查完成，開始啟動程式..."

# 創建截圖資料夾（如果不存在）
if [ ! -d "screenshots" ]; then
    mkdir screenshots
    echo "✅ 創建 screenshots 資料夾"
fi

# 檢查 Chrome 瀏覽器
if ! command -v google-chrome &> /dev/null && ! command -v chromium-browser &> /dev/null; then
    echo "⚠️  警告：找不到 Chrome 瀏覽器"
    echo "程式可能會使用系統預設瀏覽器"
fi

echo ""
echo "🚀 啟動 Yahoo 新聞廣告替換器..."
echo "目標網站：https://tw.news.yahoo.com/tourist-spots"
echo ""

# 執行主程式
python3 yahoo_replace.py

# 檢查執行結果
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 程式執行完成"
    echo "截圖檔案已保存到 screenshots 資料夾"
else
    echo ""
    echo "❌ 程式執行失敗"
    echo "請檢查錯誤訊息並重試"
fi

echo ""
echo "=========================================="
echo "程式結束"
echo "==========================================" 