"""
符號表模塊
提供符號表數據結構，支持作用域管理、符號查詢和定義
"""

from enum import Enum, auto
from typing import Dict, List, Optional, Set, Any, Union
from ..type_system.type_defs import GluxType
from ..type_system.type_system import TypeSystem


class SymbolKind(Enum):
    """符號種類"""
    VARIABLE = auto()     # 變量
    FUNCTION = auto()     # 函數
    PARAMETER = auto()    # 參數
    TYPE = auto()         # 類型
    STRUCT = auto()       # 結構體
    INTERFACE = auto()    # 接口
    ENUM = auto()         # 枚舉
    CONST = auto()        # 常量
    NAMESPACE = auto()    # 命名空間
    MODULE = auto()       # 模塊
    IMPORTED = auto()     # 導入的符號
    UNKNOWN = auto()      # 未知


class Symbol:
    """符號表中的符號項"""
    
    def __init__(self, 
                 name: str, 
                 kind: SymbolKind, 
                 type_info: Optional[GluxType] = None,
                 scope_level: int = 0,
                 is_mutable: bool = True,
                 is_initialized: bool = False,
                 is_used: bool = False,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        初始化符號
        
        Args:
            name: 符號名稱
            kind: 符號種類
            type_info: 類型信息
            scope_level: 作用域層級
            is_mutable: 是否可變
            is_initialized: 是否已初始化
            is_used: 是否已使用
            metadata: 元數據
        """
        self.name = name
        self.kind = kind
        self.type_info = type_info
        self.scope_level = scope_level
        self.is_mutable = is_mutable
        self.is_initialized = is_initialized
        self.is_used = is_used
        self.metadata = metadata or {}
        
    def __str__(self) -> str:
        """字符串表示"""
        type_str = f": {self.type_info}" if self.type_info else ""
        mutable_str = "" if self.is_mutable else " (immutable)"
        init_str = " (initialized)" if self.is_initialized else ""
        return f"{self.name}{type_str} [{self.kind.name}]{mutable_str}{init_str} @{self.scope_level}"


class Scope:
    """作用域類"""
    
    def __init__(self, parent: Optional['Scope'] = None, scope_name: str = ""):
        """
        初始化作用域
        
        Args:
            parent: 父作用域
            scope_name: 作用域名稱
        """
        self.symbols: Dict[str, Symbol] = {}
        self.parent = parent
        self.name = scope_name
        self.level = parent.level + 1 if parent else 0
        self.children: List['Scope'] = []
        
        # 如果有父作用域，將自己添加到父作用域的子作用域列表
        if parent:
            parent.children.append(self)
    
    def define(self, symbol: Symbol) -> Optional[Symbol]:
        """
        定義符號
        
        Args:
            symbol: 符號對象
            
        Returns:
            定義的符號，如果名稱衝突則返回 None
        """
        if symbol.name in self.symbols:
            return None  # 符號已存在於當前作用域
        
        # 設置正確的作用域層級
        symbol.scope_level = self.level
        self.symbols[symbol.name] = symbol
        return symbol
    
    def resolve(self, name: str) -> Optional[Symbol]:
        """
        在當前作用域查找符號
        
        Args:
            name: 符號名稱
            
        Returns:
            找到的符號，未找到則返回 None
        """
        return self.symbols.get(name)
    
    def resolve_local(self, name: str, include_parent: bool = True) -> Optional[Symbol]:
        """
        在本地作用域查找符號，可選是否包含父作用域的查找
        
        Args:
            name: 符號名稱
            include_parent: 是否包含父作用域
            
        Returns:
            找到的符號，未找到則返回 None
        """
        # 先在當前作用域查找
        symbol = self.resolve(name)
        if symbol:
            return symbol
        
        # 如果允許且有父作用域，則在父作用域中查找
        if include_parent and self.parent:
            return self.parent.resolve_local(name, True)
        
        # 未找到
        return None
    
    def get_all_symbols(self) -> Dict[str, Symbol]:
        """
        獲取所有符號，包括父作用域中的
        
        Returns:
            所有符號的字典
        """
        if not self.parent:
            return self.symbols.copy()
        
        # 獲取父作用域的所有符號
        all_symbols = self.parent.get_all_symbols()
        
        # 當前作用域的符號覆蓋父作用域的同名符號
        all_symbols.update(self.symbols)
        
        return all_symbols
    
    def get_local_symbols(self) -> Dict[str, Symbol]:
        """
        獲取當前作用域的符號
        
        Returns:
            當前作用域的符號字典
        """
        return self.symbols.copy()


class SymbolTable:
    """符號表類"""
    
    def __init__(self):
        """初始化符號表"""
        # 全局作用域
        self.global_scope = Scope(None, "global")
        self.current_scope = self.global_scope
        self.scope_level = 0
        
        # 跟蹤循環嵌套層級
        self.loop_depth = 0
        
        # 跟蹤當前函數的返回類型
        self.current_function_return_type = None
        
        # 跟蹤 unsafe 區塊
        self.unsafe_block_depth = 0
        
        # 特殊追踪：當前函數的返回類型
        self.current_function_return_type = None
        
        # 循環相關
        self.loop_stack = []  # 用於跟踪循環嵌套，影響 break/continue 是否有效
        
        # 錯誤信息
        self.errors = []
        self.warnings = []
    
    def enter_scope(self, scope_name: str = "") -> Scope:
        """
        進入新的作用域
        
        Args:
            scope_name: 作用域名稱
            
        Returns:
            新的作用域
        """
        self.current_scope = Scope(self.current_scope, scope_name)
        return self.current_scope
    
    def exit_scope(self) -> Scope:
        """
        離開當前作用域
        
        Returns:
            父作用域
            
        Raises:
            RuntimeError: 如果當前已是全局作用域
        """
        if self.current_scope == self.global_scope:
            raise RuntimeError("無法離開全局作用域")
        
        # 檢查未使用的變量
        self._check_unused_variables()
        
        self.current_scope = self.current_scope.parent
        return self.current_scope
    
    def define(self, name: str, kind: SymbolKind, type_info: Optional[GluxType] = None, 
               is_mutable: bool = True, is_initialized: bool = False, 
               metadata: Optional[Dict[str, Any]] = None) -> Optional[Symbol]:
        """
        在當前作用域定義符號
        
        Args:
            name: 符號名稱
            kind: 符號種類
            type_info: 類型信息
            is_mutable: 是否可變
            is_initialized: 是否已初始化
            metadata: 元數據
            
        Returns:
            定義的符號，如果名稱衝突則返回 None
        """
        # 創建新符號
        symbol = Symbol(
            name=name,
            kind=kind,
            type_info=type_info,
            scope_level=self.current_scope.level,
            is_mutable=is_mutable,
            is_initialized=is_initialized,
            metadata=metadata
        )
        
        # 嘗試在當前作用域定義符號
        result = self.current_scope.define(symbol)
        
        if result is None:
            self.errors.append(f"重複定義符號 '{name}' 在同一個作用域")
        
        return result
    
    def resolve(self, name: str) -> Optional[Symbol]:
        """
        解析符號（向上查找所有作用域）
        
        Args:
            name: 符號名稱
            
        Returns:
            符號或 None（如果未找到）
        """
        return self.current_scope.resolve_local(name, include_parent=True)
    
    def resolve_current_scope(self, name: str) -> Optional[Symbol]:
        """
        僅在當前作用域中解析符號（不查找父作用域）
        
        Args:
            name: 符號名稱
            
        Returns:
            符號或 None（如果在當前作用域未找到）
        """
        return self.current_scope.resolve_local(name, include_parent=False)
    
    def resolve_type(self, type_name: str) -> Optional[Symbol]:
        """
        解析類型符號
        
        Args:
            type_name: 類型名稱
            
        Returns:
            解析到的類型符號，未找到則返回 None
        """
        symbol = self.resolve(type_name)
        if symbol and symbol.kind in (SymbolKind.TYPE, SymbolKind.STRUCT, 
                                     SymbolKind.INTERFACE, SymbolKind.ENUM):
            return symbol
        return None
    
    def define_variable(self, name: str, type_info: Optional[GluxType], 
                        is_mutable: bool = True, is_initialized: bool = False) -> Optional[Symbol]:
        """
        定義變量
        
        Args:
            name: 變量名稱
            type_info: 類型信息
            is_mutable: 是否可變
            is_initialized: 是否已初始化
            
        Returns:
            定義的變量符號，如果名稱衝突則返回 None
        """
        return self.define(name, SymbolKind.VARIABLE, type_info, is_mutable, is_initialized)
    
    def define_constant(self, name: str, type_info: Optional[GluxType], 
                        is_initialized: bool = True) -> Optional[Symbol]:
        """
        定義常量
        
        Args:
            name: 常量名稱
            type_info: 類型信息
            is_initialized: 是否已初始化
            
        Returns:
            定義的常量符號，如果名稱衝突則返回 None
        """
        return self.define(name, SymbolKind.CONST, type_info, False, is_initialized)
    
    def define_function(self, name: str, return_type: Optional[GluxType], 
                        param_types: List[GluxType], param_names: List[str],
                        is_extern: bool = False) -> Optional[Symbol]:
        """
        定義函數符號
        
        Args:
            name: 函數名稱
            return_type: 返回類型
            param_types: 參數類型列表
            param_names: 參數名稱列表
            is_extern: 是否為外部函數
            
        Returns:
            定義的符號，或 None（如果重複定義）
        """
        # 創建函數類型
        fn_type = TypeSystem.create_function_type(return_type, param_types, param_names)
        
        # 函數元數據
        metadata = {
            "param_names": param_names,
            "param_types": param_types,
            "is_extern": is_extern
        }
        
        return self.define(name, SymbolKind.FUNCTION, fn_type, False, True, metadata)
    
    def define_builtin_function(self, name: str, fn_type: GluxType) -> Optional[Symbol]:
        """
        定義內建函數符號
        
        Args:
            name: 函數名稱
            fn_type: 函數類型
            
        Returns:
            定義的符號，或 None（如果重複定義）
        """
        # 內建函數永遠在全局作用域中
        temp_scope = self.current_scope
        self.current_scope = self.global_scope
        
        # 從函數類型中提取參數名稱和類型
        param_names = fn_type.param_names if hasattr(fn_type, 'param_names') else []
        param_types = fn_type.params if hasattr(fn_type, 'params') else []
        
        # 函數元數據
        metadata = {
            "param_names": param_names,
            "param_types": param_types,
            "is_builtin": True,
            "is_extern": True
        }
        
        symbol = self.define(name, SymbolKind.FUNCTION, fn_type, False, True, metadata)
        self.current_scope = temp_scope
        return symbol
    
    def define_type(self, name: str, type_info: GluxType) -> Optional[Symbol]:
        """
        定義類型符號
        
        Args:
            name: 符號名稱
            type_info: 類型資訊
            
        Returns:
            定義的符號，或 None（如果重複定義）
        """
        return self.define(name, SymbolKind.TYPE, type_info)
    
    def define_builtin_type(self, name: str, type_info: GluxType) -> Optional[Symbol]:
        """
        定義內建類型符號
        
        Args:
            name: 符號名稱
            type_info: 類型資訊
            
        Returns:
            定義的符號，或 None（如果重複定義）
        """
        # 內建類型永遠在全局作用域中
        temp_scope = self.current_scope
        self.current_scope = self.global_scope
        symbol = self.define(name, SymbolKind.TYPE, type_info)
        self.current_scope = temp_scope
        return symbol
    
    def define_struct(self, name: str, type_info: GluxType, 
                     field_names: List[str], field_types: List[GluxType]) -> Optional[Symbol]:
        """
        定義結構體
        
        Args:
            name: 結構體名稱
            type_info: 類型信息
            field_names: 字段名稱列表
            field_types: 字段類型列表
            
        Returns:
            定義的結構體符號，如果名稱衝突則返回 None
        """
        # 更新結構體類型信息
        type_info.field_names = field_names
        type_info.field_types = field_types
        
        # 結構體元數據
        metadata = {
            "field_names": field_names,
            "field_types": field_types
        }
        
        return self.define(name, SymbolKind.STRUCT, type_info, False, True, metadata)
    
    def mark_symbol_used(self, name: str) -> bool:
        """
        標記符號為已使用
        
        Args:
            name: 符號名稱
            
        Returns:
            是否成功標記
        """
        symbol = self.resolve(name)
        if symbol:
            symbol.is_used = True
            return True
        return False
    
    def mark_symbol_initialized(self, name: str) -> bool:
        """
        標記符號為已初始化
        
        Args:
            name: 符號名稱
            
        Returns:
            是否成功標記
        """
        symbol = self.resolve(name)
        if symbol:
            symbol.is_initialized = True
            return True
        return False
    
    def enter_loop(self):
        """進入循環"""
        self.loop_stack.append(True)
    
    def exit_loop(self):
        """離開循環"""
        if self.loop_stack:
            self.loop_stack.pop()
    
    def in_loop(self) -> bool:
        """
        檢查是否在循環中
        
        Returns:
            是否在循環中
        """
        return len(self.loop_stack) > 0
    
    def set_current_function_return_type(self, return_type: Optional[GluxType]):
        """
        設置當前函數的返回類型
        
        Args:
            return_type: 返回類型
        """
        self.current_function_return_type = return_type
    
    def get_current_function_return_type(self) -> Optional[GluxType]:
        """
        獲取當前函數的返回類型
        
        Returns:
            當前函數的返回類型
        """
        return self.current_function_return_type
    
    def _check_unused_variables(self):
        """檢查未使用的變量，添加警告"""
        for name, symbol in self.current_scope.symbols.items():
            if symbol.kind == SymbolKind.VARIABLE and not symbol.is_used:
                self.warnings.append(f"變量 '{name}' 在作用域 '{self.current_scope.name}' 中聲明但未使用")
    
    def dump(self) -> str:
        """
        輸出符號表的文本表示
        
        Returns:
            符號表的文本表示
        """
        result = ["符號表:"]
        
        def dump_scope(scope, indent=0):
            indent_str = "  " * indent
            scope_name = scope.name or f"<作用域#{scope.level}>"
            result.append(f"{indent_str}{scope_name}:")
            
            # 輸出符號
            symbols = scope.get_local_symbols()
            for name, symbol in sorted(symbols.items()):
                result.append(f"{indent_str}  {symbol}")
            
            # 輸出子作用域
            for child in scope.children:
                dump_scope(child, indent + 1)
        
        # 從全局作用域開始輸出
        dump_scope(self.global_scope)
        
        return "\n".join(result)
    
    def enter_unsafe_block(self):
        """進入 unsafe 區塊"""
        self.unsafe_block_depth += 1
    
    def exit_unsafe_block(self):
        """離開 unsafe 區塊"""
        if self.unsafe_block_depth > 0:
            self.unsafe_block_depth -= 1
    
    def is_in_unsafe_block(self) -> bool:
        """檢查是否在 unsafe 區塊中"""
        return self.unsafe_block_depth > 0
    
    def add_import(self, module_path: str, items: List[str] = None) -> None:
        """
        添加導入記錄
        
        Args:
            module_path: 模塊路徑
            items: 導入的項目列表
        """
        if not hasattr(self, 'imports'):
            self.imports = []
        
        self.imports.append({
            'module_path': module_path,
            'items': items or []
        }) 