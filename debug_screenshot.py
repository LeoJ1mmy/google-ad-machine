#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime

def debug_screenshot():
    print("=== 調試副螢幕截圖問題 ===\n")
    
    # 測試 1: 基本 pyautogui
    print("1. 測試基本 pyautogui 截圖:")
    try:
        import pyautogui
        screenshot = pyautogui.screenshot()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"debug_pyautogui_{timestamp}.png"
        screenshot.save(filepath)
        print(f"✅ pyautogui 截圖成功: {filepath}")
        print(f"   尺寸: {screenshot.size}")
    except Exception as e:
        print(f"❌ pyautogui 失敗: {e}")
    
    # 測試 2: MSS 庫
    print("\n2. 測試 MSS 庫:")
    try:
        import mss
        with mss.mss() as sct:
            monitors = sct.monitors
            print(f"   偵測到螢幕: {monitors}")
            
            for i, monitor in enumerate(monitors):
                if i == 0:
                    continue  # 跳過 "All in One" 螢幕
                
                print(f"\n   測試螢幕 {i}: {monitor}")
                screenshot_mss = sct.grab(monitor)
                
                # 轉換為 PIL Image
                from PIL import Image
                screenshot = Image.frombytes('RGB', screenshot_mss.size, screenshot_mss.bgra, 'raw', 'BGRX')
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = f"debug_mss_screen{i}_{timestamp}.png"
                screenshot.save(filepath)
                print(f"   ✅ MSS 螢幕 {i} 截圖成功: {filepath}")
                print(f"   尺寸: {screenshot.size}")
                
    except ImportError:
        print("❌ MSS 未安裝")
    except Exception as e:
        print(f"❌ MSS 失敗: {e}")
    
    # 測試 3: PIL ImageGrab (Windows)
    print("\n3. 測試 PIL ImageGrab (Windows):")
    try:
        from PIL import ImageGrab
        
        # 嘗試截取所有螢幕
        screenshot = ImageGrab.grab()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"debug_pil_all_{timestamp}.png"
        screenshot.save(filepath)
        print(f"✅ PIL 全螢幕截圖成功: {filepath}")
        print(f"   尺寸: {screenshot.size}")
        
        # 嘗試獲取螢幕資訊
        try:
            import win32gui
            def enum_display_monitors():
                monitors = []
                def callback(hmonitor, hdc, rect, data):
                    monitors.append({
                        'left': rect[0], 'top': rect[1], 
                        'right': rect[2], 'bottom': rect[3],
                        'width': rect[2] - rect[0], 'height': rect[3] - rect[1]
                    })
                    return True
                win32gui.EnumDisplayMonitors(None, None, callback, None)
                return monitors
            
            monitors = enum_display_monitors()
            print(f"   Win32 偵測到螢幕: {monitors}")
            
            for i, monitor in enumerate(monitors):
                bbox = (monitor['left'], monitor['top'], monitor['right'], monitor['bottom'])
                screenshot = ImageGrab.grab(bbox)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = f"debug_pil_screen{i+1}_{timestamp}.png"
                screenshot.save(filepath)
                print(f"   ✅ PIL 螢幕 {i+1} 截圖成功: {filepath}")
                print(f"   尺寸: {screenshot.size}")
                
        except ImportError:
            print("   win32gui 未安裝，無法獲取詳細螢幕資訊")
            
    except Exception as e:
        print(f"❌ PIL 失敗: {e}")

if __name__ == "__main__":
    debug_screenshot()