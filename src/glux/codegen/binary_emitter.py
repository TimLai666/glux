"""
二進制代碼生成器模組
負責將AST轉換為可執行的二進制文件
"""

import os
import subprocess
import tempfile
import logging
from typing import List, Optional, Any

from ..parser import ast_nodes
from .code_generator import CodeGenerator


class BinaryEmitter:
    """
    二進制代碼生成器類
    將AST轉換為可執行的二進制文件
    """
    
    def __init__(self, ast: ast_nodes.Module, output_path: str, logger: Optional[logging.Logger] = None):
        """
        初始化二進制代碼生成器
        
        Args:
            ast: AST根節點
            output_path: 輸出文件路徑
            logger: 日誌器（可選）
        """
        self.ast = ast
        self.output_path = output_path
        self.logger = logger or logging.getLogger("BinaryEmitter")
        self.errors = []
        self.code_generator = CodeGenerator(self.logger)
    
    def emit(self) -> str:
        """
        生成二進制文件
        
        Returns:
            生成的二進制文件路徑，失敗時返回空字符串
        """
        self.logger.info(f"開始生成二進制文件: {self.output_path}")
        
        try:
            # 生成LLVM IR代碼
            llvm_ir = self.code_generator.generate(self.ast)
            
            # 將LLVM IR寫入臨時文件
            with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as temp_file:
                temp_ir_path = temp_file.name
                temp_file.write(llvm_ir.encode('utf-8'))
            
            # 檢查llc命令是否存在
            try:
                # 嘗試執行llc命令，確認其是否存在
                subprocess.run(["llc", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                llc_exists = True
            except FileNotFoundError:
                llc_exists = False
                error_msg = "未找到LLVM工具集(llc)。請安裝LLVM以支持生成二進制文件，或使用JIT選項直接運行LLVM IR。"
                self.logger.error(error_msg)
                self.errors.append(error_msg)
                
                # 保存LLVM IR文件，以便後續手動處理
                ll_file = f"{self.output_path}.ll"
                with open(ll_file, 'w', encoding='utf-8') as f:
                    f.write(llvm_ir)
                self.logger.info(f"已保存LLVM IR到文件: {ll_file}")
                
                # 清理臨時文件
                os.unlink(temp_ir_path)
                return ""
            
            if llc_exists:
                # 使用llc編譯LLVM IR為目標文件
                object_path = f"{self.output_path}.o"
                success = self._run_command(["llc", "-filetype=obj", temp_ir_path, "-o", object_path])
                
                if not success:
                    # 清理臨時文件
                    os.unlink(temp_ir_path)
                    return ""
                
                # 使用編譯器鏈接為可執行文件
                success = self._run_command(["gcc", object_path, "-o", self.output_path])
                
                if not success:
                    # 清理臨時文件
                    os.unlink(temp_ir_path)
                    if os.path.exists(object_path):
                        os.unlink(object_path)
                    return ""
                
                # 清理臨時文件
                os.unlink(temp_ir_path)
                os.unlink(object_path)
                
                self.logger.info(f"二進制文件生成完成: {self.output_path}")
                return self.output_path
                
        except Exception as e:
            error_msg = f"生成二進制文件時發生錯誤: {str(e)}"
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return ""
    
    def _run_command(self, command: List[str]) -> bool:
        """
        運行命令
        
        Args:
            command: 命令及參數
            
        Returns:
            命令是否成功執行
        """
        self.logger.debug(f"執行命令: {' '.join(command)}")
        
        try:
            process = subprocess.run(command, capture_output=True, text=True)
            
            if process.returncode != 0:
                error_msg = f"命令執行失敗: {' '.join(command)}\n{process.stderr}"
                self.logger.error(error_msg)
                self.errors.append(error_msg)
                return False
            
            return True
            
        except Exception as e:
            error_msg = f"命令執行發生異常: {' '.join(command)}\n{str(e)}"
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return False 