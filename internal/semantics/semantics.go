package semantics

import (
	"fmt"
	"glux/internal/ast"
)

// Type 表示 Glux 程式中的類型
type Type interface {
	String() string
}

// 基本類型
type (
	IntType struct {
		BitSize int // 8, 16, 32, 64
	}

	FloatType struct {
		BitSize int // 32, 64
	}

	BoolType   struct{}
	StringType struct{}
	NullType   struct{}
	AnyType    struct{}
	ErrorType  struct{}
)

func (t *IntType) String() string {
	return fmt.Sprintf("int%d", t.BitSize)
}

func (t *FloatType) String() string {
	return fmt.Sprintf("float%d", t.BitSize)
}

func (t *BoolType) String() string {
	return "bool"
}

func (t *StringType) String() string {
	return "string"
}

func (t *NullType) String() string {
	return "null"
}

func (t *AnyType) String() string {
	return "any"
}

func (t *ErrorType) String() string {
	return "error"
}

// 複合類型
type (
	ListType struct {
		ElementType Type
	}

	ArrayType struct {
		ElementType Type
		Size        int
	}

	MapType struct {
		KeyType   Type
		ValueType Type
	}

	TupleType struct {
		ElementTypes []Type
	}

	FunctionType struct {
		ParameterTypes []Type
		ReturnType     Type
	}

	StructType struct {
		Name   string
		Fields map[string]Type
	}

	InterfaceType struct {
		Name    string
		Methods map[string]*FunctionType
	}

	UnionType struct {
		Types []Type
	}

	PointerType struct {
		BaseType Type
	}

	OptionalType struct {
		BaseType Type
	}

	FutureType struct {
		ResultType Type
	}
)

func (t *ListType) String() string {
	return fmt.Sprintf("list<%s>", t.ElementType.String())
}

func (t *ArrayType) String() string {
	return fmt.Sprintf("array<%s, %d>", t.ElementType.String(), t.Size)
}

func (t *MapType) String() string {
	return fmt.Sprintf("map<%s, %s>", t.KeyType.String(), t.ValueType.String())
}

func (t *TupleType) String() string {
	result := "("
	for i, elemType := range t.ElementTypes {
		if i > 0 {
			result += ", "
		}
		result += elemType.String()
	}
	result += ")"
	return result
}

func (t *FunctionType) String() string {
	result := "fn("
	for i, paramType := range t.ParameterTypes {
		if i > 0 {
			result += ", "
		}
		result += paramType.String()
	}
	result += ") -> " + t.ReturnType.String()
	return result
}

func (t *StructType) String() string {
	return t.Name
}

func (t *InterfaceType) String() string {
	return t.Name
}

func (t *UnionType) String() string {
	result := "union<"
	for i, unionType := range t.Types {
		if i > 0 {
			result += ", "
		}
		result += unionType.String()
	}
	result += ">"
	return result
}

func (t *PointerType) String() string {
	return fmt.Sprintf("ptr<%s>", t.BaseType.String())
}

func (t *OptionalType) String() string {
	return fmt.Sprintf("optional<%s>", t.BaseType.String())
}

func (t *FutureType) String() string {
	return fmt.Sprintf("Future<%s>", t.ResultType.String())
}

// 符號表相關結構
type SymbolScope string

const (
	GlobalScope   SymbolScope = "GLOBAL"
	FunctionScope SymbolScope = "FUNCTION"
	BlockScope    SymbolScope = "BLOCK"
)

type Symbol struct {
	Name  string
	Type  Type
	Scope SymbolScope
}

type SymbolTable struct {
	Outer    *SymbolTable
	Symbols  map[string]*Symbol
	Scope    SymbolScope
	TypeDefs map[string]Type
}

func NewSymbolTable() *SymbolTable {
	s := &SymbolTable{
		Symbols:  make(map[string]*Symbol),
		TypeDefs: make(map[string]Type),
		Scope:    GlobalScope,
	}
	return s
}

func NewEnclosedSymbolTable(outer *SymbolTable) *SymbolTable {
	s := NewSymbolTable()
	s.Outer = outer
	if outer.Scope == GlobalScope {
		s.Scope = FunctionScope
	} else {
		s.Scope = BlockScope
	}
	return s
}

func (s *SymbolTable) Define(name string, t Type) *Symbol {
	symbol := &Symbol{Name: name, Type: t, Scope: s.Scope}
	s.Symbols[name] = symbol
	return symbol
}

func (s *SymbolTable) Resolve(name string) (*Symbol, bool) {
	symbol, ok := s.Symbols[name]
	if !ok && s.Outer != nil {
		symbol, ok = s.Outer.Resolve(name)
	}
	return symbol, ok
}

func (s *SymbolTable) DefineType(name string, t Type) {
	s.TypeDefs[name] = t
}

func (s *SymbolTable) ResolveType(name string) (Type, bool) {
	t, ok := s.TypeDefs[name]
	if !ok && s.Outer != nil {
		t, ok = s.Outer.ResolveType(name)
	}
	return t, ok
}

// TypeChecker 用於檢查 AST 的類型一致性
type TypeChecker struct {
	errors      []string
	symbolTable *SymbolTable
}

func NewTypeChecker() *TypeChecker {
	return &TypeChecker{
		errors:      []string{},
		symbolTable: NewSymbolTable(),
	}
}

func (tc *TypeChecker) addError(format string, a ...interface{}) {
	tc.errors = append(tc.errors, fmt.Sprintf(format, a...))
}

// Check 檢查 AST 的語意正確性
func Check(program *ast.Program) error {
	checker := NewTypeChecker()

	// 註冊內置類型
	checker.symbolTable.DefineType("int", &IntType{BitSize: 32})
	checker.symbolTable.DefineType("int8", &IntType{BitSize: 8})
	checker.symbolTable.DefineType("int16", &IntType{BitSize: 16})
	checker.symbolTable.DefineType("int32", &IntType{BitSize: 32})
	checker.symbolTable.DefineType("int64", &IntType{BitSize: 64})
	checker.symbolTable.DefineType("float", &FloatType{BitSize: 32})
	checker.symbolTable.DefineType("float32", &FloatType{BitSize: 32})
	checker.symbolTable.DefineType("float64", &FloatType{BitSize: 64})
	checker.symbolTable.DefineType("bool", &BoolType{})
	checker.symbolTable.DefineType("string", &StringType{})
	checker.symbolTable.DefineType("null", &NullType{})
	checker.symbolTable.DefineType("any", &AnyType{})
	checker.symbolTable.DefineType("error", &ErrorType{})

	// 註冊內置函式
	checker.symbolTable.Define("print", &FunctionType{
		ParameterTypes: []Type{&AnyType{}},
		ReturnType:     &NullType{},
	})
	checker.symbolTable.Define("println", &FunctionType{
		ParameterTypes: []Type{&AnyType{}},
		ReturnType:     &NullType{},
	})
	checker.symbolTable.Define("len", &FunctionType{
		ParameterTypes: []Type{&AnyType{}},
		ReturnType:     &IntType{BitSize: 32},
	})
	checker.symbolTable.Define("copy", &FunctionType{
		ParameterTypes: []Type{&AnyType{}},
		ReturnType:     &AnyType{},
	})
	checker.symbolTable.Define("string", &FunctionType{
		ParameterTypes: []Type{&AnyType{}},
		ReturnType:     &StringType{},
	})
	checker.symbolTable.Define("int", &FunctionType{
		ParameterTypes: []Type{&AnyType{}},
		ReturnType:     &IntType{BitSize: 32},
	})
	checker.symbolTable.Define("float", &FunctionType{
		ParameterTypes: []Type{&AnyType{}},
		ReturnType:     &FloatType{BitSize: 32},
	})
	checker.symbolTable.Define("bool", &FunctionType{
		ParameterTypes: []Type{&AnyType{}},
		ReturnType:     &BoolType{},
	})
	checker.symbolTable.Define("error", &FunctionType{
		ParameterTypes: []Type{&StringType{}},
		ReturnType:     &ErrorType{},
	})
	checker.symbolTable.Define("is_error", &FunctionType{
		ParameterTypes: []Type{&AnyType{}},
		ReturnType:     &BoolType{},
	})
	checker.symbolTable.Define("range", &FunctionType{
		ParameterTypes: []Type{&IntType{BitSize: 32}},
		ReturnType:     &ListType{ElementType: &IntType{BitSize: 32}},
	})
	checker.symbolTable.Define("sleep", &FunctionType{
		ParameterTypes: []Type{&IntType{BitSize: 32}},
		ReturnType:     &NullType{},
	})

	// 進行語意分析
	for _, stmt := range program.Statements {
		checker.checkStatement(stmt)
	}

	if program.MainBlock != nil {
		// 檢查 main 區塊
		blockSymbolTable := NewEnclosedSymbolTable(checker.symbolTable)
		oldSymbolTable := checker.symbolTable
		checker.symbolTable = blockSymbolTable

		for _, stmt := range program.MainBlock.Statements {
			checker.checkStatement(stmt)
		}

		checker.symbolTable = oldSymbolTable
	}

	if len(checker.errors) > 0 {
		errorMsg := "Semantic errors:\n"
		for _, err := range checker.errors {
			errorMsg += "- " + err + "\n"
		}
		return fmt.Errorf("%s", errorMsg)
	}

	return nil
}

// 以下是針對不同語句和表達式的具體檢查方法

func (tc *TypeChecker) checkStatement(stmt ast.Statement) Type {
	switch s := stmt.(type) {
	case *ast.VarStatement:
		return tc.checkVarStatement(s)
	case *ast.ConstStatement:
		return tc.checkConstStatement(s)
	case *ast.ReturnStatement:
		return tc.checkReturnStatement(s)
	case *ast.ExpressionStatement:
		return tc.checkExpression(s.Expression)
	case *ast.BlockStatement:
		return tc.checkBlockStatement(s)
	case *ast.IfStatement:
		return tc.checkIfStatement(s)
	case *ast.WhileStatement:
		return tc.checkWhileStatement(s)
	case *ast.ForStatement:
		return tc.checkForStatement(s)
	case *ast.FunctionDefinition:
		return tc.checkFunctionDefinition(s)
	case *ast.StructStatement:
		return tc.checkStructStatement(s)
	case *ast.InterfaceStatement:
		return tc.checkInterfaceStatement(s)
	case *ast.UnsafeBlockStatement:
		return tc.checkUnsafeBlockStatement(s)
	case *ast.ImportStatement:
		return tc.checkImportStatement(s)
	case *ast.AssignmentStatement:
		return tc.checkAssignmentStatement(s)
	default:
		tc.addError("Unknown statement type: %T", stmt)
		return &ErrorType{}
	}
}

func (tc *TypeChecker) checkExpression(expr ast.Expression) Type {
	switch e := expr.(type) {
	case *ast.IdentifierExpression:
		return tc.checkIdentifier(e)
	case *ast.IntegerLiteral:
		return tc.inferIntegerType(e.Value)
	case *ast.FloatLiteral:
		return tc.inferFloatType(e.Value)
	case *ast.StringLiteral:
		return &StringType{}
	case *ast.BooleanLiteral:
		return &BoolType{}
	case *ast.NullLiteral:
		return &NullType{}
	case *ast.PrefixExpression:
		return tc.checkPrefixExpression(e)
	case *ast.InfixExpression:
		return tc.checkInfixExpression(e)
	case *ast.CallExpression:
		return tc.checkCallExpression(e)
	case *ast.IndexExpression:
		return tc.checkIndexExpression(e)
	case *ast.PropertyExpression:
		return tc.checkPropertyExpression(e)
	case *ast.ListLiteral:
		return tc.checkListLiteral(e)
	case *ast.TupleLiteral:
		return tc.checkTupleLiteral(e)
	case *ast.MapLiteral:
		return tc.checkMapLiteral(e)
	case *ast.FunctionLiteral:
		return tc.checkFunctionLiteral(e)
	case *ast.StructLiteral:
		return tc.checkStructLiteral(e)
	case *ast.ConditionalExpression:
		return tc.checkConditionalExpression(e)
	case *ast.SpawnExpression:
		return tc.checkSpawnExpression(e)
	case *ast.AwaitExpression:
		return tc.checkAwaitExpression(e)
	default:
		tc.addError("Unknown expression type: %T", expr)
		return &ErrorType{}
	}
}

// 簡單實現一些初步的語意檢查方法

func (tc *TypeChecker) checkVarStatement(stmt *ast.VarStatement) Type {
	if stmt == nil {
		tc.addError("nil VarStatement encountered")
		return &ErrorType{}
	}

	if stmt.Value == nil {
		tc.addError("Variable declaration requires an initial value")
		return &ErrorType{}
	}

	valueType := tc.checkExpression(stmt.Value)

	declaredType := valueType
	if stmt.Type != nil {
		declaredType = tc.resolveTypeExpression(stmt.Type)

		// 檢查值類型是否與聲明類型兼容
		if !tc.isTypeCompatible(valueType, declaredType) {
			tc.addError("Type mismatch: cannot assign %s to %s",
				valueType.String(), declaredType.String())
		}
	}

	tc.symbolTable.Define(stmt.Name.Value, declaredType)
	return declaredType
}

func (tc *TypeChecker) checkConstStatement(stmt *ast.ConstStatement) Type {
	valueType := tc.checkExpression(stmt.Value)

	declaredType := valueType
	if stmt.Type != nil {
		declaredType = tc.resolveTypeExpression(stmt.Type)

		// 檢查值類型是否與聲明類型兼容
		if !tc.isTypeCompatible(valueType, declaredType) {
			tc.addError("Type mismatch: cannot assign %s to %s",
				valueType.String(), declaredType.String())
		}
	}

	tc.symbolTable.Define(stmt.Name.Value, declaredType)
	return declaredType
}

func (tc *TypeChecker) checkIdentifier(expr *ast.IdentifierExpression) Type {
	symbol, ok := tc.symbolTable.Resolve(expr.Value)
	if !ok {
		tc.addError("Undefined variable: %s", expr.Value)
		return &ErrorType{}
	}
	return symbol.Type
}

func (tc *TypeChecker) isTypeCompatible(source Type, target Type) bool {
	// 簡單實現，後續可擴展
	if _, ok := target.(*AnyType); ok {
		return true // 任何類型都可以賦值給 any
	}

	// 檢查類型是否完全相同
	return source.String() == target.String()
}

func (tc *TypeChecker) resolveTypeExpression(typeExpr *ast.TypeExpression) Type {
	// 解析基本類型
	typeName := typeExpr.Name

	// 檢查是否為內置類型或用戶定義類型
	resolvedType, ok := tc.symbolTable.ResolveType(typeName)
	if !ok {
		tc.addError("Unknown type: %s", typeName)
		return &ErrorType{}
	}

	// 處理泛型參數
	if len(typeExpr.GenericParams) > 0 {
		switch typeName {
		case "list":
			if len(typeExpr.GenericParams) != 1 {
				tc.addError("List type expects exactly 1 type parameter")
				return &ErrorType{}
			}
			elemType := tc.resolveTypeExpression(typeExpr.GenericParams[0])
			return &ListType{ElementType: elemType}

		case "map":
			if len(typeExpr.GenericParams) != 2 {
				tc.addError("Map type expects exactly 2 type parameters")
				return &ErrorType{}
			}
			keyType := tc.resolveTypeExpression(typeExpr.GenericParams[0])
			valueType := tc.resolveTypeExpression(typeExpr.GenericParams[1])
			return &MapType{KeyType: keyType, ValueType: valueType}

		case "ptr":
			if len(typeExpr.GenericParams) != 1 {
				tc.addError("Pointer type expects exactly 1 type parameter")
				return &ErrorType{}
			}
			baseType := tc.resolveTypeExpression(typeExpr.GenericParams[0])
			return &PointerType{BaseType: baseType}

		case "optional":
			if len(typeExpr.GenericParams) != 1 {
				tc.addError("Optional type expects exactly 1 type parameter")
				return &ErrorType{}
			}
			baseType := tc.resolveTypeExpression(typeExpr.GenericParams[0])
			return &OptionalType{BaseType: baseType}

		case "union":
			if len(typeExpr.GenericParams) < 2 {
				tc.addError("Union type expects at least 2 type parameters")
				return &ErrorType{}
			}
			types := make([]Type, len(typeExpr.GenericParams))
			for i, tp := range typeExpr.GenericParams {
				types[i] = tc.resolveTypeExpression(tp)
			}
			return &UnionType{Types: types}

		case "Future":
			if len(typeExpr.GenericParams) != 1 {
				tc.addError("Future type expects exactly 1 type parameter")
				return &ErrorType{}
			}
			resultType := tc.resolveTypeExpression(typeExpr.GenericParams[0])
			return &FutureType{ResultType: resultType}

		default:
			tc.addError("Type %s does not support generic parameters", typeName)
			return &ErrorType{}
		}
	}

	return resolvedType
}

func (tc *TypeChecker) inferIntegerType(value int64) Type {
	// 根據值大小推導整數類型
	if value >= -128 && value <= 127 {
		return &IntType{BitSize: 8}
	} else if value >= -32768 && value <= 32767 {
		return &IntType{BitSize: 16}
	} else if value >= -2147483648 && value <= 2147483647 {
		return &IntType{BitSize: 32}
	} else {
		return &IntType{BitSize: 64}
	}
}

func (tc *TypeChecker) inferFloatType(value float64) Type {
	// 簡單實現，後續可根據精度需求優化
	if value > -3.4e38 && value < 3.4e38 {
		return &FloatType{BitSize: 32}
	}
	return &FloatType{BitSize: 64}
}

// 實現更多檢查方法...

// 這裡僅實現了最基本的部分，實際上需要更多具體的檢查邏輯
// 為了示例，先保持簡潔，可以根據需要繼續擴展

func (tc *TypeChecker) checkBlockStatement(block *ast.BlockStatement) Type {
	blockSymbolTable := NewEnclosedSymbolTable(tc.symbolTable)
	oldSymbolTable := tc.symbolTable
	tc.symbolTable = blockSymbolTable

	var resultType Type = &NullType{}

	for _, stmt := range block.Statements {
		resultType = tc.checkStatement(stmt)
	}

	tc.symbolTable = oldSymbolTable
	return resultType
}

func (tc *TypeChecker) checkReturnStatement(stmt *ast.ReturnStatement) Type {
	if stmt.Value == nil {
		return &NullType{}
	}

	return tc.checkExpression(stmt.Value)
}

// checkIfStatement 檢查 if 語句
func (tc *TypeChecker) checkIfStatement(stmt *ast.IfStatement) Type {
	conditionType := tc.checkExpression(stmt.Condition)
	if _, ok := conditionType.(*BoolType); !ok {
		tc.addError("condition in if statement must be of type bool, got %s", conditionType.String())
	}

	tc.checkBlockStatement(stmt.Consequence)
	if stmt.Alternative != nil {
		tc.checkBlockStatement(stmt.Alternative)
	}

	return &NullType{}
}

// checkWhileStatement 檢查 while 語句
func (tc *TypeChecker) checkWhileStatement(stmt *ast.WhileStatement) Type {
	conditionType := tc.checkExpression(stmt.Condition)
	if _, ok := conditionType.(*BoolType); !ok {
		tc.addError("condition in while statement must be of type bool, got %s", conditionType.String())
	}

	tc.checkBlockStatement(stmt.Body)

	return &NullType{}
}

// checkForStatement 檢查 for 語句
func (tc *TypeChecker) checkForStatement(stmt *ast.ForStatement) Type {
	// 創建新的作用域
	prevTable := tc.symbolTable
	tc.symbolTable = NewEnclosedSymbolTable(tc.symbolTable)

	// 檢查可迭代對象
	tc.checkExpression(stmt.Iterable)

	// 定義循環變量
	if stmt.Value != nil {
		// 定義值變量
		tc.symbolTable.Define(stmt.Value.Value, &AnyType{})
	}

	if stmt.Index != nil {
		// 定義索引變量
		tc.symbolTable.Define(stmt.Index.Value, &IntType{BitSize: 64})
	}

	// 檢查循環體
	tc.checkBlockStatement(stmt.Body)

	// 恢復作用域
	tc.symbolTable = prevTable

	return &NullType{}
}

// checkFunctionDefinition 檢查函數定義
func (tc *TypeChecker) checkFunctionDefinition(fn *ast.FunctionDefinition) Type {
	// 創建新的作用域
	prevTable := tc.symbolTable
	tc.symbolTable = NewEnclosedSymbolTable(tc.symbolTable)

	// 處理參數
	paramTypes := []Type{}
	for _, param := range fn.Parameters {
		var paramType Type = &AnyType{}
		if param.Type != nil {
			paramType = tc.resolveTypeExpression(param.Type)
		}
		tc.symbolTable.Define(param.Name.Value, paramType)
		paramTypes = append(paramTypes, paramType)
	}

	// 處理接收者（如果有）
	if fn.Receiver != nil {
		var receiverType Type = &AnyType{}
		if fn.Receiver.Type != nil {
			receiverType = tc.resolveTypeExpression(fn.Receiver.Type)
		}
		tc.symbolTable.Define("this", receiverType)
	}

	// 解析返回類型
	var returnType Type = &AnyType{}
	if fn.ReturnType != nil {
		returnType = tc.resolveTypeExpression(fn.ReturnType)
	}

	// 檢查函數體
	tc.checkBlockStatement(fn.Body)

	// 創建函數類型
	funcType := &FunctionType{
		ParameterTypes: paramTypes,
		ReturnType:     returnType,
	}

	// 在外層作用域中定義函數
	prevTable.Define(fn.Name.Value, funcType)

	// 恢復作用域
	tc.symbolTable = prevTable

	return &NullType{}
}

// checkStructStatement 檢查結構體定義
func (tc *TypeChecker) checkStructStatement(stmt *ast.StructStatement) Type {
	fields := make(map[string]Type)

	// 處理字段
	for _, field := range stmt.Fields {
		var fieldType Type = &AnyType{}
		if field.Type != nil {
			fieldType = tc.resolveTypeExpression(field.Type)
		}
		fields[field.Name.Value] = fieldType
	}

	// 創建結構體類型
	structType := &StructType{
		Name:   stmt.Name.Value,
		Fields: fields,
	}

	// 定義結構體類型
	tc.symbolTable.DefineType(stmt.Name.Value, structType)

	return &NullType{}
}

// checkInterfaceStatement 檢查接口定義
func (tc *TypeChecker) checkInterfaceStatement(stmt *ast.InterfaceStatement) Type {
	methods := make(map[string]*FunctionType)

	// 處理方法
	for _, method := range stmt.Methods {
		// 處理參數
		paramTypes := []Type{}
		for _, param := range method.Parameters {
			var paramType Type = &AnyType{}
			if param.Type != nil {
				paramType = tc.resolveTypeExpression(param.Type)
			}
			paramTypes = append(paramTypes, paramType)
		}

		// 處理返回類型
		var returnType Type = &AnyType{}
		if method.ReturnType != nil {
			returnType = tc.resolveTypeExpression(method.ReturnType)
		}

		// 創建函數類型
		methodType := &FunctionType{
			ParameterTypes: paramTypes,
			ReturnType:     returnType,
		}

		methods[method.Name.Value] = methodType
	}

	// 創建接口類型
	interfaceType := &InterfaceType{
		Name:    stmt.Name.Value,
		Methods: methods,
	}

	// 定義接口類型
	tc.symbolTable.DefineType(stmt.Name.Value, interfaceType)

	return &NullType{}
}

// checkUnsafeBlockStatement 檢查不安全代碼塊
func (tc *TypeChecker) checkUnsafeBlockStatement(stmt *ast.UnsafeBlockStatement) Type {
	// 在不安全代碼塊中，不進行嚴格的類型檢查
	tc.checkBlockStatement(stmt.Body)
	return &NullType{}
}

// checkImportStatement 檢查導入語句
func (tc *TypeChecker) checkImportStatement(stmt *ast.ImportStatement) Type {
	// 簡單檢查，實際導入的處理會在編譯階段完成
	return &NullType{}
}

// checkAssignmentStatement 檢查賦值語句
func (tc *TypeChecker) checkAssignmentStatement(stmt *ast.AssignmentStatement) Type {
	// 檢查左側和右側的表達式類型
	leftType := tc.checkExpression(stmt.Left)
	rightType := tc.checkExpression(stmt.Value)

	// 檢查類型兼容性
	if !tc.isTypeCompatible(rightType, leftType) {
		tc.addError("cannot assign value of type %s to variable of type %s",
			rightType.String(), leftType.String())
	}

	return &NullType{}
}

// checkPrefixExpression 檢查前綴表達式
func (tc *TypeChecker) checkPrefixExpression(expr *ast.PrefixExpression) Type {
	operandType := tc.checkExpression(expr.Right)

	switch expr.Operator {
	case "!":
		// 邏輯非操作符需要布爾類型
		if _, ok := operandType.(*BoolType); !ok {
			tc.addError("operator %s requires boolean type, got %s",
				expr.Operator, operandType.String())
			return &ErrorType{}
		}
		return &BoolType{}
	case "-":
		// 負號操作符需要數值類型
		if _, ok := operandType.(*IntType); ok {
			return operandType
		}
		if _, ok := operandType.(*FloatType); ok {
			return operandType
		}
		tc.addError("operator %s requires numeric type, got %s",
			expr.Operator, operandType.String())
		return &ErrorType{}
	case "~":
		// 位元非操作符需要整數類型
		if _, ok := operandType.(*IntType); !ok {
			tc.addError("operator %s requires integer type, got %s",
				expr.Operator, operandType.String())
			return &ErrorType{}
		}
		return operandType
	default:
		tc.addError("unknown prefix operator: %s", expr.Operator)
		return &ErrorType{}
	}
}

// checkInfixExpression 檢查中綴表達式
func (tc *TypeChecker) checkInfixExpression(expr *ast.InfixExpression) Type {
	leftType := tc.checkExpression(expr.Left)
	rightType := tc.checkExpression(expr.Right)

	switch expr.Operator {
	case "+", "-", "*", "/", "%":
		// 數值運算需要數值類型
		if _, ok1 := leftType.(*IntType); ok1 {
			if _, ok2 := rightType.(*IntType); ok2 {
				return leftType
			}
		}
		if _, ok1 := leftType.(*FloatType); ok1 {
			if _, ok2 := rightType.(*FloatType); ok2 {
				return leftType
			}
		}
		// 特殊情況：字符串連接
		if expr.Operator == "+" {
			if _, ok1 := leftType.(*StringType); ok1 {
				if _, ok2 := rightType.(*StringType); ok2 {
					return &StringType{}
				}
			}
		}
		tc.addError("operator %s requires compatible numeric types, got %s and %s",
			expr.Operator, leftType.String(), rightType.String())
		return &ErrorType{}
	case "==", "!=":
		// 相等性比較大多數類型都可以
		return &BoolType{}
	case ">", "<", ">=", "<=":
		// 比較運算符需要相同的類型
		if !tc.isTypeCompatible(leftType, rightType) {
			tc.addError("operator %s requires comparable types, got %s and %s",
				expr.Operator, leftType.String(), rightType.String())
			return &ErrorType{}
		}
		return &BoolType{}
	case "&&", "||":
		// 邏輯運算符需要布爾類型
		if _, ok1 := leftType.(*BoolType); !ok1 {
			tc.addError("operator %s requires boolean type, got %s for left operand",
				expr.Operator, leftType.String())
			return &ErrorType{}
		}
		if _, ok2 := rightType.(*BoolType); !ok2 {
			tc.addError("operator %s requires boolean type, got %s for right operand",
				expr.Operator, rightType.String())
			return &ErrorType{}
		}
		return &BoolType{}
	case "&", "|", "^", "<<", ">>":
		// 位運算符需要整數類型
		if _, ok1 := leftType.(*IntType); !ok1 {
			tc.addError("operator %s requires integer type, got %s for left operand",
				expr.Operator, leftType.String())
			return &ErrorType{}
		}
		if _, ok2 := rightType.(*IntType); !ok2 {
			tc.addError("operator %s requires integer type, got %s for right operand",
				expr.Operator, rightType.String())
			return &ErrorType{}
		}
		return leftType
	default:
		tc.addError("unknown infix operator: %s", expr.Operator)
		return &ErrorType{}
	}
}

// checkCallExpression 檢查函數調用表達式
func (tc *TypeChecker) checkCallExpression(expr *ast.CallExpression) Type {
	// 檢查被調用的函數
	funcType := tc.checkExpression(expr.Function)

	switch ft := funcType.(type) {
	case *FunctionType:
		// 檢查參數數量
		if len(expr.Arguments) != len(ft.ParameterTypes) {
			tc.addError("function call expected %d arguments, got %d",
				len(ft.ParameterTypes), len(expr.Arguments))
			return &ErrorType{}
		}

		// 檢查每個參數類型
		for i, arg := range expr.Arguments {
			argType := tc.checkExpression(arg)
			paramType := ft.ParameterTypes[i]
			if !tc.isTypeCompatible(argType, paramType) {
				tc.addError("argument %d: expected type %s, got %s",
					i+1, paramType.String(), argType.String())
			}
		}

		return ft.ReturnType
	default:
		tc.addError("cannot call non-function type: %s", funcType.String())
		return &ErrorType{}
	}
}

// checkIndexExpression 檢查索引表達式
func (tc *TypeChecker) checkIndexExpression(expr *ast.IndexExpression) Type {
	// 檢查被索引的對象
	leftType := tc.checkExpression(expr.Left)
	// 檢查索引
	indexType := tc.checkExpression(expr.Index)

	// 檢查索引是否為整數
	if _, ok := indexType.(*IntType); !ok {
		tc.addError("index must be of integer type, got %s", indexType.String())
	}

	// 確定返回類型
	switch lt := leftType.(type) {
	case *ListType:
		return lt.ElementType
	case *ArrayType:
		return lt.ElementType
	case *MapType:
		return lt.ValueType
	case *StringType:
		// 字符串的索引返回字符串
		return &StringType{}
	default:
		tc.addError("cannot index type: %s", leftType.String())
		return &ErrorType{}
	}
}

// checkPropertyExpression 檢查屬性訪問表達式
func (tc *TypeChecker) checkPropertyExpression(expr *ast.PropertyExpression) Type {
	// 檢查對象
	objType := tc.checkExpression(expr.Object)

	// 檢查屬性訪問
	switch ot := objType.(type) {
	case *StructType:
		if fieldType, ok := ot.Fields[expr.Property.Value]; ok {
			return fieldType
		}
		tc.addError("struct %s has no field named %s", ot.Name, expr.Property.Value)
		return &ErrorType{}
	default:
		tc.addError("cannot access property of non-struct type: %s", objType.String())
		return &ErrorType{}
	}
}

// checkListLiteral 檢查列表字面量
func (tc *TypeChecker) checkListLiteral(expr *ast.ListLiteral) Type {
	if len(expr.Elements) == 0 {
		// 空列表，假設元素類型為 any
		return &ListType{ElementType: &AnyType{}}
	}

	// 檢查第一個元素的類型
	firstType := tc.checkExpression(expr.Elements[0])

	// 檢查所有元素是否有相同的類型
	for i, elem := range expr.Elements[1:] {
		elemType := tc.checkExpression(elem)
		if !tc.isTypeCompatible(elemType, firstType) {
			tc.addError("inconsistent element type in list: element %d has type %s, expected %s",
				i+1, elemType.String(), firstType.String())
		}
	}

	return &ListType{ElementType: firstType}
}

// checkTupleLiteral 檢查元組字面量
func (tc *TypeChecker) checkTupleLiteral(expr *ast.TupleLiteral) Type {
	elementTypes := []Type{}

	// 檢查每個元素的類型
	for _, elem := range expr.Elements {
		elemType := tc.checkExpression(elem)
		elementTypes = append(elementTypes, elemType)
	}

	return &TupleType{ElementTypes: elementTypes}
}

// checkMapLiteral 檢查映射字面量
func (tc *TypeChecker) checkMapLiteral(expr *ast.MapLiteral) Type {
	if len(expr.Pairs) == 0 {
		// 空映射，假設類型為 any -> any
		return &MapType{KeyType: &AnyType{}, ValueType: &AnyType{}}
	}

	// 尋找第一個鍵值對
	var firstKey ast.Expression
	var firstValue ast.Expression
	for k, v := range expr.Pairs {
		firstKey = k
		firstValue = v
		break
	}

	keyType := tc.checkExpression(firstKey)
	valueType := tc.checkExpression(firstValue)

	// 檢查所有鍵值對是否有一致的類型
	for k, v := range expr.Pairs {
		if k == firstKey {
			continue
		}

		kType := tc.checkExpression(k)
		vType := tc.checkExpression(v)

		if !tc.isTypeCompatible(kType, keyType) {
			tc.addError("inconsistent key type in map: got %s, expected %s",
				kType.String(), keyType.String())
		}

		if !tc.isTypeCompatible(vType, valueType) {
			tc.addError("inconsistent value type in map: got %s, expected %s",
				vType.String(), valueType.String())
		}
	}

	return &MapType{KeyType: keyType, ValueType: valueType}
}

// checkFunctionLiteral 檢查函數字面量
func (tc *TypeChecker) checkFunctionLiteral(expr *ast.FunctionLiteral) Type {
	// 創建新的作用域
	prevTable := tc.symbolTable
	tc.symbolTable = NewEnclosedSymbolTable(tc.symbolTable)

	// 處理參數
	paramTypes := []Type{}
	for _, param := range expr.Parameters {
		var paramType Type = &AnyType{}
		if param.Type != nil {
			paramType = tc.resolveTypeExpression(param.Type)
		}
		tc.symbolTable.Define(param.Name.Value, paramType)
		paramTypes = append(paramTypes, paramType)
	}

	// 解析返回類型
	var returnType Type = &AnyType{}
	if expr.ReturnType != nil {
		returnType = tc.resolveTypeExpression(expr.ReturnType)
	}

	// 檢查函數體
	tc.checkBlockStatement(expr.Body)

	// 恢復作用域
	tc.symbolTable = prevTable

	// 返回函數類型
	return &FunctionType{
		ParameterTypes: paramTypes,
		ReturnType:     returnType,
	}
}

// checkStructLiteral 檢查結構體字面量
func (tc *TypeChecker) checkStructLiteral(expr *ast.StructLiteral) Type {
	// 找到結構體類型
	typeName := expr.Type.Value
	typeValue, ok := tc.symbolTable.ResolveType(typeName)
	if !ok {
		tc.addError("undefined struct type: %s", typeName)
		return &ErrorType{}
	}

	structType, ok := typeValue.(*StructType)
	if !ok {
		tc.addError("type %s is not a struct", typeName)
		return &ErrorType{}
	}

	// 檢查字段是否都存在，且類型匹配
	for name, value := range expr.Fields {
		fieldType, ok := structType.Fields[name]
		if !ok {
			tc.addError("struct %s has no field named %s", typeName, name)
			continue
		}

		valueType := tc.checkExpression(value)
		if !tc.isTypeCompatible(valueType, fieldType) {
			tc.addError("cannot assign value of type %s to field %s of type %s",
				valueType.String(), name, fieldType.String())
		}
	}

	return structType
}

// checkConditionalExpression 檢查條件表達式 (三元運算符)
func (tc *TypeChecker) checkConditionalExpression(expr *ast.ConditionalExpression) Type {
	// 檢查條件必須是布爾類型
	condType := tc.checkExpression(expr.Condition)
	if _, ok := condType.(*BoolType); !ok {
		tc.addError("condition in ternary expression must be of type bool, got %s", condType.String())
	}

	// 檢查兩個結果分支
	trueType := tc.checkExpression(expr.IfTrue)
	falseType := tc.checkExpression(expr.IfFalse)

	// 確保兩個分支的類型兼容
	if !tc.isTypeCompatible(trueType, falseType) && !tc.isTypeCompatible(falseType, trueType) {
		tc.addError("incompatible types in ternary expression: %s and %s",
			trueType.String(), falseType.String())
		return &ErrorType{}
	}

	// 返回更具體的類型
	if tc.isTypeCompatible(trueType, falseType) {
		return falseType
	}
	return trueType
}

// checkSpawnExpression 檢查 spawn 表達式
func (tc *TypeChecker) checkSpawnExpression(expr *ast.SpawnExpression) Type {
	// 檢查函數調用表達式
	callType := tc.checkCallExpression(expr.Call)

	// 創建 Future 類型
	return &FutureType{ResultType: callType}
}

// checkAwaitExpression 檢查 await 表達式
func (tc *TypeChecker) checkAwaitExpression(expr *ast.AwaitExpression) Type {
	if len(expr.Futures) == 0 {
		tc.addError("await expression requires at least one future")
		return &ErrorType{}
	}

	// 檢查每個 future 表達式
	resultTypes := []Type{}
	for _, future := range expr.Futures {
		futureType := tc.checkExpression(future)

		// 確保是 Future 類型
		if ft, ok := futureType.(*FutureType); ok {
			resultTypes = append(resultTypes, ft.ResultType)
		} else {
			tc.addError("await can only be used with future types, got %s", futureType.String())
			resultTypes = append(resultTypes, &ErrorType{})
		}
	}

	// 如果只有一個結果，直接返回其類型
	if len(resultTypes) == 1 {
		return resultTypes[0]
	}

	// 如果有多個結果，返回元組類型
	return &TupleType{ElementTypes: resultTypes}
}
