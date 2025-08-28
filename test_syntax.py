#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試 linshibi_replace.py 的語法
"""

import ast
import sys

def test_syntax(filename):
    """測試 Python 檔案的語法"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # 嘗試解析語法
        ast.parse(source)
        print(f"✅ {filename} 語法正確")
        return True
        
    except SyntaxError as e:
        print(f"❌ {filename} 語法錯誤:")
        print(f"   行 {e.lineno}: {e.text}")
        print(f"   錯誤: {e.msg}")
        return False
    except Exception as e:
        print(f"❌ 檢查 {filename} 時發生錯誤: {e}")
        return False

if __name__ == "__main__":
    print("🧪 語法檢查測試")
    print("=" * 30)
    
    files_to_test = ['linshibi_replace.py']
    
    all_passed = True
    for filename in files_to_test:
        if not test_syntax(filename):
            all_passed = False
    
    if all_passed:
        print("\n🎉 所有檔案語法正確！")
    else:
        print("\n💥 發現語法錯誤！")