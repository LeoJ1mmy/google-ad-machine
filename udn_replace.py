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

# 載入 GIF 功能專用設定檔
try:
    from gif_config import *
    print("成功載入 gif_config.py 設定檔")
    print(f"SCREENSHOT_COUNT 設定: {SCREENSHOT_COUNT}")
    print(f"NEWS_COUNT 設定: {NEWS_COUNT}")
    print(f"IMAGE_USAGE_COUNT 設定: {IMAGE_USAGE_COUNT}")
    print(f"GIF_PRIORITY 設定: {GIF_PRIORITY}")
    # 覆蓋 gif_config.py 中的 BASE_URL，設定 UDN 專用網址
    UDN_BASE_URL = "https://travel.udn.com/travel/index"
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
    BASE_URL = "https://travel.udn.com/travel/index"
    UDN_BASE_URL = "https://travel.udn.com/travel/index"  # 聯合報 旅遊網站
    NEWS_COUNT = 20
    TARGET_AD_SIZES = []  # 將由 load_replace_images() 動態生成
    IMAGE_USAGE_COUNT = {"google_970x90.jpg": 5, "google_986x106.jpg": 3}
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
    
    @staticmethod
    def get_screen_info(screen_id):
        """獲取指定螢幕的詳細資訊"""
        screens = ScreenManager.detect_screens()
        for screen in screens:
            if screen['id'] == screen_id:
                return screen
        return None

class UdnAdReplacer:
    def __init__(self, headless=False, screen_id=1):
        print("正在初始化 UDN 廣告替換器 - GIF 升級版...")
        self.screen_id = screen_id
        
        # 統計變數 - 採用 ETtoday 模式
        self.total_screenshots = 0      # 總截圖數量
        self.total_replacements = 0     # 總替換次數
        self.gif_replacements = 0       # GIF 替換次數
        self.static_replacements = 0    # 靜態圖片替換次數
        self.replacement_details = []   # 詳細替換記錄
        
        self.setup_driver(headless)
        self.load_replace_images()
        print("UDN 廣告替換器 - GIF 升級版")
        
    def setup_driver(self, headless):
        print("正在設定 Chrome 瀏覽器 - 網路穩定版...")
        chrome_options = Options()
        
        if headless or HEADLESS_MODE:
            chrome_options.add_argument('--headless')
        
        # 基本設定
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # 網路穩定性設定
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images=false')  # 確保圖片載入
        
        # 增加穩定性設定
        chrome_options.add_argument('--disable-gpu')  # 禁用GPU加速，避免GPU錯誤
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--no-default-browser-check')
        
        # 網路和載入優化
        chrome_options.add_argument('--aggressive-cache-discard')
        chrome_options.add_argument('--memory-pressure-off')
        chrome_options.add_argument('--max_old_space_size=4096')
        
        # SSL 和網路設定
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 多螢幕支援 - 計算螢幕偏移量
        if self.screen_id > 1:
            screen_offset = (self.screen_id - 1) * 1920
            chrome_options.add_argument(f'--window-position={screen_offset},0')
        
        # 默認全螢幕設定
        chrome_options.add_argument('--start-maximized')
        if not headless:
            chrome_options.add_argument('--start-fullscreen')
        
        print("正在啟動 Chrome 瀏覽器...")
        self.driver = webdriver.Chrome(options=chrome_options)
        print("Chrome 瀏覽器啟動成功！")
        
        # 設置超時時間
        self.driver.set_page_load_timeout(30)  # 增加到30秒
        self.driver.implicitly_wait(10)  # 隱式等待10秒
        print("瀏覽器設置完成！")
        
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
        """載入替換圖片並解析尺寸 - ETtoday GIF 升級版"""
        self.replace_images = []
        self.images_by_size = {}  # 按尺寸分組的圖片字典
        
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
        """根據 GIF_PRIORITY 配置選擇圖片 - ETtoday 優先級模式"""
        
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
        """更新截圖統計並返回檔案路徑 - ETtoday 統計模式"""
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
        try:
            print(f"正在載入網頁: {base_url}")
            self.driver.get(base_url)
            print(f"等待 {WAIT_TIME} 秒讓頁面載入...")
            time.sleep(WAIT_TIME)
            
            # 額外等待時間確保頁面完全載入
            print("額外等待 5 秒確保頁面完全載入...")
            time.sleep(5)
            
            # 檢查頁面是否成功載入
            page_title = self.driver.title
            print(f"頁面標題: {page_title}")
            
            # 檢查是否有錯誤頁面
            if "404" in page_title or "錯誤" in page_title or "Error" in page_title:
                print("❌ 頁面載入失敗，可能是404錯誤")
                return []
            
            # 聯合報旅遊網站的連結選擇器
            link_selectors = [
                "a[href*='/travel/story/']",                    # 旅遊故事連結
                "a[href*='/travel/article/']",                  # 旅遊文章連結
                "a[href*='/travel/spot/']",                     # 景點連結
                "a[href*='/travel/food/']",                     # 美食連結
                "a[href*='/travel/hotel/']",                    # 住宿連結
                "a[href*='/travel/activity/']",                 # 活動連結
                "a[href*='/travel/']",                          # 所有旅遊連結
                "h3 a[href*='travel.udn.com']",                 # 標題中的旅遊連結
                "h2 a[href*='travel.udn.com']",                 # 二級標題中的旅遊連結
                "a[href*='travel.udn.com'][href*='.html']",     # 所有 HTML 旅遊連結
                "a[href*='travel.udn.com']",                    # 旅遊網域連結
                "a[href*='travel']",                            # 包含travel的連結
                "a[href*='旅遊']",                              # 包含旅遊的連結
                "a[href*='景點']",                              # 包含景點的連結
                "a[href*='美食']",                              # 包含美食的連結
                "a[href*='住宿']",                              # 包含住宿的連結
                "a[href*='活動']",                              # 包含活動的連結
                "a[href*='story']",                             # 故事連結
                "a[href*='article']",                           # 文章連結
            ]
            
            news_urls = []
            print(f"開始搜尋旅遊連結，使用 {len(link_selectors)} 個選擇器...")
            
            for i, selector in enumerate(link_selectors):
                links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"選擇器 {i+1}: '{selector}' 找到 {len(links)} 個連結")
                for link in links:
                    href = link.get_attribute('href')
                    if href and href not in news_urls and 'travel.udn.com' in href:
                        # 檢查是否為有效的旅遊文章連結
                        is_valid_travel = any(keyword in href.lower() for keyword in [
                            'travel.udn.com', 'story', 'article', 'spot', 'food', 'hotel', 'activity',
                            'travel', '旅遊', '景點', '美食', '住宿', '活動'
                        ])
                        
                        # 排除明顯的非旅遊連結
                        is_not_travel = any(exclude in href.lower() for exclude in [
                            '/news/', '/opinion/', '/sports/', '/entertainment/', '/society/', 
                            '/politics/', '/international/', '/business/', '/tech/',
                            'login', 'signin', 'register', 'account', 'profile', 'settings', 
                            'help', 'about', 'contact', 'privacy', 'terms', 'index'
                        ])
                        
                        # 確保是具體的旅遊文章而不是分類頁面
                        is_article_page = ('.html' in href or '/story/' in href or '/article/' in href) and not href.endswith('/')
                        
                        if is_valid_travel and not is_not_travel and is_article_page:
                            news_urls.append(href)
                            print(f"✅ 找到旅遊文章連結: {href}")
                        else:
                            print(f"❌ 排除連結: {href} (valid:{is_valid_travel}, not_travel:{is_not_travel}, article:{is_article_page})")
                        
            # 使用 ETtoday 模式：順序選擇而非隨機選擇
            selected_urls = news_urls[:min(NEWS_COUNT, len(news_urls))]
            print(f"選擇前 {len(selected_urls)} 個旅遊文章連結:")
            for i, url in enumerate(selected_urls):
                print(f"  {i+1}. {url}")
            return selected_urls
        except Exception as e:
            print(f"獲取旅遊連結失敗: {e}")
            return []
    
    def scan_entire_page_for_ads(self, target_width, target_height):
        """掃描整個網頁尋找符合尺寸的廣告元素"""
        print(f"開始掃描整個網頁尋找 {target_width}x{target_height} 的廣告...")
        
        # 專門獲取 Google Ads 相關元素
        all_elements = self.driver.execute_script("""
            function getGoogleAdsElements() {
                var googleAdsElements = [];
                
                // 1. 直接選擇 Google Ads 容器
                var googleAdContainers = document.querySelectorAll('div[id*="google_ads"], div[id*="ads-"], div[class*="google"], div[class*="ads"]');
                for (var i = 0; i < googleAdContainers.length; i++) {
                    googleAdsElements.push(googleAdContainers[i]);
                }
                
                // 2. 選擇 Google Ads iframe
                var googleIframes = document.querySelectorAll('iframe[src*="googleads"], iframe[src*="googlesyndication"], iframe[src*="doubleclick"]');
                for (var i = 0; i < googleIframes.length; i++) {
                    googleAdsElements.push(googleIframes[i]);
                }
                
                // 3. 選擇包含 Google Ads 腳本的元素
                var scriptElements = document.querySelectorAll('script[src*="google"]');
                for (var i = 0; i < scriptElements.length; i++) {
                    var parent = scriptElements[i].parentElement;
                    if (parent && !googleAdsElements.includes(parent)) {
                        googleAdsElements.push(parent);
                    }
                }
                
                // 4. 選擇包含 googletag 腳本的元素
                var allScripts = document.querySelectorAll('script');
                for (var i = 0; i < allScripts.length; i++) {
                    var script = allScripts[i];
                    if (script.textContent && script.textContent.includes('googletag')) {
                        var parent = script.parentElement;
                        if (parent && !googleAdsElements.includes(parent)) {
                            googleAdsElements.push(parent);
                        }
                    }
                }
                
                // 5. 選擇 udn-ads 類別的元素（聯合報特定的廣告容器）
                var udnAdsElements = document.querySelectorAll('.udn-ads, [class*="udn-ads"]');
                for (var i = 0; i < udnAdsElements.length; i++) {
                    if (!googleAdsElements.includes(udnAdsElements[i])) {
                        googleAdsElements.push(udnAdsElements[i]);
                    }
                }
                
                return googleAdsElements;
            }
            return getGoogleAdsElements();
        """)
        
        print(f"找到 {len(all_elements)} 個 Google Ads 元素，開始檢查尺寸...")
        
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
                
                # 嚴格檢查尺寸是否完全匹配
                if (size_info and 
                    size_info['visible'] and
                    size_info['width'] == target_width and 
                    size_info['height'] == target_height and
                    size_info['width'] > 0 and 
                    size_info['height'] > 0):
                    
                    # 專門檢查 Google Ads
                    is_google_ad = self.driver.execute_script("""
                        var element = arguments[0];
                        var tagName = element.tagName.toLowerCase();
                        var className = element.className || '';
                        var id = element.id || '';
                        var src = element.src || '';
                        
                        // 檢查是否為 Google Ads 容器
                        var isGoogleAdContainer = (
                            id.includes('google_ads') || 
                            id.includes('ads-') ||
                            className.includes('google') ||
                            className.includes('ads') ||
                            id.includes('ads')
                        );
                        
                        // 檢查是否包含 Google Ads iframe
                        var hasGoogleIframe = element.querySelector('iframe[src*="googleads"], iframe[src*="googlesyndication"], iframe[src*="doubleclick"]');
                        
                        // 檢查是否為 Google Ads iframe
                        var isGoogleIframe = tagName === 'iframe' && (
                            src.includes('googleads') || 
                            src.includes('googlesyndication') || 
                            src.includes('doubleclick')
                        );
                        
                        // 檢查是否有 Google Ads 腳本
                        var hasGoogleScript = element.querySelector('script[src*="google"]');
                        
                        // 檢查是否包含 googletag 腳本
                        var hasGoogletagScript = false;
                        var scripts = element.querySelectorAll('script');
                        for (var i = 0; i < scripts.length; i++) {
                            if (scripts[i].textContent && scripts[i].textContent.includes('googletag')) {
                                hasGoogletagScript = true;
                                break;
                            }
                        }
                        
                        return isGoogleAdContainer || hasGoogleIframe || isGoogleIframe || hasGoogleScript || hasGoogletagScript;
                    """, element)
                    
                    if is_google_ad:
                        # 再次驗證尺寸
                        final_check = self.driver.execute_script("""
                            var element = arguments[0];
                            var rect = element.getBoundingClientRect();
                            var computedStyle = window.getComputedStyle(element);
                            
                            return {
                                width: Math.round(rect.width),
                                height: Math.round(rect.height),
                                display: computedStyle.display,
                                visibility: computedStyle.visibility,
                                position: computedStyle.position,
                                zIndex: computedStyle.zIndex
                            };
                        """, element)
                        
                        # 最終尺寸驗證 - 在 JavaScript 中進行
                        final_verification = self.driver.execute_script("""
                            var element = arguments[0];
                            var targetWidth = arguments[1];
                            var targetHeight = arguments[2];
                            
                            var rect = element.getBoundingClientRect();
                            var computedStyle = window.getComputedStyle(element);
                            
                            var widthDiff = Math.abs(Math.round(rect.width) - targetWidth);
                            var heightDiff = Math.abs(Math.round(rect.height) - targetHeight);
                            var isExactMatch = widthDiff <= 1 && heightDiff <= 1;
                            
                            return {
                                width: Math.round(rect.width),
                                height: Math.round(rect.height),
                                display: computedStyle.display,
                                visibility: computedStyle.visibility,
                                isExactMatch: isExactMatch,
                                isValid: isExactMatch && computedStyle.display !== 'none' && computedStyle.visibility !== 'hidden'
                            };
                        """, element, target_width, target_height)
                        
                        if final_verification['isValid']:
                            matching_elements.append({
                                'element': element,
                                'width': final_verification['width'],
                                'height': final_verification['height'],
                                'position': f"top:{size_info['top']:.0f}, left:{size_info['left']:.0f}",
                                'display': final_verification['display'],
                                'visibility': final_verification['visibility']
                            })
                            print(f"✅ 確認找到 {target_width}x{target_height} Google Ads: {final_verification['width']}x{final_verification['height']} at {size_info['top']:.0f},{size_info['left']:.0f}")
                        else:
                            print(f"❌ 尺寸不匹配: 期望 {target_width}x{target_height}, 實際 {final_verification['width']}x{final_verification['height']}")
                    else:
                        print(f"❌ 不是 Google Ads: {size_info['width']}x{size_info['height']}")
                
                # 每檢查100個元素顯示進度
                if (i + 1) % 100 == 0:
                    print(f"已檢查 {i + 1}/{len(all_elements)} 個元素...")
                    
            except Exception as e:
                continue
        
        print(f"掃描完成，找到 {len(matching_elements)} 個符合尺寸的廣告元素")
        return matching_elements
    
    def get_button_style(self):
        """根據配置返回按鈕樣式"""
        button_style = getattr(self, 'button_style', BUTTON_STYLE)
        
        # 預先定義的按鈕樣式
        # 統一的資訊按鈕樣式 - 使用 Google 標準設計
        unified_info_button = {
            "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M7.5 1.5a6 6 0 100 12 6 6 0 100-12m0 1a5 5 0 110 10 5 5 0 110-10zM6.625 11h1.75V6.5h-1.75zM7.5 3.75a1 1 0 100 2 1 1 0 100-2z" fill="#00aecd"/></svg>',
            "style": 'position:absolute;top:0px;right:17px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);cursor:pointer;'
        }
        
        button_styles = {
            "dots": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="7.5" cy="2.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="6.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="10.5" r="1.5" fill="#00aecd"/></svg>',
                    "style": 'position:absolute;top:0px;right:0px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;'
                },
                "info_button": unified_info_button
            },
            "cross": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 4L11 11M11 4L4 11" stroke="#00aecd" stroke-width="1.5" stroke-linecap="round"/></svg>',
                    "style": 'position:absolute;top:0px;right:0px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;'
                },
                "info_button": unified_info_button
            },
            "adchoices": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 4L11 11M11 4L4 11" stroke="#00aecd" stroke-width="1.5" stroke-linecap="round"/></svg>',
                    "style": 'position:absolute;top:0px;right:0px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;'
                },
                "info_button": {
                    "html": '<img src="https://tpc.googlesyndication.com/pagead/images/adchoices/adchoices_blue_wb.png" width="15" height="15" style="display:block;width:15px;height:15px;">',
                    "style": 'position:absolute;top:0px;right:17px;width:15px;height:15px;z-index:100;display:block;cursor:pointer;'
                }
            },
            "adchoices_dots": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="7.5" cy="3.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="7.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="11.5" r="1.5" fill="#00aecd"/></svg>',
                    "style": 'position:absolute;top:0px;right:0px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;'
                },
                "info_button": {
                    "html": '<img src="https://tpc.googlesyndication.com/pagead/images/adchoices/adchoices_blue_wb.png" width="15" height="15" style="display:block;width:15px;height:15px;">',
                    "style": 'position:absolute;top:0px;right:17px;width:15px;height:15px;z-index:100;display:block;cursor:pointer;'
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
            
            # 檢查是否符合目標尺寸
            if (original_info['width'] != target_width or 
                original_info['height'] != target_height):
                return False
            
            # 獲取按鈕樣式
            button_style = self.get_button_style()
            close_button_html = button_style["close_button"]["html"]
            close_button_style = button_style["close_button"]["style"]
            info_button_html = button_style["info_button"]["html"]
            info_button_style = button_style["info_button"]["style"]
            
            # 檢查是否為 "none" 模式
            current_button_style = getattr(self, 'button_style', 'dots')
            is_none_mode = current_button_style == "none"
            
            # 只替換圖片，保留廣告按鈕
            success = self.driver.execute_script("""
                // 添加 Google 廣告標準樣式
                if (!document.getElementById('google_ad_styles')) {
                    var style = document.createElement('style');
                    style.id = 'google_ad_styles';
                    style.textContent = `
                        div {
                            margin: 0;
                            padding: 0;
                        }
                        .abgb {
                            position: absolute;
                            right: 16px;
                            top: 0px;
                        }
                        .abgb {
                            display: inline-block;
                            height: 15px;
                        }
                        .abgc {
                            cursor: pointer;
                        }
                        .abgc {
                            display: block;
                            height: 15px;
                            position: absolute;
                            right: 1px;
                            top: 1px;
                            text-rendering: geometricPrecision;
                            z-index: 2147483646;
                        }
                        .abgc .il-wrap {
                            background-color: #ffffff;
                            height: 15px;
                            white-space: nowrap;
                        }
                        .abgc .il-icon {
                            height: 15px;
                            width: 15px;
                        }
                        .abgc .il-icon svg {
                            fill: #00aecd;
                        }
                        .abgs svg, .abgb svg {
                            display: inline-block;
                            height: 15px;
                            width: 15px;
                            vertical-align: top;
                        }
                        #close_button { 
                            text-decoration: none; 
                            margin: 0; 
                            padding: 0; 
                            border: none;
                            cursor: pointer;
                            position: absolute; 
                            z-index: 100; 
                            top: 0px;
                            bottom: auto;
                            vertical-align: top;
                            margin-top: 1px;
                            right: 0px;
                            left: auto;
                            text-align: right;
                            margin-right: 1px;
                            display: block; 
                            width: 15px; 
                            height: 15px;
                        }
                        #close_button #close_button_svg { 
                            width: 15px; 
                            height: 15px; 
                            line-height: 0;
                        }
                        #abgb #info_button_svg { 
                            width: 15px; 
                            height: 15px; 
                            line-height: 0;
                        }
                    `;
                    document.head.appendChild(style);
                }
                
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
                
                // Yahoo 風格：不需要複雜的備份機制
                // 只在替換個別元素時保存其原始屬性即可
                
                // 確保 container 是 relative
                if (window.getComputedStyle(container).position === 'static') {
                  container.style.position = 'relative';
                }
                // 先移除舊的（避免重複）
                ['close_button', 'abgb'].forEach(function(id){
                  var old = container.querySelector('#'+id);
                  if(old) old.remove();
                });
                
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
                        // 保存原始樣式以便復原
                        if (!img.getAttribute('data-original-style')) {
                            img.setAttribute('data-original-style', img.style.cssText || '');
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
                    
                    // 確保img的父層是relative
                    var imgParent = img.parentElement || container;
                    if (window.getComputedStyle(imgParent).position === 'static') {
                        imgParent.style.position = 'relative';
                    }
                    
                    // 先移除舊的按鈕
                    ['close_button', 'abgb'].forEach(function(id){
                        var old = imgParent.querySelector('#'+id);
                        if(old) old.remove();
                    });
                    
                    // 只有在非 none 模式下才創建按鈕
                    if (!isNoneMode && closeButtonHtml && infoButtonHtml) {
                        // 叉叉 - 貼著替換圖片的右上角
                        var closeButton = document.createElement('div');
                        closeButton.id = 'close_button';
                        closeButton.innerHTML = closeButtonHtml;
                        closeButton.style.cssText = closeButtonStyle;
                        
                        // 驚嘆號 - 貼著替換圖片的右上角，與叉叉對齊
                        var abgb = document.createElement('div');
                        abgb.id = 'abgb';
                        abgb.className = 'abgb';
                        abgb.innerHTML = infoButtonHtml;
                        abgb.style.cssText = infoButtonStyle;
                        
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
                    
                    // 在iframe位置創建新的圖片元素
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
                    
                    // 先移除舊的按鈕
                    ['close_button', 'abgb'].forEach(function(id){
                        var old = container.querySelector('#'+id);
                        if(old) old.remove();
                    });
                    
                    // 只有在非 none 模式下才創建按鈕
                    if (!isNoneMode && closeButtonHtml && infoButtonHtml) {
                        // 檢查廣告尺寸，針對小尺寸廣告調整按鈕位置
                        var adWidth = iframeRect.width;
                        var adHeight = iframeRect.height;
                        var isSmallAd = adHeight <= 60; // 高度小於等於60px的廣告視為小廣告
                        
                        // 計算按鈕位置
                        var buttonTop = iframeRect.top - container.getBoundingClientRect().top;
                        var buttonRight = container.getBoundingClientRect().right - iframeRect.right;
                        
                        // 對於小廣告，調整按鈕位置避免超出範圍
                        if (isSmallAd) {
                            // 小廣告：按鈕放在廣告內部右上角
                            buttonTop = Math.max(0, buttonTop);
                            buttonRight = Math.max(0, buttonRight);
                            
                            // 確保按鈕不會超出廣告右邊界
                            if (buttonRight < 15) {
                                buttonRight = 0; // 如果空間不足，貼著右邊
                            }
                        }
                        
                        // 叉叉 - 貼著替換圖片的右上角
                        var closeButton = document.createElement('div');
                        closeButton.id = 'close_button';
                        closeButton.innerHTML = closeButtonHtml;
                        closeButton.style.cssText = 'position:absolute;top:' + buttonTop + 'px;right:' + buttonRight + 'px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);';
                        
                        // 驚嘆號 - 位置調整
                        var infoButtonRight = buttonRight + (isSmallAd ? 16 : 17); // 小廣告間距稍小
                        
                        // 對於小廣告，如果空間不足，將info按鈕放在close按鈕左邊
                        if (isSmallAd && infoButtonRight + 15 > adWidth) {
                            infoButtonRight = buttonRight - 16; // 放在close按鈕左邊
                            if (infoButtonRight < 0) {
                                infoButtonRight = buttonRight + 1; // 如果還是不夠，就緊貼著
                            }
                        }
                        
                        var abgb = document.createElement('div');
                        abgb.id = 'abgb';
                        abgb.className = 'abgb';
                        abgb.innerHTML = infoButtonHtml;
                        abgb.style.cssText = 'position:absolute;top:' + (buttonTop + (isSmallAd ? 0 : 1)) + 'px;right:' + infoButtonRight + 'px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);line-height:0;';
                        
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
                        // 保存原始背景圖片
                        if (!container.getAttribute('data-original-background')) {
                            container.setAttribute('data-original-background', style.backgroundImage);
                        }
                        // 保存原始背景樣式
                        if (!container.getAttribute('data-original-bg-style')) {
                            var bgStyle = {
                                size: style.backgroundSize,
                                repeat: style.backgroundRepeat,
                                position: style.backgroundPosition
                            };
                            container.setAttribute('data-original-bg-style', JSON.stringify(bgStyle));
                        }
                        container.style.backgroundImage = 'url(' + newImageSrc + ')';
                        container.style.backgroundSize = 'contain';
                        container.style.backgroundRepeat = 'no-repeat';
                        container.style.backgroundPosition = 'center';
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
                            // 添加兩個按鈕 - 貼著替換圖片的右上角，水平對齊
                            var closeButton = document.createElement('div');
                            closeButton.id = 'close_button';
                            closeButton.innerHTML = closeButtonHtml;
                            closeButton.style.cssText = closeButtonStyle;
                            
                            var abgb = document.createElement('div');
                            abgb.id = 'abgb';
                            abgb.className = 'abgb';
                            abgb.innerHTML = infoButtonHtml;
                            abgb.style.cssText = infoButtonStyle;
                            
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
        """處理單個網站，使用 ETtoday GIF 選擇策略 + 錯誤處理"""
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
                
                time.sleep(WAIT_TIME + 2)  # 增加等待時間
                
                # 獲取頁面標題
                page_title = self.driver.title
                print(f"📰 頁面標題: {page_title}")
                
                # 使用 ETtoday 模式：按尺寸分組處理，而非遍歷所有圖片
                total_replacements = 0
                screenshot_paths = []  # 儲存所有截圖路徑
                
                # 遍歷動態生成的目標廣告尺寸
                for size_info in self.target_ad_sizes:
                    target_width = size_info['width']
                    target_height = size_info['height']
                    size_key = f"{target_width}x{target_height}"
                    
                    print(f"\n🔍 處理尺寸: {size_key}")
                    
                    # 獲取該尺寸的圖片組
                    if size_key in self.images_by_size:
                        static_images = self.images_by_size[size_key]['static']
                        gif_images = self.images_by_size[size_key]['gif']
                        
                        print(f"   可用圖片: {len(static_images)}張靜態 + {len(gif_images)}張GIF")
                        
                        # 使用 ETtoday 優先級策略選擇圖片
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
                        
                        # 掃描網頁尋找符合尺寸的廣告 (保留 UDN 的 Google Ads 專門檢測)
                        matching_elements = self.scan_entire_page_for_ads(target_width, target_height)
                        
                        if not matching_elements:
                            print(f"   ❌ 未找到符合 {size_key} 尺寸的 Google Ads")
                            continue
                    
                    # 嘗試替換找到的廣告
                    replaced = False
                    processed_positions = set()  # 記錄已處理的位置
                    for ad_info in matching_elements:
                        # 檢查是否已經處理過這個位置
                        position_key = f"{ad_info['position']}_{size_key}"
                        if position_key in processed_positions:
                            print(f"   ⏭️ 跳過已處理的位置: {ad_info['position']}")
                            continue
                            
                        try:
                            if self.replace_ad_content(ad_info['element'], image_data, target_width, target_height):
                                print(f"   ✅ 成功替換 {selected_image['type']}: {selected_image['filename']} at {ad_info['position']}")
                                replaced = True
                                total_replacements += 1
                                processed_positions.add(position_key)  # 記錄已處理的位置
                                
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
                                    print(f"   📍 滾動到廣告位置: {scroll_position:.0f}px")
                                    
                                    # 等待滾動完成
                                    time.sleep(1)
                                    
                                    # 立即截圖 - ETtoday 即掃即換模式
                                    screenshot_path = self.take_screenshot(page_title)
                                    if screenshot_path:
                                        # 更新統計 - 使用 ETtoday 統計模式
                                        self._update_screenshot_count(screenshot_path, selected_image, ad_info)
                                        screenshot_paths.append(screenshot_path)
                                        
                                        # 檢查是否達到截圖數量限制
                                        if self.total_screenshots >= SCREENSHOT_COUNT:
                                            print(f"🎯 已達到截圖數量限制 ({SCREENSHOT_COUNT})")
                                            return screenshot_paths
                                    
                                    # 截圖後復原該位置的廣告 - 採用 Yahoo 簡化清理策略
                                    try:
                                        self.driver.execute_script("""
                                            // Yahoo 風格的簡化還原邏輯：直接清理所有注入元素
                                            
                                            // 移除所有注入的按鈕
                                            var buttons = document.querySelectorAll('#close_button, #abgb, #info_button, [id^="close_button"], [id^="abgb"]');
                                            for (var i = 0; i < buttons.length; i++) {
                                                buttons[i].remove();
                                            }
                                            
                                            // 移除所有替換的圖片（通過 data:image 識別）
                                            var replacedImages = document.querySelectorAll('img[src*="data:image"]');
                                            for (var i = 0; i < replacedImages.length; i++) {
                                                // 恢復原始 src
                                                var originalSrc = replacedImages[i].getAttribute('data-original-src');
                                                if (originalSrc) {
                                                    replacedImages[i].src = originalSrc;
                                                    replacedImages[i].removeAttribute('data-original-src');
                                                } else {
                                                    // 如果沒有原始 src，移除該圖片
                                                    replacedImages[i].remove();
                                                }
                                            }
                                            
                                            // 恢復所有被修改樣式的圖片
                                            var styledImages = document.querySelectorAll('img[data-original-style]');
                                            for (var i = 0; i < styledImages.length; i++) {
                                                var originalStyle = styledImages[i].getAttribute('data-original-style');
                                                if (originalStyle !== null) {
                                                    styledImages[i].style.cssText = originalStyle;
                                                    styledImages[i].removeAttribute('data-original-style');
                                                }
                                            }
                                            
                                            // 恢復所有隱藏的 iframe
                                            var hiddenIframes = document.querySelectorAll('iframe[style*="display: none"], iframe[style*="visibility: hidden"]');
                                            for (var i = 0; i < hiddenIframes.length; i++) {
                                                hiddenIframes[i].style.display = 'block';
                                                hiddenIframes[i].style.visibility = 'visible';
                                            }
                                            
                                            // 恢復背景圖片
                                            var bgElements = document.querySelectorAll('[data-original-background]');
                                            for (var i = 0; i < bgElements.length; i++) {
                                                var originalBg = bgElements[i].getAttribute('data-original-background');
                                                if (originalBg) {
                                                    bgElements[i].style.backgroundImage = originalBg;
                                                    bgElements[i].removeAttribute('data-original-background');
                                                    
                                                    // 恢復背景樣式
                                                    var originalBgStyle = bgElements[i].getAttribute('data-original-bg-style');
                                                    if (originalBgStyle) {
                                                        try {
                                                            var bgStyle = JSON.parse(originalBgStyle);
                                                            bgElements[i].style.backgroundSize = bgStyle.size;
                                                            bgElements[i].style.backgroundRepeat = bgStyle.repeat;
                                                            bgElements[i].style.backgroundPosition = bgStyle.position;
                                                        } catch(e) {}
                                                        bgElements[i].removeAttribute('data-original-bg-style');
                                                    }
                                                }
                                            }
                                            
                                            // 清理所有備份相關的 data 屬性
                                            var allElements = document.querySelectorAll('[data-original-backup], [data-backup-done]');
                                            for (var i = 0; i < allElements.length; i++) {
                                                allElements[i].removeAttribute('data-original-backup');
                                                allElements[i].removeAttribute('data-backup-done');
                                            }
                                            
                                            console.log('✅ Yahoo 風格清理完成：已移除所有注入元素');
                                        """)
                                        # Yahoo 風格驗證：檢查全頁面是否還有注入元素
                                        verification = self.driver.execute_script("""
                                            // 檢查整個頁面是否還有注入元素
                                            var replacedImages = document.querySelectorAll('img[src*="data:image"]');
                                            var addedButtons = document.querySelectorAll('#close_button, #abgb, [id^="close_button"], [id^="abgb"]');
                                            var dataAttributes = document.querySelectorAll('[data-original-src], [data-original-style], [data-original-background]');
                                            
                                            return {
                                                replacedImages: replacedImages.length,
                                                addedButtons: addedButtons.length,
                                                dataAttributes: dataAttributes.length
                                            };
                                        """)
                                        
                                        if verification['replacedImages'] == 0 and verification['addedButtons'] == 0:
                                            print(f"✅ {ad_info['width']}x{ad_info['height']} at {ad_info['position']}")
                                        else:
                                            print(f"⚠️ 清理不完整: 替換圖片:{verification['replacedImages']}, 按鈕:{verification['addedButtons']}, 屬性:{verification['dataAttributes']}")
                                    except Exception as e:
                                        print(f"清理失敗: {e}")
                                    
                                except Exception as scroll_e:
                                    print(f"   ⚠️ 滾動或截圖失敗: {scroll_e}")
                                
                                # 只替換第一個找到的廣告，然後處理下一個尺寸
                                break
                                
                        except Exception as e:
                            print(f"   ❌ 替換廣告失敗: {e}")
                            continue
                    
                    if not replaced:
                        print(f"   ❌ 無法替換任何 {size_key} 廣告")
                else:
                    print(f"   ❌ 沒有 {size_key} 尺寸的圖片")
            
                if total_replacements > 0:
                    print(f"\n✅ 成功替換 {total_replacements} 個廣告")
                    return screenshot_paths
                else:
                    print("\n❌ 本網頁沒有找到任何可替換的 Google Ads")
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
            filepath = f"{SCREENSHOT_FOLDER}/udn_{clean_title}_{timestamp}.png"
        else:
            filepath = f"{SCREENSHOT_FOLDER}/udn_replaced_{timestamp}.png"
        
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
    
    def close(self):
        self.driver.quit()

def main():
    # 偵測並選擇螢幕
    screen_id, selected_screen = ScreenManager.select_screen()
    
    if screen_id is None:
        print("未選擇螢幕，程式結束")
        return
    
    print(f"\n正在啟動 Chrome 瀏覽器到螢幕 {screen_id}...")
    bot = UdnAdReplacer(headless=False, screen_id=screen_id)
    
    try:
        # 使用聯合報旅遊網站的專用網址
        udn_url = "https://travel.udn.com"  # 簡化網址
        print(f"目標網站: {udn_url}")
        
        # 尋找旅遊連結
        news_urls = bot.get_random_news_urls(udn_url, NEWS_COUNT)
        
        if not news_urls:
            print("無法獲取旅遊連結")
            return
        
        print(f"獲取到 {len(news_urls)} 個旅遊連結")
        print(f"目標截圖數量: {SCREENSHOT_COUNT}")
        
        total_screenshots = 0
        
        # 處理每個網站
        consecutive_failures = 0
        max_consecutive_failures = 3
        
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
                    consecutive_failures = 0  # 重置連續失敗計數
                    
                    # 檢查是否達到目標截圖數量
                    if total_screenshots >= SCREENSHOT_COUNT:
                        print(f"✅ 已達到目標截圖數量: {SCREENSHOT_COUNT}")
                        break
                else:
                    print("❌ 網站處理完成，但沒有找到可替換的廣告")
                    consecutive_failures += 1
                
            except Exception as e:
                print(f"❌ 處理網站失敗: {e}")
                consecutive_failures += 1
                
                # 如果連續失敗太多次，增加等待時間
                if consecutive_failures >= max_consecutive_failures:
                    print(f"⚠️ 連續失敗 {consecutive_failures} 次，延長等待時間...")
                    time.sleep(30)  # 等待30秒
                    consecutive_failures = 0  # 重置計數
                
                continue
            
            # 在處理下一個網站前稍作休息
            if i < len(news_urls) and total_screenshots < SCREENSHOT_COUNT:
                wait_time = 5 if consecutive_failures > 0 else 3
                print(f"等待 {wait_time} 秒後處理下一個網站...")
                time.sleep(wait_time)
        
        # 顯示 ETtoday 風格的詳細統計報告
        print(f"\n📊 UDN 廣告替換統計報告 - GIF 升級版")
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
    test_bot = UdnAdReplacer(headless=False, screen_id=screen_id)
    
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