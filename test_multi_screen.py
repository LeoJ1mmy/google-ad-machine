#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pyautogui
from datetime import datetime

def test_multi_screen():
    print("測試多螢幕截圖...")
    
    # 測試主螢幕
    print("\n=== 測試主螢幕 ===")
    try:
        screenshot1 = pyautogui.screenshot()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath1 = f"test_screen1_{timestamp}.png"
        screenshot1.save(filepath1)
        print(f"✅ 主螢幕截圖: {filepath1}")
        print(f"   尺寸: {screenshot1.size}")
    except Exception as e:
        print(f"❌ 主螢幕截圖失敗: {e}")
    
    # 測試副螢幕 (使用 MSS)
    print("\n=== 測試副螢幕 (MSS) ===")
    try:
        import mss
        with mss.mss() as sct:
            monitors = sct.monitors
            print(f"偵測到 {len(monitors)-1} 個螢幕:")
            for i, monitor in enumerate(monitors):
                if i == 0:
                    print(f"  全部螢幕: {monitor}")
                else:
                    print(f"  螢幕 {i}: {monitor}")
            
            # 如果有副螢幕，截取副螢幕
            if len(monitors) > 2:  # monitors[0] 是全部螢幕，monitors[1] 是主螢幕，monitors[2] 是副螢幕
                monitor = monitors[2]  # 副螢幕
                screenshot_mss = sct.grab(monitor)
                
                # 轉換為 PIL Image
                from PIL import Image
                screenshot2 = Image.frombytes('RGB', screenshot_mss.size, screenshot_mss.bgra, 'raw', 'BGRX')
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath2 = f"test_screen2_{timestamp}.png"
                screenshot2.save(filepath2)
                print(f"✅ 副螢幕截圖: {filepath2}")
                print(f"   尺寸: {screenshot2.size}")
            else:
                print("❌ 沒有偵測到副螢幕")
                
    except ImportError:
        print("❌ MSS 未安裝，無法測試副螢幕")
    except Exception as e:
        print(f"❌ 副螢幕測試失敗: {e}")

if __name__ == "__main__":
    test_multi_screen()