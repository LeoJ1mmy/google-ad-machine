#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import platform

def install_requirements():
    """安裝必要的依賴"""
    requirements = [
        "selenium==4.15.2",
        "pillow==10.0.1", 
        "pyinstaller==6.1.0"
    ]
    
    for req in requirements:
        print(f"安裝 {req}...")
        subprocess.run([sys.executable, "-m", "pip", "install", req])

def build_executable():
    """打包可執行文件"""
    system = platform.system().lower()
    
    # 基本PyInstaller命令
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed" if system == "windows" else "--console",
        "--name", "AdReplacer",
        "--add-data", "mini.png:.",
        "--add-data", "big.png:.",
        "--add-data", "replacement_config.json:.",
    ]
    
    # 選擇主程序
    if os.path.exists("simple_gui.py"):
        cmd.append("simple_gui.py")
        print("使用簡化版本打包")
    else:
        print("找不到simple_gui.py")
        return False
    
    print(f"執行打包命令: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("✅ 打包成功！")
        print(f"可執行文件位於: dist/AdReplacer{'.exe' if system == 'windows' else ''}")
        return True
    else:
        print("❌ 打包失敗")
        return False

def main():
    print("🚀 廣告替換機器人打包工具")
    print("=" * 40)
    
    # 檢查必要文件
    required_files = ["ad_replacer.py", "mini.png"]
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ 缺少必要文件: {missing_files}")
        return
    
    print("✅ 檢查文件完成")
    
    # 安裝依賴
    print("\n📦 安裝依賴...")
    install_requirements()
    
    # 打包
    print("\n🔨 開始打包...")
    if build_executable():
        print("\n🎊 打包完成！")
    else:
        print("\n❌ 打包失敗")

if __name__ == "__main__":
    main()