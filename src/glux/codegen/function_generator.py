"""
LLVM 函數生成器
負責處理 Glux 函數相關節點的代碼生成
"""

from llvmlite import ir
from typing import Dict, Any, List, Optional, Union, Tuple

from glux.parser.ast_nodes import (
    FunctionDef, Parameter, SpawnExpr, AwaitExpr
)
from .base_generator import BaseGenerator
from .type_generator import TypeGenerator


class FunctionGenerator:
    """
    處理函數相關節點的代碼生成
    """
    
    def __init__(self, base_generator: BaseGenerator):
        """
        初始化函數生成器
        
        Args:
            base_generator: 基礎生成器實例
        """
        self.base = base_generator
        self.module = base_generator.module
    
    def declare_function(self, name: str, return_type: str, param_types: List[str], 
                        param_names: Optional[List[str]] = None) -> ir.Function:
        """
        宣告函數
        
        Args:
            name: 函數名稱
            return_type: 返回類型
            param_types: 參數類型列表
            param_names: 參數名稱列表 (可選)
            
        Returns:
            LLVM 函數
        """
        # 轉換返回類型
        ret_type = self._get_llvm_type(return_type)
        
        # 轉換參數類型
        params = [self._get_llvm_type(p_type) for p_type in param_types]
        
        # 創建函數類型
        func_type = ir.FunctionType(ret_type, params)
        
        # 檢查函數是否已存在
        if name in self.base.functions:
            return self.base.functions[name]
        
        # 創建函數
        func = ir.Function(self.module, func_type, name=name)
        
        # 為參數命名 (如果提供了名稱)
        if param_names:
            for i, param_name in enumerate(param_names):
                if i < len(func.args):
                    func.args[i].name = param_name
        
        # 記錄函數
        self.base.functions[name] = func
        
        return func
    
    def define_function(self, node: FunctionDef, statement_generator=None) -> ir.Function:
        """
        定義函數
        
        Args:
            node: 函數定義節點
            statement_generator: 語句生成器 (用於生成函數體)
            
        Returns:
            LLVM 函數
        """
        # 獲取返回類型
        return_type = "void"
        if node.return_type:
            return_type = node.return_type.name
        
        # 獲取參數類型和名稱
        param_types = []
        param_names = []
        
        for param in node.params:
            param_type = "any"  # 默認類型
            if param.type_hint:
                param_type = param.type_hint.name
            param_types.append(param_type)
            param_names.append(param.name)
        
        # 宣告函數
        func = self.declare_function(node.name, return_type, param_types, param_names)
        
        # 創建函數入口塊
        entry_block = func.append_basic_block(name="entry")
        
        # 保存當前建構器上下文
        old_builder = self.base.builder
        old_function = self.base.current_function
        
        # 設置新建構器
        self.base.builder = ir.IRBuilder(entry_block)
        self.base.current_function = func
        
        # 為參數分配空間並存儲
        self.base.push_scope()  # 進入函數作用域
        
        for i, param in enumerate(func.args):
            # 分配參數空間
            param_ptr = self.base.builder.alloca(param.type, name=f"{param.name}_ptr")
            self.base.builder.store(param, param_ptr)
            
            # 記錄參數
            self.base.symbols[param.name] = param_ptr
            
            # 處理默認參數 (如果有)
            if i < len(node.params) and node.params[i].default_value:
                # TODO: 實現默認參數處理
                pass
        
        # 生成函數體
        if statement_generator:
            for stmt in node.body:
                statement_generator.generate_stmt(stmt)
        
        # 確保函數有返回值
        if not self.base.builder.block.is_terminated:
            if isinstance(func.return_type, ir.VoidType):
                self.base.builder.ret_void()
            else:
                # 使用默認值返回
                if isinstance(func.return_type, ir.IntType):
                    self.base.builder.ret(ir.Constant(func.return_type, 0))
                elif isinstance(func.return_type, (ir.FloatType, ir.DoubleType)):
                    self.base.builder.ret(ir.Constant(func.return_type, 0.0))
                else:
                    # 其他類型默認返回 null
                    self.base.builder.ret(ir.Constant(func.return_type, None))
        
        # 恢復建構器上下文
        self.base.pop_scope()  # 離開函數作用域
        self.base.builder = old_builder
        self.base.current_function = old_function
        
        return func
    
    def gen_spawn_expr(self, node: SpawnExpr, expr_generator=None) -> ir.Value:
        """
        生成併發執行表達式
        
        Args:
            node: 併發執行表達式節點
            expr_generator: 表達式生成器 (用於生成參數)
            
        Returns:
            LLVM 值 (表示併發任務的句柄)
        """
        # TODO: 實現真正的併發
        # 暫時只是同步執行函數
        
        if isinstance(node.function_call, FunctionDef):
            # 如果是內聯函數定義
            func = self.define_function(node.function_call)
            # 呼叫函數 (無參數)
            return self.base.builder.call(func, [], name=f"spawn_{func.name}")
        else:
            # 否則是函數調用
            if expr_generator is None:
                raise ValueError("需要提供表達式生成器來生成函數調用")
                
            return expr_generator.generate_expr(node.function_call)
    
    def gen_await_expr(self, node: AwaitExpr, expr_generator=None) -> ir.Value:
        """
        生成等待表達式
        
        Args:
            node: 等待表達式節點
            expr_generator: 表達式生成器 (用於生成表達式)
            
        Returns:
            LLVM 值 (表示等待結果)
        """
        # TODO: 實現真正的等待
        # 暫時只是執行表達式並返回結果
        
        if len(node.expressions) == 1:
            # 單個表達式
            if expr_generator is None:
                raise ValueError("需要提供表達式生成器來生成表達式")
                
            return expr_generator.generate_expr(node.expressions[0])
        else:
            # 多個表達式
            # TODO: 實現多個表達式的等待，返回元組
            # 暫時返回最後一個表達式的結果
            if expr_generator is None:
                raise ValueError("需要提供表達式生成器來生成表達式")
                
            results = []
            for expr in node.expressions:
                results.append(expr_generator.generate_expr(expr))
                
            return results[-1]  # 暫時只返回最後一個結果
    
    def _get_llvm_type(self, type_name: str) -> ir.Type:
        """
        將 Glux 類型名稱轉換為 LLVM 類型
        
        Args:
            type_name: Glux 類型名稱
            
        Returns:
            LLVM 類型
        """
        return TypeGenerator.get_llvm_type(type_name) 