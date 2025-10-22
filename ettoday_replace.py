#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import os
import base64
# import random  # 已移除隨機選擇功能
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
    BASE_URL = "https://travel.ettoday.net"
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
    # GIF 使用策略預設設定
    GIF_PRIORITY = True
    # RANDOM_SELECTION = False  # 已移除隨機選擇功能

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

class EttodayAdReplacer:
    def __init__(self, headless=False, screen_id=1):
        print("正在初始化 ETtoday 廣告替換器...")
        self.screen_id = screen_id
        
        # 統計變數
        self.total_screenshots = 0      # 總截圖數量
        self.total_replacements = 0     # 總替換次數
        self.gif_replacements = 0       # GIF 替換次數
        self.static_replacements = 0    # 靜態圖片替換次數
        self.replacement_details = []   # 詳細替換記錄
        
        self.setup_driver(headless)
        self.load_replace_images()
        print("ETtoday 廣告替換器初始化完成！")
        
    def setup_driver(self, headless):
        print("正在設定 Chrome 瀏覽器...")
        chrome_options = Options()
        
        if headless or HEADLESS_MODE:
            chrome_options.add_argument('--headless')
        
        # 基本設置
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images=false')  # 確保圖片載入
        chrome_options.add_argument('--window-size=1920,1080')
        
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
        
        # 確保瀏覽器在正確的螢幕上並全螢幕
        if not headless:
            self.move_to_screen()
        
        # 設置超時時間
        self.driver.set_page_load_timeout(30)  # 增加到30秒
        self.driver.implicitly_wait(10)  # 隱式等待10秒
        print("瀏覽器設置完成！")
    
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
            
            # 獲取當前窗口大小
            try:
                window_size = self.driver.get_window_size()
                print(f"當前瀏覽器窗口大小: {window_size['width']}x{window_size['height']}")
            except Exception as e:
                print(f"獲取窗口大小失敗: {e}")
            
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
            if filename.endswith(('.jpg', '.jpeg', '.png', '.gif')):
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
        """根據 GIF_PRIORITY 配置選擇圖片（已移除隨機選擇功能）"""
        
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
    
    def load_image_base64(self, image_path):
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"找不到圖片: {image_path}")
            
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def get_random_news_urls(self, base_url, count=5):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"嘗試載入首頁... (第 {attempt + 1}/{max_retries} 次)")
                
                # 使用更短的超時時間進行重試
                self.driver.set_page_load_timeout(20)
                self.driver.get(base_url)
                
                print("首頁載入成功，等待內容載入...")
                time.sleep(WAIT_TIME + 2)  # 增加等待時間
                
                # 檢查頁面是否正確載入
                page_title = self.driver.title
                if not page_title or "ETtoday" not in page_title:
                    print(f"頁面載入異常，標題: {page_title}")
                    if attempt < max_retries - 1:
                        continue
                
                print(f"頁面載入成功: {page_title}")
                
                # ETtoday 旅遊雲的文章連結選擇器
                link_selectors = [
                    "a[href*='/article/']",
                    "a[href*='article']"
                ]
                
                news_urls = []
                
                for selector in link_selectors:
                    try:
                        links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        print(f"找到 {len(links)} 個 {selector} 連結")
                        
                        for link in links:
                            try:
                                href = link.get_attribute('href')
                                if href and href not in news_urls and 'travel.ettoday.net/article' in href:
                                    news_urls.append(href)
                            except:
                                continue
                    except Exception as e:
                        print(f"搜尋連結失敗 ({selector}): {e}")
                        continue
                
                if news_urls:
                    # 選擇前 N 個新聞連結（已移除隨機選擇）
                    selected_urls = news_urls[:min(NEWS_COUNT, len(news_urls))]
                    print(f"成功獲取 {len(selected_urls)} 個新聞連結")
                    return selected_urls
                else:
                    print("未找到任何新聞連結")
                    if attempt < max_retries - 1:
                        print("重新嘗試...")
                        time.sleep(3)
                        continue
                        
            except Exception as e:
                print(f"第 {attempt + 1} 次嘗試失敗: {e}")
                if attempt < max_retries - 1:
                    print("等待後重試...")
                    time.sleep(5)
                    continue
                else:
                    print("所有重試都失敗了")
        
        print("無法獲取新聞連結")
        return []
    

    def analyze_page_sizes(self):
        """分析頁面上所有元素的尺寸分佈"""
        try:
            size_distribution = self.driver.execute_script("""
                var sizeMap = {};
                var elements = document.querySelectorAll('*');
                
                for (var i = 0; i < elements.length; i++) {
                    var element = elements[i];
                    var rect = element.getBoundingClientRect();
                    var width = Math.round(rect.width);
                    var height = Math.round(rect.height);
                    
                    // 只記錄可見且有一定尺寸的元素
                    if (width > 50 && height > 50 && rect.width > 0 && rect.height > 0) {
                        var sizeKey = width + 'x' + height;
                        if (!sizeMap[sizeKey]) {
                            sizeMap[sizeKey] = {
                                count: 0,
                                elements: []
                            };
                        }
                        sizeMap[sizeKey].count++;
                        if (sizeMap[sizeKey].elements.length < 3) {
                            sizeMap[sizeKey].elements.push({
                                tag: element.tagName.toLowerCase(),
                                class: element.className || '',
                                id: element.id || ''
                            });
                        }
                    }
                }
                
                return sizeMap;
            """)
            
            # 顯示常見尺寸
            common_sizes = sorted(size_distribution.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
            print("頁面上最常見的元素尺寸:")
            for size, info in common_sizes:
                print(f"  {size}: {info['count']} 個元素")
                if info['elements']:
                    example = info['elements'][0]
                    print(f"    例如: <{example['tag']} class='{example['class'][:30]}' id='{example['id'][:20]}'>")
            
        except Exception as e:
            print(f"分析頁面尺寸失敗: {e}")
    
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
        
        # 如果直接選擇器沒找到，再進行全頁面掃描
        print("廣告選擇器未找到目標，開始全頁面掃描...")
        
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
                        visible: rect.width > 0 && rect.height > 0,

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
    
    def get_button_style(self):
        """根據配置返回按鈕樣式"""
        try:
            button_style = BUTTON_STYLE
        except NameError:
            button_style = "dots"  # 預設樣式
        
        # 獲取按鈕偏移量設定
        try:
            top_offset = BUTTON_TOP_OFFSET
        except NameError:
            top_offset = 0  # 預設偏移量
        
        # 計算實際的 top 值 (0 + 偏移量)
        actual_top = 0 + top_offset
        
        # 預先定義的按鈕樣式
        # 統一的資訊按鈕樣式 - 使用 Google 標準設計
        unified_info_button = {
            "html": '<svg width="15" height="15" viewBox="0 -1 15 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M7.5 1.5a6 6 0 100 12 6 6 0 100-12m0 1a5 5 0 110 10 5 5 0 110-10zM6.625 11h1.75V6.5h-1.75zM7.5 3.75a1 1 0 100 2 1 1 0 100-2z" fill="#00aecd"/></svg>',
            "style": f'position:absolute;top:{actual_top+1}px;right:17px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);cursor:pointer;'
        }
        
        button_styles = {
            "dots": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 -1 15 16" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="7.5" cy="2.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="6.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="10.5" r="1.5" fill="#00aecd"/></svg>',
                    "style": f'position:absolute;top:{actual_top}px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;'
                },
                "info_button": unified_info_button
            },
            "cross": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 -1 15 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 4L11 11M11 4L4 11" stroke="#00aecd" stroke-width="1.5" stroke-linecap="round"/></svg>',
                    "style": f'position:absolute;top:{actual_top-1}px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;'
                },
                "info_button": unified_info_button
            },
            "adchoices": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 4L11 11M11 4L4 11" stroke="#00aecd" stroke-width="1.5" stroke-linecap="round"/></svg>',
                    "style": f'position:absolute;top:{actual_top-1}px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;'
                },
                "info_button": {
                    "html": '<img src="https://tpc.googlesyndication.com/pagead/images/adchoices/adchoices_blue_wb.png" width="15" height="15" style="display:block;width:15px;height:15px;">',
                    "style": f'position:absolute;top:{actual_top}px;right:17px;width:15px;height:15px;z-index:100;display:block;cursor:pointer;'
                }
            },
            "adchoices_dots": {
                "close_button": {
                    "html": '<svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="7.5" cy="2.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="6.5" r="1.5" fill="#00aecd"/><circle cx="7.5" cy="10.5" r="1.5" fill="#00aecd"/></svg>',
                    "style": f'position:absolute;top:{actual_top}px;right:1px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);cursor:pointer;'
                },
                "info_button": {
                    "html": '<img src="https://tpc.googlesyndication.com/pagead/images/adchoices/adchoices_blue_wb.png" width="15" height="15" style="display:block;width:15px;height:15px;">',
                    "style": f'position:absolute;top:{actual_top}px;right:17px;width:15px;height:15px;z-index:100;display:block;cursor:pointer;'
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

    def replace_ad_content(self, element, image_data, target_width, target_height, ad_info=None):
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
            
            # 檢查是否符合目標尺寸（允許±2像素誤差）
            if (abs(original_info['width'] - target_width) > 2 or 
                abs(original_info['height'] - target_height) > 2):
                print(f"尺寸不匹配: 期望 {target_width}x{target_height}, 實際 {original_info['width']}x{original_info['height']}")
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
            
            # 檢查是否為 GIF 檔案
            is_gif = ad_info and ad_info.get('is_gif', False) if ad_info else False
            
            # 獲取按鈕偏移量設定（用於 JavaScript 中的 actual_top）
            try:
                actual_top = 0 + BUTTON_TOP_OFFSET
            except NameError:
                actual_top = 1  # 預設偏移量
            
            # 只替換圖片，保留廣告按鈕，支援動態尺寸調整
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
                            right: 17px;
                            top: """ + str(actual_top) + """px;
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
                            top: """ + str(actual_top) + """px;
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
                            top: """ + str(actual_top) + """px;
                            bottom: auto;
                            vertical-align: top;
                            margin-top: 0px;
                            right: 1px;
                            left: auto;
                            text-align: right;
                            margin-right: 0px;
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
                        [id^="close_button_"] { 
                            text-decoration: none; 
                            margin: 0; 
                            padding: 0; 
                            border: none;
                            cursor: pointer;
                            position: absolute !important; 
                            z-index: 100 !important; 
                            top: """ + str(actual_top) + """px !important;
                            right: 1px !important;
                            display: block !important; 
                            width: 15px !important; 
                            height: 15px !important;
                            background-color: rgba(255,255,255,1) !important;
                        }
                        [id^="abgb_"] { 
                            position: absolute !important;
                            right: 17px !important;
                            top: """ + str(actual_top) + """px !important;
                            width: 15px !important; 
                            height: 15px !important;
                            z-index: 100 !important;
                            display: block !important;
                            background-color: rgba(255,255,255,1) !important;
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
                // 生成唯一ID避免衝突
                var uniqueId = Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                var closeButtonId = 'close_button_' + uniqueId;
                var infoButtonId = 'abgb_' + uniqueId;
                
                // 先移除舊的（避免重複）
                ['close_button', 'abgb', closeButtonId, infoButtonId].forEach(function(id){
                  var old = container.querySelector('#'+id);
                  if(old) old.remove();
                });
                
                var replacedCount = 0;
                var isGif = arguments[9] || false;
                var mimeType = isGif ? 'image/gif' : 'image/png';
                var newImageSrc = 'data:' + mimeType + ';base64,' + imageBase64;
                
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
                        [closeButtonId, infoButtonId, 'close_button', 'abgb'].forEach(function(id){
                            var old = imgParent.querySelector('#'+id);
                            if(old) old.remove();
                        });
                        
                        // 只有在非 none 模式下才創建按鈕
                        if (!isNoneMode && (closeButtonHtml || infoButtonHtml)) {
                            // 叉叉 - 貼著替換圖片的右上角
                            if (closeButtonHtml) {
                                var closeButton = document.createElement('div');
                                closeButton.id = closeButtonId;
                                closeButton.innerHTML = closeButtonHtml;
                                closeButton.style.cssText = closeButtonStyle;
                                imgParent.appendChild(closeButton);
                            }
                            
                            // 驚嘆號 - 貼著替換圖片的右上角，與叉叉對齊
                            if (infoButtonHtml) {
                                var abgb = document.createElement('div');
                                abgb.id = infoButtonId;
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
                    [closeButtonId, infoButtonId, 'close_button', 'abgb'].forEach(function(id){
                        var old = container.querySelector('#'+id);
                        if(old) old.remove();
                    });
                    
                    // 只有在非 none 模式下才創建按鈕
                    if (!isNoneMode && (closeButtonHtml || infoButtonHtml)) {
                        // 叉叉 - 貼著替換圖片的右上角
                        if (closeButtonHtml) {
                            var closeButton = document.createElement('div');
                            closeButton.id = closeButtonId;
                            closeButton.innerHTML = closeButtonHtml;
                            closeButton.style.cssText = 'position:absolute;top:' + (iframeRect.top - container.getBoundingClientRect().top + 1) + 'px;right:' + (container.getBoundingClientRect().right - iframeRect.right + 1) + 'px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);';
                            container.appendChild(closeButton);
                        }
                        
                        // 驚嘆號 - 貼著替換圖片的右上角，與叉叉水平對齊
                        if (infoButtonHtml) {
                            var abgb = document.createElement('div');
                            abgb.id = infoButtonId;
                            abgb.className = 'abgb';
                            abgb.innerHTML = infoButtonHtml;
                            abgb.style.cssText = 'position:absolute;top:' + (iframeRect.top - container.getBoundingClientRect().top + 1) + 'px;right:' + (container.getBoundingClientRect().right - iframeRect.right + 17) + 'px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);line-height:0;';
                            container.appendChild(abgb);
                        }
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
                        [closeButtonId, infoButtonId, 'close_button', 'abgb'].forEach(function(id){
                            var old = container.querySelector('#'+id);
                            if(old) old.remove();
                        });
                        
                        // 只有在非 none 模式下才創建按鈕
                        if (!isNoneMode && (closeButtonHtml || infoButtonHtml)) {
                            // 叉叉 - 貼著替換圖片的右上角
                            if (closeButtonHtml) {
                                var closeButton = document.createElement('div');
                                closeButton.id = closeButtonId;
                                closeButton.innerHTML = closeButtonHtml;
                                closeButton.style.cssText = closeButtonStyle;
                                container.appendChild(closeButton);
                            }
                            
                            // 驚嘆號 - 貼著替換圖片的右上角，與叉叉對齊
                            if (infoButtonHtml) {
                                var abgb = document.createElement('div');
                                abgb.id = infoButtonId;
                                abgb.className = 'abgb';
                                abgb.innerHTML = infoButtonHtml;
                                abgb.style.cssText = infoButtonStyle;
                                container.appendChild(abgb);
                            }
                        }
                    }
                }
                return replacedCount > 0;
            """, element, image_data, target_width, target_height, close_button_html, close_button_style, info_button_html, info_button_style, is_none_mode, is_gif)
            
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
            print("頁面載入完成，等待廣告載入...")
            time.sleep(WAIT_TIME + 2)  # 增加等待時間讓廣告有時間載入
            
            # 獲取頁面標題
            try:
                page_title = self.driver.title
                print(f"📰 頁面標題: {page_title}")
            except Exception as e:
                print(f"獲取頁面標題失敗: {e}")
                page_title = None
            
            # 滾動頁面以觸發懶載入的廣告
            print("滾動頁面以載入更多廣告...")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # 遍歷所有替換圖片
            total_replacements = 0
            screenshot_paths = []  # 儲存所有截圖路徑
            
            # 先分析頁面上的所有元素尺寸
            print("\n分析頁面元素尺寸分佈...")
            self.analyze_page_sizes()
            
            # 按尺寸處理，而不是按單個圖片處理
            processed_sizes = set()
            
            for image_info in self.replace_images:
                size_key = f"{image_info['width']}x{image_info['height']}"
                
                # 如果這個尺寸已經處理過，跳過
                if size_key in processed_sizes:
                    continue
                
                processed_sizes.add(size_key)
                
                print(f"\n🔍 檢查尺寸: {size_key}")
                
                # 獲取這個尺寸的所有可用圖片
                available_images = self.images_by_size.get(size_key, {'static': [], 'gif': []})
                static_images = available_images['static']
                gif_images = available_images['gif']
                
                print(f"   可用圖片: {len(static_images)}張靜態 + {len(gif_images)}張GIF")
                
                # 掃描網頁尋找符合尺寸的廣告
                matching_elements = self.scan_entire_page_for_ads(image_info['width'], image_info['height'])
                
                if not matching_elements:
                    print(f"未找到符合 {size_key} 尺寸的廣告位置")
                    continue
                
                # 嘗試替換找到的廣告
                replaced = False
                processed_positions = set()  # 記錄已處理的位置
                
                for ad_info in matching_elements:
                    # 檢查是否已經處理過這個位置
                    position_key = f"{ad_info['position']}_{size_key}"
                    if position_key in processed_positions:
                        print(f"跳過已處理的位置: {ad_info['position']}")
                        continue
                    
                    # 根據配置策略選擇圖片
                    selected_image = self.select_image_by_strategy(static_images, gif_images, size_key)
                    if not selected_image:
                        print(f"   ❌ 沒有可用的 {size_key} 圖片")
                        continue
                    
                    try:
                        # 載入選中的圖片
                        image_data = self.load_image_base64(selected_image['path'])
                        
                        # 將圖片類型資訊加入 ad_info
                        ad_info_with_type = {**ad_info, 'type': selected_image['type'], 'is_gif': selected_image['is_gif']}
                        
                        if self.replace_ad_content(ad_info['element'], image_data, selected_image['width'], selected_image['height'], ad_info_with_type):
                            type_icon = "🎬" if selected_image['is_gif'] else "🖼️"
                            print(f"✅ 成功替換廣告: {type_icon} {ad_info['width']}x{ad_info['height']} at {ad_info['position']}")
                            print(f"   📄 使用檔案: {selected_image['filename']}")
                            replaced = True
                            total_replacements += 1
                            
                            # 更新統計
                            self.total_replacements += 1
                            if selected_image['is_gif']:
                                self.gif_replacements += 1
                            else:
                                self.static_replacements += 1
                            
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
                            screenshot_path = self.take_screenshot(page_title)
                            if screenshot_path:
                                screenshot_paths.append(screenshot_path)
                                self.total_screenshots += 1  # 更新截圖統計
                                print(f"✅ 截圖保存: {screenshot_path}")
                                
                                # 記錄詳細資訊（包含截圖路徑）
                                self.replacement_details.append({
                                    'type': 'GIF' if selected_image['is_gif'] else '靜態圖片',
                                    'filename': selected_image['filename'],
                                    'size': f"{ad_info['width']}x{ad_info['height']}",
                                    'position': ad_info['position'],
                                    'screenshot_path': screenshot_path
                                })
                            else:
                                print("❌ 截圖失敗")
                                # 即使截圖失敗也記錄替換資訊
                                self.replacement_details.append({
                                    'type': 'GIF' if selected_image['is_gif'] else '靜態圖片',
                                    'filename': selected_image['filename'],
                                    'size': f"{ad_info['width']}x{ad_info['height']}",
                                    'position': ad_info['position'],
                                    'screenshot_path': None
                                })
                            
                            # 截圖後復原該位置的廣告
                            try:
                                self.driver.execute_script("""
                                    var element = arguments[0];
                                    
                                    // 只在當前廣告容器內移除我們添加的按鈕（包括動態ID）
                                    var containerButtons = element.querySelectorAll('#close_button, #abgb, [id^="close_button_"], [id^="abgb_"]');
                                    for (var i = 0; i < containerButtons.length; i++) {
                                        containerButtons[i].remove();
                                    }
                                    
                                    // 檢查父容器中的按鈕（如果廣告在父層）
                                    var parent = element.parentElement;
                                    if (parent) {
                                        var parentButtons = parent.querySelectorAll('#close_button, #abgb, [id^="close_button_"], [id^="abgb_"]');
                                        for (var i = 0; i < parentButtons.length; i++) {
                                            parentButtons[i].remove();
                                        }
                                    }
                                    
                                    // 只移除當前容器內我們添加的圖片（通過data URI識別）
                                    var containerImages = element.querySelectorAll('img[src^="data:image/"]');
                                    for (var i = 0; i < containerImages.length; i++) {
                                        // 只移除我們添加的圖片（base64 格式）
                                        if (containerImages[i].src.includes('base64')) {
                                            containerImages[i].remove();
                                        }
                                    }
                                    
                                    // 檢查父容器中我們添加的圖片
                                    if (parent) {
                                        var parentImages = parent.querySelectorAll('img[src^="data:image/"]');
                                        for (var i = 0; i < parentImages.length; i++) {
                                            if (parentImages[i].src.includes('base64')) {
                                                parentImages[i].remove();
                                            }
                                        }
                                    }
                                    
                                    // 復原原始廣告內容
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
                                    restoreElement(element);
                                    
                                    // 復原容器內的所有圖片
                                    var imgs = element.querySelectorAll('img[data-original-src]');
                                    for (var i = 0; i < imgs.length; i++) {
                                        restoreElement(imgs[i]);
                                    }
                                    
                                    // 復原容器內的所有iframe
                                    var iframes = element.querySelectorAll('iframe[style*="visibility: hidden"]');
                                    for (var i = 0; i < iframes.length; i++) {
                                        restoreElement(iframes[i]);
                                    }
                                    
                                    // 移除我們添加的按鈕
                                    var buttonsToRemove = element.querySelectorAll('[id^="close_button"], [id^="abgb"], #close_button, #abgb');
                                    for (var i = 0; i < buttonsToRemove.length; i++) {
                                        buttonsToRemove[i].remove();
                                    }
                                """, ad_info['element'])
                                print(f"✅ 廣告位置已復原: {ad_info['width']}x{ad_info['height']} at {ad_info['position']}")
                            except Exception as e:
                                print(f"復原廣告失敗: {e}")
                            
                            # 繼續尋找下一個廣告位置，不要break
                            continue
                    except Exception as e:
                        print(f"❌ 載入圖片失敗: {e}")
                        continue
                    except Exception as e:
                        print(f"❌ 替換廣告失敗: {e}")
                        continue
                
                if not replaced:
                    print(f"❌ 所有找到的 {size_key} 廣告位置都無法替換")
            
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
            filepath = f"{SCREENSHOT_FOLDER}/ettoday_{clean_title}_{timestamp}.png"
        else:
            filepath = f"{SCREENSHOT_FOLDER}/ettoday_replaced_{timestamp}.png"
        
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
    
    def show_statistics(self):
        """顯示統計資訊"""
        print("\n" + "="*60)
        print("📊 ETtoday 廣告替換統計報告")
        print("="*60)
        
        print(f"📸 總截圖數量: {self.total_screenshots} 張")
        print(f"🔄 總替換次數: {self.total_replacements} 次")
        
        if self.total_replacements > 0:
            print(f"   🎬 GIF 替換: {self.gif_replacements} 次 ({self.gif_replacements/self.total_replacements*100:.1f}%)")
            print(f"   🖼️ 靜態圖片替換: {self.static_replacements} 次 ({self.static_replacements/self.total_replacements*100:.1f}%)")
        
        if self.replacement_details:
            print(f"\n📋 詳細替換記錄:")
            for i, detail in enumerate(self.replacement_details, 1):
                type_icon = "🎬" if detail['type'] == 'GIF' else "🖼️"
                if detail.get('screenshot_path'):
                    # 使用完整路徑，在支援的環境中可以點擊開啟
                    import os
                    full_path = os.path.abspath(detail['screenshot_path'])
                    print(f"   {i:2d}. {type_icon} {detail['filename']} ({detail['size']}) → 📸 {full_path}")
                else:
                    print(f"   {i:2d}. {type_icon} {detail['filename']} ({detail['size']}) → ❌ 截圖失敗")
        

        

        
        # 顯示 GIF 使用策略
        try:
            from gif_config import GIF_PRIORITY
            print(f"\n⚙️ 當前 GIF 策略:")
            priority_text = "GIF 優先" if GIF_PRIORITY else "靜態圖片優先"
            print(f"   🎯 優先級模式 - {priority_text}")
        except:
            pass
        
        print("="*60)
    
    def close(self):
        """關閉瀏覽器並顯示統計"""
        self.show_statistics()
        self.driver.quit()

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
    test_bot = EttodayAdReplacer(headless=False, screen_id=screen_id)
    
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

def main():
    # 偵測並選擇螢幕
    screen_id, selected_screen = ScreenManager.select_screen()
    
    if screen_id is None:
        print("未選擇螢幕，程式結束")
        return
    
    print(f"\n正在啟動 Chrome 瀏覽器到螢幕 {screen_id}...")
    bot = EttodayAdReplacer(headless=False, screen_id=screen_id)
    
    try:
        # 尋找新聞連結 - 使用 ETtoday 旅遊雲網址
        ettoday_url = "https://travel.ettoday.net"
        print(f"正在連接 {ettoday_url}...")
        
        news_urls = bot.get_random_news_urls(ettoday_url, NEWS_COUNT)
        
        if not news_urls:
            print("❌ 無法獲取新聞連結，可能的原因：")
            print("   1. 網路連線問題")
            print("   2. ETtoday 網站暫時無法存取")
            print("   3. 頁面結構已改變")
            print("\n💡 建議解決方案：")
            print("   1. 檢查網路連線")
            print("   2. 稍後再試")
            print("   3. 檢查防火牆設定")
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
        print(f"🎉 所有網站處理完成！")
        print(f"{'='*50}")
        

        
    except KeyboardInterrupt:
        print(f"\n\n⚠️  程式被使用者中斷 (Ctrl+C)")
        print("正在關閉瀏覽器...")
    except Exception as e:
        print(f"\n❌ 程式執行錯誤: {e}")
        print("正在關閉瀏覽器...")
    finally:
        bot.close()
        print("瀏覽器已關閉")

if __name__ == "__main__":
    import sys
    
    # 檢查是否有命令列參數
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_screen_setup()
    else:
        main()