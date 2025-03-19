"""
接口分析器模塊
負責處理接口定義和繼承關係
"""

from typing import Dict, Set, List, Optional
import logging

from ..parser import ast_nodes
from ..type_system.type_system import TypeSystem
from ..type_system.type_defs import GluxType, TypeKind
from ..utils.symbol_table import SymbolTable, SymbolKind, Symbol


class InterfaceAnalyzer:
    """
    接口分析器類
    負責處理接口定義、接口繼承和接口實現關係
    """
    
    def __init__(self, symbol_table: SymbolTable):
        """
        初始化接口分析器
        
        Args:
            symbol_table: 符號表
        """
        self.symbol_table = symbol_table
        self.errors = []
        self.warnings = []
        self.logger = logging.getLogger("InterfaceAnalyzer")
        
        # 接口繼承圖
        self.interface_inheritance = {}  # 接口名稱 -> 父接口集合
    
    def analyze_interface(self, interface: ast_nodes.InterfaceDeclaration):
        """
        分析接口聲明
        
        Args:
            interface: 接口聲明節點
        """
        interface_name = interface.name
        
        # 檢查接口名稱是否已定義
        existing_symbol = self.symbol_table.resolve_current_scope(interface_name)
        if existing_symbol:
            self.errors.append(f"接口 '{interface_name}' 已在當前作用域中定義")
            return
        
        # 分析父接口
        parent_interfaces = []
        if interface.extends:
            # 處理接口繼承
            for parent_name in interface.extends:
                parent_symbol = self.symbol_table.resolve_type(parent_name)
                if not parent_symbol:
                    self.errors.append(f"未知接口 '{parent_name}' 在接口 '{interface_name}' 的繼承列表中")
                    continue
                
                if parent_symbol.kind != SymbolKind.INTERFACE:
                    self.errors.append(f"'{parent_name}' 不是一個接口，不能被接口 '{interface_name}' 繼承")
                    continue
                
                parent_interfaces.append(parent_symbol)
        
        # 創建接口類型
        interface_type = GluxType(
            name=interface_name,
            kind=TypeKind.INTERFACE,
            methods={},
            parent_interfaces=[p.name for p in parent_interfaces]
        )
        
        # 在符號表中註冊接口
        self.symbol_table.define_type(
            interface_name,
            interface_type,
            SymbolKind.INTERFACE
        )
        
        # 記錄接口繼承關係
        self.interface_inheritance[interface_name] = set(p.name for p in parent_interfaces)
        
        # 分析接口方法
        method_signatures = {}
        for method in interface.methods:
            method_name = method.name
            
            # 檢查方法是否重複定義
            if method_name in method_signatures:
                self.errors.append(f"方法 '{method_name}' 在接口 '{interface_name}' 中重複定義")
                continue
            
            # 解析方法參數
            param_types = []
            for param in method.parameters:
                param_type_name = param.type_annotation.name
                param_type_symbol = self.symbol_table.resolve_type(param_type_name)
                if not param_type_symbol:
                    self.errors.append(f"未知參數類型 '{param_type_name}' 在方法 '{method_name}' 參數 '{param.name}'")
                    param_types.append("any")  # 使用 any 作為默認類型
                else:
                    param_types.append(param_type_name)
            
            # 解析返回類型
            return_type = "void"
            if method.return_type:
                return_type_name = method.return_type.name
                return_type_symbol = self.symbol_table.resolve_type(return_type_name)
                if not return_type_symbol:
                    self.errors.append(f"未知返回類型 '{return_type_name}' 在方法 '{method_name}'")
                    return_type = "any"
                else:
                    return_type = return_type_name
            
            # 記錄方法簽名
            method_signatures[method_name] = {
                "params": param_types,
                "return_type": return_type
            }
        
        # 更新接口類型的方法表
        interface_type.methods = method_signatures
        
        # 繼承父接口的方法
        for parent_name in self.interface_inheritance.get(interface_name, []):
            parent_type = self.symbol_table.resolve_type(parent_name).type_info
            if hasattr(parent_type, 'methods'):
                for method_name, method_info in parent_type.methods.items():
                    # 如果接口中沒有定義該方法，則繼承父接口的方法
                    if method_name not in method_signatures:
                        interface_type.methods[method_name] = method_info
                    # 如果接口已定義同名方法，檢查簽名是否兼容
                    else:
                        # TODO: 檢查方法簽名兼容性
                        pass
    
    def check_struct_implements_interface(self, struct_type: GluxType, interface_name: str) -> bool:
        """
        檢查結構體是否實現接口
        
        Args:
            struct_type: 結構體類型
            interface_name: 接口名稱
            
        Returns:
            是否實現接口
        """
        interface_symbol = self.symbol_table.resolve_type(interface_name)
        if not interface_symbol or interface_symbol.kind != SymbolKind.INTERFACE:
            self.errors.append(f"'{interface_name}' 不是一個有效的接口")
            return False
        
        interface_type = interface_symbol.type_info
        
        # 檢查結構體是否實現接口的所有方法
        for method_name, method_info in interface_type.methods.items():
            # 查找結構體中的方法
            if not hasattr(struct_type, 'methods') or method_name not in struct_type.methods:
                self.errors.append(f"結構體 '{struct_type.name}' 未實現接口 '{interface_name}' 的方法 '{method_name}'")
                return False
            
            # 檢查方法簽名是否兼容
            struct_method = struct_type.methods[method_name]
            
            # 檢查返回類型
            if struct_method["return_type"] != method_info["return_type"]:
                self.errors.append(f"結構體 '{struct_type.name}' 的方法 '{method_name}' 返回類型與接口 '{interface_name}' 不兼容")
                return False
            
            # 檢查參數類型
            if len(struct_method["params"]) != len(method_info["params"]):
                self.errors.append(f"結構體 '{struct_type.name}' 的方法 '{method_name}' 參數數量與接口 '{interface_name}' 不兼容")
                return False
            
            for i, (struct_param, interface_param) in enumerate(zip(struct_method["params"], method_info["params"])):
                if struct_param != interface_param:
                    self.errors.append(f"結構體 '{struct_type.name}' 的方法 '{method_name}' 第 {i+1} 個參數類型與接口 '{interface_name}' 不兼容")
                    return False
        
        # 檢查是否實現接口繼承的所有接口
        for parent_interface in interface_type.parent_interfaces:
            if not self.check_struct_implements_interface(struct_type, parent_interface):
                return False
        
        return True 