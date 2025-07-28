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
    BASE_URL = "https://playing.ltn.com.tw"
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

class GoogleAdReplacer:
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
        return matching_elements
    
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
                        
                        // 叉叉 - 貼著替換圖片的右上角
                        var closeButton = document.createElement('div');
                        closeButton.id = 'close_button';
                        closeButton.innerHTML = '<img id="close_button_svg" src="https://static.criteo.net/flash/icon/close_button.svg">';
                        closeButton.style.cssText = 'position:absolute;top:0px;right:0px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);line-height:0;';
                        
                        // 驚嘆號 - 貼著替換圖片的右上角，與叉叉對齊
                        var abgb = document.createElement('div');
                        abgb.id = 'abgb';
                        abgb.className = 'abgb';
                        abgb.innerHTML = '<img id="info_button_svg" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNSAxNSI+PHBhdGggZD0iTTcuNSAxLjVhNiA2IDAgMSAwIDAgMTIgNiA2IDAgMCAwIDAtMTJ6bTAgMWE1IDUgMCAxIDEgMCAxMCA1IDUgMCAwIDEgMC0xMHpNNi42MjUgMTFoMS43NVY2LjVoLTEuNzV6TTcuNSAzLjc1YTEgMSAwIDEgMCAwIDIgMSAxIDAgMCAwIDAtMnoiIGZpbGw9IiMwMGFlY2QiLz48L3N2Zz4=">';
                        abgb.style.cssText = 'position:absolute;top:0px;right:17px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);line-height:0;';
                        
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
                    closeButton.innerHTML = '<img id="close_button_svg" src="https://static.criteo.net/flash/icon/close_button.svg">';
                    closeButton.style.cssText = 'position:absolute;top:' + (iframeRect.top - container.getBoundingClientRect().top) + 'px;right:' + (container.getBoundingClientRect().right - iframeRect.right) + 'px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);';
                    
                    // 驚嘆號 - 貼著替換圖片的右上角，與叉叉水平對齊
                    var abgb = document.createElement('div');
                    abgb.id = 'abgb';
                    abgb.className = 'abgb';
                    abgb.innerHTML = '<img id="info_button_svg" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNSAxNSI+PHBhdGggZD0iTTcuNSAxLjVhNiA2IDAgMSAwIDAgMTIgNiA2IDAgMCAwIDAtMTJ6bTAgMWE1IDUgMCAxIDEgMCAxMCA1IDUgMCAwIDEgMC0xMHpNNi42MjUgMTFoMS43NVY2LjVoLTEuNzV6TTcuNSAzLjc1YTEgMSAwIDEgMCAwIDIgMSAxIDAgMCAwIDAtMnoiIGZpbGw9IiMwMGFlY2QiLz48L3N2Zz4=">';
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
                        closeButton.innerHTML = '<img id="close_button_svg" src="https://static.criteo.net/flash/icon/close_button.svg">';
                        closeButton.style.cssText = 'position:absolute;top:0px;right:0px;width:15px;height:15px;z-index:101;display:block;background-color:rgba(255,255,255,1);line-height:0;';
                        
                        var abgb = document.createElement('div');
                        abgb.id = 'abgb';
                        abgb.className = 'abgb';
                        abgb.innerHTML = '<img id="info_button_svg" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNSAxNSI+PHBhdGggZD0iTTcuNSAxLjVhNiA2IDAgMSAwIDAgMTIgNiA2IDAgMCAwIDAtMTJ6bTAgMWE1IDUgMCAxIDEgMCAxMCA1IDUgMCAwIDEgMC0xMHpNNi42MjUgMTFoMS43NVY2LjVoLTEuNzV6TTcuNSAzLjc1YTEgMSAwIDEgMCAwIDIgMSAxIDAgMCAwIDAtMnoiIGZpbGw9IiMwMGFlY2QiLz48L3N2Zz4=">';
                        abgb.style.cssText = 'position:absolute;top:0px;right:17px;width:15px;height:15px;z-index:100;display:block;background-color:rgba(255,255,255,1);line-height:0;';
                        
                        // 將按鈕添加到container內，與背景圖片同層
                        container.appendChild(abgb);
                        container.appendChild(closeButton);
                    }
                }
                return replacedCount > 0;
            """, element, image_data, target_width, target_height)
            
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
                                print("✅ 廣告位置已復原")
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
    
    def take_screenshot(self):
        import platform
        import subprocess
        
        if not os.path.exists(SCREENSHOT_FOLDER):
            os.makedirs(SCREENSHOT_FOLDER)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"{SCREENSHOT_FOLDER}/ltn_replaced_{timestamp}.png"
        
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
    bot = GoogleAdReplacer(headless=False)
    
    try:
        # 尋找新聞連結
        news_urls = bot.get_random_news_urls(BASE_URL, NEWS_COUNT)
        
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

if __name__ == "__main__":
    main()