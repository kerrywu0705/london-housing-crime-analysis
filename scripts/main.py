"""
London Property 自動執行腳本
============================
自動依序執行所有資料處理流程：
1. download_price.py  - 下載房價數據
2. download_rent.py   - 下載租金數據
3. clean_price.py     - 清洗房價數據
4. clean_rent.py      - 清洗租金數據
5. analysis.py        - 數據分析
"""

import subprocess
import sys
import os
from datetime import datetime

# 設定工作目錄
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

# 執行順序
SCRIPTS = [
    ("download_price.py", ["--range", "2019", "2024"]),
    ("download_rent.py", ["--range", "2019", "2024"]),
    ("clean_price.py", []),
    ("clean_rent.py", []),
    ("analysis.py", []),
]


def run_script(script_name, args=None):
    """執行單一腳本"""
    if args is None:
        args = []

    script_path = os.path.join(SCRIPT_DIR, script_name)

    if not os.path.exists(script_path):
        print(f"[錯誤] 找不到腳本: {script_name}")
        return False

    print(f"\n{'='*60}")
    print(f"[執行中] {script_name}")
    print(f"{'='*60}")

    try:
        cmd = [sys.executable, script_path] + args
        result = subprocess.run(cmd, check=True)
        print(f"[完成] {script_name} 執行成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[錯誤] {script_name} 執行失敗 (返回碼: {e.returncode})")
        return False
    except Exception as e:
        print(f"[錯誤] {script_name} 發生例外: {e}")
        return False


def main():
    """主程式"""
    start_time = datetime.now()

    print("=" * 60)
    print("London Property 自動執行腳本")
    print(f"開始時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    success_count = 0
    fail_count = 0

    for script_name, args in SCRIPTS:
        if run_script(script_name, args):
            success_count += 1
        else:
            fail_count += 1
            # 若有腳本失敗，詢問是否繼續
            user_input = input(f"\n[警告] {script_name} 執行失敗，是否繼續執行? (y/n): ").strip().lower()
            if user_input != 'y':
                print("[中止] 使用者取消執行")
                break

    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "=" * 60)
    print("執行摘要")
    print("=" * 60)
    print(f"結束時間: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"總耗時: {duration}")
    print(f"成功: {success_count} 個腳本")
    print(f"失敗: {fail_count} 個腳本")
    print("=" * 60)

    if fail_count == 0:
        print("\n[完成] 所有腳本執行成功!")
    else:
        print(f"\n[警告] 有 {fail_count} 個腳本執行失敗，請檢查錯誤訊息")


if __name__ == "__main__":
    main()
