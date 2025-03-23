"""
Glux 編譯器內建函數實現模塊
此模塊包含所有內建函數的實現
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, List

# 內建模塊基類
class BuiltinModule(ABC):
    """所有內建函數模塊的基類"""

    def __init__(self, parent=None):
        """初始化內建函數模組"""
        self.parent = parent
    
    @abstractmethod
    def set_parent(self, parent):
        """設置父對象（代碼生成器）"""
        pass
    
    @abstractmethod
    def initialize(self, context):
        """初始化模塊"""
        pass

# 模塊註冊表
_module_registry: Dict[str, Type[BuiltinModule]] = {}

def register_module(name: str, module_class: Type[BuiltinModule]):
    """註冊一個模塊"""
    _module_registry[name] = module_class

def get_module(name: str) -> Optional[Type[BuiltinModule]]:
    """獲取一個已註冊的模塊"""
    return _module_registry.get(name)

def get_all_modules() -> Dict[str, Type[BuiltinModule]]:
    """獲取所有已註冊的模塊"""
    return _module_registry.copy()

# 導入所有內建模塊
from src.glux.codegen.builtins.print_functions import PrintFunctions
from src.glux.codegen.builtins.string_functions import StringFunctions
from src.glux.codegen.builtins.expr_functions import ExprFunctions
from src.glux.codegen.builtins.variable_functions import VariableFunctions
from src.glux.codegen.builtins.literal_functions import LiteralFunctions
from src.glux.codegen.builtins.standard_functions import StandardFunctions
from src.glux.codegen.concurrency_functions import ConcurrencyFunctions
from src.glux.codegen.type_functions import TypeFunctions

# 註冊所有內建模塊
register_module("print", PrintFunctions)
register_module("string", StringFunctions)
register_module("expr", ExprFunctions)
register_module("variable", VariableFunctions)
register_module("literal", LiteralFunctions)
register_module("std", StandardFunctions)
register_module("concurrency", ConcurrencyFunctions)
register_module("type", TypeFunctions) 