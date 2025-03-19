"""
Glux 語言的詞法分析器
將源碼轉換為詞法單元序列
"""

import re
from enum import Enum, auto
from typing import List, Dict, Any, Optional, Union, Tuple, Callable


class TokenType(Enum):
    """詞法單元類型"""
    # 關鍵字
    AND = auto()
    ANY = auto()
    BOOL = auto()
    CONST = auto()
    COPY = auto()
    ELSE = auto()
    ENUM = auto()     # enum 關鍵字
    ERROR = auto()
    EXTENDS = auto()
    FALSE = auto()
    FLOAT = auto()
    FN = auto()
    FOR = auto()
    IF = auto()
    IN = auto()
    INT = auto()
    INTERFACE = auto()
    IS_ERROR = auto()
    LEN = auto()
    LIST = auto()
    MAP = auto()
    NOT = auto()
    OPTIONAL = auto()
    OR = auto()
    PTR = auto()
    PRINT = auto()
    PRINTLN = auto()
    RETURN = auto()
    SLEEP = auto()
    SPAWN = auto()
    STRING = auto()
    STRUCT = auto()
    TRUE = auto()
    TUPLE = auto()
    UNION = auto()
    UNSAFE = auto()
    AWAIT = auto()
    WHILE = auto()
    OVERRIDE = auto()
    NULL = auto()
    VOID = auto()     # void 關鍵字
    
    # 標識符
    IDENTIFIER = auto()
    
    # 字面量
    NUMBER = auto()        # 整數字面量
    FLOAT_LITERAL = auto() # 浮點數字面量
    STRING_LITERAL = auto() # 字符串字面量
    CHAR_LITERAL = auto()  # 字符字面量
    TEMPLATE_STRING = auto() # 模板字符串（反引號）
    
    # 運算符
    PLUS = auto()          # +
    MINUS = auto()         # -
    STAR = auto()          # *
    SLASH = auto()         # /
    PERCENT = auto()       # %
    
    # 位運算符
    AMPERSAND = auto()     # &
    PIPE = auto()          # |
    CARET = auto()         # ^
    TILDE = auto()         # ~
    LEFT_SHIFT = auto()    # <<
    RIGHT_SHIFT = auto()   # >>
    
    # 比較運算符
    EQUAL_EQUAL = auto()   # ==
    BANG_EQUAL = auto()    # !=
    LESS = auto()          # <
    LESS_EQUAL = auto()    # <=
    GREATER = auto()       # >
    GREATER_EQUAL = auto() # >=
    
    # 邏輯運算符
    LOGICAL_AND = auto()   # &&
    LOGICAL_OR = auto()    # ||
    BANG = auto()          # !
    QUESTION = auto()      # ?
    
    # 賦值運算符
    EQUAL = auto()         # =
    PLUS_EQUAL = auto()    # +=
    MINUS_EQUAL = auto()   # -=
    STAR_EQUAL = auto()    # *=
    SLASH_EQUAL = auto()   # /=
    PERCENT_EQUAL = auto() # %=
    AMPERSAND_EQUAL = auto() # &=
    PIPE_EQUAL = auto()    # |=
    CARET_EQUAL = auto()   # ^=
    LEFT_SHIFT_EQUAL = auto() # <<=
    RIGHT_SHIFT_EQUAL = auto() # >>=
    COLONEQ = auto()       # :=
    
    # 分隔符
    LEFT_PAREN = auto()    # (
    RIGHT_PAREN = auto()   # )
    LEFT_BRACE = auto()    # {
    RIGHT_BRACE = auto()   # }
    LEFT_BRACKET = auto()  # [
    RIGHT_BRACKET = auto() # ]
    COMMA = auto()         # ,
    DOT = auto()           # .
    DOT_DOT = auto()       # ..
    COLON = auto()         # :
    SEMICOLON = auto()     # ;
    ARROW = auto()         # ->
    
    # 其他
    EOF = auto()           # 文件結束
    DOLLAR = auto()         # $
    BACKSLASH = auto()      # \


class Token:
    """詞法單元類"""
    
    def __init__(self, type: TokenType, lexeme: str, literal: Any, line: int, column: int):
        """
        初始化詞法單元
        
        Args:
            type: 詞法單元類型
            lexeme: 詞法單元文本表示
            literal: 詞法單元字面值 (可選)
            line: 行號
            column: 列號
        """
        self.type = type
        self.lexeme = lexeme
        self.literal = literal
        self.line = line
        self.column = column
    
    def __str__(self) -> str:
        """
        詞法單元的字符串表示
        
        Returns:
            字符串表示
        """
        literal_str = f" {self.literal}" if self.literal is not None else ""
        return f"{self.type.name}('{self.lexeme}'{literal_str}) at {self.line}:{self.column}"


class Lexer:
    """詞法分析器類"""
    
    # 保留關鍵字映射
    KEYWORDS = {
        'and': TokenType.AND,
        'any': TokenType.ANY,
        'bool': TokenType.BOOL,
        'const': TokenType.CONST,
        'copy': TokenType.COPY,
        'else': TokenType.ELSE,
        'error': TokenType.ERROR,
        'extends': TokenType.EXTENDS,
        'false': TokenType.FALSE,
        'float': TokenType.FLOAT,
        'fn': TokenType.FN,
        'for': TokenType.FOR,
        'if': TokenType.IF,
        'in': TokenType.IN,
        'int': TokenType.INT,
        'interface': TokenType.INTERFACE,
        'is_error': TokenType.IS_ERROR,
        'len': TokenType.LEN,
        'list': TokenType.LIST,
        'map': TokenType.MAP,
        'not': TokenType.NOT,
        'optional': TokenType.OPTIONAL,
        'or': TokenType.OR,
        'ptr': TokenType.PTR,
        'print': TokenType.PRINT,
        'println': TokenType.PRINTLN,
        'return': TokenType.RETURN,
        'sleep': TokenType.SLEEP,
        'spawn': TokenType.SPAWN,
        'string': TokenType.STRING,
        'struct': TokenType.STRUCT,
        'true': TokenType.TRUE,
        'tuple': TokenType.TUPLE,
        'union': TokenType.UNION,
        'unsafe': TokenType.UNSAFE,
        'await': TokenType.AWAIT,
        'while': TokenType.WHILE,
        'override': TokenType.OVERRIDE,
        'void': TokenType.VOID,
        'null': TokenType.NULL
    }
    
    def __init__(self, source: str, file_name: str = "<stdin>"):
        """
        初始化詞法分析器
        
        Args:
            source: 源代碼
            file_name: 文件名 (用於錯誤報告)
        """
        self.source = source
        self.file_name = file_name
        self.tokens = []
        self.errors = []
        
        # 掃描狀態
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
    
    def tokenize(self) -> List[Token]:
        """
        將源代碼轉換為詞法單元序列
        
        Returns:
            詞法單元列表
        """
        # 重置掃描狀態
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        self.errors = []
        
        # 掃描所有詞法單元
        while not self.is_at_end():
            self.start = self.current
            self.scan_token()
        
        # 添加 EOF 詞法單元
        self.tokens.append(Token(
            TokenType.EOF, "", None, self.line, self.column
        ))
        
        return self.tokens
    
    def scan_token(self):
        """掃描下一個詞法單元"""
        c = self.advance()
        
        # 空白字符
        if c in " \r\t":
            # 忽略空白
            pass
        
        # 換行
        elif c == "\n":
            self.line += 1
            self.column = 1
        
        # 分隔符
        elif c == "(":
            self.add_token(TokenType.LEFT_PAREN)
        elif c == ")":
            self.add_token(TokenType.RIGHT_PAREN)
        elif c == "{":
            self.add_token(TokenType.LEFT_BRACE)
        elif c == "}":
            self.add_token(TokenType.RIGHT_BRACE)
        elif c == "[":
            self.add_token(TokenType.LEFT_BRACKET)
        elif c == "]":
            self.add_token(TokenType.RIGHT_BRACKET)
        elif c == "," or c == "，":  # 支持中文逗號
            self.add_token(TokenType.COMMA)
        elif c == "." or c == "。":  # 支持中文句號
            if self.match("."):
                self.add_token(TokenType.DOT_DOT)
            else:
                self.add_token(TokenType.DOT)
        elif c == ":":
            if self.match("="):
                self.add_token(TokenType.COLONEQ)
            else:
                self.add_token(TokenType.COLON)
        elif c == ";" or c == "；":  # 支持中文分號
            self.add_token(TokenType.SEMICOLON)
        
        # 運算符
        elif c == "+":
            if self.match("="):
                self.add_token(TokenType.PLUS_EQUAL)
            else:
                self.add_token(TokenType.PLUS)
        elif c == "-":
            if self.match("="):
                self.add_token(TokenType.MINUS_EQUAL)
            elif self.match(">"):
                self.add_token(TokenType.ARROW)
            else:
                self.add_token(TokenType.MINUS)
        elif c == "*":
            if self.match("="):
                self.add_token(TokenType.STAR_EQUAL)
            else:
                self.add_token(TokenType.STAR)
        elif c == "/":
            if self.match("="):
                self.add_token(TokenType.SLASH_EQUAL)
            elif self.match("/"):
                # 單行註釋
                while self.peek() != "\n" and not self.is_at_end():
                    self.advance()
            elif self.match("*"):
                # 多行註釋
                self.scan_multiline_comment()
            else:
                self.add_token(TokenType.SLASH)
        elif c == "%":
            if self.match("="):
                self.add_token(TokenType.PERCENT_EQUAL)
            else:
                self.add_token(TokenType.PERCENT)
        
        # 位運算符
        elif c == "&":
            if self.match("&"):
                self.add_token(TokenType.LOGICAL_AND)
            elif self.match("="):
                self.add_token(TokenType.AMPERSAND_EQUAL)
            else:
                self.add_token(TokenType.AMPERSAND)
        elif c == "|":
            if self.match("|"):
                self.add_token(TokenType.LOGICAL_OR)
            elif self.match("="):
                self.add_token(TokenType.PIPE_EQUAL)
            else:
                self.add_token(TokenType.PIPE)
        elif c == "^":
            if self.match("="):
                self.add_token(TokenType.CARET_EQUAL)
            else:
                self.add_token(TokenType.CARET)
        elif c == "~":
            self.add_token(TokenType.TILDE)
        
        # 比較運算符
        elif c == "=":
            if self.match("="):
                self.add_token(TokenType.EQUAL_EQUAL)
            else:
                self.add_token(TokenType.EQUAL)
        elif c == "!" or c == "！":  # 支持中文驚嘆號
            if self.match("="):
                self.add_token(TokenType.BANG_EQUAL)
            else:
                self.add_token(TokenType.BANG)
        elif c == "<":
            if self.match("="):
                self.add_token(TokenType.LESS_EQUAL)
            elif self.match("<"):
                if self.match("="):
                    self.add_token(TokenType.LEFT_SHIFT_EQUAL)
                else:
                    self.add_token(TokenType.LEFT_SHIFT)
            else:
                self.add_token(TokenType.LESS)
        elif c == ">":
            if self.match("="):
                self.add_token(TokenType.GREATER_EQUAL)
            elif self.match(">"):
                if self.match("="):
                    self.add_token(TokenType.RIGHT_SHIFT_EQUAL)
                else:
                    self.add_token(TokenType.RIGHT_SHIFT)
            else:
                self.add_token(TokenType.GREATER)
        
        # 其他特殊字符
        elif c == "？":  # 中文問號
            self.add_token(TokenType.QUESTION)
        elif c == "$":  # $ 符號 (在非模板字符串中)
            self.add_token(TokenType.DOLLAR)
        elif c == "\\":  # 處理轉義字符
            self.add_token(TokenType.BACKSLASH)
        
        # 字符串字面量
        elif c == '"' or c == "'" or c == "`":  # 支持反引號
            self.scan_string()
        
        # 數字
        elif c.isdigit():
            self.scan_number()
        
        # 標識符和關鍵字
        elif self.is_alphanumeric(c):
            self.scan_identifier()
        
        # 未知字符
        else:
            self.add_error(f"未知字符: '{c}'")
    
    def scan_multiline_comment(self):
        """掃描多行註釋"""
        nesting = 1
        
        while nesting > 0 and not self.is_at_end():
            if self.peek() == "/" and self.peek_next() == "*":
                self.advance()
                self.advance()
                nesting += 1
            elif self.peek() == "*" and self.peek_next() == "/":
                self.advance()
                self.advance()
                nesting -= 1
            elif self.peek() == "\n":
                self.advance()
                self.line += 1
                self.column = 1
            else:
                self.advance()
        
        if nesting > 0:
            self.add_error("未閉合的多行註釋")
    
    def scan_string(self):
        """掃描字符串字面量"""
        # 儲存起始引號類型
        quote_type = self.source[self.start]
        is_template = (quote_type == '`')
        
        # 掃描直到字符串結束或檔案結束
        while (self.peek() != quote_type) and not self.is_at_end():
            if self.peek() == "\n":
                self.line += 1
                self.column = 1
            # 字符串中的轉義序列處理
            elif self.peek() == "\\" and self.peek_next() in ["\\", "\"", "'", "`", "n", "t", "r", "$"]:
                self.advance()  # 消耗轉義符
                self.advance()  # 消耗被轉義的字符
            # 模板字符串中的 ${} 插值
            elif is_template and self.peek() == "$" and self.peek_next() == "{":
                # 這裡不需要特殊處理，將整個字符串視為整體，後續的解析器會解析插值
                self.advance()  # $
                self.advance()  # {
            else:
                self.advance()
        
        # 未閉合的字符串
        if self.is_at_end():
            self.add_error("未閉合的字符串")
            return
        
        # 消耗結束的引號
        self.advance()
        
        # 獲取字符串的文本表示，不包括引號
        value = self.source[self.start + 1:self.current - 1]
        
        # 添加字串詞法單元 (不進行轉義處理，原始字串交給解析器處理)
        if is_template:
            self.add_token(TokenType.TEMPLATE_STRING, value)
        else:
            self.add_token(TokenType.STRING_LITERAL, value)
    
    def scan_char(self):
        """掃描字符字面量"""
        # 掃描直到字符結束或檔案結束
        if self.is_at_end():
            self.add_error("未閉合的字符字面量")
            return
        
        # 處理轉義序列
        if self.peek() == "\\":
            self.advance()
            
            if self.is_at_end():
                self.add_error("未閉合的字符字面量")
                return
            
            # 確保有結束的單引號
            c = self.advance()
            if self.peek() != "'" or self.is_at_end():
                self.add_error("未閉合的字符字面量")
                return
            
            # 消耗結束的單引號
            self.advance()
            
            # 處理轉義字符
            if c == "n":
                c = "\n"
            elif c == "t":
                c = "\t"
            elif c == "r":
                c = "\r"
            elif c == "0":
                c = "\0"
            elif c == "'":
                c = "'"
            elif c == '"':
                c = '"'
            elif c == "\\":
                c = "\\"
            
            self.add_token(TokenType.CHAR_LITERAL, c)
        else:
            # 普通字符
            c = self.advance()
            
            # 確保有結束的單引號
            if self.peek() != "'" or self.is_at_end():
                self.add_error("未閉合的字符字面量")
                return
            
            # 消耗結束的單引號
            self.advance()
            
            self.add_token(TokenType.CHAR_LITERAL, c)
    
    def scan_number(self):
        """掃描數字字面量"""
        # 掃描整數部分
        while self.peek().isdigit() or self.peek() == '_':
            self.advance()
        
        # 查看是否有小數部分
        has_decimal = False
        if self.peek() == "." and (self.peek_next().isdigit() or self.peek_next() == '_'):
            has_decimal = True
            
            # 消耗小數點
            self.advance()
            
            # 掃描小數部分
            while self.peek().isdigit() or self.peek() == '_':
                self.advance()
        
        # 處理可能的科學計數法
        if (self.peek() == "e" or self.peek() == "E"):
            next_char = self.peek_next()
            if next_char.isdigit() or next_char == "+" or next_char == "-" or next_char == '_':
                has_decimal = True
                
                # 消耗 'e' 或 'E'
                self.advance()
                
                # 消耗可能的符號
                if self.peek() == "+" or self.peek() == "-":
                    self.advance()
                
                # 必須至少有一位數字
                if not (self.peek().isdigit() or self.peek() == '_'):
                    self.add_error("科學計數法中指數部分缺少數字")
                    return
                
                # 掃描指數部分
                while self.peek().isdigit() or self.peek() == '_':
                    self.advance()
        
        # 獲取數字字面量的文本表示
        text = self.source[self.start:self.current]
        
        # 移除所有下劃線
        text_without_underscores = text.replace('_', '')
        
        # 轉換為數值
        if has_decimal:
            value = float(text_without_underscores)
            self.add_token(TokenType.FLOAT_LITERAL, value)
        else:
            value = int(text_without_underscores)
            self.add_token(TokenType.NUMBER, value)
    
    def scan_identifier(self):
        """掃描標識符"""
        # 掃描標識符的剩餘部分
        while self.is_alphanumeric(self.peek()):
            self.advance()
        
        # 獲取標識符文本
        text = self.source[self.start:self.current]
        
        # 檢查是否為關鍵字
        type = self.KEYWORDS.get(text, TokenType.IDENTIFIER)
        
        # 添加標識符或關鍵字詞法單元
        self.add_token(type)
    
    def unescape_string(self, s: str) -> str:
        """
        處理字符串中的轉義序列
        
        Args:
            s: 原始字符串
            
        Returns:
            處理後的字符串
        """
        # 處理基本轉義序列
        result = ""
        i = 0
        
        while i < len(s):
            if s[i] == "\\" and i + 1 < len(s):
                c = s[i + 1]
                
                if c == "n":
                    result += "\n"
                elif c == "t":
                    result += "\t"
                elif c == "r":
                    result += "\r"
                elif c == "0":
                    result += "\0"
                elif c == '"':
                    result += '"'
                elif c == "\\":
                    result += "\\"
                else:
                    # 未知的轉義序列，保留原樣
                    result += "\\" + c
                
                i += 2
            else:
                result += s[i]
                i += 1
        
        return result
    
    def add_token(self, type: TokenType, literal: Any = None):
        """
        添加詞法單元
        
        Args:
            type: 詞法單元類型
            literal: 詞法單元字面值 (可選)
        """
        text = self.source[self.start:self.current]
        self.tokens.append(Token(type, text, literal, self.line, self.column - (self.current - self.start)))
    
    def add_error(self, message: str):
        """
        添加錯誤信息
        
        Args:
            message: 錯誤信息
        """
        error = f"{self.file_name}:{self.line}:{self.column}: {message}"
        self.errors.append(error)
    
    def advance(self) -> str:
        """
        前進到下一個字符
        
        Returns:
            當前字符
        """
        c = self.source[self.current]
        self.current += 1
        self.column += 1
        return c
    
    def match(self, expected: str) -> bool:
        """
        嘗試匹配當前字符
        
        Args:
            expected: 期望的字符
            
        Returns:
            是否匹配
        """
        if self.is_at_end() or self.source[self.current] != expected:
            return False
        
        self.current += 1
        self.column += 1
        return True
    
    def peek(self) -> str:
        """
        預覽當前字符
        
        Returns:
            當前字符，如果已經到達末尾則返回 '\0'
        """
        if self.is_at_end():
            return "\0"
        
        return self.source[self.current]
    
    def peek_next(self) -> str:
        """
        預覽下一個字符
        
        Returns:
            下一個字符，如果已經到達末尾則返回 '\0'
        """
        if self.current + 1 >= len(self.source):
            return "\0"
        
        return self.source[self.current + 1]
    
    def is_at_end(self) -> bool:
        """
        檢查是否到達源代碼末尾
        
        Returns:
            是否到達末尾
        """
        return self.current >= len(self.source)
    
    def is_alphanumeric(self, c: str) -> bool:
        """
        檢查字符是否為字母、數字、下劃線或合法的Unicode字符
        
        Args:
            c: 字符
            
        Returns:
            是否為合法字符
        """
        # 支持中文和其他非ASCII字符（Unicode範圍）
        if len(c) > 0 and (ord(c) > 127 or c.isalpha() or c.isdigit() or c == "_"):
            return True
        return False

    def tokenize_string(self, quote_char):
        # 現有字串處理邏輯...
        
        # 添加對反引號字串插值的支援
        if quote_char == '`':
            # 處理 ${...} 插值語法
            # 實現字串插值邏輯
            pass 