from typing import Dict, Any, List, Optional
from src.glux.codegen.builtins import BuiltinModule


class ClosureFunctions(BuiltinModule):
    """閉包相關函數模塊"""

    def __init__(self):
        super().__init__()
        self.parent = None
        self.closure_counter = 0
        
    def set_parent(self, parent):
        """設置父級代碼生成器"""
        self.parent = parent
    
    def initialize(self, context):
        """初始化閉包函數模塊"""
        self.context = context
        self.logger = context.logger
        self.logger.info("初始化閉包函數模塊")
    
    def build_closure_env(self, captured_vars, parent_env=None):
        """構建閉包環境結構體"""
        # 為閉包環境創建一個結構體類型
        closure_id = self.closure_counter
        self.closure_counter += 1
        
        env_name = f"closure_env_{closure_id}"
        
        # 收集所有捕獲變數的類型
        field_types = []
        for var_name, var_info in captured_vars.items():
            # 將LLVM類型轉換為結構體字段類型
            var_type = var_info["type"]
            field_types.append((var_name, var_type))
        
        # 如果有父環境，添加父環境指針
        if parent_env:
            field_types.append(("parent", parent_env.as_pointer()))
        
        # 在LLVM中創建結構體類型
        struct_type = self.parent.context.get_identified_type(env_name)
        struct_type.set_body(*[t for _, t in field_types])
        
        return struct_type, env_name, field_types
    
    def create_closure_function(self, func_name, params, ret_type, body, captured_vars):
        """創建閉包函數"""
        self.logger.info(f"創建閉包函數 {func_name}")
        
        # 構建閉包環境
        env_type, env_name, field_types = self.build_closure_env(captured_vars)
        
        # 創建閉包函數類型（添加環境參數）
        func_params = [env_type.as_pointer()] + params
        func_type = self.parent.get_function_type(ret_type, func_params)
        
        # 創建函數
        func = self.parent.module.add_function(func_name, func_type)
        
        # 設置函數參數名稱
        func.args[0].name = "env"
        for i, param in enumerate(params):
            func.args[i+1].name = f"param_{i}"
        
        # 創建入口基本塊
        entry_block = func.append_basic_block("entry")
        builder = self.parent.context.new_builder(entry_block)
        
        # 保存當前狀態
        old_builder = self.parent.builder
        old_func = self.parent.current_function
        old_block = self.parent.current_block
        
        # 設置新狀態
        self.parent.builder = builder
        self.parent.current_function = func
        self.parent.current_block = entry_block
        
        # 處理捕獲的變數 - 從環境中加載
        env_ptr = func.args[0]
        for i, (var_name, _) in enumerate(field_types):
            if var_name != "parent":  # 跳過父環境指針
                # 獲取變數在結構體中的索引
                idx = i
                
                # 獲取變數指針
                var_ptr = builder.gep(env_type, env_ptr, [
                    self.parent.context.const_int(self.parent.context.i32_type, 0),
                    self.parent.context.const_int(self.parent.context.i32_type, idx)
                ])
                
                # 加載變數值
                var_type = field_types[i][1]
                var_value = builder.load(var_type, var_ptr)
                
                # 將變數添加到符號表
                self.parent.add_variable(var_name, var_ptr, var_type)
        
        # 生成函數體代碼
        self.parent.generate_statements(body)
        
        # 添加默認返回值（如果函數沒有顯式返回）
        if not builder.block.is_terminated:
            if ret_type == self.parent.context.void_type:
                builder.ret_void()
            else:
                builder.ret(self.parent.context.const_int(ret_type, 0))
        
        # 恢復之前的狀態
        self.parent.builder = old_builder
        self.parent.current_function = old_func
        self.parent.current_block = old_block
        
        return func
    
    def create_closure(self, func_name, params, ret_type, body, captured_vars):
        """創建完整的閉包（函數+環境）"""
        # 創建閉包函數
        closure_func = self.create_closure_function(
            func_name, params, ret_type, body, captured_vars
        )
        
        # 構建閉包環境類型
        env_type, env_name, field_types = self.build_closure_env(captured_vars)
        
        # 分配環境結構體
        env_ptr = self.parent.builder.alloca(env_type)
        
        # 填充環境結構體 - 存儲捕獲的變數
        for i, (var_name, _) in enumerate(field_types):
            if var_name != "parent":  # 跳過父環境指針
                # 獲取變數在結構體中的索引
                idx = i
                
                # 獲取變數在當前作用域中的值
                var_value = self.parent.get_variable(var_name)
                
                # 獲取環境中變數的指針
                dst_ptr = self.parent.builder.gep(env_type, env_ptr, [
                    self.parent.context.const_int(self.parent.context.i32_type, 0),
                    self.parent.context.const_int(self.parent.context.i32_type, idx)
                ])
                
                # 存儲變數值到環境
                var_type = field_types[i][1]
                self.parent.builder.store(var_value, dst_ptr)
        
        # 創建閉包結構體 (函數指針 + 環境)
        closure_type = self.parent.get_closure_type(ret_type, params)
        closure_ptr = self.parent.builder.alloca(closure_type)
        
        # 存儲函數指針
        func_ptr_field = self.parent.builder.gep(closure_type, closure_ptr, [
            self.parent.context.const_int(self.parent.context.i32_type, 0),
            self.parent.context.const_int(self.parent.context.i32_type, 0)
        ])
        self.parent.builder.store(closure_func, func_ptr_field)
        
        # 存儲環境指針
        env_ptr_field = self.parent.builder.gep(closure_type, closure_ptr, [
            self.parent.context.const_int(self.parent.context.i32_type, 0),
            self.parent.context.const_int(self.parent.context.i32_type, 1)
        ])
        self.parent.builder.store(env_ptr, env_ptr_field)
        
        return closure_ptr, closure_type 