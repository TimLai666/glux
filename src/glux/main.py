#!/usr/bin/env python
"""
Glux 編譯器主入口
整合詞法分析、語法分析、語義分析和代碼生成
"""

import os
import sys
import argparse
import logging
import time
import traceback
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
import platform

from .lexer import Lexer, Token
from .parser import Parser
from .analysis.semantic_analyzer import SemanticAnalyzer
from .codegen.code_generator import LLVMCodeGenerator
from .utils.ir_executor import IRExecutor
from .codegen.binary_emitter import BinaryEmitter
from .util.logger import Logger


def setup_logging(verbose=False):
    """
    設置日誌級別
    
    Args:
        verbose: 日誌級別
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


class GluxCompiler:
    """
    Glux 編譯器主類
    整合編譯過程的各個階段
    """
    
    def __init__(self, verbose=False):
        """
        初始化編譯器
        
        Args:
            verbose: 是否顯示詳細信息
        """
        self.verbose = verbose
        self.logger = logging.getLogger("GluxCompiler")
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    def compile_file(self, file_path: str, output_path: str = None) -> bool:
        """
        編譯源文件並生成二進制可執行文件
        
        Args:
            file_path: 源文件路徑
            output_path: 輸出文件路徑，如果為None則使用源文件名
            
        Returns:
            bool: 編譯是否成功
        """
        try:
            # 讀取源文件
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # 設置默認輸出路徑
            if not output_path:
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_dir = os.path.dirname(file_path)
                output_path = os.path.join(output_dir, base_name)
                # 添加平台相關的可執行文件擴展名
                if platform.system() == 'Windows':
                    output_path += '.exe'
            
            # 詞法分析
            self.logger.info("開始詞法分析...")
            lexer = Lexer(source_code, file_path)
            tokens = lexer.tokenize()
            
            if lexer.errors:
                self.logger.error("詞法分析錯誤:")
                for error in lexer.errors:
                    self.logger.error(f"  {error}")
                return False
            
            # 語法分析
            self.logger.info("開始語法分析...")
            parser = Parser(tokens)
            ast = parser.parse()
            
            if parser.errors:
                self.logger.error("語法分析錯誤:")
                for error in parser.errors:
                    self.logger.error(f"  {error}")
                return False
            
            # 語義分析
            self.logger.info("開始語義分析...")
            semantic_analyzer = SemanticAnalyzer()
            if not semantic_analyzer.analyze(ast):
                self.logger.error("語義分析錯誤:")
                for error in semantic_analyzer.get_errors():
                    self.logger.error(f"  {error}")
                return False
            
            # 生成LLVM IR
            self.logger.info("開始生成 LLVM IR 代碼...")
            code_generator = LLVMCodeGenerator()
            code_generator.set_symbol_table(semantic_analyzer.symbol_table)
            llvm_ir = code_generator.generate(ast)
            
            # 保存LLVM IR到文件
            ll_file = f"{output_path}.ll"
            with open(ll_file, 'w', encoding='utf-8') as f:
                f.write(llvm_ir)
            self.logger.info(f"生成 LLVM IR 文件: {ll_file}")
            
            # 嘗試生成二進制文件
            try:
                binary_emitter = BinaryEmitter(ast, output_path)
                binary_file = binary_emitter.emit()
                
                if not binary_file:
                    # 如果生成二進制文件失敗，嘗試使用JIT模式
                    if binary_emitter.errors and any("找不到 LLVM 的 llc 命令" in err for err in binary_emitter.errors):
                        self.logger.warning("使用LLVM工具鏈生成二進制文件失敗，將創建一個包裝腳本以使用JIT模式運行")
                        
                        # 創建一個包裝腳本
                        wrapper_script = self._create_jit_wrapper(output_path, ll_file)
                        if wrapper_script:
                            self.logger.info(f"已創建JIT運行包裝腳本: {wrapper_script}")
                            return True
                        else:
                            self.logger.error("創建JIT運行包裝腳本失敗")
                            return False
                    
                    self.logger.error("生成二進制文件失敗:")
                    for error in binary_emitter.errors:
                        self.logger.error(f"  {error}")
                    return False
                
                self.logger.info(f"成功生成二進制文件: {binary_file}")
                # 設置可執行權限
                os.chmod(binary_file, 0o755)
                return True
            except ImportError as e:
                self.logger.error(f"導入BinaryEmitter失敗: {str(e)}")
                return False
            
        except Exception as e:
            self.logger.error(f"編譯過程發生錯誤: {str(e)}")
            if self.verbose:
                self.logger.exception("詳細錯誤信息:")
            return False
    
    def run_file(self, file_path: str, args: List[str] = None) -> int:
        """
        編譯並執行源文件
        
        Args:
            file_path: 源文件路徑
            args: 命令行參數
            
        Returns:
            int: 程序退出碼
        """
        try:
            # 讀取源文件
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # 詞法分析
            self.logger.info("開始詞法分析...")
            lexer = Lexer(source_code, file_path)
            tokens = lexer.tokenize()
            
            if lexer.errors:
                self.logger.error("詞法分析錯誤:")
                for error in lexer.errors:
                    self.logger.error(f"  {error}")
                return 1
            
            # 語法分析
            self.logger.info("開始語法分析...")
            parser = Parser(tokens)
            ast = parser.parse()
            
            if parser.errors:
                self.logger.error("語法分析錯誤:")
                for error in parser.errors:
                    self.logger.error(f"  {error}")
                return 1
            
            # 語義分析
            self.logger.info("開始語義分析...")
            semantic_analyzer = SemanticAnalyzer()
            if not semantic_analyzer.analyze(ast):
                self.logger.error("語義分析錯誤:")
                for error in semantic_analyzer.get_errors():
                    self.logger.error(f"  {error}")
                return 1
            
            # 生成LLVM IR
            self.logger.info("開始生成 LLVM IR 代碼...")
            code_generator = LLVMCodeGenerator()
            code_generator.set_symbol_table(semantic_analyzer.symbol_table)
            llvm_ir = code_generator.generate(ast)
            
            # 創建臨時文件來存儲IR
            with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as temp_file:
                temp_file.write(llvm_ir.encode('utf-8'))
                temp_file_path = temp_file.name
            
            try:
                # 執行IR
                executor = IRExecutor()
                exit_code, stdout, stderr = executor.execute(temp_file_path, args)
                
                # 輸出結果
                if stdout:
                    print(stdout, end='')
                if stderr:
                    print(stderr, file=sys.stderr, end='')
                
                return exit_code
            finally:
                # 清理臨時文件
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                
        except Exception as e:
            self.logger.error(f"執行過程發生錯誤: {str(e)}")
            if self.verbose:
                self.logger.exception("詳細錯誤信息:")
            return 1
    
    def _create_jit_wrapper(self, output_path: str, ll_file: str) -> Optional[str]:
        """
        創建JIT運行包裝腳本
        
        Args:
            output_path: 輸出路徑
            ll_file: LLVM IR文件路徑
            
        Returns:
            str: 包裝腳本路徑，如果創建失敗則返回None
        """
        try:
            # 創建包裝腳本
            wrapper_path = output_path + '.py'
            
            # 生成包裝腳本內容
            wrapper_content = f'''#!/usr/bin/env python3
import sys
from llvmlite import binding as llvm

def main():
    # 初始化LLVM
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    
    # 讀取IR文件
    with open("{ll_file}", "r") as f:
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
'''
            
            # 寫入包裝腳本
            with open(wrapper_path, 'w', encoding='utf-8') as f:
                f.write(wrapper_content)
            
            # 設置可執行權限
            os.chmod(wrapper_path, 0o755)
            
            return wrapper_path
        except Exception as e:
            self.logger.error(f"創建JIT包裝腳本失敗: {str(e)}")
            return None


def main():
    """
    主函數
    """
    import sys
    import os
    import argparse
    
    # 創建命令行參數解析器
    parser = argparse.ArgumentParser(description='Glux 編譯器')
    
    # 添加參數
    parser.add_argument('file', help='源文件路徑')
    parser.add_argument('-o', '--output', help='輸出文件路徑')
    parser.add_argument('-v', '--verbose', action='store_true', help='詳細日誌')
    parser.add_argument('-r', '--run', action='store_true', help='編譯並執行')
    parser.add_argument('-c', '--compile', action='store_true', help='只編譯，不執行')
    parser.add_argument('-j', '--jit', action='store_true', help='使用 JIT 直接執行 (不需要生成二進制檔案)')
    parser.add_argument('--args', nargs=argparse.REMAINDER, help='程序參數 (在 -- 之後)')
    
    # 解析命令行參數
    args = parser.parse_args()
    
    # 設置日誌級別
    setup_logging(args.verbose)
    logger = logging.getLogger("main")
    
    # 獲取編譯器實例
    compiler = GluxCompiler(args.verbose)
    
    # 獲取文件路徑
    file_path = args.file
    
    # 檢查文件是否存在
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return 1
    
    # 獲取輸出文件路徑
    output_path = args.output
    if not output_path and args.compile:
        # 默認輸出文件路徑
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_path = os.path.join(os.path.dirname(file_path), base_name)
        # 添加平台相關的可執行文件擴展名
        if platform.system() == 'Windows':
            output_path += '.exe'
    
    # 獲取程序參數
    program_args = args.args or []
    
    # 設置環境變量
    if args.jit:
        os.environ["GLUX_JIT_ONLY"] = "1"
    
    # 執行操作
    if args.compile:
        # 只編譯，不執行
        logger.info(f"編譯文件: {file_path}")
        if compiler.compile_file(file_path, output_path):
            logger.info(f"編譯成功: {output_path}")
            return 0
        else:
            logger.error("編譯失敗")
            return 1
    else:
        # 編譯並執行
        logger.info(f"執行文件: {file_path}")
        exit_code = compiler.run_file(file_path, program_args)
        logger.info(f"程序退出，退出碼: {exit_code}")
        return exit_code


if __name__ == "__main__":
    main()
