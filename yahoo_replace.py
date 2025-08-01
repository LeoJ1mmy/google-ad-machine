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
    BASE_URL = "https://tw.news.yahoo.com/fun/"
    NEWS_COUNT = 20
    TARGET_AD_SIZES = [{"width": 970, "height": 90}, {"width": 986, "height": 106}]
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

class YahooAdReplacer:
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
        
        # 根據作業系統設定螢幕位置
        system = platform.system()
        
        if system == "Darwin":  # macOS
            # macOS 多螢幕支援
            if self.screen_id > 1:
                # 計算螢幕偏移量 (假設每個螢幕寬度為1920px)
                screen_offset = (self.screen_id - 1) * 1920
                chrome_options.add_argument(f'--window-position={screen_offset},0')
            
        elif system == "Windows":
            # Windows 多螢幕支援
            if self.screen_id > 1:
                screen_offset = (self.screen_id - 1) * 1920
                chrome_options.add_argument(f'--window-position={screen_offset},0')
        
        if FULLSCREEN_MODE:
            chrome_options.add_argument('--start-maximized')
            if not headless:
                chrome_options.add_argument('--start-fullscreen')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # 確保瀏覽器在正確的螢幕上
        if not headless:
            self.move_to_screen()
    
    def move_to_screen(self):
        """將瀏覽器移動到指定螢幕"""
        try:
            system = platform.system()
            
            if system == "Darwin":  # macOS
                # 使用 AppleScript 移動 Chrome 到指定螢幕
                applescript = f'''
                tell application "Google Chrome"
                    activate
                    set bounds of front window to {{0, 0, 1920, 1080}}
                end tell
                '''
                
                if self.screen_id > 1:
                    # 計算螢幕偏移
                    screen_offset = (self.screen_id - 1) * 1920
                    applescript = f'''
                    tell application "Google Chrome"
                        activate
                        set bounds of front window to {{{screen_offset}, 0, {screen_offset + 1920}, 1080}}
                    end tell
                    '''
                
                subprocess.run(['osascript', '-e', applescript], 
                             capture_output=True, text=True)
                
            elif system == "Windows":
                # Windows 使用 Selenium 的視窗管理
                if self.screen_id > 1:
                    screen_offset = (self.screen_id - 1) * 1920
                    self.driver.set_window_position(screen_offset, 0)
                    
            # 確保全螢幕模式
            if FULLSCREEN_MODE:
                time.sleep(1)  # 等待視窗移動完成
                self.driver.fullscreen_window()
                
            print(f"✅ Chrome 已移動到螢幕 {self.screen_id}")
            
        except Exception as e:
            print(f"移動瀏覽器到螢幕 {self.screen_id} 失敗: {e}")
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
    
    def get_random_news_urls(self, base_url, count=5):
        try:
            print(f"正在訪問: {base_url}")
            self.driver.get(base_url)
            time.sleep(WAIT_TIME)
            
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
            print(f"獲取新聞連結失敗: {e}")
            return []
    
    def scan_entire_page_for_ads(self, target_width, target_height):
        """掃描整個網頁尋找符合尺寸的廣告元素"""
        print(f"開始掃描整個網頁尋找 {target_width}x{target_height} 的廣告...")
        
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
                
                # 允許 5 像素的容差範圍
                tolerance = 5
                width_match = abs(size_info['width'] - target_width) <= tolerance
                height_match = abs(size_info['height'] - target_height) <= tolerance
                
                if (size_info and 
                    size_info['visible'] and
                    width_match and 
                    height_match):
                    
                    # 完全簡化的廣告檢查 - 只要尺寸符合就認為是廣告
                    is_ad = True
                    
                    if is_ad:
                        matching_elements.append({
                            'element': element,
                            'width': size_info['width'],
                            'height': size_info['height'],
                            'position': f"top:{size_info['top']:.0f}, left:{size_info['left']:.0f}"
                        })
                        print(f"找到符合尺寸的廣告元素: {size_info['width']}x{size_info['height']} (目標: {target_width}x{target_height}) at {size_info['top']:.0f},{size_info['left']:.0f}")
                
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
        # 統一的資訊按鈕樣式 - 使用正確的資訊 i 圖標
        unified_info_button = {
            "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="7.5" cy="7.5" r="7" fill="none" stroke="#00aecd" stroke-width="1.5"/><path d="M7.5 4.5L7.5 10.5M7.5 12.5L7.5 12.5" stroke="#00aecd" stroke-width="1.5" fill="none"/></svg>',
            "style": 'position:absolute;top:0px;right:17px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);border-radius:2px;cursor:pointer;'
        }
        
        button_styles = {
            "dots": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="7.5" cy="3.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="7.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="11.5" r="1.5" fill="#00aecd"/></svg>',
                    "style": 'position:absolute;top:0px;right:0px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);border-radius:2px;cursor:pointer;'
                },
                "info_button": unified_info_button
            },
            "cross": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 4L11 11M11 4L4 11" stroke="#00aecd" stroke-width="1.5" stroke-linecap="round"/></svg>',
                    "style": 'position:absolute;top:0px;right:0px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);border-radius:2px;cursor:pointer;'
                },
                "info_button": unified_info_button
            },
            "adchoices": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 4L11 11M11 4L4 11" stroke="#00aecd" stroke-width="1.5" stroke-linecap="round"/></svg>',
                    "style": 'position:absolute;top:0px;right:0px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);border-radius:2px;cursor:pointer;'
                },
                "info_button": {
                    "html": '<img src="https://tpc.googlesyndication.com/pagead/images/adchoices/adchoices_blue_wb.png" width="15" height="15" style="display:block;width:15px;height:15px;">',
                    "style": 'position:absolute;top:0px;right:17px;width:15px;height:15px;z-index:100;display:block;cursor:pointer;'
                }
            },
            "adchoices_dots": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="7.5" cy="3.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="7.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="11.5" r="1.5" fill="#00aecd"/></svg>',
                    "style": 'position:absolute;top:0px;right:0px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);border-radius:2px;cursor:pointer;'
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
            
            # 只替換圖片，保留廣告按鈕，確保不影響頁面佈局
            success = self.driver.execute_script("""
                // 添加 Google 廣告標準樣式，確保不影響頁面佈局
                if (!document.getElementById('google_ad_styles')) {
                    var style = document.createElement('style');
                    style.id = 'google_ad_styles';
                    style.textContent = `
                        /* 只針對我們的廣告容器，不影響其他元素 */
                        .ad-replacement-container {
                            margin: 0 !important;
                            padding: 0 !important;
                            position: relative !important;
                            display: block !important;
                            overflow: visible !important;
                        }
                        .ad-replacement-container img {
                            max-width: 100% !important;
                            height: auto !important;
                            display: block !important;
                            margin: 0 !important;
                            padding: 0 !important;
                        }
                        .abgb {
                            position: absolute !important;
                            right: 16px !important;
                            top: 0px !important;
                            z-index: 1000 !important;
                            background-color: rgba(255,255,255,1) !important;
                        }
                        .abgb {
                            display: inline-block !important;
                            height: 15px !important;
                            background-color: rgba(255,255,255,1) !important;
                        }
                        .abgc {
                            cursor: pointer !important;
                        }
                        .abgc {
                            display: block !important;
                            height: 15px !important;
                            position: absolute !important;
                            right: 1px !important;
                            top: 1px !important;
                            text-rendering: geometricPrecision !important;
                            z-index: 2147483646 !important;
                        }
                        .abgc .il-wrap {
                            background-color: #ffffff !important;
                            height: 15px !important;
                            white-space: nowrap !important;
                        }
                        .abgc .il-icon {
                            height: 15px !important;
                            width: 15px !important;
                        }
                        .abgc .il-icon svg {
                            fill: #00aecd !important;
                        }
                        .abgs svg, .abgb svg {
                            display: inline-block !important;
                            height: 15px !important;
                            width: 15px !important;
                            vertical-align: top !important;
                        }
                        [id^="close_button_"] { 
                            position: absolute !important; 
                            top: 0px !important;
                            right: 0px !important;
                            width: 15px !important; 
                            height: 15px !important;
                            z-index: 1001 !important;
                            cursor: pointer !important;
                            display: block !important;
                            margin: 0 !important; 
                            padding: 0 !important; 
                            border: none !important;
                            background-color: rgba(255,255,255,1) !important;
                        }
                        [id^="close_button_"] [id="close_button_svg"] { 
                            width: 15px !important; 
                            height: 15px !important; 
                            display: block !important;
                            margin: 0 !important;
                            padding: 0 !important;
                        }
                        [id^="abgb_"] [id="info_button_svg"] { 
                            width: 15px !important; 
                            height: 15px !important; 
                            line-height: 0 !important;
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
                
                // 確保 container 是 relative
                if (window.getComputedStyle(container).position === 'static') {
                  container.style.position = 'relative';
                }
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
                    
                    // 移除所有舊的按鈕（更徹底的清理）
                    var allCloseButtons = imgParent.querySelectorAll('#close_button');
                    var allInfoButtons = imgParent.querySelectorAll('#abgb');
                    allCloseButtons.forEach(function(btn) { btn.remove(); });
                    allInfoButtons.forEach(function(btn) { btn.remove(); });
                    
                                            // 叉叉 - 使用動態樣式
                        var closeButton = document.createElement('div');
                        closeButton.id = 'close_button_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                        closeButton.innerHTML = closeButtonHtml;
                        closeButton.style.cssText = closeButtonStyle;
                        
                        // 驚嘆號 - 使用動態樣式
                        var abgb = document.createElement('div');
                        abgb.id = 'abgb_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                        abgb.className = 'abgb';
                        abgb.innerHTML = infoButtonHtml;
                        abgb.style.cssText = infoButtonStyle;
                    
                    // 將按鈕添加到img的父層（驚嘆號在左，叉叉在右）
                    imgParent.appendChild(abgb);
                    imgParent.appendChild(closeButton);
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
                    
                    // 叉叉 - 使用動態樣式
                    var closeButton = document.createElement('div');
                    closeButton.id = 'close_button_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                    closeButton.innerHTML = closeButtonHtml;
                    closeButton.style.cssText = 'position:absolute;top:' + (iframeRect.top - container.getBoundingClientRect().top + 1) + 'px;right:' + (container.getBoundingClientRect().right - iframeRect.right + 1) + 'px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);line-height:0;';
                    
                    // 驚嘆號 - 使用動態樣式
                    var abgb = document.createElement('div');
                    abgb.id = 'abgb_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                    abgb.className = 'abgb';
                    abgb.innerHTML = infoButtonHtml;
                    abgb.style.cssText = 'position:absolute;top:' + (iframeRect.top - container.getBoundingClientRect().top + 1) + 'px;right:' + (container.getBoundingClientRect().right - iframeRect.right + 18) + 'px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);line-height:0;';
                    
                    // 將按鈕添加到container內，與圖片同層
                    container.appendChild(abgb);
                    container.appendChild(closeButton);
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
                        
                        // 添加兩個按鈕 - 使用動態樣式
                        var closeButton = document.createElement('div');
                        closeButton.id = 'close_button_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                        closeButton.innerHTML = closeButtonHtml;
                        closeButton.style.cssText = closeButtonStyle;
                        
                        var abgb = document.createElement('div');
                        abgb.id = 'abgb_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                        abgb.className = 'abgb';
                        abgb.innerHTML = infoButtonHtml;
                        abgb.style.cssText = infoButtonStyle;
                        
                        // 將按鈕添加到container內，與背景圖片同層
                        container.appendChild(abgb);
                        container.appendChild(closeButton);
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
        """處理單個網站，遍歷所有替換圖片"""
        try:
            print(f"\n開始處理網站: {url}")
            
            # 載入網頁
            self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
            self.driver.get(url)
            time.sleep(WAIT_TIME)
            
            # 獲取頁面標題
            page_title = self.driver.title
            print(f"📰 頁面標題: {page_title}")
            
            # 檢查是否成功載入目標頁面
            current_url = self.driver.current_url
            if url not in current_url and 'yahoo.com' not in current_url:
                print(f"警告：頁面可能已重定向，目標: {url}，實際: {current_url}")
                # 嘗試重新載入
                self.driver.get(url)
                time.sleep(WAIT_TIME)
                current_url = self.driver.current_url
                print(f"重新載入後 URL: {current_url}")
            
            # 由於我們專門針對熱門景點版面，所有新聞都應該是旅遊相關的
            page_title = self.driver.title
            print(f"✅ 處理熱門景點版面新聞: {page_title}")
            
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
                processed_positions = set()  # 記錄已處理的位置
                for ad_info in matching_elements:
                    # 檢查是否已經處理過這個位置（使用更精確的位置識別）
                    position_key = f"{ad_info['position']}_{image_info['width']}x{image_info['height']}"
                    if position_key in processed_positions:
                        print(f"跳過已處理的位置: {ad_info['position']}")
                        continue
                    
                    # 簡化的元素有效性檢查
                    try:
                        is_valid = self.driver.execute_script("""
                            var element = arguments[0];
                            if (!element || !element.getBoundingClientRect) return false;
                            var rect = element.getBoundingClientRect();
                            return rect.width > 0 && rect.height > 0;
                        """, ad_info['element'])
                        
                        if not is_valid:
                            print(f"跳過無效的廣告位置: {ad_info['position']}")
                            continue
                    except Exception as e:
                        print(f"檢查元素有效性失敗: {e}")
                        continue
                        
                    try:
                        if self.replace_ad_content(ad_info['element'], image_data, image_info['width'], image_info['height']):
                            print(f"成功替換廣告: {ad_info['width']}x{ad_info['height']} at {ad_info['position']}")
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
                                
                                # 計算滾動位置，讓廣告在螢幕中央偏上
                                viewport_height = self.driver.execute_script("return window.innerHeight;")
                                scroll_position = element_rect['top'] - (viewport_height * 0.3)  # 讓廣告在螢幕上方30%位置
                                
                                # 確保滾動位置不為負數
                                scroll_position = max(0, scroll_position)
                                
                                # 滾動到廣告位置
                                self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                                print(f"滾動到廣告位置: {scroll_position:.0f}px")
                                
                                # 等待滾動完成和頁面穩定
                                time.sleep(2)
                                
                            except Exception as e:
                                print(f"滾動到廣告位置失敗: {e}")
                            
                            # 每次替換後立即截圖
                            print("準備截圖...")
                            time.sleep(3)  # 等待頁面穩定和廣告完全載入
                            
                            # 簡化的廣告有效性檢查
                            try:
                                is_still_valid = self.driver.execute_script("""
                                    var element = arguments[0];
                                    if (!element || !element.getBoundingClientRect) return false;
                                    var rect = element.getBoundingClientRect();
                                    return rect.width > 0 && rect.height > 0;
                                """, ad_info['element'])
                                
                                if not is_still_valid:
                                    print("廣告位置已無效，跳過截圖")
                                    continue
                            except Exception as e:
                                print(f"檢查廣告有效性失敗: {e}")
                            
                            screenshot_path = self.take_screenshot(page_title)
                            if screenshot_path:
                                screenshot_paths.append(screenshot_path)
                                print(f"✅ 截圖保存: {screenshot_path}")
                            else:
                                print("❌ 截圖失敗")
                            
                            # 截圖後復原該位置的廣告
                            try:
                                # 簡化還原邏輯：直接移除所有注入的元素
                                self.driver.execute_script("""
                                    // 移除所有注入的按鈕
                                    var buttons = document.querySelectorAll('#close_button, #abgb, #info_button, [id^="close_button_"], [id^="abgb_"]');
                                    for (var i = 0; i < buttons.length; i++) {
                                        buttons[i].remove();
                                    }
                                    
                                    // 移除所有替換的圖片
                                    var replacedImages = document.querySelectorAll('img[src*="data:image/png;base64"]');
                                    for (var i = 0; i < replacedImages.length; i++) {
                                        replacedImages[i].remove();
                                    }
                                    
                                    // 移除替換容器
                                    var container = document.querySelector('#ad_replacement_container');
                                    if (container) {
                                        container.remove();
                                    }
                                    
                                    // 恢復所有隱藏的 iframe
                                    var hiddenIframes = document.querySelectorAll('iframe[style*="display: none"], iframe[style*="visibility: hidden"]');
                                    for (var i = 0; i < hiddenIframes.length; i++) {
                                        hiddenIframes[i].style.display = 'block';
                                        hiddenIframes[i].style.visibility = 'visible';
                                    }
                                    
                                    // 清理所有 data 屬性
                                    var allElements = document.querySelectorAll('[data-original-content], [data-original-src], [data-original-display], [data-injected]');
                                    for (var i = 0; i < allElements.length; i++) {
                                        allElements[i].removeAttribute('data-original-content');
                                        allElements[i].removeAttribute('data-original-src');
                                        allElements[i].removeAttribute('data-original-display');
                                        allElements[i].removeAttribute('data-injected');
                                    }
                                    
                                    console.log('✅ 已清理所有注入元素');
                                """)
                                print("✅ 廣告位置已復原")
                                
                                # 標記該位置為已處理，避免無限循環
                                position_key = f"top:{ad_info['top']}, left:{ad_info['left']}"
                                processed_positions.add(position_key)
                                print(f"📍 標記位置為已處理: {position_key}")
                            except Exception as e:
                                print(f"復原廣告失敗: {e}")
                            
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
                # Windows 多螢幕截圖
                try:
                    import pyautogui
                    
                    # 獲取所有螢幕的資訊
                    try:
                        # 使用 PowerShell 獲取螢幕位置資訊
                        powershell_cmd = '''
                        Add-Type -AssemblyName System.Windows.Forms
                        $screens = [System.Windows.Forms.Screen]::AllScreens
                        for ($i = 0; $i -lt $screens.Length; $i++) {
                            $screen = $screens[$i]
                            Write-Output "$($i+1):$($screen.Bounds.X):$($screen.Bounds.Y):$($screen.Bounds.Width):$($screen.Bounds.Height):$($screen.Primary)"
                        }
                        '''
                        result = subprocess.run(['powershell', '-Command', powershell_cmd], 
                                              capture_output=True, text=True)
                        
                        if result.returncode == 0:
                            lines = result.stdout.strip().split('\n')
                            screen_info = {}
                            for line in lines:
                                if ':' in line:
                                    parts = line.strip().split(':')
                                    if len(parts) >= 6:
                                        screen_num = int(parts[0])
                                        x = int(parts[1])
                                        y = int(parts[2])
                                        width = int(parts[3])
                                        height = int(parts[4])
                                        is_primary = parts[5].lower() == 'true'
                                        screen_info[screen_num] = {
                                            'x': x, 'y': y, 'width': width, 'height': height, 'primary': is_primary
                                        }
                            
                            # 使用正確的螢幕座標截圖
                            if self.screen_id in screen_info:
                                screen = screen_info[self.screen_id]
                                screenshot = pyautogui.screenshot(region=(screen['x'], screen['y'], screen['width'], screen['height']))
                                print(f"使用螢幕 {self.screen_id} 座標: x={screen['x']}, y={screen['y']}, w={screen['width']}, h={screen['height']}")
                            else:
                                # 回退到預設方法
                                if self.screen_id > 1:
                                    screen_offset = (self.screen_id - 1) * 1920
                                    screenshot = pyautogui.screenshot(region=(screen_offset, 0, 1920, 1080))
                                else:
                                    screenshot = pyautogui.screenshot()
                        else:
                            # PowerShell 失敗，使用預設方法
                            if self.screen_id > 1:
                                screen_offset = (self.screen_id - 1) * 1920
                                screenshot = pyautogui.screenshot(region=(screen_offset, 0, 1920, 1080))
                            else:
                                screenshot = pyautogui.screenshot()
                    except Exception as e:
                        print(f"獲取螢幕資訊失敗: {e}，使用預設方法")
                        if self.screen_id > 1:
                            screen_offset = (self.screen_id - 1) * 1920
                            screenshot = pyautogui.screenshot(region=(screen_offset, 0, 1920, 1080))
                        else:
                            screenshot = pyautogui.screenshot()
                    
                    screenshot.save(filepath)
                    print(f"截圖保存 (螢幕 {self.screen_id}): {filepath}")
                    return filepath
                    
                except ImportError:
                    print("pyautogui 未安裝，使用 Selenium 截圖")
                    self.driver.save_screenshot(filepath)
                    print(f"截圖保存: {filepath}")
                    return filepath
                except Exception as e:
                    print(f"pyautogui 截圖失敗: {e}，使用 Selenium 截圖")
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
    # 偵測並選擇螢幕
    screen_id, selected_screen = ScreenManager.select_screen()
    
    if screen_id is None:
        print("未選擇螢幕，程式結束")
        return
    
    print(f"\n正在啟動 Chrome 瀏覽器到螢幕 {screen_id}...")
    bot = YahooAdReplacer(headless=False, screen_id=screen_id)
    
    try:
        # 使用 Yahoo 新聞熱門景點版面的 URL
        yahoo_url = "https://tw.news.yahoo.com/tourist-spots"
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
        
        print(f"\n{'='*50}")
        print(f"所有網站處理完成！總共產生 {total_screenshots} 張截圖")
        print(f"{'='*50}")
        
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
