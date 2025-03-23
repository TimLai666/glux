"""
LLVM IR 執行與保存功能
"""

import os
import ctypes
import logging
import subprocess
import tempfile
from typing import Optional, Any, List, Tuple
from llvmlite import binding
import re

# 嘗試導入 LLVM Python 綁定
try:
    import llvmlite.binding as llvm
    LLVMLITE_AVAILABLE = True
except ImportError:
    LLVMLITE_AVAILABLE = False


class IRExecutor:
    """
    LLVM IR 執行器類
    負責執行和管理 LLVM IR
    """
    
    def __init__(self, verbose=False):
        """
        初始化執行器
        
        Args:
            verbose: 是否啟用詳細日誌
        """
        self.verbose = verbose
        self.logger = logging.getLogger(__name__)
        self.errors = []
        
        # 初始化 LLVM
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        self.logger.info("成功初始化LLVM綁定")
    
    def execute(self, ir_content):
        """
        執行 LLVM IR 代碼
        
        Args:
            ir_content: LLVM IR 字符串
        
        Returns:
            退出碼
        """
        self.logger.info("開始執行LLVM IR...")
        self.logger.info("成功讀取LLVM IR內容")
        
        # 解析 IR
        self.logger.info("開始解析LLVM IR...")
        try:
            # 嘗試解析 IR
            ir_module = llvm.parse_assembly(ir_content)
            ir_module.verify()
            
            # 創建執行引擎
            target_machine = llvm.Target.from_default_triple().create_target_machine()
            engine = llvm.create_mcjit_compiler(ir_module, target_machine)
            
            # 獲取 main 函數
            main_func_ptr = engine.get_function_address("main")
            
            # 將函數指針轉換為 Python 函數
            cfunc = ctypes.CFUNCTYPE(ctypes.c_int)(main_func_ptr)
            
            # 執行 main 函數
            result = cfunc()
            print(f"程序執行成功，返回值: {result}")
            return 0
            
        except Exception as e:
            self.logger.error(f"執行LLVM IR時發生錯誤: {str(e)}")
            print(f"執行LLVM IR時發生錯誤: {str(e)}")
            return 1
    
    def _is_llvm_ir(self, file_path: str) -> bool:
        """
        檢查文件是否為LLVM IR
        
        Args:
            file_path: 文件路徑
        
        Returns:
            是否為LLVM IR文件
        """
        # 檢查文件擴展名
        if file_path.endswith('.ll'):
            return True
        
        # 讀取文件前幾行，檢查是否包含LLVM IR特徵
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_lines = ''.join([f.readline() for _ in range(5)])
                return 'target datalayout' in first_lines or 'target triple' in first_lines
        except Exception as e:
            self.logger.error(f"讀取文件失敗: {str(e)}")
            return False
    
    def _execute_llvm_ir(self, ir_or_file: str, args: List[str] = None, is_ir_content: bool = False) -> Tuple[int, str, str]:
        """
        執行LLVM IR代碼
        
        Args:
            ir_or_file: LLVM IR內容或文件路徑
            args: 命令行參數
            is_ir_content: 指示傳入的是LLVM IR字符串還是文件路徑
        
        Returns:
            退出碼, 標準輸出, 標準錯誤
        """
        # 檢查是否支持JIT
        if not llvm:
            self.logger.error("未安裝llvmlite，無法使用JIT執行")
            return 1, "", "未安裝llvmlite，無法使用JIT執行"
        
        self.logger.info("開始執行LLVM IR...")
        
        try:
            # 獲取IR內容
            ir_content = ir_or_file if is_ir_content else self._read_file(ir_or_file)
            if not ir_content:
                return 1, "", "無法讀取LLVM IR內容"
            
            self.logger.info("成功讀取LLVM IR內容")
            
            # 修復字符串長度不匹配問題
            ir_content = self._fix_string_length_mismatch(ir_content)
            
            self.logger.info("開始解析LLVM IR...")
            
            # 使用llvmlite解析IR
            ir_module = llvm.parse_assembly(ir_content)
            ir_module.verify()
            
            self.logger.info("成功解析LLVM IR，正在創建執行引擎...")
            
            # 創建執行引擎
            target_machine = llvm.Target.from_default_triple().create_target_machine()
            engine = llvm.create_mcjit_compiler(ir_module, target_machine)
            
            self.logger.info("成功創建執行引擎，準備執行LLVM IR...")
            
            # 嘗試添加全局映射以支持外部函數
            try:
                # 在macOS上，直接使用None或空字符串可能會失敗
                # 我們跳過這一步，因為大多數Glux程序不需要直接調用外部函數
                # 註釋掉這一行： llvm.load_library_permanently('')
                pass
            except Exception as e:
                self.logger.warning(f"載入進程符號失敗，但繼續執行: {str(e)}")
            
            # 設置環境變量以傳遞參數
            old_environ = os.environ.copy()
            try:
                # 將參數設置為環境變量
                os.environ["GLUX_ARG_COUNT"] = str(len(args or []))
                for i, arg in enumerate(args or []):
                    os.environ[f"GLUX_ARG_{i}"] = arg
                
                # 重定向標準輸出和錯誤
                self.logger.info("準備重定向標準輸出和標準錯誤...")
                
                with tempfile.NamedTemporaryFile(delete=False, mode='w+', encoding='utf-8') as stdout_file, \
                     tempfile.NamedTemporaryFile(delete=False, mode='w+', encoding='utf-8') as stderr_file:
                    
                    stdout_path, stderr_path = stdout_file.name, stderr_file.name
                    self.logger.info(f"標准輸出重定向到: {stdout_path}")
                    self.logger.info(f"標准錯誤重定向到: {stderr_path}")
                    
                    # 保存原始文件描述符
                    old_stdout_fd = os.dup(1)
                    old_stderr_fd = os.dup(2)
                    
                    # 重定向到臨時文件
                    os.dup2(stdout_file.fileno(), 1)
                    os.dup2(stderr_file.fileno(), 2)
                    
                    try:
                        # 獲取主函數地址並執行
                        self.logger.info("獲取main函數地址並執行...")
                        main_addr = engine.get_function_address("main")
                        import ctypes
                        cfunc = ctypes.CFUNCTYPE(ctypes.c_int)(main_addr)
                        exit_code = cfunc()
                        self.logger.info(f"執行完成，退出碼：{exit_code}")
                    finally:
                        # 恢復標準輸出和錯誤
                        os.dup2(old_stdout_fd, 1)
                        os.dup2(old_stderr_fd, 2)
                        os.close(old_stdout_fd)
                        os.close(old_stderr_fd)
                        self.logger.info("已恢復標準輸出和標準錯誤")
                
                # 讀取捕獲的輸出
                self.logger.info("讀取捕獲的輸出...")
                with open(stdout_path, 'r', encoding='utf-8') as f:
                    stdout = f.read()
                    self.logger.info(f"標準輸出內容長度: {len(stdout)} 字節")
                    self.logger.info(f"標準輸出內容: {stdout!r}")
                
                with open(stderr_path, 'r', encoding='utf-8') as f:
                    stderr = f.read()
                    self.logger.info(f"標準錯誤內容長度: {len(stderr)} 字節")
                    if stderr:
                        self.logger.info(f"標準錯誤內容: {stderr!r}")
                
                # 清理臨時文件
                try:
                    os.unlink(stdout_path)
                    os.unlink(stderr_path)
                    self.logger.info("已清理臨時文件")
                except:
                    self.logger.warning("清理臨時文件失敗")
                    pass
                
                self.logger.info("LLVM IR執行完成")
                return exit_code, stdout, stderr
            finally:
                # 恢復原始環境變量
                os.environ.clear()
                os.environ.update(old_environ)
                
        except Exception as e:
            self.logger.error(f"執行LLVM IR時發生錯誤: {str(e)}")
            import traceback
            error_details = traceback.format_exc()
            self.logger.debug(error_details)
            return 1, "", f"執行LLVM IR時發生錯誤: {str(e)}\n{error_details}"
    
    def _execute_binary(self, binary_path: str, args: List[str]) -> Tuple[int, str, str]:
        """
        執行二進制文件
        
        Args:
            binary_path: 二進制文件路徑
            args: 命令行參數
        
        Returns:
            退出碼, 標準輸出, 標準錯誤
        """
        # 檢查文件是否存在
        if not os.path.exists(binary_path):
            self.logger.error(f"二進制文件不存在: {binary_path}")
            return 1, "", f"二進制文件不存在: {binary_path}"
        
        # 檢查是否可執行
        if not os.access(binary_path, os.X_OK):
            self.logger.warning(f"文件不可執行，嘗試設置執行權限: {binary_path}")
            try:
                os.chmod(binary_path, 0o755)
            except Exception as e:
                self.logger.error(f"無法設置執行權限: {str(e)}")
                return 1, "", f"無法設置執行權限: {str(e)}"
        
        try:
            # 執行二進制文件
            command = [binary_path] + args
            self.logger.info(f"執行命令: {' '.join(command)}")
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            exit_code = process.returncode
            
            self.logger.info(f"程序退出，退出碼: {exit_code}")
            return exit_code, stdout, stderr
            
        except Exception as e:
            self.logger.error(f"執行二進制文件時發生錯誤: {str(e)}")
            import traceback
            error_details = traceback.format_exc()
            self.logger.debug(error_details)
            return 1, "", f"執行二進制文件時發生錯誤: {str(e)}\n{error_details}"
    
    def _read_file(self, file_path: str) -> Optional[str]:
        """
        讀取文件內容
        
        Args:
            file_path: 文件路徑
        
        Returns:
            文件內容，如果讀取失敗則返回None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"無法讀取文件 {file_path}: {str(e)}")
            return None

    def _fix_string_length_mismatch(self, ir_content: str) -> str:
        """
        修復字符串長度不匹配的問題。
        在實際定義和使用的地方統一字符串長度。
        """
        # 查找所有字符串定義
        str_defs = {}
        def_pattern = re.compile(r'@\.str\.(\d+) = private unnamed_addr constant \[(\d+) x i8\]')
        for match in def_pattern.finditer(ir_content):
            str_idx, length = match.groups()
            str_defs[str_idx] = length
        
        # 查找並修正所有引用
        use_pattern = re.compile(r'getelementptr inbounds \[(\d+) x i8\], \[(\d+) x i8\]\* @\.str\.(\d+)')
        
        def replace_length(match):
            use_len1, use_len2, str_idx = match.groups()
            if str_idx in str_defs:
                correct_len = str_defs[str_idx]
                return f'getelementptr inbounds [{correct_len} x i8], [{correct_len} x i8]* @.str.{str_idx}'
            return match.group(0)
        
        fixed_ir = use_pattern.sub(replace_length, ir_content)
        return fixed_ir


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