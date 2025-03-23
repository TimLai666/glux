"""
Glux 語言抽象語法樹節點定義
"""

from typing import List, Any, Optional, Dict, Union


class ASTNode:
    """抽象語法樹節點基類"""
    
    def __init__(self):
        """初始化節點"""
        pass
    
    def accept(self, visitor):
        """接受訪問者模式"""
        pass


class Expression(ASTNode):
    """表達式基類"""
    
    def __init__(self):
        super().__init__()
        self.type = None  # 語義分析階段確定類型


class VarDeclaration(ASTNode):
    """變數聲明節點"""

    def __init__(self, name, var_type, initializer):
        super().__init__()
        self.name = name            # 變數名稱
        self.var_type = var_type    # 變數類型（可能為None）
        self.initializer = initializer  # 初始化表達式

    def accept(self, visitor):
        return visitor.visit_var_declaration(self)

    def __repr__(self):
        return f"VarDeclaration({self.name}, {self.var_type}, {self.initializer})"


class ConstDeclaration(ASTNode):
    """常數聲明節點"""

    def __init__(self, name, const_type, initializer):
        super().__init__()
        self.name = name              # 常數名稱
        self.const_type = const_type  # 常數類型（可能為None）
        self.initializer = initializer  # 初始化表達式

    def accept(self, visitor):
        return visitor.visit_const_declaration(self)

    def __repr__(self):
        return f"ConstDeclaration({self.name}, {self.const_type}, {self.initializer})"


class IfStatement(ASTNode):
    """IF語句節點"""

    def __init__(self, condition, then_branch, else_branch=None):
        super().__init__()
        self.condition = condition      # 條件表達式
        self.then_branch = then_branch  # Then分支（語句列表）
        self.else_branch = else_branch  # Else分支（語句列表，可能為None）

    def accept(self, visitor):
        return visitor.visit_if_statement(self)

    def __repr__(self):
        return f"IfStatement({self.condition}, then={self.then_branch}, else={self.else_branch})"


class WhileStatement(ASTNode):
    """WHILE循環節點"""

    def __init__(self, condition, body):
        super().__init__()
        self.condition = condition  # 循環條件表達式
        self.body = body            # 循環體（語句列表）

    def accept(self, visitor):
        return visitor.visit_while_statement(self)

    def __repr__(self):
        return f"WhileStatement({self.condition}, body={self.body})"


class ForStatement(ASTNode):
    """FOR循環節點"""

    def __init__(self, variable, iterable, body):
        super().__init__()
        self.variable = variable    # 迭代變數（可能是單個變數或key,value對）
        self.iterable = iterable    # 可迭代表達式
        self.body = body            # 循環體（語句列表）

    def accept(self, visitor):
        return visitor.visit_for_statement(self)

    def __repr__(self):
        return f"ForStatement({self.variable}, in={self.iterable}, body={self.body})"


class BlockStatement(ASTNode):
    """代碼塊節點"""

    def __init__(self, statements):
        super().__init__()
        self.statements = statements  # 語句列表

    def accept(self, visitor):
        return visitor.visit_block_statement(self)

    def __repr__(self):
        return f"BlockStatement({self.statements})"


class BinaryExpression(Expression):
    """二元表達式節點"""
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right
        self.type = None  # 語義分析階段確定
    
    def accept(self, visitor):
        return visitor.visit_binary_expr(self)
    
    def __repr__(self):
        op_str = ""
        if hasattr(self.operator, 'lexeme'):
            op_str = self.operator.lexeme
        elif hasattr(self.operator, 'type'):
            op_str = str(self.operator.type)
        else:
            op_str = str(self.operator)
        
        return f"BinaryExpr({self.left} {op_str} {self.right})"


class UnaryExpression(ASTNode):
    """一元運算表達式節點"""

    def __init__(self, operator, right):
        super().__init__()
        self.operator = operator  # 運算符
        self.right = right        # 操作數

    def accept(self, visitor):
        return visitor.visit_unary_expression(self)

    def __repr__(self):
        return f"UnaryExpression({self.operator}, {self.right})"


class TernaryExpression(ASTNode):
    """三元運算表達式節點"""

    def __init__(self, condition, true_expr, false_expr):
        super().__init__()
        self.condition = condition    # 條件表達式
        self.true_expr = true_expr    # 條件為真時的表達式
        self.false_expr = false_expr  # 條件為假時的表達式

    def accept(self, visitor):
        return visitor.visit_ternary_expression(self)

    def __repr__(self):
        return f"TernaryExpression({self.condition}, {self.true_expr}, {self.false_expr})"


class AssignmentExpression(ASTNode):
    """賦值表達式節點"""

    def __init__(self, target, operator, value):
        super().__init__()
        self.target = target      # 賦值目標（通常是變數或屬性訪問）
        self.operator = operator  # 賦值運算符（=, +=, -=, *=, /=, %=）
        self.value = value        # 賦值的值

    def accept(self, visitor):
        return visitor.visit_assignment_expression(self)

    def __repr__(self):
        return f"AssignmentExpression({self.target}, {self.operator}, {self.value})"


class LogicalExpression(ASTNode):
    """邏輯運算表達式節點"""

    def __init__(self, left, operator, right):
        super().__init__()
        self.left = left          # 左操作數
        self.operator = operator  # 邏輯運算符（and, or）
        self.right = right        # 右操作數

    def accept(self, visitor):
        return visitor.visit_logical_expression(self)

    def __repr__(self):
        return f"LogicalExpression({self.left}, {self.operator}, {self.right})"


class ChainedComparisonExpression(ASTNode):
    """連續比較表達式節點，如 0 < x < 8"""

    def __init__(self, operands, operators):
        super().__init__()
        self.operands = operands    # 操作數列表
        self.operators = operators  # 運算符列表

    def accept(self, visitor):
        return visitor.visit_chained_comparison_expression(self)

    def __repr__(self):
        return f"ChainedComparisonExpression({self.operands}, {self.operators})"


class Parameter(ASTNode):
    """函數參數節點"""

    def __init__(self, name, param_type=None, default_value=None):
        super().__init__()
        self.name = name                    # 參數名稱
        self.param_type = param_type        # 參數類型（可能為 None）
        self.default_value = default_value  # 默認值（可能為 None）

    def accept(self, visitor):
        return visitor.visit_parameter(self)

    def __repr__(self):
        return f"Parameter({self.name}, {self.param_type}, {self.default_value})"


class FunctionDeclaration(ASTNode):
    """函數聲明節點"""

    def __init__(self, name, params, return_type, body):
        super().__init__()
        self.name = name                # 函數名稱
        self.params = params            # 參數列表 (Parameter 節點列表)
        self.return_type = return_type  # 返回類型（可能為 None）
        self.body = body                # 函數體（語句列表）

    def accept(self, visitor):
        return visitor.visit_function_declaration(self)

    def __repr__(self):
        return f"FunctionDeclaration({self.name}, {self.params}, {self.return_type})"


class FunctionExpression(ASTNode):
    """匿名函數表達式節點"""

    def __init__(self, params, return_type, body):
        super().__init__()
        self.params = params            # 參數列表 (Parameter 節點列表)
        self.return_type = return_type  # 返回類型（可能為 None）
        self.body = body                # 函數體（語句列表）

    def accept(self, visitor):
        return visitor.visit_function_expression(self)

    def __repr__(self):
        return f"FunctionExpression({self.params}, {self.return_type})"


class ReturnStatement(ASTNode):
    """返回語句節點"""

    def __init__(self, value=None):
        super().__init__()
        self.value = value  # 返回值（可能為 None）

    def accept(self, visitor):
        return visitor.visit_return_statement(self)

    def __repr__(self):
        return f"ReturnStatement({self.value})"


class ArgumentList(ASTNode):
    """函數調用參數列表節點，支持命名參數"""

    def __init__(self, positional_args, named_args=None):
        super().__init__()
        self.positional_args = positional_args  # 位置參數列表
        self.named_args = named_args or {}      # 命名參數字典 {name: value}

    def accept(self, visitor):
        return visitor.visit_argument_list(self)

    def __repr__(self):
        return f"ArgumentList({self.positional_args}, {self.named_args})"


class SpawnExpression(ASTNode):
    """併發任務啟動表達式節點"""

    def __init__(self, call_expr):
        super().__init__()
        self.call_expr = call_expr  # 函數調用表達式

    def accept(self, visitor):
        return visitor.visit_spawn_expression(self)

    def __repr__(self):
        return f"SpawnExpression({self.call_expr})"


class AwaitExpression(ASTNode):
    """等待Future完成的表達式節點"""

    def __init__(self, futures):
        super().__init__()
        self.futures = futures  # 等待的Future列表

    def accept(self, visitor):
        return visitor.visit_await_expression(self)

    def __repr__(self):
        return f"AwaitExpression({self.futures})" 