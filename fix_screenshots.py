#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import os

def fix_screenshot_calls(filename):
    """修復檔案中的 pyautogui.screenshot() 調用"""
    print(f"修復 {filename}...")
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 計算修改次數
    original_content = content
    
    # 替換所有使用 region 參數的 pyautogui.screenshot() 調用
    # 模式1: pyautogui.screenshot(region=(...))
    content = re.sub(
        r'pyautogui\.screenshot\(region=\([^)]+\)\)',
        'pyautogui.screenshot()',
        content
    )
    
    # 檢查是否有修改
    if content != original_content:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 計算修改次數
        changes = len(re.findall(r'pyautogui\.screenshot\(region=\([^)]+\)\)', original_content))
        print(f"✅ {filename} 已修復，共修改 {changes} 處")
        return True
    else:
        print(f"⚪ {filename} 無需修改")
        return False

def main():
    files_to_fix = [
        'yahoo_replace.py',
        'ettoday_replace.py', 
        'udn_replace.py',
        'liulife_replace.py'
    ]
    
    total_fixed = 0
    for filename in files_to_fix:
        if os.path.exists(filename):
            if fix_screenshot_calls(filename):
                total_fixed += 1
        else:
            print(f"❌ 檔案不存在: {filename}")
    
    print(f"\n總共修復了 {total_fixed} 個檔案")

if __name__ == "__main__":
    main()