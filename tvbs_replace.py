#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBS 食尚玩家廣告替換器 - GIF 升級版
專注於 TVBS 食尚玩家網站 (supertaste.tvbs.com.tw)

核心功能：
- 智能廣告掃描和替換系統
- 支援多種按鈕樣式 (dots, cross, adchoices, adchoices_dots, none)
- 6段式滾動觸發懶載入廣告檢測
- ETtoday 風格的廣告還原機制（不刷新頁面）
- Yahoo 風格的 SVG 按鈕設計（正方形按鈕）
- GIF 廣告檢測和統計分析
- 多螢幕支援 (Windows, macOS, Linux)
- 嚴格的外部網域過濾機制
- 整合 nicklee 的精確檢測邏輯

版本：正式版 v1.0
作者：TVBS 廣告替換系統
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
from urllib.parse import urlparse

# 載入 GIF 功能專用設定檔
try:
    from gif_config import *
    print("成功載入 gif_config.py 設定檔")
    print(f"SCREENSHOT_COUNT 設定: {SCREENSHOT_COUNT}")
    print(f"NEWS_COUNT 設定: {NEWS_COUNT}")
    print(f"IMAGE_USAGE_COUNT 設定: {IMAGE_USAGE_COUNT}")
    print(f"GIF_PRIORITY 設定: {GIF_PRIORITY}")
    # 覆蓋 gif_config.py 中的 BASE_URL，設定 TVBS 專用網址
    TVBS_BASE_URL = "https://supertaste.tvbs.com.tw/travel"
    # print(f"RANDOM_SELECTION 設定: {RANDOM_SELECTION}")  # 已移除隨機選擇功能
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
    BASE_URL = "https://supertaste.tvbs.com.tw/travel"
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
    # RANDOM_SELECTION = False  # 已移除隨機選擇功能

# 嘗試載入 MSS 截圖庫
try:
    import mss
    MSS_AVAILABLE = True
    print("MSS 截圖庫可用")
except ImportError:
    MSS_AVAILABLE = False
    print("MSS 截圖庫不可用，將使用 Selenium 截圖")

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
    TVBS 食尚玩家廣告替換器 - 正式版
    專注於 TVBS 食尚玩家 (supertaste.tvbs.com.tw) 網站
    
    整合功能：
    - 智能廣告檢測與替換
    - ETtoday 風格還原機制
    - Yahoo 風格 SVG 按鈕
    - nicklee 精確過濾邏輯
    - 多螢幕支援系統
    """
    def __init__(self, headless=False, screen_id=1, button_style=None):
        self.screen_id = screen_id
        self.button_style = button_style or BUTTON_STYLE  # 設定按鈕樣式
        print(f"🎨 按鈕樣式設定為: {self.button_style}")
        self.setup_driver(headless)
        self.load_replace_images()
        # 統計變數
        self.total_screenshots = 0      # 總截圖數量
        self.total_replacements = 0     # 總替換次數
        self.gif_replacements = 0       # GIF 替換次數
        self.static_replacements = 0    # 靜態圖片替換次數
        self.replacement_details = []   # 詳細替換記錄
       
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
        """根據優先級策略選擇圖片（已移除隨機模式）"""
        
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
        
        # 兩種類型都有，根據 GIF_PRIORITY 優先級選擇
        try:
            gif_priority = globals().get('GIF_PRIORITY', True)
        except:
            # 如果配置不存在，使用預設值
            gif_priority = True
        
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

    def load_image_base64(self, image_path):
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"找不到圖片: {image_path}")
            
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def _update_screenshot_count(self, filepath, current_image_info, original_ad_info):
        """更新截圖統計並返回檔案路徑"""
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
    

    def _is_valid_tvbs_url(self, url):
        """檢查是否為有效的 TVBS 文章 URL，採用嚴格過濾邏輯"""
        if not url:
            return False
        
        # 嚴格過濾外部網域連結 - 整合自 nicklee 的邏輯
        external_domains = [
            'facebook.com', 'fb.com', 'twitter.com', 'x.com', 't.co',
            'instagram.com', 'youtube.com', 'linkedin.com', 'pinterest.com',
            'google.com', 'gmail.com', 'yahoo.com', 'bing.com',
            'amazon.com', 'booking.com', 'agoda.com', 'expedia.com',
            'line.me', 'telegram.org', 'whatsapp.com', 'wechat.com',
            'apple.com', 'microsoft.com', 'adobe.com'
        ]
        
        # 檢查是否包含外部網域 - 這是最重要的檢查
        url_lower = url.lower()
        for domain in external_domains:
            if domain in url_lower:
                print(f"    ❌ 過濾外部網站連結: {domain} in {url[:60]}...")
                return False
        
        # 必須是 TVBS 網站
        if 'supertaste.tvbs.com.tw' not in url:
            print(f"    ❌ 非 TVBS 網域: {url[:60]}...")
            return False
        
        parsed = urlparse(url_lower)
        path = parsed.path or ''
        
        # 排除分享連結模式 - 整合自 nicklee 的邏輯
        share_patterns = ['sharer.php', 'share?', '/share/', 'utm_source', 'utm_medium', 'taboola']
        for pattern in share_patterns:
            if pattern in url_lower:
                print(f"    ❌ 過濾分享連結: {pattern} in {url[:60]}...")
                return False
        
        # 排除的 URL 模式 - 整合自 nicklee 的邏輯
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
        
        # 排除圖片和媒體檔案 - 整合自 nicklee 的邏輯
        media_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', 
                           '.mp4', '.mp3', '.pdf', '.zip', '.rar']
        for ext in media_extensions:
            if url_lower.endswith(ext):
                return False

        # 不接受純分類頁面，需要進到文章頁
        category_only_paths = ['/', '/travel', '/travel/', '/life', '/life/']
        if path in category_only_paths:
            return False

        # TVBS 文章需符合以下任一模式（放寬限制）：
        # 1) /<分類>/<數字> (如 /travel/123, /food/456, /pack/789, /hot/101)
        # 2) 包含 /article/ 或 /post/
        # 3) 結尾是 .html
        has_category_id = re.search(r'^/[a-z]+/\d+(?:/)?$', path) is not None
        has_article_slug = ('/article/' in path) or ('/post/' in path)
        has_html = path.endswith('.html')
        
        # 必須符合 TVBS 文章 URL 模式
        if has_category_id or has_article_slug or has_html:
            print(f"    ✅ 有效 TVBS 文章連結: {url[:60]}...")
            return True
        else:
            print(f"    ❌ 不符合 TVBS 文章 URL 模式: {url[:60]}...")
            return False
    
    def get_random_news_urls(self, base_url, count=5):
        try:
            self.driver.get(base_url)
            time.sleep(WAIT_TIME)
            # 追加等待讓懶載入觸發
            try:
                state = self.driver.execute_script("return document.readyState;")
                print(f"頁面 readyState: {state}")
            except Exception:
                pass
            # 逐步觸發滾動
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(1.5)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
            except Exception:
                pass
            
            # TVBS 食尚玩家文章連結搜尋器，整合通用部落格選擇器邏輯
            link_selectors = [
                # TVBS 特定選擇器（首選）
                ".article__content > a.article__item[href]",
                "a.article__item[href]",
                "div.article__content a.article__item[href]",
                
                # TVBS 內容區域選擇器
                "a[href*='/article/'][href*='supertaste.tvbs.com.tw']",
                "a[href^='/article/']",
                "a[href*='/travel/']",
                "a[href*='/life/']",
                "a[href*='supertaste.tvbs.com.tw']",
                
                # TVBS 推薦和相關文章
                ".recommend-list a",
                ".related-articles a", 
                ".popular-articles a"
            ]
            
            news_urls = []

            # 多輪搜尋：先滾動收集連結到收集到 count 個連結或最大輪數
            max_rounds = 5
            for round_idx in range(1, max_rounds + 1):
                print(f"搜尋第 {round_idx}/{max_rounds} 輪連結...")
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
                        # 確保完整 URL
                        if href.startswith('/'):
                            full_url = base_url.rstrip('/') + href
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            full_url = base_url.rstrip('/') + '/' + href.lstrip('./')
                        
                        # 收集所有 TVBS 文章連結，排除廣告推薦連結
                        if self._is_valid_tvbs_url(full_url) and full_url not in news_urls:
                            news_urls.append(full_url)
                            valid_count += 1
                        else:
                            invalid_count += 1
                    print(f"  選擇器 {i} 結果: {valid_count} 個有效連結, {invalid_count} 個無效連結")

                # 如果已足夠就跳出
                if len(news_urls) >= count:
                    break

                # 滾動頁面讓網站載入更多卡片
                try:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    self.driver.execute_script("window.scrollBy(0, -200);")
                    time.sleep(1)
                except Exception:
                    pass
            
            # 去除重複URL
            news_urls = list(set(news_urls))
            
            # 後備：若仍不足夠連結，用 a[href] 通用語法過濾，特別針對 a.article__item
            if len(news_urls) < count:
                try:
                    print("啟用後備搜尋 a[href] ...")
                    all_links = []
                    # 先 a.article__item 連結
                    all_links.extend(self.driver.find_elements(By.CSS_SELECTOR, "a.article__item[href]"))
                    # 旅遊分類頁
                    all_links.extend(self.driver.find_elements(By.CSS_SELECTOR, "a[href^='/travel/']"))
                    # 一般連結
                    all_links.extend(self.driver.find_elements(By.CSS_SELECTOR, "a[href]"))
                    added = 0
                    for a in all_links:
                        href = a.get_attribute('href')
                        if not href:
                            continue
                        # 相對路徑轉絕對路徑
                        if href.startswith('/'):
                            full_url = base_url.rstrip('/') + href
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            full_url = base_url.rstrip('/') + '/' + href.lstrip('./')
                        # 檢查是 TVBS 連結且為旅遊/生活/文章頁面
                        if self._is_valid_tvbs_url(full_url) and full_url not in news_urls:
                            news_urls.append(full_url)
                            added += 1
                    print(f"後備搜尋新增 {added} 個連結")
                except Exception as e:
                    print(f"後備搜尋失敗: {e}")

            # 最終去重
            news_urls = list(dict.fromkeys(news_urls))

            print(f"找到 {len(news_urls)} 個新聞連結")
            if news_urls:
                selected_urls = random.sample(news_urls, min(count, len(news_urls)))
                print(f"隨機選擇 {len(selected_urls)} 個連結:")
                for i, url in enumerate(selected_urls):
                    print(f"  {i+1}. {url}")
                return selected_urls
            else:
                print("未找到任何 TVBS 新聞連結")
                print("可能原因:")
                print("  1. TVBS 網站結構可能已變更")
                print("  2. 網站載入不完整，請檢查網路連線")
                print("  3. CSS 選擇器需要更新")
                print("  4. 網頁可能需要更長的載入時間")
                return []
                        
        except Exception as e:
            print(f"獲取新聞連結失敗: {e}")
            return []
    
    def scan_and_replace_ads_immediately(self, target_width, target_height, image_data, selected_image):
        """掃描並立即替換廣告 - 參考 ETtoday 的完整流程"""
        print(f"開始掃描並立即替換 {target_width}x{target_height} 的廣告...")
        
        # 使用 ETtoday 風格的全頁面掃描
        matching_ads = self.scan_entire_page_for_ads(target_width, target_height)
        
        if not matching_ads:
            print(f"未找到 {target_width}x{target_height} 的廣告")
            return 0
        
        replaced_count = 0
        
        for ad_info in matching_ads:
            try:

                
                # 替換廣告
                replacement_result = self.replace_ad_content(ad_info['element'], image_data, 
                                                          target_width, target_height)
                
                if replacement_result:
                    replaced_count += 1
                    
                    # 滾動到廣告位置並截圖
                    try:
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
                        
                        viewport_height = self.driver.execute_script("return window.innerHeight;")
                        scroll_position = element_rect['top'] - (viewport_height / 2) + (element_rect['height'] / 2)
                        
                        self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                        print(f"滾動到廣告位置: {scroll_position:.0f}px")
                        
                        time.sleep(1)
                        
                        # 截圖
                        try:
                            page_title = self.driver.title
                        except:
                            page_title = None
                            
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        safe_title = re.sub(r'[^\w\s-]', '', page_title or 'unknown')[:50] if page_title else 'unknown'
                        safe_title = re.sub(r'[-\s]+', '_', safe_title)
                        
                        screenshot_filename = f"tvbs_{safe_title}_{timestamp}.png"
                        screenshot_path = os.path.join(SCREENSHOT_FOLDER, screenshot_filename)
                        
                        if not os.path.exists(SCREENSHOT_FOLDER):
                            os.makedirs(SCREENSHOT_FOLDER)
                        
                        # 使用統一的截圖方法
                        self._take_screenshot_with_urlbar(screenshot_path)
                        
                        # 更新統計
                        self._update_screenshot_count(screenshot_path, selected_image, None)
                        
                    except Exception as e:
                        print(f"截圖失敗: {e}")
                    
                    # 復原廣告
                    try:
                        self.restore_ad_content(ad_info['element'])
                    except Exception as e:
                        print(f"復原廣告失敗: {e}")
                    
                    # 繼續處理下一個廣告
                    continue
                else:
                    print(f"❌ 替換廣告失敗: {ad_info['position']}")
                    
            except Exception as e:
                print(f"❌ 替換廣告失敗: {ad_info['position']}")
                continue
        
        print(f"掃描完成，找到 {len(matching_ads)} 個符合尺寸的廣告元素")
        if replaced_count == 0:
            print(f"未找到 {target_width}x{target_height} 的廣告")
        
        return replaced_count
    
    def scan_entire_page_for_ads(self, target_width, target_height):
        """掃描整個網頁尋找符合尺寸的廣告元素 - 參考 ETtoday 風格"""
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
                
                # 允許小幅度的尺寸誤差（±2像素）
                if (size_info and 
                    size_info['visible'] and
                    abs(size_info['width'] - target_width) <= 2 and 
                    abs(size_info['height'] - target_height) <= 2):
                    
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
                                    
                                    # 等待滾動完成


    def scan_entire_page_for_ads(self, target_width, target_height):
        """掃描整個網頁尋找符合尺寸的廣告元素 - 保留原有邏輯作為備用"""
        print(f"開始掃描整個網頁尋找 {target_width}x{target_height} 的廣告...")
        
        # 優化：直接尋找廣告相關元素，避免掃描所有元素
        print("正在尋找廣告相關元素...")
        
        # 優化：只獲取可能的廣告元素，提高效率
        all_elements = self.driver.execute_script("""
            var targetWidth = arguments[0];
            var targetHeight = arguments[1];
            var potentialAds = [];
            
            // 優先搜尋廣告相關的選擇器（整合 nicklee 的廣告檢測邏輯）
            var adSelectors = [
                // Google AdSense 相關（整合自 nicklee）
                'ins.adsbygoogle',
                'div[id^="aswift_"]',
                'iframe[id^="aswift_"]',
                
                // 原有的 Google 廣告選擇器
                '[id*="google"]', '[class*="google"]', 
                'iframe[src*="google"]', 'iframe[src*="doubleclick"]',
                
                // 廣告容器選擇器（整合自 nicklee）
                '[id*="ads"]', '[class*="ads"]',
                '[id*="banner"]', '[class*="banner"]',
                '[class*="ad"]', '[id*="ad"]',
                
                // 尺寸匹配選擇器
                'div[style*="width: ' + targetWidth + 'px"]',
                'div[style*="height: ' + targetHeight + 'px"]',
                
                // TVBS 特定選擇器
                '[id*="supertaste"]', '[class*="tvbs"]',
                
                // 圖片廣告選擇器（整合自 nicklee）
                'img[src*="ad"]', 'img[src*="banner"]', 'img[src*="google"]',
                
                // iframe 廣告選擇器（整合自 nicklee）
                'iframe[src*="ad"]', 'iframe[src*="banner"]',
                
                // 通用廣告容器
                '.advertisement', '.ad-container', '.ad-banner',
                '.google-ad', '.adsense', '.ad-slot', '.sidebar-ad'
            ];
            
            for (var selector of adSelectors) {
                try {
                    var elements = document.querySelectorAll(selector);
                    for (var element of elements) {
                        if (potentialAds.indexOf(element) === -1) {
                            potentialAds.push(element);
                        }
                    }
                } catch (e) {
                    // 忽略無效選擇器
                }
            }
            
            // 如果找不到廣告元素，則回退到檢查所有可見元素（但限制數量）
            if (potentialAds.length === 0) {
                var allElements = document.querySelectorAll('*');
                for (var i = 0; i < Math.min(allElements.length, 500); i++) {
                    var element = allElements[i];
                    var style = window.getComputedStyle(element);
                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                        potentialAds.push(element);
                    }
                }
            }
            
            return potentialAds;
        """, target_width, target_height)
        
        print(f"找到 {len(all_elements)} 個潛在廣告元素，開始檢查尺寸...")
        
        matching_elements = []
        processed_positions = set()  # 記錄已處理的位置，避免重複
        
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
                    size_info['height'] == target_height and
                    size_info['width'] > 0 and 
                    size_info['height'] > 0):
                    
                    # 檢查是否為廣告元素（整合 nicklee 的精確檢測邏輯）
                    is_ad_element = self.driver.execute_script("""
                        var element = arguments[0];
                        var tagName = element.tagName.toLowerCase();
                        var className = element.className || '';
                        var id = element.id || '';
                        var src = element.src || '';
                        
                        // 廣告關鍵字檢查（整合自 nicklee）
                        var adKeywords = ['ad', 'advertisement', 'banner', 'google', 'ads', 'adsense', 'adsbygoogle'];
                        var hasAdKeyword = adKeywords.some(function(keyword) {
                            return className.toLowerCase().includes(keyword) ||
                                   id.toLowerCase().includes(keyword) ||
                                   src.toLowerCase().includes(keyword);
                        });
                        
                        // 檢查父元素是否有廣告特徵（整合自 nicklee）
                        var parent = element.parentElement;
                        var parentHasAdKeyword = false;
                        if (parent) {
                            var parentClass = parent.className || '';
                            var parentId = parent.id || '';
                            parentHasAdKeyword = adKeywords.some(function(keyword) {
                                return parentClass.toLowerCase().includes(keyword) ||
                                       parentId.toLowerCase().includes(keyword);
                            });
                        }
                        
                        // 原有的廣告容器檢查
                        var isAdContainer = (
                            id.includes('google_ads') || 
                            id.includes('ads-') ||
                            className.includes('google') ||
                            className.includes('ads') ||
                            id.includes('ads')
                        );
                        
                        // 檢查是否包含廣告 iframe
                        var hasAdIframe = element.querySelector('iframe[src*="googleads"], iframe[src*="googlesyndication"], iframe[src*="doubleclick"]');
                        
                        // 檢查是否為廣告 iframe
                        var isAdIframe = tagName === 'iframe' && (
                            src.includes('googleads') || 
                            src.includes('googlesyndication') || 
                            src.includes('doubleclick')
                        );
                        
                        // 檢查是否有廣告腳本
                        var hasAdScript = element.querySelector('script[src*="google"]');
                        
                        // 整合所有檢查結果
                        return hasAdKeyword || parentHasAdKeyword || isAdContainer || hasAdIframe || isAdIframe || hasAdScript;
                    """, element)
                    
                    if is_ad_element:
                        # 再次驗證尺寸
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
                            # 檢查位置是否已處理過，避免重複
                            position_key = f"{size_info['top']:.0f},{size_info['left']:.0f}"
                            if position_key not in processed_positions:
                                processed_positions.add(position_key)
                                matching_elements.append({
                                    'element': element,
                                    'width': final_verification['width'],
                                    'height': final_verification['height'],
                                    'position': f"top:{size_info['top']:.0f}, left:{size_info['left']:.0f}",
                                    'display': final_verification['display'],
                                    'visibility': final_verification['visibility']
                                })
                                print(f"找到符合尺寸的廣告元素: {target_width}x{target_height} at {size_info['top']:.0f},{size_info['left']:.0f}")
                            else:
                                print(f"跳過重複位置: {position_key}")
                
                # 只在處理大量元素時顯示進度
                if len(all_elements) > 200 and (i + 1) % 100 == 0:
                    print(f"已檢查 {i + 1}/{len(all_elements)} 個元素...")
                    
            except Exception as e:
                continue
        
        print(f"掃描完成，找到 {len(matching_elements)} 個符合尺寸的廣告元素")
        return matching_elements
    
    def get_button_style(self):
        """根據配置返回按鈕樣式 - 採用 Yahoo 風格的完整設計"""
        button_style = getattr(self, 'button_style', BUTTON_STYLE)

        
        # 統一的資訊按鈕樣式 - 針對 TVBS 網站優化，確保位置一致
        unified_info_button = {
            "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:block;width:15px;height:15px;"><path d="M7.5 1.5a6 6 0 100 12 6 6 0 100-12m0 1a5 5 0 110 10 5 5 0 110-10zM6.625 11h1.75V6.5h-1.75zM7.5 3.75a1 1 0 100 2 1 1 0 100-2z" fill="#00aecd"/></svg>',
            "style": 'position:absolute;top:1px;right:17px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);cursor:pointer;margin:0;padding:0;border:none;box-sizing:border-box;line-height:0;vertical-align:top;'
        }
        
        button_styles = {
            "dots": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:block;width:15px;height:15px;"><circle cx="7.5" cy="3.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="7.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="11.5" r="1.5" fill="#00aecd"/></svg>',
                    "style": 'position:absolute;top:1px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;margin:0;padding:0;border:none;box-sizing:border-box;line-height:0;vertical-align:top;'
                },
                "info_button": unified_info_button
            },
            "cross": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:block;width:15px;height:15px;"><path d="M4 4L11 11M11 4L4 11" stroke="#00aecd" stroke-width="1.5" stroke-linecap="round"/></svg>',
                    "style": 'position:absolute;top:1px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;margin:0;padding:0;border:none;box-sizing:border-box;line-height:0;vertical-align:top;'
                },
                "info_button": unified_info_button
            },
            "adchoices": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:block;width:15px;height:15px;"><path d="M4 4L11 11M11 4L4 11" stroke="#00aecd" stroke-width="1.5" stroke-linecap="round"/></svg>',
                    "style": 'position:absolute;top:1px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;margin:0;padding:0;border:none;box-sizing:border-box;line-height:0;vertical-align:top;'
                },
                "info_button": {
                    "html": '<img src="https://tpc.googlesyndication.com/pagead/images/adchoices/adchoices_blue_wb.png" width="15" height="15" style="display:block;width:15px;height:15px;vertical-align:top;">',
                    "style": 'position:absolute;top:1px;right:17px;width:15px;height:15px;z-index:100;display:block;cursor:pointer;margin:0;padding:0;border:none;box-sizing:border-box;line-height:0;vertical-align:top;'
                }
            },
            "adchoices_dots": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:block;width:15px;height:15px;"><circle cx="7.5" cy="3.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="7.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="11.5" r="1.5" fill="#00aecd"/></svg>',
                    "style": 'position:absolute;top:1px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;margin:0;padding:0;border:none;box-sizing:border-box;line-height:0;vertical-align:top;'
                },
                "info_button": {
                    "html": '<img src="https://tpc.googlesyndication.com/pagead/images/adchoices/adchoices_blue_wb.png" width="15" height="15" style="display:block;width:15px;height:15px;vertical-align:top;">',
                    "style": 'position:absolute;top:1px;right:17px;width:15px;height:15px;z-index:100;display:block;cursor:pointer;margin:0;padding:0;border:none;box-sizing:border-box;line-height:0;vertical-align:top;'
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
        """修復版本 - 參考 ETtoday 的完整流程"""
        try:
            # 檢查元素是否仍然有效
            try:
                element.is_displayed()
                element.get_attribute('tagName')
            except Exception as e:
                print(f"元素引用已過期，跳過此廣告: {e}")
                return None
            
            # 獲取原始廣告資訊
            original_info = self.driver.execute_script("""
                var element = arguments[0];
                if (!element || !element.getBoundingClientRect) return null;
                var rect = element.getBoundingClientRect();
                
                // 檢查是否包含 GIF
                var hasGif = false;
                try {
                    var checkForGif = function(text) {
                        return text && text.toLowerCase().includes('.gif');
                    };
                    
                    if (element.tagName.toLowerCase() === 'img' && element.src) {
                        hasGif = checkForGif(element.src);
                    }
                    
                    var style = window.getComputedStyle(element);
                    if (style.backgroundImage && style.backgroundImage !== 'none') {
                        hasGif = hasGif || checkForGif(style.backgroundImage);
                    }
                    
                    var imgs = element.querySelectorAll('img');
                    for (var i = 0; i < imgs.length; i++) {
                        if (imgs[i].src && checkForGif(imgs[i].src)) {
                            hasGif = true;
                            break;
                        }
                    }
                } catch(e) {}
                
                return {
                    width: rect.width, 
                    height: rect.height,
                    hasGif: hasGif
                };
            """, element)
            
            if not original_info:
                return None
            
            # 檢查尺寸匹配
            if (abs(original_info['width'] - target_width) > 2 or 
                abs(original_info['height'] - target_height) > 2):
                print(f"尺寸不匹配: 期望 {target_width}x{target_height}, 實際 {original_info['width']}x{original_info['height']}")
                return None
            
            # 獲取按鈕樣式
            button_style = self.get_button_style()
            close_button_html = button_style["close_button"]["html"]
            close_button_style = button_style["close_button"]["style"]
            info_button_html = button_style["info_button"]["html"]
            info_button_style = button_style["info_button"]["style"]
            
            # 檢查是否為 none 模式
            current_button_style = getattr(self, 'button_style', BUTTON_STYLE)
            is_none_mode = current_button_style == "none"
            
            # 修復的 JavaScript 程式碼 - 分段執行避免語法錯誤
            success = self.driver.execute_script("""
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
                
                // 移除舊按鈕
                var oldButtons = container.querySelectorAll('#close_button, #abgb, #info_button');
                for (var i = 0; i < oldButtons.length; i++) {
                    oldButtons[i].remove();
                }
                
                var replacedCount = 0;
                var newImageSrc = 'data:image/jpeg;base64,' + imageBase64;
                
                // 替換 img 標籤
                var imgs = container.querySelectorAll('img');
                for (var i = 0; i < imgs.length; i++) {
                    var img = imgs[i];
                    var imgRect = img.getBoundingClientRect();
                    
                    // 排除控制按鈕
                    var isControlButton = imgRect.width < 50 || imgRect.height < 50 || 
                                         img.className.includes('abg') || 
                                         img.id.includes('abg') ||
                                         img.src.includes('googleads') ||
                                         img.src.includes('googlesyndication');
                    
                    if (!isControlButton && img.src && !img.src.startsWith('data:')) {
                        // 保存原始資料
                        if (!img.getAttribute('data-original-src')) {
                            img.setAttribute('data-original-src', img.src);
                        }
                        if (!img.getAttribute('data-original-style')) {
                            img.setAttribute('data-original-style', img.style.cssText || '');
                        }
                        
                        // 替換圖片
                        img.src = newImageSrc;
                        img.style.objectFit = 'contain';
                        img.style.width = '100%';
                        img.style.height = 'auto';
                        img.style.display = 'block';
                        replacedCount++;
                        
                        // 確保父層是 relative
                        var imgParent = img.parentElement || container;
                        if (window.getComputedStyle(imgParent).position === 'static') {
                            imgParent.style.position = 'relative';
                        }
                    }
                }
                
                // 處理 iframe
                var iframes = container.querySelectorAll('iframe');
                for (var i = 0; i < iframes.length; i++) {
                    var iframe = iframes[i];
                    iframe.style.visibility = 'hidden';
                    
                    var iframeRect = iframe.getBoundingClientRect();
                    var newImg = document.createElement('img');
                    newImg.src = newImageSrc;
                    newImg.style.position = 'absolute';
                    newImg.style.top = (iframeRect.top - container.getBoundingClientRect().top) + 'px';
                    newImg.style.left = (iframeRect.left - container.getBoundingClientRect().left) + 'px';
                    newImg.style.width = Math.round(iframeRect.width) + 'px';
                    newImg.style.height = Math.round(iframeRect.height) + 'px';
                    newImg.style.objectFit = 'contain';
                    newImg.setAttribute('data-replacement-img', 'true');
                    
                    container.appendChild(newImg);
                    replacedCount++;
                }
                
                // 處理背景圖片
                if (replacedCount === 0) {
                    var style = window.getComputedStyle(container);
                    if (style.backgroundImage && style.backgroundImage !== 'none') {
                        if (!container.getAttribute('data-original-background')) {
                            container.setAttribute('data-original-background', style.backgroundImage);
                        }
                        container.style.backgroundImage = 'url(' + newImageSrc + ')';
                        container.style.backgroundSize = 'contain';
                        container.style.backgroundRepeat = 'no-repeat';
                        container.style.backgroundPosition = 'center';
                        replacedCount = 1;
                    }
                }
                
                // 添加按鈕 - 修復版本，確保位置一致
                if (!isNoneMode && replacedCount > 0) {
                    // 強制重新計算容器樣式
                    container.offsetHeight;
                    
                    if (closeButtonHtml) {
                        var closeButton = document.createElement('div');
                        closeButton.id = 'close_button';
                        closeButton.innerHTML = closeButtonHtml;
                        // 強制使用精確的樣式，避免容器影響
                        closeButton.style.cssText = 'position:absolute!important;top:1px!important;right:1px!important;width:15px!important;height:15px!important;z-index:101!important;display:block!important;background-color:rgba(255,255,255,1)!important;cursor:pointer!important;margin:0!important;padding:0!important;border:none!important;box-sizing:border-box!important;line-height:0!important;vertical-align:top!important;';
                        container.appendChild(closeButton);
                        
                        // 強制重新計算按鈕位置
                        closeButton.offsetHeight;
                    }
                    
                    if (infoButtonHtml) {
                        var infoButton = document.createElement('div');
                        infoButton.id = 'abgb';
                        infoButton.innerHTML = infoButtonHtml;
                        // 強制使用精確的樣式，避免容器影響
                        infoButton.style.cssText = 'position:absolute!important;top:1px!important;right:17px!important;width:15px!important;height:15px!important;z-index:100!important;display:block!important;background-color:rgba(255,255,255,1)!important;cursor:pointer!important;margin:0!important;padding:0!important;border:none!important;box-sizing:border-box!important;line-height:0!important;vertical-align:top!important;';
                        container.appendChild(infoButton);
                        
                        // 強制重新計算按鈕位置
                        infoButton.offsetHeight;
                    }
                }
                
                return replacedCount > 0;
            """, element, image_data, target_width, target_height, close_button_html, close_button_style, info_button_html, info_button_style, is_none_mode)
            
            if success:
                print(f"✅ 替換廣告成功 {original_info['width']}x{original_info['height']}")
                if original_info.get('hasGif'):
                    print(f"📊 檢測到 GIF 廣告內容")
                return original_info  # 返回完整的廣告資訊
            else:
                print(f"❌ 廣告替換失敗 {original_info['width']}x{original_info['height']}")
                return None
                
        except Exception as e:
            print(f"替換廣告時發生錯誤: {e}")
            return None
    
    def restore_ad_content(self, element):
        """還原廣告內容 - 參考 ETtoday 風格"""
        try:
            self.driver.execute_script("""
                var container = arguments[0];
                if (!container) return false;
                
                // 移除我們添加的按鈕
                var buttons = container.querySelectorAll('#close_button, #abgb, #info_button');
                for (var i = 0; i < buttons.length; i++) {
                    buttons[i].remove();
                }
                
                // 移除我們添加的圖片
                var addedImages = container.querySelectorAll('img[src^="data:image/jpeg;base64"], img[data-replacement-img="true"]');
                for (var i = 0; i < addedImages.length; i++) {
                    addedImages[i].remove();
                }
                
                // 復原函數
                function restoreElement(el) {
                    if (el.tagName === 'IMG') {
                        var originalSrc = el.getAttribute('data-original-src');
                        if (originalSrc) {
                            el.src = originalSrc;
                            el.removeAttribute('data-original-src');
                        }
                        var originalStyle = el.getAttribute('data-original-style');
                        if (originalStyle !== null) {
                            el.style.cssText = originalStyle;
                            el.removeAttribute('data-original-style');
                        }
                    } else if (el.tagName === 'IFRAME') {
                        el.style.visibility = 'visible';
                    }
                    
                    // 復原背景圖片
                    var originalBg = el.getAttribute('data-original-background');
                    if (originalBg) {
                        el.style.backgroundImage = originalBg;
                        el.removeAttribute('data-original-background');
                    }
                }
                
                // 復原主要元素
                restoreElement(container);
                
                // 復原所有圖片
                var imgs = container.querySelectorAll('img[data-original-src]');
                for (var i = 0; i < imgs.length; i++) {
                    restoreElement(imgs[i]);
                }
                
                // 復原所有 iframe
                var iframes = container.querySelectorAll('iframe[style*="visibility: hidden"]');
                for (var i = 0; i < iframes.length; i++) {
                    restoreElement(iframes[i]);
                }
                
                return true;
            """, element)
            print("✅ 廣告已復原")
        except Exception as e:
            print(f"復原廣告失敗: {e}")
    
    def _take_screenshot_with_urlbar(self, filepath):
        """統一的截圖方法，優先使用 MSS 以包含 URL bar"""
        try:
            # 優先使用 MSS 截圖以包含 URL bar
            if MSS_AVAILABLE:
                try:
                    with mss.mss() as sct:
                        monitor = sct.monitors[self.screen_id] if self.screen_id <= len(sct.monitors) - 1 else sct.monitors[1]
                        screenshot = sct.grab(monitor)
                        
                        from PIL import Image
                        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                        img.save(filepath)
                        print(f"✅ MSS 截圖保存 (包含 URL bar，螢幕 {self.screen_id}): {filepath}")
                        return True
                except Exception as mss_error:
                    print(f"MSS 截圖失敗: {mss_error}")
            
            # 備用方案：使用 Selenium 截圖
            self.driver.save_screenshot(filepath)
            print(f"⚠️ Selenium 截圖保存 (僅網頁內容，不含 URL bar): {filepath}")
            return True
            
        except Exception as e:
            print(f"截圖失敗: {e}")
            return False

    def take_screenshot(self, page_title=None, current_image_info=None, original_ad_info=None):
        """截圖功能，使用新聞標題命名"""
        if not os.path.exists(SCREENSHOT_FOLDER):
            os.makedirs(SCREENSHOT_FOLDER)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 清理頁面標題作為檔案名
        if page_title:
            clean_title = re.sub(r'[^\w\s-]', '', page_title)
            clean_title = re.sub(r'[-\s]+', '_', clean_title)[:50]
            filepath = f"{SCREENSHOT_FOLDER}/tvbs_{clean_title}_{timestamp}.png"
        else:
            filepath = f"{SCREENSHOT_FOLDER}/tvbs_replaced_{timestamp}.png"
        
        # 使用統一的截圖方法
        if self._take_screenshot_with_urlbar(filepath):
            return self._update_screenshot_count(filepath, current_image_info, original_ad_info)
        else:
            return None
    
    def process_website(self, url):
        """處理單個網站"""
        try:
            print(f"\n{'='*60}")
            print(f"正在處理網站: {url}")
            print(f"{'='*60}")
            
            # 載入網頁
            self.driver.get(url)
            time.sleep(WAIT_TIME)
            
            # 獲取頁面標題
            page_title = self.driver.title
            print(f"頁面標題: {page_title}")
            
            # 等待頁面完全載入和懶載入觸發
            print("等待頁面完全載入...")
            time.sleep(3)
            
            # 檢查頁面載入狀態
            try:
                state = self.driver.execute_script("return document.readyState;")
                print(f"頁面 readyState: {state}")
            except Exception:
                pass
            
            # 分段滾動觸發懶載入廣告 - 0%, 20%, 40%, 60%, 80%, 100%
            print("開始分段滾動觸發懶載入廣告...")
            scroll_positions = [0, 20, 40, 60, 80, 100]
            
            try:
                for i, position in enumerate(scroll_positions, 1):
                    print(f"第 {i}/6 階段：滾動到 {position}% 位置")
                    
                    # 計算滾動位置
                    scroll_script = f"""
                        var scrollHeight = Math.max(
                            document.body.scrollHeight,
                            document.documentElement.scrollHeight
                        );
                        var targetPosition = scrollHeight * {position / 100};
                        window.scrollTo(0, targetPosition);
                        return targetPosition;
                    """
                    
                    target_pos = self.driver.execute_script(scroll_script)
                    print(f"  滾動到位置: {target_pos}px ({position}%)")
                    
                    # 每個位置停留時間，讓廣告有時間載入
                    if position == 0:
                        time.sleep(2)  # 頂部停留較短
                    elif position == 100:
                        time.sleep(4)  # 底部停留較長，觸發更多懶載入
                    else:
                        time.sleep(3)  # 中間位置適中停留
                    
                    # 檢查是否有新的廣告元素載入
                    try:
                        ad_count = self.driver.execute_script("""
                            var ads = document.querySelectorAll('[id*="google"], [class*="ads"], iframe[src*="google"]');
                            return ads.length;
                        """)
                        print(f"  當前廣告元素數量: {ad_count}")
                    except:
                        pass
                
                # 最後回到頂部，準備開始掃描
                print("回到頂部，準備開始廣告掃描...")
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)
                
                print("✅ 分段滾動觸發完成")
            except Exception as e:
                print(f"分段滾動觸發失敗: {e}")
            
            # 最終等待，確保所有廣告都載入完成
            time.sleep(2)
            
            screenshot_paths = []
            total_replacements = 0
            # 重置已處理位置，為新網站開始
            self.processed_positions = set()
            
            # 檢查是否有可用的廣告尺寸
            if not hasattr(self, 'target_ad_sizes') or not self.target_ad_sizes:
                print("❌ 沒有找到任何替換圖片，無法進行廣告替換")
                return []
            
            # 處理每個目標廣告尺寸（根據實際載入的替換圖片）
            for target_size in self.target_ad_sizes:
                # 檢查是否已達到截圖數量限制
                if self.total_screenshots >= SCREENSHOT_COUNT:
                    print(f"📊 已達到截圖數量限制 ({SCREENSHOT_COUNT} 張)，停止處理")
                    break
                    
                try:
                    target_width = target_size['width']
                    target_height = target_size['height']
                    
                    print(f"\n尋找 {target_width}x{target_height} 的廣告...")
                    
                    # 獲取這個尺寸的所有可用圖片
                    size_key = f"{target_width}x{target_height}"
                    available_images = self.images_by_size.get(size_key, {'static': [], 'gif': []})
                    static_images = available_images['static']
                    gif_images = available_images['gif']
                    
                    print(f"🔍 檢查尺寸: {size_key}")
                    print(f"   可用圖片: {len(static_images)}張靜態 + {len(gif_images)}張GIF")
                    
                    if not static_images and not gif_images:
                        print(f"沒有找到 {target_width}x{target_height} 的替換圖片，繼續檢查下一個尺寸...")
                        continue
                    
                    # 根據配置策略選擇圖片
                    selected_image = self.select_image_by_strategy(static_images, gif_images, size_key)
                    
                    if not selected_image:
                        print(f"   ❌ 沒有可用的 {size_key} 圖片")
                        continue
                    
                    # 載入圖片數據
                    image_data = self.load_image_base64(selected_image['path'])
                    
                    # 使用新的即掃即換方法
                    replaced_count = self.scan_and_replace_ads_immediately(target_width, target_height, image_data, selected_image)
                    
                    if replaced_count > 0:
                        total_replacements += replaced_count
                        print(f"✅ 成功處理 {replaced_count} 個 {target_width}x{target_height} 的廣告")
                        # 注意：個別廣告截圖已在 scan_and_replace_ads_immediately 中完成
                    else:
                        print(f"未找到 {target_width}x{target_height} 的廣告")

                
                except Exception as e:
                    print(f"❌ 處理 {target_width}x{target_height} 廣告時發生錯誤: {e}")
                    continue  # 繼續處理下一個尺寸
            
            if total_replacements > 0:
                print(f"\n✅ 網站處理完成！總共替換了 {total_replacements} 個廣告")
            else:
                print(f"\n❌ 網站處理完成，但沒有成功替換任何廣告")
            
            return screenshot_paths
            
        except Exception as e:
            print(f"處理網站時發生錯誤: {e}")
            return []
    
    def restore_ad_content(self, element):
        """還原廣告內容 - ETtoday 風格"""
        try:
            success = self.driver.execute_script("""
                var container = arguments[0];
                if (!container) return false;
                
                console.log('開始 ETtoday 風格廣告還原');
                
                // 移除我們添加的按鈕
                var buttons = container.querySelectorAll('#close_button, #abgb, #info_button');
                buttons.forEach(function(button) {
                    button.remove();
                });
                
                // 移除我們添加的圖片（通過data URI識別）
                var addedImages = container.querySelectorAll('img[src^="data:image/jpeg;base64"], img[data-replacement-img="true"]');
                for (var i = 0; i < addedImages.length; i++) {
                    addedImages[i].remove();
                }
                
                // ETtoday 風格還原函數
                function restoreElement(el) {
                    if (el.tagName === 'IMG') {
                        // 恢復原始src
                        var originalSrc = el.getAttribute('data-original-src');
                        if (originalSrc) {
                            el.src = originalSrc;
                            el.removeAttribute('data-original-src');
                        }
                        // 恢復原始樣式
                        var originalStyle = el.getAttribute('data-original-style');
                        if (originalStyle !== null) {
                            el.style.cssText = originalStyle;
                            el.removeAttribute('data-original-style');
                        }
                    } else if (el.tagName === 'IFRAME') {
                        // 恢復iframe可見性
                        el.style.visibility = 'visible';
                    }
                    
                    // 恢復背景圖片
                    var originalBg = el.getAttribute('data-original-background');
                    if (originalBg) {
                        el.style.backgroundImage = originalBg;
                        el.removeAttribute('data-original-background');
                        
                        // 恢復背景樣式
                        var originalBgStyle = el.getAttribute('data-original-bg-style');
                        if (originalBgStyle) {
                            try {
                                var bgStyle = JSON.parse(originalBgStyle);
                                el.style.backgroundSize = bgStyle.size;
                                el.style.backgroundRepeat = bgStyle.repeat;
                                el.style.backgroundPosition = bgStyle.position;
                            } catch(e) {}
                            el.removeAttribute('data-original-bg-style');
                        }
                    }
                }
                
                // 復原主要元素
                restoreElement(container);
                
                // 復原容器內的所有圖片
                var imgs = container.querySelectorAll('img[data-original-src]');
                for (var i = 0; i < imgs.length; i++) {
                    restoreElement(imgs[i]);
                }
                
                // 復原容器內的所有iframe
                var iframes = container.querySelectorAll('iframe[style*="visibility: hidden"]');
                for (var i = 0; i < iframes.length; i++) {
                    restoreElement(iframes[i]);
                }
                
                console.log('✅ ETtoday 風格還原完成');
                
                console.log('廣告內容還原完成');
                return true;
            """, element)
            
            if success:
                print("✅ 廣告內容已還原")
                return True
            else:
                print("❌ ETtoday 風格還原失敗 - 廣告內容還原失敗")
                return False
                
        except Exception as e:
            print(f"還原廣告內容失敗: {e}")
            return False

    def close(self):
        """關閉瀏覽器"""
        try:
            self.driver.quit()
            print("瀏覽器已關閉")
        except:
            pass

def main():
    print("TVBS 食尚玩家廣告替換器 - 正式版")
    print("="*50)
    
    # 選擇螢幕
    screen_id, screen_info = ScreenManager.select_screen()
    if screen_id is None:
        return
    
    # 支援多種按鈕樣式: "dots", "cross", "adchoices", "adchoices_dots", "none"
    bot = TvbsAdReplacer(headless=False, screen_id=screen_id, button_style=BUTTON_STYLE)
    
    try:
        # 使用 TVBS 食尚玩家網站
        tvbs_url = "https://supertaste.tvbs.com.tw"
        print(f"目標網站: {tvbs_url}")
        
        # 尋找文章連結
        news_urls = bot.get_random_news_urls(tvbs_url, NEWS_COUNT)
        
        if not news_urls:
            print("無法獲取文章連結")
            return
        
        print(f"獲取到 {len(news_urls)} 個文章連結")
        print(f"目標截圖數量: {SCREENSHOT_COUNT}")
        
        # 處理每個網站
        for i, url in enumerate(news_urls):
            # 檢查是否已達到截圖數量限制
            if bot.total_screenshots >= SCREENSHOT_COUNT:
                print(f"\n📊 已達到截圖數量限制 ({SCREENSHOT_COUNT} 張)，停止處理新網站")
                break
                
            print(f"\n處理第 {i+1}/{len(news_urls)} 個網站")
            
            screenshot_paths = bot.process_website(url)
            
            if screenshot_paths:
                print(f"✅ 成功處理網站！共產生 {len(screenshot_paths)} 張截圖")
                
                # 檢查是否達到目標截圖數量
                if bot.total_screenshots >= SCREENSHOT_COUNT:
                    print(f"✅ 已達到目標截圖數量: {SCREENSHOT_COUNT}")
                    break
            else:
                print("❌ 網站處理失敗")
            
            # 在處理下一個網站前稍作休息
            if i < len(news_urls) and bot.total_screenshots < SCREENSHOT_COUNT:
                print("等待 3 秒後處理下一個網站...")
                time.sleep(3)
        
        print(f"\n{'='*60}")
        print(f"📊 TVBS 廣告替換統計報告")
        print(f"{'='*60}")
        print(f"📸 總截圖數量: {bot.total_screenshots} 張")
        print(f"🔄 總替換次數: {bot.total_replacements} 次")
        if bot.total_replacements > 0:
            gif_percentage = (bot.gif_replacements / bot.total_replacements) * 100
            static_percentage = (bot.static_replacements / bot.total_replacements) * 100
            print(f"   🎬 GIF 替換: {bot.gif_replacements} 次 ({gif_percentage:.1f}%)")
            print(f"   🖼️ 靜態圖片替換: {bot.static_replacements} 次 ({static_percentage:.1f}%)")
        
        if bot.replacement_details:
            print(f"\n📋 詳細替換記錄:")
            for i, detail in enumerate(bot.replacement_details, 1):
                type_icon = "🎬" if "GIF" in detail['type'] else "🖼️"
                print(f"    {i}. {type_icon} {detail['filename']} ({detail['size']}) → 📸 {detail['screenshot']}")
        
        # 顯示 GIF 使用策略
        try:
            from gif_config import GIF_PRIORITY
            print(f"\n⚙️ 當前 GIF 策略:")
            priority_text = "GIF 優先" if GIF_PRIORITY else "靜態圖片優先"
            print(f"   🎯 優先級模式 - {priority_text}")
        except:
            print(f"\n⚙️ 當前 GIF 策略: 預設模式")
        
        print(f"{'='*60}")
        
    except KeyboardInterrupt:
        print(f"\n{'='*50}")
        print(f"TVBS 廣告替換程式被使用者中斷！")
        print(f"已截圖: {bot.total_screenshots} 張")

        print(f"{'='*50}")
        
    finally:
        bot.close()

def process_single_website():
    """處理單個 TVBS 網站"""
    print("TVBS 食尚玩家廣告替換器 - 單網站模式")
    print("="*50)
    
    # 選擇螢幕
    screen_id, screen_info = ScreenManager.select_screen()
    if screen_id is None:
        return
    
    tvbs_bot = TvbsAdReplacer(headless=False, screen_id=screen_id, button_style=BUTTON_STYLE)
    
    try:
        # TVBS 網址
        tvbs_url = "https://supertaste.tvbs.com.tw"
        print(f"目標網站: {tvbs_url}")
        
        screenshot_paths = tvbs_bot.process_website(tvbs_url)
        
        if screenshot_paths:
            print(f"✅ 處理成功！產生 {len(screenshot_paths)} 張截圖")
            for path in screenshot_paths:
                print(f"  - {path}")
        else:
            print("❌ 處理失敗")
            
    finally:
        tvbs_bot.close()

if __name__ == "__main__":
    main()