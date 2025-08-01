#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from datetime import datetime

# 測試截圖功能
def test_screenshot():
    print("測試截圖功能...")
    
    # 測試 MSS 庫
    try:
        import mss
        with mss.mss() as sct:
            monitors = sct.monitors
            print(f"MSS 偵測到 {len(monitors)-1} 個螢幕: {monitors}")
            
            # 截取主螢幕
            if len(monitors) > 1:
                monitor = monitors[1]  # monitors[1] 是主螢幕
                screenshot_mss = sct.grab(monitor)
                
                # 轉換為 PIL Image
                from PIL import Image
                screenshot = Image.frombytes('RGB', screenshot_mss.size, screenshot_mss.bgra, 'raw', 'BGRX')
                
                # 保存測試截圖
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = f"test_screenshot_{timestamp}.png"
                screenshot.save(filepath)
                print(f"✅ MSS 測試截圖保存: {filepath}")
                print(f"   截圖尺寸: {screenshot.size}")
                return True
                
    except ImportError:
        print("❌ MSS 未安裝")
        return False
    except Exception as e:
        print(f"❌ MSS 測試失敗: {e}")
        return False

if __name__ == "__main__":
    test_screenshot()