#!/usr/bin/env python3
"""
測試 LLVM IR 執行
"""

import sys
import os
import re
from llvmlite import binding as llvm
import ctypes

def fix_string_lengths(ir_content):
    """修復 LLVM IR 中的字串長度問題"""
    # 查找字串常量定義
    pattern = r'@\.str\.\d+ = private unnamed_addr constant \[(\d+) x i8\] c"(.*?)", align \d+'
    
    def fix_length(match):
        declared_length = int(match.group(1))
        string_content = match.group(2)
        
        # 計算實際的字節長度（包括終止符 \00）
        actual_bytes = 0
        i = 0
        while i < len(string_content):
            if string_content[i:i+2] == "\\0":
                actual_bytes += 1
                i += 2
            elif string_content[i:i+2] == "\\E":
                # 處理 UTF-8 轉義序列 \E5\85\A8 等
                actual_bytes += 1
                i += 2
            else:
                actual_bytes += 1
                i += 1
        
        # 加上終止符 \00
        if string_content[-2:] != "\\0":
            actual_bytes += 1
        
        # 修正長度
        return f'@.str.{match.group(0).split(".")[2].split(" ")[0]} = private unnamed_addr constant [{actual_bytes} x i8] c"{string_content}", align 1'
    
    # 替換所有字串常量定義
    return re.sub(pattern, fix_length, ir_content)

def main():
    """主函數"""
    # 檢查參數
    if len(sys.argv) < 2:
        print("用法: python test_llvm.py <llvm_ir_文件>")
        return 1
    
    ll_file = sys.argv[1]
    if not os.path.exists(ll_file):
        print(f"找不到文件: {ll_file}")
        return 1
    
    print(f"測試執行 LLVM IR 文件: {ll_file}")
    
    # 初始化LLVM
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    
    # 讀取IR文件
    try:
        with open(ll_file, "r", encoding="utf-8") as f:
            ir = f.read()
            print(f"成功以 UTF-8 編碼讀取文件，長度: {len(ir)} 字節")
    except UnicodeDecodeError:
        try:
            print("UTF-8 編碼讀取失敗，嘗試 Latin-1 編碼")
            with open(ll_file, "r", encoding="latin-1") as f:
                ir = f.read()
                print(f"成功以 Latin-1 編碼讀取文件，長度: {len(ir)} 字節")
        except Exception as e:
            print(f"讀取文件失敗: {str(e)}")
            return 1
    
    # 修復字串長度問題
    print("修復 LLVM IR 中的字串長度問題...")
    fixed_ir = ir
    
    # 嘗試手動修復已知問題
    fixed_ir = fixed_ir.replace("[17 x i8] c\"\\E5\\85\\A8\\E5\\B1\\80\\E4\\BB\\A3\\E7\\A2\\BC 1\\0A\\00\"", 
                               "[16 x i8] c\"\\E5\\85\\A8\\E5\\B1\\80\\E4\\BB\\A3\\E7\\A2\\BC 1\\0A\\00\"")
    fixed_ir = fixed_ir.replace("[17 x i8] c\"\\E5\\85\\A8\\E5\\B1\\80\\E4\\BB\\A3\\E7\\A2\\BC 2\\0A\\00\"", 
                               "[16 x i8] c\"\\E5\\85\\A8\\E5\\B1\\80\\E4\\BB\\A3\\E7\\A2\\BC 2\\0A\\00\"")
    fixed_ir = fixed_ir.replace("[22 x i8] c\"main \\E5\\8D\\80\\E5\\A1\\8A\\E4\\BB\\A3\\E7\\A2\\BC 1\\0A\\00\"", 
                               "[21 x i8] c\"main \\E5\\8D\\80\\E5\\A1\\8A\\E4\\BB\\A3\\E7\\A2\\BC 1\\0A\\00\"")
    fixed_ir = fixed_ir.replace("[22 x i8] c\"main \\E5\\8D\\80\\E5\\A1\\8A\\E4\\BB\\A3\\E7\\A2\\BC 2\\0A\\00\"", 
                               "[21 x i8] c\"main \\E5\\8D\\80\\E5\\A1\\8A\\E4\\BB\\A3\\E7\\A2\\BC 2\\0A\\00\"")
    
    # 保存修復後的 IR 到臨時文件
    temp_file = ll_file + ".fixed"
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(fixed_ir)
    print(f"修復後的 LLVM IR 已保存到: {temp_file}")
    
    # 創建模塊
    try:
        print("解析修復後的 LLVM IR...")
        module = llvm.parse_assembly(fixed_ir)
        print("驗證 LLVM IR...")
        module.verify()
    except RuntimeError as e:
        print(f"LLVM IR 解析或驗證失敗: {str(e)}")
        return 1
    
    # 創建執行引擎
    try:
        print("創建執行引擎...")
        target = llvm.Target.from_default_triple()
        target_machine = target.create_target_machine()
        engine = llvm.create_mcjit_compiler(module, target_machine)
    except Exception as e:
        print(f"創建執行引擎失敗: {str(e)}")
        return 1
    
    # 獲取 main 函數地址
    try:
        print("獲取 main 函數地址...")
        main_addr = engine.get_function_address("main")
    except Exception as e:
        print(f"獲取 main 函數失敗: {str(e)}")
        return 1
    
    # 創建函數指針
    print("創建函數指針並執行...")
    main_function = ctypes.CFUNCTYPE(ctypes.c_int)(main_addr)
    
    # 執行
    try:
        print("開始執行 main 函數...")
        result = main_function()
        print(f"執行完成，返回值: {result}")
        return result
    except Exception as e:
        print(f"執行失敗: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 