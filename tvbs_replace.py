#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import os
import base64
import random
import re
import platform
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from urllib.parse import urlparse

# 載入設定檔
try:
    from config import *
    print("成功載入 config.py 設定檔")
    print(f"SCREENSHOT_COUNT 設定: {SCREENSHOT_COUNT}")
    print(f"NEWS_COUNT 設定: {NEWS_COUNT}")
    print(f"IMAGE_USAGE_COUNT 設定: {IMAGE_USAGE_COUNT}")
except ImportError:
    print("找不到 config.py，使用預設設定")
    # 預設設定
    SCREENSHOT_COUNT = 10
    MAX_ATTEMPTS = 50
    PAGE_LOAD_TIMEOUT = 15
    WAIT_TIME = 3
    REPLACE_IMAGE_FOLDER = "replace_image"
    DEFAULT_IMAGE = "mini.jpg"
    MINI_IMAGE = "mini.jpg"
    BASE_URL = "https://supertaste.tvbs.com.tw"
    NEWS_COUNT = 20
    TARGET_AD_SIZES = [{"width": 970, "height": 90}, {"width": 986, "height": 106}]
    IMAGE_USAGE_COUNT = {"google_970x90.jpg": 5, "google_986x106.jpg": 3}
    MAX_CONSECUTIVE_FAILURES = 10
    CLOSE_BUTTON_SIZE = {"width": 15, "height": 15}
    INFO_BUTTON_SIZE = {"width": 15, "height": 15}
    INFO_BUTTON_COLOR = "#00aecd"
    INFO_BUTTON_OFFSET = 16
    HEADLESS_MODE = False
    FULLSCREEN_MODE = True
    SCREENSHOT_FOLDER = "screenshots"

class ScreenManager:
    """螢幕管理器，用於偵測和管理多螢幕"""
    
    @staticmethod
    def detect_screens():
        """偵測可用的螢幕數量和資訊"""
        system = platform.system()
        screens = []
        
        try:
            if system == "Darwin":  # macOS
                # 使用 system_profiler 獲取顯示器資訊
                cmd = "system_profiler SPDisplaysDataType | grep -A 2 'Resolution:'"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    screen_count = 0
                    for line in lines:
                        if 'Resolution:' in line:
                            screen_count += 1
                            resolution = line.split('Resolution:')[1].strip()
                            screens.append({
                                'id': screen_count,
                                'resolution': resolution,
                                'primary': screen_count == 1
                            })
                
                # 如果無法獲取詳細資訊，使用 AppleScript 獲取螢幕數量
                if not screens:
                    applescript = '''
                    tell application "Finder"
                        set screenCount to count of desktop
                        return screenCount
                    end tell
                    '''
                    result = subprocess.run(['osascript', '-e', applescript], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        screen_count = int(result.stdout.strip())
                        for i in range(1, screen_count + 1):
                            screens.append({
                                'id': i,
                                'resolution': 'Unknown',
                                'primary': i == 1
                            })
                
            elif system == "Windows":
                # Windows 多種方法偵測螢幕
                try:
                    # 方法1: 使用 PowerShell 獲取螢幕資訊
                    powershell_cmd = '''
                    Add-Type -AssemblyName System.Windows.Forms
                    [System.Windows.Forms.Screen]::AllScreens | ForEach-Object {
                        Write-Output "$($_.Bounds.Width)x$($_.Bounds.Height):$($_.Primary)"
                    }
                    '''
                    result = subprocess.run(['powershell', '-Command', powershell_cmd], 
                                          capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        screen_id = 1
                        for line in lines:
                            if 'x' in line and ':' in line:
                                resolution, is_primary = line.strip().split(':')
                                screens.append({
                                    'id': screen_id,
                                    'resolution': resolution,
                                    'primary': is_primary.lower() == 'true'
                                })
                                screen_id += 1
                except Exception as e:
                    print(f"PowerShell 方法失敗: {e}")
                
                # 方法2: 如果 PowerShell 失敗，使用 wmic
                if not screens:
                    try:
                        cmd = 'wmic path Win32_VideoController get CurrentHorizontalResolution,CurrentVerticalResolution /format:csv'
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                        
                        if result.returncode == 0:
                            lines = result.stdout.strip().split('\n')
                            screen_id = 1
                            for line in lines[1:]:  # 跳過標題行
                                if line.strip() and ',' in line:
                                    parts = line.split(',')
                                    if len(parts) >= 3:
                                        width = parts[1].strip()
                                        height = parts[2].strip()
                                        if width and height and width != 'NULL' and width.isdigit():
                                            screens.append({
                                                'id': screen_id,
                                                'resolution': f"{width}x{height}",
                                                'primary': screen_id == 1
                                            })
                                            screen_id += 1
                    except Exception as e:
                        print(f"wmic 方法失敗: {e}")
                
                # 方法3: 使用 Python 的 tkinter 作為備用
                if not screens:
                    try:
                        import tkinter as tk
                        root = tk.Tk()
                        width = root.winfo_screenwidth()
                        height = root.winfo_screenheight()
                        screens.append({
                            'id': 1,
                            'resolution': f"{width}x{height}",
                            'primary': True
                        })
                        root.destroy()
                    except Exception as e:
                        print(f"tkinter 方法失敗: {e}")
                
            else:  # Linux
                # Linux 使用 xrandr
                try:
                    result = subprocess.run(['xrandr'], capture_output=True, text=True)
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        screen_id = 1
                        for line in lines:
                            if ' connected' in line:
                                parts = line.split()
                                if len(parts) >= 3:
                                    resolution = parts[2] if 'x' in parts[2] else 'Unknown'
                                    screens.append({
                                        'id': screen_id,
                                        'resolution': resolution,
                                        'primary': 'primary' in line
                                    })
                                    screen_id += 1
                except FileNotFoundError:
                    print("xrandr 命令未找到，無法偵測螢幕")
            
            # 如果無法偵測到螢幕，至少返回一個預設螢幕
            if not screens:
                screens.append({
                    'id': 1,
                    'resolution': 'Unknown',
                    'primary': True
                })
                
        except Exception as e:
            print(f"偵測螢幕時發生錯誤: {e}")
            screens.append({
                'id': 1,
                'resolution': 'Unknown',
                'primary': True
            })
        
        return screens
    
    @staticmethod
    def select_screen():
        """讓使用者選擇要使用的螢幕"""
        screens = ScreenManager.detect_screens()
        
        print("\n" + "="*50)
        print("偵測到的螢幕:")
        print("="*50)
        
        for screen in screens:
            primary_text = " (主螢幕)" if screen['primary'] else ""
            print(f"螢幕 {screen['id']}: {screen['resolution']}{primary_text}")
        
        print("="*50)
        
        # 如果只有一個螢幕，自動選擇
        if len(screens) == 1:
            print("只偵測到一個螢幕，自動選擇螢幕 1")
            return 1, screens[0]
        
        while True:
            try:
                choice = input(f"請選擇要使用的螢幕 (1-{len(screens)}) [預設: 1]: ").strip()
                
                # 如果使用者直接按 Enter，使用預設值 1
                if not choice:
                    choice = "1"
                
                screen_id = int(choice)
                
                if 1 <= screen_id <= len(screens):
                    selected_screen = next(s for s in screens if s['id'] == screen_id)
                    print(f"✅ 已選擇螢幕 {screen_id}: {selected_screen['resolution']}")
                    return screen_id, selected_screen
                else:
                    print(f"❌ 請輸入 1 到 {len(screens)} 之間的數字")
                    
            except ValueError:
                print("❌ 請輸入有效的數字")
            except KeyboardInterrupt:
                print("\n程式已取消")
                return None, None
    
    @staticmethod
    def get_screen_info(screen_id):
        """獲取指定螢幕的詳細資訊"""
        screens = ScreenManager.detect_screens()
        for screen in screens:
            if screen['id'] == screen_id:
                return screen
        return None

class TvbsAdReplacer:
    """
    多網站廣告替換器
    支援 TVBS 食尚玩家 (supertaste.tvbs.com.tw) 和 nicklee.tw 網站
    """
    def __init__(self, headless=False, screen_id=1):
        self.screen_id = screen_id
        self.setup_driver(headless)
        self.load_replace_images()
        
    def setup_driver(self, headless):
        chrome_options = Options()
        if headless or HEADLESS_MODE:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # 多螢幕支援 - 計算螢幕偏移量
        if self.screen_id > 1:
            screen_offset = (self.screen_id - 1) * 1920
            chrome_options.add_argument(f'--window-position={screen_offset},0')
        
        # 默認全螢幕設定
        chrome_options.add_argument('--start-maximized')
        if not headless:
            chrome_options.add_argument('--start-fullscreen')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # 確保瀏覽器在正確的螢幕上並全螢幕
        if not headless:
            self.move_to_screen()
    
    def move_to_screen(self):
        """將瀏覽器移動到指定螢幕並設為全螢幕"""
        try:
            # 多螢幕位置調整
            if self.screen_id > 1:
                screen_offset = (self.screen_id - 1) * 1920
                self.driver.set_window_position(screen_offset, 0)
            
            # 等待視窗移動完成後設為全螢幕
            time.sleep(1)
            self.driver.fullscreen_window()
            print(f"✅ Chrome 已移動到螢幕 {self.screen_id} 並設為全螢幕")
            
        except Exception as e:
            print(f"移動瀏覽器到螢幕 {self.screen_id} 失敗: {e}")
            # 即使移動失敗，也嘗試設為全螢幕
            try:
                self.driver.fullscreen_window()
                print("✅ 已設為全螢幕模式")
            except:
                print("將使用預設螢幕位置")
    
    def load_replace_images(self):
        """載入替換圖片並解析尺寸"""
        self.replace_images = []
        
        if not os.path.exists(REPLACE_IMAGE_FOLDER):
            print(f"找不到替換圖片資料夾: {REPLACE_IMAGE_FOLDER}")
            return
        
        print(f"開始載入 {REPLACE_IMAGE_FOLDER} 資料夾中的圖片...")
        
        for filename in os.listdir(REPLACE_IMAGE_FOLDER):
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                # 解析檔案名中的尺寸
                size_match = re.search(r'google_(\d+)x(\d+)', filename)
                if size_match:
                    width = int(size_match.group(1))
                    height = int(size_match.group(2))
                    
                    image_path = os.path.join(REPLACE_IMAGE_FOLDER, filename)
                    self.replace_images.append({
                        'path': image_path,
                        'filename': filename,
                        'width': width,
                        'height': height
                    })
                    print(f"載入圖片: {filename} ({width}x{height})")
                else:
                    print(f"跳過不符合命名規則的圖片: {filename}")
        
        # 按檔案名排序
        self.replace_images.sort(key=lambda x: x['filename'])
        print(f"總共載入 {len(self.replace_images)} 張替換圖片")
        
        # 顯示載入的圖片清單
        for i, img in enumerate(self.replace_images):
            print(f"  {i+1}. {img['filename']} ({img['width']}x{img['height']})")
    
    def load_image_base64(self, image_path):
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"找不到圖片: {image_path}")
            
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def _is_valid_nicklee_url(self, url):
        """檢查是否為有效的 nicklee.tw 文章 URL，嚴格過濾外部連結"""
        if not url:
            return False
        
        # 絕對不能包含外部域名，即使 URL 參數中有 nicklee.tw
        external_domains = [
            'facebook.com', 'fb.com', 'twitter.com', 'x.com', 't.co',
            'instagram.com', 'youtube.com', 'linkedin.com', 'pinterest.com',
            'google.com', 'gmail.com', 'yahoo.com', 'bing.com',
            'amazon.com', 'booking.com', 'agoda.com', 'expedia.com',
            'line.me', 'telegram.org', 'whatsapp.com', 'wechat.com',
            'apple.com', 'microsoft.com', 'adobe.com'
        ]
        
        # 檢查是否包含外部域名 - 這是最重要的檢查
        url_lower = url.lower()
        for domain in external_domains:
            if domain in url_lower:
                print(f"    ❌ 過濾外部網站連結: {domain} in {url[:60]}...")
                return False
        
        # 必須以 https://nicklee.tw 開頭，排除所有外部網站
        if not url.startswith('https://nicklee.tw'):
            print(f"    ❌ 非 nicklee.tw 域名: {url[:60]}...")
            return False
        
        # 排除分享連結模式
        share_patterns = ['sharer.php', 'share?', '/share/', 'utm_source', 'utm_medium']
        for pattern in share_patterns:
            if pattern in url_lower:
                print(f"    ❌ 過濾分享連結: {pattern} in {url[:60]}...")
                return False
        
        # 排除的 URL 模式
        excluded_patterns = [
            '#', 'javascript:', 'mailto:', 'tel:', 'sms:', 'ftp:',
            '/category/', '/tag/', '/author/', '/wp-admin', '/wp-content',
            '/wp-includes', '/feed', '.xml', '.rss', '.json',
            '/login', '/register', '/admin', '/dashboard',
            '/search', '/archive', '/sitemap'
        ]
        
        # 檢查排除模式
        for pattern in excluded_patterns:
            if pattern in url_lower:
                return False
        
        # 排除圖片和媒體檔案
        media_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', 
                           '.mp4', '.mp3', '.pdf', '.zip', '.rar']
        for ext in media_extensions:
            if url_lower.endswith(ext):
                return False
        
        # 檢查是否為文章 URL（包含數字ID、年份等）
        article_patterns = ['/20', '/19', '/post-', '/article-', '/?p=']
        has_article_pattern = any(pattern in url for pattern in article_patterns)
        has_numeric_id = re.search(r'/\d+/', url)
        
        # 必須符合文章 URL 模式
        if has_article_pattern or has_numeric_id:
            print(f"    ✅ 有效文章連結: {url[:60]}...")
            return True
        else:
            print(f"    ❌ 不符合文章 URL 模式: {url[:60]}...")
            return False
    
    def _is_valid_tvbs_url(self, url):
        """檢查是否為有效的 TVBS 文章 URL"""
        if not url:
            return False
        
        # 必須是 TVBS 域名
        if 'supertaste.tvbs.com.tw' not in url:
            return False
        
        url_lower = url.lower()
        parsed = urlparse(url_lower)
        path = parsed.path or ''
        
        # 排除明顯的廣告/推薦容器（taboola 等）與非內容頁
        excluded_keywords = ['taboola', 'utm_', 'sharer.php', 'share?', '/share/']
        if any(kw in url_lower for kw in excluded_keywords):
            return False

        # 不接受純分類頁（避免只進到列表）
        category_only_paths = ['/', '/travel', '/travel/', '/life', '/life/']
        if path in category_only_paths:
            return False

        # 內容頁規則（符合其一即可）：
        # 1) /travel/<數字>
        # 2) /life/<數字>
        # 3) 含 /article/ 或 /post/
        # 4) 結尾為 .html
        import re
        is_travel_id = re.search(r'^/travel/\d+(?:/)?$', path) is not None
        is_life_id = re.search(r'^/life/\d+(?:/)?$', path) is not None
        has_article_slug = ('/article/' in path) or ('/post/' in path)
        has_html = path.endswith('.html')
        
        return is_travel_id or is_life_id or has_article_slug or has_html

    def get_random_news_urls(self, base_url, count=5):
        try:
            self.driver.get(base_url)
            time.sleep(WAIT_TIME)
            # 追加等待與懶載入觸發
            try:
                state = self.driver.execute_script("return document.readyState;")
                print(f"頁面 readyState: {state}")
            except Exception:
                pass
            # 初步觸發懶載入
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(1.5)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
            except Exception:
                pass
            
            # 根據網站類型選擇不同的選擇器，嚴格避免社交媒體分享按鈕
            if 'nicklee.tw' in base_url:
                # Nicklee.tw 網站的文章連結選擇器 - 只選擇特定區域的連結，明確排除社交媒體分享區域
                link_selectors = [
                    "ul.blog-grid li article h2.post-title a",                              # 文章標題連結
                    "ul.blog-grid li article .post-media a:not(.facebook-share):not(.twitter-share)",  # 圖片連結（排除分享按鈕）
                    "ul.blog-grid li article .read-more a",                                 # "繼續閱讀"連結
                    ".blog-post h2.post-title a",                                           # 備用：標題連結
                    ".blog-post .post-media a:not(.facebook-share):not(.twitter-share)"    # 備用：圖片連結（排除分享按鈕）
                ]
            else:
                # TVBS 食尚玩家的文章連結選擇器（擴充與備援），特別處理 .article__content 區塊與 a.article__item
                link_selectors = [
                    # 首選：分類頁（旅行）中的內容卡片
                    ".article__content > a.article__item[href]",
                    "a.article__item[href]",
                    "div.article__content a.article__item[href]",
                    # 以內容頁為優先
                    "a[href*='/article/'][href*='supertaste.tvbs.com.tw']",
                    "a[href^='/article/']",
                    # 旅行/生活列表含與不含 .html 的情況
                    "a[href*='/travel/']",
                    "a[href*='/life/']",
                    # 其他常見位置
                    "article a[href]",
                    "h3 a[href]",
                    ".article__item a[href]",
                    "a[href*='supertaste.tvbs.com.tw']",
                ]
            
            news_urls = []

            # 多輪收集：邊滾動邊收集，直到達到 count 或達到最大輪數
            max_rounds = 5
            for round_idx in range(1, max_rounds + 1):
                print(f"開始第 {round_idx}/{max_rounds} 輪連結收集…")
                for i, selector in enumerate(link_selectors, 1):
                    print(f"使用選擇器 {i}/{len(link_selectors)}")
                    links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"  找到 {len(links)} 個連結")
                    
                    valid_count = 0
                    invalid_count = 0
                    for link in links:
                        href = link.get_attribute('href')
                        if not href:
                            continue
                        # 確保是完整的 URL
                        if href.startswith('/'):
                            full_url = base_url.rstrip('/') + href
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            full_url = base_url.rstrip('/') + '/' + href.lstrip('./')
                        
                        # 根據網站類型過濾連結
                        if 'nicklee.tw' in base_url:
                            if self._is_valid_nicklee_url(full_url) and full_url not in news_urls:
                                news_urls.append(full_url)
                                valid_count += 1
                            else:
                                invalid_count += 1
                        else:
                            # 只收集 TVBS 的文章連結，排除廣告和其他連結
                            if self._is_valid_tvbs_url(full_url) and full_url not in news_urls:
                                news_urls.append(full_url)
                                valid_count += 1
                            else:
                                invalid_count += 1
                    print(f"  選擇器 {i} 結果: {valid_count} 個有效連結, {invalid_count} 個無效連結")

                # 若已足夠則跳出
                if len(news_urls) >= count:
                    break

                # 滾動更多讓頁面載入更多卡片
                try:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    self.driver.execute_script("window.scrollBy(0, -200);")
                    time.sleep(1)
                except Exception:
                    pass
            
            # 去除重複的 URL
            news_urls = list(set(news_urls))
            
            # 後備：若仍不足，掃描所有 a[href] 進行語意過濾，特別針對 /travel/ 與 a.article__item
            if len(news_urls) < count:
                try:
                    print("啟用後備掃描 a[href] ...")
                    all_links = []
                    # 以 a.article__item 優先
                    all_links.extend(self.driver.find_elements(By.CSS_SELECTOR, "a.article__item[href]"))
                    # 旅行列表連結
                    all_links.extend(self.driver.find_elements(By.CSS_SELECTOR, "a[href^='/travel/']"))
                    # 一般備援
                    all_links.extend(self.driver.find_elements(By.CSS_SELECTOR, "a[href]"))
                    added = 0
                    for a in all_links:
                        href = a.get_attribute('href')
                        if not href:
                            continue
                        # 相對路徑轉完整
                        if href.startswith('/'):
                            full_url = base_url.rstrip('/') + href
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            full_url = base_url.rstrip('/') + '/' + href.lstrip('./')
                        # 僅保留 TVBS 域名且為文章/旅遊/生活頁面
                        if self._is_valid_tvbs_url(full_url) and full_url not in news_urls:
                            news_urls.append(full_url)
                            added += 1
                    print(f"後備掃描新增 {added} 筆")
                except Exception as e:
                    print(f"後備掃描失敗: {e}")

            # 再次去重
            news_urls = list(dict.fromkeys(news_urls))

            print(f"找到 {len(news_urls)} 個新聞連結")
            if news_urls:
                selected_urls = random.sample(news_urls, min(count, len(news_urls)))
                print(f"隨機選擇了 {len(selected_urls)} 個連結:")
                for i, url in enumerate(selected_urls):
                    print(f"  {i+1}. {url}")
                return selected_urls
            else:
                print("未找到任何新聞連結")
                print("可能的原因:")
                if 'nicklee.tw' in base_url:
                    print("  1. nicklee.tw 網站結構可能已變更")
                    print("  2. 網頁載入不完整，請檢查網路連線")
                    print("  3. CSS 選擇器需要更新")
                else:
                    print("  1. TVBS 網站結構可能已變更")
                    print("  2. 網頁載入不完整，請檢查網路連線")
                return []
                        
        except Exception as e:
            print(f"獲取新聞連結失敗: {e}")
            return []
    
    def scan_entire_page_for_ads(self, target_width, target_height):
        """掃描整個網頁尋找符合尺寸的廣告元素 - 完全複製 ad_replacer.py 的邏輯"""
        print(f"開始掃描整個網頁尋找 {target_width}x{target_height} 的廣告...")
        
        # 先顯示所有符合尺寸的元素（調試用）
        all_matching_elements = self.driver.execute_script("""
            var targetWidth = arguments[0];
            var targetHeight = arguments[1];
            var matchingElements = [];
            var allElements = document.querySelectorAll('*');
            
            for (var i = 0; i < allElements.length; i++) {
                var element = allElements[i];
                var rect = element.getBoundingClientRect();
                var width = Math.round(rect.width);
                var height = Math.round(rect.height);
                
                if (width === targetWidth && height === targetHeight && 
                    rect.width > 0 && rect.height > 0) {
                    matchingElements.push({
                        tagName: element.tagName.toLowerCase(),
                        className: element.className || '',
                        id: element.id || '',
                        width: width,
                        height: height
                    });
                }
            }
            return matchingElements;
        """, target_width, target_height)
        
        print(f"找到 {len(all_matching_elements)} 個符合 {target_width}x{target_height} 尺寸的元素:")
        for elem in all_matching_elements[:10]:  # 只顯示前10個
            print(f"  <{elem['tagName']} class='{elem['className'][:30]}' id='{elem['id'][:20]}'> {elem['width']}x{elem['height']}")
        
        # 獲取所有可見的元素
        all_elements = self.driver.execute_script("""
            function getAllVisibleElements() {
                var all = [];
                var walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_ELEMENT,
                    {
                        acceptNode: function(node) {
                            // 只接受可見的元素
                            var style = window.getComputedStyle(node);
                            if (style.display === 'none' || 
                                style.visibility === 'hidden' || 
                                style.opacity === '0') {
                                return NodeFilter.FILTER_REJECT;
                            }
                            return NodeFilter.FILTER_ACCEPT;
                        }
                    }
                );
                
                var node;
                while (node = walker.nextNode()) {
                    all.push(node);
                }
                return all;
            }
            return getAllVisibleElements();
        """)
        
        print(f"找到 {len(all_elements)} 個可見元素，開始檢查尺寸...")
        
        matching_elements = []
        
        for i, element in enumerate(all_elements):
            try:
                # 檢查元素尺寸
                size_info = self.driver.execute_script("""
                    var element = arguments[0];
                    var rect = element.getBoundingClientRect();
                    return {
                        width: Math.round(rect.width),
                        height: Math.round(rect.height),
                        top: rect.top,
                        left: rect.left,
                        visible: rect.width > 0 && rect.height > 0
                    };
                """, element)
                
                # 完全複製 ad_replacer.py 的精確尺寸匹配邏輯
                if (size_info and 
                    size_info['visible'] and
                    size_info['width'] == target_width and 
                    size_info['height'] == target_height):
                    
                    # 完全複製 ad_replacer.py 的廣告檢測邏輯
                    is_ad = self.driver.execute_script("""
                        var element = arguments[0];
                        var tagName = element.tagName.toLowerCase();
                        var className = element.className || '';
                        var id = element.id || '';
                        var src = element.src || '';
                        
                        // 檢查是否包含廣告相關的關鍵字
                        var adKeywords = ['ad', 'advertisement', 'banner', 'google', 'ads', 'ad-', '-ad'];
                        var hasAdKeyword = adKeywords.some(function(keyword) {
                            return className.toLowerCase().includes(keyword) ||
                                   id.toLowerCase().includes(keyword) ||
                                   src.toLowerCase().includes(keyword);
                        });
                        
                        // 檢查是否為圖片、iframe 或 div
                        var isImageElement = tagName === 'img' || tagName === 'iframe' || tagName === 'div';
                        
                        // 檢查是否有背景圖片
                        var style = window.getComputedStyle(element);
                        var hasBackgroundImage = style.backgroundImage && style.backgroundImage !== 'none';
                        
                        return hasAdKeyword || isImageElement || hasBackgroundImage;
                    """, element)
                    
                    if is_ad:
                        matching_elements.append({
                            'element': element,
                            'width': size_info['width'],
                            'height': size_info['height'],
                            'position': f"top:{size_info['top']:.0f}, left:{size_info['left']:.0f}"
                        })
                        print(f"找到符合尺寸的廣告元素: {size_info['width']}x{size_info['height']} at {size_info['top']:.0f},{size_info['left']:.0f}")
                
                # 每檢查100個元素顯示進度
                if (i + 1) % 100 == 0:
                    print(f"已檢查 {i + 1}/{len(all_elements)} 個元素...")
                    
            except Exception as e:
                continue
        
        print(f"掃描完成，找到 {len(matching_elements)} 個符合尺寸的廣告元素")
        return matching_elements
    
    def get_button_style(self):
        """根據配置返回按鈕樣式 - 完全複製 ad_replacer.py 的邏輯"""
        button_style = getattr(self, 'button_style', BUTTON_STYLE)
        
        # 簡化的按鈕樣式，避免複雜的 SVG 造成 JavaScript 錯誤
        button_styles = {
            "dots": {
                "close_button": {
                    "html": '⋮',  # 使用 Unicode 字符代替 SVG
                    "style": 'position:absolute;top:1px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;text-align:center;line-height:15px;font-size:12px;color:#00aecd;'
                },
                "info_button": {
                    "html": 'ⓘ',  # 使用 Unicode 字符代替 SVG
                    "style": 'position:absolute;top:1px;right:18px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);cursor:pointer;text-align:center;line-height:15px;font-size:12px;color:#00aecd;'
                }
            },
            "cross": {
                "close_button": {
                    "html": '✕',  # 使用 Unicode 字符代替 SVG
                    "style": 'position:absolute;top:1px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;text-align:center;line-height:15px;font-size:12px;color:#00aecd;'
                },
                "info_button": {
                    "html": 'ⓘ',  # 使用 Unicode 字符代替 SVG
                    "style": 'position:absolute;top:1px;right:18px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);cursor:pointer;text-align:center;line-height:15px;font-size:12px;color:#00aecd;'
                }
            },
            "adchoices": {
                "close_button": {
                    "html": '✕',  # 使用 Unicode 字符代替 SVG
                    "style": 'position:absolute;top:1px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;text-align:center;line-height:15px;font-size:12px;color:#00aecd;'
                },
                "info_button": {
                    "html": '<img src="https://tpc.googlesyndication.com/pagead/images/adchoices/adchoices_blue_wb.png" width="15" height="15" style="display:block;width:15px;height:15px;">',
                    "style": 'position:absolute;top:1px;right:18px;width:15px;height:15px;z-index:100;display:block;cursor:pointer;'
                }
            },
            "adchoices_dots": {
                "close_button": {
                    "html": '⋮',  # 使用 Unicode 字符代替 SVG
                    "style": 'position:absolute;top:1px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;text-align:center;line-height:15px;font-size:12px;color:#00aecd;'
                },
                "info_button": {
                    "html": '<img src="https://tpc.googlesyndication.com/pagead/images/adchoices/adchoices_blue_wb.png" width="15" height="15" style="display:block;width:15px;height:15px;">',
                    "style": 'position:absolute;top:1px;right:18px;width:15px;height:15px;z-index:100;display:block;cursor:pointer;'
                }
            },
            "none": {
                "close_button": {
                    "html": '',
                    "style": 'display:none;'
                },
                "info_button": {
                    "html": '',
                    "style": 'display:none;'
                }
            }
        }
        
        return button_styles.get(button_style, button_styles["dots"])
    
    def replace_ad_content(self, element, image_data, target_width, target_height):
        """完全複製 ad_replacer.py 的替換邏輯"""
        try:
            # 檢查元素是否仍然有效
            try:
                is_valid = self.driver.execute_script("""
                    var element = arguments[0];
                    try {
                        return element && element.getBoundingClientRect && 
                               element.getBoundingClientRect().width > 0;
                    } catch(e) {
                        return false;
                    }
                """, element)
                
                if not is_valid:
                    print("元素已失效，無法替換")
                    return False
            except:
                print("元素已失效，無法替換")
                return False
                
            # 獲取原始尺寸
            original_info = self.driver.execute_script("""
                var element = arguments[0];
                if (!element || !element.getBoundingClientRect) return null;
                var rect = element.getBoundingClientRect();
                return {width: rect.width, height: rect.height};
            """, element)
            
            if not original_info:
                return False
            
            # 檢查是否符合目標尺寸 - 完全複製 ad_replacer.py 的邏輯
            if (original_info['width'] != target_width or 
                original_info['height'] != target_height):
                return False
            
            # 獲取按鈕樣式
            button_style = self.get_button_style()
            
            # 檢查是否為 "none" 模式
            current_button_style = getattr(self, 'button_style', BUTTON_STYLE)
            is_none_mode = current_button_style == "none"
            
            if not is_none_mode:
                close_button_html = button_style["close_button"]["html"]
                close_button_style = button_style["close_button"]["style"]
                info_button_html = button_style["info_button"]["html"]
                info_button_style = button_style["info_button"]["style"]
            else:
                close_button_html = ""
                close_button_style = ""
                info_button_html = ""
                info_button_style = ""
            
            # 完整的替換邏輯 - 處理各種廣告元素類型
            # 分步執行 JavaScript 以避免語法錯誤
            try:
                # 第一步：基本替換
                success = self.driver.execute_script("""
                    var container = arguments[0];
                    var imageBase64 = arguments[1];
                    var targetWidth = arguments[2];
                    var targetHeight = arguments[3];
                    
                    if (!container) return false;
                    
                    var replacedCount = 0;
                    var newImageSrc = 'data:image/png;base64,' + imageBase64;
                    
                    // 確保容器是 relative
                    if (window.getComputedStyle(container).position === 'static') {
                        container.style.position = 'relative';
                    }
                    
                    // 方法1: 處理圖片元素
                    var imgs = container.querySelectorAll('img');
                    for (var i = 0; i < imgs.length; i++) {
                        var img = imgs[i];
                        var imgRect = img.getBoundingClientRect();
                        
                        // 排除控制按鈕
                        var isControlButton = imgRect.width < 50 || imgRect.height < 50 || 
                                             (img.className && img.className.includes('abg')) || 
                                             (img.id && img.id.includes('abg')) ||
                                             (img.src && img.src.includes('googleads')) ||
                                             (img.src && img.src.includes('googlesyndication')) ||
                                             (img.src && img.src.includes('adchoices'));
                        
                        if (!isControlButton && img.src && !img.src.startsWith('data:')) {
                            img.src = newImageSrc;
                            img.style.objectFit = 'contain';
                            img.style.width = '100%';
                            img.style.height = 'auto';
                            replacedCount++;
                        }
                    }
                    
                    // 方法2: 處理 iframe 元素
                    var iframes = container.querySelectorAll('iframe');
                    for (var i = 0; i < iframes.length; i++) {
                        var iframe = iframes[i];
                        var iframeRect = iframe.getBoundingClientRect();
                        
                        // 隱藏 iframe
                        iframe.style.visibility = 'hidden';
                        
                        // 創建替換圖片
                        var newImg = document.createElement('img');
                        newImg.src = newImageSrc;
                        newImg.style.position = 'absolute';
                        newImg.style.top = (iframeRect.top - container.getBoundingClientRect().top) + 'px';
                        newImg.style.left = (iframeRect.left - container.getBoundingClientRect().left) + 'px';
                        newImg.style.width = Math.round(iframeRect.width) + 'px';
                        newImg.style.height = Math.round(iframeRect.height) + 'px';
                        newImg.style.objectFit = 'contain';
                        newImg.style.zIndex = '1';
                        
                        container.appendChild(newImg);
                        replacedCount++;
                    }
                    
                    // 方法3: 處理 div 容器（直接替換內容）
                    if (container.tagName.toLowerCase() === 'div') {
                        // 清空容器內容
                        container.innerHTML = '';
                        
                        // 創建新圖片
                        var newImg = document.createElement('img');
                        newImg.src = newImageSrc;
                        newImg.style.width = '100%';
                        newImg.style.height = '100%';
                        newImg.style.objectFit = 'contain';
                        newImg.style.display = 'block';
                        
                        container.appendChild(newImg);
                        replacedCount++;
                    }
                    
                    // 方法4: 處理背景圖片
                    if (replacedCount === 0) {
                        var style = window.getComputedStyle(container);
                        if (style.backgroundImage && style.backgroundImage !== 'none') {
                            container.style.backgroundImage = 'url(' + newImageSrc + ')';
                            container.style.backgroundSize = 'contain';
                            container.style.backgroundRepeat = 'no-repeat';
                            container.style.backgroundPosition = 'center';
                            replacedCount = 1;
                        }
                    }
                    
                    return replacedCount > 0;
                """, element, image_data, target_width, target_height)
                
                # 第二步：添加控制按鈕（如果需要）
                if success and not is_none_mode:
                    self.driver.execute_script("""
                        var container = arguments[0];
                        var closeButtonHtml = arguments[1];
                        var closeButtonStyle = arguments[2];
                        var infoButtonHtml = arguments[3];
                        var infoButtonStyle = arguments[4];
                        
                        // 移除舊按鈕
                        var oldClose = container.querySelector('#close_button');
                        var oldInfo = container.querySelector('#abgb');
                        if (oldClose) oldClose.remove();
                        if (oldInfo) oldInfo.remove();
                        
                        // 添加關閉按鈕
                        if (closeButtonHtml) {
                            var closeButton = document.createElement('div');
                            closeButton.id = 'close_button';
                            closeButton.innerHTML = closeButtonHtml;
                            closeButton.style.cssText = closeButtonStyle;
                            container.appendChild(closeButton);
                        }
                        
                        // 添加資訊按鈕
                        if (infoButtonHtml) {
                            var infoButton = document.createElement('div');
                            infoButton.id = 'abgb';
                            infoButton.innerHTML = infoButtonHtml;
                            infoButton.style.cssText = infoButtonStyle;
                            container.appendChild(infoButton);
                        }
                    """, element, close_button_html, close_button_style, info_button_html, info_button_style)
                
            except Exception as js_error:
                print(f"JavaScript 執行錯誤: {js_error}")
                return False
            
            if success:
                print(f"✅ 替換廣告成功 {original_info['width']}x{original_info['height']}")
                return True
            else:
                # 調試：檢查元素類型和內容
                element_info = self.driver.execute_script("""
                    var element = arguments[0];
                    return {
                        tagName: element.tagName.toLowerCase(),
                        id: element.id || '',
                        className: element.className || '',
                        innerHTML: element.innerHTML.substring(0, 200),
                        hasImages: element.querySelectorAll('img').length,
                        hasIframes: element.querySelectorAll('iframe').length
                    };
                """, element)
                
                print(f"❌ 廣告替換失敗 {original_info['width']}x{original_info['height']}")
                print(f"   元素類型: <{element_info['tagName']}> id='{element_info['id']}' class='{element_info['className'][:50]}'")
                print(f"   包含圖片: {element_info['hasImages']} 個, iframe: {element_info['hasIframes']} 個")
                print(f"   內容預覽: {element_info['innerHTML'][:100]}...")
                return False
                
        except Exception as e:
            print(f"替換廣告失敗: {e}")
            return False
    
    def process_website(self, url):
        """處理單個網站，遍歷所有替換圖片 - 完全複製 ad_replacer.py 的邏輯"""
        try:
            print(f"\n開始處理網站: {url}")
            
            # 載入網頁
            self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
            self.driver.get(url)
            time.sleep(WAIT_TIME)
            
            # 獲取新聞標題
            try:
                news_title = self.driver.execute_script("""
                    // 嘗試多種選擇器來獲取標題
                    var title = document.querySelector('h1') || 
                               document.querySelector('.article-title') ||
                               document.querySelector('.title') ||
                               document.querySelector('title');
                    return title ? title.textContent.trim() : document.title;
                """)
                print(f"新聞標題: {news_title}")
            except:
                news_title = "unknown_title"
            
            # 遍歷所有替換圖片
            total_replacements = 0
            screenshot_paths = []  # 儲存所有截圖路徑
            
            for image_info in self.replace_images:
                print(f"\n檢查圖片: {image_info['filename']} ({image_info['width']}x{image_info['height']})")
                
                # 載入當前圖片
                try:
                    image_data = self.load_image_base64(image_info['path'])
                except Exception as e:
                    print(f"載入圖片失敗: {e}")
                    continue
                
                # 掃描網頁尋找符合尺寸的廣告
                matching_elements = self.scan_entire_page_for_ads(image_info['width'], image_info['height'])
                
                if not matching_elements:
                    print(f"未找到符合 {image_info['width']}x{image_info['height']} 尺寸的廣告位置")
                    continue
                
                # 嘗試替換找到的廣告
                replaced = False
                for ad_info in matching_elements:
                    try:
                        # 檢查元素是否仍然有效
                        try:
                            # 嘗試訪問元素來檢查是否 stale
                            is_valid = self.driver.execute_script("""
                                var element = arguments[0];
                                try {
                                    return element && element.getBoundingClientRect && 
                                           element.getBoundingClientRect().width > 0;
                                } catch(e) {
                                    return false;
                                }
                            """, ad_info['element'])
                            
                            if not is_valid:
                                print(f"元素已失效，跳過此廣告位置: {ad_info['position']}")
                                continue
                        except:
                            print(f"元素已失效，跳過此廣告位置: {ad_info['position']}")
                            continue
                            
                        if self.replace_ad_content(ad_info['element'], image_data, image_info['width'], image_info['height']):
                            print(f"成功替換廣告: {ad_info['width']}x{ad_info['height']} at {ad_info['position']}")
                            replaced = True
                            total_replacements += 1
                            
                            # 滾動到廣告位置確保可見
                            try:
                                # 獲取廣告元素的位置
                                element_rect = self.driver.execute_script("""
                                    var element = arguments[0];
                                    var rect = element.getBoundingClientRect();
                                    return {
                                        top: rect.top + window.pageYOffset,
                                        left: rect.left + window.pageXOffset,
                                        width: rect.width,
                                        height: rect.height
                                    };
                                """, ad_info['element'])
                                
                                # 計算滾動位置，讓廣告在螢幕中央
                                viewport_height = self.driver.execute_script("return window.innerHeight;")
                                scroll_position = element_rect['top'] - (viewport_height / 2) + (element_rect['height'] / 2)
                                
                                # 滾動到廣告位置
                                self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                                print(f"滾動到廣告位置: {scroll_position:.0f}px")
                                
                                # 等待滾動完成
                                time.sleep(1)
                                
                            except Exception as e:
                                print(f"滾動到廣告位置失敗: {e}")
                            
                            # 每次替換後立即截圖
                            print("準備截圖...")
                            time.sleep(2)  # 等待頁面穩定
                            screenshot_path = self.take_screenshot(news_title)
                            if screenshot_path:
                                screenshot_paths.append(screenshot_path)
                                print(f"✅ 截圖保存: {screenshot_path}")
                            else:
                                print("❌ 截圖失敗")
                            
                            # 截圖後復原該位置的廣告 - 使用最簡單的方法：重新載入頁面
                            try:
                                print("準備還原廣告位置...")
                                # 最可靠的還原方法：重新載入頁面
                                current_url = self.driver.current_url
                                self.driver.refresh()
                                time.sleep(WAIT_TIME)
                                print("✅ 頁面已重新載入，所有廣告已還原")
                                
                                # 重新載入後需要重新獲取新聞標題
                                try:
                                    news_title = self.driver.execute_script("""
                                        // 嘗試多種選擇器來獲取標題
                                        var title = document.querySelector('h1') || 
                                                   document.querySelector('.article-title') ||
                                                   document.querySelector('.title') ||
                                                   document.querySelector('title');
                                        return title ? title.textContent.trim() : document.title;
                                    """)
                                except:
                                    pass  # 保持原有標題
                                
                                # 重新載入後，跳出當前圖片的廣告處理循環
                                # 因為頁面已經還原，其他相同尺寸的廣告可以在下次掃描時處理
                                break
                                
                            except Exception as e:
                                print(f"頁面重新載入失敗: {e}")
                                # 如果重新載入失敗，繼續處理下一個廣告
                                continue
                            
                            # 繼續尋找下一個廣告位置，不要break
                            continue
                    except Exception as e:
                        print(f"替換廣告失敗: {e}")
                        continue
                
                if not replaced:
                    print(f"所有找到的 {image_info['width']}x{image_info['height']} 廣告位置都無法替換")
            
            # 總結處理結果
            if total_replacements > 0:
                print(f"\n{'='*50}")
                print(f"網站處理完成！總共成功替換了 {total_replacements} 個廣告")
                print(f"截圖檔案:")
                for i, path in enumerate(screenshot_paths, 1):
                    print(f"  {i}. {path}")
                print(f"{'='*50}")
                return screenshot_paths
            else:
                print("本網頁沒有找到任何可替換的廣告")
                return []
                
        except Exception as e:
            print(f"處理網站失敗: {e}")
            return []
    
    def take_screenshot(self, news_title=""):
        """截圖功能，使用新聞標題作為檔名"""
        if not os.path.exists(SCREENSHOT_FOLDER):
            os.makedirs(SCREENSHOT_FOLDER)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 清理新聞標題作為檔名
        if news_title:
            # 移除不適合檔名的字符
            clean_title = re.sub(r'[<>:"/\\|?*]', '', news_title)
            clean_title = clean_title.replace(' ', '_')[:50]  # 限制長度
            filepath = f"{SCREENSHOT_FOLDER}/tvbs_{clean_title}_{timestamp}.png"
        else:
            filepath = f"{SCREENSHOT_FOLDER}/tvbs_replaced_{timestamp}.png"
        
        try:
            time.sleep(1)  # 等待頁面穩定
            
            system = platform.system()
            
            if system == "Windows":
                # Windows 多螢幕截圖 - 使用更可靠的方法
                try:
                    # 直接使用 MSS 庫 - 最可靠的多螢幕截圖方法
                    import mss
                    with mss.mss() as sct:
                        monitors = sct.monitors
                        print(f"MSS 偵測到 {len(monitors)-1} 個螢幕: {monitors}")
                        
                        # MSS monitors[0] 是所有螢幕的組合，實際螢幕從 monitors[1] 開始
                        # 所以 screen_id=1 對應 monitors[1]，screen_id=2 對應 monitors[2]
                        if self.screen_id < len(monitors):
                            # 截取指定螢幕 (screen_id 直接對應 monitors 索引)
                            monitor = monitors[self.screen_id]
                            screenshot_mss = sct.grab(monitor)
                            
                            # 轉換為 PIL Image
                            from PIL import Image
                            screenshot = Image.frombytes('RGB', screenshot_mss.size, screenshot_mss.bgra, 'raw', 'BGRX')
                            print(f"✅ 使用 MSS 截取螢幕 {self.screen_id}: {monitor}")
                            print(f"   截圖尺寸: {screenshot.size}")
                        else:
                            # 螢幕 ID 超出範圍，使用主螢幕
                            monitor = monitors[1]  # 主螢幕
                            screenshot_mss = sct.grab(monitor)
                            from PIL import Image
                            screenshot = Image.frombytes('RGB', screenshot_mss.size, screenshot_mss.bgra, 'raw', 'BGRX')
                            print(f"⚠️ 螢幕 {self.screen_id} 不存在，使用主螢幕: {monitor}")
                    
                    screenshot.save(filepath)
                    print(f"✅ MSS 截圖保存 (螢幕 {self.screen_id}): {filepath}")
                    return filepath
                        
                except ImportError:
                    print("❌ MSS 未安裝，使用 pyautogui 備用方案")
                    try:
                        import pyautogui
                        screenshot = pyautogui.screenshot()
                        screenshot.save(filepath)
                        print(f"✅ pyautogui 截圖保存: {filepath}")
                        return filepath
                    except:
                        print("pyautogui 也失敗，使用 Selenium 截圖")
                        self.driver.save_screenshot(filepath)
                        print(f"截圖保存: {filepath}")
                        return filepath
                except Exception as e:
                    print(f"❌ MSS 截圖失敗: {e}，使用 pyautogui 備用方案")
                    try:
                        import pyautogui
                        screenshot = pyautogui.screenshot()
                        screenshot.save(filepath)
                        print(f"✅ pyautogui 截圖保存: {filepath}")
                        return filepath
                    except:
                        print("pyautogui 也失敗，使用 Selenium 截圖")
                        self.driver.save_screenshot(filepath)
                        print(f"截圖保存: {filepath}")
                        return filepath
                    
            elif system == "Darwin":  # macOS
                # macOS 多螢幕截圖
                try:
                    # 使用 screencapture 的 -D 參數指定螢幕
                    result = subprocess.run([
                        'screencapture', 
                        '-D', str(self.screen_id),  # 指定螢幕編號
                        filepath
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0 and os.path.exists(filepath):
                        print(f"截圖保存 (螢幕 {self.screen_id}): {filepath}")
                        return filepath
                    else:
                        print(f"指定螢幕 {self.screen_id} 截圖失敗，嘗試全螢幕截圖")
                        # 回退到全螢幕截圖
                        result = subprocess.run([
                            'screencapture', 
                            filepath
                        ], capture_output=True, text=True)
                        
                        if result.returncode == 0 and os.path.exists(filepath):
                            print(f"截圖保存 (全螢幕): {filepath}")
                            return filepath
                        else:
                            raise Exception("screencapture 命令失敗")
                            
                except Exception as e:
                    print(f"系統截圖失敗: {e}，使用 Selenium 截圖")
                    self.driver.save_screenshot(filepath)
                    print(f"截圖保存: {filepath}")
                    return filepath
                    
            else:  # Linux
                # Linux 多螢幕截圖
                try:
                    # 使用 import 命令截取指定螢幕
                    display = f":0.{self.screen_id - 1}" if self.screen_id > 1 else ":0"
                    result = subprocess.run([
                        'import', 
                        '-window', 'root',
                        '-display', display,
                        filepath
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0 and os.path.exists(filepath):
                        print(f"截圖保存 (螢幕 {self.screen_id}): {filepath}")
                        return filepath
                    else:
                        raise Exception("import 命令失敗")
                        
                except Exception as e:
                    print(f"系統截圖失敗: {e}，使用 Selenium 截圖")
                    self.driver.save_screenshot(filepath)
                    print(f"截圖保存: {filepath}")
                    return filepath
                
        except Exception as e:
            print(f"截圖失敗: {e}，使用 Selenium 截圖")
            try:
                self.driver.save_screenshot(filepath)
                print(f"截圖保存: {filepath}")
                return filepath
            except Exception as e2:
                print(f"截圖失敗: {e2}")
                return None
    
    def close(self):
        self.driver.quit()

def main():
    """
    主程式入口
    
    目前設定為處理 nicklee.tw 網站
    如要切換到 TVBS 食尚玩家，請將下方的 NICKLEE_BASE_URL 改為 TVBS_BASE_URL
    """
    print("="*60)
    print("多網站廣告替換器")
    print("目前設定: nicklee.tw")
    print("如要切換網站，請修改 main() 函數中的 BASE_URL 設定")
    print("="*60)
    
    # 偵測並選擇螢幕
    screen_id, selected_screen = ScreenManager.select_screen()
    
    if screen_id is None:
        print("未選擇螢幕，程式結束")
        return
    
    print(f"\n正在啟動 Chrome 瀏覽器到螢幕 {screen_id}...")
    bot = TvbsAdReplacer(headless=False, screen_id=screen_id)
    
    try:
        # 尋找新聞連結 - 指定 TVBS 分類起始頁（旅行 / 亞洲）
        start_pages = [
            f"{TVBS_BASE_URL.rstrip('/')}/travel",
            f"{TVBS_BASE_URL.rstrip('/')}/asia",
        ]

        news_urls = []
        for idx, start_url in enumerate(start_pages, 1):
            print(f"起始頁 {idx}/{len(start_pages)}: {start_url}")
            urls = bot.get_random_news_urls(start_url, NEWS_COUNT)
            if urls:
                news_urls.extend(urls)
            # 去重
            news_urls = list(dict.fromkeys(news_urls))
            # 已達需求數量則停止
            if len(news_urls) >= NEWS_COUNT:
                break

        # 最後防呆：若仍沒有任何連結，退回主站
        if not news_urls:
            print("⚠️ 分類頁未取得連結，退回主站嘗試一次…")
            news_urls = bot.get_random_news_urls(TVBS_BASE_URL, NEWS_COUNT)
        
        if not news_urls:
            print("無法獲取新聞連結")
            return
        
        print(f"獲取到 {len(news_urls)} 個新聞連結")
        print(f"目標截圖數量: {SCREENSHOT_COUNT}")
        
        total_screenshots = 0
        
        # 處理每個網站
        for i, url in enumerate(news_urls, 1):
            print(f"\n{'='*50}")
            print(f"處理第 {i}/{len(news_urls)} 個網站")
            print(f"{'='*50}")
            
            try:
                # 處理網站並嘗試替換廣告
                screenshot_paths = bot.process_website(url)
                
                if screenshot_paths:
                    print(f"✅ 成功處理網站！共產生 {len(screenshot_paths)} 張截圖")
                    total_screenshots += len(screenshot_paths)
                    
                    # 檢查是否達到目標截圖數量
                    if total_screenshots >= SCREENSHOT_COUNT:
                        print(f"✅ 已達到目標截圖數量: {SCREENSHOT_COUNT}")
                        break
                else:
                    print("❌ 網站處理完成，但沒有找到可替換的廣告")
                
            except Exception as e:
                print(f"❌ 處理網站失敗: {e}")
                continue
            
            # 在處理下一個網站前稍作休息
            if i < len(news_urls) and total_screenshots < SCREENSHOT_COUNT:
                print("等待 3 秒後處理下一個網站...")
                time.sleep(3)
        
        print(f"\n{'='*50}")
        print(f"所有網站處理完成！總共產生 {total_screenshots} 張截圖")
        print(f"{'='*50}")
        
    finally:
        bot.close()

if __name__ == "__main__":
    main()