# Yahoo 新聞廣告替換器使用手冊 - GIF 升級版

## 🎯 程式簡介

Yahoo 新聞廣告替換器是一個專門針對 Yahoo 新聞熱門景點版面的廣告替換工具。它能夠自動掃描頁面中的廣告，並用自定義圖片進行替換，現已全面支援 GIF 動畫廣告！

### 主要功能
- 🔍 自動掃描 Yahoo 新聞熱門景點版面的廣告
- 🎬 **支援 GIF 動畫廣告替換**（新功能）
- 🖼️ 智能選擇靜態圖片或 GIF 動畫
- 🎛️ 添加驚嘆號和叉叉按鈕
- 📸 自動截圖保存（滑動到最佳位置）
- 🎯 專門處理旅遊相關新聞
- ⚙️ 使用 gif_config.py 統一設定檔

## 💻 系統需求

- **Python 3.7+**
- **Google Chrome 瀏覽器**
- **至少 4GB RAM**

## 📦 安裝步驟

### 1. 安裝 Python 套件
```bash
pip3 install selenium webdriver-manager
```

### 2. 設定替換圖片
```bash
# 確保 replace_image 資料夾包含圖片
mkdir -p replace_image
# 將替換圖片放入資料夾
```

### 3. 設定執行權限
```bash
chmod +x start_yahoo.sh
```

## 🚀 使用方法

### 方法一：使用啟動腳本（推薦）
```bash
./start_yahoo.sh
```

### 方法二：直接執行
```bash
python3 yahoo_replace.py
```

## ⚙️ 設定說明

### gif_config.py 主要設定（新版統一設定檔）
```python
SCREENSHOT_COUNT = 30          # 目標截圖數量
NEWS_COUNT = 20               # 每次處理的新聞數量
HEADLESS_MODE = False         # 無頭模式
FULLSCREEN_MODE = True        # 全螢幕模式
GIF_PRIORITY = True           # GIF 優先模式（新功能）
IMAGE_USAGE_COUNT = {}        # 圖片使用次數統計
```

### 替換圖片命名規則（支援 GIF）
```
google_[寬度]x[高度].jpg     # 靜態圖片
google_[寬度]x[高度].gif     # GIF 動畫（新支援）
```
例如：
- `google_970x90.jpg` / `google_970x90.gif`
- `google_300x250.jpg` / `google_300x250.gif`

### GIF 優先級策略
- **GIF_PRIORITY = True**：優先使用 GIF 動畫
- **GIF_PRIORITY = False**：優先使用靜態圖片
- 如果只有一種類型，自動選擇可用的圖片

## 📁 檔案結構
```
├── yahoo_replace.py          # 主程式（GIF 升級版）
├── gif_config.py            # 統一設定檔（新版）
├── config.py                # 舊版設定檔（備用）
├── start_yahoo.sh           # 啟動腳本
├── replace_image/           # 替換圖片資料夾（支援 GIF）
│   ├── google_300x250.jpg   # 靜態圖片
│   ├── google_300x250.gif   # GIF 動畫
│   └── ...
├── screenshots/             # 截圖輸出資料夾
└── Yahoo廣告替換器使用手冊.md  # 本手冊
```

## ✨ 功能特色

### 1. 智能廣告識別
- 自動掃描符合標準廣告尺寸的元素
- 支援多種廣告尺寸（970x90、728x90、300x250 等）
- 允許 10 像素的尺寸容差

### 2. GIF 動畫支援（新功能）
- **智能圖片選擇**：根據 GIF_PRIORITY 設定自動選擇
- **GIF 優先模式**：優先使用動畫廣告，提升視覺效果
- **靜態備用**：當 GIF 不可用時自動使用靜態圖片
- **使用統計**：詳細記錄 GIF 和靜態圖片的使用次數

### 3. 精確按鈕定位
- 叉叉按鈕：右上角，與邊緣保持 1px 間距
- 驚嘆號按鈕：與叉叉保持 17px 間距
- 完全不透明的白色背景

### 4. 多種替換方式
- **圖片替換**：直接替換 `<img>` 標籤的 src（支援 GIF）
- **iframe 替換**：隱藏 iframe 並在相同位置顯示圖片
- **背景圖片替換**：替換元素的背景圖片

### 5. 智能截圖定位
- **自動滑動**：讓廣告按鈕出現在螢幕上 25% 位置
- **最佳視角**：確保截圖效果最佳
- **即時還原**：截圖後立即還原廣告

## 🔧 故障排除

### 常見問題

#### 1. Chrome 瀏覽器無法啟動
**解決方案**：安裝 Google Chrome 瀏覽器

#### 2. 找不到廣告位置
**解決方案**：
- 檢查 `replace_image` 資料夾中的圖片尺寸
- 確認圖片命名格式正確

#### 3. 按鈕顯示異常
**解決方案**：檢查 `config.py` 中的按鈕設定

#### 4. 截圖失敗
**解決方案**：
```bash
chmod 755 screenshots/
```

#### 5. 網路連線問題
**解決方案**：檢查網路連線和防火牆設定

### 錯誤代碼
| 錯誤 | 解決方案 |
|------|----------|
| `ModuleNotFoundError` | `pip3 install selenium` |
| `WebDriverException` | 更新 Chrome 瀏覽器 |
| `TimeoutException` | 檢查網路連線 |

## 📝 更新日誌

### 版本 2.0 - GIF 升級版 (2025年)
- 🎬 **新增 GIF 動畫廣告支援**
- ⚙️ **整合 gif_config.py 統一設定檔**
- 🎯 **智能圖片選擇策略**
- 📊 **詳細的 GIF/靜態圖片使用統計**
- 📍 **智能截圖定位（25% 螢幕位置）**
- 🔄 **即時廣告還原機制**
- 🛡️ **避免 stale element 問題**

### 版本 1.0 (2025年)
- ✅ 支援 Yahoo 新聞熱門景點版面
- ✅ 自動廣告掃描和替換
- ✅ 自定義按鈕功能
- ✅ 多平台截圖支援
- ✅ 簡化廣告識別邏輯
- ✅ 優化按鈕定位

---

**版本**：2.0 - GIF 升級版  
**作者**：AI Assistant 