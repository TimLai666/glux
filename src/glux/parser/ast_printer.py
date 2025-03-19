"""
AST打印器模組
用於在調試時美觀地打印抽象語法樹結構
"""

from typing import Any, List, Dict, Optional
from . import ast_nodes

class ASTPrinter:
    """抽象語法樹打印器"""
    
    def __init__(self):
        """初始化AST打印器"""
        self.indent = 0
        
    def print(self, node, indent: int = 0):
        """打印AST節點"""
        self.indent = indent
        if isinstance(node, ast_nodes.Program):
            print("Program")
            self.indent += 2
            for stmt in node.statements:
                self._print_indent()
                self.print(stmt, self.indent)
        elif hasattr(node, 'expression') and hasattr(node, 'token'):  # 檢查是否是Statement
            self._print_statement(node)
        elif hasattr(node, 'value') or hasattr(node, 'name') or hasattr(node, 'operator'):  # 檢查是否是Expression
            self._print_expression(node)
        else:
            self._print_indent()
            print(f"Unknown node type: {type(node).__name__}")
        
    def _print_indent(self):
        """打印縮進"""
        print(" " * self.indent, end="")
        
    def _print_statement(self, stmt):
        """打印語句節點"""
        from . import ast_nodes
        
        if isinstance(stmt, ast_nodes.ExpressionStatement):
            print("ExpressionStatement")
            self.indent += 2
            self._print_indent()
            self.print(stmt.expression, self.indent)
            self.indent -= 2
        elif isinstance(stmt, ast_nodes.VarDeclaration):
            print(f"VarDeclaration: {stmt.name}")
            if stmt.value:
                self.indent += 2
                self._print_indent()
                print("Value:")
                self.indent += 2
                self._print_indent()
                self.print(stmt.value, self.indent)
                self.indent -= 4
        elif isinstance(stmt, ast_nodes.ConstDeclaration):
            print(f"ConstDeclaration: {stmt.name}")
            if stmt.value:
                self.indent += 2
                self._print_indent()
                print("Value:")
                self.indent += 2
                self._print_indent()
                self.print(stmt.value, self.indent)
                self.indent -= 4
        elif isinstance(stmt, ast_nodes.IfStatement):
            print("IfStatement")
            self.indent += 2
            self._print_indent()
            print("Condition:")
            self.indent += 2
            self._print_indent()
            self.print(stmt.condition, self.indent)
            self.indent -= 2
            self._print_indent()
            print("Then:")
            self.indent += 2
            if isinstance(stmt.body, list):
                for body_stmt in stmt.body:
                    self._print_indent()
                    self.print(body_stmt, self.indent)
            else:
                self._print_indent()
                self.print(stmt.body, self.indent)
            self.indent -= 2
            if stmt.else_body:
                self._print_indent()
                print("Else:")
                self.indent += 2
                if isinstance(stmt.else_body, list):
                    for else_stmt in stmt.else_body:
                        self._print_indent()
                        self.print(else_stmt, self.indent)
                else:
                    self._print_indent()
                    self.print(stmt.else_body, self.indent)
                self.indent -= 2
            self.indent -= 2
        elif isinstance(stmt, ast_nodes.BlockStatement):
            print("BlockStatement")
            self.indent += 2
            for block_stmt in stmt.statements:
                self._print_indent()
                self.print(block_stmt, self.indent)
            self.indent -= 2
        else:
            print(f"Statement({type(stmt).__name__})")
            
    def _print_expression(self, expr):
        """打印表達式節點"""
        from . import ast_nodes
        
        if isinstance(expr, ast_nodes.Number):
            print(f"Number: {expr.value}")
        elif isinstance(expr, ast_nodes.StringLiteral):
            print(f"String: '{expr.value}'")
        elif isinstance(expr, ast_nodes.Boolean):
            print(f"Boolean: {expr.value}")
        elif isinstance(expr, ast_nodes.Variable):
            print(f"Variable: {expr.name}")
        elif isinstance(expr, ast_nodes.BinaryExpr):
            print(f"BinaryExpr: {expr.operator}")
            self.indent += 2
            self._print_indent()
            print("Left:")
            self.indent += 2
            self._print_indent()
            self.print(expr.left, self.indent)
            self.indent -= 2
            self._print_indent()
            print("Right:")
            self.indent += 2
            self._print_indent()
            self.print(expr.right, self.indent)
            self.indent -= 4
        elif isinstance(expr, ast_nodes.CallExpression):
            print("CallExpression")
            self.indent += 2
            self._print_indent()
            print("Callee:")
            self.indent += 2
            self._print_indent()
            self.print(expr.callee, self.indent)
            self.indent -= 2
            self._print_indent()
            print("Arguments:")
            self.indent += 2
            for arg in expr.arguments:
                self._print_indent()
                self.print(arg, self.indent)
            self.indent -= 4
        elif isinstance(expr, ast_nodes.SpawnExpression):
            print("SpawnExpression")
            self.indent += 2
            self._print_indent()
            print("Function:")
            self.indent += 2
            self._print_indent()
            self.print(expr.function_call, self.indent)
            self.indent -= 4
        elif isinstance(expr, ast_nodes.AwaitExpression):
            print("AwaitExpression")
            self.indent += 2
            for await_expr in expr.expressions:
                self._print_indent()
                self.print(await_expr, self.indent)
            self.indent -= 2
        elif isinstance(expr, ast_nodes.GetExpression):
            print("GetExpression")
            self.indent += 2
            self._print_indent()
            print("Object:")
            self.indent += 2
            self._print_indent()
            self.print(expr.object, self.indent)
            self.indent -= 2
            self._print_indent()
            print(f"Property: {expr.property}")
            self.indent -= 2
        elif isinstance(expr, ast_nodes.ConditionalExpression):
            print("ConditionalExpression")
            self.indent += 2
            self._print_indent()
            print("Condition:")
            self.indent += 2
            self._print_indent()
            self.print(expr.condition, self.indent)
            self.indent -= 2
            self._print_indent()
            print("Then:")
            self.indent += 2
            self._print_indent()
            self.print(expr.then_branch, self.indent)
            self.indent -= 2
            self._print_indent()
            print("Else:")
            self.indent += 2
            self._print_indent()
            self.print(expr.else_branch, self.indent)
            self.indent -= 4
        else:
            print(f"Expression({type(expr).__name__})") 