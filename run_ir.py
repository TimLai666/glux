#!/usr/bin/env python3
import sys
from src.glux.utils.ir_executor import IRExecutor

def main():
    """執行指定的LLVM IR文件"""
    if len(sys.argv) < 2:
        print("用法: python run_ir.py <IR文件路徑>")
        return 1
        
    ir_file_path = sys.argv[1]
    print(f"正在讀取IR文件: {ir_file_path}")
    
    try:
        with open(ir_file_path, 'r', encoding='utf-8') as f:
            ir_content = f.read()
    except Exception as e:
        print(f"讀取文件失敗: {e}")
        return 1
    
    print("正在執行IR...")
    try:
        executor = IRExecutor()
        exit_code, stdout, stderr = executor.execute(ir_content, is_ir=True)
        
        print(f"執行結果 (退出碼: {exit_code})")
        if stdout:
            print("\n標準輸出:")
            print(stdout)
        
        if stderr:
            print("\n標準錯誤:")
            print(stderr)
            
        return exit_code
    except Exception as e:
        print(f"執行失敗: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 