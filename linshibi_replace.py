#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Linshibi.com Ad Replacer
========================

A specialized ad replacement tool for linshibi.com website.
Based on the ad_replacer.py framework with customizations for linshibi.com's
specific structure and ad placement patterns.

Features:
- Automatic article discovery from linshibi.com
- Multi-screen support with ScreenManager
- Configurable button styles (dots, cross, adchoices, adchoices_dots, none)
- Ad replacement with custom images while preserving <ins> elements
- Screenshot capture with automatic restoration
- Integration with config.py parameters

Author: Ad Replacement System
Version: 1.0
Target Website: https://linshibi.com
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
    LINSHIBI_BASE_URL = "https://linshibi.com/?cat=165"
    NEWS_COUNT = 20
    LINSHIBI_TARGET_AD_SIZES = [
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
    BUTTON_STYLE = "dots"

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

class LinshibiAdReplacer:
    """Linshibi.com 廣告替換器"""
    
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
    
    def get_button_style(self):
        """根據配置返回按鈕樣式 - 參考 ad_replacer.py"""
        button_style = getattr(self, 'button_style', BUTTON_STYLE)
        
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
    
    def scan_entire_page_for_ads(self, target_width, target_height):
        """掃描整個網頁尋找符合尺寸的廣告元素 - 針對 linshibi.com 優化，保留 <ins> 元素"""
        print(f"開始掃描整個網頁尋找 {target_width}x{target_height} 的廣告...")
        
        # 先嘗試特定的 linshibi.com 廣告選擇器
        specific_selectors = [
            # Google AdSense 相關 - 但排除 <ins> 元素
            'div[id^="aswift_"]:not(ins)',
            'iframe[id^="aswift_"]:not(ins)',
            # 一般廣告容器 - 但排除 <ins> 元素
            'div[class*="ad"]:not(ins)',
            'div[id*="ad"]:not(ins)',
            'div[class*="banner"]:not(ins)',
            'div[id*="banner"]:not(ins)',
            'div[class*="google"]:not(ins)',
            'div[id*="google"]:not(ins)',
            # 圖片廣告 - 但排除 <ins> 元素內的圖片
            'img[src*="ad"]:not(ins img)',
            'img[src*="banner"]:not(ins img)',
            'img[src*="google"]:not(ins img)',
            # iframe 廣告 - 但排除 <ins> 元素內的 iframe
            'iframe[src*="google"]:not(ins iframe)',
            'iframe[src*="ad"]:not(ins iframe)',
            # 通用容器 - 但排除 <ins> 元素
            'div:not(ins)',
            'img:not(ins img)',
            'iframe:not(ins iframe)'
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
                        
                        # 檢查元素是否在 <ins> 內部，如果是則跳過
                        is_inside_ins = self.driver.execute_script("""
                            var element = arguments[0];
                            var current = element;
                            while (current && current.parentElement) {
                                current = current.parentElement;
                                if (current.tagName && current.tagName.toLowerCase() === 'ins') {
                                    return true;
                                }
                            }
                            return false;
                        """, element)
                        
                        if is_inside_ins:
                            continue  # 跳過 <ins> 內部的元素
                        
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
                                
                                if (!visible || !sizeMatch) {
                                    return null;
                                }
                                
                                // 廣告特徵檢查
                                var adKeywords = ['ad', 'advertisement', 'banner', 'google', 'ads', 'adsense', 'adsbygoogle'];
                                var hasAdKeyword = adKeywords.some(function(keyword) {
                                    return className.toLowerCase().includes(keyword) ||
                                           id.toLowerCase().includes(keyword) ||
                                           src.toLowerCase().includes(keyword);
                                });
                                
                                // 檢查父元素是否有廣告特徵
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
                                
                                // 檢查是否為常見的廣告元素類型
                                var isAdElement = tagName === 'iframe' || 
                                                (tagName === 'img' && (hasAdKeyword || parentHasAdKeyword)) ||
                                                (tagName === 'div' && (hasAdKeyword || parentHasAdKeyword || 
                                                 style.backgroundImage && style.backgroundImage !== 'none'));
                                
                                // 對於 linshibi.com，放寬條件
                                var isLikelyAd = hasAdKeyword || parentHasAdKeyword || isAdElement ||
                                               // 特定尺寸通常是廣告
                                               (width >= 120 && height >= 60) ||
                                               // 常見廣告尺寸
                                               (width === 728 && height === 90) ||
                                               (width === 970 && height === 90) ||
                                               (width === 300 && height === 250) ||
                                               (width === 336 && height === 280) ||
                                               (width === 160 && height === 600) ||
                                               (width === 320 && height === 50);
                                
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
        
        print(f"🎯 掃描完成，總共找到 {len(matching_elements)} 個符合 {target_width}x{target_height} 尺寸的廣告元素")
        
        # 按位置排序，優先處理頁面上方的廣告
        matching_elements.sort(key=lambda x: x['info']['top'] if 'info' in x else x['position'])
        
        return matching_elements    
   
 def replace_ad_content(self, element, image_data, target_width, target_height):
        """替換廣告內容 - 保留 <ins> 元素，參考 ad_replacer.py 的按鈕組設計"""
        try:
            # 檢查元素是否在 <ins> 內部，如果是則跳過
            is_inside_ins = self.driver.execute_script("""
                var element = arguments[0];
                var current = element;
                while (current && current.parentElement) {
                    current = current.parentElement;
                    if (current.tagName && current.tagName.toLowerCase() === 'ins') {
                        return true;
                    }
                }
                return false;
            """, element)
            
            if is_inside_ins:
                print("跳過 <ins> 內部的元素")
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
            
            # 檢查是否符合目標尺寸
            if (abs(original_info['width'] - target_width) > 2 or 
                abs(original_info['height'] - target_height) > 2):
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
            
            # 替換廣告內容 - 參考 ad_replacer.py 的實現
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
                        // 替換圖片
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
                        
                        // 只有在非 none 模式下才創建按鈕
                        if (!isNoneMode && closeButtonHtml && infoButtonHtml) {
                            // 叉叉按鈕
                            if (closeButtonHtml) {
                                var closeButton = document.createElement('div');
                                closeButton.id = 'close_button';
                                closeButton.innerHTML = closeButtonHtml;
                                closeButton.style.cssText = closeButtonStyle;
                                imgParent.appendChild(closeButton);
                            }
                            
                            // 資訊按鈕
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
                        // 叉叉按鈕
                        var closeButton = document.createElement('div');
                        closeButton.id = 'close_button';
                        closeButton.innerHTML = closeButtonHtml;
                        closeButton.style.cssText = 'position:absolute;top:' + (iframeRect.top - container.getBoundingClientRect().top) + 'px;right:' + (container.getBoundingClientRect().right - iframeRect.right) + 'px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);border-radius:2px;';
                        
                        // 資訊按鈕
                        var abgb = document.createElement('div');
                        abgb.id = 'abgb';
                        abgb.className = 'abgb';
                        abgb.innerHTML = infoButtonHtml;
                        abgb.style.cssText = 'position:absolute;top:' + (iframeRect.top - container.getBoundingClientRect().top) + 'px;right:' + (container.getBoundingClientRect().right - iframeRect.right + 17) + 'px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);border-radius:2px;line-height:0;';
                        
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
                        container.setAttribute('data-original-bg', style.backgroundImage);
                        container.style.backgroundImage = 'url(' + newImageSrc + ')';
                        container.style.backgroundSize = 'contain';
                        container.style.backgroundRepeat = 'no-repeat';
                        container.style.backgroundPosition = 'center';
                        replacedCount = 1;
                        
                        // 只有在非 none 模式下才創建按鈕
                        if (!isNoneMode && closeButtonHtml && infoButtonHtml) {
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
                        img.style.maxWidth = '';
                        img.style.maxHeight = '';
                        img.style.minWidth = '';
                        img.style.minHeight = '';
                        img.style.display = '';
                        img.style.margin = '';
                        img.style.padding = '';
                        img.style.border = '';
                        img.style.outline = '';
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
                
                // 方法1: 嘗試獲取 h1 標題
                var h1Elements = document.querySelectorAll('h1');
                for (var i = 0; i < h1Elements.length; i++) {
                    var h1 = h1Elements[i];
                    if (h1.textContent && h1.textContent.trim()) {
                        title = h1.textContent.trim();
                        break;
                    }
                }
                
                // 方法2: 如果沒找到，嘗試其他標題選擇器
                if (!title) {
                    var titleSelectors = [
                        '.entry-title',
                        '.post-title',
                        'h2',
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
                title = title.replace(/[<>:"/\\|?*]/g, '').replace(/\s+/g, '_');
                
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
        filepath = f"{SCREENSHOT_FOLDER}/linshibi_{article_title}_{timestamp}.png"
        
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
    
    def get_linshibi_article_urls(self, base_url, count):
        """獲取 linshibi.com 文章 URLs"""
        print(f"正在從 {base_url} 獲取文章連結...")
        
        try:
            self.driver.get(base_url)
            time.sleep(3)
            
            # 尋找文章連結
            article_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='linshibi.com']")
            
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
        if not url or not url.startswith('https://linshibi.com'):
            return False
        
        # 排除不需要的 URL
        exclude_patterns = ['#', 'javascript:', 'mailto:', '/category', '/tag', '/feed', '.xml', '?cat=']
        for pattern in exclude_patterns:
            if pattern in url.lower():
                return False
        
        # 檢查是否包含文章 ID 或年份
        return bool(re.search(r'/\d+/', url) or '/20' in url)
    
    def run(self, urls=None, count=None):
        """運行廣告替換程序"""
        if count is None:
            count = SCREENSHOT_COUNT
        
        print(f"\n🚀 Linshibi.com 廣告替換器啟動")
        print(f"目標截圖數量: {count}")
        
        try:
            # 如果沒有提供 URLs，則自動獲取
            if not urls:
                print("未提供 URLs，將自動從 linshibi.com 獲取文章連結...")
                urls = self.get_linshibi_article_urls(LINSHIBI_BASE_URL, count)
                
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
    print("🌟 Linshibi.com 廣告替換器")
    print("=" * 50)
    
    # 偵測並選擇螢幕
    screen_id, selected_screen = ScreenManager.select_screen()
    
    if screen_id is None:
        print("未選擇螢幕，程式結束")
        return
    
    try:
        # 創建廣告替換器實例
        replacer = LinshibiAdReplacer(headless=HEADLESS_MODE, screen_id=screen_id)
        
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