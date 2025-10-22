#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Yahoo 新聞廣告替換器 - GIF 升級版
專注於 Yahoo 新聞熱門景點版面 (tw.news.yahoo.com/tourist-spots)

核心功能：
- 智能廣告掃描和替換系統
- 支援多種按鈕樣式 (dots, cross, adchoices, adchoices_dots, none)
- GIF 和靜態圖片智能選擇策略
- Yahoo 風格的廣告還原機制（簡化清理策略）
- 按尺寸分組的圖片管理系統
- 詳細的 GIF/靜態圖片使用統計
- 多螢幕支援 (Windows, macOS, Linux)
- 重試機制和錯誤處理
- 整合 UDN 的 GIF 功能架構

版本：GIF 升級版 v2.0
作者：Yahoo 廣告替換系統
"""

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

# 載入 GIF 功能專用設定檔
try:
    from gif_config import *
    print("成功載入 gif_config.py 設定檔")
    print(f"SCREENSHOT_COUNT 設定: {SCREENSHOT_COUNT}")
    print(f"NEWS_COUNT 設定: {NEWS_COUNT}")
    print(f"IMAGE_USAGE_COUNT 設定: {IMAGE_USAGE_COUNT}")
    print(f"GIF_PRIORITY 設定: {GIF_PRIORITY}")
    # 覆蓋 gif_config.py 中的 BASE_URL，設定 Yahoo 專用網址
    YAHOO_BASE_URL = "https://tw.news.yahoo.com/tourist-spots"
except ImportError:
    print("找不到 gif_config.py，使用預設設定")
    # 預設設定
    SCREENSHOT_COUNT = 3
    MAX_ATTEMPTS = 50
    PAGE_LOAD_TIMEOUT = 15
    WAIT_TIME = 3
    REPLACE_IMAGE_FOLDER = "replace_image"
    DEFAULT_IMAGE = "mini.jpg"
    MINI_IMAGE = "mini.jpg"
    BASE_URL = "https://tw.news.yahoo.com/tourist-spots"
    YAHOO_BASE_URL = "https://tw.news.yahoo.com/tourist-spots"  # Yahoo 新聞熱門景點版面
    NEWS_COUNT = 20
    TARGET_AD_SIZES = []  # 將由 load_replace_images() 動態生成
    IMAGE_USAGE_COUNT = {"google_970x90.jpg": 5, "google_986x106.jpg": 3}
    YAHOO_TARGET_AD_SIZES = [
        {"width": 970, "height": 90},
        {"width": 728, "height": 90},
        {"width": 300, "height": 250},
        {"width": 320, "height": 50},
        {"width": 336, "height": 280}
    ]
    MAX_CONSECUTIVE_FAILURES = 10
    CLOSE_BUTTON_SIZE = {"width": 15, "height": 15}
    INFO_BUTTON_SIZE = {"width": 15, "height": 15}
    INFO_BUTTON_COLOR = "#00aecd"
    INFO_BUTTON_OFFSET = 16
    HEADLESS_MODE = False
    FULLSCREEN_MODE = True
    SCREENSHOT_FOLDER = "screenshots"
    BUTTON_STYLE = "dots"  # 預設按鈕樣式
    # GIF 使用策略預設設定
    GIF_PRIORITY = True

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
    


class YahooAdReplacer:
    def __init__(self, headless=False, screen_id=1):
        print("正在初始化 Yahoo 廣告替換器 - GIF 升級版...")
        self.screen_id = screen_id
        
        # 統計變數 - 採用 ETtoday 模式
        self.total_screenshots = 0      # 總截圖數量
        self.total_replacements = 0     # 總替換次數
        self.gif_replacements = 0       # GIF 替換次數
        self.static_replacements = 0    # 靜態圖片替換次數
        self.replacement_details = []   # 詳細替換記錄
        
        self.setup_driver(headless)
        self.load_replace_images()
        print("Yahoo 廣告替換器 - GIF 升級版")
        
    def setup_driver(self, headless):
        chrome_options = Options()
        if headless or HEADLESS_MODE:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        
        # 禁用 Google 服務相關功能，避免 QUOTA_EXCEEDED 錯誤
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        chrome_options.add_argument('--disable-background-networking')
        chrome_options.add_argument('--disable-sync')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-component-extensions-with-background-pages')
        chrome_options.add_argument('--disable-background-mode')
        
        # 禁用 Google Cloud Messaging (GCM) 相關服務
        chrome_options.add_argument('--gcm-registration-url=')
        chrome_options.add_argument('--gcm-checkin-url=')
        chrome_options.add_argument('--disable-client-side-phishing-detection')
        chrome_options.add_argument('--disable-component-update')
        
        # 設定日誌級別，減少錯誤訊息
        chrome_options.add_argument('--log-level=3')  # 只顯示 FATAL 錯誤
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 多螢幕支援 - 計算螢幕偏移量
        if self.screen_id > 1:
            screen_offset = (self.screen_id - 1) * 1920
            chrome_options.add_argument(f'--window-position={screen_offset},0')
        
        # 默認全螢幕設定
        chrome_options.add_argument('--start-maximized')
        if not headless:
            chrome_options.add_argument('--start-fullscreen')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # 設置超時時間 - 解決網路連線問題
        self.driver.set_page_load_timeout(30)  # 頁面載入超時30秒
        self.driver.implicitly_wait(10)        # 隱式等待10秒
        print("瀏覽器超時設定完成")
        
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
        """載入替換圖片並解析尺寸 - Yahoo GIF 升級版"""
        self.replace_images = []
        self.images_by_size = {}  # 按尺寸分組的圖片字典
        self.target_ad_sizes = []  # 初始化目標廣告尺寸
        
        if not os.path.exists(REPLACE_IMAGE_FOLDER):
            print(f"找不到替換圖片資料夾: {REPLACE_IMAGE_FOLDER}")
            return
        
        print(f"開始載入 {REPLACE_IMAGE_FOLDER} 資料夾中的圖片...")
        
        for filename in os.listdir(REPLACE_IMAGE_FOLDER):
            if filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                # 解析檔案名中的尺寸
                size_match = re.search(r'google_(\d+)x(\d+)', filename)
                if size_match:
                    width = int(size_match.group(1))
                    height = int(size_match.group(2))
                    size_key = f"{width}x{height}"
                    
                    image_path = os.path.join(REPLACE_IMAGE_FOLDER, filename)
                    file_type = "GIF" if filename.lower().endswith('.gif') else "靜態圖片"
                    
                    image_info = {
                        'path': image_path,
                        'filename': filename,
                        'width': width,
                        'height': height,
                        'type': file_type,
                        'is_gif': filename.lower().endswith('.gif')
                    }
                    
                    self.replace_images.append(image_info)
                    
                    # 按尺寸分組
                    if size_key not in self.images_by_size:
                        self.images_by_size[size_key] = {'static': [], 'gif': []}
                    
                    if image_info['is_gif']:
                        self.images_by_size[size_key]['gif'].append(image_info)
                    else:
                        self.images_by_size[size_key]['static'].append(image_info)
                    
                    print(f"載入{file_type}: {filename} ({width}x{height})")
                else:
                    print(f"跳過不符合命名規則的圖片: {filename}")
        
        # 按檔案名排序
        self.replace_images.sort(key=lambda x: x['filename'])
        print(f"總共載入 {len(self.replace_images)} 張替換圖片")
        
        # 顯示按尺寸分組的統計
        print("\n📊 圖片尺寸分佈統計:")
        for size_key, images in sorted(self.images_by_size.items()):
            static_count = len(images['static'])
            gif_count = len(images['gif'])
            total_count = static_count + gif_count
            
            status_parts = []
            if static_count > 0:
                status_parts.append(f"{static_count}張靜態")
            if gif_count > 0:
                status_parts.append(f"{gif_count}張GIF")
            
            status = " + ".join(status_parts)
            print(f"  {size_key}: {total_count}張 ({status})")
        
        # 根據載入的圖片動態生成目標廣告尺寸
        self.target_ad_sizes = []
        unique_sizes = set()
        
        for img in self.replace_images:
            size_key = (img['width'], img['height'])
            if size_key not in unique_sizes:
                unique_sizes.add(size_key)
                self.target_ad_sizes.append({
                    'width': img['width'],
                    'height': img['height']
                })
        
        size_list = [f"{size['width']}x{size['height']}" for size in self.target_ad_sizes]
        print(f"根據替換圖片生成目標廣告尺寸: {size_list}")
        
        # 顯示載入的圖片清單
        print(f"\n📋 完整圖片清單:")
        for i, img in enumerate(self.replace_images):
            type_icon = "🎬" if img['is_gif'] else "🖼️"
            print(f"  {i+1}. {type_icon} {img['filename']} ({img['width']}x{img['height']})")
    
    def select_image_by_strategy(self, static_images, gif_images, size_key):
        """根據 GIF_PRIORITY 配置選擇圖片 - Yahoo 優先級模式"""
        
        # 如果沒有任何圖片，返回 None
        if not static_images and not gif_images:
            return None
        
        # 如果只有一種類型的圖片，直接選擇第一個
        if not static_images and gif_images:
            selected = gif_images[0]  # 選擇第一個 GIF
            print(f"   🎬 選擇 GIF (唯一選項): {selected['filename']}")
            return selected
        elif static_images and not gif_images:
            selected = static_images[0]  # 選擇第一個靜態圖片
            print(f"   🖼️ 選擇靜態圖片 (唯一選項): {selected['filename']}")
            return selected
        
        # 兩種類型都有，根據 GIF_PRIORITY 策略選擇
        try:
            gif_priority = globals().get('GIF_PRIORITY', True)
        except:
            gif_priority = True
        
        # 優先級模式：根據 GIF_PRIORITY 決定
        if gif_priority:
            # 優先使用 GIF
            if gif_images:
                selected = gif_images[0]  # 選擇第一個 GIF
                print(f"   🎬 優先選擇 GIF: {selected['filename']}")
                return selected
            else:
                selected = static_images[0]  # 選擇第一個靜態圖片
                print(f"   🖼️ 選擇靜態圖片 (GIF 不可用): {selected['filename']}")
                return selected
        else:
            # 優先使用靜態圖片
            if static_images:
                selected = static_images[0]  # 選擇第一個靜態圖片
                print(f"   🖼️ 優先選擇靜態圖片: {selected['filename']}")
                return selected
            else:
                selected = gif_images[0]  # 選擇第一個 GIF
                print(f"   🎬 選擇 GIF (靜態圖片不可用): {selected['filename']}")
                return selected

    def _update_screenshot_count(self, filepath, current_image_info, original_ad_info):
        """更新截圖統計並返回檔案路徑 - Yahoo 統計模式"""
        self.total_screenshots += 1
        self.total_replacements += 1
        
        # 檢查是否為 GIF 廣告
        if current_image_info and current_image_info.get('is_gif'):
            self.gif_replacements += 1
            print(f"📊 替換了 GIF 廣告")
        else:
            self.static_replacements += 1
        
        # 記錄詳細替換資訊
        if current_image_info:
            self.replacement_details.append({
                'filename': current_image_info['filename'],
                'size': f"{current_image_info['width']}x{current_image_info['height']}",
                'type': current_image_info['type'],
                'screenshot': filepath
            })
        
        print(f"📊 總截圖數: {self.total_screenshots}")
        if self.gif_replacements > 0:
            print(f"📊 GIF 廣告數: {self.gif_replacements}")
        
        return filepath

    def load_image_base64(self, image_path):
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"找不到圖片: {image_path}")
            
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def get_random_news_urls(self, base_url, count=5):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"正在訪問: {base_url}")
                if attempt > 0:
                    print(f"重試第 {attempt}/{max_retries-1} 次...")
                
                # 設置較長的超時時間
                self.driver.set_page_load_timeout(45)
                self.driver.get(base_url)
                print("✅ 頁面載入成功")
                time.sleep(WAIT_TIME + 2)  # 增加等待時間
                
                # 檢查當前頁面 URL
                current_url = self.driver.current_url
                print(f"實際頁面 URL: {current_url}")
                
                # 檢查頁面標題
                page_title = self.driver.title
                print(f"頁面標題: {page_title}")
                
                # Yahoo 新聞娛樂版面的連結選擇器 - 針對特定結構
                link_selectors = [
                # 針對您提供的 HTML 結構的選擇器 - 優先尋找具體的新聞文章
                "h3 a[href*='.html']",                            # 新聞標題連結（最優先）
                "h2 a[href*='.html']",                            # 二級標題連結
                "h1 a[href*='.html']",                            # 一級標題連結
                "a[href*='.html']",                               # 所有 HTML 文章連結
                "a[href*='story'][href*='.html']",                # 故事連結
                "a[href*='article'][href*='.html']",              # 文章連結
                "a[href*='news'][href*='.html']",                 # 新聞連結
                "a[href*='-'][href*='.html']",                    # 包含連字符的連結（通常是新聞標題）
                # 備用選擇器
                "ul li a[href*='.html']",                         # 列表中的新聞連結
                "li a[href*='.html']",                            # 列表項目的連結
                "div a[href*='.html']",                           # 區塊中的連結
                # 最後的備用選擇器
                "a[href*='tw.news.yahoo.com'][href*='.html']",    # 所有 Yahoo 新聞連結
                "a[data-ylk*='news'][href*='.html']",             # Yahoo 新聞連結
                # 調試選擇器
                "a",                                               # 所有連結（調試用）
                "h3 a",                                           # 所有 h3 中的連結
                "a[href*='/']",                                   # 所有以 / 開頭的連結
                ]
                
                news_urls = []
                
                for selector in link_selectors:
                    try:
                        links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        print(f"使用選擇器 '{selector}' 找到 {len(links)} 個連結")
                        for link in links:
                            href = link.get_attribute('href')
                            print(f"  連結: {href}")
                            if href and href not in news_urls and '.html' in href:
                                # 檢查是否為有效的 Yahoo 新聞文章連結
                                is_valid_news = any(keyword in href.lower() for keyword in [
                                    'tw.news.yahoo.com', '.html', 'story', 'article', 'news'
                                ])
                                
                                # 排除明顯的非新聞連結
                                is_not_news = any(exclude in href.lower() for exclude in [
                                    '/mail/', '/shopping/', '/auction/', '/finance/', '/sports/', '/politics/', '/international/', '/society/', '/health/', '/taste/', '/weather/', '/archive/', '/most-popular/', '/topic/',
                                    'login', 'signin', 'register', 'account', 'profile', 'settings', 'help', 'about', 'contact', 'privacy', 'terms'
                                ])
                                
                                # 確保是具體的新聞文章而不是分類頁面
                                is_article_page = '.html' in href and not href.endswith('/') and not href.endswith('/tourist-spots')
                                
                                # 接受所有有效的 Yahoo 新聞文章連結
                                if is_valid_news and not is_not_news and is_article_page:
                                    # 如果是相對路徑，轉換為完整 URL
                                    if href.startswith('/'):
                                        full_url = 'https://tw.news.yahoo.com' + href
                                    else:
                                        full_url = href
                                    news_urls.append(full_url)
                                    print(f"找到娛樂新聞文章連結: {full_url}")
                    except Exception as e:
                        print(f"使用選擇器 {selector} 尋找連結失敗: {e}")
                        continue
                
                # 如果沒有找到足夠的連結，嘗試從主頁面獲取
                if len(news_urls) < NEWS_COUNT:
                    print(f"只找到 {len(news_urls)} 個連結，嘗試從主頁面獲取更多...")
                    try:
                        # 檢查是否仍在熱門景點版面
                        current_url = self.driver.current_url
                        if '/tourist-spots' not in current_url:
                            print(f"警告：頁面已離開熱門景點版面，當前 URL: {current_url}")
                            # 重新導航到熱門景點版面
                            self.driver.get(base_url)
                            time.sleep(WAIT_TIME)
                        
                        # 使用更寬鬆的選擇器來獲取更多連結
                        additional_selectors = [
                        "h3 a[href*='.html']",                            # 新聞標題連結
                        "h2 a[href*='.html']",                            # 二級標題連結
                        "h1 a[href*='.html']",                            # 一級標題連結
                        "a[href*='.html'][href*='tw.news.yahoo.com']",    # HTML 文章連結
                        "a[href*='story'][href*='.html']",                # 故事連結
                        "a[href*='article'][href*='.html']",              # 文章連結
                        "a[href*='news'][href*='.html']",                 # 新聞連結
                        "a[href*='-'][href*='.html']",                    # 包含連字符的連結
                        "ul li a[href*='.html']",                         # 列表中的新聞連結
                        "li a[href*='.html']",                            # 列表項目的連結
                        "div a[href*='.html']",                           # 區塊中的連結
                        "a[href*='tw.news.yahoo.com'][href*='.html']",    # 所有 Yahoo 新聞連結
                        "a[data-ylk*='news'][href*='.html']"              # Yahoo 新聞連結
                        ]
                        
                        for selector in additional_selectors:
                            try:
                                links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                for link in links:
                                    href = link.get_attribute('href')
                                    if href and href not in news_urls and '.html' in href:
                                        # 檢查是否為有效的 Yahoo 新聞文章連結
                                        is_valid_news = any(keyword in href.lower() for keyword in [
                                            'tw.news.yahoo.com', '.html', 'story', 'article', 'news'
                                        ])
                                        
                                        # 排除明顯的非新聞連結
                                        is_not_news = any(exclude in href.lower() for exclude in [
                                            '/mail/', '/shopping/', '/auction/', '/finance/', '/sports/', '/politics/', '/international/', '/society/', '/health/', '/taste/', '/weather/', '/archive/', '/most-popular/', '/topic/',
                                            'login', 'signin', 'register', 'account', 'profile', 'settings', 'help', 'about', 'contact', 'privacy', 'terms'
                                        ])
                                        
                                        # 確保是具體的新聞文章而不是分類頁面
                                        is_article_page = '.html' in href and not href.endswith('/') and not href.endswith('/tourist-spots')
                                        
                                        # 接受所有有效的 Yahoo 新聞文章連結
                                        if is_valid_news and not is_not_news and is_article_page:
                                            # 如果是相對路徑，轉換為完整 URL
                                            if href.startswith('/'):
                                                full_url = 'https://tw.news.yahoo.com' + href
                                            else:
                                                full_url = href
                                            news_urls.append(full_url)
                                            print(f"找到娛樂新聞文章連結: {full_url}")
                            except Exception as e:
                                continue
                    except Exception as e:
                        print(f"獲取額外連結失敗: {e}")
                
                return random.sample(news_urls, min(NEWS_COUNT, len(news_urls)))
                
            except Exception as e:
                print(f"第 {attempt + 1} 次嘗試失敗: {e}")
                if attempt < max_retries - 1:
                    print(f"等待 10 秒後重試...")
                    time.sleep(10)
                    continue
                else:
                    print(f"所有重試都失敗，無法獲取新聞連結")
                    return []
    
    def find_all_yahoo_ads(self):
        """全面掃描Yahoo網站的所有廣告 - 使用完整17個選擇器"""
        print("🔍 全面掃描Yahoo網站所有廣告 (使用完整選擇器)...")
        
        # 一次性獲取所有廣告元素和尺寸
        all_ads_data = self.driver.execute_script("""
            // 在瀏覽器中完成所有廣告掃描工作
            var allAds = [];
            
            // 完整的17個廣告選擇器 - 基於4個實際廣告位置
            var selectors = [
                // 廣告位置1: Google AdSense (各種尺寸)
                'div[class="GoogleActiveViewInnerContainer"]',
                'div[class="GoogleActiveViewElement"]',
                'div[class*="GoogleActiveViewElement"]',
                'div[data-google-av-cxn]',
                'div[data-google-av-metadata]',
                'div[data-google-av-adk]',
                'div[data-google-av-override]',
                'div[data-google-av-dm]',
                'div[data-google-av-aid]',
                
                // 廣告位置2: Criteo 廣告 (300x600)
                'div[id="bnr"][class="isSetup"]',
                'div[class="isSetup"]',
                'a[href*="cat.sg1.as.criteo.com"]',
                'a[href*="criteo.com"]',
                'div[data-crto-id]',
                'div[class*="imageholder"]',
                'div[class*="overflowHidden"]',
                
                // 廣告位置3: Yahoo 右側 iframe 廣告 (300x250, 300x600)
                'div[id="sda-top-right-iframe"]',
                'div[id="sda-mid-right-iframe"]',
                'div[id="sda-mid-right-2-iframe"]',
                'div[id*="sda-"][id*="-iframe"]',
                'div[data-google-query-id]',
                'div[class*="min-w-[300px]"]',
                'div[class*="min-h-[250px]"]',
                'div[class*="min-h-[600px]"]',
                
                // 廣告位置4: Yahoo 橫幅廣告 (970x250)
                'div[id="sda-top-center-iframe"]',
                'div[id*="google_ads_iframe_"]',
                'div[id*="tw_ynews_ros_dt_top_center"]',
                'div[id*="container__"]',
                'div[class*="sticky"]',
                'div[class*="z-index-1"]',
                
                // 通用 Google Ads 特徵
                'iframe[src*="googlesyndication.com"]',
                'iframe[src*="safeframe.googlesyndication.com"]',
                'iframe[src*="doubleclick"]',
                'ins.adsbygoogle',
                'div[class*="google-ads"]',
                'div[id*="google_ads"]',
                
                // Yahoo 特定廣告容器
                'div[class*="mb-module-gap"]',
                'div[class*="lg:w-article-aside"]',
                'div[class*="w-full"]',
                'div[class*="shrink-0"]',
                'aside[class*="mt-module-gap"]',
                
                // 廣告相關 data 屬性
                'div[data-creative-load-listener]',
                'div[data-tag]',
                'div[data-bsc]',
                'div[data-imgsrc]',
                
                // 常見廣告特徵
                'div[id*="ad"]',
                'div[class*="ad"]',
                'div[class*="advertisement"]',
                'div[class*="banner"]',
                'div[onclick*="clickTag"]'
            ];
            
            var processed = new Set();
            var selectorStats = {};
            
            selectors.forEach(function(selector) {
                try {
                    var elements = document.querySelectorAll(selector);
                    selectorStats[selector] = elements.length;
                    
                    for (var i = 0; i < elements.length; i++) {
                        var element = elements[i];
                        var rect = element.getBoundingClientRect();
                        
                        // 只要是可見的元素就收集
                        if (rect.width > 50 && rect.height > 50) {
                            var posKey = Math.round(rect.top) + ',' + Math.round(rect.left);
                            if (processed.has(posKey)) continue;
                            processed.add(posKey);
                            
                            var width = Math.round(rect.width);
                            var height = Math.round(rect.height);
                            
                            allAds.push({
                                element: element,
                                width: width,
                                height: height,
                                top: rect.top,
                                left: rect.left,
                                tagName: element.tagName.toLowerCase(),
                                id: element.id || '',
                                className: element.className || '',
                                selector: selector,
                                sizeKey: width + 'x' + height
                            });
                        }
                    }
                } catch(e) {
                    selectorStats[selector] = 0;
                }
            });
            
            return {ads: allAds, stats: selectorStats};
        """)
        
        # 顯示選擇器統計
        print("📊 選擇器掃描統計:")
        for selector, count in all_ads_data['stats'].items():
            if count > 0:
                print(f"   ✅ {selector}: {count}個")
        
        # 按尺寸分組所有廣告
        ads_by_size = {}
        
        for ad_data in all_ads_data['ads']:
            size_key = ad_data['sizeKey']
            
            if size_key not in ads_by_size:
                ads_by_size[size_key] = []
            
            ads_by_size[size_key].append({
                'element': ad_data['element'],
                'width': ad_data['width'],
                'height': ad_data['height'],
                'position': f"top:{ad_data['top']:.0f}, left:{ad_data['left']:.0f}",
                'selector': ad_data['selector'],
                'tagName': ad_data['tagName'],
                'id': ad_data['id'],
                'className': ad_data['className']
            })
        
        # 顯示找到的所有廣告尺寸
        print("📊 找到的所有廣告尺寸:")
        total_ads = 0
        for size_key, ads in sorted(ads_by_size.items()):
            print(f"   {size_key}: {len(ads)}個")
            total_ads += len(ads)
            
            # 顯示每個尺寸的詳細資訊
            for i, ad in enumerate(ads, 1):
                print(f"      {i}. {ad['tagName']} #{ad['id']} at {ad['position']} (選擇器: {ad['selector']})")
        
        print(f"🔍 全面掃描完成: 總共找到 {total_ads} 個廣告")
        
        return ads_by_size

    def scan_entire_page_for_ads(self, target_width, target_height):
        """掃描Yahoo所有廣告 - 全面掃描版本"""
        print(f"🎯 尋找 {target_width}x{target_height} 的廣告...")
        
        # 如果還沒有掃描過所有廣告，先進行全面掃描
        if not hasattr(self, '_all_yahoo_ads'):
            self._all_yahoo_ads = self.find_all_yahoo_ads()
        
        size_key = f"{target_width}x{target_height}"
        
        # 從所有廣告中找到符合尺寸的
        if size_key in self._all_yahoo_ads:
            matching_elements = self._all_yahoo_ads[size_key]
            print(f"✅ 從所有廣告中找到 {len(matching_elements)} 個 {size_key} 廣告")
        else:
            # 如果沒有完全匹配的尺寸，尋找相近的尺寸 (容差10像素)
            matching_elements = []
            tolerance = 10  # 容差改為10像素，確保按鈕位置準確
            
            for existing_size, ads in self._all_yahoo_ads.items():
                try:
                    existing_width, existing_height = map(int, existing_size.split('x'))
                    width_match = abs(existing_width - target_width) <= tolerance
                    height_match = abs(existing_height - target_height) <= tolerance
                    
                    if width_match and height_match:
                        matching_elements.extend(ads)
                        print(f"✅ 找到相近尺寸 {existing_size} (目標: {size_key}, 容差±{tolerance}px): {len(ads)}個")
                except:
                    continue
            
            if not matching_elements:
                print(f"❌ 未找到 {size_key} 或相近尺寸的廣告 (容差±{tolerance}px)")
        
        return matching_elements
    
    def _scan_for_other_sizes(self, target_width, target_height):
        """備用掃描函數 - 當全面掃描未啟用時使用"""
        print(f"🔍 備用掃描: {target_width}x{target_height}")
        print("⚠️ 全面掃描未啟用，使用備用掃描方法")
        
        # 如果全面掃描沒有執行，先執行一次
        if not hasattr(self, '_all_yahoo_ads'):
            print("🔄 執行全面掃描...")
            self._all_yahoo_ads = self.find_all_yahoo_ads()
        
        # 從全面掃描結果中查找
        size_key = f"{target_width}x{target_height}"
        tolerance = 10
        matching_elements = []
        
        for existing_size, ads in self._all_yahoo_ads.items():
            try:
                existing_width, existing_height = map(int, existing_size.split('x'))
                width_match = abs(existing_width - target_width) <= tolerance
                height_match = abs(existing_height - target_height) <= tolerance
                
                if width_match and height_match:
                    matching_elements.extend(ads)
                    print(f"✅ 找到相近尺寸 {existing_size} (目標: {size_key}): {len(ads)}個")
            except:
                continue
        
        print(f"🎯 備用掃描找到 {len(matching_elements)} 個廣告")
        return matching_elements
    
    def is_valid_ad_element(self, element, target_width, target_height):
        """基於4個廣告樣式特徵驗證元素是否為有效廣告"""
        try:
            # 獲取元素的基本資訊
            element_info = self.driver.execute_script("""
                var element = arguments[0];
                var rect = element.getBoundingClientRect();
                var computedStyle = window.getComputedStyle(element);
                
                return {
                    tagName: element.tagName.toLowerCase(),
                    id: element.id || '',
                    className: element.className || '',
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    src: element.src || '',
                    href: element.href || '',
                    onclick: element.onclick ? element.onclick.toString() : '',
                    backgroundColor: computedStyle.backgroundColor,
                    position: computedStyle.position,
                    display: computedStyle.display,
                    visibility: computedStyle.visibility,
                    opacity: computedStyle.opacity,
                    // 檢查是否有廣告相關的data屬性
                    hasGoogleAd: element.hasAttribute('data-google-av-cxn') || 
                                element.hasAttribute('data-google-query-id') ||
                                element.hasAttribute('data-creative-load-listener') ||
                                element.hasAttribute('data-google-av-adk') ||
                                element.hasAttribute('data-google-av-metadata') ||
                                element.hasAttribute('data-crto-id') ||
                                element.hasAttribute('data-tag') ||
                                element.hasAttribute('data-bsc'),
                    // 檢查父元素是否有廣告特徵
                    parentHasAdFeatures: element.parentElement ? (
                        element.parentElement.id.includes('ad') ||
                        element.parentElement.className.includes('ad') ||
                        element.parentElement.className.includes('Google')
                    ) : false
                };
            """, element)
            
            # 尺寸匹配檢查（允許10像素容差）
            tolerance = 10
            width_match = abs(element_info['width'] - target_width) <= tolerance
            height_match = abs(element_info['height'] - target_height) <= tolerance
            
            if not (width_match and height_match):
                return False
            
            # 基於4個實際廣告位置的特徵檢查
            ad_indicators = []
            
            # 廣告位置1特徵: Google AdSense
            if ('GoogleActiveViewInnerContainer' in element_info['className'] or
                'GoogleActiveViewElement' in element_info['className'] or
                element_info['hasGoogleAd']):
                ad_indicators.append('google_adsense')
            
            # 廣告位置2特徵: Criteo 廣告
            if (element_info['id'] == 'bnr' or
                'isSetup' in element_info['className'] or
                'criteo.com' in element_info['href'] or
                'imageholder' in element_info['className'] or
                'overflowHidden' in element_info['className']):
                ad_indicators.append('criteo_ad')
            
            # 廣告位置3特徵: Yahoo 右側 iframe 廣告
            if ('sda-' in element_info['id'] and 'iframe' in element_info['id'] or
                'min-w-[300px]' in element_info['className'] or
                'min-h-[250px]' in element_info['className'] or
                'min-h-[600px]' in element_info['className']):
                ad_indicators.append('yahoo_sidebar_ad')
            
            # 廣告位置4特徵: Yahoo 橫幅廣告
            if ('sda-top-center-iframe' in element_info['id'] or
                'google_ads_iframe_' in element_info['id'] or
                'tw_ynews_ros_dt_top_center' in element_info['id'] or
                'container__' in element_info['id'] or
                ('sticky' in element_info['className'] and 'z-index-1' in element_info['className'])):
                ad_indicators.append('yahoo_banner_ad')
            
            # iframe廣告特徵
            if (element_info['tagName'] == 'iframe' and
                ('googlesyndication' in element_info['src'] or
                 'safeframe' in element_info['src'] or
                 'doubleclick' in element_info['src'])):
                ad_indicators.append('iframe_ad')
            
            # 通用廣告特徵
            if (any(keyword in element_info['id'].lower() for keyword in ['ad', 'banner', 'advertisement']) or
                any(keyword in element_info['className'].lower() for keyword in ['ad', 'banner', 'advertisement', 'google']) or
                'doubleclick' in element_info['href'] or
                'googleadservices' in element_info['href'] or
                'clickTag' in element_info['onclick'] or
                element_info['parentHasAdFeatures']):
                ad_indicators.append('general_ad')
            
            # 如果有任何廣告特徵，認為是有效廣告
            is_valid = len(ad_indicators) > 0
            
            if is_valid:
                print(f"   ✅ 有效廣告元素: {element_info['tagName']} ({element_info['width']}x{element_info['height']}) 特徵: {', '.join(ad_indicators)}")
            
            return is_valid
            
        except Exception as e:
            print(f"   ❌ 廣告驗證失敗: {e}")
            return False
                  
    def get_button_style(self):
        """根據配置返回按鈕樣式 - 採用 ad_replacer.py 的標準設計"""
        button_style = getattr(self, 'button_style', BUTTON_STYLE)
        
        # 統一的資訊按鈕樣式 - 針對 Yahoo 網站優化，與叉叉按鈕間隔1px
        unified_info_button = {
            "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M7.5 1.5a6 6 0 100 12 6 6 0 100-12m0 1a5 5 0 110 10 5 5 0 110-10zM6.625 11h1.75V6.5h-1.75zM7.5 3.75a1 1 0 100 2 1 1 0 100-2z" fill="#00aecd"/></svg>',
            "style": 'position:absolute;top:1px;right:17px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);cursor:pointer;'
        }
        
        button_styles = {
            "dots": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="7.5" cy="3.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="7.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="11.5" r="1.5" fill="#00aecd"/></svg>',
                    "style": 'position:absolute;top:1px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;'
                },
                "info_button": unified_info_button
            },
            "cross": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 4L11 11M11 4L4 11" stroke="#00aecd" stroke-width="1.5" stroke-linecap="round"/></svg>',
                    "style": 'position:absolute;top:1px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;'
                },
                "info_button": unified_info_button
            },
            "adchoices": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 4L11 11M11 4L4 11" stroke="#00aecd" stroke-width="1.5" stroke-linecap="round"/></svg>',
                    "style": 'position:absolute;top:1px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;'
                },
                "info_button": {
                    "html": '<img src="https://tpc.googlesyndication.com/pagead/images/adchoices/adchoices_blue_wb.png" width="15" height="15" style="display:block;width:15px;height:15px;">',
                    "style": 'position:absolute;top:1px;right:17px;width:15px;height:15px;z-index:100;display:block;cursor:pointer;'
                }
            },
            "adchoices_dots": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="7.5" cy="3.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="7.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="11.5" r="1.5" fill="#00aecd"/></svg>',
                    "style": 'position:absolute;top:1px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;'
                },
                "info_button": {
                    "html": '<img src="https://tpc.googlesyndication.com/pagead/images/adchoices/adchoices_blue_wb.png" width="15" height="15" style="display:block;width:15px;height:15px;">',
                    "style": 'position:absolute;top:1px;right:17px;width:15px;height:15px;z-index:100;display:block;cursor:pointer;'
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
        try:
            # 獲取原始尺寸
            original_info = self.driver.execute_script("""
                var element = arguments[0];
                if (!element || !element.getBoundingClientRect) return null;
                var rect = element.getBoundingClientRect();
                return {width: rect.width, height: rect.height};
            """, element)
            
            if not original_info:
                return False
            
            # 檢查是否符合目標尺寸（允許 5 像素的容差）
            tolerance = 5
            width_match = abs(original_info['width'] - target_width) <= tolerance
            height_match = abs(original_info['height'] - target_height) <= tolerance
            
            if not (width_match and height_match):
                print(f"尺寸不匹配: 實際 {original_info['width']}x{original_info['height']}, 目標 {target_width}x{target_height}")
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
            
            # 安全的廣告替換，完全避免注入可能影響佈局的 CSS
            success = self.driver.execute_script("""
                // 不注入任何全域 CSS，使用內聯樣式確保不影響網頁佈局
                
                var container = arguments[0];
                var imageBase64 = arguments[1];
                var targetWidth = arguments[2];
                var targetHeight = arguments[3];
                var closeButtonHtml = arguments[4];
                var closeButtonStyle = arguments[5];
                var infoButtonHtml = arguments[6];
                var infoButtonStyle = arguments[7];
                var isNoneMode = arguments[8];
                
                if (!container) return false;
                
                // 檢查容器位置，但不強制修改為 relative 以避免影響佈局
                var containerPosition = window.getComputedStyle(container).position;
                var needsPositioning = (containerPosition === 'static');
                
                // 如果容器是 static，我們將使用 fixed 定位按鈕而不是修改容器
                console.log('容器位置:', containerPosition, '需要特殊定位:', needsPositioning);
                // 先移除舊的（避免重複）
                ['close_button', 'abgb'].forEach(function(id){
                  var old = container.querySelector('#'+id);
                  if(old) old.remove();
                });
                
                // 移除所有舊的按鈕（更徹底的清理）
                var allCloseButtons = container.querySelectorAll('#close_button');
                var allInfoButtons = container.querySelectorAll('#abgb');
                allCloseButtons.forEach(function(btn) { btn.remove(); });
                allInfoButtons.forEach(function(btn) { btn.remove(); });
                
                var replacedCount = 0;
                var newImageSrc = 'data:image/png;base64,' + imageBase64;
                
                // 方法1: 只替換img標籤的src，不移除元素
                var imgs = container.querySelectorAll('img');
                for (var i = 0; i < imgs.length; i++) {
                    var img = imgs[i];
                    // 排除Google廣告控制按鈕
                    var imgRect = img.getBoundingClientRect();
                    var isControlButton = imgRect.width < 50 || imgRect.height < 50 || 
                                         img.className.includes('abg') || 
                                         img.id.includes('abg') ||
                                         img.src.includes('googleads') ||
                                         img.src.includes('googlesyndication') ||
                                         img.src.includes('adchoices') ||
                                         img.src.includes('zh_tw.png') ||
                                         img.closest('#abgcp') ||
                                         img.closest('.abgcp') ||
                                         img.closest('#abgc') ||
                                         img.closest('.abgc') ||
                                         img.closest('#abgb') ||
                                         img.closest('.abgb') ||
                                         img.closest('#abgs') ||
                                         img.closest('.abgs') ||
                                         img.closest('#cbb') ||
                                         img.closest('.cbb') ||
                                         img.closest('label.cbb') ||
                                         img.closest('[data-vars-label*="feedback"]') ||
                                         img.alt.includes('關閉') ||
                                         img.alt.includes('close');
                    
                    if (!isControlButton && img.src && !img.src.startsWith('data:')) {
                        // 保存原始src以便復原
                        if (!img.getAttribute('data-original-src')) {
                            img.setAttribute('data-original-src', img.src);
                        }
                        // 替換圖片，保持原始尺寸和佈局
                        img.src = newImageSrc;
                        img.style.objectFit = 'contain';
                        img.style.width = '100%';
                        img.style.height = 'auto';
                        img.style.maxWidth = 'none';
                        img.style.maxHeight = 'none';
                        img.style.minWidth = 'auto';
                        img.style.minHeight = 'auto';
                        img.style.display = 'block';
                        img.style.margin = '0';
                        img.style.padding = '0';
                        img.style.border = 'none';
                        img.style.outline = 'none';
                        replacedCount++;
                    
                    // 獲取img的父層，但不修改其position屬性
                    var imgParent = img.parentElement || container;
                    var parentPosition = window.getComputedStyle(imgParent).position;
                    
                    // 先移除舊的按鈕
                    ['close_button', 'abgb'].forEach(function(id){
                        var old = imgParent.querySelector('#'+id);
                        if(old) old.remove();
                    });
                    
                    // 移除所有舊的按鈕（更徹底的清理）
                    var allCloseButtons = imgParent.querySelectorAll('#close_button');
                    var allInfoButtons = imgParent.querySelectorAll('#abgb');
                    allCloseButtons.forEach(function(btn) { btn.remove(); });
                    allInfoButtons.forEach(function(btn) { btn.remove(); });
                    
                    // 只有在非 none 模式下才創建按鈕
                    if (!isNoneMode && closeButtonHtml && infoButtonHtml) {
                        // 叉叉 - 使用動態樣式並添加標記
                        var closeButton = document.createElement('div');
                        closeButton.id = 'close_button_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                        closeButton.innerHTML = closeButtonHtml;
                        closeButton.style.cssText = closeButtonStyle;
                        closeButton.setAttribute('data-injected', 'true');  // 添加標記
                        closeButton.setAttribute('data-ad-replacer', 'close-button');  // 添加類型標記
                        
                        // 驚嘆號 - 使用動態樣式並添加標記
                        var abgb = document.createElement('div');
                        abgb.id = 'abgb_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                        abgb.className = 'abgb';
                        abgb.innerHTML = infoButtonHtml;
                        abgb.style.cssText = infoButtonStyle;
                        abgb.setAttribute('data-injected', 'true');  // 添加標記
                        abgb.setAttribute('data-ad-replacer', 'info-button');  // 添加類型標記
                        
                        // 將按鈕添加到img的父層（驚嘆號在左，叉叉在右）
                        imgParent.appendChild(abgb);
                        imgParent.appendChild(closeButton);
                    }
                }
                }
                // 方法2: 處理iframe
                var iframes = container.querySelectorAll('iframe');
                for (var i = 0; i < iframes.length; i++) {
                    var iframe = iframes[i];
                    var iframeRect = iframe.getBoundingClientRect();
                    
                    // 隱藏iframe
                    iframe.style.visibility = 'hidden';
                    
                    // 確保容器是relative
                    if (window.getComputedStyle(container).position === 'static') {
                        container.style.position = 'relative';
                    }
                    
                    // 在iframe位置創建新的圖片元素，保持原始佈局
                    var newImg = document.createElement('img');
                    newImg.src = newImageSrc;
                    newImg.style.position = 'absolute';
                    newImg.style.top = (iframeRect.top - container.getBoundingClientRect().top) + 'px';
                    newImg.style.left = (iframeRect.left - container.getBoundingClientRect().left) + 'px';
                    newImg.style.width = Math.round(iframeRect.width) + 'px';
                    newImg.style.height = Math.round(iframeRect.height) + 'px';
                    newImg.style.objectFit = 'contain';
                    newImg.style.zIndex = '1';
                    newImg.style.maxWidth = 'none';
                    newImg.style.maxHeight = 'none';
                    newImg.style.minWidth = 'auto';
                    newImg.style.minHeight = 'auto';
                    newImg.style.display = 'block';
                    newImg.style.margin = '0';
                    newImg.style.padding = '0';
                    newImg.style.border = 'none';
                    newImg.style.outline = 'none';
                    newImg.setAttribute('data-injected', 'true');  // 添加標記
                    newImg.setAttribute('data-ad-replacer', 'replacement-image');  // 添加類型標記
                    
                    container.appendChild(newImg);
                    
                                            // 先移除舊的按鈕
                        ['close_button', 'abgb'].forEach(function(id){
                            var old = container.querySelector('#'+id);
                            if(old) old.remove();
                        });
                        
                        // 移除所有舊的按鈕（更徹底的清理）
                        var allCloseButtons = container.querySelectorAll('#close_button');
                        var allInfoButtons = container.querySelectorAll('#abgb');
                        allCloseButtons.forEach(function(btn) { btn.remove(); });
                        allInfoButtons.forEach(function(btn) { btn.remove(); });
                    
                    // 移除所有舊的按鈕（更徹底的清理）
                    var allCloseButtons = container.querySelectorAll('#close_button');
                    var allInfoButtons = container.querySelectorAll('#abgb');
                    allCloseButtons.forEach(function(btn) { btn.remove(); });
                    allInfoButtons.forEach(function(btn) { btn.remove(); });
                    
                    // 只有在非 none 模式下才創建按鈕
                    if (!isNoneMode && closeButtonHtml && infoButtonHtml) {
                        // 叉叉 - 使用動態樣式並添加標記
                        var closeButton = document.createElement('div');
                        closeButton.id = 'close_button_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                        closeButton.innerHTML = closeButtonHtml;
                        closeButton.style.cssText = 'position:absolute;top:' + (iframeRect.top - container.getBoundingClientRect().top + 1) + 'px;right:' + (container.getBoundingClientRect().right - iframeRect.right + 1) + 'px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);line-height:0;';
                        closeButton.setAttribute('data-injected', 'true');  // 添加標記
                        closeButton.setAttribute('data-ad-replacer', 'close-button');  // 添加類型標記
                        
                        // 驚嘆號 - 使用動態樣式並添加標記
                        var abgb = document.createElement('div');
                        abgb.id = 'abgb_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                        abgb.className = 'abgb';
                        abgb.innerHTML = infoButtonHtml;
                        abgb.style.cssText = 'position:absolute;top:' + (iframeRect.top - container.getBoundingClientRect().top + 1) + 'px;right:' + (container.getBoundingClientRect().right - iframeRect.right + 17) + 'px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);line-height:0;';
                        abgb.setAttribute('data-injected', 'true');  // 添加標記
                        abgb.setAttribute('data-ad-replacer', 'info-button');  // 添加類型標記
                        
                        // 將按鈕添加到container內，與圖片同層
                        container.appendChild(abgb);
                        container.appendChild(closeButton);
                    }
                    replacedCount++;
                }
                // 方法3: 處理背景圖片
                if (replacedCount === 0) {
                    var style = window.getComputedStyle(container);
                    if (style.backgroundImage && style.backgroundImage !== 'none') {
                        container.style.backgroundImage = 'url(' + newImageSrc + ')';
                        container.style.backgroundSize = 'contain';
                        container.style.backgroundRepeat = 'no-repeat';
                        container.style.backgroundPosition = 'center';
                        container.style.backgroundAttachment = 'scroll';
                        container.style.backgroundOrigin = 'border-box';
                        container.style.backgroundClip = 'border-box';
                        replacedCount = 1;
                        
                        // 確保容器是relative
                        if (window.getComputedStyle(container).position === 'static') {
                            container.style.position = 'relative';
                        }
                        
                        // 先移除舊的按鈕
                        ['close_button', 'abgb'].forEach(function(id){
                            var old = container.querySelector('#'+id);
                            if(old) old.remove();
                        });
                        
                        // 只有在非 none 模式下才創建按鈕
                        if (!isNoneMode && closeButtonHtml && infoButtonHtml) {
                            // 添加兩個按鈕 - 使用動態樣式並添加標記
                            var closeButton = document.createElement('div');
                            closeButton.id = 'close_button_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                            closeButton.innerHTML = closeButtonHtml;
                            closeButton.style.cssText = closeButtonStyle;
                            closeButton.setAttribute('data-injected', 'true');  // 添加標記
                            closeButton.setAttribute('data-ad-replacer', 'close-button');  // 添加類型標記
                            
                            var abgb = document.createElement('div');
                            abgb.id = 'abgb_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                            abgb.className = 'abgb';
                            abgb.innerHTML = infoButtonHtml;
                            abgb.style.cssText = infoButtonStyle;
                            abgb.setAttribute('data-injected', 'true');  // 添加標記
                            abgb.setAttribute('data-ad-replacer', 'info-button');  // 添加類型標記
                            
                            // 將按鈕添加到container內，與背景圖片同層
                            container.appendChild(abgb);
                            container.appendChild(closeButton);
                        }
                    }
                }
                return replacedCount > 0;
            """, element, image_data, target_width, target_height, close_button_html, close_button_style, info_button_html, info_button_style, is_none_mode)
            
            if success:
                print(f"替換廣告 {original_info['width']}x{original_info['height']}")
                return True
            else:
                print(f"廣告替換失敗 {original_info['width']}x{original_info['height']}")
                return False
                
        except Exception as e:
            print(f"替換廣告失敗: {e}")
            return False
    
    def process_website(self, url):
        """處理單個網站，使用 Yahoo GIF 選擇策略 + 錯誤處理"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"\n開始處理網站: {url}")
                if attempt > 0:
                    print(f"重試第 {attempt}/{max_retries-1} 次...")
                
                # 載入網頁 - 加入重試機制
                self.driver.set_page_load_timeout(30)  # 增加超時時間
                
                try:
                    self.driver.get(url)
                    print("✅ 網頁載入成功")
                except Exception as load_error:
                    print(f"❌ 網頁載入失敗: {load_error}")
                    if attempt < max_retries - 1:
                        print(f"等待 5 秒後重試...")
                        time.sleep(5)
                        continue
                    else:
                        raise load_error
                
                # 等待5秒讓廣告完全載入
                print("⏳ 等待 5 秒讓廣告完全載入...")
                time.sleep(5)
                
                # 獲取頁面標題
                page_title = self.driver.title
                print(f"📰 頁面標題: {page_title}")
                
                # 使用新的全面掃描模式：一次掃描所有廣告，然後按尺寸處理
                total_replacements = 0
                screenshot_paths = []  # 儲存所有截圖路徑
                
                # 先進行一次全面掃描，找到所有廣告
                print(f"\n🔍 全面掃描網站廣告...")
                all_ads = self.find_all_yahoo_ads()
                
                if not all_ads:
                    print("❌ 未找到任何廣告")
                    return []
                
                # 按替換圖片尺寸處理廣告
                for size_key in self.images_by_size.keys():
                    try:
                        target_width, target_height = map(int, size_key.split('x'))
                    except:
                        continue
                    
                    print(f"\n🔍 處理尺寸: {size_key}")
                    
                    # 獲取該尺寸的圖片組
                    static_images = self.images_by_size[size_key]['static']
                    gif_images = self.images_by_size[size_key]['gif']
                    
                    print(f"   可用圖片: {len(static_images)}張靜態 + {len(gif_images)}張GIF")
                    
                    # 使用 Yahoo 優先級策略選擇圖片
                    selected_image = self.select_image_by_strategy(static_images, gif_images, size_key)
                    
                    if not selected_image:
                        print(f"   ❌ 沒有可用的 {size_key} 圖片")
                        continue
                    
                    # 載入選中的圖片
                    try:
                        image_data = self.load_image_base64(selected_image['path'])
                    except Exception as e:
                        print(f"載入圖片失敗: {e}")
                        continue
                    
                    # 重新掃描並立即替換符合尺寸的廣告（避免stale element問題）
                    print(f"🎯 尋找 {size_key} 的廣告...")
                    replaced = False
                    processed_positions = set()  # 記錄已處理的位置
                    
                    # 重新掃描頁面，找到符合尺寸的廣告並立即替換
                    matching_ads = self.find_and_replace_ads_immediately(target_width, target_height, image_data, selected_image, processed_positions)
                    
                    if matching_ads > 0:
                        print(f"   ✅ 成功替換 {matching_ads} 個 {size_key} 廣告")
                        replaced = True
                        total_replacements += matching_ads
                        
                        # 替換成功後滑動到廣告位置並截圖
                        print("📍 滑動到廣告位置...")
                        self.scroll_to_ads_for_screenshot(target_width, target_height)
                        
                        print("📸 正在截圖...")
                        screenshot_path = self.take_screenshot(page_title)
                        if screenshot_path:
                            screenshot_paths.append(screenshot_path)
                            self.total_screenshots += 1
                            print(f"✅ 截圖完成: {screenshot_path}")
                            
                            # 更新統計
                            if selected_image['type'] == 'GIF':
                                self.gif_replacements += 1
                            else:
                                self.static_replacements += 1
                            
                            # 記錄替換詳情
                            self.replacement_details.append({
                                'size': size_key,
                                'type': selected_image['type'],
                                'filename': selected_image['filename'],
                                'count': matching_ads
                            })
                            
                            # 檢查是否達到截圖數量限制
                            if self.total_screenshots >= SCREENSHOT_COUNT:
                                print(f"🎯 已達到截圖數量限制 ({SCREENSHOT_COUNT})")
                                return screenshot_paths
                        
                        # 截圖後等待1秒，然後還原廣告
                        print("🔄 正在還原廣告...")
                        time.sleep(1)
                        self.restore_ads()
                        print("✅ 廣告已還原")
                        
                    else:
                        print(f"   ❌ 未找到符合 {size_key} 尺寸的廣告")
                
                if total_replacements > 0:
                    print(f"\n✅ 成功替換 {total_replacements} 個廣告")
                    return screenshot_paths
                else:
                    print("\n❌ 本網頁沒有找到任何可替換的廣告")
                    return []
                    
            except Exception as e:
                print(f"第 {attempt + 1} 次嘗試失敗: {e}")
                if attempt < max_retries - 1:
                    print(f"等待 10 秒後重試...")
                    time.sleep(10)
                    continue
                else:
                    print(f"所有重試都失敗，跳過此網站: {url}")
                    return []
    
    def take_screenshot(self, page_title=None):
        if not os.path.exists(SCREENSHOT_FOLDER):
            os.makedirs(SCREENSHOT_FOLDER)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 處理頁面標題，移除特殊字符
        if page_title:
            # 移除特殊字符，只保留中文、英文、數字
            import re
            clean_title = re.sub(r'[^\u4e00-\u9fff\w\s]', '', page_title)
            # 限制標題長度，避免檔案名過長
            clean_title = clean_title[:30].strip()
            # 替換空格為底線
            clean_title = clean_title.replace(' ', '_')
            filepath = f"{SCREENSHOT_FOLDER}/yahoo_{clean_title}_{timestamp}.png"
        else:
            filepath = f"{SCREENSHOT_FOLDER}/yahoo_replaced_{timestamp}.png"
        
        try:
            # 確保頁面完全穩定
            time.sleep(2)  # 等待頁面穩定
            
            # 檢查頁面是否仍在載入
            page_state = self.driver.execute_script("return document.readyState;")
            if page_state != "complete":
                print(f"頁面仍在載入中 (readyState: {page_state})，等待...")
                time.sleep(3)
            
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
                    print(f"❌ MSS 截圖失敗: {e}")
                    import traceback
                    traceback.print_exc()
                    print("使用 pyautogui 備用方案")
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
            print(f"截圖失敗: {e}")
            import traceback
            traceback.print_exc()
            print("使用 Selenium 截圖")
            try:
                self.driver.save_screenshot(filepath)
                print(f"截圖保存: {filepath}")
                return filepath
            except Exception as e2:
                print(f"Selenium 截圖也失敗: {e2}")
                import traceback
                traceback.print_exc()
                return None
    
    def find_and_replace_ads_immediately(self, target_width, target_height, image_data, selected_image, processed_positions, tolerance=10):
        """重新掃描頁面並立即替換符合尺寸的廣告，避免stale element問題"""
        replaced_count = 0
        
        # 重新掃描所有廣告選擇器
        all_selectors = [
            # Yahoo 特定選擇器
            'div[class*="ad"]',
            'div[id*="ad"]', 
            'div[class*="sticky"]',
            'div[data-google-query-id]',
            'div[id*="google_ads"]',
            'div[id*="google_ads_iframe_"]',
            'div[id*="container__"]',
            'div[id*="sda-"][id*="-iframe"]',
            'div[id="sda-top-center-iframe"]',
            'div[id="sda-top-right-iframe"]',
            'div[id="sda-mid-right-iframe"]',
            'div[id="sda-mid-right-2-iframe"]',
            'div[id*="tw_ynews_ros_dt_top_center"]',
            'iframe[src*="googlesyndication.com"]',
            'iframe[src*="doubleclick"]',
            'iframe[src*="safeframe.googlesyndication.com"]',
            # 通用廣告選擇器
            'div[class*="w-full"]',
            'div[class*="shrink-0"]',
            'div[class*="min-h-[250px]"]',
            'div[class*="min-w-[300px]"]',
            'div[class*="mb-module-gap"]',
            'div[class*="z-index-1"]',
            'aside[class*="mt-module-gap"]'
        ]
        
        for selector in all_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for element in elements:
                    try:
                        # 檢查元素是否可見且有尺寸
                        if not element.is_displayed():
                            continue
                            
                        size = element.size
                        location = element.location
                        width = size['width']
                        height = size['height']
                        
                        # 跳過太小的元素
                        if width < 50 or height < 50:
                            continue
                        
                        # 檢查尺寸是否匹配
                        if (abs(width - target_width) <= tolerance and 
                            abs(height - target_height) <= tolerance):
                            
                            # 檢查是否已經處理過這個位置
                            position_key = f"{location['x']}_{location['y']}_{width}x{height}"
                            if position_key in processed_positions:
                                continue
                            
                            # 立即嘗試替換
                            if self.replace_ad_content(element, image_data, target_width, target_height):
                                print(f"   ✅ 成功替換 {selected_image['type']}: {selected_image['filename']} at top:{location['y']}, left:{location['x']}")
                                replaced_count += 1
                                processed_positions.add(position_key)
                                
                                # 限制每個尺寸最多替換的廣告數量
                                if replaced_count >= 3:  # 每個尺寸最多替換3個廣告
                                    return replaced_count
                            
                    except Exception as e:
                        # 忽略個別元素的錯誤，繼續處理下一個
                        continue
                        
            except Exception as e:
                # 忽略選擇器錯誤，繼續下一個選擇器
                continue
        
        return replaced_count

    def scroll_to_ads_for_screenshot(self, target_width, target_height, tolerance=10):
        """滑動到廣告位置，讓按鈕出現在螢幕上25%的位置"""
        try:
            # 重新找到符合尺寸的廣告元素
            all_selectors = [
                'div[class*="ad"]',
                'div[id*="ad"]', 
                'div[data-google-query-id]',
                'div[id*="google_ads_iframe_"]',
                'div[id*="sda-"][id*="-iframe"]',
                'iframe[src*="googlesyndication.com"]'
            ]
            
            ad_elements = []
            
            for selector in all_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        try:
                            if not element.is_displayed():
                                continue
                                
                            size = element.size
                            location = element.location
                            width = size['width']
                            height = size['height']
                            
                            # 檢查尺寸是否匹配
                            if (abs(width - target_width) <= tolerance and 
                                abs(height - target_height) <= tolerance):
                                ad_elements.append({
                                    'element': element,
                                    'top': location['y'],
                                    'left': location['x'],
                                    'width': width,
                                    'height': height
                                })
                        except:
                            continue
                except:
                    continue
            
            if not ad_elements:
                print("   ⚠️ 未找到廣告元素，無法滑動")
                return
            
            # 選擇第一個廣告元素進行滑動
            target_ad = ad_elements[0]
            
            # 獲取視窗高度
            viewport_height = self.driver.execute_script("return window.innerHeight;")
            
            # 計算滑動位置：讓廣告頂部出現在螢幕上25%的位置
            scroll_position = target_ad['top'] - (viewport_height * 0.25)
            
            # 確保滑動位置不會是負數
            scroll_position = max(0, scroll_position)
            
            # 滑動到計算的位置
            self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
            print(f"   ✅ 滑動到位置: {scroll_position:.0f}px (廣告將出現在螢幕上25%位置)")
            
            # 等待滑動完成
            time.sleep(1)
            
        except Exception as e:
            print(f"   ⚠️ 滑動失敗: {e}")

    def restore_ads(self):
        """還原所有被替換的廣告"""
        try:
            self.driver.execute_script("""
                // 還原所有被替換的圖片
                var replacedImages = document.querySelectorAll('img[data-original-src]');
                for (var i = 0; i < replacedImages.length; i++) {
                    var img = replacedImages[i];
                    var originalSrc = img.getAttribute('data-original-src');
                    if (originalSrc) {
                        img.src = originalSrc;
                        img.removeAttribute('data-original-src');
                    }
                }
                
                // 移除所有注入的按鈕
                var buttons = document.querySelectorAll('[data-ad-replacer]');
                for (var i = 0; i < buttons.length; i++) {
                    buttons[i].remove();
                }
                
                // 還原被隱藏的iframe
                var hiddenIframes = document.querySelectorAll('iframe[style*="visibility: hidden"]');
                for (var i = 0; i < hiddenIframes.length; i++) {
                    hiddenIframes[i].style.visibility = 'visible';
                }
                
                // 還原背景圖片
                var elementsWithBg = document.querySelectorAll('[data-original-background]');
                for (var i = 0; i < elementsWithBg.length; i++) {
                    var element = elementsWithBg[i];
                    var originalBg = element.getAttribute('data-original-background');
                    if (originalBg) {
                        element.style.backgroundImage = originalBg;
                        element.removeAttribute('data-original-background');
                    }
                }
                
                console.log('✅ 廣告還原完成');
            """)
        except Exception as e:
            print(f"還原廣告時發生錯誤: {e}")

    def close(self):
        self.driver.quit()

def main():
    # 偵測並選擇螢幕
    screen_id, selected_screen = ScreenManager.select_screen()
    
    if screen_id is None:
        print("未選擇螢幕，程式結束")
        return
    
    print(f"\n正在啟動 Chrome 瀏覽器到螢幕 {screen_id}...")
    bot = YahooAdReplacer(headless=False, screen_id=screen_id)
    
    try:
        # 使用 Yahoo 新聞熱門景點版面的 URL
        yahoo_url = YAHOO_BASE_URL
        print(f"目標網站: {yahoo_url}")
        
        # 尋找新聞連結
        news_urls = bot.get_random_news_urls(yahoo_url, NEWS_COUNT)
        
        if not news_urls:
            print("無法獲取新聞連結")
            return
        
        # 檢查獲取的連結是否都是熱門景點版面的
        tourist_urls = []
        for url in news_urls:
            # 簡化的熱門景點版面檢查 - 只要來自 Yahoo 新聞且包含 .html 就接受
            if ('yahoo.com' in url and 
                'tw.news.yahoo.com' in url and
                '.html' in url and
                not any(exclude in url.lower() for exclude in ['/mail/', '/shopping/', '/auction/', '/finance/', '/sports/', '/politics/', '/international/', '/society/', '/health/', '/taste/', '/weather/', '/archive/', '/most-popular/', '/topic/', 'login', 'signin', 'register', 'account', 'profile', 'settings', 'help', 'about', 'contact', 'privacy', 'terms'])):
                tourist_urls.append(url)
                print(f"✅ 確認 Yahoo 新聞連結: {url}")
            else:
                print(f"❌ 跳過非 Yahoo 新聞連結: {url}")
        
        if not tourist_urls:
            print("沒有找到有效的熱門景點版面連結")
            return
        
        print(f"獲取到 {len(tourist_urls)} 個熱門景點版面新聞連結")
        print(f"目標截圖數量: {SCREENSHOT_COUNT}")
        
        # 使用過濾後的熱門景點版面連結
        news_urls = tourist_urls
        
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
                    print("❌ 網站處理完成，但沒有找到可替換的廣告或主題不符")
                
            except Exception as e:
                print(f"❌ 處理網站失敗: {e}")
                print("繼續處理下一個網站...")
                continue
            
            # 在處理下一個網站前稍作休息
            if i < len(news_urls) and total_screenshots < SCREENSHOT_COUNT:
                print("等待 3 秒後處理下一個網站...")
                time.sleep(3)
            
            # 如果處理的網站數量超過一半但截圖數量不足，重新獲取更多連結
            if i >= len(news_urls) // 2 and total_screenshots < SCREENSHOT_COUNT // 2:
                print("⚠️  截圖數量不足，嘗試重新獲取更多熱門景點連結...")
                try:
                    additional_urls = bot.get_random_news_urls(yahoo_url, NEWS_COUNT // 2)
                    if additional_urls:
                        # 過濾出熱門景點相關的連結
                        additional_tourist_urls = []
                        for url in additional_urls:
                            if ('yahoo.com' in url and 
                                ('/tourist-spots' in url or 'tw.news.yahoo.com' in url) and
                                any(keyword in url.lower() for keyword in ['景點', '旅遊', '美食', '住宿', '旅宿', '避暑', '秘境', '風景', '觀光', '度假', '溫泉', '海灘', '山景', '湖景', '古蹟', '建築', '步道', '輕旅行', '週末', '假期', '夏日', '涼夏', '療癒', '美景', '拍照', '打卡', 'instagram', '淡水', '榕堤', '夕陽', '旅館', '飯店', '民宿', '度假村'])):
                                additional_tourist_urls.append(url)
                        
                        if additional_tourist_urls:
                            news_urls.extend(additional_tourist_urls)
                            print(f"✅ 新增 {len(additional_tourist_urls)} 個熱門景點連結")
                        else:
                            print("❌ 無法獲取額外的熱門景點連結")
                except Exception as e:
                    print(f"重新獲取連結失敗: {e}")
        
        # 顯示 Yahoo 風格的詳細統計報告
        print(f"\n📊 Yahoo 廣告替換統計報告 - GIF 升級版")
        print("="*60)
        print(f"📸 總截圖數量: {bot.total_screenshots} 張")
        print(f"🔄 總替換次數: {bot.total_replacements} 次")
        if bot.gif_replacements > 0 or bot.static_replacements > 0:
            gif_percentage = (bot.gif_replacements / bot.total_replacements * 100) if bot.total_replacements > 0 else 0
            static_percentage = (bot.static_replacements / bot.total_replacements * 100) if bot.total_replacements > 0 else 0
            print(f"   🎬 GIF 替換: {bot.gif_replacements} 次 ({gif_percentage:.1f}%)")
            print(f"   🖼️ 靜態圖片替換: {bot.static_replacements} 次 ({static_percentage:.1f}%)")
        
        if bot.replacement_details:
            print(f"\n📋 詳細替換記錄:")
            for i, detail in enumerate(bot.replacement_details, 1):
                type_icon = "🎬" if detail['type'] == "GIF" else "🖼️"
                print(f"    {i}. {type_icon} {detail['filename']} ({detail['size']}) → 📸 {detail['screenshot']}")
        
        # 顯示當前 GIF 策略
        try:
            gif_priority = globals().get('GIF_PRIORITY', True)
            strategy_text = "GIF 優先" if gif_priority else "靜態圖片優先"
            print(f"\n⚙️ 當前 GIF 策略:")
            print(f"   🎯 優先級模式 - {strategy_text} (GIF_PRIORITY = {gif_priority})")
        except:
            pass
        
        print("="*60)
        
    finally:
        bot.close()

def test_screen_setup():
    """測試螢幕設定功能"""
    print("測試螢幕偵測功能...")
    
    # 偵測螢幕
    screens = ScreenManager.detect_screens()
    print(f"偵測到 {len(screens)} 個螢幕:")
    
    for screen in screens:
        primary_text = " (主螢幕)" if screen['primary'] else ""
        print(f"  螢幕 {screen['id']}: {screen['resolution']}{primary_text}")
    
    # 讓使用者選擇螢幕進行測試
    screen_id, selected_screen = ScreenManager.select_screen()
    
    if screen_id is None:
        return
    
    print(f"\n正在測試螢幕 {screen_id}...")
    
    # 創建測試用的瀏覽器實例
    test_bot = YahooAdReplacer(headless=False, screen_id=screen_id)
    
    try:
        # 開啟測試頁面
        test_bot.driver.get("https://www.google.com")
        time.sleep(3)
        
        # 測試截圖功能
        print("測試截圖功能...")
        screenshot_path = test_bot.take_screenshot("測試頁面")
        
        if screenshot_path:
            print(f"✅ 螢幕 {screen_id} 設定成功！")
            print(f"測試截圖已保存: {screenshot_path}")
        else:
            print(f"❌ 螢幕 {screen_id} 截圖失敗")
        
        input("按 Enter 鍵關閉測試...")
        
    finally:
        test_bot.close()

if __name__ == "__main__":
    import sys
    
    # 檢查是否有命令列參數
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_screen_setup()
    else:
        main()