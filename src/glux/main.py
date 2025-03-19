#!/usr/bin/env python
"""
Glux 編譯器主入口
整合詞法分析、語法分析、語義分析和代碼生成
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple

from .lexer import Lexer, Token
from .parser.parser import Parser
from .type_system.type_system import TypeSystem
from .codegen.code_generator import LLVMCodeGenerator
from .utils.ir_executor import IRExecutor
from .analysis.semantic_analyzer import SemanticAnalyzer
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
    
    def compile_file(self, file_path: str, output_path: Optional[str] = None) -> bool:
        """
        編譯單個文件
        
        Args:
            file_path: 輸入文件路徑
            output_path: 輸出文件路徑
            
        Returns:
            是否成功
        """
        source_code = self._read_file(file_path)
        if source_code is None:
            return False
        
        if not output_path:
            # 默認輸出路徑
            output_path = str(Path(file_path).with_suffix('.o'))
        
        return self.compile_string(source_code, Path(file_path).name, output_path)
    
    def compile_string(self, source_code: str, file_name: str, output_path: str) -> bool:
        """
        編譯源代碼字符串
        
        Args:
            source_code: 源代碼
            file_name: 文件名 (用於錯誤報告)
            output_path: 輸出文件路徑
            
        Returns:
            是否成功
        """
        # 1. 詞法分析
        self.logger.info("開始詞法分析")
        lexer = Lexer(source_code, file_name)
        tokens = lexer.tokenize()
        
        if lexer.errors:
            self.logger.error(f"詞法分析錯誤:")
            for error in lexer.errors:
                self.logger.error(f"  {error}")
            return False
        
        if self.verbose:
            self.logger.debug(f"詞法分析結果: {len(tokens)} 個詞法單元")
            for token in tokens[:10]:  # 只打印前 10 個詞法單元
                self.logger.debug(f"  {token}")
            if len(tokens) > 10:
                self.logger.debug(f"  ... (還有 {len(tokens) - 10} 個詞法單元)")
        
        # 2. 語法分析
        self.logger.info("開始語法分析")
        parser = Parser(tokens)
        ast = parser.parse()
        
        if parser.errors:
            self.logger.error(f"語法分析錯誤:")
            for error in parser.errors:
                self.logger.error(f"  {error}")
            return False
        
        if self.verbose:
            self.logger.debug(f"語法分析結果: {len(ast.declarations)} 個頂層聲明")
        
        # 3. 語義分析和類型檢查
        self.logger.info("開始語義分析和類型檢查")
        semantic_analyzer = SemanticAnalyzer(ast, self.logger)
        if not semantic_analyzer.analyze():
            self.logger.error(f"語義分析錯誤:")
            for error in semantic_analyzer.errors:
                self.logger.error(f"  {error}")
            return False
        
        # 4. 代碼生成
        self.logger.info("開始代碼生成")
        emitter = BinaryEmitter(ast, output_path, self.logger)
        binary_file = emitter.emit()
        
        if emitter.errors:
            self.logger.error(f"代碼生成錯誤:")
            for error in emitter.errors:
                self.logger.error(f"  {error}")
            return False
        
        self.logger.info(f"已生成二進制檔案: {binary_file}")
        return True
    
    def run_file(self, file_path: str, args: List[str] = []) -> int:
        """
        執行文件
        
        Args:
            file_path: 輸入文件路徑
            args: 程序參數
            
        Returns:
            退出碼
        """
        source_code = self._read_file(file_path)
        if source_code is None:
            return 1
        
        return self.run_string(source_code, Path(file_path).name, args)
    
    def run_string(self, source_code: str, file_name: str, args: List[str] = []) -> int:
        """
        執行源代碼字符串
        
        Args:
            source_code: 源代碼
            file_name: 文件名 (用於錯誤報告)
            args: 程序參數
            
        Returns:
            退出碼
        """
        # 1. 詞法分析
        self.logger.info("開始詞法分析")
        lexer = Lexer(source_code, file_name)
        tokens = lexer.tokenize()
        
        if lexer.errors:
            self.logger.error(f"詞法分析錯誤:")
            for error in lexer.errors:
                self.logger.error(f"  {error}")
            return 1
        
        # 2. 語法分析
        self.logger.info("開始語法分析")
        parser = Parser(tokens)
        ast = parser.parse()
        
        if parser.errors:
            self.logger.error(f"語法分析錯誤:")
            for error in parser.errors:
                self.logger.error(f"  {error}")
            return 1
        
        # 3. 語義分析和類型檢查
        self.logger.info("開始語義分析和類型檢查")
        semantic_analyzer = SemanticAnalyzer(ast, self.logger)
        if not semantic_analyzer.analyze():
            self.logger.error(f"語義分析錯誤:")
            for error in semantic_analyzer.errors:
                self.logger.error(f"  {error}")
            return 1
        
        # 4. 代碼生成
        self.logger.info("開始代碼生成")
        emitter = BinaryEmitter(ast, file_name, self.logger)
        binary_file = emitter.emit()
        
        if emitter.errors:
            self.logger.error(f"代碼生成錯誤:")
            for error in emitter.errors:
                self.logger.error(f"  {error}")
            return 1
        
        # 5. 執行
        self.logger.info("開始執行")
        executor = IRExecutor(binary_file)
        exit_code = executor.execute("main", args)
        
        self.logger.info(f"執行完成，退出碼: {exit_code}")
        return exit_code
    
    def _read_file(self, file_path: str) -> Optional[str]:
        """
        讀取文件內容
        
        Args:
            file_path: 文件路徑
            
        Returns:
            文件內容，如果讀取失敗則返回 None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"無法讀取文件 {file_path}: {e}")
            return None


def main():
    """Glux 編譯器主入口"""
    # 檢查是否直接執行文件 (不帶子命令)
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-') and not sys.argv[1] in ['compile', 'run', 'check']:
        # 將命令行參數調整為標準格式
        sys.argv.insert(1, 'run')  # 默認使用 run 子命令
    
    parser = argparse.ArgumentParser(description='Glux 語言編譯器')
    parser.add_argument('action', choices=['compile', 'run', 'check'], help='執行動作')
    parser.add_argument('file', help='Glux 源碼檔案')
    parser.add_argument('-o', '--output', help='輸出檔案名稱')
    parser.add_argument('-v', '--verbose', action='store_true', help='顯示詳細資訊')
    parser.add_argument('-j', '--jit', action='store_true', help='使用 JIT 直接執行 (不需要生成二進制檔案)')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger("GluxMain")
    
    # 檢查文件
    source_file = args.file
    if not os.path.exists(source_file):
        logger.error(f"找不到檔案: {source_file}")
        sys.exit(1)
    
    # 設置輸出文件
    output_file = args.output or os.path.splitext(source_file)[0]
    
    try:
        # 讀取源碼
        with open(source_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # 詞法分析
        logger.info("開始詞法分析...")
        lexer = Lexer(source_code, source_file)
        tokens = lexer.tokenize()
        
        if lexer.errors:
            logger.error("詞法分析錯誤:")
            for error in lexer.errors:
                logger.error(f"  {error}")
            sys.exit(1)
        
        # 語法分析
        logger.info("開始語法分析...")
        parser = Parser(tokens)
        ast = parser.parse()
        
        if parser.errors:
            logger.error("語法分析錯誤:")
            for error in parser.errors:
                logger.error(f"  {error}")
            sys.exit(1)
        
        # 語義分析
        logger.info("開始語義分析...")
        semantic_analyzer = SemanticAnalyzer()
        if not semantic_analyzer.analyze(ast):
            logger.error("語義分析錯誤:")
            for error in semantic_analyzer.get_errors():
                logger.error(f"  {error}")
            sys.exit(1)
        
        # 只進行檢查
        if args.action == 'check':
            logger.info("程式碼檢查通過")
            sys.exit(0)
        
        # 代碼生成
        logger.info("開始代碼生成...")
        code_generator = LLVMCodeGenerator()
        llvm_ir = code_generator.generate(ast)
        
        # 輸出 LLVM IR
        ll_file = f"{output_file}.ll"
        with open(ll_file, 'w', encoding='utf-8') as f:
            f.write(llvm_ir)
        
        logger.info(f"生成 LLVM IR 檔案: {ll_file}")
        
        # 運行程式
        if args.action == 'run':
            # JIT 模式
            if args.jit:
                logger.info("使用 JIT 直接執行 LLVM IR...")
                from .utils.ir_executor import execute_llvm_ir
                exit_code = execute_llvm_ir(llvm_ir)
                sys.exit(exit_code)
            # 傳統模式
            else:
                logger.info("生成並執行二進制檔案...")
                binary_emitter = BinaryEmitter(ast, output_file)
                binary_file = binary_emitter.emit()
                
                if binary_emitter.errors:
                    logger.error("代碼生成錯誤:")
                    for error in binary_emitter.errors:
                        logger.error(f"  {error}")
                    sys.exit(1)
                
                logger.info(f"生成二進制文件: {binary_file}")
                logger.info("執行程式...")
                os.chmod(binary_file, 0o755)  # 設為可執行
                exit_code = os.system(binary_file)
                sys.exit(exit_code >> 8)  # 提取實際退出碼
        
    except Exception as e:
        logger.error(f"發生錯誤: {str(e)}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main() 