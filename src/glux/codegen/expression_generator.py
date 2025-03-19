"""
LLVM 表達式生成器
負責處理 Glux 表達式節點的代碼生成
"""

from llvmlite import ir
import operator
from typing import Dict, Any, Tuple, List, Optional, Union

from glux.parser.ast_nodes import (
    Number, Float, String, Boolean, Variable, BinaryOp, UnaryOp,
    FunctionCall, ListLiteral, MapLiteral, Tuple as TupleNode,
    ErrorLiteral, PtrExpr, DerefExpr, MemberAccess, IndexAccess
)
from .base_generator import BaseGenerator
from .type_generator import TypeGenerator


class ExpressionGenerator:
    """
    處理表達式節點的代碼生成
    """
    
    def __init__(self, base_generator: BaseGenerator):
        """
        初始化表達式生成器
        
        Args:
            base_generator: 基礎生成器實例
        """
        self.base = base_generator
        self.builder = base_generator.builder
        
        # 二元運算符映射
        self.binary_ops = {
            "+": operator.add,
            "-": operator.sub,
            "*": operator.mul,
            "/": operator.truediv,
            "%": operator.mod,
            "&": operator.and_,
            "|": operator.or_,
            "^": operator.xor,
            "<<": operator.lshift,
            ">>": operator.rshift,
        }
        
        # 比較運算符映射
        self.comp_ops = {
            "==": "==",
            "!=": "!=",
            "<": "<",
            "<=": "<=",
            ">": ">",
            ">=": ">=",
        }
    
    def generate_expr(self, node) -> ir.Value:
        """
        生成表達式的 LLVM IR
        
        Args:
            node: 表達式節點
            
        Returns:
            LLVM 值
        """
        if isinstance(node, Number):
            return self._gen_number(node)
        elif isinstance(node, Float):
            return self._gen_float(node)
        elif isinstance(node, String):
            return self._gen_string(node)
        elif isinstance(node, Boolean):
            return self._gen_boolean(node)
        elif isinstance(node, Variable):
            return self._gen_variable(node)
        elif isinstance(node, BinaryOp):
            return self._gen_binary_op(node)
        elif isinstance(node, UnaryOp):
            return self._gen_unary_op(node)
        elif isinstance(node, FunctionCall):
            return self._gen_function_call(node)
        elif isinstance(node, ListLiteral):
            return self._gen_list_literal(node)
        elif isinstance(node, MapLiteral):
            return self._gen_map_literal(node)
        elif isinstance(node, TupleNode):
            return self._gen_tuple(node)
        elif isinstance(node, ErrorLiteral):
            return self._gen_error_literal(node)
        elif isinstance(node, PtrExpr):
            return self._gen_ptr_expr(node)
        elif isinstance(node, DerefExpr):
            return self._gen_deref_expr(node)
        elif isinstance(node, MemberAccess):
            return self._gen_member_access(node)
        elif isinstance(node, IndexAccess):
            return self._gen_index_access(node)
        else:
            raise NotImplementedError(f"未實現表達式類型: {type(node)}")
    
    def _gen_number(self, node: Number) -> ir.Constant:
        """生成整數字面量"""
        value = int(node.value)
        
        # 根據數值大小選擇適當的整數類型
        if -128 <= value <= 127:
            return ir.Constant(ir.IntType(8), value)
        elif -32768 <= value <= 32767:
            return ir.Constant(ir.IntType(16), value)
        elif -2147483648 <= value <= 2147483647:
            return ir.Constant(ir.IntType(32), value)
        else:
            return ir.Constant(ir.IntType(64), value)
    
    def _gen_float(self, node: Float) -> ir.Constant:
        """生成浮點數字面量"""
        value = float(node.value)
        
        # 暫時統一使用 float64 (double)
        return ir.Constant(ir.DoubleType(), value)
    
    def _gen_string(self, node: String) -> ir.Value:
        """生成字串字面量"""
        _, ptr = self.base.get_new_string_constant(node.value)
        return ptr
    
    def _gen_boolean(self, node: Boolean) -> ir.Constant:
        """生成布爾字面量"""
        return ir.Constant(ir.IntType(1), int(node.value))
    
    def _gen_variable(self, node: Variable) -> ir.Value:
        """生成變數引用"""
        return self.base.get_variable_value(node.name)
    
    def _gen_binary_op(self, node: BinaryOp) -> ir.Value:
        """生成二元運算表達式"""
        left = self.generate_expr(node.left)
        right = self.generate_expr(node.right)
        
        # 處理不同的二元運算符
        if node.op in self.binary_ops:
            # 算術運算
            return self._handle_arithmetic_op(node.op, left, right)
        elif node.op in self.comp_ops:
            # 比較運算
            return self._handle_comparison_op(node.op, left, right)
        elif node.op in ["&&", "and"]:
            # 邏輯與
            return self._handle_logical_and(left, right)
        elif node.op in ["||", "or"]:
            # 邏輯或
            return self._handle_logical_or(left, right)
        else:
            raise NotImplementedError(f"未實現的二元運算符: {node.op}")
    
    def _handle_arithmetic_op(self, op: str, left: ir.Value, right: ir.Value) -> ir.Value:
        """處理算術運算符"""
        # 確保操作數類型一致
        if hasattr(left.type, 'width') and hasattr(right.type, 'width'):
            if left.type.width != right.type.width:
                # 將較小的類型轉換為較大的類型
                if left.type.width < right.type.width:
                    left = self.builder.zext(left, right.type)
                else:
                    right = self.builder.zext(right, left.type)
        
        # 字串連接特殊處理
        if op == "+" and isinstance(left.type, ir.PointerType) and isinstance(right.type, ir.PointerType):
            return self._handle_string_concat(left, right)
        
        # 處理不同的算術運算符
        if op == "+":
            return self.builder.add(left, right, name="addtmp")
        elif op == "-":
            return self.builder.sub(left, right, name="subtmp")
        elif op == "*":
            return self.builder.mul(left, right, name="multmp")
        elif op == "/":
            return self.builder.sdiv(left, right, name="divtmp")
        elif op == "%":
            return self.builder.srem(left, right, name="modtmp")
        elif op == "&":
            return self.builder.and_(left, right, name="bitandtmp")
        elif op == "|":
            return self.builder.or_(left, right, name="bitortmp")
        elif op == "^":
            return self.builder.xor(left, right, name="bitxortmp")
        elif op == "<<":
            return self.builder.shl(left, right, name="shltmp")
        elif op == ">>":
            return self.builder.ashr(left, right, name="shrtmp")
    
    def _handle_comparison_op(self, op: str, left: ir.Value, right: ir.Value) -> ir.Value:
        """處理比較運算符"""
        # 確保操作數類型一致
        if hasattr(left.type, 'width') and hasattr(right.type, 'width'):
            if left.type.width != right.type.width:
                # 將較小的類型轉換為較大的類型
                if left.type.width < right.type.width:
                    left = self.builder.zext(left, right.type)
                else:
                    right = self.builder.zext(right, left.type)
        
        # 處理浮點數比較
        if isinstance(left.type, (ir.FloatType, ir.DoubleType)) or isinstance(right.type, (ir.FloatType, ir.DoubleType)):
            return self.builder.fcmp_ordered(self.comp_ops[op], left, right, name="fcmptmp")
        
        # 處理整數比較
        return self.builder.icmp_signed(self.comp_ops[op], left, right, name="icmptmp")
    
    def _handle_logical_and(self, left: ir.Value, right: ir.Value) -> ir.Value:
        """處理邏輯與運算"""
        # 將操作數轉換為布爾值 (0 或 1)
        left_bool = self._to_bool(left)
        
        # 為了實現短路運算，需要使用條件分支
        # 創建基本塊
        current_block = self.builder.block
        right_block = self.base.current_function.append_basic_block(name="and_right")
        merge_block = self.base.current_function.append_basic_block(name="and_merge")
        
        # 判斷左操作數，如果為假則短路，否則計算右操作數
        self.builder.cbranch(left_bool, right_block, merge_block)
        
        # 進入右操作數塊
        self.builder.position_at_end(right_block)
        right_bool = self._to_bool(right)
        right_block = self.builder.block  # 可能已經變化
        self.builder.branch(merge_block)
        
        # 進入合併塊
        self.builder.position_at_end(merge_block)
        phi = self.builder.phi(ir.IntType(1), name="andtmp")
        phi.add_incoming(ir.Constant(ir.IntType(1), 0), current_block)
        phi.add_incoming(right_bool, right_block)
        
        return phi
    
    def _handle_logical_or(self, left: ir.Value, right: ir.Value) -> ir.Value:
        """處理邏輯或運算"""
        # 將操作數轉換為布爾值 (0 或 1)
        left_bool = self._to_bool(left)
        
        # 為了實現短路運算，需要使用條件分支
        # 創建基本塊
        current_block = self.builder.block
        right_block = self.base.current_function.append_basic_block(name="or_right")
        merge_block = self.base.current_function.append_basic_block(name="or_merge")
        
        # 判斷左操作數，如果為真則短路，否則計算右操作數
        self.builder.cbranch(left_bool, merge_block, right_block)
        
        # 進入右操作數塊
        self.builder.position_at_end(right_block)
        right_bool = self._to_bool(right)
        right_block = self.builder.block  # 可能已經變化
        self.builder.branch(merge_block)
        
        # 進入合併塊
        self.builder.position_at_end(merge_block)
        phi = self.builder.phi(ir.IntType(1), name="ortmp")
        phi.add_incoming(ir.Constant(ir.IntType(1), 1), current_block)
        phi.add_incoming(right_bool, right_block)
        
        return phi
    
    def _handle_string_concat(self, left: ir.Value, right: ir.Value) -> ir.Value:
        """處理字串連接"""
        # 獲取 C 標準庫函數
        strlen_name = "strlen"
        strcpy_name = "strcpy"
        strcat_name = "strcat"
        malloc_name = "malloc"
        
        # 確保函數已聲明
        if strlen_name not in self.base.functions:
            strlen_type = ir.FunctionType(ir.IntType(64), [ir.PointerType(ir.IntType(8))])
            self.base.functions[strlen_name] = ir.Function(self.base.module, strlen_type, name=strlen_name)
            
        if strcpy_name not in self.base.functions:
            strcpy_type = ir.FunctionType(ir.PointerType(ir.IntType(8)), 
                                        [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))])
            self.base.functions[strcpy_name] = ir.Function(self.base.module, strcpy_type, name=strcpy_name)
            
        if strcat_name not in self.base.functions:
            strcat_type = ir.FunctionType(ir.PointerType(ir.IntType(8)), 
                                        [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))])
            self.base.functions[strcat_name] = ir.Function(self.base.module, strcat_type, name=strcat_name)
            
        if malloc_name not in self.base.functions:
            malloc_type = ir.FunctionType(ir.PointerType(ir.IntType(8)), [ir.IntType(64)])
            self.base.functions[malloc_name] = ir.Function(self.base.module, malloc_type, name=malloc_name)
        
        # 計算兩個字串的長度
        left_len = self.builder.call(self.base.functions[strlen_name], [left])
        right_len = self.builder.call(self.base.functions[strlen_name], [right])
        
        # 計算新字串所需的總長度 (left_len + right_len + 1)，+1 是為了 null 終止符
        total_len = self.builder.add(left_len, right_len)
        total_len = self.builder.add(total_len, ir.Constant(ir.IntType(64), 1))
        
        # 分配新字串的內存
        new_str_ptr = self.builder.call(self.base.functions[malloc_name], [total_len])
        
        # 複製第一個字串到新內存
        self.builder.call(self.base.functions[strcpy_name], [new_str_ptr, left])
        
        # 連接第二個字串
        self.builder.call(self.base.functions[strcat_name], [new_str_ptr, right])
        
        return new_str_ptr
    
    def _to_bool(self, value: ir.Value) -> ir.Value:
        """將值轉換為布爾值"""
        if isinstance(value.type, ir.IntType):
            if value.type.width == 1:
                return value
            return self.builder.icmp_signed("!=", value, ir.Constant(value.type, 0), name="to_bool")
        elif isinstance(value.type, (ir.FloatType, ir.DoubleType)):
            return self.builder.fcmp_ordered("!=", value, ir.Constant(value.type, 0), name="to_bool")
        elif isinstance(value.type, ir.PointerType):
            null_ptr = ir.Constant(value.type, None)
            return self.builder.icmp_signed("!=", value, null_ptr, name="to_bool")
        else:
            raise TypeError(f"無法將類型 {value.type} 轉換為布爾值")
    
    def _gen_unary_op(self, node: UnaryOp) -> ir.Value:
        """生成一元運算表達式"""
        operand = self.generate_expr(node.operand)
        
        if node.op in ["!", "not"]:
            # 邏輯非
            bool_val = self._to_bool(operand)
            return self.builder.xor(bool_val, ir.Constant(ir.IntType(1), 1), name="not_result")
        elif node.op == "-":
            # 數字取負
            return self.builder.neg(operand, name="neg_result")
        elif node.op == "+":
            # 一元加號，直接返回操作數
            return operand
        elif node.op == "&":
            # 取地址運算符
            if isinstance(node.operand, Variable):
                if node.operand.name not in self.base.symbols:
                    raise NameError(f"變數 '{node.operand.name}' 未定義")
                return self.base.symbols[node.operand.name]  # 直接返回變數的指針
            else:
                raise TypeError("只能對變數取地址")
        elif node.op == "*":
            # 解引用運算符
            return self.builder.load(operand, name="deref_result")
        elif node.op == "~":
            # 位元取反
            return self.builder.not_(operand, name="bitnot_result")
        else:
            raise NotImplementedError(f"未實現的一元運算符: {node.op}")
    
    def _gen_function_call(self, node: FunctionCall) -> ir.Value:
        """生成函數調用"""
        # 這裡只是一個基本實現，完整的函數調用處理應在獨立模組中
        if node.name in self.base.functions:
            # 處理參數
            args = [self.generate_expr(arg) for arg in node.args]
            
            # 處理關鍵字參數 (如果有)
            # ...
            
            # 呼叫函數
            return self.builder.call(self.base.functions[node.name], args, name=f"call_{node.name}")
        else:
            raise NameError(f"函數 '{node.name}' 未定義")
    
    def _gen_list_literal(self, node: ListLiteral) -> ir.Value:
        """生成列表字面量"""
        # 暫時返回 NULL 指針，實際實現需要分配內存並填充數據
        return ir.Constant(ir.PointerType(ir.IntType(8)), None)
    
    def _gen_map_literal(self, node: MapLiteral) -> ir.Value:
        """生成映射字面量"""
        # 暫時返回 NULL 指針，實際實現需要分配內存並填充數據
        return ir.Constant(ir.PointerType(ir.IntType(8)), None)
    
    def _gen_tuple(self, node: TupleNode) -> ir.Value:
        """生成元組字面量"""
        # 暫時返回 NULL 指針，實際實現需要分配內存並填充數據
        return ir.Constant(ir.PointerType(ir.IntType(8)), None)
    
    def _gen_error_literal(self, node: ErrorLiteral) -> ir.Value:
        """生成錯誤字面量"""
        # 暫時返回 NULL 指針，實際實現需要分配內存並填充錯誤數據
        return ir.Constant(ir.PointerType(ir.IntType(8)), None)
    
    def _gen_ptr_expr(self, node: PtrExpr) -> ir.Value:
        """生成指針表達式"""
        # 與一元運算符 & 相同
        if isinstance(node.expr, Variable):
            if node.expr.name not in self.base.symbols:
                raise NameError(f"變數 '{node.expr.name}' 未定義")
            return self.base.symbols[node.expr.name]  # 直接返回變數的指針
        else:
            raise TypeError("只能對變數取地址")
    
    def _gen_deref_expr(self, node: DerefExpr) -> ir.Value:
        """生成解引用表達式"""
        # 與一元運算符 * 相同
        operand = self.generate_expr(node.expr)
        return self.builder.load(operand, name="deref_result")
    
    def _gen_member_access(self, node: MemberAccess) -> ir.Value:
        """生成成員存取表達式"""
        # 暫時返回 0，實際實現需要根據對象類型獲取成員
        return ir.Constant(ir.IntType(32), 0)
    
    def _gen_index_access(self, node: IndexAccess) -> ir.Value:
        """生成索引存取表達式"""
        # 暫時返回 0，實際實現需要根據對象類型獲取索引元素
        return ir.Constant(ir.IntType(32), 0) 