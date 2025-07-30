# LiuLife 部落格廣告替換器使用手冊

## 🎯 程式簡介

LiuLife 部落格廣告替換器是一個專門針對 https://liulifejp.com 部落格的廣告替換工具。它能夠自動掃描頁面中的廣告，並用自定義圖片進行替換。

### 主要功能
- 🔍 自動掃描 LiuLife 部落格的廣告
- 🖼️ 用自定義圖片替換原始廣告
- 🎛️ 添加驚嘆號和叉叉按鈕
- 📸 自動截圖保存
- 🎯 專門處理部落格內容

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
chmod +x start_liulife.sh
```

## 🚀 使用方法

### 方法一：使用啟動腳本（推薦）
```bash
./start_liulife.sh
```

### 方法二：直接執行
```bash
python3 liulife_replace.py
```

## ⚙️ 設定說明

### config.py 主要設定
```python
SCREENSHOT_COUNT = 30          # 目標截圖數量
NEWS_COUNT = 20               # 每次處理的部落格文章數量
HEADLESS_MODE = False         # 無頭模式
FULLSCREEN_MODE = True        # 全螢幕模式
LIULIFE_BASE_URL = "https://liulifejp.com"  # 部落格網址
```

### 替換圖片命名規則
```
google_[寬度]x[高度].jpg
```
例如：`google_970x90.jpg`、`google_300x250.jpg`

## 📁 檔案結構
```
├── liulife_replace.py        # 主程式
├── config.py                 # 設定檔
├── start_liulife.sh         # 啟動腳本
├── replace_image/           # 替換圖片資料夾
├── screenshots/             # 截圖輸出資料夾
└── LiuLife使用手冊.md       # 本手冊
```

## ✨ 功能特色

### 1. 智能廣告識別
- 自動掃描符合標準廣告尺寸的元素
- 支援多種廣告尺寸（970x90、728x90、300x250 等）
- 精確匹配廣告元素

### 2. 精確按鈕定位
- 叉叉按鈕：右上角，與邊緣保持 1px 間距
- 驚嘆號按鈕：與叉叉保持 2px 間距
- 完全不透明的白色背景

### 3. 多種替換方式
- **圖片替換**：直接替換 `<img>` 標籤的 src
- **iframe 替換**：隱藏 iframe 並在相同位置顯示圖片
- **背景圖片替換**：替換元素的背景圖片

### 4. 部落格特化功能
- 智能識別部落格文章連結
- 適應部落格頁面載入時間
- 針對部落格內容優化掃描邏輯

## 🔧 故障排除

### 常見問題

#### 1. Chrome 瀏覽器無法啟動
**解決方案**：安裝 Google Chrome 瀏覽器

#### 2. 找不到部落格文章
**解決方案**：
- 檢查網路連線
- 確認 `https://liulifejp.com` 可正常訪問

#### 3. 找不到廣告位置
**解決方案**：
- 檢查 `replace_image` 資料夾中的圖片尺寸
- 確認圖片命名格式正確

#### 4. 按鈕顯示異常
**解決方案**：檢查 `config.py` 中的按鈕設定

#### 5. 截圖失敗
**解決方案**：
```bash
chmod 755 screenshots/
```

#### 6. 網路連線問題
**解決方案**：檢查網路連線和防火牆設定

### 錯誤代碼
| 錯誤 | 解決方案 |
|------|----------|
| `ModuleNotFoundError` | `pip3 install selenium` |
| `WebDriverException` | 更新 Chrome 瀏覽器 |
| `TimeoutException` | 檢查網路連線 |

## 🎨 按鈕樣式設定

### 可用樣式
- `dots` - 三個點的關閉按鈕
- `cross` - 叉叉關閉按鈕
- `adchoices` - AdChoices 樣式
- `adchoices_dots` - AdChoices + 點點樣式

### 修改按鈕樣式
```python
# 在 config.py 中修改
BUTTON_STYLE = "adchoices_dots"  # 改為你想要的樣式
```

## 📊 支援的廣告尺寸

### 標準廣告尺寸
- **橫幅廣告**: 728x90, 970x90, 980x120
- **矩形廣告**: 300x250, 336x280, 250x250
- **摩天大樓**: 120x600, 160x600, 300x600
- **行動廣告**: 320x50, 320x100, 300x50

## 📝 更新日誌

### 版本 1.0 (2025年)
- ✅ 支援 LiuLife 部落格
- ✅ 自動廣告掃描和替換
- ✅ 自定義按鈕功能
- ✅ 多平台截圖支援
- ✅ 部落格特化功能
- ✅ 優化按鈕定位

## 🔄 與其他版本的差異

### 與自由時報版本的差異
- 針對部落格結構優化
- 更長的頁面載入等待時間
- 部落格文章連結識別邏輯
- 截圖檔案命名為 `liulife_` 前綴

### 與 Yahoo 新聞版本的差異
- 簡化的廣告識別邏輯
- 適應部落格的內容結構
- 更靈活的連結獲取方式

## 💡 使用技巧

### 1. 提高成功率
- 確保網路連線穩定
- 使用較大尺寸的替換圖片
- 定期清理瀏覽器快取

### 2. 優化效能
- 減少 `NEWS_COUNT` 數量以加快處理速度
- 使用 `HEADLESS_MODE = True` 節省資源
- 定期重啟程式避免記憶體累積

### 3. 自定義設定
- 調整 `WAIT_TIME` 適應網路速度
- 修改 `SCREENSHOT_COUNT` 控制輸出數量
- 選擇合適的 `BUTTON_STYLE`

---

**版本**：1.0  
**目標網站**：https://liulifejp.com  
**作者**：AI Assistant  
**更新日期**：2025年1月