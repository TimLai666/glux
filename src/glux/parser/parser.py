"""
Glux 語言解析器
將詞法單元轉換為抽象語法樹
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from ..lexer.lexer import Token
from ..lexer.token_type import TokenType
from . import ast_nodes
from .string_interpolation import StringInterpolationProcessor
from src.glux.ast.ast_nodes import BinaryExpression, Expression


class Parser:
    """
    Glux 語言解析器類
    將詞法單元序列解析為抽象語法樹
    """
    
    def __init__(self, tokens: List[Token]):
        """
        初始化解析器
        
        Args:
            tokens: 詞法單元列表
        """
        self.tokens = tokens
        self.current = 0
        self.errors = []
        self.string_processor = StringInterpolationProcessor(self)
    
    def parse(self) -> ast_nodes.Module:
        """
        解析程序
        
        Returns:
            模塊 AST 節點
        """
        try:
            print("開始解析...")
            statements = []
            
            while not self.is_at_end():
                statements.append(self.declaration())
            
            return ast_nodes.Module(statements)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.errors.append(str(e))
            return ast_nodes.Module([])
    
    def declaration(self) -> ast_nodes.Declaration:
        """
        解析聲明語句
        
        Returns:
            聲明節點
        """
        try:
            if self.match(TokenType.CONST):
                return self.const_declaration()
            elif self.match(TokenType.FN):
                return self.function_declaration()
            elif self.match(TokenType.STRUCT):
                return self.struct_declaration()
            elif self.match(TokenType.ENUM):
                return self.enum_declaration()
            elif self.match(TokenType.IMPORT, TokenType.FROM):
                return self.import_declaration()
            elif self.match(TokenType.MAIN):
                return self.main_block()
            elif self.check(TokenType.IDENTIFIER) and self.peek_next().type == TokenType.WALRUS:
                return self.var_declaration()
                
            # 變數聲明或表達式語句
            return self.statement()
            
        except Exception as e:
            self.error(str(e))
            self.synchronize()
            return ast_nodes.ExpressionStatement(ast_nodes.ErrorExpression("語法錯誤"))
    
    def function_declaration(self) -> ast_nodes.FunctionDeclaration:
        """
        解析函數聲明
        
        Returns:
            函數聲明 AST 節點
        """
        name = self.consume(TokenType.IDENTIFIER, "期望函數名稱").lexeme
        
        # 解析參數列表
        self.consume(TokenType.LEFT_PAREN, "期望 '(' 在函數參數列表前")
        parameters = []
        
        if not self.check(TokenType.RIGHT_PAREN):
            parameters.append(self.function_parameter())
            
            while self.match(TokenType.COMMA):
                parameters.append(self.function_parameter())
        
        self.consume(TokenType.RIGHT_PAREN, "期望 ')' 在函數參數列表後")
        
        # 解析返回類型
        return_type = None
        if self.match(TokenType.ARROW):
            return_type = self.type_expression()
        
        # 解析函數體
        body = self.block_statement()
        
        return ast_nodes.FunctionDeclaration(name, parameters, body, return_type)
    
    def function_parameter(self) -> ast_nodes.Parameter:
        """
        解析函數參數
        
        Returns:
            參數 AST 節點
        """
        name = self.consume(TokenType.IDENTIFIER, "期望參數名稱").lexeme
        
        # 可選的類型註解
        param_type = None
        if self.match(TokenType.COLON):
            param_type = self.type_expression()
        
        # 可選的默認值
        default_value = None
        if self.match(TokenType.EQUAL):
            default_value = self.expression()
        
        return ast_nodes.Parameter(name, param_type, default_value)
    
    def struct_declaration(self) -> ast_nodes.StructDeclaration:
        """
        解析結構體聲明
        
        Returns:
            結構體聲明 AST 節點
        """
        name = self.consume(TokenType.IDENTIFIER, "期望結構體名稱").lexeme
        
        # 解析父結構體（繼承）
        parent = None
        if self.match(TokenType.EXTENDS):
            parent = self.consume(TokenType.IDENTIFIER, "期望父結構體名稱").lexeme
        
        # 解析結構體體
        self.consume(TokenType.LEFT_BRACE, "期望 '{' 在結構體體前")
        
        fields = []
        methods = []
        
        while not self.check(TokenType.RIGHT_BRACE) and not self.is_at_end():
            # 結構體成員
            if self.check(TokenType.IDENTIFIER):
                # 解析欄位或方法
                fields.append(self.struct_field())
            elif self.match(TokenType.FN):
                # 解析結構體方法
                methods.append(self.struct_method(name))
            else:
                self.error(f"期望結構體成員或方法，但得到 {self.peek().lexeme}")
                self.advance()  # 跳過無法解析的標記
        
        self.consume(TokenType.RIGHT_BRACE, "期望 '}' 在結構體體後")
        
        return ast_nodes.StructDeclaration(name, fields, methods, parent)
    
    def enum_declaration(self) -> ast_nodes.EnumDeclaration:
        """
        解析枚舉聲明
        
        Returns:
            枚舉聲明 AST 節點
        """
        name = self.consume(TokenType.IDENTIFIER, "期望枚舉名稱").lexeme
        
        self.consume(TokenType.LEFT_BRACE, "期望 '{' 在枚舉定義前")
        variants = []
        
        while not self.check(TokenType.RIGHT_BRACE) and not self.is_at_end():
            variant_name = self.consume(TokenType.IDENTIFIER, "期望枚舉變體名稱").lexeme
            
            # 處理可能的值賦值
            value = None
            if self.match(TokenType.EQUAL):
                value = self.expression()
            
            variants.append(ast_nodes.EnumVariant(variant_name, value))
            
            # 允許尾部逗號
            if self.match(TokenType.COMMA):
                continue
            
            if self.check(TokenType.RIGHT_BRACE):
                break
            
            # 分號是可選的
            self.match(TokenType.SEMICOLON)
        
        self.consume(TokenType.RIGHT_BRACE, "期望 '}' 在枚舉定義之後")
        
        return ast_nodes.EnumDeclaration(name, variants)
    
    def var_declaration(self) -> ast_nodes.VarDeclaration:
        """
        解析變量聲明
        
        Returns:
            變量聲明 AST 節點
        """
        name = self.consume(TokenType.IDENTIFIER, "期望變量名稱").lexeme
        
        # 變量使用 := 進行初始化
        self.consume(TokenType.WALRUS, "期望 ':=' 在變量聲明中")
        initializer = self.expression()
        
        # 可選的分號
        self.match(TokenType.SEMICOLON)
        
        return ast_nodes.VarDeclaration(name, initializer, None)
    
    def const_declaration(self) -> ast_nodes.ConstDeclaration:
        """
        解析常量聲明
        
        Returns:
            常量聲明 AST 節點
        """
        name = self.consume(TokenType.IDENTIFIER, "期望常量名稱").lexeme
        
        # 可選的類型註解
        const_type = None
        if self.match(TokenType.COLON):
            const_type = self.type_expression()
        
        # 常量必須初始化
        self.consume(TokenType.EQUAL, "期望 '=' 在常量聲明中")
        initializer = self.expression()
        
        # 分號是可選的
        self.match(TokenType.SEMICOLON)
        
        return ast_nodes.ConstDeclaration(name, initializer, const_type)
    
    def statement(self) -> ast_nodes.Statement:
        """
        解析語句
        
        Returns:
            語句 AST 節點
        """
        # 解析塊語句
        if self.match(TokenType.LEFT_BRACE):
            return self.block_statement()
        
        # 解析 unsafe 區塊
        if self.match(TokenType.UNSAFE):
            return self.unsafe_block_statement()
        
        # 解析 if 語句
        if self.match(TokenType.IF):
            return self.if_statement()
        
        # 解析 for 語句
        if self.match(TokenType.FOR):
            return self.for_statement()
        
        # 解析 while 語句
        if self.match(TokenType.WHILE):
            return self.while_statement()
        
        # 解析 return 語句
        if self.match(TokenType.RETURN):
            return self.return_statement()
        
        # 解析表達式語句
        return self.expression_statement()
    
    def unsafe_block_statement(self) -> ast_nodes.UnsafeBlockStatement:
        """
        解析 unsafe 區塊語句
        
        Returns:
            UnsafeBlockStatement AST 節點
        """
        # 解析左花括號
        self.consume(TokenType.LEFT_BRACE, "預期 unsafe 後有 '{'")
        
        # 解析區塊內的語句
        statements = []
        while not self.check(TokenType.RIGHT_BRACE) and not self.is_at_end():
            try:
                statements.append(self.declaration())
            except Exception as e:
                # 發生錯誤時，同步到下一個語句
                self.synchronize()
                # 如果還沒到右括號，繼續解析
                if not self.check(TokenType.RIGHT_BRACE) and not self.is_at_end():
                    continue
                else:
                    # 否則退出循環
                    break
        
        # 解析右花括號
        self.consume(TokenType.RIGHT_BRACE, "預期 unsafe 區塊以 '}' 結束")
        
        return ast_nodes.UnsafeBlockStatement(statements)
    
    def block_statement(self) -> ast_nodes.BlockStatement:
        """解析塊語句"""
        statements = []
        
        while not self.check(TokenType.RIGHT_BRACE) and not self.is_at_end():
            statements.append(self.declaration())
        
        if not self.is_at_end():
            self.consume(TokenType.RIGHT_BRACE, "期望 '}' 在塊結束")
        
        return ast_nodes.BlockStatement(statements)
    
    def if_statement(self) -> ast_nodes.IfStatement:
        """
        解析 if 語句
        
        Returns:
            if 語句 AST 節點
        """
        condition = self.expression()
        
        then_branch = self.statement()
        
        else_branch = None
        if self.match(TokenType.ELSE):
            else_branch = self.statement()
        
        return ast_nodes.IfStatement(condition, then_branch, else_branch)
    
    def for_statement(self) -> ast_nodes.ForStatement:
        """
        解析 for 語句
        
        Returns:
            for 語句 AST 節點
        """
        iterator = self.consume(TokenType.IDENTIFIER, "期望迭代變量名稱").lexeme
        
        self.consume(TokenType.IN, "期望 'in' 在 for 循環中")
        
        # 解析範圍表達式 (例如: 0..10)
        start = self.expression()
        
        self.consume(TokenType.DOT_DOT, "期望 '..' 在範圍表達式中")
        
        end = self.expression()
        
        body = self.statement()
        
        return ast_nodes.ForStatement(iterator, start, end, body)
    
    def while_statement(self) -> ast_nodes.WhileStatement:
        """
        解析 while 語句
        
        Returns:
            while 語句 AST 節點
        """
        condition = self.expression()
        
        body = self.statement()
        
        return ast_nodes.WhileStatement(condition, body)
    
    def return_statement(self) -> ast_nodes.ReturnStatement:
        """
        解析 return 語句
        
        Returns:
            return 語句 AST 節點
        """
        value = None
        if not self.check(TokenType.SEMICOLON):
            value = self.expression()
        
        # 分號是可選的
        self.match(TokenType.SEMICOLON)
        
        return ast_nodes.ReturnStatement(value)
    
    def expression_statement(self) -> ast_nodes.ExpressionStatement:
        """
        解析表達式語句
        
        Returns:
            表達式語句 AST 節點
        """
        expr = self.expression()
        
        # 分號是可選的
        self.match(TokenType.SEMICOLON)
        
        return ast_nodes.ExpressionStatement(expr)
    
    def expression(self) -> ast_nodes.Expression:
        """
        解析表達式
        
        Returns:
            表達式 AST 節點
        """
        return self.assignment()
    
    def assignment(self) -> ast_nodes.Expression:
        """
        解析賦值表達式
        
        Returns:
            表達式 AST 節點
        """
        expr = self.ternary()
        
        if (self.previous().type in [TokenType.EQUAL, TokenType.PLUS_EQUAL, 
                                   TokenType.MINUS_EQUAL, TokenType.STAR_EQUAL, 
                                   TokenType.SLASH_EQUAL, TokenType.PERCENT_EQUAL]):
            operator = self.previous().lexeme
            self.advance()
            value = self.assignment()  # 遞迴處理右結合性
            
            # 檢查左側是否為有效的賦值目標
            if isinstance(expr, ast_nodes.Variable):
                return ast_nodes.AssignmentExpression(expr.name, value)
            
            if isinstance(expr, ast_nodes.GetExpression):
                return ast_nodes.SetExpression(expr.object, expr.name, value)
            
            if isinstance(expr, ast_nodes.IndexExpression):
                return ast_nodes.IndexAssignmentExpression(expr.object, expr.index, value)
            
            self.error("無效的賦值目標")
        
        return expr
    
    def ternary(self) -> ast_nodes.Expression:
        """解析三元運算表達式"""
        expr = self.logical_or()
        
        if self.previous().type == TokenType.QUESTION:
            self.advance()  # 消耗 '?'
            true_expr = self.expression()
            
            if self.previous().type != TokenType.COLON:
                self.error("預期 ':' 在三元運算表達式中")
            
            self.advance()  # 消耗 ':'
            false_expr = self.ternary()  # 遞迴處理右結合性
            
            return ast_nodes.ConditionalExpression(expr, true_expr, false_expr)
        
        return expr
    
    def logical_or(self) -> ast_nodes.Expression:
        """解析邏輯OR表達式"""
        expr = self.logical_and()
        
        while (self.previous().type == TokenType.OR or 
               self.previous().type == TokenType.OR_OR):
            operator = self.previous().lexeme
            self.advance()
            right = self.logical_and()
            expr = ast_nodes.LogicalExpression(expr, operator, right)
        
        return expr
    
    def logical_and(self) -> ast_nodes.Expression:
        """解析邏輯AND表達式"""
        expr = self.equality()
        
        while (self.previous().type == TokenType.AND or 
               self.previous().type == TokenType.AND_AND):
            operator = self.previous().lexeme
            self.advance()
            right = self.equality()
            expr = ast_nodes.LogicalExpression(expr, operator, right)
        
        return expr
    
    def equality(self) -> ast_nodes.Expression:
        """
        解析等式表達式
        
        Returns:
            AST節點
        """
        expr = self.comparison()
        
        while self.match([TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL]):
            operator = self.previous()
            right = self.comparison()
            expr = ast_nodes.BinaryExpression(expr, operator, right)
        
        return expr
    
    def comparison(self) -> ast_nodes.Expression:
        """
        解析比較表達式
        
        Returns:
            AST節點
        """
        expr = self.term()
        
        while self.match([TokenType.GREATER, TokenType.GREATER_EQUAL, 
                         TokenType.LESS, TokenType.LESS_EQUAL]):
            operator = self.previous()
            right = self.term()
            expr = ast_nodes.BinaryExpression(expr, operator, right)
        
        # 處理鏈式比較，如 a < b < c
        if hasattr(expr, 'operator') and hasattr(expr, 'right'):
            expressions = [expr.left, expr.right]
            operators = [expr.operator]
            
            while self.match([TokenType.GREATER, TokenType.GREATER_EQUAL, 
                             TokenType.LESS, TokenType.LESS_EQUAL]):
                operators.append(self.previous())
                expressions.append(self.term())
            
            # 如果有多個比較運算符，構建鏈式比較
            if len(operators) > 1:
                # 使用AND合併多個比較
                comparison_expr = ast_nodes.BinaryExpression(
                    expressions[0], operators[0], expressions[1]
                )
                
                for i in range(1, len(operators)):
                    right_expr = ast_nodes.BinaryExpression(
                        expressions[i], operators[i], expressions[i + 1]
                    )
                    comparison_expr = ast_nodes.LogicalExpression(
                        comparison_expr, TokenType.LOGICAL_AND, right_expr
                    )
                
                return comparison_expr
        
        return expr
    
    def term(self) -> ast_nodes.Expression:
        """
        解析加減法表達式
        term -> factor ( ( "+" | "-" ) factor )*
        
        Returns:
            AST節點
        """
        expr = self.factor()
        
        while self.match([TokenType.PLUS, TokenType.MINUS]):
            operator = self.previous()
            right = self.factor()
            expr = ast_nodes.BinaryExpression(expr, operator, right)
        
        return expr
    
    def factor(self) -> ast_nodes.Expression:
        """解析乘除與取餘表達式"""
        expr = self.bitwise()
        
        while (self.previous().type == TokenType.STAR or 
               self.previous().type == TokenType.SLASH or
               self.previous().type == TokenType.PERCENT):
            operator = self.previous().lexeme
            self.advance()
            right = self.bitwise()
            expr = ast_nodes.BinaryExpression(expr, operator, right)
        
        return expr
    
    def bitwise(self) -> ast_nodes.Expression:
        """
        解析位運算表達式
        
        Returns:
            AST節點
        """
        expr = self.unary()
        
        while self.match([TokenType.AMPERSAND, TokenType.PIPE, TokenType.CARET,
                         TokenType.LEFT_SHIFT, TokenType.RIGHT_SHIFT]):
            operator = self.previous()
            right = self.unary()
            expr = ast_nodes.BinaryExpression(expr, operator, right)
        
        return expr
    
    def unary(self) -> ast_nodes.Expression:
        """解析一元表達式"""
        if (self.previous().type in [TokenType.BANG, TokenType.MINUS, 
                                   TokenType.TILDE, TokenType.AMPERSAND]):
            operator = self.previous().lexeme
            self.advance()
            right = self.unary()  # 遞迴處理右結合性
            return ast_nodes.UnaryExpr(operator, right)
        
        return self.call()
    
    def call(self) -> ast_nodes.Expression:
        """解析函數調用表達式"""
        expr = self.primary()
        
        while True:
            if self.previous().type == TokenType.LEFT_PAREN:
                expr = self.finish_call(expr)
            elif self.previous().type == TokenType.DOT:
                self.advance()  # 消耗 '.'
                if self.previous().type != TokenType.IDENTIFIER:
                    self.error("預期成員名稱")
                
                name = self.previous().lexeme
                self.advance()
                expr = ast_nodes.GetExpression(expr, name)
            elif self.previous().type == TokenType.LEFT_BRACKET:
                index = self.expression()
                self.consume(TokenType.RIGHT_BRACKET, "期望 ']' 在索引表達式之後")
                expr = ast_nodes.IndexExpression(expr, index)
            else:
                break
        
        return expr
    
    def finish_call(self, callee: ast_nodes.Expression) -> ast_nodes.CallExpression:
        """完成函數調用解析"""
        self.advance()  # 消耗 '('
        
        arguments = []
        if self.previous().type != TokenType.RIGHT_PAREN:
            # 解析參數列表
            arguments.append(self.expression())
            
            while self.previous().type == TokenType.COMMA:
                self.advance()  # 消耗 ','
                
                # 處理尾隨逗號
                if self.previous().type == TokenType.RIGHT_PAREN:
                    break
                    
                arguments.append(self.expression())
        
        if self.previous().type != TokenType.RIGHT_PAREN:
            self.error("預期 ')' 結束函數調用")
        
        self.advance()  # 消耗 ')'
        
        return ast_nodes.CallExpression(callee, arguments)
    
    def primary(self) -> ast_nodes.Expression:
        """解析基本表達式"""
        if self.previous().type == TokenType.FALSE:
            self.advance()
            return ast_nodes.BooleanLiteral(False)
        elif self.previous().type == TokenType.TRUE:
            self.advance()
            return ast_nodes.BooleanLiteral(True)
        elif self.previous().type == TokenType.NUMBER:
            value = self.previous().lexeme
            self.advance()
            return ast_nodes.IntLiteral(int(value))
        elif self.previous().type == TokenType.FLOAT_LITERAL:
            value = self.previous().lexeme
            self.advance()
            return ast_nodes.FloatLiteral(float(value))
        """
        解析基本表達式，如變數、字面量等
        
        Returns:
            表達式 AST 節點
        """
        # 布林字面量
        if self.match(TokenType.TRUE):
            return ast_nodes.BooleanLiteral(True)
        if self.match(TokenType.FALSE):
            return ast_nodes.BooleanLiteral(False)
        
        # null 字面量
        if self.match(TokenType.NULL):
            return ast_nodes.NullLiteral()
        
        # 數字字面量
        if self.match(TokenType.NUMBER):
            return ast_nodes.IntLiteral(int(self.previous().lexeme))
        if self.match(TokenType.FLOAT_LITERAL):
            return ast_nodes.FloatLiteral(float(self.previous().lexeme))
        
        # 字符串字面量
        if self.match(TokenType.STRING_LITERAL):
            return ast_nodes.StringLiteral(self.previous().literal)
        if self.match(TokenType.TEMPLATE_STRING):
            # 使用字符串插值處理器處理模板字符串
            content = self.previous().literal
            return self.string_processor.process_string(content, '`')
        
        # 字符字面量
        if self.match(TokenType.CHAR_LITERAL):
            return ast_nodes.CharLiteral(self.previous().literal)
        
        # 處理內建函數關鍵字
        if self.match(TokenType.PRINT):
            return ast_nodes.Variable("print")
        if self.match(TokenType.PRINTLN):
            return ast_nodes.Variable("println")
        if self.match(TokenType.SLEEP):
            return ast_nodes.Variable("sleep")
        if self.match(TokenType.LEN):
            return ast_nodes.Variable("len")
        if self.match(TokenType.IS_ERROR):
            return ast_nodes.Variable("is_error")
        
        # 變數引用
        if self.match(TokenType.IDENTIFIER):
            return ast_nodes.Variable(self.previous().lexeme)
        
        # 處理錯誤表達式
        if self.match(TokenType.ERROR):
            # 檢查是否接著一個開括號
            if self.match(TokenType.LEFT_PAREN):
                # 解析錯誤消息表達式
                message = self.expression()
                self.consume(TokenType.RIGHT_PAREN, "期望 ')' 在錯誤消息後")
                return ast_nodes.ErrorExpression(message)
            else:
                # 沒有括號，報錯
                self.error("期望 '(' 在 error 關鍵字後")
                return ast_nodes.ErrorExpression(ast_nodes.StringLiteral("錯誤表達式格式不正確"))
        
        # 括號表達式
        if self.match(TokenType.LEFT_PAREN):
            expr = self.expression()
            self.consume(TokenType.RIGHT_PAREN, "期望 ')' 在表達式後")
            return expr
        
        # 數組字面量
        if self.match(TokenType.LEFT_BRACKET):
            elements = []
            
            # 如果不是空數組，解析元素
            if not self.check(TokenType.RIGHT_BRACKET):
                elements.append(self.expression())
                
                while self.match(TokenType.COMMA):
                    elements.append(self.expression())
            
            self.consume(TokenType.RIGHT_BRACKET, "期望 ']' 在數組字面量後")
            return ast_nodes.ListLiteral(elements)
        
        # 無效的表達式
        self.error(f"期望表達式，但得到 {self.peek().lexeme}")
        return ast_nodes.ErrorExpression("無效的表達式")
    
    def type_expression(self) -> ast_nodes.TypeExpression:
        """
        解析類型表達式
        
        Returns:
            類型表達式 AST 節點
        """
        # 處理內建類型關鍵字
        if self.match(TokenType.INT, TokenType.FLOAT, TokenType.BOOL, 
                      TokenType.STRING, TokenType.ANY, TokenType.VOID,
                      TokenType.ERROR):
            type_name = self.previous().lexeme.lower()
            return ast_nodes.NamedTypeExpression(type_name)
        
        # 基本類型和泛型類型
        if self.match(TokenType.IDENTIFIER):
            type_name = self.previous().lexeme
            
            # 檢查是否為泛型類型（如 List<T>）
            if self.match(TokenType.LESS):
                type_params = []
                
                # 至少需要一個類型參數
                type_params.append(self.type_expression())
                
                while self.match(TokenType.COMMA):
                    type_params.append(self.type_expression())
                
                self.consume(TokenType.GREATER, "期望 '>' 在泛型類型參數列表後")
                
                return ast_nodes.GenericTypeExpression(type_name, type_params)
            
            # 普通命名類型
            return ast_nodes.NamedTypeExpression(type_name)
        
        # 指針類型
        if self.match(TokenType.STAR):
            element_type = self.type_expression()
            return ast_nodes.PointerTypeExpression(element_type)
        
        # 數組類型
        if self.match(TokenType.LEFT_BRACKET):
            size = None
            if not self.check(TokenType.RIGHT_BRACKET):
                size_expr = self.expression()
                if isinstance(size_expr, ast_nodes.IntLiteral):
                    size = size_expr.value
                else:
                    self.error("數組大小必須是整數常量")
            
            self.consume(TokenType.RIGHT_BRACKET, "期望 ']' 在數組類型之後")
            
            element_type = self.type_expression()
            
            return ast_nodes.ArrayTypeExpression(element_type, size)
        
        # 元組類型
        if self.match(TokenType.LEFT_PAREN):
            element_types = []
            
            if not self.check(TokenType.RIGHT_PAREN):
                element_types.append(self.type_expression())
                
                while self.match(TokenType.COMMA):
                    element_types.append(self.type_expression())
            
            self.consume(TokenType.RIGHT_PAREN, "期望 ')' 在元組類型之後")
            
            return ast_nodes.TupleTypeExpression(element_types)
        
        # 函數類型
        if self.match(TokenType.FN):
            self.consume(TokenType.LEFT_PAREN, "期望 '(' 在函數類型參數列表前")
            
            param_types = []
            
            if not self.check(TokenType.RIGHT_PAREN):
                param_types.append(self.type_expression())
                
                while self.match(TokenType.COMMA):
                    param_types.append(self.type_expression())
            
            self.consume(TokenType.RIGHT_PAREN, "期望 ')' 在函數類型參數列表後")
            
            self.consume(TokenType.ARROW, "期望 '->' 在函數類型的返回類型前")
            
            return_type = self.type_expression()
            
            return ast_nodes.FunctionTypeExpression(param_types, return_type)
        
        # 可選類型
        if self.match(TokenType.OPTIONAL):
            self.consume(TokenType.LESS, "期望 '<' 在 optional 類型參數前")
            inner_type = self.type_expression()
            self.consume(TokenType.GREATER, "期望 '>' 在 optional 類型參數後")
            return ast_nodes.OptionalTypeExpression(inner_type)
        
        # 聯合類型
        if self.match(TokenType.UNION):
            self.consume(TokenType.LESS, "期望 '<' 在聯合類型參數列表前")
            
            types = []
            types.append(self.type_expression())
            
            while self.match(TokenType.COMMA):
                types.append(self.type_expression())
            
            self.consume(TokenType.GREATER, "期望 '>' 在聯合類型參數列表後")
            
            return ast_nodes.UnionTypeExpression(types)
        
        # 錯誤處理
        self.error(f"期望類型表達式，但得到 {self.peek().lexeme}")
        return ast_nodes.ErrorTypeExpression()
    
    def struct_field(self) -> ast_nodes.StructField:
        """
        解析結構體欄位
        
        Returns:
            結構體欄位 AST 節點
        """
        # 檢查是否有override修飾
        is_override = self.match(TokenType.OVERRIDE)
        
        field_name = self.consume(TokenType.IDENTIFIER, "期望欄位名稱").lexeme
        self.consume(TokenType.COLON, "期望 ':' 在欄位名稱之後")
        field_type = self.type_expression()
        
        # 允許尾部逗號或分號
        self.match(TokenType.COMMA) or self.match(TokenType.SEMICOLON)
        
        return ast_nodes.StructField(field_name, field_type, is_override)
    
    def struct_method(self, struct_name: str) -> ast_nodes.MethodDeclaration:
        """
        解析結構體方法
        
        Args:
            struct_name: 結構體名稱
        
        Returns:
            方法聲明 AST 節點
        """
        # 檢查是否有override修飾
        is_override = self.match(TokenType.OVERRIDE)
        
        name = self.consume(TokenType.IDENTIFIER, "期望方法名稱").lexeme
        
        # 解析參數列表
        self.consume(TokenType.LEFT_PAREN, "期望 '(' 在方法參數列表前")
        parameters = []
        
        # 添加接收者作為第一個參數
        parameters.append(ast_nodes.Parameter("self", ast_nodes.TypeExpression(struct_name)))
        
        if not self.check(TokenType.RIGHT_PAREN):
            parameters.append(self.function_parameter())
            
            while self.match(TokenType.COMMA):
                if self.check(TokenType.RIGHT_PAREN):
                    break
                parameters.append(self.function_parameter())
        
        self.consume(TokenType.RIGHT_PAREN, "期望 ')' 在方法參數列表後")
        
        # 解析返回類型
        return_type = None
        if self.match(TokenType.ARROW):
            return_type = self.type_expression()
        
        # 解析方法體
        body = self.block_statement()
        
        return ast_nodes.MethodDeclaration(name, parameters, return_type, body, struct_name, is_override)
    
    def lambda_expression(self) -> ast_nodes.LambdaExpression:
        """
        解析匿名函數表達式，例如：fn(x: int) -> int { return x * 2 }
        
        Returns:
            匿名函數表達式 AST 節點
        """
        # 匿名函數必須以 fn 開頭
        self.consume(TokenType.FN, "期望 'fn' 在匿名函數開始處")
        
        # 解析參數列表
        self.consume(TokenType.LEFT_PAREN, "期望 '(' 在 fn 關鍵字之後")
        parameters = []
        
        if not self.check(TokenType.RIGHT_PAREN):
            # 解析第一個參數
            param = self.function_parameter()
            parameters.append(param)
            
            # 解析後續參數
            while self.match(TokenType.COMMA):
                param = self.function_parameter()
                parameters.append(param)
        
        self.consume(TokenType.RIGHT_PAREN, "期望 ')' 在參數列表之後")
        
        # 解析回傳型別（可選）
        return_type = None
        if self.match(TokenType.ARROW):
            return_type = self.type_expression()
        
        # 解析函數體
        body = self.block_statement()
        
        return ast_nodes.LambdaExpression(parameters, return_type, body)
    
    def import_declaration(self):
        """解析 import 語句"""
        from_module = None
        
        # 處理 from ... import ... 結構
        if self.match(TokenType.FROM):
            # 解析模組路徑
            module_path = []
            
            # 第一個標識符
            module_path.append(self.consume(TokenType.IDENTIFIER, "期望模組名稱").lexeme)
            
            # 處理 a.b.c 形式的路徑
            while self.match(TokenType.DOT):
                module_path.append(self.consume(TokenType.IDENTIFIER, "期望模組名稱").lexeme)
            
            from_module = ".".join(module_path)
            
            # 必須存在 import 關鍵字
            self.consume(TokenType.IMPORT, "期望 'import' 關鍵字")
        
        # 解析要導入的內容
        imports = []
        
        # 第一個導入元素
        imports.append(self.consume(TokenType.IDENTIFIER, "期望導入項目名稱").lexeme)
        
        # 處理多個導入項 (import a, b, c)
        while self.match(TokenType.COMMA):
            imports.append(self.consume(TokenType.IDENTIFIER, "期望導入項目名稱").lexeme)
        
        # 如果有分號，消耗它
        self.match(TokenType.SEMICOLON)
        
        # 創建並返回 ImportDeclaration 節點
        return ast_nodes.ImportDeclaration(from_module, imports)
    
    def main_block(self) -> ast_nodes.MainBlock:
        """
        解析main區塊
        
        Returns:
            MainBlock節點
        """
        # 期望左大括號
        self.consume(TokenType.LEFT_BRACE, "期望 '{' 在 main 之後")
        
        # 解析區塊語句
        statements = []
        while not self.check(TokenType.RIGHT_BRACE) and not self.is_at_end():
            statements.append(self.declaration())
            
        # 期望右大括號
        self.consume(TokenType.RIGHT_BRACE, "期望 '}' 結束 main 區塊")
        
        return ast_nodes.MainBlock(statements)
    
    # 輔助方法
    
    def match(self, *types) -> bool:
        """
        檢查當前詞法單元是否匹配指定類型，如果匹配則消耗
        
        Args:
            *types: 可接受的詞法單元類型
            
        Returns:
            是否匹配成功
        """
        for type in types:
            if isinstance(type, list):
                # 處理列表形式的類型
                for t in type:
                    if self.check(t):
                        self.advance()
                        return True
            elif self.check(type):
                self.advance()
                return True
        return False
    
    def check(self, type) -> bool:
        """
        檢查當前詞法單元類型
        
        Args:
            type: 詞法單元類型
            
        Returns:
            是否匹配
        """
        if self.is_at_end():
            return False
        
        return self.peek().type == type
    
    def advance(self) -> Token:
        """
        前進到下一個詞法單元
        
        Returns:
            前一個詞法單元
        """
        if not self.is_at_end():
            self.current += 1
        
        return self.previous()
    
    def is_at_end(self) -> bool:
        """
        檢查是否到達詞法單元序列末尾
        
        Returns:
            是否到達末尾
        """
        return self.peek().type == TokenType.EOF
    
    def peek(self) -> Token:
        """
        獲取當前詞法單元
        
        Returns:
            當前詞法單元
        """
        return self.tokens[self.current]
    
    def peek_next(self) -> Token:
        """
        獲取下一個詞法單元
        
        Returns:
            下一個詞法單元
        """
        if self.current + 1 >= len(self.tokens):
            return self.tokens[-1]  # 返回 EOF 標記
        return self.tokens[self.current + 1]
    
    def previous(self) -> Token:
        """
        獲取前一個詞法單元
        
        Returns:
            前一個詞法單元
        """
        return self.tokens[self.current - 1]
    
    def consume(self, type, message) -> Token:
        """
        消耗當前詞法單元
        
        Args:
            type: 期望的詞法單元類型
            message: 錯誤消息
            
        Returns:
            消耗的詞法單元
            
        Raises:
            Exception: 如果當前詞法單元類型不匹配
        """
        if self.check(type):
            return self.advance()
        
        self.error(message)
        return self.peek()
    
    def error(self, message):
        """
        報告錯誤
        
        Args:
            message: 錯誤消息
            
        Raises:
            Exception: 錯誤
        """
        token = self.peek()
        error = f"第 {token.line} 行，{token.column} 列: {message}"
        self.errors.append(error)
        raise Exception(error)
    
    def synchronize(self):
        """
        在錯誤後同步
        """
        self.advance()
        
        while not self.is_at_end():
            if self.previous().type == TokenType.SEMICOLON:
                return
            
            if self.peek().type in [
                TokenType.FN,
                TokenType.CONST,
                TokenType.IF,
                TokenType.WHILE,
                TokenType.FOR,
                TokenType.RETURN,
                TokenType.STRUCT,
                TokenType.ENUM
            ]:
                return
            
            self.advance()
    
    def scan_string(self):
        """
        掃描字符串字面量
        
        Returns:
            字符串字面量節點
        """
        # 記錄引號類型
        quote_type = self.previous().lexeme  # '、"、`
        
        # 掃描直到字符串結束或文件結束
        content = ""
        while not self.is_at_end() and self.peek().lexeme != quote_type:
            # 處理轉義字符
            if self.peek().lexeme == '\\':
                self.advance()  # 消耗 \
                if self.is_at_end():
                    self.error("未閉合的字符串")
                    break
                # 處理常見轉義序列
                c = self.advance().lexeme
                if c == 'n':
                    content += '\n'
                elif c == 't':
                    content += '\t'
                elif c == 'r':
                    content += '\r'
                elif c == quote_type:
                    content += quote_type
                elif c == '\\':
                    content += '\\'
                else:
                    content += c
            else:
                # 獲取下一個字符
                content += self.advance().lexeme
        
        # 消耗右引號
        if self.is_at_end():
            self.error("未閉合的字符串")
        else:
            self.advance()  # 消耗右引號
        
        # 處理字符串插值
        if quote_type == '`':
            return self.string_processor.process_string(content, quote_type)
        else:
            return ast_nodes.StringLiteral(content)
    
    def spawn_expression(self) -> ast_nodes.Expression:
        """
        解析spawn表達式，例如：spawn work() 或 spawn fn() { ... }
        
        Returns:
            spawn表達式 AST 節點
        """
        # 檢查是否為 spawn 表達式
        if not self.match(TokenType.SPAWN):
            return self.assignment()
        
        # 根據新的語法規範，spawn 可以後接函數調用或匿名函數
        if self.check(TokenType.FN):
            # 解析匿名函數表達式
            lambda_expr = self.lambda_expression()
            
            # 匿名函數必須立即被調用
            if not self.check(TokenType.LEFT_PAREN):
                self.error("spawn 後的匿名函數必須立即被調用")
                return ast_nodes.ErrorExpression("spawn 後的匿名函數必須立即被調用")
            
            # 解析函數調用
            self.consume(TokenType.LEFT_PAREN, "期望 '(' 在函數表達式之後")
            arguments = []
            if not self.check(TokenType.RIGHT_PAREN):
                arguments.append(self.assignment())
                
                while self.match(TokenType.COMMA):
                    arguments.append(self.assignment())
            
            self.consume(TokenType.RIGHT_PAREN, "期望 ')' 在參數列表之後")
            
            call = ast_nodes.CallExpression(lambda_expr, arguments)
            return ast_nodes.SpawnExpression(call)
        else:
            # 普通變量或函數調用
            callee = self.call()
            
            # 如果不是函數調用，將其包裝為調用表達式
            if not isinstance(callee, ast_nodes.CallExpression):
                if self.check(TokenType.LEFT_PAREN):
                    # 如果後面是左括號，解析函數調用
                    self.consume(TokenType.LEFT_PAREN, "期望 '(' 在函數名稱之後")
                    arguments = []
                    if not self.check(TokenType.RIGHT_PAREN):
                        arguments.append(self.assignment())
                        
                        while self.match(TokenType.COMMA):
                            arguments.append(self.assignment())
                    
                    self.consume(TokenType.RIGHT_PAREN, "期望 ')' 在參數列表之後")
                    callee = ast_nodes.CallExpression(callee, arguments)
                else:
                    # 函數變量需要被調用
                    self.error("spawn 後必須接函數調用")
                    return ast_nodes.ErrorExpression("spawn 後必須接函數調用")
            
            return ast_nodes.SpawnExpression(callee)
    
    def await_expression(self) -> ast_nodes.Expression:
        """
        解析await表達式，例如：await task1, task2 或 await task1(), task2()
        
        Returns:
            await表達式 AST 節點
        """
        # 檢查是否為 await 表達式
        if not self.match(TokenType.AWAIT):
            return self.spawn_expression()
            
        # 解析等待的表達式列表
        expressions = []
        
        # 解析第一個表達式（可以是任務變數或函數調用）
        expressions.append(self.call())
        
        # 解析後續表達式（如果有）
        while self.match(TokenType.COMMA):
            expressions.append(self.call())
        
        # 創建 await 表達式節點
        return ast_nodes.AwaitExpression(expressions)

    def _variable_declaration(self):
        """解析變數聲明語句"""
        # 變數名稱
        if self.current_token.type != TokenType.IDENTIFIER:
            self._error("預期變數名稱")
        
        name = self.current_token.lexeme
        self._advance()
        
        # 變數類型註解（可選）
        var_type = None
        if self.current_token.type == TokenType.COLON:
            self._advance()
            var_type = self._type_annotation()
        
        # 必須有初始化表達式
        if self.current_token.type != TokenType.WALRUS:
            self._error("變數宣告必須使用 ':=' 進行賦值")
        
        self._advance()  # 消耗 ':='
        value = self._expression()
        
        return ast_nodes.VarDeclaration(name, var_type, value)

    def _const_declaration(self):
        """解析常數聲明語句"""
        # 消耗 'const' 關鍵字
        self._advance()
        
        # 常數名稱
        if self.current_token.type != TokenType.IDENTIFIER:
            self._error("預期常數名稱")
        
        name = self.current_token.lexeme
        self._advance()
        
        # 常數類型註解（可選）
        const_type = None
        if self.current_token.type == TokenType.COLON:
            self._advance()
            const_type = self._type_annotation()
        
        # 必須有初始化表達式
        if self.current_token.type != TokenType.EQUAL:
            self._error("常數宣告必須使用 '=' 進行賦值")
        
        self._advance()  # 消耗 '='
        value = self._expression()
        
        return ast_nodes.ConstDeclaration(name, const_type, value)

    def _type_annotation(self):
        """解析類型注解"""
        if self.current_token.type != TokenType.IDENTIFIER:
            self._error("預期類型名稱")
        
        type_name = self.current_token.lexeme
        self._advance()
        
        # 處理數組類型標記 '[]'
        if (self.current_token.type == TokenType.LEFT_BRACKET and 
            self._peek_next().type == TokenType.RIGHT_BRACKET):
            self._advance()  # 消耗 '['
            self._advance()  # 消耗 ']'
            type_name += "[]"
        
        # 處理泛型類型如 ptr<T>, optional<T> 等
        if self.current_token.type == TokenType.LESS:
            self._advance()  # 消耗 '<'
            generic_param = self._type_annotation()
            if self.current_token.type != TokenType.GREATER:
                self._error("預期 '>' 結束泛型參數")
            self._advance()  # 消耗 '>'
            type_name = f"{type_name}<{generic_param}>"
        
        return type_name 

    def _statement(self):
        """解析語句"""
        if self.current_token.type == TokenType.IF:
            return self._if_statement()
        elif self.current_token.type == TokenType.WHILE:
            return self._while_statement()
        elif self.current_token.type == TokenType.FOR:
            return self._for_statement()
        elif self.current_token.type == TokenType.LEFT_BRACE:
            return self._block_statement()
        elif self.current_token.type == TokenType.CONST:
            return self._const_declaration()
        elif self.current_token.type == TokenType.FN:
            return self._function_declaration()
        elif self.current_token.type == TokenType.RETURN:
            return self._return_statement()
        elif self.current_token.type == TokenType.IDENTIFIER:
            # 檢查下一個token是否為:=，判斷是變數宣告還是表達式語句
            if self._peek_next().type == TokenType.WALRUS:
                return self._variable_declaration()
            else:
                return self._expression_statement()
        else:
            return self._expression_statement()

    def _if_statement(self):
        """解析IF語句"""
        self._advance()  # 消耗 'if' 關鍵字
        
        # 解析條件表達式（不需要括號）
        condition = self._expression()
        
        # 解析then分支
        if self.current_token.type != TokenType.LEFT_BRACE:
            self._error("預期 '{' 開始IF語句體")
        
        then_branch = self._block_statement().statements
        
        # 解析可選的else分支
        else_branch = None
        if self.current_token.type == TokenType.ELSE:
            self._advance()  # 消耗 'else' 關鍵字
            
            if self.current_token.type == TokenType.IF:
                # else if 結構
                else_branch = [self._if_statement()]
            elif self.current_token.type == TokenType.LEFT_BRACE:
                # 普通else塊
                else_branch = self._block_statement().statements
            else:
                self._error("預期 '{' 或 'if' 在ELSE關鍵字後")
        
        return ast_nodes.IfStatement(condition, then_branch, else_branch)

    def _while_statement(self):
        """解析WHILE循環語句"""
        self._advance()  # 消耗 'while' 關鍵字
        
        # 解析條件表達式（不需要括號）
        condition = self._expression()
        
        # 解析循環體
        if self.current_token.type != TokenType.LEFT_BRACE:
            self._error("預期 '{' 開始WHILE循環體")
        
        body = self._block_statement().statements
        
        return ast_nodes.WhileStatement(condition, body)

    def _for_statement(self):
        """解析FOR循環語句"""
        self._advance()  # 消耗 'for' 關鍵字
        
        # 解析迭代變數
        if self.current_token.type != TokenType.IDENTIFIER:
            self._error("預期迭代變數名稱")
        
        variables = [self.current_token.lexeme]
        self._advance()
        
        # 處理鍵值對迭代情況（如 for key, value in map）
        if self.current_token.type == TokenType.COMMA:
            self._advance()  # 消耗 ','
            
            if self.current_token.type != TokenType.IDENTIFIER:
                self._error("預期第二個迭代變數名稱")
            
            variables.append(self.current_token.lexeme)
            self._advance()
        
        # 檢查 'in' 關鍵字
        if self.current_token.type != TokenType.IN:
            self._error("預期 'in' 關鍵字")
        self._advance()  # 消耗 'in' 關鍵字
        
        # 解析可迭代對象
        iterable = self._expression()
        
        # 解析循環體
        if self.current_token.type != TokenType.LEFT_BRACE:
            self._error("預期 '{' 開始FOR循環體")
        
        body = self._block_statement().statements
        
        return ast_nodes.ForStatement(variables, iterable, body)

    def _block_statement(self):
        """解析代碼塊"""
        self._advance()  # 消耗 '{'
        
        statements = []
        while self.current_token.type != TokenType.RIGHT_BRACE and self.current_token.type != TokenType.EOF:
            statements.append(self._statement())
        
        if self.current_token.type != TokenType.RIGHT_BRACE:
            self._error("預期 '}' 結束代碼塊")
        
        self._advance()  # 消耗 '}'
        
        return ast_nodes.BlockStatement(statements)

    def _function_declaration(self):
        """解析函數聲明"""
        self._advance()  # 消耗 'fn' 關鍵字
        
        # 獲取函數名稱
        name = self.current_token.lexeme
        if self.current_token.type != TokenType.IDENTIFIER:
            self._error("預期函數名稱")
        self._advance()
        
        # 解析參數列表
        if self.current_token.type != TokenType.LEFT_PAREN:
            self._error("預期 '(' 開始參數列表")
        self._advance()  # 消耗 '('
        
        params = self._parameter_list()
        
        if self.current_token.type != TokenType.RIGHT_PAREN:
            self._error("預期 ')' 結束參數列表")
        self._advance()  # 消耗 ')'
        
        # 解析返回類型（可選）
        return_type = None
        if self.current_token.type == TokenType.ARROW:
            self._advance()  # 消耗 '->'
            return_type = self._type_annotation()
        
        # 解析函數體
        if self.current_token.type != TokenType.LEFT_BRACE:
            self._error("預期 '{' 開始函數體")
        
        body = self._block_statement().statements
        
        return ast_nodes.FunctionDeclaration(name, params, return_type, body)

    def _function_expression(self):
        """解析匿名函數表達式"""
        self._advance()  # 消耗 'fn' 關鍵字
        
        # 解析參數列表
        if self.current_token.type != TokenType.LEFT_PAREN:
            self._error("預期 '(' 開始參數列表")
        self._advance()  # 消耗 '('
        
        params = self._parameter_list()
        
        if self.current_token.type != TokenType.RIGHT_PAREN:
            self._error("預期 ')' 結束參數列表")
        self._advance()  # 消耗 ')'
        
        # 解析返回類型（可選）
        return_type = None
        if self.current_token.type == TokenType.ARROW:
            self._advance()  # 消耗 '->'
            return_type = self._type_annotation()
        
        # 解析函數體
        if self.current_token.type != TokenType.LEFT_BRACE:
            self._error("預期 '{' 開始函數體")
        
        body = self._block_statement().statements
        
        return ast_nodes.FunctionExpression(params, return_type, body)

    def _parameter_list(self):
        """解析參數列表"""
        params = []
        
        # 空參數列表
        if self.current_token.type == TokenType.RIGHT_PAREN:
            return params
        
        # 解析第一個參數
        params.append(self._parameter())
        
        # 解析剩餘參數
        while self.current_token.type == TokenType.COMMA:
            self._advance()  # 消耗 ','
            
            # 處理尾隨逗號
            if self.current_token.type == TokenType.RIGHT_PAREN:
                break
            
            params.append(self._parameter())
        
        # 檢查參數列表中是否有默認值參數後出現無默認值參數
        has_default = False
        for param in params:
            if param.default_value is not None:
                has_default = True
            elif has_default:
                self._error("無默認值參數必須放在有默認值參數之前")
        
        return params

    def _parameter(self):
        """解析單個參數"""
        # 獲取參數名稱
        if self.current_token.type != TokenType.IDENTIFIER:
            self._error("預期參數名稱")
        
        name = self.current_token.lexeme
        self._advance()
        
        # 解析參數類型（可選）
        param_type = None
        if self.current_token.type == TokenType.COLON:
            self._advance()  # 消耗 ':'
            param_type = self._type_annotation()
        
        # 解析默認值（可選）
        default_value = None
        if self.current_token.type == TokenType.EQUAL:
            self._advance()  # 消耗 '='
            default_value = self._expression()
        
        return ast_nodes.Parameter(name, param_type, default_value)

    def _return_statement(self):
        """解析返回語句"""
        self._advance()  # 消耗 'return' 關鍵字
        
        # 如果後面沒有表達式，則為空返回
        if self.current_token.type in [TokenType.SEMICOLON, TokenType.RIGHT_BRACE]:
            return ast_nodes.ReturnStatement(None)
        
        # 解析返回值表達式
        value = self._expression()
        
        return ast_nodes.ReturnStatement(value)

    def _expression(self):
        """解析表達式"""
        if self.current_token.type == TokenType.SPAWN:
            return self._spawn_expression()
        elif self.current_token.type == TokenType.AWAIT:
            return self._await_expression()
        else:
            return self._assignment()

    def _spawn_expression(self):
        """解析spawn表達式，啟動併發任務"""
        self._advance()  # 消耗 'spawn' 關鍵字
        
        # spawn後必須跟著函數調用
        if self.current_token.type != TokenType.IDENTIFIER:
            self._error("預期函數名稱")
        
        # 保存函數名稱
        callee = ast_nodes.VariableExpression(self.current_token.lexeme)
        self._advance()
        
        # 解析函數調用
        if self.current_token.type != TokenType.LEFT_PAREN:
            self._error("預期 '(' 開始參數列表")
        
        call_expr = self._call_expression(callee)
        
        return ast_nodes.SpawnExpression(call_expr)

    def _await_expression(self):
        """解析await表達式，等待Future完成"""
        self._advance()  # 消耗 'await' 關鍵字
        
        # 解析等待的Future列表
        futures = [self._expression()]
        
        # 處理同時等待多個Future的情況
        while self.current_token.type == TokenType.COMMA:
            self._advance()  # 消耗 ','
            futures.append(self._expression())
        
        return ast_nodes.AwaitExpression(futures)

    def _binary_expression(self):
        """解析二元表達式"""
        left = self._unary_expression()
        if not left:
            return None
        
        return self._binary_expression_right(left, 0)
    
    def _binary_expression_right(self, left, min_precedence):
        """解析二元表達式右側"""
        token = self.peek()
        
        # 當前token不是運算符或優先級低於最小優先級時結束
        while token and self._is_operator(token) and self._get_operator_precedence(token) >= min_precedence:
            operator = self.consume()
            
            # 解析右側表達式
            right = self._unary_expression()
            if not right:
                self.report_error(f"期望表達式，但得到 {self.peek().lexeme if self.peek() else 'EOF'}")
                return None
            
            # 查看下一個運算符
            next_token = self.peek()
            
            # 如果下一個運算符優先級更高，先處理右側
            while (next_token and self._is_operator(next_token) and 
                   self._get_operator_precedence(next_token) > self._get_operator_precedence(operator)):
                right = self._binary_expression_right(right, self._get_operator_precedence(next_token))
                if not right:
                    return None
                next_token = self.peek()
            
            # 構建二元表達式
            left = BinaryExpression(left, operator, right)
            
            # 繼續檢查下一個運算符
            token = self.peek()
        
        return left
    
    def _is_operator(self, token):
        """判斷是否為運算符"""
        # 檢查是否是算術、比較或邏輯運算符
        return token and token.type in [
            TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH,
            TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL, 
            TokenType.GREATER, TokenType.GREATER_EQUAL,
            TokenType.LESS, TokenType.LESS_EQUAL,
            TokenType.LOGICAL_AND, TokenType.LOGICAL_OR
        ]
    
    def _get_operator_precedence(self, token):
        """獲取運算符優先級"""
        # 運算符優先級映射
        precedences = {
            TokenType.LOGICAL_OR: 1,      # 邏輯OR
            TokenType.LOGICAL_AND: 2,     # 邏輯AND
            
            TokenType.EQUAL_EQUAL: 3,  # 相等
            TokenType.BANG_EQUAL: 3,   # 不相等
            
            TokenType.LESS: 4,         # 小於
            TokenType.LESS_EQUAL: 4,   # 小於等於
            TokenType.GREATER: 4,      # 大於
            TokenType.GREATER_EQUAL: 4, # 大於等於
            
            TokenType.PLUS: 5,    # 加法
            TokenType.MINUS: 5,   # 減法
            
            TokenType.STAR: 6,    # 乘法
            TokenType.SLASH: 6,   # 除法
        }
        
        return precedences.get(token.type, 0) 