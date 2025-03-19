"""
Glux 語言的抽象語法樹 (AST) 節點定義
"""

from typing import List, Dict, Optional, Union, Any, Tuple


class ASTNode:
    """AST 節點基類"""
    pass


class Module(ASTNode):
    """模組節點，表示整個程式"""
    def __init__(self, statements: List[ASTNode]):
        self.statements = statements  # 語句列表（可以是聲明或表達式語句）
        self.name = "main"  # 預設模組名稱

    def __repr__(self) -> str:
        return f"Module({self.name}, {len(self.statements)} statements)"


class Declaration(ASTNode):
    """聲明節點基類，用於變數、函數、結構體等聲明"""
    pass


class Statement(ASTNode):
    """語句節點基類"""
    pass


class Expression(ASTNode):
    """表達式節點基類"""
    pass


class Literal(Expression):
    """字面量節點基類"""
    pass


class TypeExpression(ASTNode):
    """類型表達式節點基類"""
    def __init__(self, type_name: str):
        self.type_name = type_name
    
    def __repr__(self) -> str:
        return self.type_name


class GenericTypeExpression(TypeExpression):
    """泛型類型表達式，例如 List<T>"""
    def __init__(self, type_name: str, type_params: list):
        super().__init__(type_name)
        self.type_params = type_params
    
    def __repr__(self) -> str:
        params_str = ", ".join(str(param) for param in self.type_params)
        return f"{self.type_name}<{params_str}>"


class PointerTypeExpression(TypeExpression):
    """指針類型表達式，例如 *int"""
    def __init__(self, base_type: TypeExpression):
        super().__init__("*")
        self.base_type = base_type
    
    def __repr__(self) -> str:
        return f"*{self.base_type}"


class OptionalTypeExpression(TypeExpression):
    """可選類型表達式，例如 optional<int>"""
    def __init__(self, inner_type: TypeExpression):
        super().__init__("optional")
        self.inner_type = inner_type
    
    def __repr__(self) -> str:
        return f"optional<{self.inner_type}>"


class UnionTypeExpression(TypeExpression):
    """聯合類型表達式，例如 union<int, string>"""
    def __init__(self, types: list):
        super().__init__("union")
        self.types = types
    
    def __repr__(self) -> str:
        types_str = ", ".join(str(t) for t in self.types)
        return f"union<{types_str}>"


class ErrorTypeExpression(TypeExpression):
    """錯誤類型表達式，用於錯誤恢復"""
    def __init__(self, message: str = "類型錯誤"):
        super().__init__("ERROR")
        self.message = message
    
    def __repr__(self) -> str:
        return f"ERROR_TYPE: {self.message}"


class NamedTypeExpression(TypeExpression):
    """命名類型表達式，例如 int, string"""
    def __init__(self, type_name: str):
        self.type_name = type_name
        self.name = type_name  # 添加 name 屬性
    
    def __repr__(self) -> str:
        return self.type_name


class ArrayTypeExpression(TypeExpression):
    """數組類型表達式，例如 [10]int"""
    def __init__(self, element_type: TypeExpression, size: Optional[int] = None):
        super().__init__("array")
        self.element_type = element_type
        self.size = size
    
    def __repr__(self) -> str:
        if self.size is None:
            return f"[]{self.element_type}"
        else:
            return f"[{self.size}]{self.element_type}"


class TupleTypeExpression(TypeExpression):
    """元組類型表達式，例如 (int, string)"""
    def __init__(self, element_types: list):
        super().__init__("tuple")
        self.element_types = element_types
    
    def __repr__(self) -> str:
        types_str = ", ".join(str(t) for t in self.element_types)
        return f"({types_str})"


class FunctionTypeExpression(TypeExpression):
    """函數類型表達式，例如 fn(int, string) -> bool"""
    def __init__(self, param_types: list, return_type: TypeExpression):
        super().__init__("function")
        self.param_types = param_types
        self.return_type = return_type
    
    def __repr__(self) -> str:
        params_str = ", ".join(str(p) for p in self.param_types)
        return f"fn({params_str}) -> {self.return_type}"


class ExpressionStatement(Statement):
    """表達式語句"""
    def __init__(self, expression: Expression):
        self.expression = expression

    def __repr__(self) -> str:
        return f"{self.expression};"


class VarDeclaration(Declaration):
    """變數聲明"""
    def __init__(self, name: str, value: Expression, type_hint: Optional[TypeExpression] = None):
        self.name = name  # 變數名稱
        self.value = value  # 初始值
        self.type_hint = type_hint  # 類型提示

    def __repr__(self) -> str:
        type_str = f": {self.type_hint}" if self.type_hint else ""
        return f"var {self.name}{type_str} = {self.value};"


class ConstDeclaration(Declaration):
    """常量聲明"""
    def __init__(self, name: str, value: Expression, type_hint: Optional[TypeExpression] = None):
        self.name = name  # 常量名稱
        self.value = value  # 值
        self.type_hint = type_hint  # 類型提示

    def __repr__(self) -> str:
        type_str = f": {self.type_hint}" if self.type_hint else ""
        return f"const {self.name}{type_str} = {self.value};"


class FunctionDeclaration(Declaration):
    """函數聲明"""
    def __init__(self, name: str, params: List['Parameter'], body: List[Statement], return_type: Optional[TypeExpression] = None):
        self.name = name  # 函數名稱
        self.params = params  # 參數列表
        self.body = body  # 函數體
        self.return_type = return_type  # 返回類型

    def __repr__(self) -> str:
        params_str = ", ".join(map(str, self.params))
        return_str = f" -> {self.return_type}" if self.return_type else ""
        return f"fn {self.name}({params_str}){return_str} {{ ... }}"


class StructDeclaration(Declaration):
    """結構體聲明節點"""
    
    def __init__(self, name: str, fields: List['StructField'], methods: List['MethodDeclaration'] = None, parent: str = None):
        """
        初始化結構體聲明節點
        
        Args:
            name: 結構體名稱
            fields: 欄位列表
            methods: 方法列表
            parent: 父結構體名稱（繼承）
        """
        super().__init__()
        self.name = name
        self.fields = fields
        self.methods = methods or []
        self.parent = parent
    
    def accept(self, visitor):
        return visitor.visit_struct_declaration(self)


class StructField:
    """結構體欄位節點"""
    
    def __init__(self, name: str, type_annotation, is_override: bool = False):
        """
        初始化結構體欄位節點
        
        Args:
            name: 欄位名稱
            type_annotation: 類型標註
            is_override: 是否覆寫父結構體的欄位
        """
        self.name = name
        self.type_annotation = type_annotation
        self.is_override = is_override
    
    def accept(self, visitor):
        return visitor.visit_struct_field(self)


class MethodDeclaration(Declaration):
    """方法聲明節點"""
    
    def __init__(self, name: str, parameters: List['Parameter'], return_type, body: List['Statement'], receiver_type: str = None, is_override: bool = False):
        """
        初始化方法聲明節點
        
        Args:
            name: 方法名稱
            parameters: 參數列表
            return_type: 返回類型
            body: 方法體
            receiver_type: 接收者類型（結構體名稱）
            is_override: 是否覆寫父結構體或接口的方法
        """
        super().__init__()
        self.name = name
        self.parameters = parameters
        self.return_type = return_type
        self.body = body
        self.receiver_type = receiver_type
        self.is_override = is_override
    
    def accept(self, visitor):
        return visitor.visit_method_declaration(self)


class EnumDeclaration(Declaration):
    """枚舉聲明"""
    def __init__(self, name: str, variants: List[str], values: Optional[List[Any]] = None):
        self.name = name  # 枚舉名稱
        self.variants = variants  # 變體名稱列表
        self.values = values or []  # 變體值列表(如果有)

    def __repr__(self) -> str:
        variants_str = ", ".join(self.variants)
        return f"enum {self.name} {{ {variants_str} }}"


class CallExpression(Expression):
    """函數呼叫表達式"""
    def __init__(self, callee: Expression, arguments: List[Expression], keywords: Optional[Dict[str, Expression]] = None):
        self.callee = callee  # 被呼叫的函數
        self.arguments = arguments  # 位置參數
        self.keywords = keywords or {}  # 關鍵字參數

    def __repr__(self) -> str:
        args_str = ", ".join(map(str, self.arguments))
        keywords_str = ", ".join(f"{k}={v}" for k, v in self.keywords.items())
        all_args = [args_str, keywords_str] if keywords_str else [args_str]
        return f"{self.callee}({', '.join(filter(bool, all_args))})"


class Type(ASTNode):
    """類型節點，用於表示變數的類型"""
    def __init__(self, name: str, subtypes: Optional[List['Type']] = None):
        self.name = name  # 如 'int', 'string', 'list' 等
        self.subtypes = subtypes or []  # 如 list<int> 中的 int

    def __repr__(self) -> str:
        if self.subtypes:
            return f"{self.name}<{', '.join(map(str, self.subtypes))}>"
        return self.name


class Number(Literal):
    """整數字面量"""
    def __init__(self, value: str):
        self.value = value
        # 自動判斷整數大小類別 (int8, int16, int32, int64)
        self.type = "int"  # 預設類型
        self.determine_type()

    def determine_type(self) -> None:
        """根據數字大小自動判斷整數類型"""
        value = int(self.value)
        if -128 <= value <= 127:
            self.type = "int8"
        elif -32768 <= value <= 32767:
            self.type = "int16"
        elif -2147483648 <= value <= 2147483647:
            self.type = "int32"
        else:
            self.type = "int64"

    def __repr__(self) -> str:
        return f"Number({self.value}:{self.type})"


class Float(Literal):
    """浮點數字面量"""
    def __init__(self, value: str):
        self.value = value
        # 自動判斷 float32 或 float64
        self.type = "float32"  # 預設使用 float32
        # 未來可以根據精度需求自動選擇 float32 或 float64

    def __repr__(self) -> str:
        return f"Float({self.value}:{self.type})"


class StringLiteral(Literal):
    """字串字面量"""
    def __init__(self, value: str, is_raw: bool = False):
        self.value = value
        self.is_raw = is_raw  # 是否為原始字串（使用反引號）

    def __repr__(self) -> str:
        prefix = "r" if self.is_raw else ""
        return f"{prefix}String({repr(self.value)})"


class StringInterpolation(ASTNode):
    """字串插值表達式，如 `Hello, ${name}!`"""
    def __init__(self, parts: List[ASTNode], is_raw: bool = True):
        self.parts = parts  # 字串片段列表，可能包含字面量和表達式
        self.is_raw = is_raw  # 是否為原始字串（通常插值字串使用反引號）

    def __repr__(self) -> str:
        parts_str = ", ".join(map(str, self.parts))
        return f"StringInterpolation([{parts_str}])"


class Boolean(Literal):
    """布爾值字面量"""
    def __init__(self, value: str):
        self.value = value == "true"

    def __repr__(self) -> str:
        return f"Boolean({self.value})"


class Variable(ASTNode):
    """變數引用"""
    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return f"Variable({self.name})"


class Assign(ASTNode):
    """變數賦值表達式"""
    def __init__(self, name: str, value: ASTNode, type_hint: Optional[Type] = None):
        self.name = name  # 變數名稱
        self.value = value  # 賦值表達式
        self.type_hint = type_hint  # 可選類型提示

    def __repr__(self) -> str:
        type_str = f": {self.type_hint}" if self.type_hint else ""
        return f"Assign({self.name}{type_str} := {self.value})"


class ConstDecl(ASTNode):
    """常數聲明"""
    def __init__(self, name: str, value: ASTNode, type_hint: Optional[Type] = None):
        self.name = name  # 常數名稱
        self.value = value  # 值表達式
        self.type_hint = type_hint  # 可選類型提示

    def __repr__(self) -> str:
        type_str = f": {self.type_hint}" if self.type_hint else ""
        return f"ConstDecl({self.name}{type_str} = {self.value})"


class BinaryOp(ASTNode):
    """二元運算表達式"""
    def __init__(self, left: ASTNode, op: str, right: ASTNode):
        self.left = left
        self.op = op
        self.right = right

    def __repr__(self) -> str:
        return f"({self.left} {self.op} {self.right})"


class UnaryOp(ASTNode):
    """一元運算表達式"""
    def __init__(self, op: str, operand: ASTNode):
        self.op = op
        self.operand = operand

    def __repr__(self) -> str:
        return f"({self.op} {self.operand})"


class GroupingExpression(ASTNode):
    """括號分組表達式"""
    def __init__(self, expression: ASTNode):
        self.expression = expression

    def __repr__(self) -> str:
        return f"({self.expression})"


class FunctionCall(ASTNode):
    """函式呼叫表達式"""
    def __init__(self, name: str, args: List[ASTNode], keywords: Optional[Dict[str, ASTNode]] = None):
        self.name = name  # 函式名稱
        self.args = args  # 位置參數
        self.keywords = keywords or {}  # 關鍵字參數

    def __repr__(self) -> str:
        args_str = ", ".join(map(str, self.args))
        keywords_str = ", ".join(f"{k}={v}" for k, v in self.keywords.items())
        all_args = [args_str, keywords_str] if keywords_str else [args_str]
        return f"{self.name}({', '.join(filter(bool, all_args))})"


class Parameter(ASTNode):
    """函式參數"""
    def __init__(self, name: str, type_hint: Optional[Type] = None, default_value: Optional[ASTNode] = None):
        self.name = name  # 參數名稱
        self.type_hint = type_hint  # 類型提示
        self.default_value = default_value  # 預設值

    def __repr__(self) -> str:
        type_str = f": {self.type_hint}" if self.type_hint else ""
        default_str = f" = {self.default_value}" if self.default_value is not None else ""
        return f"{self.name}{type_str}{default_str}"


class FunctionDef(ASTNode):
    """函式定義"""
    def __init__(self, name: str, params: List[Parameter], body: List[ASTNode], return_type: Optional[Type] = None):
        self.name = name  # 函式名稱
        self.params = params  # 參數列表
        self.body = body  # 函式體
        self.return_type = return_type  # 返回類型

    def __repr__(self) -> str:
        params_str = ", ".join(map(str, self.params))
        return_str = f" -> {self.return_type}" if self.return_type else ""
        return f"fn {self.name}({params_str}){return_str} {{ ... }}"


class Return(ASTNode):
    """return 語句"""
    def __init__(self, value: Optional[ASTNode] = None):
        self.value = value  # 返回值表達式

    def __repr__(self) -> str:
        return f"return {self.value}" if self.value else "return"


class If(ASTNode):
    """if 語句"""
    def __init__(self, condition: ASTNode, body: List[ASTNode], else_body: Optional[List[ASTNode]] = None):
        self.condition = condition  # 條件表達式
        self.body = body  # if 區塊
        self.else_body = else_body  # else 區塊（可能是 None 或另一個 If 節點）

    def __repr__(self) -> str:
        else_str = f" else {{ ... }}" if self.else_body else ""
        return f"if {self.condition} {{ ... }}{else_str}"


class While(ASTNode):
    """while 循環"""
    def __init__(self, condition: ASTNode, body: List[ASTNode]):
        self.condition = condition  # 條件表達式
        self.body = body  # 循環體

    def __repr__(self) -> str:
        return f"while {self.condition} {{ ... }}"


class For(ASTNode):
    """for 循環"""
    def __init__(self, iterator: Union[str, List[str]], iterable: ASTNode, body: List[ASTNode]):
        self.iterator = iterator  # 迭代變量 (可能是單個名稱或多個名稱)
        self.iterable = iterable  # 可迭代物件
        self.body = body  # 循環體

    def __repr__(self) -> str:
        if isinstance(self.iterator, list):
            iter_str = ", ".join(self.iterator)
        else:
            iter_str = self.iterator
        return f"for {iter_str} in {self.iterable} {{ ... }}"


class Field(ASTNode):
    """結構體欄位"""
    def __init__(self, name: str, type_hint: Type, default_value: Optional[ASTNode] = None, is_override: bool = False):
        self.name = name  # 欄位名稱
        self.type_hint = type_hint  # 類型提示
        self.default_value = default_value  # 預設值
        self.is_override = is_override  # 是否覆寫父結構體欄位

    def __repr__(self) -> str:
        override_str = "override " if self.is_override else ""
        default_str = f" = {self.default_value}" if self.default_value is not None else ""
        return f"{override_str}{self.name}: {self.type_hint}{default_str}"


class InterfaceDef(ASTNode):
    """介面定義"""
    def __init__(self, name: str, methods: List['MethodSignature'], parents: Optional[List[str]] = None):
        self.name = name  # 介面名稱
        self.methods = methods  # 方法列表
        self.parents = parents or []  # 父介面清單 (繼承)

    def __repr__(self) -> str:
        parents_str = f" extends {', '.join(self.parents)}" if self.parents else ""
        return f"interface {self.name}{parents_str} {{ ... }}"


class MethodSignature(ASTNode):
    """介面方法簽名"""
    def __init__(self, name: str, params: List[Parameter], return_type: Optional[Type] = None):
        self.name = name  # 方法名稱
        self.params = params  # 參數列表
        self.return_type = return_type  # 返回類型

    def __repr__(self) -> str:
        params_str = ", ".join(map(str, self.params))
        return_str = f" -> {self.return_type}" if self.return_type else ""
        return f"{self.name}({params_str}){return_str}"


class ListLiteral(Literal):
    """列表字面量"""
    def __init__(self, elements: List[ASTNode]):
        self.elements = elements  # 元素列表

    def __repr__(self) -> str:
        return f"[{', '.join(map(str, self.elements))}]"


class MapLiteral(Literal):
    """映射字面量"""
    def __init__(self, pairs: List[Tuple]):
        self.pairs = pairs  # 映射鍵值對

    def __repr__(self) -> str:
        return f"{{{', '.join(f'{k}: {v}' for k, v in self.pairs)}}}"


class Tuple(Literal):
    """元組字面量"""
    def __init__(self, elements: List[ASTNode]):
        self.elements = elements  # 元素列表

    def __repr__(self) -> str:
        return f"({', '.join(map(str, self.elements))})"


class ErrorLiteral(Literal):
    """錯誤字面量"""
    def __init__(self, message: ASTNode):
        self.message = message  # 錯誤訊息

    def __repr__(self) -> str:
        return f"error({repr(self.message)})"


class SpawnExpr(ASTNode):
    """併發執行 (spawn) 表達式"""
    def __init__(self, function_call: Union[FunctionCall, FunctionDef]):
        self.function_call = function_call  # 函數呼叫表達式或函數定義

    def __repr__(self) -> str:
        return f"spawn {self.function_call}"


class AwaitExpr(ASTNode):
    """等待表達式"""
    def __init__(self, expressions: List[ASTNode]):
        self.expressions = expressions  # 要等待的表達式列表

    def __repr__(self) -> str:
        return f"await {', '.join(map(str, self.expressions))}"


class UnsafeBlock(ASTNode):
    """不安全區塊"""
    def __init__(self, body: List[ASTNode]):
        self.body = body  # 區塊內的語句

    def __repr__(self) -> str:
        return "unsafe { ... }"


class PtrExpr(ASTNode):
    """指標表達式"""
    def __init__(self, expr: ASTNode):
        self.expr = expr  # 表達式

    def __repr__(self) -> str:
        return f"&{self.expr}"


class DerefExpr(ASTNode):
    """解參考表達式"""
    def __init__(self, expr: ASTNode):
        self.expr = expr  # 表達式

    def __repr__(self) -> str:
        return f"*{self.expr}"


class BlockStatement(ASTNode):
    """代碼區塊，用於分組語句"""
    def __init__(self, statements: List[ASTNode]):
        self.statements = statements  # 語句列表

    def __repr__(self) -> str:
        return "{ ... }"


class MemberAccess(ASTNode):
    """成員存取表達式"""
    def __init__(self, object: ASTNode, member: str):
        self.object = object  # 對象
        self.member = member  # 成員名稱

    def __repr__(self) -> str:
        return f"{self.object}.{self.member}"


class IndexAccess(ASTNode):
    """索引存取表達式"""
    def __init__(self, object: ASTNode, index: ASTNode):
        self.object = object  # 對象
        self.index = index  # 索引表達式

    def __repr__(self) -> str:
        return f"{self.object}[{self.index}]"


class ComparisonChain(ASTNode):
    """連續比較表達式，如 0 < x < 10"""
    def __init__(self, left: ASTNode, comparisons: List[Tuple]):
        self.left = left  # 左側表達式
        self.comparisons = comparisons  # 比較運算符和右側表達式的列表

    def __repr__(self) -> str:
        result = str(self.left)
        for op, right in self.comparisons:
            result += f" {op} {right}"
        return f"({result})"


class BreakStatement(ASTNode):
    """break 語句"""
    def __repr__(self) -> str:
        return "break"


class ContinueStatement(ASTNode):
    """continue 語句"""
    def __repr__(self) -> str:
        return "continue"


class BooleanLiteral(ASTNode):
    """布爾值字面量"""
    def __init__(self, value: str):
        self.value = value == "true"

    def __repr__(self) -> str:
        return f"Boolean({self.value})"


# 為了向後兼容性，提供類型別名
IfStatement = If
WhileStatement = While
ForStatement = For
ReturnStatement = Return
ImportDeclaration = Declaration  # 暫時使用基類
CallExpr = CallExpression
BinaryExpr = BinaryOp
UnaryExpr = UnaryOp
MemberAccessExpr = MemberAccess
IndexAccessExpr = IndexAccess
AssignmentExpr = Assign
ComparisonChainExpr = ComparisonChain
Variable = Variable  # 保持一致性
StringLiteral = StringLiteral
BooleanLiteral = Boolean
NumberLiteral = Number
IntLiteral = Number  # 添加 IntLiteral 作為 Number 的別名
FloatLiteral = Float
ListLiteral = ListLiteral  # 保持一致性

class GetExpression(ASTNode):
    """屬性訪問表達式"""
    def __init__(self, object: ASTNode, name: str):
        self.object = object
        self.name = name
    
    def __repr__(self) -> str:
        return f"{self.object}.{self.name}"


class SetExpression(ASTNode):
    """屬性賦值表達式"""
    def __init__(self, object: ASTNode, name: str, value: ASTNode):
        self.object = object
        self.name = name
        self.value = value
    
    def __repr__(self) -> str:
        return f"{self.object}.{self.name} = {self.value}"


class IndexExpression(ASTNode):
    """索引訪問表達式"""
    def __init__(self, object: ASTNode, index: ASTNode):
        self.object = object
        self.index = index
    
    def __repr__(self) -> str:
        return f"{self.object}[{self.index}]"


class IndexAssignmentExpression(ASTNode):
    """索引賦值表達式"""
    def __init__(self, object: ASTNode, index: ASTNode, value: ASTNode):
        self.object = object
        self.index = index
        self.value = value
    
    def __repr__(self) -> str:
        return f"{self.object}[{self.index}] = {self.value}"


class AssignmentExpression(ASTNode):
    """變數賦值表達式"""
    def __init__(self, name: str, value: ASTNode):
        self.name = name
        self.value = value
    
    def __repr__(self) -> str:
        return f"{self.name} = {self.value}"


class UnsafeBlockStatement(Statement):
    """unsafe 區塊語句，用於執行不安全操作"""
    def __init__(self, statements: List[Statement]):
        self.statements = statements  # 區塊中的語句

    def __repr__(self) -> str:
        return f"unsafe {{ ... }}"


# 添加併發相關的AST節點

class SpawnExpression(Expression):
    """併發任務生成表達式節點"""
    
    def __init__(self, function_call):
        """
        初始化併發任務生成表達式節點
        
        Args:
            function_call: 函數調用表達式
        """
        super().__init__()
        self.function_call = function_call
    
    def __repr__(self) -> str:
        return f"spawn {self.function_call}"

class AwaitExpression(Expression):
    """等待併發任務完成表達式節點"""
    
    def __init__(self, expressions):
        """
        初始化等待併發任務完成表達式節點
        
        Args:
            expressions: 要等待的表達式列表
        """
        super().__init__()
        self.expressions = expressions
    
    def __repr__(self) -> str:
        exprs = ", ".join(repr(expr) for expr in self.expressions)
        return f"await {exprs}"

class ErrorExpression(Expression):
    """表達式錯誤的佔位符"""
    
    def __init__(self, message: str):
        """
        初始化錯誤表達式節點
        
        Args:
            message: 錯誤訊息
        """
        super().__init__()
        self.message = message
    
    def __repr__(self) -> str:
        return f"ERROR: {self.message}"

class LogicalExpression(Expression):
    """邏輯表達式節點"""
    
    def __init__(self, left: Expression, operator: str, right: Expression):
        """
        初始化邏輯表達式節點
        
        Args:
            left: 左側表達式
            operator: 運算符（"and" 或 "or"）
            right: 右側表達式
        """
        super().__init__()
        self.left = left
        self.operator = operator
        self.right = right
    
    def __repr__(self) -> str:
        return f"({self.left} {self.operator} {self.right})"


class BinaryExpr(Expression):
    """二元運算表達式節點"""
    
    def __init__(self, left: Expression, operator: str, right: Expression):
        """
        初始化二元運算表達式節點
        
        Args:
            left: 左側表達式
            operator: 運算符
            right: 右側表達式
        """
        super().__init__()
        self.left = left
        self.operator = operator
        self.right = right
    
    def __repr__(self) -> str:
        return f"({self.left} {self.operator} {self.right})"


class UnaryExpr(Expression):
    """一元運算表達式節點"""
    
    def __init__(self, operator: str, operand: Expression):
        """
        初始化一元運算表達式節點
        
        Args:
            operator: 運算符
            operand: 操作數
        """
        super().__init__()
        self.operator = operator
        self.operand = operand
    
    def __repr__(self) -> str:
        return f"{self.operator}({self.operand})"


class ConditionalExpression(Expression):
    """條件表達式（三元運算符）節點"""
    
    def __init__(self, condition: Expression, then_expr: Expression, else_expr: Expression):
        """
        初始化條件表達式節點
        
        Args:
            condition: 條件表達式
            then_expr: 條件為真時的表達式
            else_expr: 條件為假時的表達式
        """
        super().__init__()
        self.condition = condition
        self.then_expr = then_expr
        self.else_expr = else_expr
    
    def __repr__(self) -> str:
        return f"({self.condition} ? {self.then_expr} : {self.else_expr})" 