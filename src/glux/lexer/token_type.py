from enum import Enum, auto

class TokenType(Enum):
    # 單字元符號
    LEFT_PAREN = '('
    RIGHT_PAREN = ')'
    LEFT_BRACE = '{'
    RIGHT_BRACE = '}'
    LEFT_BRACKET = '['
    RIGHT_BRACKET = ']'
    COMMA = ','
    DOT = '.'
    MINUS = '-'
    PLUS = '+'
    SEMICOLON = ';'
    SLASH = '/'
    STAR = '*'
    PERCENT = '%'
    
    # 一或二字元符號
    BANG = '!'
    BANG_EQUAL = '!='
    EQUAL = '='
    EQUAL_EQUAL = '=='
    GREATER = '>'
    GREATER_EQUAL = '>='
    LESS = '<'
    LESS_EQUAL = '<='
    
    # 賦值運算符
    PLUS_EQUAL = '+='
    MINUS_EQUAL = '-='
    STAR_EQUAL = '*='
    SLASH_EQUAL = '/='
    PERCENT_EQUAL = '%='
    
    # 邏輯運算符
    LOGICAL_AND = '&&'
    LOGICAL_OR = '||'
    
    # 為兼容性添加的屬性
    AND_AND = LOGICAL_AND  # &&
    OR_OR = LOGICAL_OR     # ||
    
    # 位運算符
    AMPERSAND = '&'
    PIPE = '|'
    CARET = '^'
    TILDE = '~'
    LEFT_SHIFT = '<<'
    RIGHT_SHIFT = '>>'
    
    # 賦值聲明
    WALRUS = ':='
    COLONEQ = ':='
    
    # 三元運算符
    QUESTION = '?'
    COLON = ':'
    
    # 其他符號
    ARROW = '->'
    DOT_DOT = '..'
    
    # 字面量
    IDENTIFIER = 'IDENTIFIER'
    STRING = 'STRING'
    TEMPLATE_STRING = 'TEMPLATE_STRING'
    NUMBER = 'NUMBER'
    FLOAT_LITERAL = 'FLOAT_LITERAL'
    CHAR_LITERAL = 'CHAR_LITERAL'
    STRING_LITERAL = 'STRING_LITERAL'
    
    # 關鍵字
    AND = 'AND'
    AWAIT = 'AWAIT'
    CONST = 'CONST'
    ELSE = 'ELSE'
    ENUM = 'ENUM'
    ERROR = 'ERROR'
    EXTENDS = 'EXTENDS'
    FALSE = 'FALSE'
    FN = 'FN'
    FOR = 'FOR'
    FUNCTION = 'FUNCTION'
    FROM = 'FROM'
    IF = 'IF'
    IMPORT = 'IMPORT'
    IN = 'IN'
    INTERFACE = 'INTERFACE'
    IS_ERROR = 'IS_ERROR'
    LEN = 'LEN'
    MAIN = 'MAIN'
    NEW = 'NEW'
    NOT = 'NOT'
    NULL = 'NULL'
    OR = 'OR'
    PRINT = 'PRINT'
    PRINTLN = 'PRINTLN'
    RETURN = 'RETURN'
    SLEEP = 'SLEEP'
    SPAWN = 'SPAWN'
    STRUCT = 'STRUCT'
    TRUE = 'TRUE'
    UNSAFE = 'UNSAFE'
    WHILE = 'WHILE'
    OVERRIDE = 'OVERRIDE'
    
    # 特殊標記
    EOF = 'EOF' 