from typing import Dict, Any, List, Optional
from src.glux.codegen.builtins import BuiltinModule
from llvmlite import ir
import logging


class ConcurrencyFunctions(BuiltinModule):
    """併發功能模塊"""

    def __init__(self, parent=None):
        """
        初始化併發函數模塊
        
        Args:
            parent: 父級代碼生成器
        """
        super().__init__()
        self.parent = parent
        self.logger = parent.logger if parent and hasattr(parent, 'logger') else logging.getLogger(__name__)
        self.context = None
        self.module = None
        self.builder = None
        
        # 運行時函數引用
        self.create_future_func = None
        self.spawn_task_func = None
        self.await_future_func = None
        self.await_multiple_func = None
        self.free_future_func = None
        self.get_multi_result_func = None
        self.free_multi_result_func = None
        
    def set_parent(self, parent):
        """設置父對象（代碼生成器）"""
        self.parent = parent
    
    def initialize(self, context=None):
        """初始化併發函數模組"""
        self.context = context
        
        # 處理context為None的情況
        if context is None:
            self.logger.debug("併發函數模組初始化：LLVM上下文尚未準備就緒，僅完成初步初始化")
            return
        
        # 正常初始化流程
        self.logger.debug("開始初始化併發函數模組...")
        
        # 聲明併發函數
        self._declare_concurrency_functions()
        
        self.logger.debug("併發函數模組初始化完成")
    
    def _declare_future_type(self):
        """聲明Future結構體類型"""
        # 檢查是否已經由type模組定義
        if hasattr(self.parent, 'future_type'):
            return
        
        # 獲取常用類型引用
        void_ptr_type = self.parent.context.void_ptr_type
        i32_type = self.parent.context.i32_type
        i1_type = self.parent.context.i1_type
        
        # 定義Future結構體
        future_type = self.parent.context.get_identified_type("Future")
        future_type.set_body(
            void_ptr_type,    # result: void*
            i32_type,         # status: int
            i1_type,          # is_multi_value: bool 
            i32_type,         # result_type_id: int
            i32_type,         # task_id: int
            self.parent.context.i8_type.as_pointer()  # error_message: char*
        )
        
        # 註冊到代碼生成器
        self.parent.future_type = future_type
    
    def _declare_runtime_functions(self):
        """聲明併發運行時函數"""
        # 通用類型引用
        void_type = self.parent.context.void_type
        i32_type = self.parent.context.i32_type
        void_ptr_type = self.parent.context.void_ptr_type
        future_ptr_type = self.parent.future_type.as_pointer()
        
        # 函數指針類型（void* (*)(void*)）- 用於任務函數
        task_func_type = ir.FunctionType(void_ptr_type, [void_ptr_type])
        task_func_ptr_type = task_func_type.as_pointer()
        
        # __glux_create_future - 創建Future對象
        self.create_future_func = ir.Function(
            self.module,
            ir.FunctionType(future_ptr_type, [i32_type]),
            name="__glux_create_future"
        )
        
        # __glux_spawn_task - 啟動併發任務
        self.spawn_task_func = ir.Function(
            self.module,
            ir.FunctionType(i32_type, [task_func_ptr_type, void_ptr_type, future_ptr_type]),
            name="__glux_spawn_task"
        )
        
        # __glux_await_future - 等待單個Future完成
        self.await_future_func = ir.Function(
            self.module,
            ir.FunctionType(void_ptr_type, [future_ptr_type]),
            name="__glux_await_future"
        )
        
        # __glux_await_multiple - 等待多個Future完成
        self.await_multiple_func = ir.Function(
            self.module,
            ir.FunctionType(
                void_ptr_type,
                [future_ptr_type.as_pointer(), i32_type]
            ),
            name="__glux_await_multiple"
        )
        
        # __glux_free_future - 釋放Future資源
        self.free_future_func = ir.Function(
            self.module,
            ir.FunctionType(void_type, [future_ptr_type]),
            name="__glux_free_future"
        )
        
        # __glux_get_multi_result - 獲取多值結果中的元素
        self.get_multi_result_func = ir.Function(
            self.module,
            ir.FunctionType(void_ptr_type, [void_ptr_type, i32_type]),
            name="__glux_get_multi_result"
        )
        
        # __glux_free_multi_result - 釋放多值結果
        self.free_multi_result_func = ir.Function(
            self.module,
            ir.FunctionType(void_type, [void_ptr_type]),
            name="__glux_free_multi_result"
        )
    
    def _create_task_wrapper(self, call_expr):
        """創建任務包裝函數"""
        # 1. 獲取目標函數的類型信息
        if hasattr(call_expr, 'callee'):
            func_name = call_expr.callee.name if hasattr(call_expr.callee, 'name') else "anonymous_func"
            func_ref = self.parent.function_manager.get_function(func_name)
            args = call_expr.arguments if hasattr(call_expr, 'arguments') else []
        else:
            self.logger.error("無效的函數調用表達式")
            return None
        
        # 2. 創建任務包裝函數
        wrapper_name = f"{func_name}_task_wrapper"
        wrapper_type = ir.FunctionType(
            self.parent.context.void_ptr_type,  # 返回 void*
            [self.parent.context.void_ptr_type]   # 接受 void* 參數
        )
        
        wrapper_func = ir.Function(self.module, wrapper_type, name=wrapper_name)
        
        # 3. 生成包裝函數體
        block = wrapper_func.append_basic_block(name="entry")
        saved_builder = self.builder
        self.builder = ir.IRBuilder(block)
        
        # 4. 從參數結構體中解包參數
        arg_struct_ptr = wrapper_func.args[0]
        
        # 5. 調用目標函數
        if func_ref:
            # 為每個參數生成加載代碼
            arg_values = []
            for i, arg in enumerate(args):
                # 計算參數在結構體中的位置
                idx = self.builder.const_int(self.parent.context.i32_type, i)
                ptr = self.builder.gep(arg_struct_ptr, [idx], name=f"arg{i}_ptr")
                # 加載參數值（需要轉換為正確類型）
                arg_value = self.builder.load(ptr, name=f"arg{i}")
                arg_values.append(arg_value)
            
            # 調用目標函數
            result = self.builder.call(func_ref, arg_values, name="task_result")
            
            # 返回結果（可能需要進行類型轉換）
            if result.type != self.parent.context.void_ptr_type:
                if result.type.is_pointer:
                    result_cast = self.builder.bitcast(result, self.parent.context.void_ptr_type, name="result_cast")
                elif result.type.is_integer:
                    alloc = self.builder.alloca(result.type, name="result_alloc")
                    self.builder.store(result, alloc)
                    result_cast = self.builder.bitcast(alloc, self.parent.context.void_ptr_type, name="result_cast")
                else:
                    self.logger.warning(f"未知的返回類型轉換: {result.type}")
                    result_cast = self.builder.inttoptr(
                        self.builder.const_int(self.parent.context.i64_type, 0),
                        self.parent.context.void_ptr_type
                    )
            else:
                result_cast = result
            
            self.builder.ret(result_cast)
        else:
            # 如果找不到函數引用，返回NULL
            null_ptr = self.builder.inttoptr(
                self.builder.const_int(self.parent.context.i64_type, 0),
                self.parent.context.void_ptr_type
            )
            self.builder.ret(null_ptr)
        
        # 恢復原始Builder
        self.builder = saved_builder
        
        return wrapper_func
    
    def _create_task_arg_struct(self, call_expr):
        """創建任務參數結構體並填充"""
        if hasattr(call_expr, 'arguments'):
            args = call_expr.arguments
        else:
            args = []
        
        # 分配參數數組
        array_type = self.parent.context.void_ptr_type.as_pointer()
        
        if len(args) > 0:
            # 分配參數數組內存
            arg_array = self.builder.alloca(
                array_type,
                size=self.builder.const_int(self.parent.context.i32_type, len(args)),
                name="task_args"
            )
            
            # 填充參數
            for i, arg in enumerate(args):
                # 生成參數值
                arg_value = self.parent.generate_expression(arg)
                
                # 計算數組元素地址
                idx = self.builder.const_int(self.parent.context.i32_type, i)
                ptr = self.builder.gep(arg_array, [idx], name=f"arg{i}_ptr")
                
                # 如果需要，轉換類型為void*
                if arg_value.type != self.parent.context.void_ptr_type:
                    if arg_value.type.is_pointer:
                        arg_cast = self.builder.bitcast(arg_value, self.parent.context.void_ptr_type)
                    elif arg_value.type.is_integer:
                        # 為整數分配內存
                        alloc = self.builder.alloca(arg_value.type, name=f"arg{i}_alloc")
                        self.builder.store(arg_value, alloc)
                        arg_cast = self.builder.bitcast(alloc, self.parent.context.void_ptr_type)
                    else:
                        self.logger.warning(f"未知的參數類型轉換: {arg_value.type}")
                        # 默認為NULL
                        arg_cast = self.builder.inttoptr(
                            self.builder.const_int(self.parent.context.i64_type, 0),
                            self.parent.context.void_ptr_type
                        )
                else:
                    arg_cast = arg_value
                
                # 存儲參數
                self.builder.store(arg_cast, ptr)
            
            return arg_array
        else:
            # 沒有參數時返回NULL
            return self.builder.inttoptr(
                self.builder.const_int(self.parent.context.i64_type, 0),
                self.parent.context.void_ptr_type
            )
    
    def _get_type_id(self, type_name):
        """獲取類型ID"""
        if hasattr(self.parent, 'modules') and 'type' in self.parent.modules:
            type_module = self.parent.modules['type']
            if hasattr(type_module, 'get_type_id'):
                return type_module.get_type_id(type_name)
        
        # 默認類型ID
        type_ids = {
            "void": 0,
            "bool": 1,
            "int": 2,
            "float": 7,
            "string": 9,
            None: 999
        }
        return type_ids.get(type_name, 999)
    
    def generate_spawn(self, call_expr):
        """生成spawn表達式的代碼"""
        self.logger.info("生成spawn表達式代碼")
        
        # 1. 創建任務函數包裝器（接收void*參數並返回void*結果）
        task_wrapper = self._create_task_wrapper(call_expr)
        
        # 2. 創建參數結構體並填充
        arg_struct_ptr = self._create_task_arg_struct(call_expr)
        
        # 3. 創建Future對象
        # 根據函數返回類型確定Future的類型
        return_type_id = self._get_type_id(call_expr.return_type)
        future_ptr = self.builder.call(
            self.create_future_func,
            [self.builder.const_int(self.parent.context.i32_type, return_type_id)]
        )
        
        # 4. 調用spawn運行時函數啟動任務
        task_id = self.builder.call(
            self.spawn_task_func,
            [task_wrapper, arg_struct_ptr, future_ptr]
        )
        
        # 返回Future對象
        return future_ptr
    
    def generate_await(self, futures):
        """生成await表達式的代碼"""
        self.logger.info("生成await表達式代碼")
        
        if len(futures) == 1:
            # 單個Future的等待
            future = futures[0]
            # 确保future是正确的类型
            if future.type != self.parent.future_type.as_pointer():
                self.logger.warning(f"嘗試await非Future類型: {future.type}")
                future = self.builder.bitcast(future, self.parent.future_type.as_pointer())
            
            # 等待Future完成並獲取結果
            result = self.builder.call(self.await_future_func, [future])
            return result
        else:
            # 多個Future的等待
            # 1. 分配Future指針數組
            futures_array = self.builder.alloca(
                self.parent.future_type.as_pointer().as_pointer(),
                size=self.builder.const_int(self.parent.context.i32_type, len(futures)),
                name="futures_array"
            )
            
            # 2. 填充數組
            for i, future in enumerate(futures):
                # 确保future是正确的类型
                if future.type != self.parent.future_type.as_pointer():
                    self.logger.warning(f"嘗試await非Future類型: {future.type}")
                    future = self.builder.bitcast(future, self.parent.future_type.as_pointer())
                
                # 计算數組元素地址
                idx = self.builder.const_int(self.parent.context.i32_type, i)
                ptr = self.builder.gep(futures_array, [idx], name=f"future{i}_ptr")
                
                # 存储Future指針
                self.builder.store(future, ptr)
            
            # 3. 调用多值等待函數
            result = self.builder.call(
                self.await_multiple_func,
                [
                    futures_array,
                    self.builder.const_int(self.parent.context.i32_type, len(futures))
                ]
            )
            
            return result
    
    def generate_multi_result_access(self, result, index):
        """生成多值結果訪問的代碼"""
        self.logger.info(f"生成多值結果訪問代碼，索引: {index}")
        
        # 調用運行時函數獲取特定索引的結果
        element = self.builder.call(
            self.get_multi_result_func,
            [
                result,
                self.builder.const_int(self.parent.context.i32_type, index)
            ]
        )
        
        return element

    def _declare_concurrency_functions(self):
        """聲明所有併發函數到LLVM模塊"""
        # 檢查LLVM上下文是否就緒
        if self.context is None or not hasattr(self.context, 'module') or self.context.module is None:
            self.parent.logger.warning("無法聲明併發函數：LLVM上下文未初始化")
            return
            
        try:
            # 定義Future類型
            self._declare_future_type()
            
            # 定義併發運行時函數
            self._declare_runtime_functions()
            
            self.logger.debug("併發函數聲明完成")
        except Exception as e:
            self.logger.error(f"聲明併發函數時出錯: {e}")
            import traceback
            traceback.print_exc() 