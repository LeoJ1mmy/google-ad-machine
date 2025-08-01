#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 測試 ad_replacer.py 中的截圖功能
import sys
import os
from datetime import datetime

# 模擬 AdReplacer 類的截圖方法
class TestScreenshot:
    def __init__(self, screen_id):
        self.screen_id = screen_id
    
    def take_screenshot(self):
        SCREENSHOT_FOLDER = "screenshots"
        if not os.path.exists(SCREENSHOT_FOLDER):
            os.makedirs(SCREENSHOT_FOLDER)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"{SCREENSHOT_FOLDER}/test_ltn_replaced_{timestamp}.png"
        
        try:
            # 直接使用 MSS 庫 - 最可靠的多螢幕截圖方法
            import mss
            with mss.mss() as sct:
                monitors = sct.monitors
                print(f"MSS 偵測到 {len(monitors)-1} 個螢幕: {monitors}")
                
                if self.screen_id < len(monitors):
                    # 截取指定螢幕
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
            print("❌ MSS 未安裝")
            return None
        except Exception as e:
            print(f"❌ MSS 截圖失敗: {e}")
            return None

def main():
    print("測試 AdReplacer 截圖功能...")
    
    # 測試主螢幕
    print("\n=== 測試主螢幕 ===")
    test1 = TestScreenshot(1)
    result1 = test1.take_screenshot()
    
    # 測試副螢幕
    print("\n=== 測試副螢幕 ===")
    test2 = TestScreenshot(2)
    result2 = test2.take_screenshot()
    
    if result1 and result2:
        print("\n✅ 所有測試通過！")
    else:
        print("\n❌ 部分測試失敗")

if __name__ == "__main__":
    main()