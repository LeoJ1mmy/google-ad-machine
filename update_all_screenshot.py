#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

# 新的截圖代碼
new_screenshot_code = '''                        # 方法2: 直接使用 MSS 庫 - 最可靠的多螢幕截圖方法
                        try:
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
                                    
                        except ImportError:
                            print("❌ MSS 未安裝，使用 pyautogui 備用方案")
                            import pyautogui
                            screenshot = pyautogui.screenshot()
                            print("使用 pyautogui 截取主螢幕")
                        except Exception as e:
                            print(f"❌ MSS 截圖失敗: {e}，使用 pyautogui 備用方案")
                            import pyautogui
                            screenshot = pyautogui.screenshot()
                            print("使用 pyautogui 截取主螢幕")'''

def update_file(filename):
    """更新檔案中的截圖代碼"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 尋找並替換 "方法2" 的截圖代碼
        # 使用更寬鬆的模式匹配
        pattern = r'# 方法2:.*?screenshot = pyautogui\.screenshot\(\)\s*print\("使用 pyautogui 截取主螢幕"\)'
        
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, new_screenshot_code.strip(), content, flags=re.DOTALL)
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 已更新 {filename}")
            return True
        else:
            print(f"⚪ {filename} 沒有找到需要更新的代碼")
            return False
            
    except Exception as e:
        print(f"❌ 更新 {filename} 失敗: {e}")
        return False

def main():
    files_to_update = [
        'ettoday_replace.py',
        'udn_replace.py', 
        'liulife_replace.py'
    ]
    
    for filename in files_to_update:
        update_file(filename)

if __name__ == "__main__":
    main()