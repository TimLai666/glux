#!/usr/bin/env python3
"""
使用 llvmlite.binding JIT 執行 LLVM IR 文件
"""

import sys
import logging
from llvmlite import binding
import ctypes
import io
import contextlib
import os

# 設置基本日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLVMIRRunner")

def read_llvm_ir(file_path):
    """讀取 LLVM IR 文件"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"讀取 LLVM IR 文件失敗: {str(e)}")
        return None

def execute_llvm_ir(llvm_ir_str):
    """使用 llvmlite.binding JIT 執行 LLVM IR"""
    
    try:
        # 初始化 LLVM
        binding.initialize()
        binding.initialize_native_target()
        binding.initialize_native_asmprinter()
        
        # 解析 LLVM IR 並驗證
        logger.info("解析 LLVM IR...")
        llvm_mod = binding.parse_assembly(llvm_ir_str)
        logger.info("驗證 LLVM IR...")
        llvm_mod.verify()
        
        # 建立 JIT 編譯器
        logger.info("建立 JIT 編譯器...")
        target = binding.Target.from_default_triple()
        target_machine = target.create_target_machine()
        
        # 添加LLVM生成的函數信息
        logger.info("LLVM 模塊函數:")
        for func in llvm_mod.functions:
            logger.info(f"  - {func.name}")
        
        logger.info("準備執行...")
        with binding.create_mcjit_compiler(llvm_mod, target_machine) as engine:
            engine.finalize_object()
            engine.run_static_constructors()
            
            # 獲取並執行 `main` 函數
            try:
                main_func = engine.get_function_address("main")
            except Exception as e:
                logger.error(f"無法獲取 main 函數: {str(e)}")
                main_func = engine.get_function_address("_main")  # 嘗試使用 _main
            
            main_cfunc = ctypes.CFUNCTYPE(ctypes.c_int)(main_func)
            
            logger.info("開始執行 main 函數...")
            
            # 捕獲標準輸出
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            new_stdout = io.StringIO()
            new_stderr = io.StringIO()
            
            sys.stdout = new_stdout
            sys.stderr = new_stderr
            
            try:
                return_code = main_cfunc()
            finally:
                # 恢復標準輸出
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            # 獲取捕獲的輸出
            stdout_output = new_stdout.getvalue()
            stderr_output = new_stderr.getvalue()
            
            if stdout_output:
                print("\n--- 標準輸出 ---")
                print(stdout_output)
            
            if stderr_output:
                print("\n--- 標準錯誤 ---")
                print(stderr_output)
            
            logger.info(f"執行完成，返回碼: {return_code}")
            return return_code
            
    except Exception as e:
        logger.error(f"執行 LLVM IR 時發生錯誤: {str(e)}")
        return -1

def main():
    """主函數"""
    if len(sys.argv) < 2:
        print(f"用法: {sys.argv[0]} <llvm_ir_file>")
        return -1
    
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return -1
    
    logger.info(f"讀取 LLVM IR 文件: {file_path}")
    
    llvm_ir = read_llvm_ir(file_path)
    if not llvm_ir:
        return -1
    
    # 添加 LLVM IR 文件內容的前幾行作為調試信息
    ir_lines = llvm_ir.split('\n')
    logger.info(f"LLVM IR 文件前5行:")
    for i in range(min(5, len(ir_lines))):
        logger.info(f"  {ir_lines[i]}")
    
    return execute_llvm_ir(llvm_ir)

if __name__ == "__main__":
    sys.exit(main()) 