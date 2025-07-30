#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import os
import base64
import random
import re
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
    BASE_URL = "https://travel.udn.com/travel/index"
    UDN_BASE_URL = "https://travel.udn.com/travel/index"  # 聯合報旅遊網站
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

class UdnAdReplacer:
    def __init__(self, headless=False):
        self.setup_driver(headless)
        self.load_replace_images()
        
    def setup_driver(self, headless):
        chrome_options = Options()
        if headless or HEADLESS_MODE:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        if FULLSCREEN_MODE:
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--start-fullscreen')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # 確保瀏覽器為全螢幕模式
        if not headless and FULLSCREEN_MODE:
            self.driver.fullscreen_window()
    
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
                        
            return random.sample(news_urls, min(NEWS_COUNT, len(news_urls)))
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
                
                if (!container) return false;
                
                // 保存原始廣告內容 - 針對 GDN 廣告結構優化
                var originalContent = {
                    html: container.innerHTML,
                    style: container.getAttribute('style') || '',
                    className: container.getAttribute('class') || '',
                    id: container.getAttribute('id') || '',
                    outerHTML: container.outerHTML,
                    // 特別保存 iframe 的狀態
                    iframes: []
                };
                
                // 保存所有 iframe 的原始狀態
                var iframes = container.querySelectorAll('iframe');
                for (var i = 0; i < iframes.length; i++) {
                    var iframe = iframes[i];
                    originalContent.iframes.push({
                        src: iframe.src,
                        style: iframe.getAttribute('style') || '',
                        display: window.getComputedStyle(iframe).display,
                        visibility: window.getComputedStyle(iframe).visibility
                    });
                }
                
                container.setAttribute('data-original-content', JSON.stringify(originalContent));
                
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
                return replacedCount > 0;
            """, element, image_data, target_width, target_height, close_button_html, close_button_style, info_button_html, info_button_style)
            
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
                                print(f"✅ 截圖保存: {screenshot_path}")
                            else:
                                print("❌ 截圖失敗")
                            
                            # 截圖後復原該位置的廣告
                            try:
                                self.driver.execute_script("""
                                    // 簡化還原邏輯：直接移除所有注入的元素
                                    // 移除所有注入的按鈕
                                    var buttons = document.querySelectorAll('#close_button, #abgb, #info_button');
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
                                """, ad_info['element'])
                                print("✅ 廣告位置已復原")
                                
                                # 標記該位置為已處理，避免無限循環
                                position_key = f"top:{ad_info['top']}, left:{ad_info['left']}"
                                processed_positions.add(position_key)
                                print(f"📍 標記位置為已處理: {position_key}")
                                
                                # 驗證還原是否成功
                                try:
                                    restored = self.driver.execute_script("""
                                        // 不依賴傳入的元素，直接檢查頁面狀態
                                        var hasNoButtons = !document.querySelector('#close_button') && 
                                                          !document.querySelector('#abgb');
                                        
                                        // 檢查是否有任何元素還保留原始內容標記
                                        var hasNoOriginalData = !document.querySelector('[data-original-content]');
                                        
                                        // 檢查是否有替換的圖片
                                        var hasNoReplacedImages = !document.querySelector('img[src*="data:image/png;base64"]');
                                        
                                        // 檢查是否有替換容器
                                        var hasNoReplacementContainer = !document.querySelector('#ad_replacement_container');
                                        
                                        return hasNoButtons && hasNoOriginalData && hasNoReplacedImages && hasNoReplacementContainer;
                                    """)
                                    
                                    if restored:
                                        print("✅ 還原驗證成功 - GDN廣告已恢復")
                                    else:
                                        print("⚠️ 還原驗證失敗，但繼續執行")
                                except Exception as e:
                                    print(f"還原驗證失敗: {e}")
                            except Exception as e:
                                print(f"復原廣告失敗: {e}")
                            
                            # 等待還原完成
                            time.sleep(1)
                            
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
        import platform
        import subprocess
        
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
                # Windows 系統使用 pyautogui
                try:
                    import pyautogui
                    # 獲取螢幕尺寸
                    screen_width, screen_height = pyautogui.size()
                    # 截取整個螢幕
                    screenshot = pyautogui.screenshot()
                    screenshot.save(filepath)
                    print(f"截圖保存: {filepath}")
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
                # 獲取Chrome所在的螢幕編號並截圖
                # 使用AppleScript獲取Chrome窗口位置
                get_display_cmd = '''osascript -e '
                    tell application "Google Chrome"
                        activate
                        set windowBounds to bounds of front window
                        set screenWidth to item 3 of windowBounds
                        return screenWidth
                    end tell
                ' '''
                
                display_result = subprocess.run(get_display_cmd, shell=True, capture_output=True, text=True)
                
                if display_result.returncode == 0:
                    # 使用-D參數指定螢幕（預設為主螢幕）
                    result = subprocess.run([
                        'screencapture', 
                        '-D', '1',  # 截取第一個螢幕
                        filepath
                    ], capture_output=True, text=True)
                else:
                    # 如果無法獲取螢幕資訊，使用全螢幕截圖
                    result = subprocess.run([
                        'screencapture', 
                        filepath
                    ], capture_output=True, text=True)
                
                if result.returncode == 0 and os.path.exists(filepath):
                    print(f"截圖保存: {filepath}")
                    return filepath
                else:
                    # 如果互動截圖失敗，回退到Selenium截圖
                    print("互動截圖失敗，使用Selenium截圖")
                    self.driver.save_screenshot(filepath)
                    print(f"截圖保存: {filepath}")
                    return filepath
                    
            else:  # Linux 或其他系統
                # 使用 Selenium 截圖
                self.driver.save_screenshot(filepath)
                print(f"截圖保存: {filepath}")
                return filepath
                
        except Exception as e:
            print(f"系統截圖失敗: {e}，使用Selenium截圖")
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
    bot = UdnAdReplacer(headless=False)
    
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

if __name__ == "__main__":
    main() 