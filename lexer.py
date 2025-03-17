import re

# 定義 Token 類型
TOKEN_SPEC = [
    ("NUMBER",   r'\d+(\.\d*)?'),  # 正常數字
    ("NEG_NUMBER", r'(?<![\w\)])-?\d+(\.\d*)?'),  # **負數 (需排除變數/右括號)**
    ("AND",      r'&&|and'),
    ("OR",       r'\|\||or'),
    ("NOT",      r'!|not'),
    ("IDENT",    r'[a-zA-Z_]\w*'),
    ("ASSIGN",   r':='),
    ("PLUS",     r'\+'),
    ("MINUS",    r'-'),  # **單獨 `-` 處理 `a - b`**
    ("MUL",      r'\*'),
    ("DIV",      r'/'),
    ("LPAREN",   r'\('),
    ("RPAREN",   r'\)'),
    ("COMMA",    r','),
    ("NEWLINE",  r'\n|;'),
    ("SKIP",     r'[ \t]+'),
]

# 建立正則表達式
TOKEN_REGEX = '|'.join(f'(?P<{name}>{regex})' for name, regex in TOKEN_SPEC)
token_re = re.compile(TOKEN_REGEX)

def lexer(code):
    tokens = []
    prev_token = None
    for match in re.finditer(token_re, code):
        kind = match.lastgroup
        value = match.group()

        if kind == "SKIP":
            continue

        elif kind == "NEWLINE":
            tokens.append(("NEWLINE", "\n"))
            continue

        elif kind == "NEG_NUMBER":  # **負數處理**
            if prev_token and prev_token[0] in ("IDENT", "NUMBER", "RPAREN"):
                kind = "MINUS"  # `a-3` 解析為 `a - 3`
            else:
                kind = "NUMBER"  # `-3` 解析為 `NUMBER(-3)`

        tokens.append((kind, value))
        prev_token = (kind, value)

    return tokens
