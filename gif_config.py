# ========================================
# GIF 廣告替換器專用設定檔
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
    # 可以繼續添加更多圖片和次數
}

# 找不到對應尺寸時的連續失敗次數限制
MAX_CONSECUTIVE_FAILURES = 3  # 連續失敗次數限制

# 網站設定
BASE_URL = "https://travel.ettoday.net"  # ETtoday 旅遊雲
NEWS_COUNT = 20             # 每次搜尋的新聞數量

# 目標廣告尺寸 (寬度x高度) - 實際上程式會根據 replace_image 資料夾中的圖片自動偵測尺寸
TARGET_AD_SIZES = [
    {"width": 120, "height": 600},   # google_120x600.jpg
    {"width": 160, "height": 600},   # google_160x600.jpg
    {"width": 200, "height": 200},   # google_200x200.gif
    {"width": 240, "height": 400},   # google_240x400.jpg
    {"width": 250, "height": 250},   # google_250x250.jpg/gif
    {"width": 300, "height": 50},    # google_300x50.jpg
    {"width": 300, "height": 250},   # google_300x250.jpg/gif
    {"width": 300, "height": 600},   # google_300x600.jpg
    {"width": 320, "height": 50},    # google_320x50.jpg/gif
    {"width": 320, "height": 100},   # google_320x100.jpg/gif
    {"width": 336, "height": 280},   # google_336x280.jpg/gif
    {"width": 728, "height": 90},    # google_728x90.jpg
    {"width": 970, "height": 90}     # google_970x90.jpg
]

# 按鈕設定
CLOSE_BUTTON_SIZE = {"width": 15, "height": 15}  # 關閉按鈕大小
INFO_BUTTON_SIZE = {"width": 15, "height": 15}   # 資訊按鈕大小 (與關閉按鈕一致)
INFO_BUTTON_COLOR = "#00aecd"                     # 資訊按鈕顏色 (Google藍)
INFO_BUTTON_OFFSET = 16                          # 資訊按鈕偏移量
BUTTON_TOP_OFFSET = 0                            # 按鈕上邊距偏移 (固定1px距離)

# 按鈕樣式設定 - 只需要修改這個變數即可切換樣式
BUTTON_STYLE = "dots"  # 可選: "dots" (驚嘆號+點點), "cross" (驚嘆號+叉叉), "adchoices" (AdChoices+叉叉), "adchoices_dots" (AdChoices+點點), "none" (無按鈕)

# 瀏覽器設定
HEADLESS_MODE = False       # 無頭模式 (True/False)
FULLSCREEN_MODE = True      # 全螢幕模式 (True/False)

# ========================================
# GIF 使用策略設定 (專用功能)
# ========================================

# 圖片選擇優先級 (主要設定)
GIF_PRIORITY = False         # True: 優先使用 GIF，沒有才用靜態圖片
                           # False: 優先使用靜態圖片，沒有才用 GIF

# 固定設定 (程式內部使用，不需修改)
RANDOM_SELECTION = False    # 固定使用優先級模式

# ========================================
# 說明：
# - 每種尺寸不一定都有 GIF 和靜態圖片兩種選擇
# - 優先選擇設定的類型，沒有時自動選擇另一種
# - 例如：GIF_PRIORITY = True 時
#   * 300x250 有 GIF 和靜態 → 選 GIF
#   * 728x90 只有靜態圖片 → 選靜態圖片
# ========================================

# 輸出設定
SCREENSHOT_FOLDER = "screenshots"  # 截圖資料夾名稱