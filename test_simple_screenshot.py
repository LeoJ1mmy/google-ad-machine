#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pyautogui
from datetime import datetime

def test_simple_screenshot():
    print("測試 pyautogui 全螢幕截圖...")
    
    try:
        # 直接全螢幕截圖
        screenshot = pyautogui.screenshot()
        
        # 保存測試截圖
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"test_full_screen_{timestamp}.png"
        screenshot.save(filepath)
        
        print(f"✅ 全螢幕截圖保存: {filepath}")
        print(f"   截圖尺寸: {screenshot.size}")
        
        return True
        
    except Exception as e:
        print(f"❌ 截圖失敗: {e}")
        return False

if __name__ == "__main__":
    test_simple_screenshot()