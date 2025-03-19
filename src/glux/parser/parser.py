"""
Glux 語言解析器
將詞法單元轉換為抽象語法樹
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from ..lexer.lexer import Token, TokenType
from . import ast_nodes
from .string_interpolation import StringInterpolationProcessor


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
        解析聲明
        
        Returns:
            聲明 AST 節點
        """
        # 解析函數聲明
        if self.match(TokenType.FN):
            return self.function_declaration()
        
        # 解析結構體聲明
        if self.match(TokenType.STRUCT):
            return self.struct_declaration()
        
        # 解析枚舉聲明
        if self.match(TokenType.ENUM):
            return self.enum_declaration()
        
        # 解析變量聲明
        if self.peek().type == TokenType.IDENTIFIER and self.peek_next().type == TokenType.COLONEQ:
            return self.var_declaration()
        
        # 解析常量聲明
        if self.match(TokenType.CONST):
            return self.const_declaration()
        
        # 其他類型的聲明...
        
        # 默認為表達式語句
        return self.statement()
    
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
        self.consume(TokenType.COLON, "期望 ':' 在參數名稱之後")
        param_type = self.type_expression()
        
        return ast_nodes.Parameter(name, param_type)
    
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
        self.consume(TokenType.COLONEQ, "期望 ':=' 在變量聲明中")
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
        return self.await_expression()
    
    def assignment(self) -> ast_nodes.Expression:
        """
        解析賦值表達式
        
        Returns:
            表達式 AST 節點
        """
        expr = self.logical_or()
        
        if self.match(TokenType.EQUAL):
            value = self.assignment()
            
            if isinstance(expr, ast_nodes.Variable):
                return ast_nodes.AssignmentExpression(expr.name, value)
            
            if isinstance(expr, ast_nodes.GetExpression):
                return ast_nodes.SetExpression(expr.object, expr.name, value)
            
            if isinstance(expr, ast_nodes.IndexExpression):
                return ast_nodes.IndexAssignmentExpression(expr.object, expr.index, value)
            
            self.error("無效的賦值目標")
        
        return expr
    
    def logical_or(self) -> ast_nodes.Expression:
        """解析邏輯或表達式"""
        expr = self.logical_and()
        
        while self.match(TokenType.OR, TokenType.LOGICAL_OR):
            operator = "or" if self.previous().type == TokenType.OR else "||"
            right = self.logical_and()
            expr = ast_nodes.LogicalExpression(expr, operator, right)
        
        # 解析三元運算符 (條件 ? 真值 : 假值)
        if self.match(TokenType.QUESTION):
            then_expr = self.expression()  # 解析條件為真時的表達式
            self.consume(TokenType.COLON, "期望 ':' 在三元運算符中")
            else_expr = self.logical_or()  # 解析條件為假時的表達式
            expr = ast_nodes.ConditionalExpression(expr, then_expr, else_expr)
        
        return expr
    
    def logical_and(self) -> ast_nodes.Expression:
        """
        解析邏輯與表達式
        
        Returns:
            表達式 AST 節點
        """
        expr = self.equality()
        
        while self.match(TokenType.AND, TokenType.LOGICAL_AND):
            right = self.equality()
            operator = "and" if self.previous().type == TokenType.AND else "&&"
            expr = ast_nodes.LogicalExpression(expr, operator, right)
        
        return expr
    
    def equality(self) -> ast_nodes.Expression:
        """
        解析相等性表達式
        
        Returns:
            表達式 AST 節點
        """
        expr = self.comparison()
        
        while self.match(TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL):
            operator = self.previous().lexeme
            right = self.comparison()
            expr = ast_nodes.BinaryExpr(expr, operator, right)
        
        return expr
    
    def comparison(self) -> ast_nodes.Expression:
        """
        解析比較表達式
        
        Returns:
            表達式 AST 節點
        """
        expr = self.term()
        
        # 記錄所有連續比較運算符和表達式
        operators = []
        expressions = [expr]
        
        while self.match(TokenType.LESS, TokenType.LESS_EQUAL, 
                        TokenType.GREATER, TokenType.GREATER_EQUAL):
            operators.append(self.previous().lexeme)
            expressions.append(self.term())
        
        # 如果沒有比較運算符，直接返回表達式
        if not operators:
            return expr
        
        # 如果只有一個比較運算符，創建簡單的二元運算表達式
        if len(operators) == 1:
            return ast_nodes.BinaryExpr(expressions[0], operators[0], expressions[1])
        
        # 處理連續比較運算（如 0 < x < 8）
        # 轉換為 0 < x && x < 8
        result = None
        for i in range(len(operators)):
            # 創建當前比較表達式
            comparison_expr = ast_nodes.BinaryExpr(
                expressions[i], operators[i], expressions[i+1]
            )
            
            if result is None:
                result = comparison_expr
            else:
                # 使用邏輯AND連接
                result = ast_nodes.LogicalExpression(result, "and", comparison_expr)
        
        return result
    
    def term(self) -> ast_nodes.Expression:
        """
        解析加減表達式
        
        Returns:
            表達式 AST 節點
        """
        expr = self.bitwise()
        
        while self.match(TokenType.PLUS, TokenType.MINUS):
            operator = self.previous().lexeme
            right = self.bitwise()
            expr = ast_nodes.BinaryExpr(expr, operator, right)
        
        return expr
    
    def bitwise(self) -> ast_nodes.Expression:
        """
        解析位元運算表達式 (&, |, ^, <<, >>)
        
        Returns:
            表達式 AST 節點
        """
        expr = self.factor()
        
        while self.match(TokenType.AMPERSAND, TokenType.PIPE, TokenType.CARET, 
                         TokenType.LEFT_SHIFT, TokenType.RIGHT_SHIFT):
            operator = self.previous().lexeme
            right = self.factor()
            expr = ast_nodes.BinaryExpr(expr, operator, right)
        
        return expr
    
    def factor(self) -> ast_nodes.Expression:
        """
        解析乘除表達式
        
        Returns:
            表達式 AST 節點
        """
        expr = self.unary()
        
        while self.match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            operator = self.previous().lexeme
            right = self.unary()
            expr = ast_nodes.BinaryExpr(expr, operator, right)
        
        return expr
    
    def unary(self) -> ast_nodes.Expression:
        """
        解析一元表達式
        
        Returns:
            表達式 AST 節點
        """
        if self.match(TokenType.BANG, TokenType.MINUS, TokenType.TILDE):
            operator = self.previous().lexeme
            right = self.unary()
            return ast_nodes.UnaryExpr(operator, right)
        
        return self.call()
    
    def call(self) -> ast_nodes.Expression:
        """解析函數調用表達式"""
        expr = self.primary()
        
        while True:
            if self.match(TokenType.LEFT_PAREN):
                expr = self.finish_call(expr)
            elif self.match(TokenType.DOT):
                # 處理元組成員訪問（如：results.0）
                if self.check(TokenType.NUMBER):
                    index = int(self.advance().lexeme)
                    expr = ast_nodes.GetExpression(expr, str(index))
                else:
                    name = self.consume(TokenType.IDENTIFIER, "期望屬性名稱").lexeme
                    expr = ast_nodes.GetExpression(expr, name)
            elif self.match(TokenType.LEFT_BRACKET):
                index = self.expression()
                self.consume(TokenType.RIGHT_BRACKET, "期望 ']' 在索引表達式之後")
                expr = ast_nodes.IndexExpression(expr, index)
            else:
                break
        
        return expr
    
    def finish_call(self, callee: ast_nodes.Expression) -> ast_nodes.CallExpression:
        """完成調用表達式的解析"""
        arguments = []
        
        if not self.check(TokenType.RIGHT_PAREN):
            arguments.append(self.expression())
            
            while self.match(TokenType.COMMA):
                arguments.append(self.expression())
        
        self.consume(TokenType.RIGHT_PAREN, "期望 ')' 在參數列表之後")
        
        return ast_nodes.CallExpression(callee, arguments)
    
    def primary(self) -> ast_nodes.Expression:
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
    
    # 輔助方法
    
    def match(self, *types) -> bool:
        """
        嘗試匹配當前詞法單元
        
        Args:
            *types: 詞法單元類型
            
        Returns:
            是否匹配
        """
        for type in types:
            if self.check(type):
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
        解析spawn表達式，例如：spawn work()
        
        Returns:
            spawn表達式 AST 節點
        """
        # 檢查是否為 spawn 表達式
        if not self.match(TokenType.SPAWN):
            return self.assignment()
            
        # 根據新的語法規範，spawn 必須直接後接函數調用
        # 例如：spawn work1()
        callee = self.primary()
        if not self.check(TokenType.LEFT_PAREN):
            self.error("spawn後必須接函數調用")
            return ast_nodes.ErrorExpression("spawn後必須接函數調用")
        
        # 解析函數調用
        self.consume(TokenType.LEFT_PAREN, "期望 '(' 在函數名稱之後")
        arguments = []
        if not self.check(TokenType.RIGHT_PAREN):
            arguments.append(self.assignment())
            
            while self.match(TokenType.COMMA):
                arguments.append(self.assignment())
        
        self.consume(TokenType.RIGHT_PAREN, "期望 ')' 在參數列表之後")
        
        call = ast_nodes.CallExpression(callee, arguments)
        return ast_nodes.SpawnExpression(call)
    
    def await_expression(self) -> ast_nodes.Expression:
        """
        解析await表達式，例如：await task1, task2
        
        Returns:
            await表達式 AST 節點
        """
        # 檢查是否為 await 表達式
        if not self.match(TokenType.AWAIT):
            return self.spawn_expression()
            
        # 解析等待的表達式列表
        expressions = []
        
        # 解析第一個表達式（任務變數）
        expressions.append(self.primary())
        
        # 解析後續表達式（如果有）
        while self.match(TokenType.COMMA):
            expressions.append(self.primary())
        
        # 創建 await 表達式節點
        return ast_nodes.AwaitExpression(expressions) 