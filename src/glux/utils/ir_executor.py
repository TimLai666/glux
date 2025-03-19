"""
LLVM IR 執行與保存功能
"""

import os
import ctypes
import logging
from typing import Optional, Any, List
from llvmlite import binding


class IRExecutor:
    """
    LLVM IR 執行器類
    負責執行和管理 LLVM IR
    """
    
    def __init__(self, binary_file: str, logger: Optional[logging.Logger] = None):
        """
        初始化 IR 執行器
        
        Args:
            binary_file: 二進制文件路徑
            logger: 日誌器
        """
        self.binary_file = binary_file
        self.logger = logger or logging.getLogger("IRExecutor")
    
    def execute(self, function_name: str = "main", args: List[str] = None) -> int:
        """
        執行指定函數
        
        Args:
            function_name: 函數名稱
            args: 函數參數
            
        Returns:
            執行結果代碼
        """
        import subprocess
        
        try:
            args = args or []
            cmd = [self.binary_file] + args
            self.logger.debug(f"執行命令: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.stdout:
                print(result.stdout)
            
            if result.stderr:
                self.logger.error(f"執行錯誤: {result.stderr}")
            
            return result.returncode
        except Exception as e:
            self.logger.error(f"執行過程中發生錯誤: {str(e)}")
            return -1


def save_llvm_ir(llvm_ir: Any, filename: str) -> None:
    """
    將 LLVM IR 保存到文件
    
    Args:
        llvm_ir: LLVM IR 模組
        filename: 輸出文件名
    """
    with open(filename, "w") as f:
        f.write(str(llvm_ir))


def execute_llvm_ir(llvm_ir: Any) -> int:
    """
    使用 `llvmlite.binding` JIT 即時編譯並執行 LLVM IR
    
    Args:
        llvm_ir: LLVM IR 模組或字符串
        
    Returns:
        main 函數的返回值
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 初始化 LLVM
        binding.initialize()
        binding.initialize_native_target()
        binding.initialize_native_asmprinter()

        # 確保輸入是字符串形式的 LLVM IR
        llvm_ir_str = str(llvm_ir)
        
        # 解析 LLVM IR 並驗證
        try:
            llvm_mod = binding.parse_assembly(llvm_ir_str)
        except RuntimeError as e:
            logger.error(f"LLVM IR 解析錯誤: {str(e)}")
            return -1
            
        try:
            llvm_mod.verify()
        except RuntimeError as e:
            logger.error(f"LLVM IR 驗證錯誤: {str(e)}")
            return -1
        
        # 輸出可用函數
        logger.debug("LLVM 模塊中的函數:")
        for func in llvm_mod.functions:
            logger.debug(f"  - {func.name}")

        # 建立 JIT 編譯器
        target = binding.Target.from_default_triple()
        target_machine = target.create_target_machine()
        
        # 注意：目前無法直接捕獲 LLVM JIT 執行時的輸出，因為標準輸出是通過 LLVM 的外部函數實現的
        # 在 Glux 中的輸出是直接通過調用 C 標準庫的 printf/puts 函數實現的
        # 這些調用會直接輸出到 Python 解釋器的標準輸出，而不經過 Python 的 stdout
        
        try:
            with binding.create_mcjit_compiler(llvm_mod, target_machine) as engine:
                engine.finalize_object()
                engine.run_static_constructors()

                # 獲取並執行 `main` 函數
                try:
                    main_func = engine.get_function_address("main")
                    main_cfunc = ctypes.CFUNCTYPE(ctypes.c_int)(main_func)
                    
                    # 執行主函數
                    logger.debug("開始執行 main 函數")
                    return_code = main_cfunc()
                    logger.debug(f"main 函數執行完成，返回代碼: {return_code}")
                    
                    return return_code
                except Exception as e:
                    logger.error(f"執行 main 函數時發生錯誤: {str(e)}")
                    return -1
        except Exception as e:
            logger.error(f"創建或使用 JIT 編譯器時發生錯誤: {str(e)}")
            return -1
            
    except Exception as e:
        logger.error(f"執行 LLVM IR 時發生未知錯誤: {str(e)}")
        return -1


def compile_to_machine_code(llvm_ir: Any, output_file: str, file_type: str = "obj") -> None:
    """
    將 LLVM IR 編譯為機器碼
    
    Args:
        llvm_ir: LLVM IR 模組或字符串
        output_file: 輸出文件名
        file_type: 輸出文件類型，可以是 "obj" (目標文件) 或 "asm" (彙編文件)
    """
    binding.initialize()
    binding.initialize_native_target()
    binding.initialize_native_asmprinter()

    # 確保輸入是字符串形式的 LLVM IR
    llvm_ir_str = str(llvm_ir)
    
    # 解析 LLVM IR 並驗證
    llvm_mod = binding.parse_assembly(llvm_ir_str)
    llvm_mod.verify()

    # 建立目標機器
    target = binding.Target.from_default_triple()
    target_machine = target.create_target_machine()
    
    # 決定輸出類型
    if file_type == "obj":
        output = target_machine.emit_object(llvm_mod)
    elif file_type == "asm":
        output = target_machine.emit_assembly(llvm_mod)
    else:
        raise ValueError(f"不支持的輸出類型: {file_type}")
    
    # 保存到文件
    with open(output_file, "wb") as f:
        f.write(output) 