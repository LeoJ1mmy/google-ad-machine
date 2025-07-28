# ========================================
# 廣告替換器設定檔
# ========================================

# 截圖設定
SCREENSHOT_COUNT = 30       # 要截圖的張數
MAX_ATTEMPTS = 50           # 最大嘗試次數
PAGE_LOAD_TIMEOUT = 15      # 頁面載入超時(秒)
WAIT_TIME = 3              # 等待時間(秒)

# 圖片設定
REPLACE_IMAGE_FOLDER = "replace_image"  # 替換圖片資料夾
DEFAULT_IMAGE = "mini.jpg"   # 預設圖片檔案名
MINI_IMAGE = "mini.jpg"      # 小尺寸圖片檔案名

# 每張圖片的使用次數設定
IMAGE_USAGE_COUNT = {
    "replace_image/google_120x600.jpg": 5,
    "replace_image/google_160x600.jpg": 5,
    "replace_image/google_240x400.jpg": 5,
    "replace_image/google_250x250.jpg": 5,
    "replace_image/google_300x50.jpg": 5,
    "replace_image/google_300x250.jpg": 5,
    "replace_image/google_300x600.jpg": 5,
    "replace_image/google_320x50.jpg": 5,
    "replace_image/google_320x100.jpg": 5,
    "replace_image/google_336x280.jpg": 5,
    "replace_image/google_728x90.jpg": 5,
    "replace_image/google_970x90.jpg": 5,
    "replace_image/google_980x120.jpg": 5,
  # 728x90 尺寸的圖片使用4次
    # 可以繼續添加更多圖片和次數
}

# 找不到對應尺寸時的連續失敗次數限制
MAX_CONSECUTIVE_FAILURES = 3  # 連續10次找不到對應尺寸就換下一張圖片

# 網站設定
BASE_URL = "https://playing.ltn.com.tw"  # 基礎網址 (自由時報)
YAHOO_BASE_URL = "https://tw.news.yahoo.com/fun/"  # Yahoo 新聞娛樂版面
NEWS_COUNT = 20             # 每次搜尋的新聞數量

# 目標廣告尺寸 (寬度x高度)
TARGET_AD_SIZES = [
    {"width": 970, "height": 90},
    {"width": 986, "height": 106},
    {"width": 728, "height": 90}
]

# Yahoo 新聞特定的廣告尺寸
YAHOO_TARGET_AD_SIZES = [
    {"width": 970, "height": 90},
    {"width": 728, "height": 90},
    {"width": 300, "height": 250},
    {"width": 320, "height": 50},
    {"width": 336, "height": 280}
]

# 按鈕設定
CLOSE_BUTTON_SIZE = {"width": 15, "height": 15}  # 關閉按鈕大小
INFO_BUTTON_SIZE = {"width": 15, "height": 15}   # 資訊按鈕大小 (與關閉按鈕一致)
INFO_BUTTON_COLOR = "#00aecd"                     # 資訊按鈕顏色 (Google藍)
INFO_BUTTON_OFFSET = 16                          # 資訊按鈕偏移量

# 瀏覽器設定
HEADLESS_MODE = False       # 無頭模式 (True/False)
FULLSCREEN_MODE = True      # 全螢幕模式 (True/False)

# 輸出設定
SCREENSHOT_FOLDER = "screenshots"  # 截圖資料夾名稱 