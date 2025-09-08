# ETtoday旅遊雲廣告替換程式使用手冊

## 🎯 程式功能
- 自動掃描 ETtoday 旅遊雲網站
- 將廣告替換為自訂圖片（支援 GIF 動畫）
- 自動截圖記錄結果
- 智能按鈕添加與移除
- 專門針對旅遊相關內容

## 📦 安裝
```bash
pip install -r requirements.txt
```

## ⚙️ 設定檔案 (gif_config.py)

### 主要設定
```python
SCREENSHOT_COUNT = 30        # 要截圖的張數
NEWS_COUNT = 20             # 要搜尋的新聞數量
HEADLESS_MODE = False       # 是否隱藏瀏覽器視窗
BASE_URL = "https://travel.ettoday.net"  # ETtoday旅遊雲

# GIF 使用策略設定
GIF_PRIORITY = True         # True: 優先使用 GIF，False: 優先使用靜態圖片
RANDOM_SELECTION = False    # 固定使用優先級模式

# 按鈕設定
BUTTON_STYLE = "dots"       # 按鈕樣式：dots, cross, adchoices, adchoices_dots, none
BUTTON_TOP_OFFSET = 0       # 按鈕上邊距偏移 (固定1px距離)
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

### 圖片命名規則
- 靜態圖片：`google_寬度x高度.jpg`
- GIF 動畫：`google_寬度x高度.gif`
- 範例：`google_300x250.jpg`, `google_300x250.gif`

### ETtoday 支援尺寸
- **主要尺寸**：300x250, 300x600, 728x90, 970x90
- **行動尺寸**：320x50, 320x100
- **其他尺寸**：120x600, 160x600, 240x400, 250x250, 336x280, 980x120
- **特殊尺寸**：200x200 (僅 GIF)

### 圖片選擇策略
- **GIF 優先模式** (`GIF_PRIORITY = True`)：有 GIF 就用 GIF，沒有才用靜態圖片
- **靜態優先模式** (`GIF_PRIORITY = False`)：有靜態圖片就用靜態，沒有才用 GIF

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
# 在 gif_config.py 中改這行
SCREENSHOT_COUNT = 5        # 改為5張
```

### 修改新聞數量
```python
# 在 gif_config.py 中改這行
NEWS_COUNT = 15             # 改為15個
```

### 隱藏瀏覽器視窗
```python
# 在 gif_config.py 中改這行
HEADLESS_MODE = True        # 不顯示瀏覽器
```

### GIF 使用策略
```python
# 在 gif_config.py 中改這行
GIF_PRIORITY = True         # True: GIF 優先, False: 靜態圖片優先
```

### 按鈕樣式設定
```python
# 在 gif_config.py 中改這行
BUTTON_STYLE = "dots"       # 可選: dots, cross, adchoices, adchoices_dots, none
```

### 按鈕位置微調
```python
# 在 gif_config.py 中改這行
BUTTON_TOP_OFFSET = 0       # 0=固定1px, -1=往上移, 1=往下移
```

## 📁 檔案說明

- `ettoday_replace.py` - 主程式
- `gif_config.py` - 設定檔（支援 GIF 功能）
- `handbook/ETtoday旅遊雲使用手冊.md` - 使用說明
- `replace_image/` - 替換圖片資料夾（支援 .jpg 和 .gif）
- `screenshots/` - 截圖輸出資料夾

## ❓ 常見問題

### Q: 程式無法啟動？
A: 確認已安裝依賴包：`pip install -r requirements.txt`

### Q: 找不到廣告？
A: 確認 `replace_image/` 資料夾中有對應尺寸的圖片（.jpg 或 .gif）

### Q: 截圖數量不對？
A: 檢查 `gif_config.py` 中的 `SCREENSHOT_COUNT` 設定

### Q: GIF 沒有被使用？
A: 檢查 `GIF_PRIORITY` 設定，或確認有對應尺寸的 GIF 檔案

### Q: 按鈕位置不對？
A: 調整 `BUTTON_TOP_OFFSET` 數值，或更改 `BUTTON_STYLE`

### Q: 瀏覽器無法開啟？
A: 確認已安裝 Google Chrome

### Q: 找不到旅遊文章？
A: 程式會自動搜尋 ETtoday 旅遊雲的文章連結

### Q: 廣告替換失敗？
A: 檢查圖片尺寸是否符合網站廣告規格

## 🌟 特殊功能

### GIF 動畫支援
- 支援 GIF 動畫廣告替換
- 智能選擇 GIF 或靜態圖片
- 可配置優先級策略

### 智能按鈕系統
- 自動添加 Google 標準按鈕
- 5 種按鈕樣式可選
- 可調整按鈕位置
- 截圖後自動移除按鈕

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
- 截圖後自動還原廣告和移除按鈕
- 不影響網站正常運作

### 多螢幕支援
- 自動偵測多螢幕環境
- 可選擇指定螢幕執行
- 支援全螢幕模式

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
ettoday_[簡化標題]_[時間戳].png
```

範例：
```
ettoday_台北水舞嘉年華913登場120公尺雙水幕投影萌趣IP__ET_20250905_170355.png
```

## 📊 統計報告

程式執行完成後會顯示詳細統計：
```
📊 ETtoday 廣告替換統計報告
📸 總截圖數量: 10 張
🔄 總替換次數: 10 次
   🎬 GIF 替換: 6 次 (60.0%)
   🖼️ 靜態圖片替換: 4 次 (40.0%)

⚙️ 當前 GIF 策略:
   🎯 優先級模式 - GIF 優先
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

## 🎯 按鈕樣式說明

### 可選樣式
- **dots**：三個藍色圓點 + 驚嘆號圓圈
- **cross**：藍色叉叉 + 驚嘆號圓圈  
- **adchoices**：藍色叉叉 + AdChoices 圖標
- **adchoices_dots**：三個藍色圓點 + AdChoices 圖標
- **none**：無按鈕

### 按鈕位置
- 關閉按鈕：廣告右上角
- 資訊按鈕：關閉按鈕左側 17px
- 可透過 `BUTTON_TOP_OFFSET` 微調垂直位置

---

**簡單三步驟：**
1. 修改 `gif_config.py` 設定
2. 執行 `python ettoday_replace.py`
3. 查看 `screenshots/` 資料夾的結果

**專業提示：**
- ETtoday 旅遊雲內容豐富且更新頻繁
- 建議在網路流量較低時執行以提高成功率
- 程式支援 Ctrl+C 安全中斷，不會損壞資料
- GIF 檔案會讓廣告更生動，但檔案較大
- 按鈕會在截圖後自動移除，不影響網站原貌