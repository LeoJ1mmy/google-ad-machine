#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
語法測試腳本
"""

try:
    # 嘗試導入 nicklee_replace 模組來檢查語法
    import ast
    
    print("🔍 檢查 nicklee_replace.py 語法...")
    
    with open('nicklee_replace.py', 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # 嘗試解析 AST
    ast.parse(source_code)
    print("✅ 語法檢查通過！")
    
    # 嘗試編譯
    compile(source_code, 'nicklee_replace.py', 'exec')
    print("✅ 編譯檢查通過！")
    
    print("\n🎉 nicklee_replace.py 語法完全正確，可以安全運行！")
    
except SyntaxError as e:
    print(f"❌ 語法錯誤: {e}")
    print(f"   行號: {e.lineno}")
    print(f"   位置: {e.offset}")
    print(f"   錯誤文本: {e.text}")
    
except Exception as e:
    print(f"❌ 其他錯誤: {e}")