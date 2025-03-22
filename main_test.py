#!/usr/bin/env python
"""
測試 LLVM IR 執行
"""

import os
import sys
import subprocess
import tempfile

def main():
    """運行測試"""
    # 檢查參數
    if len(sys.argv) < 2:
        print("用法: python main_test.py <glux文件>")
        return 1
    
    file_path = sys.argv[1]
    
    # 獲取虛擬環境中的 Python 執行檔
    venv_dir = ".venv"
    python_executable = os.path.join(venv_dir, "Scripts" if sys.platform == "win32" else "bin", "python")
    
    # 使用 build 命令生成 LLVM IR
    cmd = [python_executable, "main.py", "build", file_path]
    print(f"執行命令: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if result.returncode != 0:
        print(f"編譯失敗: {result.returncode}")
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        return 1
    
    # 運行生成的包裝腳本
    base_name = os.path.splitext(file_path)[0]
    wrapper_script = base_name + ".exe.py"
    if not os.path.exists(wrapper_script):
        print(f"找不到包裝腳本: {wrapper_script}")
        return 1
    
    cmd = [python_executable, wrapper_script]
    print(f"執行命令: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    print(f"退出碼: {result.returncode}")
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
