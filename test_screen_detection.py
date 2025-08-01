#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import platform
import subprocess

def test_screen_detection():
    """測試螢幕檢測和截圖的一致性"""
    print("=== 螢幕檢測測試 ===")
    
    system = platform.system()
    print(f"作業系統: {system}")
    
    if system == "Windows":
        print("\n1. 使用 PowerShell 檢測螢幕:")
        try:
            powershell_cmd = '''
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.Screen]::AllScreens | ForEach-Object {
                $index = [Array]::IndexOf([System.Windows.Forms.Screen]::AllScreens, $_) + 1
                Write-Output "螢幕 $index : $($_.Bounds.Width)x$($_.Bounds.Height) Primary:$($_.Primary)"
            }
            '''
            result = subprocess.run(['powershell', '-Command', powershell_cmd], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print(result.stdout)
            else:
                print(f"PowerShell 失敗: {result.stderr}")
        except Exception as e:
            print(f"PowerShell 檢測失敗: {e}")
        
        print("\n2. 使用 MSS 檢測螢幕:")
        try:
            import mss
            with mss.mss() as sct:
                monitors = sct.monitors
                print(f"MSS 偵測到 {len(monitors)} 個監視器 (包含組合螢幕):")
                for i, monitor in enumerate(monitors):
                    if i == 0:
                        print(f"  monitors[{i}] (組合螢幕): {monitor}")
                    else:
                        print(f"  monitors[{i}] (螢幕 {i}): {monitor}")
                        
                print(f"\n實際可用螢幕數量: {len(monitors) - 1}")
                print("螢幕對應關係:")
                for i in range(1, len(monitors)):
                    print(f"  使用者選擇螢幕 {i} → MSS monitors[{i}]")
                    
        except ImportError:
            print("MSS 未安裝")
        except Exception as e:
            print(f"MSS 檢測失敗: {e}")
            
        print("\n3. 測試截圖:")
        try:
            import mss
            from PIL import Image
            import os
            
            with mss.mss() as sct:
                monitors = sct.monitors
                
                # 測試每個螢幕的截圖
                for screen_id in range(1, len(monitors)):
                    try:
                        monitor = monitors[screen_id]
                        screenshot_mss = sct.grab(monitor)
                        screenshot = Image.frombytes('RGB', screenshot_mss.size, screenshot_mss.bgra, 'raw', 'BGRX')
                        
                        # 保存測試截圖
                        test_filename = f"test_screen_{screen_id}.png"
                        screenshot.save(test_filename)
                        print(f"✅ 螢幕 {screen_id} 截圖成功: {test_filename} ({screenshot.size})")
                        
                    except Exception as e:
                        print(f"❌ 螢幕 {screen_id} 截圖失敗: {e}")
                        
        except Exception as e:
            print(f"截圖測試失敗: {e}")
    
    elif system == "Darwin":  # macOS
        print("\n1. 使用 system_profiler 檢測螢幕:")
        try:
            cmd = "system_profiler SPDisplaysDataType | grep -A 2 'Resolution:'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(result.stdout)
            else:
                print("system_profiler 失敗")
        except Exception as e:
            print(f"system_profiler 檢測失敗: {e}")
            
        print("\n2. 使用 AppleScript 檢測螢幕:")
        try:
            applescript = '''
            tell application "Finder"
                set screenCount to count of desktop
                return screenCount
            end tell
            '''
            result = subprocess.run(['osascript', '-e', applescript], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                screen_count = int(result.stdout.strip())
                print(f"偵測到 {screen_count} 個螢幕")
            else:
                print("AppleScript 失敗")
        except Exception as e:
            print(f"AppleScript 檢測失敗: {e}")
    
    else:  # Linux
        print("\n1. 使用 xrandr 檢測螢幕:")
        try:
            result = subprocess.run(['xrandr'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                screen_id = 1
                for line in lines:
                    if ' connected' in line:
                        print(f"螢幕 {screen_id}: {line}")
                        screen_id += 1
            else:
                print("xrandr 失敗")
        except FileNotFoundError:
            print("xrandr 命令未找到")
        except Exception as e:
            print(f"xrandr 檢測失敗: {e}")

if __name__ == "__main__":
    test_screen_detection()