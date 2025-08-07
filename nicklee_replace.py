#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Nicklee.tw Ad Replacer
======================

A specialized ad replacement tool for nicklee.tw website.
Based on the NickleeAdReplacer framework with customizations for nicklee.tw's
specific structure and ad placement patterns.

Features:
- Automatic article discovery from nicklee.tw
- Multi-screen support with ScreenManager
- Configurable button styles (dots, cross, adchoices, adchoices_dots, none)
- Ad replacement with custom images
- Screenshot capture with automatic restoration
- Integration with config.py parameters

Author: Ad Replacement System
Version: 1.0
Target Website: https://nicklee.tw
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
    SCREENSHOT_COUNT = 30
    MAX_ATTEMPTS = 50
    PAGE_LOAD_TIMEOUT = 15
    WAIT_TIME = 3
    REPLACE_IMAGE_FOLDER = "replace_image"
    DEFAULT_IMAGE = "mini.jpg"
    MINI_IMAGE = "mini.jpg"
    NICKLEE_BASE_URL = "https://nicklee.tw"
    NEWS_COUNT = 20
    NICKLEE_TARGET_AD_SIZES = [
        {"width": 970, "height": 90},
        {"width": 728, "height": 90},
        {"width": 300, "height": 250},
        {"width": 320, "height": 50},
        {"width": 336, "height": 280}
    ]
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
    }
    MAX_CONSECUTIVE_FAILURES = 3
    CLOSE_BUTTON_SIZE = {"width": 15, "height": 15}
    INFO_BUTTON_SIZE = {"width": 15, "height": 15}
    INFO_BUTTON_COLOR = "#00aecd"
    INFO_BUTTON_OFFSET = 16
    HEADLESS_MODE = False
    FULLSCREEN_MODE = True
    SCREENSHOT_FOLDER = "screenshots"
    BUTTON_STYLE = "none"

# 設定 nicklee.tw 特定參數
try:
    # 如果 config.py 中沒有定義 nicklee.tw 特定設定，使用預設值
    if 'NICKLEE_BASE_URL' not in globals():
        NICKLEE_BASE_URL = "https://nicklee.tw"
    if 'NICKLEE_TARGET_AD_SIZES' not in globals():
        NICKLEE_TARGET_AD_SIZES = [
            {"width": 970, "height": 90},
            {"width": 728, "height": 90},
            {"width": 300, "height": 250},
            {"width": 320, "height": 50},
            {"width": 336, "height": 280}
        ]
except:
    NICKLEE_BASE_URL = "https://nicklee.tw"
    NICKLEE_TARGET_AD_SIZES = [
        {"width": 970, "height": 90},
        {"width": 728, "height": 90},
        {"width": 300, "height": 250},
        {"width": 320, "height": 50},
        {"width": 336, "height": 280}
    ]

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

class NickleeAdReplacer:
    """Nicklee.tw 廣告替換器"""
    
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
 
    def get_nicklee_article_urls(self, base_url, count=None):
        """
        獲取 nicklee.tw 的文章連結
        
        Args:
            base_url (str): nicklee.tw 的基礎 URL
            count (int, optional): 要獲取的文章數量，預設使用 NEWS_COUNT
            
        Returns:
            list: 篩選後的文章 URL 列表
        """
        if count is None:
            count = NEWS_COUNT
            
        print(f"開始從 {base_url} 獲取 nicklee.tw 文章連結...")
        
        try:
            # 載入首頁
            print("正在載入 nicklee.tw 首頁...")
            try:
                self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
                self.driver.get(base_url)
                time.sleep(WAIT_TIME)
                print("✅ 首頁載入成功")
            except Exception as e:
                self._handle_url_discovery_error(e, "載入首頁")
                print("嘗試使用備用策略...")
                fallback_urls = self._retry_url_discovery_with_fallback(base_url)
                if fallback_urls:
                    selected_count = min(count, len(fallback_urls))
                    selected_urls = random.sample(fallback_urls, selected_count)
                    print(f"✅ 備用策略成功獲取 {len(selected_urls)} 個連結")
                    return selected_urls
                else:
                    print("❌ 備用策略也失敗，無法獲取任何連結")
                    return []
            
            # nicklee.tw 特定的 CSS 選擇器 (按優先級排序)
            primary_selectors = [
                "a[href*='/article/']",      # 文章頁面
                "a[href*='/post/']",         # 部落格文章
                "a[href*='/blog/']",         # 部落格頁面
                ".post-title a",             # 文章標題連結
                ".entry-title a",            # 條目標題連結
                "article a[href*='nicklee.tw']",  # 文章區塊內的 nicklee.tw 連結
                ".content a[href*='nicklee.tw']", # 內容區塊內的 nicklee.tw 連結
            ]
            
            # 備用選擇器
            fallback_selectors = [
                "a[href*='nicklee.tw'][href*='/20']",  # 包含年份的連結 (通常是文章)
                "a[href*='nicklee.tw']:not([href*='#']):not([href*='javascript'])",  # 所有 nicklee.tw 連結但排除錨點和 JS
                "article a",                 # 文章區塊內的所有連結
                ".post a",                   # 文章區塊內的連結
                ".entry a",                  # 條目區塊內的連結
            ]
            
            news_urls = set()  # 使用 set 避免重複
            
            # 嘗試主要選擇器
            print("使用主要選擇器搜尋文章連結...")
            selector_success_count = 0
            
            for i, selector in enumerate(primary_selectors, 1):
                try:
                    print(f"  嘗試選擇器 {i}/{len(primary_selectors)}: {selector}")
                    
                    # 設定元素查找超時
                    links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    found_count = 0
                    processed_count = 0
                    
                    for link in links:
                        try:
                            href = link.get_attribute('href')
                            processed_count += 1
                            
                            if self._is_valid_nicklee_article_url(href):
                                news_urls.add(href)
                                found_count += 1
                                
                        except Exception as link_error:
                            # 個別連結處理失敗不影響整體流程
                            continue
                    
                    print(f"    處理了 {processed_count} 個連結，找到 {found_count} 個有效連結")
                    
                    if found_count > 0:
                        selector_success_count += 1
                    
                    # 如果已經找到足夠的連結，可以提前結束
                    if len(news_urls) >= count * 2:  # 收集比需要的多一些，以便後續隨機選擇
                        print(f"    已收集足夠連結 ({len(news_urls)} 個)，停止主要選擇器搜尋")
                        break
                        
                except Exception as e:
                    self._handle_url_discovery_error(e, f"主要選擇器 {selector}")
                    continue
            
            print(f"主要選擇器階段完成: {selector_success_count}/{len(primary_selectors)} 個選擇器成功")
            
            # 如果主要選擇器找到的連結不夠，使用備用選擇器
            if len(news_urls) < count:
                print(f"主要選擇器只找到 {len(news_urls)} 個連結，使用備用選擇器...")
                fallback_success_count = 0
                
                for i, selector in enumerate(fallback_selectors, 1):
                    try:
                        print(f"  嘗試備用選擇器 {i}/{len(fallback_selectors)}: {selector}")
                        links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        found_count = 0
                        processed_count = 0
                        
                        # 限制處理的連結數量以提高效率
                        max_links_to_process = 50
                        links_to_process = links[:max_links_to_process]
                        
                        for link in links_to_process:
                            try:
                                href = link.get_attribute('href')
                                processed_count += 1
                                
                                if self._is_valid_nicklee_article_url(href):
                                    news_urls.add(href)
                                    found_count += 1
                                    
                            except Exception as link_error:
                                # 個別連結處理失敗不影響整體流程
                                continue
                        
                        print(f"    處理了 {processed_count} 個連結，找到 {found_count} 個有效連結")
                        
                        if found_count > 0:
                            fallback_success_count += 1
                        
                        if len(news_urls) >= count * 2:
                            print(f"    已收集足夠連結 ({len(news_urls)} 個)，停止備用選擇器搜尋")
                            break
                            
                    except Exception as e:
                        self._handle_url_discovery_error(e, f"備用選擇器 {selector}")
                        continue
                
                print(f"備用選擇器階段完成: {fallback_success_count}/{len(fallback_selectors)} 個選擇器成功")
            
            # 轉換為列表並隨機選擇
            news_urls_list = list(news_urls)
            
            if news_urls_list:
                # 隨機選擇指定數量的連結
                selected_count = min(count, len(news_urls_list))
                try:
                    selected_urls = random.sample(news_urls_list, selected_count)
                except ValueError as e:
                    # 如果 sample 失敗（比如列表為空），直接返回所有找到的 URL
                    selected_urls = news_urls_list[:selected_count]
                
                print(f"✅ 成功從 nicklee.tw 找到 {len(news_urls_list)} 個文章連結")
                print(f"✅ 隨機選擇了 {len(selected_urls)} 個連結進行處理")
                
                # 顯示選中的 URL (僅顯示前 5 個以避免輸出過長)
                for i, url in enumerate(selected_urls[:5], 1):
                    print(f"  {i}. {url}")
                if len(selected_urls) > 5:
                    print(f"  ... 還有 {len(selected_urls) - 5} 個連結")
                
                return selected_urls
            else:
                # 沒有找到任何文章連結的情況
                print("❌ 在 nicklee.tw 上沒有找到任何有效的文章連結")
                print("可能的原因:")
                print("  1. 網站結構已變更，CSS 選擇器需要更新")
                print("  2. 網路連線問題導致頁面載入不完整")
                print("  3. 網站暫時無法訪問")
                print("  4. 網站使用了動態載入，需要更長的等待時間")
                
                # 嘗試最後的備用策略
                print("嘗試最後的備用策略...")
                final_fallback_urls = self._retry_url_discovery_with_fallback(base_url, max_retries=1)
                if final_fallback_urls:
                    selected_count = min(count, len(final_fallback_urls))
                    selected_urls = final_fallback_urls[:selected_count]
                    print(f"✅ 最後備用策略成功獲取 {len(selected_urls)} 個連結")
                    return selected_urls
                
                return []
                
        except Exception as e:
            self._handle_url_discovery_error(e, "主要 URL 發現流程")
            
            # 嘗試緊急備用策略
            print("執行緊急備用策略...")
            try:
                emergency_urls = self._retry_url_discovery_with_fallback(base_url, max_retries=2)
                if emergency_urls:
                    selected_count = min(count, len(emergency_urls))
                    selected_urls = emergency_urls[:selected_count]
                    print(f"✅ 緊急備用策略成功獲取 {len(selected_urls)} 個連結")
                    return selected_urls
            except Exception as emergency_error:
                print(f"❌ 緊急備用策略也失敗: {emergency_error}")
            
            print("❌ 所有 URL 發現策略都失敗，無法獲取任何文章連結")
            return []
    
    def _is_valid_nicklee_article_url(self, href):
        """
        檢查 URL 是否為有效的 nicklee.tw 文章連結
        
        Args:
            href (str): 要檢查的 URL
            
        Returns:
            bool: 如果是有效的文章連結則返回 True
        """
        if not href:
            return False
        
        # 必須包含 nicklee.tw 域名
        if 'nicklee.tw' not in href:
            return False
        
        # 排除的 URL 模式
        excluded_patterns = [
            '#',                    # 錨點連結
            'javascript:',          # JavaScript 連結
            'mailto:',              # 郵件連結
            'tel:',                 # 電話連結
            '/about',               # 關於頁面
            '/contact',             # 聯絡頁面
            '/category',            # 分類頁面
            '/tag',                 # 標籤頁面
            '/search',              # 搜尋頁面
            '/archive',             # 存檔頁面
            '/feed',                # RSS feed
            '.xml',                 # XML 檔案
            '.rss',                 # RSS 檔案
            '/wp-admin',            # WordPress 管理頁面
            '/wp-content',          # WordPress 內容檔案
            '/wp-includes',         # WordPress 核心檔案
            'login',                # 登入頁面
            'register',             # 註冊頁面
        ]
        
        # 檢查是否包含排除的模式
        href_lower = href.lower()
        for pattern in excluded_patterns:
            if pattern in href_lower:
                return False
        
        # 優先接受明確的文章 URL 模式
        preferred_patterns = [
            '/article/',
            '/post/',
            '/blog/',
            '/20',  # 年份，通常文章 URL 會包含發布年份
        ]
        
        for pattern in preferred_patterns:
            if pattern in href_lower:
                return True
        
        # 如果沒有明確的文章模式，但是 nicklee.tw 的連結且不在排除列表中，也接受
        return True
    
    def _handle_url_discovery_error(self, error, context=""):
        """
        處理 URL 發現過程中的錯誤
        
        Args:
            error (Exception): 發生的錯誤
            context (str): 錯誤發生的上下文
        """
        error_msg = f"URL 發現錯誤"
        if context:
            error_msg += f" ({context})"
        error_msg += f": {str(error)}"
        
        print(f"⚠️ {error_msg}")
        
        # 根據錯誤類型提供不同的處理建議
        if "timeout" in str(error).lower():
            print("   建議: 網頁載入超時，可能是網路連線問題")
        elif "no such element" in str(error).lower():
            print("   建議: 找不到指定元素，可能是網頁結構已變更")
        elif "webdriver" in str(error).lower():
            print("   建議: WebDriver 相關錯誤，可能需要重新啟動瀏覽器")
        elif "connection" in str(error).lower():
            print("   建議: 連線錯誤，請檢查網路連線或網站是否可用")
    
    def _retry_url_discovery_with_fallback(self, base_url, max_retries=3):
        """
        使用備用策略重試 URL 發現
        
        Args:
            base_url (str): 基礎 URL
            max_retries (int): 最大重試次數
            
        Returns:
            list: 發現的 URL 列表
        """
        print(f"開始備用 URL 發現策略 (最多重試 {max_retries} 次)...")
        
        # 備用 URL 列表 - 如果主頁失敗，嘗試這些頁面
        fallback_urls = [
            f"{base_url}",
            f"{base_url}/",
            f"{base_url}/blog",
            f"{base_url}/articles",
            f"{base_url}/posts",
        ]
        
        for retry in range(max_retries):
            for i, url in enumerate(fallback_urls):
                try:
                    print(f"  重試 {retry + 1}/{max_retries}, 嘗試 URL {i + 1}/{len(fallback_urls)}: {url}")
                    
                    # 設定較短的超時時間
                    self.driver.set_page_load_timeout(10)
                    self.driver.get(url)
                    time.sleep(2)  # 較短的等待時間
                    
                    # 使用最簡單的選擇器
                    simple_selectors = [
                        "a[href*='nicklee.tw']",
                        "a[href*='/20']",  # 包含年份的連結
                        "a"  # 所有連結作為最後手段
                    ]
                    
                    found_urls = set()
                    for selector in simple_selectors:
                        try:
                            links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for link in links[:20]:  # 限制檢查數量以提高速度
                                href = link.get_attribute('href')
                                if self._is_valid_nicklee_article_url(href):
                                    found_urls.add(href)
                                    
                            if len(found_urls) >= 5:  # 找到足夠的連結就停止
                                break
                        except:
                            continue
                    
                    if found_urls:
                        print(f"  ✅ 備用策略成功找到 {len(found_urls)} 個連結")
                        return list(found_urls)
                        
                except Exception as e:
                    print(f"  ❌ 備用 URL {url} 失敗: {e}")
                    continue
        
        print("  ❌ 所有備用策略都失敗了")
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
                
                if (size_info and 
                    size_info['visible'] and
                    size_info['width'] == target_width and 
                    size_info['height'] == target_height):
                    
                    # 進一步檢查是否可能是廣告
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
        """根據配置返回按鈕樣式"""
        button_style = getattr(self, 'button_style', BUTTON_STYLE)
        
        # 預先定義的按鈕樣式
        # 統一的資訊按鈕樣式 - 使用 Google 標準設計
        unified_info_button = {
            "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M7.5 1.5a6 6 0 100 12 6 6 0 100-12m0 1a5 5 0 110 10 5 5 0 110-10zM6.625 11h1.75V6.5h-1.75zM7.5 3.75a1 1 0 100 2 1 1 0 100-2z" fill="#00aecd"/></svg>',
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
            
            # 檢查是否符合目標尺寸
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
            
            # 只替換圖片，根據模式決定是否添加按鈕
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
                        // 確保img的父層是relative
                        if (window.getComputedStyle(imgParent).position === 'static') {
                            imgParent.style.position = 'relative';
                        }
                        
                        // 只有在非 none 模式下才創建按鈕
                        if (closeButtonHtml || infoButtonHtml) {
                            // 叉叉 - 貼著替換圖片的右上角
                            if (closeButtonHtml) {
                                var closeButton = document.createElement('div');
                                closeButton.id = 'close_button';
                                closeButton.innerHTML = closeButtonHtml;
                                closeButton.style.cssText = closeButtonStyle;
                                imgParent.appendChild(closeButton);
                            }
                            
                            // 驚嘆號 - 貼著替換圖片的右上角，與叉叉對齊
                            if (infoButtonHtml) {
                                var abgb = document.createElement('div');
                                abgb.id = 'abgb';
                                abgb.className = 'abgb';
                                abgb.innerHTML = infoButtonHtml;
                                abgb.style.cssText = infoButtonStyle;
                                imgParent.appendChild(abgb);
                            }
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
                        // 叉叉 - 貼著替換圖片的右上角
                        var closeButton = document.createElement('div');
                        closeButton.id = 'close_button';
                        closeButton.innerHTML = closeButtonHtml;
                        closeButton.style.cssText = 'position:absolute;top:' + (iframeRect.top - container.getBoundingClientRect().top) + 'px;right:' + (container.getBoundingClientRect().right - iframeRect.right) + 'px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);';
                        
                        // 驚嘆號 - 貼著替換圖片的右上角，與叉叉水平對齊
                        var abgb = document.createElement('div');
                        abgb.id = 'abgb';
                        abgb.className = 'abgb';
                        abgb.innerHTML = infoButtonHtml;
                        abgb.style.cssText = 'position:absolute;top:' + (iframeRect.top - container.getBoundingClientRect().top + 1) + 'px;right:' + (container.getBoundingClientRect().right - iframeRect.right + 17) + 'px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);line-height:0;';
                        
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
                            // 確保容器是relative
                            if (window.getComputedStyle(container).position === 'static') {
                                container.style.position = 'relative';
                            }
                            
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
        """處理單個網站，遍歷所有替換圖片"""
        try:
            print(f"\n開始處理 nicklee.tw 網站: {url}")
            
            # 載入網頁
            self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
            self.driver.get(url)
            time.sleep(WAIT_TIME)
            
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
                    # 檢查是否已經處理過這個位置
                    position_key = f"{ad_info['position']}_{image_info['width']}x{image_info['height']}"
                    if position_key in processed_positions:
                        print(f"跳過已處理的位置: {ad_info['position']}")
                        continue
                        
                    try:
                        if self.replace_ad_content(ad_info['element'], image_data, image_info['width'], image_info['height']):
                            print(f"成功替換 nicklee.tw 廣告: {ad_info['width']}x{ad_info['height']} at {ad_info['position']}")
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
                                print(f"滾動到廣告位置: {scroll_position:.0f}px")
                                
                                # 等待滾動完成
                                time.sleep(1)
                                
                            except Exception as e:
                                print(f"滾動到廣告位置失敗: {e}")
                            
                            # 每次替換後立即截圖
                            print("準備截圖...")
                            time.sleep(2)  # 等待頁面穩定
                            screenshot_path = self.take_screenshot()
                            if screenshot_path:
                                screenshot_paths.append(screenshot_path)
                                print(f"✅ 截圖保存: {screenshot_path}")
                            else:
                                print("❌ 截圖失敗")
                            
                            # 截圖後復原該位置的廣告
                            try:
                                self.driver.execute_script("""
                                    // 移除我們添加的按鈕
                                    var closeBtn = document.querySelector('#close_button');
                                    var infoBtn = document.querySelector('#abgb');
                                    if (closeBtn) closeBtn.remove();
                                    if (infoBtn) infoBtn.remove();
                                    
                                    // 復原原始廣告內容（這裡需要根據實際情況調整）
                                    var element = arguments[0];
                                    if (element.tagName === 'IMG') {
                                        // 如果是圖片，恢復原始src
                                        element.src = element.getAttribute('data-original-src') || element.src;
                                    } else if (element.tagName === 'IFRAME') {
                                        // 如果是iframe，恢復可見性
                                        element.style.visibility = 'visible';
                                    }
                                """, ad_info['element'])
                                print("✅ nicklee.tw 廣告位置已復原")
                            except Exception as e:
                                print(f"復原 nicklee.tw 廣告失敗: {e}")
                            
                            # 繼續尋找下一個廣告位置，不要break
                            continue
                    except Exception as e:
                        print(f"替換 nicklee.tw 廣告失敗: {e}")
                        continue
                
                if not replaced:
                    print(f"所有找到的 {image_info['width']}x{image_info['height']} nicklee.tw 廣告位置都無法替換")
            
            # 總結處理結果
            if total_replacements > 0:
                print(f"\n{'='*50}")
                print(f"nicklee.tw 網站處理完成！總共成功替換了 {total_replacements} 個廣告")
                print(f"截圖檔案:")
                for i, path in enumerate(screenshot_paths, 1):
                    print(f"  {i}. {path}")
                print(f"{'='*50}")
                return screenshot_paths
            else:
                print("本 nicklee.tw 網頁沒有找到任何可替換的廣告")
                return []
                
        except Exception as e:
            print(f"處理 nicklee.tw 網站失敗: {e}")
            return []
    
    def take_screenshot(self):
        if not os.path.exists(SCREENSHOT_FOLDER):
            os.makedirs(SCREENSHOT_FOLDER)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"{SCREENSHOT_FOLDER}/nicklee_replaced_{timestamp}.png"
        
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
    # 偵測並選擇螢幕
    screen_id, selected_screen = ScreenManager.select_screen()
    
    if screen_id is None:
        print("未選擇螢幕，程式結束")
        return
    
    print(f"\n正在啟動 Chrome 瀏覽器到螢幕 {screen_id}...")
    bot = NickleeAdReplacer(headless=False, screen_id=screen_id)
    
    try:
        # 尋找 nicklee.tw 文章連結
        news_urls = bot.get_nicklee_article_urls(NICKLEE_BASE_URL, NEWS_COUNT)
        
        if not news_urls:
            print("無法獲取 nicklee.tw 文章連結")
            return
        
        print(f"從 nicklee.tw 獲取到 {len(news_urls)} 個文章連結")
        print(f"目標截圖數量: {SCREENSHOT_COUNT}")
        
        total_screenshots = 0
        
        # 處理每個 nicklee.tw 文章
        for i, url in enumerate(news_urls, 1):
            print(f"\n{'='*50}")
            print(f"處理第 {i}/{len(news_urls)} 個 nicklee.tw 文章")
            print(f"{'='*50}")
            
            try:
                # 處理 nicklee.tw 文章並嘗試替換廣告
                screenshot_paths = bot.process_website(url)
                
                if screenshot_paths:
                    print(f"✅ 成功處理 nicklee.tw 文章！共產生 {len(screenshot_paths)} 張截圖")
                    total_screenshots += len(screenshot_paths)
                    
                    # 檢查是否達到目標截圖數量
                    if total_screenshots >= SCREENSHOT_COUNT:
                        print(f"✅ 已達到目標截圖數量: {SCREENSHOT_COUNT}")
                        break
                else:
                    print("❌ nicklee.tw 文章處理完成，但沒有找到可替換的廣告")
                
            except Exception as e:
                print(f"❌ 處理 nicklee.tw 文章失敗: {e}")
                continue
            
            # 在處理下一個 nicklee.tw 文章前稍作休息
            if i < len(news_urls) and total_screenshots < SCREENSHOT_COUNT:
                print("等待 3 秒後處理下一個 nicklee.tw 文章...")
                time.sleep(3)
        
        print(f"\n{'='*50}")
        print(f"所有 nicklee.tw 文章處理完成！總共產生 {total_screenshots} 張截圖")
        print(f"{'='*50}")
        
    finally:
        bot.close()

def test_screen_setup():
    """測試螢幕設定功能"""
    print("測試 nicklee.tw 螢幕偵測功能...")
    
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
    test_bot = NickleeAdReplacer(headless=False, screen_id=screen_id)
    
    try:
        # 開啟 nicklee.tw 測試頁面
        test_bot.driver.get(NICKLEE_BASE_URL)
        time.sleep(3)
        
        # 測試截圖功能
        print("測試截圖功能...")
        screenshot_path = test_bot.take_screenshot()
        
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