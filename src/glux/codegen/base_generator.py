"""
代碼生成器基類模組
定義代碼生成器的基本介面
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import logging

from ..parser import ast_nodes


class CodeGenerator(ABC):
    """代碼生成器抽象基類，定義通用介面"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """初始化代碼生成器"""
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.errors: List[str] = []
    
    @abstractmethod
    def generate(self, ast: ast_nodes.Module) -> str:
        """生成目標代碼"""
        pass 