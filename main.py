from lexer import lexer
from parser import Parser
from llvm_generator import LLVMGenerator

from llvmlite import binding
import os

import os
from llvmlite import binding

def save_ll(ir, filename):
    with open(filename, "w") as f:
        f.write(str(ir))

def run_llc(filename):
    with open (filename, "r") as file:
        ir=file.read()
        execute_llvm_ir(ir)
        

def execute_llvm_ir(llvm_ir):
    """使用 `llvmlite.binding` JIT 即時編譯並執行 LLVM IR"""
    binding.initialize()
    binding.initialize_native_target()
    binding.initialize_native_asmprinter()

    llvm_mod = binding.parse_assembly(str(llvm_ir))
    llvm_mod.verify()

    # 建立 JIT 編譯器
    target = binding.Target.from_default_triple()
    target_machine = target.create_target_machine()
    with binding.create_mcjit_compiler(llvm_mod, target_machine) as engine:
        engine.finalize_object()
        engine.run_static_constructors()

        # 執行 `main` 函數
        main_func = engine.get_function_address("main")
        import ctypes
        main_cfunc = ctypes.CFUNCTYPE(ctypes.c_int)(main_func)
        return main_cfunc()


if __name__ == "__main__":
    # 產生 LLVM IR
    code = """
    a := -400
    print(a - 3)
    """

    tokens = lexer(code)
    print(tokens)  # 先打印 Token，確認正確
    parser = Parser(tokens)
    ast = parser.parse()

    llvm_gen = LLVMGenerator()
    llvm_ir = llvm_gen.generate(ast)
    print(llvm_ir)  # 先打印 LLVM IR，確認正確

    # JIT 執行 LLVM IR
    result = execute_llvm_ir(llvm_ir)
    save_ll(llvm_ir, "output.ll")
    print("執行結果:", result)
