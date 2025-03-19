"""
LLVM 語句生成器
負責處理 Glux 語句節點的代碼生成
"""

from llvmlite import ir
from typing import Dict, Any, List, Optional, Union

from glux.parser.ast_nodes import (
    ExprStmt, BlockStmt, VarDeclStmt, IfStmt, WhileStmt, ForStmt,
    ReturnStmt, BreakStmt, ContinueStmt, ThrowStmt, TryCatchStmt,
    AssignStmt, FunctionDef
)
from .base_generator import BaseGenerator
from .expression_generator import ExpressionGenerator


class StatementGenerator:
    """
    處理 Glux 語句節點的代碼生成
    """
    
    def __init__(self, base_generator: BaseGenerator):
        """
        初始化語句生成器
        
        Args:
            base_generator: 基礎生成器實例
        """
        self.base = base_generator
        self.module = base_generator.module
        self.expr_gen = ExpressionGenerator(base_generator)
        
        # 跟踪迴圈相關信息
        self.loop_exit_blocks = []  # break 語句的目標
        self.loop_continue_blocks = []  # continue 語句的目標
    
    def generate_stmt(self, node):
        """
        生成語句代碼
        
        Args:
            node: 語句節點
            
        Returns:
            生成的 LLVM IR 值 (如果有)
        """
        if isinstance(node, ExprStmt):
            return self.gen_expr_stmt(node)
        elif isinstance(node, BlockStmt):
            return self.gen_block_stmt(node)
        elif isinstance(node, VarDeclStmt):
            return self.gen_var_decl_stmt(node)
        elif isinstance(node, IfStmt):
            return self.gen_if_stmt(node)
        elif isinstance(node, WhileStmt):
            return self.gen_while_stmt(node)
        elif isinstance(node, ForStmt):
            return self.gen_for_stmt(node)
        elif isinstance(node, ReturnStmt):
            return self.gen_return_stmt(node)
        elif isinstance(node, BreakStmt):
            return self.gen_break_stmt(node)
        elif isinstance(node, ContinueStmt):
            return self.gen_continue_stmt(node)
        elif isinstance(node, ThrowStmt):
            return self.gen_throw_stmt(node)
        elif isinstance(node, TryCatchStmt):
            return self.gen_try_catch_stmt(node)
        elif isinstance(node, AssignStmt):
            return self.gen_assign_stmt(node)
        elif isinstance(node, FunctionDef):
            # 在語句中的函數定義（內部函數）
            from .function_generator import FunctionGenerator
            func_gen = FunctionGenerator(self.base)
            return func_gen.define_function(node, self)
        else:
            raise TypeError(f"不支持的語句類型: {type(node).__name__}")
    
    def gen_expr_stmt(self, node: ExprStmt):
        """
        生成表達式語句代碼
        
        Args:
            node: 表達式語句節點
            
        Returns:
            表達式的值
        """
        return self.expr_gen.generate_expr(node.expr)
    
    def gen_block_stmt(self, node: BlockStmt):
        """
        生成代碼塊語句代碼
        
        Args:
            node: 代碼塊語句節點
            
        Returns:
            最後一個語句的值 (如果有)
        """
        # 進入新的作用域
        self.base.push_scope()
        
        # 生成塊中的所有語句
        result = None
        for stmt in node.statements:
            result = self.generate_stmt(stmt)
            
            # 如果當前塊已經終止（例如因為 return），則停止
            if self.base.builder.block.is_terminated:
                break
        
        # 離開作用域
        self.base.pop_scope()
        
        return result
    
    def gen_var_decl_stmt(self, node: VarDeclStmt):
        """
        生成變數宣告語句代碼
        
        Args:
            node: 變數宣告語句節點
            
        Returns:
            變數的地址
        """
        # 確定變數類型
        if node.type_hint:
            var_type_name = node.type_hint.name
            var_type = self.base.type_generator.get_llvm_type(var_type_name)
        else:
            # 如果沒有類型提示，從初始值推斷類型
            if node.init_value:
                init_value = self.expr_gen.generate_expr(node.init_value)
                var_type = init_value.type
            else:
                # 默認為通用指針類型 (void*)
                var_type = ir.IntType(8).as_pointer()
        
        # 生成初始值
        init_value = None
        if node.init_value:
            init_value = self.expr_gen.generate_expr(node.init_value)
            
            # 確保類型匹配
            if init_value.type != var_type:
                # 嘗試類型轉換
                init_value = self._convert_type(init_value, init_value.type, var_type)
        
        # 宣告變數
        return self.base.declare_variable(node.name, var_type, init_value)
    
    def gen_if_stmt(self, node: IfStmt):
        """
        生成 if 語句代碼
        
        Args:
            node: if 語句節點
            
        Returns:
            None
        """
        # 生成條件
        condition = self.expr_gen.generate_expr(node.condition)
        
        # 如果條件是一個指針，將其轉換為布爾值
        if isinstance(condition.type, ir.PointerType):
            zero = ir.Constant(condition.type, None)
            condition = self.base.builder.icmp_unsigned('!=', condition, zero)
        
        # 確保條件是布爾類型或 i1
        if not isinstance(condition.type, ir.IntType) or condition.type.width != 1:
            # 轉換為布爾類型
            condition = self._to_bool(condition)
        
        # 創建基本塊
        with self.base.builder.if_else(condition) as (then, otherwise):
            with then:
                # 生成 then 塊
                self.generate_stmt(node.then_block)
            
            with otherwise:
                # 生成 else 塊 (如果有)
                if node.else_block:
                    self.generate_stmt(node.else_block)
        
        return None
    
    def gen_while_stmt(self, node: WhileStmt):
        """
        生成 while 語句代碼
        
        Args:
            node: while 語句節點
            
        Returns:
            None
        """
        # 創建基本塊
        cond_block = self.base.builder.append_basic_block("while.cond")
        body_block = self.base.builder.append_basic_block("while.body")
        end_block = self.base.builder.append_basic_block("while.end")
        
        # 跳到條件塊
        self.base.builder.branch(cond_block)
        
        # 條件塊
        self.base.builder.position_at_start(cond_block)
        condition = self.expr_gen.generate_expr(node.condition)
        
        # 確保條件是布爾類型
        condition = self._to_bool(condition)
        
        # 根據條件跳轉
        self.base.builder.cbranch(condition, body_block, end_block)
        
        # 循環體塊
        self.base.builder.position_at_start(body_block)
        
        # 保存循環出口和繼續目標
        self.loop_exit_blocks.append(end_block)
        self.loop_continue_blocks.append(cond_block)
        
        # 生成循環體
        self.generate_stmt(node.body)
        
        # 移除循環目標
        self.loop_exit_blocks.pop()
        self.loop_continue_blocks.pop()
        
        # 如果循環體沒有終止（例如 return 或 break），則跳回條件塊
        if not self.base.builder.block.is_terminated:
            self.base.builder.branch(cond_block)
        
        # 結束塊
        self.base.builder.position_at_start(end_block)
        
        return None
    
    def gen_for_stmt(self, node: ForStmt):
        """
        生成 for 語句代碼
        
        Args:
            node: for 語句節點
            
        Returns:
            None
        """
        # 進入循環作用域
        self.base.push_scope()
        
        # 創建基本塊
        init_block = self.base.builder.append_basic_block("for.init")
        cond_block = self.base.builder.append_basic_block("for.cond")
        body_block = self.base.builder.append_basic_block("for.body")
        update_block = self.base.builder.append_basic_block("for.update")
        end_block = self.base.builder.append_basic_block("for.end")
        
        # 跳到初始塊
        self.base.builder.branch(init_block)
        
        # 初始化塊
        self.base.builder.position_at_start(init_block)
        if node.init:
            self.generate_stmt(node.init)
        self.base.builder.branch(cond_block)
        
        # 條件塊
        self.base.builder.position_at_start(cond_block)
        if node.condition:
            condition = self.expr_gen.generate_expr(node.condition)
            condition = self._to_bool(condition)
            self.base.builder.cbranch(condition, body_block, end_block)
        else:
            # 如果沒有條件，則一直循環
            self.base.builder.branch(body_block)
        
        # 循環體塊
        self.base.builder.position_at_start(body_block)
        
        # 保存循環出口和繼續目標
        self.loop_exit_blocks.append(end_block)
        self.loop_continue_blocks.append(update_block)
        
        # 生成循環體
        self.generate_stmt(node.body)
        
        # 移除循環目標
        self.loop_exit_blocks.pop()
        self.loop_continue_blocks.pop()
        
        # 如果循環體沒有終止，則跳到更新塊
        if not self.base.builder.block.is_terminated:
            self.base.builder.branch(update_block)
        
        # 更新塊
        self.base.builder.position_at_start(update_block)
        if node.update:
            self.expr_gen.generate_expr(node.update)
        self.base.builder.branch(cond_block)
        
        # 結束塊
        self.base.builder.position_at_start(end_block)
        
        # 離開循環作用域
        self.base.pop_scope()
        
        return None
    
    def gen_return_stmt(self, node: ReturnStmt):
        """
        生成 return 語句代碼
        
        Args:
            node: return 語句節點
            
        Returns:
            None
        """
        if not self.base.current_function:
            raise RuntimeError("Return 語句必須在函數內部使用")
        
        # 獲取返回值類型
        ret_type = self.base.current_function.return_type
        
        if node.value:
            # 有返回值
            value = self.expr_gen.generate_expr(node.value)
            
            # 確保類型匹配
            if value.type != ret_type:
                value = self._convert_type(value, value.type, ret_type)
            
            self.base.builder.ret(value)
        else:
            # 無返回值
            if isinstance(ret_type, ir.VoidType):
                self.base.builder.ret_void()
            else:
                # 有返回類型但沒有返回值，使用默認值
                if isinstance(ret_type, ir.IntType):
                    self.base.builder.ret(ir.Constant(ret_type, 0))
                elif isinstance(ret_type, (ir.FloatType, ir.DoubleType)):
                    self.base.builder.ret(ir.Constant(ret_type, 0.0))
                else:
                    # 其他類型默認返回 null
                    self.base.builder.ret(ir.Constant(ret_type, None))
        
        return None
    
    def gen_break_stmt(self, node: BreakStmt):
        """
        生成 break 語句代碼
        
        Args:
            node: break 語句節點
            
        Returns:
            None
        """
        if not self.loop_exit_blocks:
            raise RuntimeError("Break 語句必須在循環內部使用")
        
        # 跳轉到當前循環的出口
        self.base.builder.branch(self.loop_exit_blocks[-1])
        
        return None
    
    def gen_continue_stmt(self, node: ContinueStmt):
        """
        生成 continue 語句代碼
        
        Args:
            node: continue 語句節點
            
        Returns:
            None
        """
        if not self.loop_continue_blocks:
            raise RuntimeError("Continue 語句必須在循環內部使用")
        
        # 跳轉到當前循環的繼續目標
        self.base.builder.branch(self.loop_continue_blocks[-1])
        
        return None
    
    def gen_throw_stmt(self, node: ThrowStmt):
        """
        生成 throw 語句代碼
        
        Args:
            node: throw 語句節點
            
        Returns:
            None
        """
        # TODO: 實現異常處理
        raise NotImplementedError("Throw 語句尚未實現")
    
    def gen_try_catch_stmt(self, node: TryCatchStmt):
        """
        生成 try-catch 語句代碼
        
        Args:
            node: try-catch 語句節點
            
        Returns:
            None
        """
        # TODO: 實現異常處理
        raise NotImplementedError("Try-catch 語句尚未實現")
    
    def gen_assign_stmt(self, node: AssignStmt):
        """
        生成賦值語句代碼
        
        Args:
            node: 賦值語句節點
            
        Returns:
            None
        """
        # 生成右值
        right_value = self.expr_gen.generate_expr(node.value)
        
        # 生成左值（目標位址）
        target = self.expr_gen.generate_address(node.target)
        
        # 確保類型匹配
        target_type = target.type.pointee
        if right_value.type != target_type:
            right_value = self._convert_type(right_value, right_value.type, target_type)
        
        # 存儲值
        self.base.builder.store(right_value, target)
        
        return None
    
    def _to_bool(self, value: ir.Value) -> ir.Value:
        """
        將值轉換為布爾類型
        
        Args:
            value: LLVM 值
            
        Returns:
            布爾類型值
        """
        if isinstance(value.type, ir.IntType):
            if value.type.width == 1:
                return value
            else:
                # 整數轉布爾：非零為真
                zero = ir.Constant(value.type, 0)
                return self.base.builder.icmp_unsigned('!=', value, zero)
        elif isinstance(value.type, (ir.FloatType, ir.DoubleType)):
            # 浮點數轉布爾：非零為真
            zero = ir.Constant(value.type, 0.0)
            return self.base.builder.fcmp_ordered('!=', value, zero)
        elif isinstance(value.type, ir.PointerType):
            # 指針轉布爾：非 null 為真
            null = ir.Constant(value.type, None)
            return self.base.builder.icmp_unsigned('!=', value, null)
        else:
            # 不支持的類型
            raise TypeError(f"無法將類型 {value.type} 轉換為布爾值")
    
    def _convert_type(self, value: ir.Value, from_type: ir.Type, to_type: ir.Type) -> ir.Value:
        """
        類型轉換
        
        Args:
            value: 要轉換的值
            from_type: 原始類型
            to_type: 目標類型
            
        Returns:
            轉換後的值
        """
        # 如果類型相同，不需要轉換
        if from_type == to_type:
            return value
        
        # 整數之間的轉換
        if isinstance(from_type, ir.IntType) and isinstance(to_type, ir.IntType):
            if from_type.width < to_type.width:
                # 小整數到大整數
                return self.base.builder.zext(value, to_type)
            else:
                # 大整數到小整數
                return self.base.builder.trunc(value, to_type)
        
        # 浮點數之間的轉換
        if isinstance(from_type, (ir.FloatType, ir.DoubleType)) and isinstance(to_type, (ir.FloatType, ir.DoubleType)):
            if isinstance(from_type, ir.FloatType) and isinstance(to_type, ir.DoubleType):
                # float 到 double
                return self.base.builder.fpext(value, to_type)
            else:
                # double 到 float
                return self.base.builder.fptrunc(value, to_type)
        
        # 整數到浮點數
        if isinstance(from_type, ir.IntType) and isinstance(to_type, (ir.FloatType, ir.DoubleType)):
            # 判斷是否有符號
            # 這裡假設所有整數都是有符號的
            return self.base.builder.sitofp(value, to_type)
        
        # 浮點數到整數
        if isinstance(from_type, (ir.FloatType, ir.DoubleType)) and isinstance(to_type, ir.IntType):
            # 這裡假設所有整數都是有符號的
            return self.base.builder.fptosi(value, to_type)
        
        # 指針之間的轉換
        if isinstance(from_type, ir.PointerType) and isinstance(to_type, ir.PointerType):
            return self.base.builder.bitcast(value, to_type)
        
        # 其他類型轉換暫不支持
        raise TypeError(f"不支持從 {from_type} 轉換到 {to_type}")
    
    def generate_concurrency(self, spawn_node):
        """生成併發相關代碼"""
        # 確保已初始化併發運行時
        self._ensure_concurrency_runtime()
        
        # 生成函數原型
        func_type = ir.FunctionType(
            spawn_node.func.return_type,
            [param.type for param in spawn_node.func.params]
        )
        
        # 創建任務並生成函數體
        task_id = self._create_task(spawn_node.func, func_type)
        
        # 啟動任務
        self._spawn_task(task_id, spawn_node.args)
        
        # 返回任務 ID
        return task_id

    def _ensure_concurrency_runtime(self):
        """確保併發運行時已初始化"""
        if not hasattr(self, "_concurrency_initialized"):
            # 創建任務管理器
            self._init_task_manager()
            self._concurrency_initialized = True

    def _init_task_manager(self):
        """初始化任務管理器"""
        # 創建任務表
        self.tasks = {}
        self.task_counter = 0
        
        # 創建任務池
        task_pool_type = ir.LiteralStructType([
            ir.IntType(32),                          # 任務數量
            ir.ArrayType(ir.IntType(8).as_pointer(), 64)  # 任務指針數組
        ])
        
        self.task_pool = self.module.add_global(task_pool_type, "glux.task_pool")
        self.task_pool.initializer = ir.Constant(task_pool_type, [0, [None] * 64])

    def _create_task(self, func_node, func_type):
        """創建任務"""
        # 生成唯一的任務 ID
        task_id = self.task_counter
        self.task_counter += 1
        
        # 定義任務函數
        func_name = f"task_{task_id}"
        task_func = ir.Function(self.module, func_type, name=func_name)
        
        # 保存任務
        self.tasks[task_id] = {
            "function": task_func,
            "node": func_node
        }
        
        # 生成函數體
        with self.base.builder.goto_entry_block(task_func):
            self.generate_stmt(func_node.body)
        
        return task_id

    def _spawn_task(self, task_id, args):
        """啟動任務"""
        task_info = self.tasks[task_id]
        task_func = task_info["function"]
        
        # 創建參數數組
        arg_values = []
        for arg_expr in args:
            arg_value = self.expr_gen.generate_expr(arg_expr)
            arg_values.append(arg_value)
        
        # 調用任務調度函數
        self.builder.call(
            self.module.get_global("glux.spawn_task"),
            [task_func, *arg_values]
        )

    def generate_await(self, await_node):
        """生成 await 代碼"""
        # 檢查是單個還是多個任務
        if len(await_node.tasks) == 1:
            # 單個任務
            task_id = await_node.tasks[0]
            return self._await_single_task(task_id)
        else:
            # 多個任務
            return self._await_multiple_tasks(await_node.tasks)

    def _await_single_task(self, task_id):
        """等待單個任務"""
        task_info = self.tasks[task_id]
        
        # 調用等待函數
        result = self.builder.call(
            self.module.get_global("glux.await_task"),
            [ir.Constant(ir.IntType(32), task_id)]
        )
        
        return result

    def _await_multiple_tasks(self, task_ids):
        """等待多個任務"""
        results = []
        
        for task_id in task_ids:
            result = self._await_single_task(task_id)
            results.append(result)
        
        # 創建結果元組
        tuple_type = ir.LiteralStructType([result.type for result in results])
        tuple_ptr = self.builder.alloca(tuple_type)
        
        # 設置結果
        for i, result in enumerate(results):
            elem_ptr = self.builder.gep(tuple_ptr, [
                ir.Constant(ir.IntType(32), 0),
                ir.Constant(ir.IntType(32), i)
            ])
            self.builder.store(result, elem_ptr)
        
        return tuple_ptr

    def generate_struct_inheritance(self, struct_node):
        """生成結構體繼承相關代碼"""
        # 基本結構
        struct_type = ir.LiteralStructType([field.type for field in struct_node.fields])
        struct_name = struct_node.name
        
        # 註冊結構體類型
        self.type_generator.register_struct_type(
            struct_name,
            struct_type,
            [field.name for field in struct_node.fields]
        )
        
        # 處理繼承
        if struct_node.base:
            base_name = struct_node.base.name
            base_type = self.type_generator.get_llvm_type(base_name)
            
            # 獲取基類欄位
            base_fields = self.type_generator.get_struct_fields(base_name)
            if not base_fields:
                self.errors.append(f"找不到基類 {base_name} 的欄位信息")
                return None
            
            # 合併基類和當前結構體欄位
            all_fields = []
            all_field_names = []
            
            # 首先添加基類欄位
            for i, (field_type, field_name) in enumerate(zip(base_fields[0], base_fields[1])):
                # 檢查是否被覆寫
                overridden = False
                for current_field in struct_node.fields:
                    if (current_field.name == field_name and 
                        hasattr(current_field, 'override') and 
                        current_field.override):
                        overridden = True
                        all_fields.append(current_field.type)
                        all_field_names.append(current_field.name)
                        break
                
                if not overridden:
                    all_fields.append(field_type)
                    all_field_names.append(field_name)
            
            # 然後添加當前結構體的新欄位
            for field in struct_node.fields:
                # 跳過已處理的覆寫欄位
                if hasattr(field, 'override') and field.override:
                    continue
                
                all_fields.append(field.type)
                all_field_names.append(field.name)
            
            # 創建完整的結構體類型
            extended_struct_type = ir.LiteralStructType(all_fields)
            
            # 重新註冊結構體類型
            self.type_generator.register_struct_type(
                struct_name,
                extended_struct_type,
                all_field_names
            )
        
        return struct_name 