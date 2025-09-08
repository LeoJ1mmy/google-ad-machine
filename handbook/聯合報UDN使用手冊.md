# 聯合報 UDN 旅遊廣告替換器 - 正式版使用手冊

## 🎯 核心功能特色
- 🎬 **GIF 動畫廣告替換**：智能 GIF 檢測、優先級策略、統計分析
- 🖥️ **跨平台多螢幕支援**：Windows、macOS、Linux 自動偵測與選擇
- 🎨 **5 種按鈕樣式**：dots、cross、adchoices、adchoices_dots、none
- 📊 **6段式滾動觸發**：智能懶載入廣告檢測機制
- 🔄 **Yahoo 風格還原**：簡化清理式廣告還原機制
- 🎯 **Yahoo 風格 SVG 按鈕**：15x15px 正方形向量按鈕設計
- 🛡️ **nicklee 精確檢測邏輯**：嚴格外部網域過濾機制
- 🏛️ **UDN 旅遊專門優化**：travel.udn.com 深度整合

## 📦 安裝
```bash
pip install -r requirements.txt
```

## ⚙️ 設定檔案 (gif_config.py)

### 🎬 GIF 功能設定
```python
# GIF 使用策略
GIF_PRIORITY = False         # True: 優先使用 GIF, False: 優先使用靜態圖片

# 基本設定
SCREENSHOT_COUNT = 30        # 要截圖的張數
NEWS_COUNT = 20             # 要搜尋的文章數量
IMAGE_USAGE_COUNT = {        # 圖片使用次數限制
    "google_970x90.jpg": 5,
    "google_986x106.jpg": 3
}
```

### 🎨 按鈕樣式設定
```python
BUTTON_STYLE = "dots"           # 三個點按鈕（預設）
BUTTON_STYLE = "cross"          # 十字關閉按鈕  
BUTTON_STYLE = "adchoices"      # AdChoices 標準樣式
BUTTON_STYLE = "adchoices_dots" # AdChoices + 點按鈕
BUTTON_STYLE = "none"           # 無按鈕模式
```

### 🖥️ 多螢幕設定
```python
HEADLESS_MODE = False       # 是否隱藏瀏覽器視窗
FULLSCREEN_MODE = True      # 全螢幕模式
# 程式啟動時會自動偵測多螢幕並讓使用者選擇
```

### 📊 統計分析設定
```python
MAX_CONSECUTIVE_FAILURES = 10   # 最大連續失敗次數
PAGE_LOAD_TIMEOUT = 15          # 頁面載入超時時間
WAIT_TIME = 3                   # 等待時間
```## 🚀 使用方法


### 1. 螢幕選擇與啟動
程式啟動時會自動偵測多螢幕環境：
```
==================================================
偵測到的螢幕:
==================================================
螢幕 1: 1536x864 (主螢幕)
螢幕 2: 2560x1440
螢幕 3: 1920x1080
==================================================
請選擇要使用的螢幕 (1-3) [預設: 1]:
```

### 2. 執行程式
```bash
python udn_replace.py
```

### 3. 圖片載入與統計
程式會自動載入並分析替換圖片：
```
📊 圖片尺寸分佈統計:
  300x250: 2張 (1張靜態 + 1張GIF)
  728x90: 2張 (1張靜態 + 1張GIF)
  970x90: 1張 (1張靜態)

📋 完整圖片清單:
  1. 🎬 google_300x250.gif (300x250)
  2. 🖼️ google_300x250.jpg (300x250)
  3. 🎬 google_728x90.gif (728x90)
```

### 4. 智能執行流程
- 🔍 **多輪文章搜尋**：使用 UDN 特定選擇器 + 後備搜尋
- 📊 **6段式滾動觸發**：0% → 50% → 100% → 0% 循環載入
- 🎯 **全頁面廣告掃描**：使用多層 CSS 選擇器檢測
- 🎬 **GIF 優先級選擇**：根據 `GIF_PRIORITY` 智能選擇
- 📸 **即掃即換截圖**：找到廣告立即替換並截圖
- 🔄 **Yahoo 風格還原**：簡化清理式廣告還原
- 📈 **即時統計報告**：追蹤 GIF vs 靜態替換比例

## 📸 GIF 升級版替換圖片系統

### 🎬 混合圖片格式支援
```
replace_image/
├── google_300x250.jpg    # 靜態圖片
├── google_300x250.gif    # GIF 動畫 (同尺寸)
├── google_728x90.jpg     # 靜態圖片
├── google_728x90.gif     # GIF 動畫 (同尺寸)
├── google_970x90.jpg     # 靜態圖片
├── google_320x50.gif     # GIF 動畫
└── google_336x280.webp   # WebP 格式
```

### 📏 嚴格命名規則
- **格式**：`google_寬度x高度.副檔名`
- **支援格式**：`.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
- **尺寸匹配**：檔名尺寸必須與實際圖片尺寸一致
- **範例**：
  - `google_300x250.gif` ✅ 正確
  - `google_300x250_animated.gif` ❌ 錯誤
  - `ad_300x250.gif` ❌ 錯誤

### 🎯 智能選擇策略 (已移除隨機模式)
程式使用**優先級模式**進行圖片選擇：

#### GIF 優先模式 (`GIF_PRIORITY = True`)
1. 如果有 GIF 動畫 → 選擇第一個 GIF
2. 如果沒有 GIF → 選擇第一個靜態圖片
3. 顯示：`🎬 優先選擇 GIF: google_300x250.gif`

#### 靜態優先模式 (`GIF_PRIORITY = False`)
1. 如果有靜態圖片 → 選擇第一個靜態圖片
2. 如果沒有靜態圖片 → 選擇第一個 GIF
3. 顯示：`🖼️ 優先選擇靜態圖片: google_300x250.jpg`

### 📊 動態尺寸生成
程式會根據 `replace_image/` 資料夾自動生成目標廣告尺寸：
```
根據替換圖片生成目標廣告尺寸: 
[120x600, 160x600, 200x200, 240x400, 250x250, 300x250, 300x50, 300x600, 320x100, 320x50, 336x280, 728x90, 970x90, 980x120]
```## 🏛️ 聯
合報 UDN 旅遊專門優化

### 🎯 目標網站特色
- **權威新聞平台**：travel.udn.com 專門優化
- **豐富旅遊內容**：景點、美食、住宿、交通全方位
- **高品質報導**：專業記者採訪、深度旅遊報導
- **即時更新**：每日更新的旅遊資訊和新聞

### 🔍 19選擇器智能文章搜尋系統
程式使用 **19個選擇器** 進行全面搜尋：

#### UDN 旅遊特定選擇器 (前7個)
```python
link_selectors = [
    "a[href*='/travel/story/']",        # 旅遊故事連結 (主要)
    "a[href*='/travel/article/']",      # 旅遊文章連結
    "a[href*='/travel/spot/']",         # 景點連結
    "a[href*='/travel/food/']",         # 美食連結
    "a[href*='/travel/hotel/']",        # 住宿連結
    "a[href*='/travel/activity/']",     # 活動連結
    "a[href*='/travel/']",              # 所有旅遊連結
]
```

#### UDN 標題和網域選擇器 (第8-11個)
```python
    "h3 a[href*='travel.udn.com']",                 # 標題中的旅遊連結
    "h2 a[href*='travel.udn.com']",                 # 二級標題中的旅遊連結
    "a[href*='travel.udn.com'][href*='.html']",     # 所有 HTML 旅遊連結
    "a[href*='travel.udn.com']",                    # 旅遊網域連結
```

#### 關鍵字搜尋選擇器 (第12-17個)
```python
    "a[href*='travel']",                            # 包含travel的連結
    "a[href*='旅遊']",                              # 包含旅遊的連結
    "a[href*='景點']",                              # 包含景點的連結
    "a[href*='美食']",                              # 包含美食的連結
    "a[href*='住宿']",                              # 包含住宿的連結
    "a[href*='活動']",                              # 包含活動的連結
```

#### 通用文章選擇器 (第18-19個)
```python
    "a[href*='story']",                             # 故事連結
    "a[href*='article']",                           # 文章連結
```

### 🛡️ UDN 專用 URL 驗證
#### 必須符合的 URL 模式
```python
# UDN 文章 URL 模式驗證
valid_travel = any(keyword in href.lower() for keyword in [
    'travel.udn.com', 'story', 'article', 'spot', 'food', 'hotel', 'activity',
    'travel', '旅遊', '景點', '美食', '住宿', '活動'
])

# 確保是具體的旅遊文章而不是分類頁面
is_article_page = ('.html' in href or '/story/' in href or '/article/' in href) and not href.endswith('/')
```

#### 排除的連結類型
```python
not_travel = any(exclude in href.lower() for exclude in [
    '/news/', '/opinion/', '/sports/', '/entertainment/', '/society/', 
    '/politics/', '/international/', '/business/', '/tech/',
    'login', 'signin', 'register', 'account', 'profile', 'settings', 
    'help', 'about', 'contact', 'privacy', 'terms', 'index'
])
```

### 🎯 廣告檢測優化
#### UDN 特定廣告選擇器
```python
# 針對 UDN 網站的廣告檢測
ad_selectors = [
    "div[id*='google_ads']",
    "div[id*='ads-']", 
    "div[class*='google']",
    "div[class*='ads']",
    "iframe[src*='googleads']",
    "iframe[src*='googlesyndication']",
    "iframe[src*='doubleclick']",
    # UDN 特定廣告容器
    ".udn-ads",
    "[class*='udn-ads']"
]
```

#### 完全尺寸匹配
- **嚴格匹配**：廣告尺寸必須完全符合替換圖片尺寸
- **無容差範圍**：不允許 ±2px 容差，確保精確替換
- **多重驗證**：檢查 `getBoundingClientRect()` 的 width 和 height## 
🔧 進階設定調整

### 📊 統計設定
```python
# 在 gif_config.py 中修改
SCREENSHOT_COUNT = 30       # 截圖數量
NEWS_COUNT = 20            # 搜尋文章數量
```

### 🎬 GIF 策略調整
```python
# GIF 使用優先級
GIF_PRIORITY = False       # True: 優先GIF, False: 優先靜態
```

### 🎨 按鈕樣式切換
```python
# 5種按鈕樣式選擇
BUTTON_STYLE = "dots"           # 預設三點樣式
BUTTON_STYLE = "cross"          # 十字關閉樣式
BUTTON_STYLE = "adchoices"      # AdChoices 標準樣式
BUTTON_STYLE = "adchoices_dots" # AdChoices + 點樣式
BUTTON_STYLE = "none"           # 無按鈕樣式
```

### ⏱️ 效能調整
```python
PAGE_LOAD_TIMEOUT = 30     # 頁面載入超時
WAIT_TIME = 3              # 等待時間
MAX_CONSECUTIVE_FAILURES = 10  # 最大連續失敗次數
```

## 📁 檔案結構說明

```
udn_replace_project/
├── udn_replace.py                   # 主程式 - 正式版
├── gif_config.py                    # GIF 功能專用設定檔
├── handbook/
│   └── 聯合報UDN使用手冊.md          # 本使用手冊
├── replace_image/                   # 替換圖片資料夾
│   ├── google_300x250.jpg          # 靜態廣告圖片
│   ├── google_300x250.gif          # GIF 動畫廣告
│   ├── google_728x90.jpg           # 各種尺寸支援
│   └── ...
├── screenshots/                     # 截圖輸出資料夾
└── requirements.txt                # 依賴套件清單
```

### 🔧 核心檔案功能
- **udn_replace.py**：整合所有功能的主程式
- **gif_config.py**：GIF 和進階功能設定
- **ScreenManager**：多螢幕偵測和管理
- **UdnAdReplacer**：核心廣告替換引擎

## ❓ 常見問題與解決方案

### Q: 程式無法啟動？
A: 
1. 確認已安裝依賴：`pip install -r requirements.txt`
2. 檢查是否有 `gif_config.py` 設定檔
3. 確認 Google Chrome 已安裝

### Q: 多螢幕偵測失敗？
A: 
- **Windows**：程式會嘗試 PowerShell、wmic、tkinter 三種方法
- **macOS**：使用 system_profiler 和 AppleScript
- **Linux**：需要 xrandr 命令
- 如果偵測失敗會自動使用主螢幕

### Q: GIF 功能不正常？
A: 
1. 確認 `replace_image/` 資料夾中有 `.gif` 檔案
2. 檢查 `gif_config.py` 中的 `GIF_PRIORITY` 設定
3. 查看程式輸出的圖片載入統計

### Q: 找不到 UDN 文章？
A: 
- 程式使用 19 個選擇器進行全面搜尋
- 會自動過濾外部網域連結
- 支援 `/travel/story/`, `/travel/article/` 等路徑

### Q: Yahoo 風格還原失敗？
A: 
- Yahoo 風格使用簡化清理機制
- 檢查是否有殘留的 `data:image` 圖片
- 確認按鈕和注入元素已清理完成##
 🌟 核心特色功能

### 🎬 GIF 動畫廣告系統
- **智能 GIF 識別**：自動區分 `.gif` 和靜態圖片格式
- **優先級策略**：`GIF_PRIORITY` 設定優先使用 GIF 或靜態圖片
- **即時統計追蹤**：分別統計 `gif_replacements` 和 `static_replacements`
- **詳細替換記錄**：`replacement_details` 記錄每次替換的完整資訊
- **混合格式支援**：同一尺寸可同時有 GIF 和靜態版本

### 🔄 Yahoo 風格還原機制
- **簡化清理策略**：直接移除所有注入元素
- **全域清理檢查**：檢查整個頁面而不是單個容器
- **輕量級備份**：只保存個別元素的原始屬性
- **清理式還原**：移除注入內容讓原始廣告自然恢復

### 🎨 Yahoo 風格 SVG 按鈕系統
#### 5種按鈕樣式
```python
BUTTON_STYLE = "dots"           # 三個點按鈕 (預設)
BUTTON_STYLE = "cross"          # 十字關閉按鈕  
BUTTON_STYLE = "adchoices"      # AdChoices 標準樣式
BUTTON_STYLE = "adchoices_dots" # AdChoices + 點按鈕組合
BUTTON_STYLE = "none"           # 無按鈕模式
```

#### 按鈕規格
- **尺寸**：15x15 像素正方形
- **格式**：SVG 向量圖形
- **顏色**：`#00aecd` (可自訂)
- **間距**：按鈕間距 1px
- **位置**：右上角偏移 16px

### 📊 6段式滾動觸發機制
```javascript
// 實際程式碼中的滾動策略
1. scrollTo(0, document.body.scrollHeight/2)  // 滾動到中間
2. scrollTo(0, document.body.scrollHeight)    // 滾動到底部  
3. scrollTo(0, 0)                            // 滾動回頂部
4. scrollBy(0, -200)                         // 微調滾動
5. 等待 1-2 秒讓懶載入觸發
6. 重複滾動確保所有廣告載入
```

### 📈 即時統計與分析系統
```python
# 統計變數
self.total_screenshots = 0      # 總截圖數量
self.total_replacements = 0     # 總替換次數  
self.gif_replacements = 0       # GIF 替換次數
self.static_replacements = 0    # 靜態圖片替換次數
self.replacement_details = []   # 詳細替換記錄
```

#### 統計報告輸出
```
📊 UDN 廣告替換統計報告
====================================
📸 總截圖數量: 15 張
🔄 總替換次數: 15 次
   🎬 GIF 替換: 3 次 (20.0%)
   🖼️ 靜態圖片替換: 12 次 (80.0%)

📋 詳細替換記錄:
    1. 🖼️ google_250x250.jpg (250x250)
    2. 🖼️ google_300x250.jpg (300x250)
    3. 🖼️ google_728x90.jpg (728x90)

⚙️ 當前 GIF 策略:
   🎯 優先級模式 - 靜態圖片優先 (GIF_PRIORITY = False)
====================================
```

## 📸 即掃即換截圖系統

### 🎨 截圖命名規則
採用 **即掃即換** 模式，每次廣告替換後立即截圖：
```
udn_[文章標題]_[時間戳].png
```

#### 實際截圖範例
```
udn_2025墾丁住宿推薦_6間必收藏親子友善民宿平價高CP值室內_20250908_112047.png
udn_藏壽司18款吉伊卡哇扭蛋來了全台5間主題店　打卡再抽保冷袋_20250908_112114.png
udn_去郊區走走京都嵐山這樣玩最輕鬆景點交通一次掌握_20250908_112138.png
```

### 🔄 Yahoo 風格清理驗證
```python
# Yahoo 風格驗證：檢查全頁面是否還有注入元素
verification = self.driver.execute_script("""
    // 檢查整個頁面是否還有注入元素
    var replacedImages = document.querySelectorAll('img[src*="data:image"]');
    var addedButtons = document.querySelectorAll('#close_button, #abgb, [id^="close_button"], [id^="abgb"]');
    
    return {
        replacedImages: replacedImages.length,
        addedButtons: addedButtons.length
    };
""")

if verification['replacedImages'] == 0 and verification['addedButtons'] == 0:
    print(f"✅ {ad_info['width']}x{ad_info['height']} at {ad_info['position']}")
```## 📝
 重要注意事項

### ✅ 系統需求
1. **網路連線**：需要穩定的網路連接 UDN 網站
2. **Google Chrome**：必須安裝最新版 Chrome 瀏覽器
3. **Python 環境**：Python 3.7+ 和相關依賴套件
4. **螢幕解析度**：建議 1920x1080 或更高解析度

### 🎬 GIF 功能需求
1. **圖片格式**：支援 `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
2. **命名規則**：必須遵循 `google_寬度x高度.副檔名` 格式
3. **檔案大小**：GIF 建議小於 5MB 以確保載入速度
4. **尺寸匹配**：圖片尺寸必須與網站廣告尺寸相符

### 🛡️ 安全與隱私
1. **僅限 UDN**：程式只會處理 travel.udn.com
2. **無資料收集**：不會收集或傳送個人資料
3. **本地執行**：所有處理都在本地電腦進行
4. **優雅中斷**：支援 Ctrl+C 安全停止程式

### ⚠️ 使用限制
1. **網站結構變更**：UDN 網站更新可能影響功能
2. **廣告載入時間**：懶載入廣告需要等待時間
3. **螢幕截圖權限**：某些系統可能需要螢幕錄製權限
4. **防毒軟體**：可能被誤判為自動化工具

## 🚀 快速開始指南

### **四步驟啟動流程：**
1. **準備 GIF 圖片**：在 `replace_image/` 放入 `.gif` 和 `.jpg` 檔案
2. **設定 GIF 策略**：修改 `gif_config.py` 中的 `GIF_PRIORITY = False`
3. **執行程式**：`python udn_replace.py`
4. **選擇螢幕**：從自動偵測的多螢幕中選擇最佳螢幕
5. **查看結果**：檢查 `screenshots/` 資料夾和完整統計報告

### **🎯 最佳實踐建議：**
- **混合圖片策略**：同一尺寸準備 GIF 和靜態兩個版本
- **靜態優先模式**：`GIF_PRIORITY = False` 確保穩定性
- **多螢幕優勢**：選擇解析度較高的螢幕 (如 2560x1440)
- **網路穩定性**：確保網路連線穩定以提高文章搜尋成功率
- **即時監控**：觀察程式輸出了解 GIF vs 靜態替換比例

### **🎬 GIF 升級版亮點：**
- **智能混合替換**：根據 `GIF_PRIORITY` 自動選擇最佳圖片類型
- **即掃即換技術**：找到廣告立即替換並截圖，無需等待
- **Yahoo 風格還原**：簡化清理式廣告還原機制
- **詳細統計分析**：追蹤 GIF 使用比例和替換成功率
- **多螢幕全螢幕**：支援多螢幕環境的全螢幕操作

### **🏛️ UDN 旅遊專門優化：**
- **19選擇器搜尋**：確保找到足夠的旅遊文章
- **嚴格網域過濾**：只處理 travel.udn.com 文章
- **6段式滾動載入**：觸發所有懶載入廣告完整載入
- **即時統計報告**：顯示 GIF vs 靜態圖片使用分析
- **安全中斷機制**：Ctrl+C 優雅停止，不損壞資料

### **🔄 Yahoo 風格還原優勢：**
- **簡化清理機制**：直接移除注入元素，讓原始廣告自然恢復
- **全域檢查驗證**：檢查整個頁面而不是單個容器
- **輕量級備份**：只保存必要的原始屬性
- **高效能還原**：減少複雜的 JavaScript 操作

---

**簡單三步驟：**
1. 修改 `gif_config.py` 設定
2. 執行 `python udn_replace.py`
3. 查看 `screenshots/` 資料夾的結果

**專業提示：**
- UDN 旅遊內容豐富且更新頻繁
- 建議在網路流量較低時執行以提高成功率
- 程式支援 Ctrl+C 安全中斷，不會損壞資料
- GIF 檔案會讓廣告更生動，但檔案較大
- Yahoo 風格還原機制更簡單可靠
- 19個選擇器確保找到足夠的旅遊文章
- 完全尺寸匹配確保替換精確度