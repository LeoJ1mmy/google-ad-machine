# ETtoday旅遊雲廣告替換程式使用手冊

## 🎯 程式功能
- 自動掃描 ETtoday 旅遊雲網站
- 將廣告替換為自訂圖片
- 自動截圖記錄結果
- 專門針對旅遊相關內容

## 📦 安裝
```bash
pip install -r requirements.txt
```

## ⚙️ 設定檔案 (config.py)

### 主要設定
```python
SCREENSHOT_COUNT = 10        # 要截圖的張數
NEWS_COUNT = 20             # 要搜尋的新聞數量
HEADLESS_MODE = False       # 是否隱藏瀏覽器視窗
BASE_URL = "https://travel.ettoday.net"  # ETtoday旅遊雲
```

## 🚀 使用方法


### 1. 手動執行程式
```bash
python ettoday_replace.py
```

### 3. 程式會自動：
- 搜尋 ETtoday 旅遊雲文章
- 掃描廣告位置
- 替換廣告圖片
- 截圖記錄結果
- 達到設定數量後停止

## 📸 替換圖片

### 圖片命名
- 格式：`google_寬度x高度.jpg`
- 範例：`google_300x250.jpg`

### ETtoday 支援尺寸
- 300x250, 728x90, 970x90
- 320x50, 336x280
- 其他常見廣告尺寸

## 🎯 目標網站特色

### ETtoday 旅遊雲
- 專業的旅遊資訊平台
- 豐富的景點介紹
- 美食、住宿、交通資訊
- 高品質的旅遊攝影

### 智能掃描
- 全頁面元素尺寸分析
- ±2像素容差匹配
- 自動排除控制按鈕
- 精確的廣告位置識別

## 🔧 調整設定

### 修改截圖數量
```python
# 在 config.py 中改這行
SCREENSHOT_COUNT = 5        # 改為5張
```

### 修改新聞數量
```python
# 在 config.py 中改這行
NEWS_COUNT = 15             # 改為15個
```

### 隱藏瀏覽器視窗
```python
# 在 config.py 中改這行
HEADLESS_MODE = True        # 不顯示瀏覽器
```

### 修改目標網站
```python
# 在 config.py 中改這行
BASE_URL = "https://travel.ettoday.net"  # ETtoday旅遊雲
```

## 📁 檔案說明

- `ettoday_replace.py` - 主程式
- `start_ettoday.sh` - 啟動腳本
- `ETtoday使用手冊.md` - 使用說明
- `config.py` - 設定檔
- `replace_image/` - 替換圖片資料夾
- `screenshots/` - 截圖輸出資料夾

## ❓ 常見問題

### Q: 程式無法啟動？
A: 確認已安裝依賴包：`pip install -r requirements.txt`

### Q: 找不到廣告？
A: 確認 `replace_image/` 資料夾中有對應尺寸的圖片

### Q: 截圖數量不對？
A: 檢查 `config.py` 中的 `SCREENSHOT_COUNT` 設定

### Q: 瀏覽器無法開啟？
A: 確認已安裝 Google Chrome

### Q: 找不到旅遊文章？
A: 程式會自動搜尋 ETtoday 旅遊雲的文章連結

### Q: 廣告替換失敗？
A: 檢查圖片尺寸是否符合網站廣告規格

## 🌟 特殊功能

### 頁面尺寸分析
- 自動分析頁面元素尺寸分佈
- 顯示最常見的元素尺寸
- 幫助了解網站廣告規格

### 智能滾動載入
- 自動滾動頁面觸發懶載入
- 確保所有廣告都能載入
- 提高廣告發現率

### 精確尺寸匹配
- 允許 ±2 像素的容差範圍
- 適應不同解析度螢幕
- 提高匹配成功率

### 完整還原機制
- 保存原始廣告內容
- 截圖後自動還原
- 不影響網站正常運作

## 📝 注意事項

1. 需要網路連線
2. 需要 Google Chrome 瀏覽器
3. 圖片建議使用 JPG 格式
4. 程式會自動停止達到目標數量
5. 專門針對 ETtoday 旅遊雲網站
6. 支援 Ctrl+C 優雅中斷

## 🎨 截圖命名規則

截圖檔案會自動命名為：
```
ettoday_replaced_[news title]_[時間戳].png
```

範例：
```
ettoday_replaced_[title]_20240131_143022.png
```

## 🔍 除錯功能

### 頁面分析
程式會自動分析頁面上的元素尺寸分佈：
```
頁面上最常見的元素尺寸:
  300x250: 8 個元素
    例如: <div class='ad-container' id='ad_1'>
  728x90: 3 個元素
    例如: <iframe class='google-ad' id=''>
```

### 詳細日誌
- 顯示載入的替換圖片清單
- 記錄廣告掃描進度
- 報告替換成功/失敗狀態
- 截圖保存路徑

---

**簡單三步驟：**
1. 修改 `config.py` 設定
2. 執行 `python ettoday_replace.py`
3. 查看 `screenshots/` 資料夾的結果

**專業提示：**
- ETtoday 旅遊雲內容豐富且更新頻繁
- 建議在網路流量較低時執行以提高成功率
- 程式支援 Ctrl+C 安全中斷，不會損壞資料