class ASTNode:
    pass

class Number(ASTNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"Number({self.value})"

class Variable(ASTNode):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"Variable({self.name})"

class Assign(ASTNode):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return f"Assign({self.name} := {self.value})"

class BinaryOp(ASTNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def __repr__(self):
        return f"({self.left} {self.op} {self.right})"

class UnaryOp(ASTNode):  # 針對 `not` 運算
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand

    def __repr__(self):
        return f"({self.op} {self.operand})"

class FunctionCall(ASTNode):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __repr__(self):
        return f"{self.name}({', '.join(map(str, self.args))})"


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def eat(self, token_type):
        if self.pos < len(self.tokens) and self.tokens[self.pos][0] == token_type:
            self.pos += 1
        else:
            raise SyntaxError(f"Expected {token_type}, got {self.tokens[self.pos]}")

    def parse_expr(self):
        """解析 `+`, `-`, `&&`, `||` 運算"""
        left = self.parse_term()

        while self.pos < len(self.tokens) and self.tokens[self.pos][0] in ("PLUS", "MINUS", "AND", "OR"):
            op = self.tokens[self.pos][1]
            self.pos += 1
            right = self.parse_term()
            left = BinaryOp(left, op, right)

        return left

    
    def parse_term(self):
        """解析 `*`, `/` 以及 `!` 運算"""
        left = self.parse_factor()

        while self.pos < len(self.tokens) and self.tokens[self.pos][0] in ("MUL", "DIV"):
            op = self.tokens[self.pos][1]
            self.pos += 1
            right = self.parse_factor()
            left = BinaryOp(left, op, right)

        return left

    def parse_factor(self):
        """解析數字、變數，並支援 `!` 和 `-`"""
        token = self.tokens[self.pos]

        if token[0] == "NUMBER":
            self.pos += 1
            return Number(token[1])

        elif token[0] == "IDENT":
            self.pos += 1
            return Variable(token[1])

        elif token[0] == "NOT":  # `!` 運算
            op = token[1]
            self.pos += 1
            operand = self.parse_factor()
            return UnaryOp(op, operand)

        elif token[0] == "MINUS":  # **負數 `-10` 轉換為 `UnaryOp("-", Number(10))`**
            op = token[1]
            self.pos += 1
            operand = self.parse_factor()
            return UnaryOp(op, operand)

        else:
            raise SyntaxError(f"Unexpected token {token}")

    def parse_function_call(self, name):
        """解析函式呼叫，例如 `print(a, b, c)`"""
        self.eat("LPAREN")  # 跳過 `(`
        args = []
        while self.tokens[self.pos][0] != "RPAREN":
            args.append(self.parse_expr())  # 解析變數或數字
            if self.tokens[self.pos][0] == "COMMA":
                self.eat("COMMA")  # **跳過逗號**
            elif self.tokens[self.pos][0] == "RPAREN":
                break
            else:
                raise SyntaxError(f"Unexpected token {self.tokens[self.pos]} in function call")
        self.eat("RPAREN")  # 跳過 `)`
        return FunctionCall(name, args)


    def parse(self):
        ast = []
        while self.pos < len(self.tokens):
            token_type, token_value = self.tokens[self.pos]

            if token_type == "IDENT":
                name = token_value
                self.eat("IDENT")

                if self.tokens[self.pos][0] == "LPAREN":
                    ast.append(self.parse_function_call(name))
                else:
                    self.eat("ASSIGN")  # 這裡報錯，因為 `NEWLINE` 可能未被處理
                    value = self.parse_expr()
                    ast.append(Assign(name, value))

            elif token_type == "NEWLINE":
                self.eat("NEWLINE")  # **正確跳過換行**
                continue

            else:
                raise SyntaxError(f"Unexpected token {self.tokens[self.pos]}")

        return ast
