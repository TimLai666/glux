"""
字串插值處理模組
負責解析和處理用反引號(`)定義的帶插值的字串
"""

from typing import List, Tuple, Optional
from ..lexer.lexer import Token, TokenType
from . import ast_nodes


class StringInterpolationProcessor:
    """
    字串插值處理器
    處理字串中的表達式插值，例如 `Hello, ${name}!`
    """
    
    def __init__(self, parser):
        """
        初始化字串插值處理器
        
        Args:
            parser: 解析器實例，用於解析插值表達式
        """
        self.parser = parser
    
    def process_string(self, content: str, string_type: str) -> ast_nodes.Expression:
        """
        處理字串內容，識別並處理插值表達式
        
        Args:
            content: 字串內容
            string_type: 字串引號類型（'、"、`）
            
        Returns:
            處理後的表達式
        """
        # 只有反引號(`)字串才支援插值
        if string_type != '`':
            return ast_nodes.StringLiteral(content)
        
        # 處理插值
        parts = []
        pos = 0
        
        while pos < len(content):
            # 尋找下一個插值標記
            start = content.find('${', pos)
            
            if start == -1:
                # 沒有更多插值，添加剩餘部分
                if pos < len(content):
                    parts.append(ast_nodes.StringLiteral(content[pos:]))
                break
            
            # 添加插值前的文本
            if start > pos:
                parts.append(ast_nodes.StringLiteral(content[pos:start]))
            
            # 找到插值結束位置
            end = content.find('}', start + 2)
            if end == -1:
                # 插值未閉合，視為普通文本
                parts.append(ast_nodes.StringLiteral(content[pos:]))
                break
            
            # 解析插值表達式
            expr_text = content[start+2:end]
            expr = self._parse_interpolation_expression(expr_text)
            
            # 將表達式轉換為字串 - 使用 string 函數
            string_expr = ast_nodes.CallExpression(
                ast_nodes.Variable("string"),
                [expr]
            )
            
            # 添加到部件列表
            parts.append(string_expr)
            
            # 更新位置
            pos = end + 1
        
        # 如果只有一個部分，直接返回
        if len(parts) == 1:
            return parts[0]
        
        # 否則使用字串連接運算符連接所有部分
        result = parts[0]
        for part in parts[1:]:
            result = ast_nodes.BinaryExpr(result, '+', part)
        
        return result
    
    def _parse_interpolation_expression(self, expr_text: str) -> ast_nodes.Expression:
        """
        解析插值表達式
        
        Args:
            expr_text: 表達式文本
            
        Returns:
            解析後的表達式
        """
        # 保存當前解析狀態
        saved_tokens = self.parser.tokens.copy()
        saved_current = self.parser.current
        
        try:
            # 使用臨時 Lexer 對表達式進行詞法分析
            from ..lexer.lexer import Lexer
            lexer = Lexer(expr_text)
            tokens = lexer.tokenize()
            
            # 創建臨時解析器
            from .parser import Parser
            temp_parser = Parser(tokens)
            
            # 解析表達式
            expr = temp_parser.expression()
            
            return expr
        except Exception as e:
            # 解析失敗，返回一個錯誤文本節點
            return ast_nodes.StringLiteral(f"${{ERROR: {str(e)}}}")
        finally:
            # 恢復解析狀態
            self.parser.tokens = saved_tokens
            self.parser.current = saved_current 