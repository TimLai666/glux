import traceback
import sys
import subprocess

try:
    # 使用子進程執行命令，以獲取完整的錯誤輸出
    process = subprocess.run(
        ["python3", "-m", "src.glux.cli", "check", "tests/examples/test_unary_operators.glux"],
        capture_output=True,
        text=True
    )
    
    # 打印輸出
    print("標準輸出：")
    print(process.stdout)
    
    print("\n標準錯誤：")
    print(process.stderr)
    
    # 打印退出碼
    print(f"\n退出碼: {process.returncode}")
except Exception as e:
    traceback.print_exc()
    print(f"錯誤: {e}") 