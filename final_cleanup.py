#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def clean_all_region_calls(filename):
    """清理檔案中所有的 region 調用"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 替換所有 pyautogui.screenshot(region=(...)) 為 pyautogui.screenshot()
        content = re.sub(
            r'pyautogui\.screenshot\(region=\([^)]+\)\)',
            'pyautogui.screenshot()',
            content
        )
        
        if content != original_content:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 計算修改次數
            changes = len(re.findall(r'pyautogui\.screenshot\(region=\([^)]+\)\)', original_content))
            print(f"✅ {filename} 已清理，共修改 {changes} 處")
            return True
        else:
            print(f"⚪ {filename} 無需清理")
            return False
            
    except Exception as e:
        print(f"❌ 清理 {filename} 失敗: {e}")
        return False

def main():
    files_to_clean = [
        'ad_replacer.py',
        'yahoo_replace.py',
        'ettoday_replace.py',
        'udn_replace.py',
        'liulife_replace.py'
    ]
    
    total_cleaned = 0
    for filename in files_to_clean:
        if clean_all_region_calls(filename):
            total_cleaned += 1
    
    print(f"\n總共清理了 {total_cleaned} 個檔案")

if __name__ == "__main__":
    main()