# TVBS 食尚玩家廣告替換器 - 正式版使用手冊

## 🎯 核心功能特色
- 🎬 **GIF 動畫廣告替換**：智能 GIF 檢測、優先級策略、統計分析
- 🖥️ **跨平台多螢幕支援**：Windows、macOS、Linux 自動偵測與選擇
- 🎨 **5 種按鈕樣式**：dots、cross、adchoices、adchoices_dots、none
- 📊 **6段式滾動觸發**：智能懶載入廣告檢測機制
- 🔄 **ETtoday 風格還原**：無刷新頁面的完整廣告還原
- 🎯 **Yahoo 風格 SVG 按鈕**：15x15px 正方形向量按鈕設計
- 🛡️ **nicklee 精確檢測邏輯**：嚴格外部網域過濾機制
- 🍽️ **TVBS 食尚玩家專門優化**：supertaste.tvbs.com.tw 深度整合

## 📦 安裝
```bash
pip install -r requirements.txt
```

## ⚙️ 設定檔案 (gif_config.py)

### 🎬 GIF 功能設定
```python
# GIF 使用策略
GIF_PRIORITY = True          # True: 優先使用 GIF, False: 優先使用靜態圖片

# 基本設定
SCREENSHOT_COUNT = 10        # 要截圖的張數
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
```

## 🚀 使用方法

### 1. 螢幕選擇與啟動
程式啟動時會自動偵測多螢幕環境：
```
==================================================
偵測到的螢幕:
==================================================
螢幕 1: 1920x1080 (主螢幕)
螢幕 2: 2560x1440
螢幕 3: 1920x1080
==================================================
請選擇要使用的螢幕 (1-3) [預設: 1]:
```

### 2. 執行程式
```bash
python tvbs_replace.py
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
- 🔍 **多輪文章搜尋**：使用 TVBS 特定選擇器 + 後備搜尋
- 📊 **6段式滾動觸發**：0% → 50% → 100% → 0% 循環載入
- 🎯 **全頁面廣告掃描**：使用多層 CSS 選擇器檢測
- 🎬 **GIF 優先級選擇**：根據 `GIF_PRIORITY` 智能選擇
- 📸 **即掃即換截圖**：找到廣告立即替換並截圖
- 🔄 **ETtoday 風格還原**：保存原始狀態並完整還原
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
[300x250, 728x90, 970x90, 320x50, 336x280, 120x600, 160x600]
```

### 🔍 按尺寸分組管理
```
📊 圖片尺寸分佈統計:
  300x250: 2張 (1張靜態 + 1張GIF)
  728x90: 2張 (1張靜態 + 1張GIF)  
  970x90: 1張 (1張靜態)
  320x50: 1張 (1張GIF)
  336x280: 1張 (1張靜態)
```

## 🎯 TVBS 食尚玩家專門優化

### 🍽️ 目標網站特色
- **專業美食旅遊平台**：supertaste.tvbs.com.tw
- **豐富內容類型**：美食、旅遊、生活風格
- **高品質攝影**：專業的美食和旅遊攝影
- **即時更新**：頻繁的內容更新

### 🔍 智能掃描系統
- **6段式滾動觸發**：逐步觸發懶載入廣告
- **全頁面元素分析**：掃描所有可能的廣告位置
- **±2像素容差匹配**：適應不同解析度
- **嚴格外部網域過濾**：整合 nicklee 精確邏輯

### 🛡️ 網域過濾機制
自動過濾外部網站連結：
- 社群媒體：Facebook, Twitter, Instagram, YouTube
- 搜尋引擎：Google, Yahoo, Bing
- 電商平台：Amazon, 訂房網站
- 通訊軟體：Line, Telegram, WhatsApp

## 🔧 進階設定調整

### 📊 統計設定
```python
# 在 gif_config.py 中修改
SCREENSHOT_COUNT = 10       # 截圖數量
NEWS_COUNT = 20            # 搜尋文章數量
```

### 🎬 GIF 策略調整
```python
# GIF 使用優先級
GIF_PRIORITY = True        # True: 優先GIF, False: 優先靜態
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

### 🖥️ 螢幕和顯示設定
```python
HEADLESS_MODE = False      # 顯示瀏覽器視窗
FULLSCREEN_MODE = True     # 全螢幕模式
# 多螢幕會在程式啟動時自動選擇
```

### ⏱️ 效能調整
```python
PAGE_LOAD_TIMEOUT = 15     # 頁面載入超時
WAIT_TIME = 3              # 等待時間
MAX_CONSECUTIVE_FAILURES = 10  # 最大連續失敗次數
```

## 📁 檔案結構說明

```
tvbs_replace_project/
├── tvbs_replace.py              # 主程式 - 正式版
├── gif_config.py                # GIF 功能專用設定檔
├── handbook/
│   └── TVBS食尚玩家使用手冊.md   # 本使用手冊
├── replace_image/               # 替換圖片資料夾
│   ├── google_300x250.jpg      # 靜態廣告圖片
│   ├── google_300x250.gif      # GIF 動畫廣告
│   ├── google_728x90.jpg       # 各種尺寸支援
│   └── ...
├── screenshots/                 # 截圖輸出資料夾
└── requirements.txt            # 依賴套件清單
```

### 🔧 核心檔案功能
- **tvbs_replace.py**：整合所有功能的主程式
- **gif_config.py**：GIF 和進階功能設定
- **ScreenManager**：多螢幕偵測和管理
- **TvbsAdReplacer**：核心廣告替換引擎

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

### Q: 找不到 TVBS 文章？
A: 
- 程式使用多輪搜尋機制，包含後備搜尋
- 會自動過濾外部網域連結
- 支援 `/travel/`, `/life/`, `/article/` 等路徑

### Q: 按鈕樣式不顯示？
A: 
- 檢查 `BUTTON_STYLE` 設定是否正確
- 支援：dots, cross, adchoices, adchoices_dots, none
- 按鈕使用 Yahoo 風格 SVG 設計

### Q: 截圖統計不準確？
A: 
- 程式會分別統計 GIF 和靜態圖片替換次數
- 檢查 `replacement_details` 詳細記錄
- 確認 `SCREENSHOT_COUNT` 設定值

## 🌟 核心特色功能

### 🎬 GIF 動畫廣告系統
- **智能 GIF 識別**：自動區分 `.gif` 和靜態圖片格式
- **優先級策略**：`GIF_PRIORITY` 設定優先使用 GIF 或靜態圖片
- **即時統計追蹤**：分別統計 `gif_replacements` 和 `static_replacements`
- **詳細替換記錄**：`replacement_details` 記錄每次替換的完整資訊
- **混合格式支援**：同一尺寸可同時有 GIF 和靜態版本

### 🖥️ ScreenManager 多螢幕系統
#### Windows 螢幕偵測
- **PowerShell 方法**：使用 `System.Windows.Forms.Screen` 獲取螢幕資訊
- **wmic 備用方法**：`Win32_VideoController` 查詢螢幕解析度
- **tkinter 後備方法**：使用 Python tkinter 獲取螢幕尺寸

#### macOS 螢幕偵測
- **system_profiler**：`SPDisplaysDataType` 獲取顯示器詳細資訊
- **AppleScript 備用**：使用 Finder 計算螢幕數量

#### Linux 螢幕偵測
- **xrandr 命令**：解析 `xrandr` 輸出獲取螢幕資訊
- **connected 狀態檢測**：只顯示已連接的螢幕

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

### 🔄 ETtoday 風格還原機制
- **scan_and_replace_ads_immediately**：即掃即換不刷新頁面
- **完整狀態備份**：保存 `src`、`style`、`background-image` 等屬性
- **按鈕清理機制**：移除所有添加的 SVG 按鈕元素
- **iframe 可見性還原**：恢復 `display` 和 `visibility` 屬性

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

### 🛡️ nicklee 精確檢測邏輯
#### 外部網域過濾清單
```python
external_domains = [
    'facebook.com', 'fb.com', 'twitter.com', 'x.com', 't.co',
    'instagram.com', 'youtube.com', 'linkedin.com', 'pinterest.com',
    'google.com', 'gmail.com', 'yahoo.com', 'bing.com',
    'amazon.com', 'booking.com', 'agoda.com', 'expedia.com',
    'line.me', 'telegram.org', 'whatsapp.com', 'wechat.com'
]
```

#### URL 驗證模式
- **TVBS 網域檢查**：必須包含 `supertaste.tvbs.com.tw`
- **文章路徑驗證**：`/travel/123`, `/life/456`, `/article/`, `.html`
- **分享連結過濾**：排除 `utm_source`, `sharer.php`, `taboola`
- **媒體檔案排除**：`.jpg`, `.mp4`, `.pdf` 等檔案

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
📊 TVBS 廣告替換統計報告
====================================
📸 總截圖數量: 13 張
🔄 總替換次數: 13 次
   🎬 GIF 替換: 8 次 (61.5%)
   🖼️ 靜態圖片替換: 5 次 (38.5%)

📋 詳細替換記錄:
    1. 🎬 google_300x250.gif (300x250)
    2. 🖼️ google_728x90.jpg (728x90)
    3. 🎬 google_320x50.gif (320x50)
====================================
```

## 📝 重要注意事項

### ✅ 系統需求
1. **網路連線**：需要穩定的網路連接 TVBS 網站
2. **Google Chrome**：必須安裝最新版 Chrome 瀏覽器
3. **Python 環境**：Python 3.7+ 和相關依賴套件
4. **螢幕解析度**：建議 1920x1080 或更高解析度

### 🎬 GIF 功能需求
1. **圖片格式**：支援 `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
2. **命名規則**：必須遵循 `google_寬度x高度.副檔名` 格式
3. **檔案大小**：GIF 建議小於 5MB 以確保載入速度
4. **尺寸匹配**：圖片尺寸必須與網站廣告尺寸相符

### 🖥️ 多螢幕使用
1. **螢幕偵測**：程式會自動偵測所有可用螢幕
2. **手動選擇**：可以選擇要使用的螢幕編號
3. **全螢幕模式**：建議使用全螢幕以獲得最佳效果
4. **解析度適應**：支援不同解析度的螢幕

### 🛡️ 安全與隱私
1. **僅限 TVBS**：程式只會處理 supertaste.tvbs.com.tw
2. **無資料收集**：不會收集或傳送個人資料
3. **本地執行**：所有處理都在本地電腦進行
4. **優雅中斷**：支援 Ctrl+C 安全停止程式

### ⚠️ 使用限制
1. **網站結構變更**：TVBS 網站更新可能影響功能
2. **廣告載入時間**：懶載入廣告需要等待時間
3. **螢幕截圖權限**：某些系統可能需要螢幕錄製權限
4. **防毒軟體**：可能被誤判為自動化工具

## 📸 即掃即換截圖系統

### 🎨 截圖命名規則
採用 **即掃即換** 模式，每次廣告替換後立即截圖：
```
tvbs_replaced_[文章標題]_[時間戳].png
```

#### 實際截圖範例
```
tvbs_replaced_台北美食推薦_20240908_143022.png
tvbs_replaced_97白露習俗禁忌一覽_20240908_095049.png  
tvbs_replaced_拉亞漢堡不二家聯名_20240908_101530.png
tvbs_replaced_宜蘭旅遊景點推薦_20240908_143055.png
```

### 📊 即時統計更新系統
```python
def _update_screenshot_count(self, filepath, current_image_info, original_ad_info):
    """更新截圖統計並返回檔案路徑"""
    self.total_screenshots += 1
    self.total_replacements += 1
    
    # 檢查是否為 GIF 廣告
    if current_image_info and current_image_info.get('is_gif'):
        self.gif_replacements += 1
        print(f"📊 替換了 GIF 廣告")
    else:
        self.static_replacements += 1
```

#### 即時統計顯示
```
📊 總截圖數: 1
📊 總截圖數: 2  
📊 GIF 廣告數: 1
📊 總截圖數: 3
📊 總截圖數: 4
📊 GIF 廣告數: 2
```

### 🎬 GIF 替換記錄系統
```python
# 記錄詳細替換資訊
self.replacement_details.append({
    'filename': current_image_info['filename'],
    'size': f"{current_image_info['width']}x{current_image_info['height']}",
    'type': current_image_info['type'],  # "GIF" 或 "靜態圖片"
    'screenshot': filepath
})
```

### 📈 完整統計報告
程式結束時會顯示完整統計：
```
📊 TVBS 廣告替換統計報告
====================================
📸 總截圖數量: 13 張
🔄 總替換次數: 13 次
   🎬 GIF 替換: 8 次 (61.5%)
   🖼️ 靜態圖片替換: 5 次 (38.5%)

📋 詳細替換記錄:
    1. 🎬 google_300x250.gif (300x250) → 📸 tvbs_台北美食_20240908_143022.png
    2. 🖼️ google_728x90.jpg (728x90) → 📸 tvbs_旅遊景點_20240908_143055.png
    3. 🎬 google_320x50.gif (320x50) → 📸 tvbs_生活資訊_20240908_143128.png

⚙️ 當前 GIF 策略:
   🎯 優先級模式 - GIF 優先 (GIF_PRIORITY = True)
====================================
```

### 🔍 MSS 高效能截圖支援
```python
# 嘗試載入 MSS 截圖庫
try:
    import mss
    MSS_AVAILABLE = True
    print("MSS 截圖庫可用")
except ImportError:
    MSS_AVAILABLE = False
    print("MSS 截圖庫不可用，將使用 Selenium 截圖")
```

#### 截圖方法選擇
- **MSS 可用**：使用高效能 MSS 截圖（推薦）
- **MSS 不可用**：自動切換到 Selenium 截圖
- **跨平台支援**：Windows、macOS、Linux 全支援
- **全螢幕截圖**：支援多螢幕環境的全螢幕截圖

## 🔍 除錯與監控功能

### 📊 即時頁面分析
程式會自動分析頁面元素並顯示統計：
```
🔍 頁面元素尺寸分析:
找到 15 個可能的廣告元素
  300x250: 5 個元素 (iframe, div)
  728x90: 3 個元素 (div, img)  
  970x90: 2 個元素 (iframe)
  320x50: 1 個元素 (div)
```

### 🛡️ URL 過濾日誌
詳細記錄 URL 過濾過程：
```
🔍 URL 檢查過程:
  ✅ 有效 TVBS 文章連結: https://supertaste.tvbs.com.tw/travel/123...
  ❌ 過濾外部網站連結: facebook.com in https://www.facebook.com/share...
  ❌ 過濾分享連結: utm_source in https://supertaste.tvbs.com.tw/travel/123?utm_source...
```

### 🎬 GIF 載入監控
```
🎬 GIF 功能載入:
成功載入 gif_config.py 設定檔
SCREENSHOT_COUNT 設定: 10
NEWS_COUNT 設定: 20
GIF_PRIORITY 設定: True

📋 完整圖片清單:
1. 🎬 google_300x250.gif (300x250)
2. 🖼️ google_300x250.jpg (300x250)
3. 🎬 google_728x90.gif (728x90)
```

### 🖥️ 多螢幕偵測日誌
```
🖥️ 螢幕偵測結果:
偵測到的螢幕:
螢幕 1: 1920x1080 (主螢幕)
螢幕 2: 2560x1440
✅ Chrome 已移動到螢幕 2 並設為全螢幕
```

## 🍽️ TVBS 食尚玩家專門優化

### 🎯 目標網站深度整合
- **專業美食平台**：supertaste.tvbs.com.tw 專門優化
- **豐富內容類型**：美食、旅遊、生活、熱門四大分類
- **高品質內容**：專業攝影、詳細介紹、即時更新
- **廣告位置分析**：針對 TVBS 網站廣告版位特別優化

### 🔍 多輪智能文章搜尋系統
程式使用 **5輪搜尋 + 後備搜尋** 策略：

#### 第1-5輪：TVBS 特定選擇器
```python
link_selectors = [
    # TVBS 特定選擇器（首選）
    ".article__content > a.article__item[href]",
    "a.article__item[href]",
    "div.article__content a.article__item[href]",
    
    # TVBS 內容區域選擇器
    "a[href*='/article/'][href*='supertaste.tvbs.com.tw']",
    "a[href^='/article/']",
    "a[href*='/travel/']",
    "a[href*='/life/']",
    
    # TVBS 推薦和相關文章
    ".recommend-list a",
    ".related-articles a", 
    ".popular-articles a"
]
```

#### 後備搜尋：通用連結過濾
```python
# 當前5輪搜尋不足時啟動
all_links.extend(driver.find_elements(By.CSS_SELECTOR, "a.article__item[href]"))
all_links.extend(driver.find_elements(By.CSS_SELECTOR, "a[href^='/travel/']"))
all_links.extend(driver.find_elements(By.CSS_SELECTOR, "a[href]"))
```

### 🔄 滾動載入優化
每輪搜尋間會執行滾動載入：
```javascript
// 觸發懶載入的滾動策略
window.scrollTo(0, document.body.scrollHeight);  // 滾動到底部
window.scrollBy(0, -200);                        // 微調回滾
```

### 📊 文章連結統計
```
搜尋第 1/5 輪連結...
使用選擇器 1/9
  找到 12 個連結
  選擇器 1 結果: 8 個有效連結, 4 個無效連結

後備搜尋新增 3 個連結
找到 15 個新聞連結
隨機選擇 10 個連結
```

### 🛡️ TVBS 專用 URL 驗證
#### 必須符合的 URL 模式
```python
# TVBS 文章 URL 模式驗證
has_category_id = re.search(r'^/[a-z]+/\d+(?:/)?$', path)  # /travel/123
has_article_slug = ('/article/' in path) or ('/post/' in path)
has_html = path.endswith('.html')
```

#### 排除的分類頁面
```python
category_only_paths = ['/', '/travel', '/travel/', '/life', '/life/']
# 不接受純分類頁面，需要進到文章頁
```

### 🎯 廣告檢測優化
#### TVBS 特定廣告選擇器
```python
# 針對 TVBS 網站的廣告檢測
ad_selectors = [
    "iframe[src*='googlesyndication']",
    "div[id*='google_ads']", 
    "div[class*='ad-']",
    "div[data-ad-slot]",
    # TVBS 特定廣告容器
    ".advertisement",
    ".ad-container"
]
```

#### 精確尺寸匹配
- **完全匹配**：廣告尺寸必須完全符合替換圖片尺寸
- **無容差範圍**：不允許 ±2px 容差，確保精確替換
- **多重驗證**：檢查 `offsetWidth`、`offsetHeight`、`clientWidth`、`clientHeight`

---

## 🚀 快速開始指南

### **四步驟啟動流程：**
1. **準備 GIF 圖片**：在 `replace_image/` 放入 `.gif` 和 `.jpg` 檔案
2. **設定 GIF 策略**：修改 `gif_config.py` 中的 `GIF_PRIORITY = True`
3. **執行程式**：`python tvbs_replace.py`
4. **選擇螢幕**：從自動偵測的多螢幕中選擇最佳螢幕
5. **查看結果**：檢查 `screenshots/` 資料夾和完整統計報告

### **🎯 最佳實踐建議：**
- **混合圖片策略**：同一尺寸準備 GIF 和靜態兩個版本
- **GIF 優先模式**：`GIF_PRIORITY = True` 優先使用動態效果
- **多螢幕優勢**：選擇解析度較高的螢幕 (如 2560x1440)
- **網路穩定性**：確保網路連線穩定以提高文章搜尋成功率
- **即時監控**：觀察程式輸出了解 GIF vs 靜態替換比例

### **🎬 GIF 升級版亮點：**
- **智能混合替換**：根據 `GIF_PRIORITY` 自動選擇最佳圖片類型
- **即掃即換技術**：找到廣告立即替換並截圖，無需等待
- **ETtoday 風格還原**：完整保存和還原廣告原始狀態
- **詳細統計分析**：追蹤 GIF 使用比例和替換成功率
- **多螢幕全螢幕**：支援多螢幕環境的全螢幕操作

### **🍽️ TVBS 食尚玩家專門優化：**
- **5輪 + 後備搜尋**：確保找到足夠的美食旅遊文章
- **嚴格網域過濾**：只處理 supertaste.tvbs.com.tw 文章
- **6段式滾動載入**：觸發所有懶載入廣告完整載入
- **即時統計報告**：顯示 GIF vs 靜態圖片使用分析
- **安全中斷機制**：Ctrl+C 優雅停止，不損壞資料

### **⚡ 效能優化提示：**
- 使用 MSS 截圖庫可大幅提升截圖速度
- 選擇較少廣告的螢幕可減少干擾
- 關閉不必要的瀏覽器擴充功能
- 確保 `replace_image/` 資料夾圖片命名正確