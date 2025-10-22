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

# 載入 GIF 設定檔（主要設定檔）
try:
    from gif_config import *
    print("成功載入 gif_config.py 設定檔")
    print(f"SCREENSHOT_COUNT 設定: {SCREENSHOT_COUNT}")
    print(f"NEWS_COUNT 設定: {NEWS_COUNT}")
    print(f"IMAGE_USAGE_COUNT 設定: {IMAGE_USAGE_COUNT}")
    print(f"BUTTON_STYLE 設定: {BUTTON_STYLE}")
except ImportError:
    print("找不到 gif_config.py，請確保 gif_config.py 存在")
    exit(1)

# 確保必要變數總是有定義
if 'LINSHIBI_BASE_URL' not in globals():
    LINSHIBI_BASE_URL = "https://linshibi.com"

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
        self.prewarm_svg_rendering()
        
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
    
    def prewarm_svg_rendering(self):
        """預熱 SVG 渲染引擎，避免第一次按鈕顯示異常"""
        try:
            print("正在預熱 SVG 渲染引擎...")
            
            # 載入一個簡單的空白頁面來執行預熱
            self.driver.get("data:text/html,<html><body></body></html>")
            time.sleep(0.5)  # 等待頁面載入
            
            # 創建一個隱藏的預熱容器
            prewarm_script = """
                // 創建預熱容器
                var prewarmContainer = document.createElement('div');
                prewarmContainer.id = 'svg-prewarm-container';
                prewarmContainer.style.cssText = 'position:fixed;top:-100px;left:-100px;width:50px;height:50px;opacity:0;pointer-events:none;z-index:-1;';
                
                // 創建所有可能用到的 SVG 按鈕樣式進行預熱
                var svgButtons = [
                    // dots 樣式 (viewBox="0 -1 15 16")
                    '<svg width="15" height="15" viewBox="0 -1 15 16" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="7.5" cy="1.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="5.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="9.5" r="1.5" fill="#00aecd"/></svg>',
                    // cross 樣式
                    '<svg width="15" height="15" viewBox="0 -1 15 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 1L11 8M11 1L4 8" stroke="#00aecd" stroke-width="1.5" stroke-linecap="round"/></svg>',
                    // adchoices cross 樣式 (與 cross 相同)
                    '<svg width="15" height="15" viewBox="0 -1 15 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 1L11 8M11 1L4 8" stroke="#00aecd" stroke-width="1.5" stroke-linecap="round"/></svg>',
                    // adchoices_dots 樣式 (與 dots 相同)
                    '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="7.5" cy="1.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="5.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="9.5" r="1.5" fill="#00aecd"/></svg>',
                    // unified_info_button 樣式
                    '<svg width="15" height="15" viewBox="0 -1 15 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M7.5 -1.5a6 6 0 100 12 6 6 0 100-12m0 1a5 5 0 110 10 5 5 0 110-10zM6.625 8h1.75V3.5h-1.75zM7.5 0.75a1 1 0 100 2 1 1 0 100-2z" fill="#00aecd"/></svg>' 
                
                // 為每個 SVG 創建預熱元素
                svgButtons.forEach(function(svgHtml, index) {
                    var prewarmButton = document.createElement('div');
                    prewarmButton.innerHTML = svgHtml;
                    prewarmButton.style.cssText = 'position:absolute;top:0px;left:' + (index * 20) + 'px;width:15px;height:15px;background-color:rgba(255,255,255,1);';
                    prewarmContainer.appendChild(prewarmButton);
                });
                
                // 添加 AdChoices 圖片預熱
                var adChoicesImg = document.createElement('img');
                adChoicesImg.src = 'https://tpc.googlesyndication.com/pagead/images/adchoices/adchoices_blue_wb.png';
                adChoicesImg.style.cssText = 'position:absolute;top:0px;left:80px;width:15px;height:15px;';
                prewarmContainer.appendChild(adChoicesImg);
                
                // 添加到頁面
                document.body.appendChild(prewarmContainer);
                
                // 強制渲染
                prewarmContainer.offsetHeight;
                
                // 短暫延遲後移除預熱容器
                setTimeout(function() {
                    if (document.getElementById('svg-prewarm-container')) {
                        document.body.removeChild(prewarmContainer);
                    }
                }, 200);
                
                return 'SVG 預熱完成';
            """
            
            # 執行預熱腳本
            result = self.driver.execute_script(prewarm_script)
            print(f"✅ {result}")
            
            # 等待預熱完成
            time.sleep(0.3)
            
        except Exception as e:
            print(f"⚠️ SVG 預熱失敗，但不影響正常功能: {e}")

    def load_image_base64(self, image_path):
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"找不到圖片: {image_path}")
            
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def get_button_style(self):
        """根據配置返回按鈕樣式 - 參考 ad_replacer.py"""
        button_style = getattr(self, 'button_style', BUTTON_STYLE)
        
        # 計算動態按鈕位置
        actual_top = 0 + BUTTON_TOP_OFFSET
        
        # 統一的資訊按鈕樣式 - 使用新的結構設計
        unified_info_button = {
            "html": '<svg width="15" height="15" viewBox="0 -1 15 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M7.5 -1.5a6 6 0 100 12 6 6 0 100-12m0 1a5 5 0 110 10 5 5 0 110-10zM6.625 8h1.75V3.5h-1.75zM7.5 0.75a1 1 0 100 2 1 1 0 100-2z" fill="#00aecd"/></svg>',
            "style": f'position:absolute;top:{actual_top}px;right:17px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);cursor:pointer;border:none;padding:0;margin:0;box-sizing:border-box;border-radius:0;'
        }
        
        button_styles = {
            "dots": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 -1 15 16" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="7.5" cy="1.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="5.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="9.5" r="1.5" fill="#00aecd"/></svg>',
                    "style": f'position:absolute;top:{actual_top}px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;border:none;padding:0;margin:0;box-sizing:border-box;border-radius:0;'
                },
                "info_button": unified_info_button
            },
            "cross": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 -1 15 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 1L11 8M11 1L4 8" stroke="#00aecd" stroke-width="1.5" stroke-linecap="round"/></svg>',
                    "style": f'position:absolute;top:{actual_top}px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;border:none;padding:0;margin:0;box-sizing:border-box;border-radius:0;'
                },
                "info_button": unified_info_button
            },
            "adchoices": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 -1 15 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 1L11 8M11 1L4 8" stroke="#00aecd" stroke-width="1.5" stroke-linecap="round"/></svg>',
                    "style": f'position:absolute;top:{actual_top}px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;border:none;padding:0;margin:0;box-sizing:border-box;border-radius:0;'
                },
                "info_button": {
                    "html": '<img src="https://tpc.googlesyndication.com/pagead/images/adchoices/adchoices_blue_wb.png" style="display:block;width:auto;height:auto;max-width:15px;max-height:15px;object-fit:contain;border:none;padding:0;margin:auto;position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);">',
                    "style": f'position:absolute;top:{actual_top}px;right:17px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);cursor:pointer;border:none;padding:0;margin:0;box-sizing:border-box;border-radius:0;overflow:hidden;'
                }
            },
            "adchoices_dots": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="7.5" cy="1.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="5.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="9.5" r="1.5" fill="#00aecd"/></svg>',
                    "style": f'position:absolute;top:{actual_top}px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;border:none;padding:0;margin:0;box-sizing:border-box;border-radius:0;'
                },
                "info_button": {
                    "html": '<img src="https://tpc.googlesyndication.com/pagead/images/adchoices/adchoices_blue_wb.png" style="display:block;width:auto;height:auto;max-width:15px;max-height:15px;object-fit:contain;border:none;padding:0;margin:auto;position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);">',
                    "style": f'position:absolute;top:{actual_top}px;right:17px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);cursor:pointer;border:none;padding:0;margin:0;box-sizing:border-box;border-radius:0;overflow:hidden;'
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
        """掃描整個網頁尋找符合尺寸的廣告元素 - 針對 linshibi.com 優化，參考 nicklee 方式"""
        print(f"開始掃描整個網頁尋找 {target_width}x{target_height} 的廣告...")
        
        # 先嘗試特定的 linshibi.com 廣告選擇器 (保持原狀)
        specific_selectors = [
            # 核心 AdSense 容器（參考 linshibi_replace.py 的簡化邏輯）
            'ins.adsbygoogle',
            'div[id^="aswift_"]',
            'iframe[id^="aswift_"]',
            
            # 側邊欄廣告區塊
            'aside .textwidget ins.adsbygoogle',
            'aside .textwidget div[id^="aswift_"]',
            '.textwidget ins.adsbygoogle',
            '.textwidget div[id^="aswift_"]',
            
            # iframe 容器
            'iframe[width="160"][height="600"]',
            f'iframe[width="{target_width}"][height="{target_height}"]',
            
            # 廣告狀態相關
            'ins.adsbygoogle[data-adsbygoogle-status="done"]',
            
            # 廣告容器
            'aside .textwidget',
            '.textwidget',
            
            # nicklee 的進階選擇器 (新增)
            'div[class*="ad"]',
            'div[id*="ad"]',
            'div[class*="banner"]',
            'div[id*="banner"]',
            'div[class*="google"]',
            'div[id*="google"]',
            'img[src*="ad"]',
            'img[src*="banner"]',
            'img[src*="google"]',
            'iframe[src*="google"]',
            'iframe[src*="ad"]'
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
                        
                        # 檢查元素尺寸和詳細資訊（簡化版，參考 linshibi_replace.py）
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
                                
                                // 🚫 過濾 AdSense 控制面板和隱藏元素
                                // 檢查 aria-hidden 屬性
                                var ariaHidden = element.getAttribute('aria-hidden') === 'true';
                                
                                // 檢查是否為 AdSense 控制元素
                                var adSenseControlIds = ['mute_panel', 'abgac', 'abgcp', 'abgs', 'abgl', 'abgb'];
                                var adSenseControlClasses = ['mute_panel', 'abgac', 'abgcp', 'abgs', 'abgl', 'abgb'];
                                var isAdSenseControl = adSenseControlIds.some(function(controlId) {
                                    return id.includes(controlId) || className.includes(controlId);
                                });
                                
                                // 檢查位置是否在螢幕外（負座標或超出螢幕）
                                var isOffScreen = rect.left < -500 || rect.top < -500 || 
                                                rect.left > window.innerWidth + 500 || 
                                                rect.top > window.innerHeight + 500;
                                
                                // � 簡化過濾邏-輯 - 只過濾明顯的控制面板
                                if (ariaHidden || isAdSenseControl) {
                                    return null;  // 靜默過濾，不輸出除錯資訊
                                }
                                
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
                                
                                // 廣告特徵檢查（簡化版，參考 linshibi_replace.py）
                                var adKeywords = ['ad', 'advertisement', 'banner', 'google', 'ads', 'adsense', 'adsbygoogle'];
                                var hasAdKeyword = adKeywords.some(function(keyword) {
                                    return className.toLowerCase().includes(keyword) ||
                                           id.toLowerCase().includes(keyword) ||
                                           src.toLowerCase().includes(keyword);
                                });
                                
                                // 檢查是否為 Google AdSense 相關元素
                                var isGoogleAd = className.includes('adsbygoogle') ||
                                               id.includes('aswift') ||
                                               element.hasAttribute('data-ad-client') ||
                                               element.hasAttribute('data-ad-slot') ||
                                               src.includes('googleads') ||
                                               src.includes('googlesyndication') ||
                                               src.includes('doubleclick');
                                
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
                                
                                // 對於 linshibi.com，專注於兩種主要廣告尺寸（參考 linshibi_replace.py）
                                var isTargetSize = (width === targetWidth && height === targetHeight) ||
                                                 (Math.abs(width - targetWidth) <= 3 && Math.abs(height - targetHeight) <= 3);
                                
                                var isPrimaryAdSize = (width === 160 && height === 600);  // 側邊欄廣告
                                
                                // 🎯 採用 Nicklee 的簡化廣告驗證邏輯，但保留控制面板過濾
                                // 排除明顯的控制面板（保留 Linshibi 的優化）
                                var isNotControlPanel = !isAdSenseControl && !ariaHidden;
                                
                                // 📏 Nicklee 風格的寬鬆尺寸檢查
                                var isLikelyAd = (hasAdKeyword || parentHasAdKeyword || isAdElement ||
                                               // 🔓 寬鬆條件：特定尺寸通常是廣告 (來自 Nicklee)
                                               (width >= 120 && height >= 60) ||
                                               // 常見廣告尺寸
                                               (width === 728 && height === 90) ||
                                               (width === 970 && height === 90) ||
                                               (width === 300 && height === 250) ||
                                               (width === 336 && height === 280) ||
                                               (width === 160 && height === 600) ||
                                               (width === 320 && height === 50)) &&
                                               isNotControlPanel;  // 但仍然排除控制面板
                                
                                // 🔍 簡化的除錯資訊
                                if (width >= 100 && height >= 50) {  // 只記錄可能的廣告尺寸
                                    console.log('🔍 檢查元素:', tagName, className.substring(0, 20), width + 'x' + height, 
                                               'ad-features:', (hasAdKeyword || parentHasAdKeyword || isAdElement), 
                                               'not-control:', isNotControlPanel);
                                }
                                
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
        """替換廣告內容 - 參考 nicklee 的實現方式"""
        try:
            # 取得元素 tag 與 class 以決定尺寸容差策略 (參考 nicklee)
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
            
            # 檢查是否符合目標尺寸（<ins> 保持嚴格，其餘放寬 ±5px，參考 nicklee）
            width_diff = abs(original_info['width'] - target_width)
            height_diff = abs(original_info['height'] - target_height)
            
            if is_ins_like:
                if width_diff > 2 or height_diff > 2:  # 允許 ±2px 誤差
                    print(f"❌ ins 元素尺寸不匹配: 期望 {target_width}x{target_height}, 實際 {original_info['width']}x{original_info['height']} (差異: {width_diff}x{height_diff})")
                    return False
            else:
                if width_diff > 5 or height_diff > 5:
                    print(f"❌ 元素尺寸不匹配: 期望 {target_width}x{target_height}, 實際 {original_info['width']}x{original_info['height']} (差異: {width_diff}x{height_diff})")
                    return False
            
            print(f"✅ 尺寸匹配: {original_info['width']}x{original_info['height']} ≈ {target_width}x{target_height} (差異: {width_diff}x{height_diff})")
            
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
            
            # 替換廣告內容 (參考 nicklee 的完整實現)
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
                
                console.log('🔄 開始替換廣告:', targetWidth + 'x' + targetHeight);
                console.log('📦 容器元素:', container.tagName, container.className, container.id);
                console.log('📏 容器尺寸:', container.getBoundingClientRect().width + 'x' + container.getBoundingClientRect().height);
                
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
                
                // 方法1: 處理 ins 元素 (linshibi.com 的主要廣告類型)
                if (container.tagName.toLowerCase() === 'ins') {
                    console.log('🎯 處理 ins 廣告元素');
                    console.log('📋 原始內容長度:', container.innerHTML.length);
                    console.log('📋 原始內容預覽:', container.innerHTML.substring(0, 100) + '...');
                    
                    // 保存原始內容
                    if (!container.getAttribute('data-original-content')) {
                        container.setAttribute('data-original-content', container.innerHTML);
                        console.log('💾 已保存原始內容');
                    }
                    
                    // 創建替換圖片
                    var newImg = document.createElement('img');
                    newImg.src = newImageSrc;
                    newImg.style.width = targetWidth + 'px';
                    newImg.style.height = targetHeight + 'px';
                    newImg.style.objectFit = 'contain';
                    newImg.style.display = 'block';
                    newImg.style.margin = '0';
                    newImg.style.padding = '0';
                    newImg.setAttribute('data-replacement-img', 'true');
                    
                    console.log('🖼️ 創建替換圖片:', targetWidth + 'x' + targetHeight);
                    
                    // 清空並替換內容
                    container.innerHTML = '';
                    container.appendChild(newImg);
                    
                    // 確保容器樣式
                    container.style.position = 'relative';
                    container.style.display = 'block';
                    container.style.overflow = 'visible';
                    container.style.border = 'none';
                    container.style.padding = '0';
                    container.style.margin = '0 auto';
                    container.style.boxSizing = 'border-box';
                    
                    // 🎯 處理廣告置中 - 檢查父容器並設定置中
                    var parentElement = container.parentElement;
                    if (parentElement) {
                        // 如果父容器是 textwidget 或類似的容器，設定置中
                        var parentClass = parentElement.className || '';
                        if (parentClass.includes('textwidget') || parentClass.includes('widget')) {
                            parentElement.style.textAlign = 'center';
                        }
                        
                        // 確保容器本身也置中
                        container.style.margin = '0 auto';
                        container.style.display = 'block';
                    }
                    
                    replacedCount++;
                    console.log('✅ ins 元素替換成功，replacedCount:', replacedCount);
                    
                    // 添加按鈕
                    if (!isNoneMode && closeButtonHtml && infoButtonHtml) {
                        console.log('🔘 添加控制按鈕');
                        if (closeButtonHtml) {
                            var closeButton = document.createElement('div');
                            closeButton.id = 'close_button';
                            closeButton.innerHTML = closeButtonHtml;
                            closeButton.style.cssText = closeButtonStyle;
                            container.appendChild(closeButton);
                            console.log('✅ 關閉按鈕已添加');
                        }
                        
                        if (infoButtonHtml) {
                            var abgb = document.createElement('div');
                            abgb.id = 'abgb';
                            abgb.className = 'abgb';
                            abgb.innerHTML = infoButtonHtml;
                            abgb.style.cssText = infoButtonStyle;
                            container.appendChild(abgb);
                            console.log('✅ 資訊按鈕已添加');
                        }
                    } else {
                        console.log('⚠️ 跳過按鈕添加 (none模式或按鈕HTML為空)');
                    }
                }
                
                // 方法2: 替換img標籤的src
                var imgs = container.querySelectorAll('img');
                for (var i = 0; i < imgs.length; i++) {
                    var img = imgs[i];
                    // 排除Google廣告控制按鈕和我們剛創建的替換圖片
                    var imgRect = img.getBoundingClientRect();
                    var isControlButton = imgRect.width < 50 || imgRect.height < 50 || 
                                         img.className.includes('abg') || 
                                         img.id.includes('abg') ||
                                         img.src.includes('googleads') ||
                                         img.src.includes('googlesyndication') ||
                                         img.src.includes('adchoices') ||
                                         img.hasAttribute('data-replacement-img');
                    
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
                
                // 方法3: 處理iframe
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
                        closeButton.style.cssText = 'position:absolute;top:' + (iframeRect.top - container.getBoundingClientRect().top + 1) + 'px;right:' + (container.getBoundingClientRect().right - iframeRect.right + 1) + 'px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);';
                        
                        // 資訊按鈕
                        var abgb = document.createElement('div');
                        abgb.id = 'abgb';
                        abgb.className = 'abgb';
                        abgb.innerHTML = infoButtonHtml;
                        abgb.style.cssText = 'position:absolute;top:' + (iframeRect.top - container.getBoundingClientRect().top + 1) + 'px;right:' + (container.getBoundingClientRect().right - iframeRect.right + 17) + 'px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);line-height:0;';
                        
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
                
                console.log('🎉 廣告替換完成，替換了', replacedCount, '個元素');
                console.log('📊 最終結果:', replacedCount > 0 ? '成功' : '失敗');
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
                
                // 還原 ins 元素的原始內容
                var originalContent = container.getAttribute('data-original-content');
                if (originalContent) {
                    container.innerHTML = originalContent;
                    container.removeAttribute('data-original-content');
                    console.log('✅ 已還原 ins 元素內容');
                }
                
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
            
            # 等待並處理動態廣告
            print("🔄 檢查動態廣告...")
            self.wait_for_dynamic_ads()
            
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
                            
                            # 改進的滾動邏輯
                            try:
                                print("📍 準備滾動到廣告位置...")
                                
                                # 先滾動到頁面底部，幫助判斷位置
                                print("🔄 先滾動到頁面底部...")
                                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                time.sleep(1)
                                
                                # 獲取廣告元素的精確位置
                                scroll_info = self.driver.execute_script("""
                                    var element = arguments[0];
                                    var rect = element.getBoundingClientRect();
                                    var viewportHeight = window.innerHeight;
                                    var documentHeight = document.body.scrollHeight;
                                    var currentScrollY = window.pageYOffset;
                                    
                                    // 計算元素在文檔中的絕對位置
                                    var elementTop = rect.top + currentScrollY;
                                    var elementCenter = elementTop + (rect.height / 2);
                                    
                                    // 尋找按鈕位置（關閉按鈕或資訊按鈕）
                                    var closeButton = element.querySelector('#close_button');
                                    var infoButton = element.querySelector('#abgb');
                                    var button = closeButton || infoButton;
                                    
                                    var buttonTop = elementTop;
                                    if (button) {
                                        var buttonRect = button.getBoundingClientRect();
                                        buttonTop = buttonRect.top + currentScrollY;
                                        console.log('🔘 找到按鈕，位置:', buttonTop);
                                    } else {
                                        console.log('⚠️ 未找到按鈕，使用廣告元素頂部');
                                    }
                                    
                                    // 計算滾動位置，讓按鈕出現在螢幕上方約 10% 的位置
                                    var targetScrollY = buttonTop - (viewportHeight * 0.1);
                                    
                                    // 確保滾動位置在有效範圍內
                                    targetScrollY = Math.max(0, Math.min(targetScrollY, documentHeight - viewportHeight));
                                    
                                    return {
                                        elementTop: elementTop,
                                        elementCenter: elementCenter,
                                        buttonTop: buttonTop,
                                        targetScrollY: targetScrollY,
                                        viewportHeight: viewportHeight,
                                        documentHeight: documentHeight,
                                        currentScrollY: currentScrollY,
                                        hasButton: button !== null,
                                        elementRect: {
                                            width: Math.round(rect.width),
                                            height: Math.round(rect.height),
                                            top: Math.round(rect.top),
                                            left: Math.round(rect.left)
                                        }
                                    };
                                """, ad_info['element'])
                                
                                print(f"📊 滾動資訊:")
                                print(f"   廣告位置: {scroll_info['elementTop']:.0f}px (中心: {scroll_info['elementCenter']:.0f}px)")
                                print(f"   按鈕位置: {scroll_info['buttonTop']:.0f}px (找到按鈕: {scroll_info['hasButton']})")
                                print(f"   目標滾動: {scroll_info['targetScrollY']:.0f}px (按鈕在螢幕上方10%)")
                                print(f"   螢幕高度: {scroll_info['viewportHeight']}px")
                                print(f"   頁面高度: {scroll_info['documentHeight']}px")
                                
                                # 執行滾動
                                self.driver.execute_script(f"window.scrollTo(0, {scroll_info['targetScrollY']});")
                                print(f"✅ 已滾動到位置: {scroll_info['targetScrollY']:.0f}px")
                                
                                # 等待滾動完成
                                time.sleep(2)
                                
                                # 驗證廣告是否在可視區域
                                final_check = self.driver.execute_script("""
                                    var element = arguments[0];
                                    var rect = element.getBoundingClientRect();
                                    var viewportHeight = window.innerHeight;
                                    
                                    var isVisible = rect.top >= 0 && 
                                                   rect.bottom <= viewportHeight && 
                                                   rect.width > 0 && 
                                                   rect.height > 0;
                                    
                                    var isPartiallyVisible = rect.bottom > 0 && 
                                                            rect.top < viewportHeight && 
                                                            rect.width > 0 && 
                                                            rect.height > 0;
                                    
                                    return {
                                        isVisible: isVisible,
                                        isPartiallyVisible: isPartiallyVisible,
                                        rect: {
                                            top: Math.round(rect.top),
                                            bottom: Math.round(rect.bottom),
                                            left: Math.round(rect.left),
                                            right: Math.round(rect.right)
                                        }
                                    };
                                """, ad_info['element'])
                                
                                if final_check['isPartiallyVisible']:
                                    visibility_status = "完全可見" if final_check['isVisible'] else "部分可見"
                                    print(f"✅ 廣告現在{visibility_status}")
                                    print(f"   位置: top={final_check['rect']['top']}, bottom={final_check['rect']['bottom']}")
                                else:
                                    print(f"⚠️ 廣告仍不在可視區域")
                                    print(f"   位置: top={final_check['rect']['top']}, bottom={final_check['rect']['bottom']}")
                                
                            except Exception as e:
                                print(f"滾動到廣告位置失敗: {e}")
                            
                            # 驗證廣告替換是否成功
                            print("🔍 驗證廣告替換效果...")
                            replacement_check = self.driver.execute_script("""
                                var element = arguments[0];
                                var checkResults = {
                                    replacedImages: 0,
                                    replacedIframes: 0,
                                    replacedBackgrounds: 0,
                                    addedButtons: 0,
                                    details: []
                                };
                                
                                // 檢查替換的圖片
                                var imgs = element.querySelectorAll('img[src^="data:image/jpeg;base64"]');
                                checkResults.replacedImages = imgs.length;
                                if (imgs.length > 0) {
                                    checkResults.details.push('替換了 ' + imgs.length + ' 個圖片');
                                }
                                
                                // 檢查隱藏的 iframe
                                var hiddenIframes = element.querySelectorAll('iframe[style*="visibility: hidden"]');
                                checkResults.replacedIframes = hiddenIframes.length;
                                if (hiddenIframes.length > 0) {
                                    checkResults.details.push('隱藏了 ' + hiddenIframes.length + ' 個 iframe');
                                }
                                
                                // 檢查替換圖片元素
                                var replacementImgs = element.querySelectorAll('img[data-replacement-img="true"]');
                                if (replacementImgs.length > 0) {
                                    checkResults.details.push('添加了 ' + replacementImgs.length + ' 個替換圖片');
                                }
                                
                                // 檢查背景圖片
                                var style = window.getComputedStyle(element);
                                if (style.backgroundImage && style.backgroundImage.includes('data:image/jpeg;base64')) {
                                    checkResults.replacedBackgrounds = 1;
                                    checkResults.details.push('設置了容器背景圖片');
                                }
                                
                                // 檢查按鈕
                                var buttons = element.querySelectorAll('#close_button, #abgb');
                                checkResults.addedButtons = buttons.length;
                                if (buttons.length > 0) {
                                    checkResults.details.push('添加了 ' + buttons.length + ' 個控制按鈕');
                                }
                                
                                return checkResults;
                            """, ad_info['element'])
                            
                            print(f"📊 替換驗證結果:")
                            for detail in replacement_check['details']:
                                print(f"   ✅ {detail}")
                            
                            total_replacements_check = (replacement_check['replacedImages'] + 
                                                      replacement_check['replacedIframes'] + 
                                                      replacement_check['replacedBackgrounds'])
                            
                            if total_replacements_check > 0:
                                print(f"✅ 廣告替換成功！共 {total_replacements_check} 個元素被替換")
                            else:
                                print("⚠️ 警告：沒有檢測到成功的廣告替換")
                            
                            # 截圖
                            print("📸 準備截圖...")
                            time.sleep(3)  # 等待頁面穩定
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
    
    def wait_for_dynamic_ads(self, timeout=10):
        """等待動態廣告載入完成"""
        print("⏳ 等待動態廣告載入...")
        
        # 等待 AdSense 廣告載入
        try:
            self.driver.execute_script("""
                // 等待 AdSense 腳本載入
                return new Promise((resolve) => {
                    var checkAdsense = function() {
                        if (window.adsbygoogle && window.adsbygoogle.loaded) {
                            resolve(true);
                        } else if (document.querySelectorAll('iframe[id^="aswift_"]').length > 0) {
                            resolve(true);
                        } else {
                            setTimeout(checkAdsense, 500);
                        }
                    };
                    checkAdsense();
                    // 最多等待 10 秒
                    setTimeout(() => resolve(false), 10000);
                });
            """)
            print("✅ AdSense 廣告載入完成")
        except:
            print("⚠️ AdSense 廣告載入檢查失敗")
        
        # 等待其他動態廣告載入
        time.sleep(3)
        
        # 檢查廣告是否真的載入了
        ad_count = len(self.driver.find_elements(By.CSS_SELECTOR, 
            'iframe[id^="aswift_"], div[class^="ns-"], div#bnr, ins.adsbygoogle'))
        print(f"🎯 檢測到 {ad_count} 個廣告元素")
        
        return ad_count > 0
    
    def handle_dynamic_ads(self, target_width, target_height):
        """專門處理動態廣告的替換"""
        print(f"🔄 開始處理動態廣告 ({target_width}x{target_height})")
        
        # 等待動態廣告載入
        self.wait_for_dynamic_ads()
        
        # 針對不同類型的動態廣告使用不同策略
        replaced_count = 0
        
        # 1. 處理 AdSense iframe 廣告
        adsense_iframes = self.driver.find_elements(By.CSS_SELECTOR, 'iframe[id^="aswift_"]')
        for iframe in adsense_iframes:
            try:
                # 檢查 iframe 尺寸
                size = self.driver.execute_script("""
                    var iframe = arguments[0];
                    var rect = iframe.getBoundingClientRect();
                    return {width: Math.round(rect.width), height: Math.round(rect.height)};
                """, iframe)
                
                if (abs(size['width'] - target_width) <= 2 and 
                    abs(size['height'] - target_height) <= 2):
                    
                    # 替換 iframe 的父容器
                    parent = iframe.find_element(By.XPATH, '..')
                    if self.replace_iframe_ad(parent, target_width, target_height):
                        replaced_count += 1
                        print(f"✅ 成功替換 AdSense iframe 廣告")
            except Exception as e:
                print(f"⚠️ 處理 AdSense iframe 失敗: {e}")
        
        # 2. 處理 Google 展示廣告 (ns- 類型)
        ns_ads = self.driver.find_elements(By.CSS_SELECTOR, 'div[class^="ns-"]')
        for ad in ns_ads:
            try:
                if self.replace_ns_ad(ad, target_width, target_height):
                    replaced_count += 1
                    print(f"✅ 成功替換 Google 展示廣告")
            except Exception as e:
                print(f"⚠️ 處理 Google 展示廣告失敗: {e}")
        
        # 3. 處理 Criteo 廣告
        criteo_ads = self.driver.find_elements(By.CSS_SELECTOR, 'div#bnr, div.isSetup')
        for ad in criteo_ads:
            try:
                if self.replace_criteo_ad(ad, target_width, target_height):
                    replaced_count += 1
                    print(f"✅ 成功替換 Criteo 廣告")
            except Exception as e:
                print(f"⚠️ 處理 Criteo 廣告失敗: {e}")
        
        print(f"🎯 動態廣告處理完成，共替換 {replaced_count} 個廣告")
        return replaced_count > 0
    
    def replace_iframe_ad(self, container, target_width, target_height):
        """替換 iframe 廣告"""
        try:
            # 獲取替換圖片
            image_data = self.get_replacement_image(target_width, target_height)
            if not image_data:
                return False
            
            # 替換整個容器的內容
            success = self.driver.execute_script("""
                var container = arguments[0];
                var imageBase64 = arguments[1];
                var width = arguments[2];
                var height = arguments[3];
                
                // 清空容器內容
                container.innerHTML = '';
                
                // 創建新的廣告內容
                container.style.width = width + 'px';
                container.style.height = height + 'px';
                container.style.position = 'relative';
                container.style.overflow = 'visible';
                container.style.border = 'none';
                container.style.padding = '0';
                container.style.boxSizing = 'border-box';
                container.style.background = '#f0f0f0';
                
                // 🎯 處理廣告置中
                container.style.margin = '0 auto';
                container.style.display = 'block';
                var parentElement = container.parentElement;
                if (parentElement) {
                    var parentClass = parentElement.className || '';
                    if (parentClass.includes('textwidget') || parentClass.includes('widget')) {
                        parentElement.style.textAlign = 'center';
                    }
                }
                
                // 添加替換圖片
                var img = document.createElement('img');
                img.src = 'data:image/jpeg;base64,' + imageBase64;
                img.style.width = '100%';
                img.style.height = '100%';
                img.style.objectFit = 'cover';
                container.appendChild(img);
                
                return true;
            """, container, image_data, target_width, target_height)
            
            return success
        except Exception as e:
            print(f"替換 iframe 廣告失敗: {e}")
            return False
    
    def replace_ns_ad(self, element, target_width, target_height):
        """替換 ns- 類型的 Google 展示廣告"""
        try:
            # 檢查元素尺寸
            size = self.driver.execute_script("""
                var element = arguments[0];
                var rect = element.getBoundingClientRect();
                return {width: Math.round(rect.width), height: Math.round(rect.height)};
            """, element)
            
            if (abs(size['width'] - target_width) > 5 or 
                abs(size['height'] - target_height) > 5):
                return False
            
            # 獲取替換圖片
            image_data = self.get_replacement_image(target_width, target_height)
            if not image_data:
                return False
            
            # 替換內容
            success = self.driver.execute_script("""
                var element = arguments[0];
                var imageBase64 = arguments[1];
                var width = arguments[2];
                var height = arguments[3];
                
                // 保持原有樣式但替換內容
                element.innerHTML = '';
                element.style.backgroundImage = 'url(data:image/jpeg;base64,' + imageBase64 + ')';
                element.style.backgroundSize = 'contain';
                element.style.backgroundPosition = 'center';
                element.style.width = width + 'px';
                element.style.height = height + 'px';
                
                // 🎯 處理廣告置中
                element.style.margin = '0 auto';
                element.style.display = 'block';
                var parentElement = element.parentElement;
                if (parentElement) {
                    var parentClass = parentElement.className || '';
                    if (parentClass.includes('textwidget') || parentClass.includes('widget')) {
                        parentElement.style.textAlign = 'center';
                    }
                }
                
                return true;
            """, element, image_data, target_width, target_height)
            
            return success
        except Exception as e:
            print(f"替換 ns- 廣告失敗: {e}")
            return False
    
    def replace_criteo_ad(self, element, target_width, target_height):
        """替換 Criteo 廣告"""
        try:
            # 獲取替換圖片
            image_data = self.get_replacement_image(target_width, target_height)
            if not image_data:
                return False
            
            # 替換 Criteo 廣告內容
            success = self.driver.execute_script("""
                var element = arguments[0];
                var imageBase64 = arguments[1];
                var width = arguments[2];
                var height = arguments[3];
                
                // 清空並重新設置
                element.innerHTML = '';
                element.style.width = width + 'px';
                element.style.height = height + 'px';
                element.style.position = 'relative';
                element.style.overflow = 'visible';
                element.style.border = 'none';
                element.style.padding = '0';
                element.style.boxSizing = 'border-box';
                
                // 🎯 處理廣告置中
                element.style.margin = '0 auto';
                element.style.display = 'block';
                var parentElement = element.parentElement;
                if (parentElement) {
                    var parentClass = parentElement.className || '';
                    if (parentClass.includes('textwidget') || parentClass.includes('widget')) {
                        parentElement.style.textAlign = 'center';
                    }
                }
                
                // 添加替換圖片
                var img = document.createElement('img');
                img.src = 'data:image/jpeg;base64,' + imageBase64;
                img.style.width = '100%';
                img.style.height = '100%';
                img.style.objectFit = 'cover';
                element.appendChild(img);
                
                return true;
            """, element, image_data, target_width, target_height)
            
            return success
        except Exception as e:
            print(f"替換 Criteo 廣告失敗: {e}")
            return False
    
    def detect_ad_type(self, element):
        """檢測廣告類型"""
        try:
            ad_info = self.driver.execute_script("""
                var element = arguments[0];
                var tagName = element.tagName.toLowerCase();
                var className = element.className || '';
                var id = element.id || '';
                
                // 檢查是否為 AdSense iframe 相關
                if (id.includes('aswift') || 
                    (tagName === 'iframe' && element.src && element.src.includes('googleads')) ||
                    (tagName === 'div' && id.includes('aswift'))) {
                    return 'adsense_iframe';
                }
                
                // 檢查是否為 Google 展示廣告 (ns- 類型)
                if (className.includes('ns-') || id.includes('ns-')) {
                    return 'google_display';
                }
                
                // 檢查是否為 Criteo 廣告
                if (id === 'bnr' || className.includes('isSetup') ||
                    element.querySelector('a[href*="criteo.com"]') ||
                    element.querySelector('a[href*="googleadservices.com"]')) {
                    return 'criteo';
                }
                
                // 檢查父元素的特徵
                var parent = element.parentElement;
                if (parent) {
                    var parentClass = parent.className || '';
                    var parentId = parent.id || '';
                    
                    if (parentId.includes('aswift') || parentClass.includes('aswift')) {
                        return 'adsense_iframe';
                    }
                    
                    if (parentClass.includes('ns-') || parentId.includes('ns-')) {
                        return 'google_display';
                    }
                }
                
                return 'generic';
            """, element)
            
            return ad_info
        except Exception as e:
            print(f"檢測廣告類型失敗: {e}")
            return 'generic'
    
    def replace_generic_ad(self, element, image_data, target_width, target_height):
        """通用廣告替換策略 - 使用原有的替換邏輯"""
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
            
            # 執行通用廣告替換 - 修正版本
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
                
                console.log('🔄 開始替換廣告:', targetWidth + 'x' + targetHeight);
                console.log('📦 容器元素:', container.tagName, container.className, container.id);
                
                // 確保 container 是 relative
                if (window.getComputedStyle(container).position === 'static') {
                    container.style.position = 'relative';
                }
                
                // 移除舊按鈕
                var oldButtons = container.querySelectorAll('#close_button, #abgb, [id^="close_button_"], [id^="abgb_"]');
                oldButtons.forEach(function(btn) { btn.remove(); });
                
                var replacedCount = 0;
                var newImageSrc = 'data:image/jpeg;base64,' + imageBase64;
                
                console.log('🖼️ 新圖片 URL 長度:', newImageSrc.length);
                
                // 方法1: 替換 img 標籤
                var imgs = container.querySelectorAll('img');
                console.log('🖼️ 找到', imgs.length, '個圖片元素');
                
                for (var i = 0; i < imgs.length; i++) {
                    var img = imgs[i];
                    var imgRect = img.getBoundingClientRect();
                    
                    console.log('檢查圖片', i + 1, ':', {
                        src: img.src.substring(0, 50) + '...',
                        size: Math.round(imgRect.width) + 'x' + Math.round(imgRect.height),
                        visible: imgRect.width > 0 && imgRect.height > 0
                    });
                    
                    // 排除控制按鈕
                    var isControlButton = imgRect.width < 50 || imgRect.height < 50 || 
                                         img.className.includes('abg') || 
                                         img.id.includes('abg') ||
                                         img.src.includes('googleads') ||
                                         img.src.includes('googlesyndication') ||
                                         img.src.includes('adchoices') ||
                                         img.alt.includes('關閉') ||
                                         img.alt.includes('close');
                    
                    if (!isControlButton && img.src && !img.src.startsWith('data:')) {
                        console.log('✅ 替換圖片:', img.src.substring(0, 50));
                        
                        // 保存原始 src
                        if (!img.getAttribute('data-original-src')) {
                            img.setAttribute('data-original-src', img.src);
                        }
                        
                        // 替換圖片
                        img.src = newImageSrc;
                        img.style.width = '100%';
                        img.style.height = 'auto';
                        img.style.objectFit = 'cover';
                        img.style.display = 'block';
                        
                        replacedCount++;
                        console.log('🎯 成功替換圖片', replacedCount);
                    }
                }
                
                // 方法2: 處理 iframe
                var iframes = container.querySelectorAll('iframe');
                console.log('🖼️ 找到', iframes.length, '個 iframe 元素');
                
                for (var i = 0; i < iframes.length; i++) {
                    var iframe = iframes[i];
                    var iframeRect = iframe.getBoundingClientRect();
                    
                    console.log('檢查 iframe', i + 1, ':', {
                        id: iframe.id,
                        src: iframe.src.substring(0, 50) + '...',
                        size: Math.round(iframeRect.width) + 'x' + Math.round(iframeRect.height)
                    });
                    
                    if (iframeRect.width > 0 && iframeRect.height > 0) {
                        // 隱藏 iframe
                        iframe.style.visibility = 'hidden';
                        iframe.setAttribute('data-original-visibility', 'visible');
                        
                        // 創建替換圖片
                        var newImg = document.createElement('img');
                        newImg.src = newImageSrc;
                        newImg.style.position = 'absolute';
                        newImg.style.top = (iframeRect.top - container.getBoundingClientRect().top) + 'px';
                        newImg.style.left = (iframeRect.left - container.getBoundingClientRect().left) + 'px';
                        newImg.style.width = Math.round(iframeRect.width) + 'px';
                        newImg.style.height = Math.round(iframeRect.height) + 'px';
                        newImg.style.objectFit = 'cover';
                        newImg.style.zIndex = '1';
                        newImg.setAttribute('data-replacement-img', 'true');
                        
                        container.appendChild(newImg);
                        replacedCount++;
                        
                        console.log('✅ 替換 iframe 為圖片');
                    }
                }
                
                // 方法3: 處理背景圖片
                if (replacedCount === 0) {
                    console.log('🎨 嘗試設置背景圖片');
                    var style = window.getComputedStyle(container);
                    
                    // 保存原始背景
                    if (!container.getAttribute('data-original-bg')) {
                        container.setAttribute('data-original-bg', style.backgroundImage);
                    }
                    
                    // 設置新背景
                    container.style.backgroundImage = 'url(' + newImageSrc + ')';
                    container.style.backgroundSize = 'contain';
                    container.style.backgroundPosition = 'center';
                    container.style.backgroundRepeat = 'no-repeat';
                    replacedCount = 1;
                    
                    console.log('✅ 設置容器背景圖片');
                }
                
                // 添加按鈕
                if (!isNoneMode && (closeButtonHtml || infoButtonHtml)) {
                    console.log('🔘 添加控制按鈕');
                    
                    if (closeButtonHtml) {
                        var closeButton = document.createElement('div');
                        closeButton.id = 'close_button';
                        closeButton.innerHTML = closeButtonHtml;
                        closeButton.style.cssText = closeButtonStyle;
                        container.appendChild(closeButton);
                        console.log('✅ 關閉按鈕已添加');
                    }
                    
                    if (infoButtonHtml) {
                        var infoButton = document.createElement('div');
                        infoButton.id = 'abgb';
                        infoButton.innerHTML = infoButtonHtml;
                        infoButton.style.cssText = infoButtonStyle;
                        container.appendChild(infoButton);
                        console.log('✅ 資訊按鈕已添加');
                    }
                }
                
                console.log('🎉 廣告替換完成，替換了', replacedCount, '個元素');
                return replacedCount > 0;
            """, element, image_data, target_width, target_height, close_button_html, close_button_style, info_button_html, info_button_style, is_none_mode)
            
            if success:
                print(f"✅ 成功替換通用廣告 {original_info['width']}x{original_info['height']}")
                return True
            else:
                print(f"❌ 通用廣告替換失敗 {original_info['width']}x{original_info['height']}")
                return False
                
        except Exception as e:
            print(f"廣告替換失敗: {e}")
            return False
    
    def get_replacement_image(self, width, height):
        """獲取指定尺寸的替換圖片"""
        try:
            # 尋找匹配尺寸的圖片
            for image_info in self.replace_images:
                if image_info['width'] == width and image_info['height'] == height:
                    return self.load_image_base64(image_info['path'])
            
            # 如果沒有完全匹配的，使用預設圖片
            if hasattr(self, 'replace_images') and self.replace_images:
                return self.load_image_base64(self.replace_images[0]['path'])
            
            return None
        except Exception as e:
            print(f"獲取替換圖片失敗: {e}")
            return None
    
    def get_linshibi_article_urls(self, base_url, count):
        """獲取 linshibi.com 文章 URLs - 參考 linshibi_replace.py 的成功模式"""
        try:
            print(f"正在訪問 {base_url}...")
            self.driver.get(base_url)
            time.sleep(WAIT_TIME * 2)  # 網站需要更多載入時間
            
            # 等待頁面完全載入
            self.driver.execute_script("return document.readyState") == "complete"
            
            # 按順序獲取文章連結
            blog_urls = []
            processed_urls = set()  # 記錄已處理的URL，避免重複
            
            print("開始按順序搜尋文章連結...")
            
            # 使用 JavaScript 獲取文章連結（參考 linshibi_replace.py 模式）
            article_links = self.driver.execute_script("""
                var links = [];
                
                // 方法1: 尋找 content 區塊內的文章
                var contentDiv = document.querySelector('#content.col-sm-9') || document.querySelector('#content');
                if (contentDiv) {
                    // 尋找文章標題連結
                    var titleLinks = contentDiv.querySelectorAll('h1 a, h2 a, h3 a, .entry-title a, .post-title a');
                    for (var i = 0; i < titleLinks.length; i++) {
                        var link = titleLinks[i];
                        if (link.href) {
                            links.push({
                                url: link.href,
                                title: link.textContent.trim(),
                                order: i,
                                source: 'title_link'
                            });
                        }
                    }
                    
                    // 尋找文章內容連結
                    var contentLinks = contentDiv.querySelectorAll('a[href*="linshibi.com"], a[href^="/"]');
                    for (var i = 0; i < contentLinks.length; i++) {
                        var link = contentLinks[i];
                        if (link.href && link.textContent.trim()) {
                            links.push({
                                url: link.href,
                                title: link.textContent.trim(),
                                order: i + 1000,  // 較低優先級
                                source: 'content_link'
                            });
                        }
                    }
                }
                
                // 方法2: 如果 content 區塊沒找到，搜尋整個頁面
                if (links.length === 0) {
                    var allLinks = document.querySelectorAll('a[href*="linshibi.com"], a[href^="/"]');
                    for (var i = 0; i < allLinks.length; i++) {
                        var link = allLinks[i];
                        if (link.href && link.textContent.trim()) {
                            links.push({
                                url: link.href,
                                title: link.textContent.trim(),
                                order: i + 2000,  // 最低優先級
                                source: 'all_links'
                            });
                        }
                    }
                }
                
                return links;
            """)
            
            print(f"找到 {len(article_links)} 個潛在連結")
            
            # 按順序處理文章連結
            for link_info in article_links:
                url = link_info['url']
                title = link_info['title']
                source = link_info['source']
                
                # 處理相對路徑
                if url.startswith('/'):
                    url = 'https://linshibi.com' + url
                
                # 精確的分頁導航連結檢查（保留 ?p= 文章連結）
                is_pagination = False
                
                # 簡化的分頁檢查（針對 linshibi.com 的 ?paged= 格式）
                title_stripped = title.strip()
                
                # 檢查是否為純數字標題（頁碼）
                is_numeric_title = title_stripped.isdigit() and len(title_stripped) <= 2
                
                # 檢查URL是否包含 paged 參數
                has_paged_param = 'paged=' in url.lower()
                
                # 如果是純數字標題或包含 paged 參數，就是分頁連結
                is_pagination = is_numeric_title or has_paged_param
                
                # 檢查URL是否有效且未重複，並排除分頁連結
                if (url and 
                    url != base_url and
                    url not in processed_urls and
                    not is_pagination and
                    self._is_valid_article_url(url)):
                    
                    blog_urls.append(url)
                    processed_urls.add(url)
                    print(f"第 {len(blog_urls)} 個文章: {title[:50]}...")
                    print(f"  URL: {url} (來源: {source})")
                    
                    # 達到所需數量就停止
                    if len(blog_urls) >= count:
                        break
                elif is_pagination:
                    print(f"⏭️ 跳過分頁連結: {title[:30]}... → {url}")
            
            print(f"總共獲取到 {len(blog_urls)} 個按順序排列的文章連結")
            
            # 如果沒找到任何文章，返回備用 URL
            if not blog_urls:
                print("未找到任何文章連結，使用備用 URL")
                blog_urls = [
                    "https://linshibi.com/?p=47121",
                    "https://linshibi.com/?p=47120", 
                    "https://linshibi.com/?p=47119"
                ]
            
            return blog_urls
            
        except Exception as e:
            print(f"獲取文章連結失敗: {e}")
            return [
                "https://linshibi.com/?p=47121",
                "https://linshibi.com/?p=47120",
                "https://linshibi.com/?p=47119"
            ]
    
    def _is_valid_article_url(self, url):
        """檢查是否為有效的文章 URL - 參考 linshibi_replace.py 的邏輯"""
        if not url or not url.startswith('https://linshibi.com'):
            return False
        
        # 排除明顯不需要的 URL（簡化版，專注於 linshibi.com）
        exclude_patterns = [
            '#', 'javascript:', 'mailto:', 
            '/feed', '.xml', '.rss',
            '/wp-admin', '/wp-content',
            '.jpg', '.png', '.gif', '.pdf',
            
            # linshibi.com 的分頁格式
            'paged=',  # ?paged=2, &paged=3 等
            
            # 其他非文章頁面
            '/category/', '/cat/', '/tag/',
            '/about', '/contact', '/privacy',
            '/terms', '/sitemap', '/search'
        ]
        
        for pattern in exclude_patterns:
            if pattern in url.lower():
                return False
        
        # 排除首頁和分類頁面
        if url == 'https://linshibi.com' or url == 'https://linshibi.com/':
            return False
            
        # 更寬鬆的檢查條件
        # 包含以下任一條件就認為是有效的文章 URL：
        # 1. 包含數字（文章 ID）
        # 2. 包含年份
        # 3. 包含 blog, post, article 等關鍵字
        # 4. URL 長度合理（避免太短的 URL）
        
        # 特別識別 ?p= 文章連結（linshibi.com 的文章格式）
        has_p_param = bool(re.search(r'\?p=\d+', url))  # ?p=14836 格式
        has_numbers = bool(re.search(r'/\d+', url))
        has_year = bool(re.search(r'/20\d{2}', url))
        has_keywords = any(keyword in url.lower() for keyword in ['blog', 'post', 'article', 'entry'])
        reasonable_length = len(url) > 25  # 基本長度檢查
        
        # 如果 URL 包含路徑且不是分類頁面，就認為可能是文章
        has_path = len(url.split('/')) > 3
        not_category = '?cat=' not in url and '/category' not in url and '/tag' not in url
        
        # ?p= 參數是 linshibi.com 的主要文章格式，優先識別
        is_valid = (has_p_param or has_numbers or has_year or has_keywords or (has_path and not_category and reasonable_length))
        
        return is_valid
    
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