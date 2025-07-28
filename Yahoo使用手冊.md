# Yahoo 新聞廣告替換器使用手冊

## 🎯 程式簡介

Yahoo 新聞廣告替換器是一個專門針對 Yahoo 新聞熱門景點版面的廣告替換工具。它能夠自動掃描頁面中的廣告，並用自定義圖片進行替換。

### 主要功能
- 🔍 自動掃描 Yahoo 新聞熱門景點版面的廣告
- 🖼️ 用自定義圖片替換原始廣告
- 🎛️ 添加驚嘆號和叉叉按鈕
- 📸 自動截圖保存
- 🎯 專門處理旅遊相關新聞

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

### config.py 主要設定
```python
SCREENSHOT_COUNT = 30          # 目標截圖數量
NEWS_COUNT = 20               # 每次處理的新聞數量
HEADLESS_MODE = False         # 無頭模式
FULLSCREEN_MODE = True        # 全螢幕模式
```

### 替換圖片命名規則
```
google_[寬度]x[高度].jpg
```
例如：`google_970x90.jpg`、`google_300x250.jpg`

## 📁 檔案結構
```
├── yahoo_replace.py          # 主程式
├── config.py                 # 設定檔
├── start_yahoo.sh           # 啟動腳本
├── replace_image/           # 替換圖片資料夾
├── screenshots/             # 截圖輸出資料夾
└── Yahoo廣告替換器使用手冊.md  # 本手冊
```

## ✨ 功能特色

### 1. 智能廣告識別
- 自動掃描符合標準廣告尺寸的元素
- 支援多種廣告尺寸（970x90、728x90、300x250 等）
- 允許 5 像素的尺寸容差

### 2. 精確按鈕定位
- 叉叉按鈕：右上角，與邊緣保持 1px 間距
- 驚嘆號按鈕：與叉叉保持 2px 間距
- 完全不透明的白色背景

### 3. 多種替換方式
- **圖片替換**：直接替換 `<img>` 標籤的 src
- **iframe 替換**：隱藏 iframe 並在相同位置顯示圖片
- **背景圖片替換**：替換元素的背景圖片

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

### 版本 1.0 (2025年)
- ✅ 支援 Yahoo 新聞熱門景點版面
- ✅ 自動廣告掃描和替換
- ✅ 自定義按鈕功能
- ✅ 多平台截圖支援
- ✅ 簡化廣告識別邏輯
- ✅ 優化按鈕定位

---

**版本**：1.0  
**作者**：AI Assistant 