#!/usr/bin/env python3
import sys
from llvmlite import binding as llvm

def main():
    # 初始化LLVM
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    
    # 讀取IR文件
    with open("main_test.ll", "r") as f:
        ir = f.read()
    
    # 創建模塊
    module = llvm.parse_assembly(ir)
    module.verify()
    
    # 創建執行引擎
    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()
    engine = llvm.create_mcjit_compiler(module, target_machine)
    
    # 獲取main函數地址
    main_addr = engine.get_function_address("main")
    
    # 創建函數指針
    from ctypes import CFUNCTYPE, c_int
    main_function = CFUNCTYPE(c_int)(main_addr)
    
    # 執行
    result = main_function()
    return result

if __name__ == "__main__":
    sys.exit(main())
