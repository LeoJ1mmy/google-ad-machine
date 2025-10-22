#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Nicklee.tw Ad Replacer
======================

A specialized ad replacement tool for nicklee.tw website.
Based on the ad_replacer.py framework with customizations for nicklee.tw's
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

# 載入 GIF 功能專用設定檔
try:
    from gif_config import *
    print("成功載入 gif_config.py 設定檔")
    print(f"SCREENSHOT_COUNT 設定: {SCREENSHOT_COUNT}")
    print(f"NEWS_COUNT 設定: {NEWS_COUNT}")
    print(f"IMAGE_USAGE_COUNT 設定: {IMAGE_USAGE_COUNT}")
    print(f"GIF_PRIORITY 設定: {GIF_PRIORITY}")
    # 覆蓋 gif_config.py 中的 BASE_URL，設定 Nicklee 專用網址
    NICKLEE_BASE_URL = "https://nicklee.tw"
except ImportError:
    print("找不到 gif_config.py，使用預設設定")
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
        {"width": 336, "height": 280},
        {"width": 160, "height": 600},
        {"width": 120, "height": 600},
        {"width": 240, "height": 400},
        {"width": 250, "height": 250},
        {"width": 300, "height": 600},
        {"width": 320, "height": 100},
        {"width": 980, "height": 120},
        {"width": 468, "height": 60},
        {"width": 234, "height": 60},
        {"width": 125, "height": 125},
        {"width": 200, "height": 200}
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
                    # 方法1: 使用 PowerShell 取得所有螢幕資訊
                    powershell_cmd = '''
                    Add-Type -AssemblyName System.Windows.Forms
                    [System.Windows.Forms.Screen]::AllScreens | ForEach-Object {
                        Write-Output "$( $_.Bounds.Width )x$( $_.Bounds.Height ):$( $_.Primary )"
                    }
                    '''
                    result = subprocess.run(['powershell', '-Command', powershell_cmd], 
                                             capture_output=True, text=True)
                    if result.returncode == 0:
                        lines = [l for l in result.stdout.strip().split('\n') if l.strip()]
                        screen_id = 1
                        for line in lines:
                            if 'x' in line and ':' in line:
                                try:
                                    resolution, is_primary = line.strip().split(':')
                                    screens.append({
                                        'id': screen_id,
                                        'resolution': resolution,
                                        'primary': is_primary.lower() == 'true'
                                    })
                                    screen_id += 1
                                except Exception:
                                    continue
                except Exception as e:
                    print(f"PowerShell 方法失敗: {e}")
                
                # 方法2: 如果 PowerShell 失敗，使用 wmic (較舊環境)
                if not screens:
                    try:
                        cmd = 'wmic path Win32_VideoController get CurrentHorizontalResolution,CurrentVerticalResolution /format:csv'
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                        if result.returncode == 0:
                            lines = [l for l in result.stdout.strip().split('\n') if l.strip()]
                            screen_id = 1
                            for line in lines[1:]:  # 跳過標題行
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
                
                # 方法3: 再退回使用 tkinter
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
        """根據 GIF_PRIORITY 配置選擇圖片 - Nicklee 多螢幕支援版"""
        
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
        
        # Nicklee 多螢幕支援：優先級模式
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
    
    def get_button_style(self, element=None):
        """根據配置返回按鈕樣式 - 固定位置版本，針對扁平廣告優化"""
        button_style = getattr(self, 'button_style', BUTTON_STYLE)
        
        # 固定按鈕位置：距離廣告右上角各1px
        top_offset = "1px"
        right_offset = "1px"
        info_right_offset = "17px"  # 關閉按鈕右邊1px + 按鈕寬度15px + 間距1px = 17px
        
        # 統一的資訊按鈕樣式 - 針對扁平廣告優化
        unified_info_button = {
            "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M7.5 1.5a6 6 0 100 12 6 6 0 100-12m0 1a5 5 0 110 10 5 5 0 110-10zM6.625 11h1.75V6.5h-1.75zM7.5 3.75a1 1 0 100 2 1 1 0 100-2z" fill="#00aecd"/></svg>',
            "style": f'position:absolute;top:{top_offset};right:{info_right_offset};width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);cursor:pointer;line-height:0;vertical-align:top;'
        }
        
        button_styles = {
            "dots": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:block;"><circle cx="7.5" cy="3.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="7.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="11.5" r="1.5" fill="#00aecd"/></svg>',
                    "style": f'position:absolute;top:{top_offset};right:{right_offset};width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;line-height:0;vertical-align:top;'
                },
                "info_button": unified_info_button
            },
            "cross": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:block;"><path d="M4 4L11 11M11 4L4 11" stroke="#00aecd" stroke-width="1.5" stroke-linecap="round"/></svg>',
                    "style": f'position:absolute;top:{top_offset};right:{right_offset};width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;line-height:0;vertical-align:top;'
                },
                "info_button": unified_info_button
            },
            "adchoices": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:block;"><path d="M4 4L11 11M11 4L4 11" stroke="#00aecd" stroke-width="1.5" stroke-linecap="round"/></svg>',
                    "style": f'position:absolute;top:{top_offset};right:{right_offset};width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;line-height:0;vertical-align:top;'
                },
                "info_button": {
                    "html": '<img src="https://tpc.googlesyndication.com/pagead/images/adchoices/adchoices_blue_wb.png" width="15" height="15" style="display:block;width:15px;height:15px;vertical-align:top;">',
                    "style": f'position:absolute;top:{top_offset};right:{info_right_offset};width:15px;height:15px;z-index:100;display:block;cursor:pointer;line-height:0;vertical-align:top;'
                }
            },
            "adchoices_dots": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:block;"><circle cx="7.5" cy="3.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="7.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="11.5" r="1.5" fill="#00aecd"/></svg>',
                    "style": f'position:absolute;top:{top_offset};right:{right_offset};width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;line-height:0;vertical-align:top;'
                },
                "info_button": {
                    "html": '<img src="https://tpc.googlesyndication.com/pagead/images/adchoices/adchoices_blue_wb.png" width="15" height="15" style="display:block;width:15px;height:15px;vertical-align:top;">',
                    "style": f'position:absolute;top:{top_offset};right:{info_right_offset};width:15px;height:15px;z-index:100;display:block;cursor:pointer;line-height:0;vertical-align:top;'
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
    
    def scan_entire_page_for_ads(self, target_width, target_height):
        """掃描整個網頁尋找符合尺寸的廣告元素 - 針對 nicklee.tw 優化"""
        print(f"開始掃描整個網頁尋找 {target_width}x{target_height} 的廣告...")
        
        # 針對 nicklee.tw 的特定廣告選擇器（根據實際 HTML 結構優化）
        specific_selectors = [
            # 主要 Google AdSense 廣告區域
            'ins.adsbygoogle',  # 主要廣告容器
            'div[id^="aswift_"]',  # AdSense 廣告容器
            'iframe[id^="aswift_"]',  # AdSense iframe
            
            # 側邊廣告區塊（根據你的截圖）
            'div[id^="adwidget_htmlwidget-"]',  # 側邊廣告小工具
            'div[class*="graceful-widget AdWidget_HTMLWidget"]',  # 廣告小工具容器
            
            # 文章內廣告區域
            'div[class*="post-content"] ins.adsbygoogle',  # 文章內的廣告
            'center ins.adsbygoogle',  # 居中的廣告
            
            # 特定廣告容器（根據你的 HTML）
            'div[id="aswift_3_host"]',  # 特定廣告主機
            'div[id="aswift_2_host"]',  # 特定廣告主機
            'div[id="aswift_1_host"]',  # 特定廣告主機
            
            # iframe 廣告
            'iframe[name^="aswift_"]',  # AdSense iframe
            'iframe[src*="googleads"]',  # Google 廣告 iframe
            'iframe[src*="googlesyndication"]',  # Google 聯播網 iframe
            
            # 一般廣告容器
            'div[class*="ad"]',
            'div[id*="ad"]',
            'div[class*="banner"]',
            'div[id*="banner"]',
            
            # 圖片廣告
            'img[src*="ad"]',
            'img[src*="banner"]',
            'img[src*="google"]',
            
            # 通用容器（最後檢查）
            'div',
            'img',
            'iframe'
        ]
        
        matching_elements = []
        checked_elements = set()  # 避免重複檢查
        
        print("🔍 使用特定選擇器搜尋廣告...")
        for selector in specific_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"   選擇器 '{selector}' 找到 {len(elements)} 個元素")
                
                for element in elements:
                    try:
                        # 避免重複檢查同一個元素
                        element_id = self.driver.execute_script("return arguments[0]", element)
                        if element_id in checked_elements:
                            continue
                        checked_elements.add(element_id)
                        
                        # 檢查元素尺寸和詳細資訊
                        element_info = self.driver.execute_script("""
                            var element = arguments[0];
                            var targetWidth = arguments[1];
                            var targetHeight = arguments[2];
                            
                            try {
                                var rect = element.getBoundingClientRect();
                                var style = window.getComputedStyle(element);
                                var tagName = element.tagName.toLowerCase();
                                var className = element.className || '';
                                var id = element.id || '';
                                var src = element.src || '';
                                
                                // 基本尺寸檢查
                                var width = Math.round(rect.width);
                                var height = Math.round(rect.height);
                                var visible = rect.width > 0 && rect.height > 0 && 
                                             style.display !== 'none' && 
                                             style.visibility !== 'hidden' && 
                                             parseFloat(style.opacity) > 0;
                                
                                // 尺寸匹配檢查（允許小幅誤差）
                                var widthMatch = Math.abs(width - targetWidth) <= 2;
                                var heightMatch = Math.abs(height - targetHeight) <= 2;
                                var sizeMatch = widthMatch && heightMatch;
                                // 非 ins 元素放寬至 ±5px（避免影響右側/下方 <ins> 判斷）
                                if (!sizeMatch) {
                                    var looseMatch = (tagName !== 'ins') && (Math.abs(width - targetWidth) <= 5) && (Math.abs(height - targetHeight) <= 5);
                                    if (!looseMatch) {
                                        return null;
                                    }
                                }
                                
                                if (!visible || !sizeMatch) {
                                    return null;
                                }
                                
                                // nicklee.tw 特定廣告特徵檢查
                                var adKeywords = ['ad', 'advertisement', 'banner', 'google', 'ads', 'adsense', 'adsbygoogle', 'aswift', 'adwidget'];
                                var hasAdKeyword = adKeywords.some(function(keyword) {
                                    return className.toLowerCase().includes(keyword) ||
                                           id.toLowerCase().includes(keyword) ||
                                           src.toLowerCase().includes(keyword);
                                });
                                
                                // 檢查父元素和祖父元素的廣告特徵
                                var parentHasAdKeyword = false;
                                var grandparentHasAdKeyword = false;
                                var parent = element.parentElement;
                                if (parent) {
                                    var parentClass = parent.className || '';
                                    var parentId = parent.id || '';
                                    parentHasAdKeyword = adKeywords.some(function(keyword) {
                                        return parentClass.toLowerCase().includes(keyword) ||
                                               parentId.toLowerCase().includes(keyword);
                                    });
                                    
                                    // 檢查祖父元素
                                    var grandparent = parent.parentElement;
                                    if (grandparent) {
                                        var grandparentClass = grandparent.className || '';
                                        var grandparentId = grandparent.id || '';
                                        grandparentHasAdKeyword = adKeywords.some(function(keyword) {
                                            return grandparentClass.toLowerCase().includes(keyword) ||
                                                   grandparentId.toLowerCase().includes(keyword);
                                        });
                                    }
                                }
                                
                                // nicklee.tw 特定廣告容器檢查
                                var isNickleeAdContainer = 
                                    // AdSense 容器
                                    (tagName === 'ins' && className.includes('adsbygoogle')) ||
                                    // AdSense iframe 容器
                                    (id && id.includes('aswift_')) ||
                                    // 側邊廣告小工具
                                    (id && id.includes('adwidget_htmlwidget')) ||
                                    // 廣告小工具容器
                                    (className && className.includes('AdWidget_HTMLWidget')) ||
                                    // iframe 廣告
                                    (tagName === 'iframe' && (src.includes('googleads') || src.includes('googlesyndication')));
                                
                                // 檢查是否為常見的廣告元素類型
                                var isAdElement = tagName === 'ins' || 
                                                (tagName === 'iframe' && (hasAdKeyword || src.includes('google'))) || 
                                                (tagName === 'img' && (hasAdKeyword || parentHasAdKeyword)) ||
                                                (tagName === 'div' && (hasAdKeyword || parentHasAdKeyword || grandparentHasAdKeyword ||
                                                 style.backgroundImage && style.backgroundImage !== 'none'));
                                
                                // nicklee.tw 廣告判斷邏輯（更精確）
                                var isLikelyAd = isNickleeAdContainer || hasAdKeyword || parentHasAdKeyword || grandparentHasAdKeyword || isAdElement ||
                                               // 根據你提供的截圖，這些是實際的廣告尺寸
                                               (width === 600 && height === 280) ||  // 文章前廣告
                                               (width === 280 && height === 1073) || // 文章下方廣告
                                               (width === 1073 && height === 280) || // 文章上方廣告
                                               (width === 270 && height === 600) ||  // 側邊廣告
                                               // 常見廣告尺寸
                                               (width === 728 && height === 90) ||
                                               (width === 970 && height === 90) ||
                                               (width === 300 && height === 250) ||
                                               (width === 336 && height === 280) ||
                                               (width === 160 && height === 600) ||
                                               (width === 320 && height === 50) ||
                                               (width === 320 && height === 100) ||
                                               (width === 250 && height === 250) ||
                                               (width === 200 && height === 200) ||
                                               (width === 240 && height === 400) ||
                                               (width === 120 && height === 600);
                                
                                if (isLikelyAd) {
                                    return {
                                        width: width,
                                        height: height,
                                        top: rect.top,
                                        left: rect.left,
                                        visible: visible,
                                        tagName: tagName,
                                        className: className,
                                        id: id,
                                        hasAdKeyword: hasAdKeyword,
                                        parentHasAdKeyword: parentHasAdKeyword,
                                        isAdElement: isAdElement
                                    };
                                }
                                
                                return null;
                                
                            } catch (e) {
                                console.log('檢查元素時發生錯誤:', e);
                                return null;
                            }
                        """, element, target_width, target_height)
                        
                        if element_info:
                            matching_elements.append({
                                'element': element,
                                'width': element_info['width'],
                                'height': element_info['height'],
                                'position': f"top:{element_info['top']:.0f}, left:{element_info['left']:.0f}",
                                'info': element_info
                            })
                            print(f"✅ 找到符合廣告: {element_info['width']}x{element_info['height']} at {element_info['top']:.0f},{element_info['left']:.0f} ({element_info['tagName']}, class='{element_info['className'][:30]}...', id='{element_info['id'][:20]}...')")
                            
                    except Exception as e:
                        continue
                        
            except Exception as e:
                print(f"   選擇器 '{selector}' 執行失敗: {e}")
                continue
        
        # 如果特定選擇器沒找到，使用通用掃描
        if not matching_elements:
            print("🔍 特定選擇器未找到廣告，使用通用掃描...")
            all_elements = self.driver.execute_script("""
                var all = [];
                var elements = document.querySelectorAll('*');
                for (var i = 0; i < elements.length; i++) {
                    var element = elements[i];
                    var style = window.getComputedStyle(element);
                    if (style.display !== 'none' && 
                        style.visibility !== 'hidden' && 
                        parseFloat(style.opacity) > 0) {
                        all.push(element);
                    }
                }
                return all;
            """)
            
            print(f"通用掃描找到 {len(all_elements)} 個可見元素，開始檢查尺寸...")
            
            for i, element in enumerate(all_elements):
                try:
                    # 檢查元素尺寸
                    size_info = self.driver.execute_script("""
                        var element = arguments[0];
                        var targetWidth = arguments[1];
                        var targetHeight = arguments[2];
                        
                        var rect = element.getBoundingClientRect();
                        var width = Math.round(rect.width);
                        var height = Math.round(rect.height);
                        
                        // 允許小幅誤差
                        if (Math.abs(width - targetWidth) <= 2 && 
                            Math.abs(height - targetHeight) <= 2 &&
                            rect.width > 0 && rect.height > 0) {
                            return {
                                width: width,
                                height: height,
                                top: rect.top,
                                left: rect.left,
                                visible: true
                            };
                        }
                        return null;
                    """, element, target_width, target_height)
                    
                    if size_info:
                        matching_elements.append({
                            'element': element,
                            'width': size_info['width'],
                            'height': size_info['height'],
                            'position': f"top:{size_info['top']:.0f}, left:{size_info['left']:.0f}"
                        })
                        print(f"✅ 通用掃描找到: {size_info['width']}x{size_info['height']} at {size_info['top']:.0f},{size_info['left']:.0f}")
                    
                    # 每檢查1000個元素顯示進度
                    if (i + 1) % 1000 == 0:
                        print(f"已檢查 {i + 1}/{len(all_elements)} 個元素...")
                        
                except Exception as e:
                    continue
        
        print(f"🎯 掃描完成，總共找到 {len(matching_elements)} 個符合 {target_width}x{target_height} 尺寸的廣告元素")
        
        # 如果沒有找到符合尺寸的廣告，顯示 nicklee.tw 網站上的實際廣告尺寸
        if len(matching_elements) == 0:
            print(f"💡 未找到 {target_width}x{target_height} 尺寸的廣告，以下是 nicklee.tw 網站上的廣告尺寸分析：")
            ad_sizes = self.driver.execute_script("""
                var adSizes = {};
                
                // 檢查 AdSense 廣告
                var adsenseElements = document.querySelectorAll('ins.adsbygoogle, div[id*="aswift"], iframe[id*="aswift"], div[id*="adwidget"]');
                
                for (var i = 0; i < adsenseElements.length; i++) {
                    var el = adsenseElements[i];
                    var rect = el.getBoundingClientRect();
                    var width = Math.round(rect.width);
                    var height = Math.round(rect.height);
                    
                    if (width > 50 && height > 50) {
                        var sizeKey = width + 'x' + height;
                        var info = {
                            size: sizeKey,
                            count: (adSizes[sizeKey] ? adSizes[sizeKey].count : 0) + 1,
                            tagName: el.tagName.toLowerCase(),
                            className: el.className || '',
                            id: el.id || '',
                            position: 'top:' + Math.round(rect.top) + ', left:' + Math.round(rect.left)
                        };
                        adSizes[sizeKey] = info;
                    }
                }
                
                // 轉換為陣列並排序
                var sizeArray = [];
                for (var size in adSizes) {
                    sizeArray.push(adSizes[size]);
                }
                
                // 按尺寸排序
                sizeArray.sort(function(a, b) { 
                    var aSize = a.size.split('x').map(Number);
                    var bSize = b.size.split('x').map(Number);
                    return (bSize[0] * bSize[1]) - (aSize[0] * aSize[1]);
                });
                
                return sizeArray;
            """)
            
            if ad_sizes:
                print("   📐 發現的廣告尺寸:")
                for ad_info in ad_sizes:
                    tag_info = f"<{ad_info['tagName']}>"
                    class_info = f" class='{ad_info['className'][:30]}...'" if ad_info['className'] else ""
                    id_info = f" id='{ad_info['id'][:20]}...'" if ad_info['id'] else ""
                    print(f"      🎯 {ad_info['size']}: {ad_info['count']} 個 {tag_info}{class_info}{id_info}")
                    print(f"         位置: {ad_info['position']}")
            else:
                print("   📐 無法檢測到廣告元素，可能網站結構已變更或廣告被阻擋")
        
        # 按位置排序，優先處理頁面上方的廣告
        matching_elements.sort(key=lambda x: x['info']['top'] if 'info' in x else float(x['position'].split(',')[0].split(':')[1]))
        
        return matching_elements
    
    def replace_ad_content(self, element, image_data, target_width, target_height):
        """替換廣告內容"""
        try:
            # 取得元素 tag 與 class 以決定尺寸容差策略
            try:
                tag_and_class = self.driver.execute_script("""
                    var el = arguments[0];
                    return {
                        tag: (el && el.tagName) ? el.tagName.toLowerCase() : '',
                        className: (el && el.className) ? (el.className.toString()) : ''
                    };
                """, element)
            except Exception:
                tag_and_class = {'tag': '', 'className': ''}
            is_ins_like = (tag_and_class.get('tag') == 'ins') or ('adsbygoogle' in (tag_and_class.get('className') or '').lower())

            # 獲取原始尺寸
            original_info = self.driver.execute_script("""
                var element = arguments[0];
                if (!element || !element.getBoundingClientRect) return null;
                var rect = element.getBoundingClientRect();
                return {width: rect.width, height: rect.height};
            """, element)
            
            if not original_info:
                return False
            
            # 檢查是否符合目標尺寸（<ins> 保持嚴格，其餘放寬 ±5px）
            if is_ins_like:
                if (original_info['width'] != target_width or original_info['height'] != target_height):
                    return False
            else:
                if (abs(original_info['width'] - target_width) > 5 or abs(original_info['height'] - target_height) > 5):
                    return False
            
            # 獲取按鈕樣式（傳遞 element 參數進行動態位置調整）
            button_style = self.get_button_style(element)
            
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
            
            # 替換廣告內容
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
                
                console.log('開始替換廣告:', targetWidth + 'x' + targetHeight);
                
                // 確保 container 是 relative
                if (window.getComputedStyle(container).position === 'static') {
                  container.style.position = 'relative';
                }
                
                // 先移除舊的按鈕（避免重複）
                ['close_button', 'abgb'].forEach(function(id){
                  var old = container.querySelector('#'+id);
                  if(old) old.remove();
                });
                
                var replacedCount = 0;
                var newImageSrc = 'data:image/png;base64,' + imageBase64;
                
                // 方法1: 替換img標籤的src
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
                                         img.src.includes('adchoices');
                    
                    if (!isControlButton && img.src && !img.src.startsWith('data:')) {
                        // 保存原始src以便復原
                        if (!img.getAttribute('data-original-src')) {
                            img.setAttribute('data-original-src', img.src);
                        }
                        // 替換圖片
                        img.src = newImageSrc;
                        img.style.objectFit = 'contain';
                        img.style.width = '100%';
                        img.style.height = 'auto';
                        replacedCount++;
                        
                        // 確保img的父層是relative
                        var imgParent = img.parentElement || container;
                        if (window.getComputedStyle(imgParent).position === 'static') {
                            imgParent.style.position = 'relative';
                        }
                        
                        // 只有在非 none 模式下才創建按鈕
                        if (!isNoneMode && closeButtonHtml && infoButtonHtml) {
                            // 確保父容器是 relative 定位
                            if (window.getComputedStyle(imgParent).position === 'static') {
                                imgParent.style.position = 'relative';
                            }
                            
                            // 使用 setTimeout 延遲創建按鈕，確保樣式完全應用
                            setTimeout(function() {
                                // 移除可能存在的舊按鈕
                                ['close_button', 'abgb'].forEach(function(id){
                                    var old = imgParent.querySelector('#'+id);
                                    if(old) old.remove();
                                });
                                
                                // 叉叉按鈕 - 固定位置：距離右上角各1px
                                if (closeButtonHtml) {
                                    var closeButton = document.createElement('div');
                                    closeButton.id = 'close_button';
                                    closeButton.innerHTML = closeButtonHtml;
                                    closeButton.style.cssText = closeButtonStyle;
                                    imgParent.appendChild(closeButton);
                                }
                                
                                // 資訊按鈕 - 固定位置：距離右上角1px，距離關閉按鈕17px
                                if (infoButtonHtml) {
                                    var abgb = document.createElement('div');
                                    abgb.id = 'abgb';
                                    abgb.className = 'abgb';
                                    abgb.innerHTML = infoButtonHtml;
                                    abgb.style.cssText = infoButtonStyle;
                                    imgParent.appendChild(abgb);
                                }
                            }, 10); // 延遲10毫秒，讓瀏覽器完成樣式計算
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
                    iframe.setAttribute('data-original-visibility', 'visible');
                    
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
                    newImg.setAttribute('data-replacement-img', 'true');
                    
                    container.appendChild(newImg);
                    
                    // 只有在非 none 模式下才創建按鈕
                    if (!isNoneMode && closeButtonHtml && infoButtonHtml) {
                        // 確保容器定位正確
                        if (window.getComputedStyle(container).position === 'static') {
                            container.style.position = 'relative';
                        }
                        
                        // 強制重新計算容器樣式
                        container.offsetHeight;
                        
                        // 重新獲取精確的位置信息（避免第一次計算誤差）
                        var containerRect = container.getBoundingClientRect();
                        var updatedIframeRect = iframe.getBoundingClientRect();
                        
                        // 固定按鈕位置：距離 iframe 右上角各1px
                        var topPos = updatedIframeRect.top - containerRect.top + 1;
                        var rightPos = containerRect.right - updatedIframeRect.right + 1;
                        
                        // 叉叉按鈕 - 固定位置
                        var closeButton = document.createElement('div');
                        closeButton.id = 'close_button';
                        closeButton.innerHTML = closeButtonHtml;
                        closeButton.style.cssText = 'position:absolute;top:' + topPos + 'px;right:' + rightPos + 'px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;box-sizing:border-box;';
                        
                        // 資訊按鈕 - 距離關閉按鈕17px
                        var abgb = document.createElement('div');
                        abgb.id = 'abgb';
                        abgb.className = 'abgb';
                        abgb.innerHTML = infoButtonHtml;
                        abgb.style.cssText = 'position:absolute;top:' + topPos + 'px;right:' + (rightPos + 17) + 'px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);cursor:pointer;box-sizing:border-box;';
                        
                        container.appendChild(abgb);
                        container.appendChild(closeButton);
                        
                        // 強制重新計算按鈕位置
                        closeButton.offsetHeight;
                        abgb.offsetHeight;
                    }
                    replacedCount++;
                }
                
                // 方法3: 處理背景圖片
                if (replacedCount === 0) {
                    var style = window.getComputedStyle(container);
                    if (style.backgroundImage && style.backgroundImage !== 'none') {
                        // 保存原始背景圖片
                        container.setAttribute('data-original-bg', style.backgroundImage);
                        container.style.backgroundImage = 'url(' + newImageSrc + ')';
                        container.style.backgroundSize = 'contain';
                        container.style.backgroundRepeat = 'no-repeat';
                        container.style.backgroundPosition = 'center';
                        replacedCount = 1;
                        
                        // 只有在非 none 模式下才創建按鈕
                        if (!isNoneMode && closeButtonHtml && infoButtonHtml) {
                            // 確保容器定位正確
                            if (window.getComputedStyle(container).position === 'static') {
                                container.style.position = 'relative';
                            }
                            
                            // 使用 setTimeout 延遲創建按鈕
                            setTimeout(function() {
                                // 叉叉按鈕
                                var closeButton = document.createElement('div');
                                closeButton.id = 'close_button';
                                closeButton.innerHTML = closeButtonHtml;
                                closeButton.style.cssText = closeButtonStyle;
                                
                                // 資訊按鈕
                                var abgb = document.createElement('div');
                                abgb.id = 'abgb';
                                abgb.className = 'abgb';
                                abgb.innerHTML = infoButtonHtml;
                                abgb.style.cssText = infoButtonStyle;
                                
                                container.appendChild(abgb);
                                container.appendChild(closeButton);
                            }, 10);
                        }
                    }
                }
                
                console.log('廣告替換完成，替換了', replacedCount, '個元素');
                return replacedCount > 0;
            """, element, image_data, target_width, target_height, close_button_html, close_button_style, info_button_html, info_button_style, is_none_mode)
            
            if success:
                print(f"✅ 成功替換廣告 {original_info['width']}x{original_info['height']}")
                return True
            else:
                print(f"❌ 廣告替換失敗 {original_info['width']}x{original_info['height']}")
                return False
                
        except Exception as e:
            print(f"替換廣告失敗: {e}")
            return False
    
    def restore_ad_content(self, element):
        """還原廣告內容"""
        try:
            success = self.driver.execute_script("""
                var container = arguments[0];
                if (!container) return false;
                
                console.log('開始還原廣告內容');
                
                // 移除我們添加的按鈕
                ['close_button', 'abgb'].forEach(function(id){
                    var btn = container.querySelector('#'+id);
                    if (btn) btn.remove();
                });
                
                // 移除我們添加的替換圖片
                var replacementImgs = container.querySelectorAll('img[data-replacement-img="true"]');
                for (var i = 0; i < replacementImgs.length; i++) {
                    replacementImgs[i].remove();
                }
                
                // 還原原始圖片
                var imgs = container.querySelectorAll('img[data-original-src]');
                for (var i = 0; i < imgs.length; i++) {
                    var img = imgs[i];
                    var originalSrc = img.getAttribute('data-original-src');
                    if (originalSrc) {
                        img.src = originalSrc;
                        img.removeAttribute('data-original-src');
                        // 還原原始樣式
                        img.style.objectFit = '';
                        img.style.width = '';
                        img.style.height = '';
                    }
                }
                
                // 還原iframe可見性
                var iframes = container.querySelectorAll('iframe[data-original-visibility]');
                for (var i = 0; i < iframes.length; i++) {
                    var iframe = iframes[i];
                    iframe.style.visibility = iframe.getAttribute('data-original-visibility');
                    iframe.removeAttribute('data-original-visibility');
                }
                
                // 還原背景圖片
                var originalBg = container.getAttribute('data-original-bg');
                if (originalBg) {
                    container.style.backgroundImage = originalBg;
                    container.removeAttribute('data-original-bg');
                    // 還原背景樣式
                    container.style.backgroundSize = '';
                    container.style.backgroundRepeat = '';
                    container.style.backgroundPosition = '';
                }
                
                console.log('廣告內容還原完成');
                return true;
            """, element)
            
            if success:
                print("✅ 成功還原廣告內容")
                return True
            else:
                print("❌ 還原廣告內容失敗")
                return False
                
        except Exception as e:
            print(f"還原廣告內容失敗: {e}")
            return False
    
    def process_website(self, url):
        """處理單個網站，遍歷所有替換圖片"""
        try:
            print(f"\n開始處理網站: {url}")
            
            # 載入網頁
            self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
            self.driver.get(url)
            time.sleep(WAIT_TIME)
            
            # 遍歷所有替換圖片
            total_replacements = 0
            screenshot_paths = []  # 儲存所有截圖路徑
            processed_positions = set()  # 記錄已處理的位置，避免重複
            
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
                
                # 只處理第一個找到的廣告位置（每個版位只截一次）
                for ad_info in matching_elements:
                    # 檢查是否已經處理過這個位置
                    position_key = f"{ad_info['position']}_{image_info['width']}x{image_info['height']}"
                    if position_key in processed_positions:
                        print(f"跳過已處理的位置: {ad_info['position']}")
                        continue
                        
                    try:
                        # 替換廣告
                        if self.replace_ad_content(ad_info['element'], image_data, image_info['width'], image_info['height']):
                            print(f"成功替換廣告: {ad_info['width']}x{ad_info['height']} at {ad_info['position']}")
                            total_replacements += 1
                            processed_positions.add(position_key)  # 記錄已處理的位置
                            
                            # 滾動到廣告位置確保可見
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
                            
                            # 截圖
                            print("準備截圖...")
                            time.sleep(2)  # 等待頁面穩定
                            screenshot_path = self.take_screenshot()
                            if screenshot_path:
                                screenshot_paths.append(screenshot_path)
                                print(f"✅ 截圖保存: {screenshot_path}")
                            else:
                                print("❌ 截圖失敗")
                            
                            # 截圖後立即還原該位置的廣告
                            self.restore_ad_content(ad_info['element'])
                            print("✅ 廣告位置已還原")
                            
                            # 每個版位只處理一次，處理完就跳出
                            break
                            
                    except Exception as e:
                        print(f"替換廣告失敗: {e}")
                        continue
            
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
    
    def take_screenshot(self):
        """截圖功能"""
        if not os.path.exists(SCREENSHOT_FOLDER):
            os.makedirs(SCREENSHOT_FOLDER)
        
        # 獲取文章標題
        try:
            article_title = self.driver.execute_script("""
                // 嘗試多種方式獲取文章標題
                var title = '';
                
                // 方法1: 嘗試獲取 h1.post-title
                var postTitle = document.querySelector('h1.post-title');
                if (postTitle && postTitle.textContent) {
                    title = postTitle.textContent.trim();
                }
                
                // 方法2: 如果沒找到，嘗試其他標題選擇器
                if (!title) {
                    var titleSelectors = [
                        '.post-title',
                        '.entry-title', 
                        'h1',
                        'title'
                    ];
                    
                    for (var i = 0; i < titleSelectors.length; i++) {
                        var element = document.querySelector(titleSelectors[i]);
                        if (element && element.textContent) {
                            title = element.textContent.trim();
                            break;
                        }
                    }
                }
                
                // 方法3: 最後嘗試 document.title
                if (!title) {
                    title = document.title || '';
                }
                
                // 清理標題，移除不適合檔名的字符
                title = title.replace(/[<>:"/\\\\|?*]/g, '').replace(/\\s+/g, '_');
                
                // 限制長度
                if (title.length > 50) {
                    title = title.substring(0, 50);
                }
                
                return title || 'untitled';
            """)
        except Exception as e:
            print(f"獲取文章標題失敗: {e}")
            article_title = "untitled"
        
        # 進一步清理標題
        if article_title:
            # 移除或替換特殊字符
            article_title = re.sub(r'[^\w\u4e00-\u9fff\-_]', '_', article_title)
            # 移除多餘的底線
            article_title = re.sub(r'_+', '_', article_title).strip('_')
            # 限制長度
            if len(article_title) > 40:
                article_title = article_title[:40]
        else:
            article_title = "untitled"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"{SCREENSHOT_FOLDER}/nicklee_{article_title}_{timestamp}.png"
        
        try:
            time.sleep(1)  # 等待頁面穩定
            
            system = platform.system()
            
            if system == "Darwin":  # macOS
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
            elif system == "Windows":
                # Windows 多螢幕截圖 - 優先使用 MSS
                try:
                    import mss
                    with mss.mss() as sct:
                        monitors = sct.monitors
                        print(f"MSS 偵測到 {len(monitors)-1} 個螢幕: {monitors}")
                        # MSS monitors[0] 是所有螢幕的組合，實際螢幕從 monitors[1] 開始
                        if 0 < self.screen_id < len(monitors):
                            monitor = monitors[self.screen_id]
                        else:
                            monitor = monitors[1]
                            print(f"⚠️ 螢幕 {self.screen_id} 超出範圍，使用主螢幕")
                        screenshot_mss = sct.grab(monitor)
                        from PIL import Image
                        screenshot = Image.frombytes('RGB', screenshot_mss.size, screenshot_mss.bgra, 'raw', 'BGRX')
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
                    except Exception:
                        print("pyautogui 也失敗，使用 Selenium 截圖")
                        self.driver.save_screenshot(filepath)
                        print(f"截圖保存: {filepath}")
                        return filepath
                except Exception as e:
                    print(f"❌ MSS 截圖失敗: {e}")
                    try:
                        import pyautogui
                        screenshot = pyautogui.screenshot()
                        screenshot.save(filepath)
                        print(f"✅ pyautogui 截圖保存: {filepath}")
                        return filepath
                    except Exception:
                        print("pyautogui 也失敗，使用 Selenium 截圖")
                        self.driver.save_screenshot(filepath)
                        print(f"截圖保存: {filepath}")
                        return filepath
            else:
                # 其他系統使用 Selenium 截圖
                self.driver.save_screenshot(filepath)
                print(f"截圖保存: {filepath}")
                return filepath
                
        except Exception as e:
            print(f"截圖失敗: {e}")
            return None
    
    def get_nicklee_article_urls(self, base_url, count):
        """獲取 nicklee.tw 文章 URLs"""
        print(f"正在從 {base_url} 獲取文章連結...")
        
        try:
            self.driver.get(base_url)
            time.sleep(3)
            
            # 尋找文章連結
            article_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='nicklee.tw']")
            
            urls = []
            for link in article_links:
                try:
                    href = link.get_attribute('href')
                    if href and self._is_valid_article_url(href):
                        urls.append(href)
                except:
                    continue
            
            # 去重並限制數量
            unique_urls = list(set(urls))
            return unique_urls[:count]
            
        except Exception as e:
            print(f"獲取文章連結時發生錯誤: {e}")
            return []
    
    def _is_valid_article_url(self, url):
        """檢查是否為有效的文章 URL"""
        if not url or not url.startswith('https://nicklee.tw'):
            return False
        
        # 排除不需要的 URL
        exclude_patterns = ['#', 'javascript:', 'mailto:', '/category', '/tag', '/feed', '.xml']
        for pattern in exclude_patterns:
            if pattern in url.lower():
                return False
        
        # 檢查是否包含文章 ID 或年份
        return bool(re.search(r'/\d+/', url) or '/20' in url)
    
    def run(self, urls=None, count=None):
        """運行廣告替換程序"""
        if count is None:
            count = SCREENSHOT_COUNT
        
        print(f"\n🚀 Nicklee.tw 廣告替換器啟動")
        print(f"目標截圖數量: {count}")
        
        try:
            # 如果沒有提供 URLs，則自動獲取
            if not urls:
                print("未提供 URLs，將自動從 nicklee.tw 獲取文章連結...")
                urls = self.get_nicklee_article_urls(NICKLEE_BASE_URL, count)
                
                if not urls:
                    print("❌ 無法獲取任何文章連結，程序結束")
                    return
            
            # 處理每個 URL
            results = []
            successful_count = 0
            
            for i, url in enumerate(urls[:count], 1):
                print(f"\n📄 處理第 {i}/{min(count, len(urls))} 個頁面")
                
                try:
                    screenshot_paths = self.process_website(url)
                    
                    result = {
                        'url': url,
                        'screenshot_paths': screenshot_paths,
                        'success': len(screenshot_paths) > 0
                    }
                    
                    results.append(result)
                    
                    if result['success']:
                        successful_count += 1
                    
                    # 避免請求過於頻繁
                    if i < len(urls):
                        time.sleep(1)
                        
                except Exception as e:
                    print(f"處理 URL 時發生錯誤: {e}")
                    results.append({
                        'url': url,
                        'screenshot_paths': [],
                        'success': False
                    })
            
            # 輸出最終統計
            print(f"\n{'='*80}")
            print(f"🎉 廣告替換完成！")
            print(f"{'='*80}")
            print(f"總處理頁面: {len(results)}")
            print(f"成功處理: {successful_count}")
            print(f"失敗處理: {len(results) - successful_count}")
            
            # 顯示截圖資訊
            total_screenshots = sum(len(r['screenshot_paths']) for r in results)
            print(f"\n📸 截圖統計:")
            print(f"成功截圖: {total_screenshots}")
            print(f"截圖保存位置: {SCREENSHOT_FOLDER}/")
            
            return results
            
        except KeyboardInterrupt:
            print("\n⚠️ 用戶中斷程序")
            return []
        except Exception as e:
            print(f"\n❌ 程序執行時發生嚴重錯誤: {e}")
            return []
        finally:
            # 清理資源
            try:
                self.driver.quit()
                print("✅ 瀏覽器已關閉")
            except:
                pass

def main():
    """主函數"""
    print("🌟 Nicklee.tw 廣告替換器")
    print("=" * 50)
    
    # 偵測並選擇螢幕
    screen_id, selected_screen = ScreenManager.select_screen()
    
    if screen_id is None:
        print("未選擇螢幕，程式結束")
        return
    
    try:
        # 創建廣告替換器實例
        replacer = NickleeAdReplacer(headless=HEADLESS_MODE, screen_id=screen_id)
        
        # 運行廣告替換
        results = replacer.run()
        
        if results:
            print(f"\n✅ 程序執行完成，共處理 {len(results)} 個頁面")
        else:
            print("\n❌ 程序執行失敗或被中斷")
            
    except Exception as e:
        print(f"\n❌ 程序啟動失敗: {e}")

if __name__ == "__main__":
    main()