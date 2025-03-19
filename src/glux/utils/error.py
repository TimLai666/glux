"""
錯誤處理模組
定義Glux語言編譯過程中的各種錯誤類型
"""

from typing import Optional


class GluxError(Exception):
    """Glux語言錯誤的基類"""
    
    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None):
        """
        初始化錯誤
        
        Args:
            message: 錯誤訊息
            line: 發生錯誤的行號（可選）
            column: 發生錯誤的列號（可選）
        """
        self.message = message
        self.line = line
        self.column = column
        
        # 構建帶有位置資訊的完整訊息
        if line is not None and column is not None:
            full_message = f"行 {line}, 列 {column}: {message}"
        elif line is not None:
            full_message = f"行 {line}: {message}"
        else:
            full_message = message
            
        super().__init__(full_message)


class LexicalError(GluxError):
    """詞法分析錯誤"""
    pass


class SyntaxError(GluxError):
    """語法分析錯誤"""
    pass


class SemanticError(GluxError):
    """語義分析錯誤"""
    pass


class TypeError(SemanticError):
    """類型錯誤"""
    pass


class NameError(SemanticError):
    """名稱解析錯誤"""
    pass


class CodegenError(GluxError):
    """代碼生成錯誤"""
    pass 