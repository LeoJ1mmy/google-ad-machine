
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
    # 覆蓋 gif_config.py 中的 BASE_URL，設定 LTN 專用網址
    LTN_BASE_URL = "https://playing.ltn.com.tw"
except ImportError:
    print("找不到 gif_config.py，使用預設設定")
    # 預設設定
    SCREENSHOT_COUNT = 10
    MAX_ATTEMPTS = 50
    PAGE_LOAD_TIMEOUT = 15
    WAIT_TIME = 3
    REPLACE_IMAGE_FOLDER = "replace_image"
    DEFAULT_IMAGE = "mini.jpg"
    MINI_IMAGE = "mini.jpg"
    LTN_BASE_URL = "https://playing.ltn.com.tw"
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
    BUTTON_STYLE = "dots"  # 預設按鈕樣式
    ENABLE_DYNAMIC_AD_CHECK = True  # 是否啟用動態廣告檢測
    DYNAMIC_CHECK_TIMEOUT = 1  # 動態檢測等待時間（秒）
    PROCESS_DYNAMIC_ADS = False  # 是否處理動態廣告（False=跳過動態廣告）
    MAX_STABILITY_RETRIES = 3  # 每個位置最大重試次數
    STABILITY_WAIT_TIME = 2  # 等待廣告穩定的時間（秒）

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

class GoogleAdReplacer:
    def __init__(self, headless=False, screen_id=1):
        self.screen_id = screen_id
        self.enable_dynamic_check = ENABLE_DYNAMIC_AD_CHECK
        self.dynamic_check_timeout = DYNAMIC_CHECK_TIMEOUT
        self.process_dynamic_ads = PROCESS_DYNAMIC_ADS
        self.max_stability_retries = MAX_STABILITY_RETRIES
        self.stability_wait_time = STABILITY_WAIT_TIME
        self.position_retry_count = {}  # 記錄每個位置的重試次數
        self.setup_driver(headless)
        self.load_replace_images()
        
    def setup_driver(self, headless):
        chrome_options = Options()
        if headless or HEADLESS_MODE:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-certificate-errors-spki-list')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        
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
        """載入替換圖片並解析尺寸 - GIF 升級版"""
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
        
        # 顯示載入的圖片清單
        print(f"\n📋 完整圖片清單:")
        for i, img in enumerate(self.replace_images):
            type_icon = "🎬" if img['is_gif'] else "🖼️"
            print(f"  {i+1}. {type_icon} {img['filename']} ({img['width']}x{img['height']})")
    

    
    def select_image_by_strategy(self, static_images, gif_images, size_key):
        """根據 GIF_PRIORITY 配置選擇圖片 - LTN 精確尺寸匹配版"""
        
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
        
        # LTN 精確尺寸匹配：優先級模式
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
    
    def get_random_news_urls(self, base_url, count=5):
        try:
            self.driver.get(base_url)
            time.sleep(WAIT_TIME)
            
            link_selectors = [
                "a[href*='/article/']"
            ]
            
            news_urls = []
            
            for selector in link_selectors:
                links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for link in links:
                    href = link.get_attribute('href')
                    if href and href not in news_urls and 'ltn.com.tw' in href:
                        news_urls.append(href)
                        
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
        
        # 去除重複位置的廣告元素
        unique_elements = []
        seen_positions = set()
        
        for element_info in matching_elements:
            position_key = f"{element_info['position']}"
            if position_key not in seen_positions:
                unique_elements.append(element_info)
                seen_positions.add(position_key)
            else:
                print(f"🔄 跳過重複位置: {element_info['position']}")
        
        if len(unique_elements) != len(matching_elements):
            print(f"📍 位置去重: {len(matching_elements)} → {len(unique_elements)} 個廣告位置")
        
        return unique_elements
    
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
                    "style": 'position:absolute;top:-1px;right:0px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);border-radius:2px;cursor:pointer;'
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

    def save_complete_ad_state(self, element):
        """在任何操作前保存完整的廣告狀態"""
        try:
            saved_state = self.driver.execute_script("""
                var element = arguments[0];
                if (!element) return null;
                
                return {
                    outerHTML: element.outerHTML,
                    innerHTML: element.innerHTML,
                    cssSelector: arguments[1],
                    xpath: arguments[2],
                    attributes: Array.from(element.attributes).reduce((attrs, attr) => {
                        attrs[attr.name] = attr.value;
                        return attrs;
                    }, {}),
                    computedStyle: window.getComputedStyle(element).cssText,
                    parentHTML: element.parentElement ? element.parentElement.outerHTML : null
                };
            """, element, self.generate_css_selector(element), self.generate_xpath(element))
            
            return saved_state
        except Exception as e:
            print(f"保存廣告狀態失敗: {e}")
            return None

    def generate_css_selector(self, element):
        """生成元素的 CSS 選擇器"""
        try:
            return self.driver.execute_script("""
                function getSelector(element) {
                    if (element.id) {
                        return '#' + element.id;
                    }
                    
                    var path = [];
                    while (element && element.nodeType === Node.ELEMENT_NODE) {
                        var selector = element.nodeName.toLowerCase();
                        if (element.className) {
                            selector += '.' + element.className.replace(/\\s+/g, '.');
                        }
                        path.unshift(selector);
                        element = element.parentElement;
                    }
                    return path.join(' > ');
                }
                return getSelector(arguments[0]);
            """, element)
        except Exception as e:
            print(f"生成 CSS 選擇器失敗: {e}")
            return None

    def generate_xpath(self, element):
        """生成元素的 XPath"""
        try:
            return self.driver.execute_script("""
                function getXPath(element) {
                    if (element.id) {
                        return '//*[@id="' + element.id + '"]';
                    }
                    
                    var path = [];
                    while (element && element.nodeType === Node.ELEMENT_NODE) {
                        var index = 0;
                        var siblings = element.parentNode.childNodes;
                        for (var i = 0; i < siblings.length; i++) {
                            var sibling = siblings[i];
                            if (sibling.nodeType === Node.ELEMENT_NODE && sibling.nodeName === element.nodeName) {
                                index++;
                            }
                            if (sibling === element) {
                                break;
                            }
                        }
                        var tagName = element.nodeName.toLowerCase();
                        path.unshift(tagName + '[' + index + ']');
                        element = element.parentElement;
                    }
                    return '/' + path.join('/');
                }
                return getXPath(arguments[0]);
            """, element)
        except Exception as e:
            print(f"生成 XPath 失敗: {e}")
            return None

    def restore_from_saved_state(self, saved_state):
        """使用保存的狀態還原廣告"""
        try:
            if not saved_state:
                return False
                
            # 嘗試使用 CSS 選擇器找到元素
            element = None
            if saved_state.get('cssSelector'):
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, saved_state['cssSelector'])
                except:
                    pass
            
            # 如果 CSS 選擇器失敗，嘗試 XPath
            if not element and saved_state.get('xpath'):
                try:
                    element = self.driver.find_element(By.XPATH, saved_state['xpath'])
                except:
                    pass
            
            if element:
                # 還原元素內容
                self.driver.execute_script("""
                    var element = arguments[0];
                    var savedState = arguments[1];
                    
                    // 還原 innerHTML
                    element.innerHTML = savedState.innerHTML;
                    
                    // 還原屬性
                    for (var attr in savedState.attributes) {
                        element.setAttribute(attr, savedState.attributes[attr]);
                    }
                """, element, saved_state)
                
                print("✅ 從保存狀態成功還原廣告")
                return True
            else:
                print("⚠️ 無法找到要還原的元素")
                return False
                
        except Exception as e:
            print(f"從保存狀態還原失敗: {e}")
            return False

    def disable_sticky_behavior(self):
        """暫時禁用網站的 sticky 廣告行為"""
        disable_script = """
            // 保存原始樣式
            window.originalStyles = window.originalStyles || new Map();
            
            // 禁用所有 sticky 和 fixed 定位
            var elements = document.querySelectorAll('*');
            elements.forEach(function(el) {
                var style = window.getComputedStyle(el);
                if (style.position === 'sticky' || style.position === 'fixed') {
                    if (!window.originalStyles.has(el)) {
                        window.originalStyles.set(el, {
                            position: style.position,
                            top: style.top,
                            bottom: style.bottom,
                            left: style.left,
                            right: style.right,
                            zIndex: style.zIndex
                        });
                    }
                    el.style.position = 'static';
                }
            });
            
            // 暫停可能導致 DOM 變化的事件（簡化版本，避免使用 getEventListeners）
            window.pausedEvents = [];
            
            // 暫停滾動事件的簡單方法
            window.originalOnScroll = window.onscroll;
            window.onscroll = null;
            
            // 暫停 resize 事件
            window.originalOnResize = window.onresize;
            window.onresize = null;
            
            console.log('已禁用 sticky 行為');
        """
        
        try:
            self.driver.execute_script(disable_script)
            print("🛡️ 已禁用 sticky 廣告行為")
            return True
        except Exception as e:
            print(f"禁用 sticky 行為失敗: {e}")
            return False

    def enable_sticky_behavior(self):
        """重新啟用 sticky 行為"""
        enable_script = """
            // 還原原始樣式
            if (window.originalStyles) {
                window.originalStyles.forEach(function(originalStyle, element) {
                    element.style.position = originalStyle.position;
                    element.style.top = originalStyle.top;
                    element.style.bottom = originalStyle.bottom;
                    element.style.left = originalStyle.left;
                    element.style.right = originalStyle.right;
                    element.style.zIndex = originalStyle.zIndex;
                });
                window.originalStyles.clear();
            }
            
            // 重新啟用事件監聽器
            if (window.originalOnScroll !== undefined) {
                window.onscroll = window.originalOnScroll;
                window.originalOnScroll = undefined;
            }
            
            if (window.originalOnResize !== undefined) {
                window.onresize = window.originalOnResize;
                window.originalOnResize = undefined;
            }
            
            console.log('已重新啟用 sticky 行為');
        """
        
        try:
            self.driver.execute_script(enable_script)
            print("🛡️ 已重新啟用 sticky 行為")
            return True
        except Exception as e:
            print(f"重新啟用 sticky 行為失敗: {e}")
            return False

    def safe_ad_replacement(self, element, image_data, target_width, target_height):
        """安全的廣告替換，確保可以還原"""
        
        print("🛡️ 開始安全廣告替換流程...")
        
        # 1. 禁用 sticky 行為
        self.disable_sticky_behavior()
        time.sleep(0.5)
        
        # 2. 保存完整狀態
        saved_state = self.save_complete_ad_state(element)
        if not saved_state:
            print("⚠️ 無法保存廣告狀態，跳過此廣告")
            self.enable_sticky_behavior()
            return None
        
        try:
            # 3. 替換廣告
            success = self.replace_ad_content(element, image_data, target_width, target_height)
            
            if success:
                print("✅ 廣告替換成功，準備截圖...")
                
                # 4. 滾動並截圖
                self.scroll_to_element(element)
                screenshot_path = self.take_screenshot()
                print(f"📸 截圖完成: {screenshot_path}")
                
                # 5. 還原廣告
                restore_success = self.restore_ad_content(element)
                if not restore_success:
                    print("⚠️ 常規還原失敗，嘗試從保存狀態還原...")
                    self.restore_from_saved_state(saved_state)
                
                return screenshot_path
            else:
                print("❌ 廣告替換失敗")
                return None
                
        except Exception as e:
            print(f"廣告替換過程出錯: {e}")
            # 緊急還原
            if saved_state:
                print("🚨 執行緊急還原...")
                self.restore_from_saved_state(saved_state)
            return None
        
        finally:
            # 6. 重新啟用 sticky 行為
            self.enable_sticky_behavior()
            print("🛡️ 安全廣告替換流程完成")

    def scroll_to_element(self, element):
        """滾動到元素位置"""
        try:
            # 獲取元素位置並滾動
            element_location = element.location
            scroll_y = max(0, element_location['y'] - 200)  # 留一些邊距
            
            self.driver.execute_script(f"window.scrollTo(0, {scroll_y});")
            time.sleep(1)  # 等待滾動完成
            print(f"✅ 已滾動到元素位置: {scroll_y}px")
            
        except Exception as e:
            print(f"滾動到元素失敗: {e}")

    def restore_ad_content(self, element):
        """還原廣告內容 - 完全清除所有替換內容"""
        try:
            success = self.driver.execute_script("""
                var container = arguments[0];
                if (!container) return false;
                
                console.log('開始完全還原廣告內容');
                
                // 1. 移除我們添加的按鈕
                ['close_button', 'abgb'].forEach(function(id){
                    var btn = document.querySelector('#'+id);  // 全域搜尋
                    if (btn) {
                        btn.remove();
                        console.log('移除按鈕: ' + id);
                    }
                    // 也在容器內搜尋
                    var containerBtn = container.querySelector('#'+id);
                    if (containerBtn) {
                        containerBtn.remove();
                        console.log('移除容器內按鈕: ' + id);
                    }
                });
                
                // 2. 移除所有我們添加的替換圖片（全域搜尋）
                var allReplacementImgs = document.querySelectorAll('img[data-replacement-img="true"]');
                allReplacementImgs.forEach(function(img) {
                    img.remove();
                    console.log('移除全域替換圖片');
                });
                
                // 3. 移除容器內的替換圖片
                var replacementImgs = container.querySelectorAll('img[data-replacement-img="true"]');
                replacementImgs.forEach(function(img) {
                    img.remove();
                    console.log('移除容器內替換圖片');
                });
                
                // 4. 移除所有 base64 圖片（我們的替換圖片）- 全域搜尋
                var allBase64Imgs = document.querySelectorAll('img[src^="data:image/jpeg;base64"]');
                allBase64Imgs.forEach(function(img) {
                    img.remove();
                    console.log('移除全域 base64 圖片');
                });
                
                // 5. 移除容器內的 base64 圖片
                var base64Imgs = container.querySelectorAll('img[src^="data:image/jpeg;base64"]');
                base64Imgs.forEach(function(img) {
                    img.remove();
                    console.log('移除容器內 base64 圖片');
                });
                
                // 6. 還原 ins 元素的原始內容
                var originalContent = container.getAttribute('data-original-content');
                if (originalContent) {
                    container.innerHTML = originalContent;
                    container.removeAttribute('data-original-content');
                    console.log('已還原 ins 元素內容');
                }
                
                // 7. 還原圖片的原始 src 和樣式
                var imgs = container.querySelectorAll('img[data-original-src]');
                imgs.forEach(function(img) {
                    img.src = img.getAttribute('data-original-src');
                    img.removeAttribute('data-original-src');
                    img.removeAttribute('data-replacement-img');
                    
                    // 還原原始樣式
                    var originalStyle = img.getAttribute('data-original-style');
                    if (originalStyle) {
                        img.style.cssText = originalStyle;
                        img.removeAttribute('data-original-style');
                    }
                    console.log('已還原圖片 src 和樣式');
                });
                
                // 8. 還原 iframe 的可見性
                var iframes = container.querySelectorAll('iframe[data-was-hidden]');
                iframes.forEach(function(iframe) {
                    iframe.style.visibility = 'visible';
                    iframe.removeAttribute('data-was-hidden');
                    console.log('已還原 iframe 可見性');
                });
                
                // 9. 完全清除容器的背景樣式（只清除我們替換的）
                if (container.getAttribute('data-replacement-bg')) {
                    container.style.backgroundImage = '';
                    container.style.backgroundSize = '';
                    container.style.backgroundRepeat = '';
                    container.style.backgroundPosition = '';
                    container.style.background = '';
                    container.removeAttribute('data-replacement-bg');
                    console.log('已清除替換的背景圖片');
                }
                
                // 10. 移除我們可能添加的其他樣式
                container.style.position = '';
                container.style.overflow = '';
                
                // 11. 清除所有子元素的替換標記
                var allElements = container.querySelectorAll('*');
                allElements.forEach(function(el) {
                    el.removeAttribute('data-replacement-img');
                    el.removeAttribute('data-original-src');
                    el.removeAttribute('data-original-style');
                    el.removeAttribute('data-was-hidden');
                    el.removeAttribute('data-replacement-bg');
                });
                
                // 12. 移除全域的 Google 廣告樣式
                var googleAdStyles = document.getElementById('google_ad_styles');
                if (googleAdStyles) {
                    googleAdStyles.remove();
                    console.log('移除 Google 廣告樣式');
                }
                
                console.log('廣告內容完全還原完成');
                return true;
            """, element)
            
            if success:
                print("✅ 廣告內容已完全還原")
                return True
            else:
                print("⚠️ 廣告內容還原可能不完整")
                return False
                
        except Exception as e:
            print(f"還原廣告內容失敗: {e}")
            return False

    def replace_ad_content(self, element, image_data, target_width, target_height):
        try:
            # 多次檢查尺寸，確保廣告沒有在輪播過程中改變
            for attempt in range(3):
                # 獲取當前尺寸
                current_info = self.driver.execute_script("""
                    var element = arguments[0];
                    if (!element || !element.getBoundingClientRect) return null;
                    var rect = element.getBoundingClientRect();
                    return {
                        width: rect.width, 
                        height: rect.height,
                        innerHTML: element.innerHTML.substring(0, 100),  // 取前100字符作為內容指紋
                        timestamp: Date.now()
                    };
                """, element)
                
                if not current_info:
                    return False
                
                # 檢查是否符合目標尺寸（允許 5 像素的誤差）
                width_diff = abs(current_info['width'] - target_width)
                height_diff = abs(current_info['height'] - target_height)
                
                if width_diff > 5 or height_diff > 5:
                    print(f"🔄 嘗試 {attempt + 1}/3: 尺寸不符合 - 實際 {current_info['width']}x{current_info['height']}, 目標 {target_width}x{target_height}")
                    if attempt < 2:  # 不是最後一次嘗試
                        time.sleep(1)  # 等待1秒讓廣告輪播
                        continue
                    else:
                        print(f"❌ 廣告尺寸持續不符合，可能正在輪播中，跳過此廣告")
                        return False
                
                # 尺寸符合，再等待0.5秒確保廣告穩定
                time.sleep(0.5)
                
                # 再次檢查確保廣告沒有改變
                verify_info = self.driver.execute_script("""
                    var element = arguments[0];
                    if (!element || !element.getBoundingClientRect) return null;
                    var rect = element.getBoundingClientRect();
                    return {
                        width: rect.width, 
                        height: rect.height,
                        innerHTML: element.innerHTML.substring(0, 100)
                    };
                """, element)
                
                if (verify_info and 
                    abs(verify_info['width'] - current_info['width']) <= 2 and
                    abs(verify_info['height'] - current_info['height']) <= 2 and
                    verify_info['innerHTML'] == current_info['innerHTML']):
                    
                    print(f"✅ 廣告穩定，尺寸符合: {verify_info['width']}x{verify_info['height']}")
                    original_info = verify_info
                    break
                else:
                    print(f"⚠️ 廣告在驗證期間發生變化，重新嘗試...")
                    if attempt < 2:
                        time.sleep(1)
                        continue
                    else:
                        print(f"❌ 廣告持續變化中，跳過此廣告")
                        return False
            else:
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
                        var isControlButton = (imgRect.width < 30 || imgRect.height < 30) && 
                                             (img.className.includes('abg') || 
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
                                             (img.alt && (img.alt.includes('關閉') || img.alt.includes('close'))));
                        
                        if (!isControlButton && img.src && !img.src.startsWith('data:')) {
                            // 保存原始src以便復原
                            if (!img.getAttribute('data-original-src')) {
                                img.setAttribute('data-original-src', img.src);
                            }
                            // 保存原始樣式
                            if (!img.getAttribute('data-original-style')) {
                                img.setAttribute('data-original-style', img.style.cssText);
                            }
                            
                            // 替換圖片，保持目標尺寸
                            img.src = newImageSrc;
                            img.setAttribute('data-replacement-img', 'true');  // 標記為替換圖片
                            img.style.objectFit = 'cover';
                            img.style.width = targetWidth + 'px';
                            img.style.height = targetHeight + 'px';
                            img.style.maxWidth = targetWidth + 'px';
                            img.style.maxHeight = targetHeight + 'px';
                            img.style.minWidth = targetWidth + 'px';
                            img.style.minHeight = targetHeight + 'px';
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
                    newImg.setAttribute('data-replacement-img', 'true');  // 標記為替換圖片
                    newImg.style.position = 'absolute';
                    newImg.style.top = (iframeRect.top - container.getBoundingClientRect().top) + 'px';
                    newImg.style.left = (iframeRect.left - container.getBoundingClientRect().left) + 'px';
                    newImg.style.width = targetWidth + 'px';
                    newImg.style.height = targetHeight + 'px';
                    newImg.style.objectFit = 'cover';
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
                        container.setAttribute('data-replacement-bg', 'true');  // 標記背景已替換
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
                # 驗證替換是否真的成功
                time.sleep(0.3)  # 等待DOM更新
                verification_result = self.driver.execute_script("""
                    var element = arguments[0];
                    var targetImageData = arguments[1];
                    
                    // 檢查是否有我們的替換圖片
                    var imgs = element.querySelectorAll('img');
                    var hasOurImage = false;
                    
                    for (var i = 0; i < imgs.length; i++) {
                        var img = imgs[i];
                        if (img.src && img.src.includes('data:image/png;base64,')) {
                            var base64Part = img.src.split('data:image/png;base64,')[1];
                            if (base64Part && base64Part.substring(0, 50) === targetImageData.substring(0, 50)) {
                                hasOurImage = true;
                                break;
                            }
                        }
                    }
                    
                    // 檢查背景圖片
                    var hasBgImage = false;
                    if (element.getAttribute('data-replacement-bg') === 'true') {
                        var bgImage = window.getComputedStyle(element).backgroundImage;
                        if (bgImage && bgImage.includes('data:image/png;base64,')) {
                            hasBgImage = true;
                        }
                    }
                    
                    return {
                        hasImage: hasOurImage,
                        hasBackground: hasBgImage,
                        success: hasOurImage || hasBgImage
                    };
                """, element, image_data)
                
                if verification_result and verification_result['success']:
                    print(f"✅ 替換廣告成功並驗證 {original_info['width']}x{original_info['height']}")
                    return True
                else:
                    print(f"❌ 替換廣告失敗 - 驗證未通過 {original_info['width']}x{original_info['height']}")
                    return False
            else:
                print(f"❌ 廣告替換失敗 {original_info['width']}x{original_info['height']}")
                return False
                
        except Exception as e:
            print(f"替換廣告失敗: {e}")
            return False
    
    def process_website(self, url):
        """處理單個網站，遍歷所有替換圖片 - 新的穩定性檢測策略"""
        try:
            print(f"\n開始處理網站: {url}")
            
            # 重置重試計數器（每個新網站重新開始）
            self.position_retry_count.clear()
            print("🔄 已重置位置重試計數器")
            
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
                
                print(f"🎯 找到 {len(matching_elements)} 個廣告位置，開始穩定性檢測...")
                
                # 新策略：不管動態還是靜態，都先記錄位置，然後逐個檢測穩定性
                replaced = False
                processed_positions = set()  # 記錄已處理的位置
                
                for ad_info in matching_elements:
                    position_key = f"{ad_info['position']}_{image_info['width']}x{image_info['height']}"
                    
                    # 檢查是否已經處理過這個位置
                    if position_key in processed_positions:
                        print(f"跳過已處理的位置: {ad_info['position']}")
                        continue
                    
                    # 檢查重試次數
                    if position_key not in self.position_retry_count:
                        self.position_retry_count[position_key] = 0
                    
                    if self.position_retry_count[position_key] >= self.max_stability_retries:
                        print(f"⚠️ 位置 {ad_info['position']} 已達到最大重試次數 ({self.max_stability_retries})，跳過")
                        continue
                    
                    # 對每個位置進行穩定性檢測
                    print(f"🔍 檢測位置 {ad_info['position']} 的穩定性 (嘗試 {self.position_retry_count[position_key] + 1}/{self.max_stability_retries})")
                    
                    # 等待廣告穩定
                    is_stable = self.wait_for_ad_stability(ad_info['element'], image_info['width'], image_info['height'])
                    
                    if is_stable:
                        print(f"✅ 廣告位置 {ad_info['position']} 已穩定，開始替換")
                        try:
                            # 使用安全替換策略處理廣告
                            screenshot_path = self.safe_ad_replacement(ad_info['element'], image_data, image_info['width'], image_info['height'])
                            if screenshot_path:
                                print(f"✅ 成功替換廣告: {ad_info['width']}x{ad_info['height']} at {ad_info['position']}")
                                replaced = True
                                total_replacements += 1
                                processed_positions.add(position_key)  # 記錄已處理的位置
                                screenshot_paths.append(screenshot_path)  # 添加截圖路徑
                                
                                # 重置重試計數器（成功後）
                                self.position_retry_count[position_key] = 0
                                continue
                            else:
                                print(f"❌ 替換廣告失敗: {ad_info['position']}")
                                self.position_retry_count[position_key] += 1
                        except Exception as e:
                            print(f"❌ 替換廣告異常: {e}")
                            self.position_retry_count[position_key] += 1
                    else:
                        print(f"⚠️ 廣告位置 {ad_info['position']} 不穩定，增加重試計數")
                        self.position_retry_count[position_key] += 1
                
                if not replaced:
                    print(f"所有找到的 {image_info['width']}x{image_info['height']} 廣告位置都無法替換")
            
            # 總結處理結果
            if total_replacements > 0:
                print(f"\n{'='*50}")
                print(f"網站處理完成！總共成功替換了 {total_replacements} 個廣告")
                print(f"截圖檔案:")
                for i, path in enumerate(screenshot_paths, 1):
                    print(f"  {i}. {path}")
                
                # 顯示重試統計
                if self.position_retry_count:
                    print(f"\n📊 位置重試統計:")
                    for position_key, retry_count in self.position_retry_count.items():
                        if retry_count > 0:
                            status = "已跳過" if retry_count >= self.max_stability_retries else "重試中"
                            print(f"  {position_key}: {retry_count}/{self.max_stability_retries} 次重試 ({status})")
                
                print(f"{'='*50}")
                return screenshot_paths
            else:
                print("本網頁沒有找到任何可替換的廣告")
                
                # 即使沒有成功替換，也顯示重試統計
                if self.position_retry_count:
                    print(f"\n📊 位置重試統計:")
                    for position_key, retry_count in self.position_retry_count.items():
                        if retry_count > 0:
                            status = "已跳過" if retry_count >= self.max_stability_retries else "重試中"
                            print(f"  {position_key}: {retry_count}/{self.max_stability_retries} 次重試 ({status})")
                
                return []
                
        except Exception as e:
            print(f"處理網站失敗: {e}")
            return []
    
    def wait_for_ad_stability(self, element, target_width, target_height):
        """等待廣告穩定 - 新的穩定性檢測策略"""
        try:
            print(f"⏳ 等待廣告穩定 ({self.stability_wait_time}秒)...")
            
            # 獲取初始狀態
            initial_state = self.driver.execute_script("""
                var element = arguments[0];
                if (!element || !element.getBoundingClientRect) return null;
                
                var rect = element.getBoundingClientRect();
                var imgs = element.querySelectorAll('img');
                var imgSrcs = Array.from(imgs).map(img => img.src).join('|');
                
                return {
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    top: Math.round(rect.top),
                    left: Math.round(rect.left),
                    innerHTML: element.innerHTML.substring(0, 200),  // 取前200字符作為內容指紋
                    imgSrcs: imgSrcs,
                    imgCount: imgs.length,
                    timestamp: Date.now()
                };
            """, element)
            
            if not initial_state:
                print("❌ 無法獲取廣告初始狀態")
                return False
            
            print(f"📊 初始狀態: {initial_state['width']}x{initial_state['height']} at ({initial_state['left']}, {initial_state['top']})")
            
            # 等待指定時間
            time.sleep(self.stability_wait_time)
            
            # 獲取最終狀態
            final_state = self.driver.execute_script("""
                var element = arguments[0];
                if (!element || !element.getBoundingClientRect) return null;
                
                var rect = element.getBoundingClientRect();
                var imgs = element.querySelectorAll('img');
                var imgSrcs = Array.from(imgs).map(img => img.src).join('|');
                
                return {
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    top: Math.round(rect.top),
                    left: Math.round(rect.left),
                    innerHTML: element.innerHTML.substring(0, 200),
                    imgSrcs: imgSrcs,
                    imgCount: imgs.length,
                    timestamp: Date.now()
                };
            """, element)
            
            if not final_state:
                print("❌ 無法獲取廣告最終狀態")
                return False
            
            print(f"📊 最終狀態: {final_state['width']}x{final_state['height']} at ({final_state['left']}, {final_state['top']})")
            
            # 檢查各種變化
            size_changed = (abs(initial_state['width'] - final_state['width']) > 5 or 
                           abs(initial_state['height'] - final_state['height']) > 5)
            
            position_changed = (abs(initial_state['top'] - final_state['top']) > 5 or
                               abs(initial_state['left'] - final_state['left']) > 5)
            
            content_changed = initial_state['innerHTML'] != final_state['innerHTML']
            
            img_changed = (initial_state['imgSrcs'] != final_state['imgSrcs'] or
                          initial_state['imgCount'] != final_state['imgCount'])
            
            # 檢查尺寸是否符合目標
            size_matches = (abs(final_state['width'] - target_width) <= 5 and
                           abs(final_state['height'] - target_height) <= 5)
            
            # 判斷是否穩定
            is_stable = not (size_changed or position_changed or content_changed or img_changed) and size_matches
            
            if is_stable:
                print(f"✅ 廣告穩定: 尺寸={final_state['width']}x{final_state['height']}, 符合目標={size_matches}")
                return True
            else:
                change_reasons = []
                if size_changed:
                    change_reasons.append("尺寸變化")
                if position_changed:
                    change_reasons.append("位置變化")
                if content_changed:
                    change_reasons.append("內容變化")
                if img_changed:
                    change_reasons.append("圖片變化")
                if not size_matches:
                    change_reasons.append("尺寸不符")
                
                print(f"⚠️ 廣告不穩定: {', '.join(change_reasons)}")
                return False
                
        except Exception as e:
            print(f"⚠️ 穩定性檢測失敗: {e}")
            return False

    def is_likely_dynamic_ad(self, element):
        """快速檢查元素是否可能是動態廣告（不等待）"""
        try:
            return self.driver.execute_script("""
                var element = arguments[0];
                var html = element.innerHTML.toLowerCase();
                var outerHTML = element.outerHTML.toLowerCase();
                var id = element.id ? element.id.toLowerCase() : '';
                var className = element.className ? element.className.toLowerCase() : '';
                var allText = html + ' ' + outerHTML + ' ' + id + ' ' + className;
                
                var dynamicMarkers = [
                    'adpushup', 'rotation', 'carousel', 'slider', 'rotate',
                    'data-timeout', 'data-interval', 'auto-refresh',
                    'ad-rotation', 'banner-rotation', 'data-refresh',
                    'refresh-ad', 'ad-refresh', 'timer', 'countdown'
                ];
                
                for (var i = 0; i < dynamicMarkers.length; i++) {
                    if (allText.includes(dynamicMarkers[i])) {
                        return true;
                    }
                }
                return false;
            """, element)
        except:
            return False
    
    def fast_dynamic_ad_replacement(self, element, image_data, target_width, target_height):
        """快速動態廣告替換策略 - 立即替換並鎖定"""
        try:
            print("🚀 執行快速動態廣告替換...")
            
            # 1. 立即停止廣告輪播
            self.stop_ad_rotation(element)
            
            # 2. 快速尺寸檢查（不等待）
            current_info = self.driver.execute_script("""
                var element = arguments[0];
                if (!element || !element.getBoundingClientRect) return null;
                var rect = element.getBoundingClientRect();
                return {width: rect.width, height: rect.height};
            """, element)
            
            if not current_info:
                print("❌ 無法獲取廣告尺寸")
                return None
            
            # 檢查尺寸是否符合（允許更大的誤差，因為動態廣告可能在變化中）
            width_diff = abs(current_info['width'] - target_width)
            height_diff = abs(current_info['height'] - target_height)
            
            if width_diff > 10 or height_diff > 10:
                print(f"⚠️ 動態廣告尺寸差異較大: 實際 {current_info['width']}x{current_info['height']}, 目標 {target_width}x{target_height}")
                # 對於動態廣告，我們仍然嘗試替換
            
            print(f"🎯 動態廣告尺寸: {current_info['width']}x{current_info['height']}")
            
            # 3. 禁用 sticky 行為
            self.disable_sticky_behavior()
            
            # 4. 立即替換廣告內容
            success = self.replace_ad_content_fast(element, image_data, target_width, target_height)
            
            if success:
                print("✅ 動態廣告替換成功，準備截圖...")
                
                # 5. 滾動並截圖
                self.scroll_to_element(element)
                screenshot_path = self.take_screenshot()
                print(f"📸 截圖完成: {screenshot_path}")
                
                # 6. 保持替換狀態（不還原，因為動態廣告可能會自動還原）
                print("🔒 保持動態廣告替換狀態")
                
                return screenshot_path
            else:
                print("❌ 動態廣告替換失敗")
                return None
                
        except Exception as e:
            print(f"動態廣告替換過程出錯: {e}")
            return None
        
        finally:
            # 重新啟用 sticky 行為
            self.enable_sticky_behavior()
            print("🚀 快速動態廣告替換完成")
    
    def stop_ad_rotation(self, element):
        """停止廣告輪播"""
        try:
            self.driver.execute_script("""
                var element = arguments[0];
                
                // 停止所有可能的定時器
                var highestTimeoutId = setTimeout(";");
                for (var i = 0; i < highestTimeoutId; i++) {
                    clearTimeout(i);
                }
                
                var highestIntervalId = setInterval(";");
                for (var i = 0; i < highestIntervalId; i++) {
                    clearInterval(i);
                }
                
                // 停止 adpushup 相關的輪播
                if (window.adpushup && window.adpushup.que) {
                    window.adpushup.que = [];
                }
                
                // 移除可能的輪播事件監聽器
                if (element) {
                    element.style.pointerEvents = 'none';
                    
                    // 標記為已停止輪播
                    element.setAttribute('data-rotation-stopped', 'true');
                }
                
                console.log('廣告輪播已停止');
            """, element)
            print("⏸️ 已停止廣告輪播")
        except Exception as e:
            print(f"停止廣告輪播失敗: {e}")
    
    def replace_ad_content_fast(self, element, image_data, target_width, target_height):
        """快速替換廣告內容（簡化版本，專為動態廣告設計）"""
        try:
            # 獲取按鈕樣式
            button_style = self.get_button_style()
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
            
            # 快速替換策略：直接覆蓋整個容器內容
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
                
                var newImageSrc = 'data:image/png;base64,' + imageBase64;
                
                // 強制替換整個容器內容
                container.innerHTML = '';
                container.style.position = 'relative';
                container.style.overflow = 'hidden';
                container.style.width = targetWidth + 'px';
                container.style.height = targetHeight + 'px';
                
                // 創建新的圖片元素
                var newImg = document.createElement('img');
                newImg.src = newImageSrc;
                newImg.style.width = '100%';
                newImg.style.height = '100%';
                newImg.style.objectFit = 'contain';
                newImg.style.display = 'block';
                newImg.setAttribute('data-fast-replacement', 'true');
                
                container.appendChild(newImg);
                
                // 添加按鈕（如果不是 none 模式）
                if (!isNoneMode && closeButtonHtml && infoButtonHtml) {
                    container.insertAdjacentHTML('beforeend', closeButtonHtml);
                    container.insertAdjacentHTML('beforeend', infoButtonHtml);
                }
                
                // 防止進一步的動態變化
                container.setAttribute('data-dynamic-locked', 'true');
                container.style.pointerEvents = 'auto';
                
                console.log('快速動態廣告替換完成');
                return true;
                
            """, element, image_data, target_width, target_height, close_button_html, close_button_style, info_button_html, info_button_style, is_none_mode)
            
            if success:
                print(f"✅ 快速替換動態廣告成功")
                return True
            else:
                print(f"❌ 快速替換動態廣告失敗")
                return False
                
        except Exception as e:
            print(f"快速替換廣告內容失敗: {e}")
            return False
    
    def classify_ads(self, matching_elements, target_width, target_height):
        """將廣告分類為穩定廣告和動態廣告"""
        if not matching_elements:
            return [], []
        
        print(f"🔍 分析廣告類型 ({len(matching_elements)} 個)...")
        stable_elements = []
        dynamic_elements = []
        
        for i, ad_info in enumerate(matching_elements):
            element = ad_info['element']
            
            try:
                # 快速檢查是否包含動態廣告標識（不等待）
                has_dynamic_markers = self.driver.execute_script("""
                    var element = arguments[0];
                    var html = element.innerHTML.toLowerCase();
                    var outerHTML = element.outerHTML.toLowerCase();
                    var id = element.id ? element.id.toLowerCase() : '';
                    var className = element.className ? element.className.toLowerCase() : '';
                    var allText = html + ' ' + outerHTML + ' ' + id + ' ' + className;
                    
                    var dynamicMarkers = [
                        'adpushup', 'rotation', 'carousel', 'slider', 'rotate',
                        'data-timeout', 'data-interval', 'auto-refresh',
                        'ad-rotation', 'banner-rotation', 'data-refresh'
                    ];
                    
                    for (var i = 0; i < dynamicMarkers.length; i++) {
                        if (allText.includes(dynamicMarkers[i])) {
                            return dynamicMarkers[i];
                        }
                    }
                    return false;
                """, element)
                
                if has_dynamic_markers:
                    print(f"⚠️ 動態廣告區塊: {ad_info['position']} ({ad_info['width']}x{ad_info['height']}) - 檢測到標識: {has_dynamic_markers}")
                    dynamic_elements.append(ad_info)
                else:
                    print(f"✅ 穩定廣告區塊: {ad_info['position']} ({ad_info['width']}x{ad_info['height']})")
                    stable_elements.append(ad_info)
                    
            except Exception as e:
                print(f"⚠️ 檢測廣告 {ad_info['position']} 時出錯，視為穩定: {str(e)[:50]}...")
                stable_elements.append(ad_info)
        
        return stable_elements, dynamic_elements
    
    def is_dynamic_ad_block(self, element, target_width, target_height, check_duration=None):
        """檢測廣告區塊是否為動態輪播廣告（快速版本）"""
        if check_duration is None:
            check_duration = self.dynamic_check_timeout
            
        try:
            # 首先快速檢查是否包含已知的動態廣告標識
            has_dynamic_markers = self.driver.execute_script("""
                var element = arguments[0];
                var html = element.innerHTML.toLowerCase();
                var outerHTML = element.outerHTML.toLowerCase();
                var allHTML = html + ' ' + outerHTML;
                
                var dynamicMarkers = [
                    'adpushup', 'rotation', 'carousel', 'slider', 'rotate',
                    'data-timeout', 'data-interval', 'auto-refresh',
                    'ad-rotation', 'banner-rotation', 'data-refresh',
                    'refresh-ad', 'ad-refresh', 'timer', 'countdown'
                ];
                
                for (var i = 0; i < dynamicMarkers.length; i++) {
                    if (allHTML.includes(dynamicMarkers[i])) {
                        return dynamicMarkers[i];
                    }
                }
                return false;
            """, element)
            
            if has_dynamic_markers:
                print(f"🔄 檢測到動態廣告標識: {has_dynamic_markers}")
                return True
            
            # 快速檢查元素的ID和class是否包含動態標識
            element_info = self.driver.execute_script("""
                var element = arguments[0];
                var id = element.id ? element.id.toLowerCase() : '';
                var className = element.className ? element.className.toLowerCase() : '';
                var combined = id + ' ' + className;
                
                var dynamicKeywords = [
                    'rotate', 'carousel', 'slider', 'dynamic', 'refresh',
                    'timer', 'auto', 'cycle', 'switch'
                ];
                
                for (var i = 0; i < dynamicKeywords.length; i++) {
                    if (combined.includes(dynamicKeywords[i])) {
                        return dynamicKeywords[i];
                    }
                }
                return false;
            """, element)
            
            if element_info:
                print(f"🔄 元素標識符包含動態關鍵字: {element_info}")
                return True
            
            # 獲取初始狀態（簡化版本）
            initial_state = self.driver.execute_script("""
                var element = arguments[0];
                if (!element) return null;
                
                var rect = element.getBoundingClientRect();
                var imgs = element.querySelectorAll('img');
                var imgSrc = imgs.length > 0 ? imgs[0].src : '';
                
                return {
                    width: rect.width,
                    height: rect.height,
                    imgSrc: imgSrc,
                    imgCount: imgs.length
                };
            """, element)
            
            if not initial_state:
                return False
            
            # 短暫等待（減少到1秒）
            time.sleep(check_duration)
            
            # 獲取後續狀態（簡化版本）
            final_state = self.driver.execute_script("""
                var element = arguments[0];
                if (!element) return null;
                
                var rect = element.getBoundingClientRect();
                var imgs = element.querySelectorAll('img');
                var imgSrc = imgs.length > 0 ? imgs[0].src : '';
                
                return {
                    width: rect.width,
                    height: rect.height,
                    imgSrc: imgSrc,
                    imgCount: imgs.length
                };
            """, element)
            
            if not final_state:
                return False
            
            # 比較關鍵變化
            size_changed = (abs(initial_state['width'] - final_state['width']) > 5 or 
                           abs(initial_state['height'] - final_state['height']) > 5)
            
            img_changed = (initial_state['imgSrc'] != final_state['imgSrc'] or
                          initial_state['imgCount'] != final_state['imgCount'])
            
            is_dynamic = size_changed or img_changed
            
            if is_dynamic:
                print(f"🔄 檢測到動態廣告: 尺寸變化={size_changed}, 圖片變化={img_changed}")
            else:
                print(f"✅ 廣告區塊穩定")
            
            return is_dynamic
            
        except Exception as e:
            print(f"⚠️ 動態廣告檢測失敗: {str(e)[:100]}...")
            # 發生錯誤時，為了不影響流程，認為是穩定的
            return False
    
    def take_screenshot(self):
        if not os.path.exists(SCREENSHOT_FOLDER):
            os.makedirs(SCREENSHOT_FOLDER)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"{SCREENSHOT_FOLDER}/ltn_{timestamp}.png"
        
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
    bot = GoogleAdReplacer(headless=False, screen_id=screen_id)
    
    try:
        # 使用 LTN_BASE_URL 如果存在，否則使用預設值
        base_url = "https://playing.ltn.com.tw"
        
        if 'LTN_BASE_URL' in globals():
            base_url = LTN_BASE_URL
        elif 'BASE_URL' in globals():
            base_url = BASE_URL
        
        print(f"目標網站: {base_url}")
        
        # 尋找新聞連結
        news_urls = bot.get_random_news_urls(base_url, NEWS_COUNT)
        
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
    test_bot = GoogleAdReplacer(headless=False, screen_id=screen_id)
    
    try:
        # 開啟測試頁面
        test_bot.driver.get("https://www.google.com")
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


    