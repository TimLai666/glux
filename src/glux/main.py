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
            
            # 生成LLVM IR
            llvm_ir = self._generate_llvm_ir(source_code, file_path)
            if not llvm_ir:
                return False
            
            # 保存LLVM IR到文件
            ll_file = f"{output_path}.ll"
            with open(ll_file, 'w', encoding='utf-8') as f:
                f.write(llvm_ir)
            self.logger.info(f"生成 LLVM IR 文件: {ll_file}")
            
            # 嘗試生成二進制文件
            try:
                ast = self._parse_and_analyze(source_code, file_path)
                if not ast:
                    return False
                    
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
    
    def _parse_and_analyze(self, source_code: str, file_path: str) -> Optional[Any]:
        """
        解析源代碼並進行語義分析
        
        Args:
            source_code: 源代碼
            file_path: 文件路徑 (用於錯誤報告)
            
        Returns:
            解析後的AST，如果解析失敗則返回None
        """
        try:
            # 詞法分析
            start_time = time.time()
            self.logger.info("開始詞法分析...")
            lexer = Lexer(source_code, file_path)
            tokens = lexer.tokenize()
            
            if lexer.errors:
                self.logger.error("詞法分析錯誤:")
                for error in lexer.errors:
                    self.logger.error(f"  {error}")
                return None
            
            lexer_time = time.time() - start_time
            self.logger.info(f"詞法分析完成，耗時 {lexer_time:.2f} 秒")
            
            # 語法分析
            start_time = time.time()
            self.logger.info("開始語法分析...")
            parser = Parser(tokens)
            ast = parser.parse()
            
            if parser.errors:
                self.logger.error("語法分析錯誤:")
                for error in parser.errors:
                    self.logger.error(f"  {error}")
                return None
            
            parser_time = time.time() - start_time
            self.logger.info(f"語法分析完成，耗時 {parser_time:.2f} 秒")
            
            # 語義分析
            start_time = time.time()
            self.logger.info("開始語義分析...")
            semantic_analyzer = SemanticAnalyzer()
            if not semantic_analyzer.analyze(ast):
                self.logger.error("語義分析錯誤:")
                for error in semantic_analyzer.get_errors():
                    self.logger.error(f"  {error}")
                return None
            
            semantic_time = time.time() - start_time
            self.logger.info(f"語義分析完成，耗時 {semantic_time:.2f} 秒")
            
            return ast
            
        except Exception as e:
            self.logger.error(f"解析過程發生錯誤: {str(e)}")
            if self.verbose:
                self.logger.exception("詳細錯誤信息:")
            return None
    
    def _generate_llvm_ir(self, source_code: str, file_path: str) -> Optional[str]:
        """
        生成 LLVM IR 代碼
        
        Args:
            source_code: 源代碼
            file_path: 文件路徑 (用於錯誤報告)
        
        Returns:
            LLVM IR 代碼，如果生成失敗則返回None
        """
        ast = self._parse_and_analyze(source_code, file_path)
        if not ast:
            return None
        
        try:
            # 代碼生成
            start_time = time.time()
            self.logger.info("開始生成 LLVM IR 代碼...")
            code_generator = LLVMCodeGenerator()
            llvm_ir = code_generator.generate(ast)
            
            gen_time = time.time() - start_time
            self.logger.info(f"代碼生成完成，耗時 {gen_time:.2f} 秒")
            
            # 調試輸出
            self.logger.debug(f"生成的LLVM IR:\n{llvm_ir}")
            with open("/tmp/debug_llvm_ir.ll", "w") as f:
                f.write(llvm_ir)
            self.logger.info(f"LLVM IR已保存至/tmp/debug_llvm_ir.ll")
            
            return llvm_ir
        except Exception as e:
            self.logger.error(f"代碼生成過程發生錯誤: {str(e)}")
            if self.verbose:
                self.logger.exception("詳細錯誤信息:")
            return None
    
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
            
            return self.run_string(source_code, file_path, args)
        except Exception as e:
            self.logger.error(f"讀取文件失敗: {str(e)}")
            return 1
    
    def run_string(self, source_code: str, file_name: str = "<string>", args: List[str] = None) -> int:
        """
        編譯並執行源代碼字符串
        
        Args:
            source_code: 源代碼
            file_name: 文件名 (用於錯誤報告)
            args: 命令行參數
            
        Returns:
            int: 程序退出碼
        """
        # 強制使用JIT模式
        os.environ["GLUX_JIT_ONLY"] = "1"
        args = args or []
        
        # 生成LLVM IR
        llvm_ir = self._generate_llvm_ir(source_code, file_name)
        if not llvm_ir:
            return 1
        
        try:
            # 執行程序
            self.logger.info("開始使用JIT執行程序...")
            from .utils.ir_executor import IRExecutor
            
            # 保存LLVM IR到臨時文件
            with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as temp_file:
                ir_file = temp_file.name
                temp_file.write(llvm_ir.encode('utf-8'))
                
            # 執行LLVM IR
            executor = IRExecutor()
            exit_code, stdout, stderr = executor.execute(ir_file, args, is_ir=True)
            
            # 清理臨時文件
            try:
                os.unlink(ir_file)
            except:
                pass
            
            # 輸出結果
            if stdout:
                print(stdout)
            if stderr:
                print(stderr, file=sys.stderr)
                
            return exit_code
            
        except Exception as e:
            self.logger.error(f"執行過程發生錯誤: {str(e)}")
            if self.verbose:
                self.logger.exception("詳細錯誤信息:")
            return 1
        
    def _create_jit_wrapper(self, output_path: str, ll_file: str) -> Optional[str]:
        """
        創建一個包裝腳本，使用JIT模式運行LLVM IR
        
        Args:
            output_path: 輸出文件路徑
            ll_file: LLVM IR文件路徑
            
        Returns:
            生成的包裝腳本路徑，如果失敗則返回None
        """
        try:
            # 獲取Python解釋器路徑
            python_path = sys.executable
            
            # 獲取Glux編譯器的安裝路徑
            glux_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            
            # 創建包裝腳本
            if platform.system() == 'Windows':
                # Windows批處理腳本
                wrapper_path = f"{output_path}.bat"
                script_content = f"""@echo off
"{python_path}" -c "import sys; sys.path.insert(0, '{glux_path}'); from src.glux.utils.ir_executor import IRExecutor; executor = IRExecutor(); exit_code, stdout, stderr = executor.execute('{ll_file}', sys.argv[1:], is_ir=True); print(stdout, end=''); print(stderr, end='', file=sys.stderr); sys.exit(exit_code)" %*
"""
            else:
                # Unix shell腳本
                wrapper_path = output_path
                script_content = f"""#!/bin/sh
exec "{python_path}" -c "import sys; sys.path.insert(0, '{glux_path}'); from src.glux.utils.ir_executor import IRExecutor; executor = IRExecutor(); exit_code, stdout, stderr = executor.execute('{ll_file}', sys.argv[1:], is_ir=True); print(stdout, end=''); print(stderr, end='', file=sys.stderr); sys.exit(exit_code)" "$@"
"""
            
            # 寫入腳本
            with open(wrapper_path, 'w') as f:
                f.write(script_content)
            
            # 設置可執行權限
            os.chmod(wrapper_path, 0o755)
            
            return wrapper_path
        except Exception as e:
            self.logger.error(f"創建JIT包裝腳本時發生錯誤: {str(e)}")
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
