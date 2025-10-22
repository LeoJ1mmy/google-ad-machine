# Google 廣告替換器系統 - GIF 升級版

## 🎬 全面支援 GIF 動畫廣告

所有網站的廣告替換器現已全面升級，支援 GIF 動畫廣告替換！

### ✨ 新功能亮點
- 🎬 **GIF 動畫廣告替換**：智能選擇 GIF 或靜態圖片
- ⚙️ **統一設定檔**：所有網站都使用 `gif_config.py`
- 📊 **詳細統計報告**：追蹤 GIF vs 靜態圖片使用比例
- 📍 **智能截圖定位**：廣告按鈕出現在螢幕上 25% 位置
- 🔄 **即時還原機制**：截圖後立即還原廣告

## 📚 各網站使用手冊

### 🗞️ 新聞媒體類
- [Yahoo 新聞使用手冊](Yahoo使用手冊.md) - 熱門景點版面專門優化
- [ETtoday 旅遊雲使用手冊](ETtoday旅遊雲使用手冊.md) - 旅遊內容專門優化
- [聯合報 UDN 使用手冊](聯合報UDN使用手冊.md) - 旅遊新聞專門優化
- [TVBS 食尚玩家使用手冊](TVBS食尚玩家使用手冊.md) - 美食旅遊專門優化
- [自由時報使用手冊](自由時報使用手冊.md) - 新聞廣告替換

### 🗾 旅遊部落格類
- [Linshibi 使用手冊](Linshibi使用手冊.md) - 日本旅遊專門優化

### 🌐 生活風格類
- [Liulife 使用手冊](Liulife使用手冊.md) - 生活風格內容專門優化
- [nicklee 使用手冊](nicklee使用手冊.md) - 商業科技內容專門優化

## 🎯 GIF 優先級策略

所有網站都支援智能圖片選擇：

### GIF 優先模式 (`GIF_PRIORITY = True`)
```python
# 在 gif_config.py 中設定
GIF_PRIORITY = True
```
- 有 GIF 動畫 → 優先選擇 GIF
- 沒有 GIF → 自動使用靜態圖片
- 顯示：`🎬 優先選擇 GIF: google_300x250.gif`

### 靜態優先模式 (`GIF_PRIORITY = False`)
```python
# 在 gif_config.py 中設定
GIF_PRIORITY = False
```
- 有靜態圖片 → 優先選擇靜態圖片
- 沒有靜態圖片 → 自動使用 GIF
- 顯示：`🖼️ 優先選擇靜態圖片: google_300x250.jpg`

## 📸 替換圖片格式

### 命名規則
```
replace_image/
├── google_300x250.jpg    # 靜態圖片
├── google_300x250.gif    # GIF 動畫（同尺寸）
├── google_728x90.jpg     # 靜態圖片
├── google_728x90.gif     # GIF 動畫（同尺寸）
└── ...
```

### 支援格式
- `.jpg`, `.jpeg`, `.png` - 靜態圖片
- `.gif` - GIF 動畫
- `.webp` - WebP 格式

## ⚙️ 統一設定檔 (gif_config.py)

所有網站都使用相同的設定檔：

```python
# 基本設定
SCREENSHOT_COUNT = 30        # 截圖數量
NEWS_COUNT = 20             # 搜尋文章數量
HEADLESS_MODE = False       # 顯示瀏覽器

# GIF 功能設定
GIF_PRIORITY = True         # GIF 優先模式
IMAGE_USAGE_COUNT = {}      # 圖片使用次數統計

# 按鈕樣式設定
BUTTON_STYLE = "dots"       # dots, cross, adchoices, adchoices_dots, none

# 其他設定
PAGE_LOAD_TIMEOUT = 15      # 頁面載入超時
WAIT_TIME = 3               # 等待時間
```

## 📊 統計報告範例

每個網站執行完成後都會顯示詳細統計：

```
📊 [網站名稱] 廣告替換統計報告
====================================
📸 總截圖數量: 15 張
🔄 總替換次數: 15 次
   🎬 GIF 替換: 9 次 (60.0%)
   🖼️ 靜態圖片替換: 6 次 (40.0%)

📋 詳細替換記錄:
    1. 🎬 google_300x250.gif (300x250)
    2. 🖼️ google_728x90.jpg (728x90)
    3. 🎬 google_970x90.gif (970x90)

⚙️ 當前 GIF 策略:
   🎯 優先級模式 - GIF 優先 (GIF_PRIORITY = True)
====================================
```

## 🚀 快速開始

### 1. 準備圖片
在 `replace_image/` 資料夾中放入：
- 靜態圖片：`google_300x250.jpg`
- GIF 動畫：`google_300x250.gif`

### 2. 設定 GIF 策略
修改 `gif_config.py`：
```python
GIF_PRIORITY = True  # 優先使用 GIF
```

### 3. 執行程式
```bash
# Yahoo 新聞
python yahoo_replace.py

# ETtoday 旅遊雲
python ettoday_replace.py

# 聯合報 UDN
python udn_replace.py

# TVBS 食尚玩家
python tvbs_replace.py

# 自由時報
python ltn_replacer.py

# Linshibi 日本旅遊
python linshibi_replace.py

# Liulife 生活風格
python liulife_replace.py

# nicklee 商業科技
python nicklee_replace.py
```

### 4. 查看結果
檢查 `screenshots/` 資料夾中的截圖和統計報告

## 🌟 各網站特色

| 網站 | 專門領域 | 特色功能 |
|------|----------|----------|
| **Yahoo 新聞** | 熱門景點 | 25% 螢幕位置截圖、5秒廣告載入等待 |
| **ETtoday** | 旅遊雲 | 6段式滾動載入、即掃即換技術 |
| **UDN** | 旅遊新聞 | 19選擇器搜尋、Yahoo風格還原 |
| **TVBS** | 美食旅遊 | 5輪搜尋機制、ETtoday風格還原 |
| **自由時報** | 一般新聞 | 基礎廣告替換、多尺寸支援 |
| **Linshibi** | 日本旅遊 | 智能廣告識別、多螢幕支援 |
| **Liulife** | 生活風格 | 生活內容優化、智能廣告識別 |
| **nicklee** | 商業科技 | 商業科技內容、智能廣告識別 |

## 💡 最佳實踐建議

### 圖片準備策略
- **混合準備**：同一尺寸準備 GIF 和靜態兩個版本
- **檔案大小**：GIF 建議小於 5MB
- **常用尺寸**：300x250, 300x600, 728x90, 970x90

### 設定建議
- **新手推薦**：`GIF_PRIORITY = False`（靜態優先，更穩定）
- **進階用戶**：`GIF_PRIORITY = True`（GIF 優先，更生動）
- **截圖數量**：建議 10-30 張

### 執行建議
- **網路穩定**：確保網路連線穩定
- **多螢幕**：選擇解析度較高的螢幕
- **安全中斷**：支援 Ctrl+C 優雅停止

## 🔧 故障排除

### 常見問題
1. **GIF 沒有被使用**：檢查 `GIF_PRIORITY` 設定和檔案存在
2. **找不到廣告**：確認圖片尺寸和命名正確
3. **截圖位置不佳**：所有網站都支援智能定位
4. **統計不準確**：檢查 `gif_config.py` 設定

### 檢查清單
- ✅ `gif_config.py` 設定正確
- ✅ `replace_image/` 資料夾有對應圖片
- ✅ 圖片命名格式正確：`google_寬度x高度.副檔名`
- ✅ 網路連線穩定
- ✅ Google Chrome 已安裝

---

**版本**：GIF 升級版 v2.0  
**更新日期**：2025年10月  
**支援網站**：8個主要新聞、旅遊和生活風格網站  
**核心特色**：全面 GIF 動畫支援 + 統一設定檔 + 智能截圖定位
