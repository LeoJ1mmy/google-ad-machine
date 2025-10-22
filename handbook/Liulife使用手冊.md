# Liulife 廣告替換程式使用手冊 - GIF 升級版

## 🎯 程式功能
- 🎬 **支援 GIF 動畫廣告替換**（新功能）
- 🔍 自動掃描 Liulife 網站廣告
- 🖼️ 智能選擇靜態圖片或 GIF 動畫
- 📸 支援多種廣告尺寸 (970x90, 728x90, 300x250, 300x600 等)
- 🎛️ 智能廣告識別和動態廣告處理
- 📍 自動截圖記錄結果（滑動到最佳位置）
- 🌐 專門針對生活風格相關內容
- ⚙️ 使用 gif_config.py 統一設定檔

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
GIF_PRIORITY = True         # GIF 優先模式（新功能）
BUTTON_STYLE = "dots"       # 按鈕樣式 (dots/cross/adchoices/adchoices_dots/none)
```

## 🚀 執行程式

### 基本執行
```bash
python liulife_replace.py
```

### 執行流程
1. 🌐 自動開啟 Liulife 網站
2. 🔍 掃描頁面中的廣告元素
3. 🎬 根據 GIF_PRIORITY 選擇替換圖片
4. 🎛️ 添加驚嘆號和叉叉按鈕
5. 📍 滑動到最佳位置（25% 螢幕位置）
6. 📸 自動截圖並保存
7. 🔄 還原廣告並處理下一個

## 📸 替換圖片（支援 GIF）

### 圖片命名規則
- **靜態圖片**：`google_寬度x高度.jpg`
- **GIF 動畫**：`google_寬度x高度.gif`
- 範例：`google_300x250.jpg`, `google_300x250.gif`

### GIF 優先級策略
- **GIF_PRIORITY = True**：優先使用 GIF 動畫
- **GIF_PRIORITY = False**：優先使用靜態圖片
- 如果只有一種類型，自動選擇可用的圖片

### Liulife 支援尺寸
- **970x90** - 大橫幅廣告
- **728x90** - 橫幅廣告  
- **300x250** - 中矩形廣告
- **300x600** - 大側邊欄廣告
- **320x50** - 手機橫幅
- **336x280** - 大矩形廣告
- **160x600** - 側邊欄廣告
- **120x600** - 窄側邊欄廣告
- **240x400** - 中型廣告
- **250x250** - 正方形廣告
- **320x100** - 手機大橫幅
- **980x120** - 超大橫幅
- **200x200** - 正方形廣告（僅 GIF）
- 其他常見廣告尺寸

## 🔧 調整設定

### 修改截圖數量
```python
# 在 gif_config.py 中改這行
SCREENSHOT_COUNT = 10       # 改為10張
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

## 📁 檔案說明

- `liulife_replace.py` - 主程式（GIF 升級版）
- `gif_config.py` - 統一設定檔（新版）
- `config.py` - 舊版設定檔（備用）
- `replace_image/` - 替換圖片資料夾（支援 GIF）
  - `google_300x250.jpg` - 靜態圖片
  - `google_300x250.gif` - GIF 動畫
- `screenshots/` - 截圖輸出資料夾

## ❓ 常見問題

### Q: 找不到廣告？
A: 
- 確認 `replace_image/` 資料夾中有對應尺寸的圖片（.jpg 或 .gif）
- 程式會自動等待動態廣告載入
- 檢查網站是否有廣告區塊
- 程式支援多種廣告類型（AdSense、Google 展示廣告）

### Q: 截圖數量不對？
A: 檢查 `gif_config.py` 中的 `SCREENSHOT_COUNT` 設定

### Q: GIF 沒有被使用？
A: 檢查 `GIF_PRIORITY` 設定，或確認有對應尺寸的 GIF 檔案

### Q: 按鈕位置不對？
A: 調整 `BUTTON_STYLE` 設定，支援 5 種按鈕樣式

## ✨ 新功能特色

### 1. GIF 動畫支援
- **智能圖片選擇**：根據 GIF_PRIORITY 設定自動選擇
- **GIF 優先模式**：優先使用動畫廣告，提升視覺效果
- **靜態備用**：當 GIF 不可用時自動使用靜態圖片
- **使用統計**：詳細記錄 GIF 和靜態圖片的使用次數

### 2. 智能截圖定位
- **自動滑動**：讓廣告按鈕出現在螢幕上 25% 位置
- **最佳視角**：確保截圖效果最佳
- **即時還原**：截圖後立即還原廣告

### 3. 多種按鈕樣式
- **dots**：三個藍色圓點 + 驚嘆號圓圈
- **cross**：藍色叉叉 + 驚嘆號圓圈
- **adchoices**：藍色叉叉 + AdChoices 圖標
- **adchoices_dots**：三個藍色圓點 + AdChoices 圖標
- **none**：無按鈕模式

## 📝 注意事項

1. 需要網路連線
2. 需要 Google Chrome 瀏覽器
3. 支援 JPG、PNG、GIF、WebP 格式
4. 程式會自動停止達到目標數量
5. GIF 檔案會讓廣告更生動，但檔案較大

## 📊 統計報告

程式執行完成後會顯示詳細統計：
```
📊 Liulife 廣告替換統計報告
====================================
📸 總截圖數量: 30 張
🔄 總替換次數: 30 次
   🎬 GIF 替換: 18 次 (60.0%)
   🖼️ 靜態圖片替換: 12 次 (40.0%)

📋 詳細替換記錄:
    1. 🎬 google_300x250.gif (300x250)
    2. 🖼️ google_728x90.jpg (728x90)
    3. 🎬 google_970x90.gif (970x90)

⚙️ 當前 GIF 策略:
   🎯 優先級模式 - GIF 優先 (GIF_PRIORITY = True)
====================================
```

---

**簡單三步驟：**
1. 修改 `gif_config.py` 設定（特別是 `SCREENSHOT_COUNT` 和 `GIF_PRIORITY`）
2. 執行 `python liulife_replace.py`（GIF 升級版）
3. 查看 `screenshots/` 資料夾的結果

**專業提示：**
- Liulife 內容豐富且更新頻繁
- 程式支援多種廣告尺寸，自動識別最佳匹配
- 智能按順序獲取文章，避免重複處理
- 建議在網路流量較低時執行以提高成功率
- 程式支援 Ctrl+C 安全中斷，不會損壞資料
- 每個廣告位置只處理一次，提高效率
- GIF 檔案會讓廣告更生動，但檔案較大
- 同一尺寸準備 GIF 和靜態兩個版本

---

**版本**：3.0 - GIF 升級版  
**目標網站**：Liulife  
**特色**：GIF 動畫支援 + 多尺寸廣告支援 + 智能廣告識別 + 生活風格內容優化