package codegen

import (
	"fmt"
	"glux/internal/ast"
	"strings"
)

// 生成標識符表達式
func (g *CodeGenerator) generateIdentifierExpression(expr *ast.IdentifierExpression) string {
	return g.safeVarName(expr.Value)
}

// 生成整數字面量
func (g *CodeGenerator) generateIntegerLiteral(expr *ast.IntegerLiteral) string {
	return fmt.Sprintf("%d", expr.Value)
}

// 生成浮點數字面量
func (g *CodeGenerator) generateFloatLiteral(expr *ast.FloatLiteral) string {
	return fmt.Sprintf("%g", expr.Value)
}

// 生成字符串字面量
func (g *CodeGenerator) generateStringLiteral(expr *ast.StringLiteral) string {
	// 確保字符串中的轉義字符被正確處理
	return fmt.Sprintf("%q", expr.Value)
}

// 生成字符串插值表達式
func (g *CodeGenerator) generateStringInterpolationExpression(expr *ast.StringInterpolationExpression) string {
	var parts []string
	g.imports["fmt"] = ""

	for _, part := range expr.Parts {
		if strLit, ok := part.(*ast.StringLiteral); ok {
			// 字符串字面量部分
			parts = append(parts, fmt.Sprintf("%s", strLit.Value))
		} else {
			// 表達式部分，將其轉換為字符串
			exprCode := g.generateExpression(part)
			parts = append(parts, fmt.Sprintf("%s", exprCode))
		}
	}

	// 使用fmt.Sprintf來連接所有部分
	if len(parts) == 1 {
		return fmt.Sprintf("%q", parts[0])
	}

	// 生成格式字符串和參數列表
	var fmtParts []string
	var args []string

	for i, part := range expr.Parts {
		if _, ok := part.(*ast.StringLiteral); ok {
			// 字符串字面量部分直接加入格式字符串
			fmtParts = append(fmtParts, parts[i])
		} else {
			// 表達式部分使用占位符和參數
			fmtParts = append(fmtParts, "%v")
			args = append(args, parts[i])
		}
	}

	fmtStr := strings.Join(fmtParts, "")

	if len(args) == 0 {
		return fmt.Sprintf("%q", fmtStr)
	}

	return fmt.Sprintf("fmt.Sprintf(%q, %s)", fmtStr, strings.Join(args, ", "))
}

// 生成布爾字面量
func (g *CodeGenerator) generateBooleanLiteral(expr *ast.BooleanLiteral) string {
	return fmt.Sprintf("%t", expr.Value)
}

// 生成 null 字面量
func (g *CodeGenerator) generateNullLiteral(expr *ast.NullLiteral) string {
	return "nil"
}

// 生成前綴表達式
func (g *CodeGenerator) generatePrefixExpression(expr *ast.PrefixExpression) string {
	operand := g.generateExpression(expr.Right)

	// 處理不同的前綴運算符
	switch expr.Operator {
	case "!":
		return fmt.Sprintf("!%s", operand)
	case "-":
		return fmt.Sprintf("-%s", operand)
	case "+":
		return fmt.Sprintf("+%s", operand)
	case "~":
		// 位元運算符
		return fmt.Sprintf("^%s", operand)
	default:
		g.addError("Unknown prefix operator: %s", expr.Operator)
		return fmt.Sprintf("/* ERROR: Unknown prefix operator: %s */ %s", expr.Operator, operand)
	}
}

// 生成中綴表達式
func (g *CodeGenerator) generateInfixExpression(expr *ast.InfixExpression) string {
	left := g.generateExpression(expr.Left)
	right := g.generateExpression(expr.Right)

	// 處理不同的運算符
	switch expr.Operator {
	case "+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">=", "&&", "||", "&", "|", "^":
		// 直接映射到Go的運算符
		return fmt.Sprintf("(%s %s %s)", left, expr.Operator, right)
	case "and":
		return fmt.Sprintf("(%s && %s)", left, right)
	case "or":
		return fmt.Sprintf("(%s || %s)", left, right)
	case "=":
		// 賦值運算符
		return fmt.Sprintf("%s = %s", left, right)
	default:
		g.addError("Unknown infix operator: %s", expr.Operator)
		return fmt.Sprintf("/* ERROR: Unknown infix operator: %s */ (%s ?? %s)", expr.Operator, left, right)
	}
}

// 生成三元運算符表達式
func (g *CodeGenerator) generateConditionalExpression(expr *ast.ConditionalExpression) string {
	condition := g.generateExpression(expr.Condition)
	trueExpr := g.generateExpression(expr.IfTrue)
	falseExpr := g.generateExpression(expr.IfFalse)

	// Go 沒有三元運算符，所以我們使用一個立即執行的匿名函數
	tempVar := g.nextTempVar()
	g.writeLine(fmt.Sprintf("var %s interface{}", tempVar))
	g.writeLine(fmt.Sprintf("if %s {", condition))
	g.indentLevel++
	g.writeLine(fmt.Sprintf("%s = %s", tempVar, trueExpr))
	g.indentLevel--
	g.writeLine("} else {")
	g.indentLevel++
	g.writeLine(fmt.Sprintf("%s = %s", tempVar, falseExpr))
	g.indentLevel--
	g.writeLine("}")

	return tempVar
}

// 生成函數調用表達式
func (g *CodeGenerator) generateCallExpression(expr *ast.CallExpression) string {
	function := g.generateExpression(expr.Function)

	var args []string

	// 處理普通參數
	for _, arg := range expr.Arguments {
		args = append(args, g.generateExpression(arg))
	}

	// 處理具名參數 (Go 不支持具名參數，所以這裡的處理是簡化的)
	for name, value := range expr.NamedArgs {
		g.addError("Go does not support named arguments, using positional argument for %s", name)
		args = append(args, g.generateExpression(value))
	}

	// 檢查是否為內建函數
	if ident, ok := expr.Function.(*ast.IdentifierExpression); ok {
		// 處理println函數
		if ident.Value == "println" {
			// 直接使用Go的內建println
			return fmt.Sprintf("fmt.Println(%s)", strings.Join(args, ", "))
		}
	}

	return fmt.Sprintf("%s(%s)", function, strings.Join(args, ", "))
}

// 生成索引表達式
func (g *CodeGenerator) generateIndexExpression(expr *ast.IndexExpression) string {
	left := g.generateExpression(expr.Left)
	index := g.generateExpression(expr.Index)

	return fmt.Sprintf("%s[%s]", left, index)
}

// 生成屬性訪問表達式
func (g *CodeGenerator) generatePropertyExpression(expr *ast.PropertyExpression) string {
	object := g.generateExpression(expr.Object)
	property := expr.Property.Value

	// 確保屬性名稱開頭是大寫的，因為 Go 中只有大寫的字段才能被導出/訪問
	if len(property) > 0 && property[0] >= 'a' && property[0] <= 'z' {
		// Go 中不能訪問小寫開頭的字段，這裡我們暫時不進行大寫轉換
		// 但應該添加一個警告
		g.addError("Field '%s' starts with lowercase and might not be accessible in Go", property)
	}

	return fmt.Sprintf("%s.%s", object, property)
}

// 生成列表字面量
func (g *CodeGenerator) generateListLiteral(expr *ast.ListLiteral) string {
	var elements []string

	for _, element := range expr.Elements {
		elements = append(elements, g.generateExpression(element))
	}

	// 如果列表為空，則返回空切片
	if len(elements) == 0 {
		return "[]interface{}{}"
	}

	return fmt.Sprintf("[]interface{}{%s}", strings.Join(elements, ", "))
}

// 生成元組字面量
func (g *CodeGenerator) generateTupleLiteral(expr *ast.TupleLiteral) string {
	var elements []string

	for _, element := range expr.Elements {
		elements = append(elements, g.generateExpression(element))
	}

	// Go 沒有內置的元組類型，所以我們使用一個結構體來模擬
	tupleType := fmt.Sprintf("struct {\n")
	for fieldIdx := range expr.Elements {
		tupleType += fmt.Sprintf("\tItem%d interface{}\n", fieldIdx)
	}
	tupleType += "}"

	var fieldValues []string
	for fieldIdx, elem := range elements {
		fieldValues = append(fieldValues, fmt.Sprintf("Item%d: %s", fieldIdx, elem))
	}

	return fmt.Sprintf("%s{%s}", tupleType, strings.Join(fieldValues, ", "))
}

// 生成映射字面量
func (g *CodeGenerator) generateMapLiteral(expr *ast.MapLiteral) string {
	var pairs []string

	for key, value := range expr.Pairs {
		keyStr := g.generateExpression(key)
		valueStr := g.generateExpression(value)
		pairs = append(pairs, fmt.Sprintf("%s: %s", keyStr, valueStr))
	}

	// 如果映射為空，則返回空映射
	if len(pairs) == 0 {
		return "map[interface{}]interface{}{}"
	}

	return fmt.Sprintf("map[interface{}]interface{}{%s}", strings.Join(pairs, ", "))
}

// 生成函數字面量
func (g *CodeGenerator) generateFunctionLiteral(expr *ast.FunctionLiteral) string {
	var paramNames []string
	var paramTypes []string

	// 處理參數
	for _, param := range expr.Parameters {
		paramName := g.safeVarName(param.Name.Value)
		paramType := "interface{}"

		if param.Type != nil {
			paramType = g.goType(param.Type.String())
		}

		paramNames = append(paramNames, paramName)
		paramTypes = append(paramTypes, paramType)
	}

	// 處理返回類型
	returnType := "interface{}"
	if expr.ReturnType != nil {
		returnType = g.goType(expr.ReturnType.String())
	}

	// 函數體
	oldReturnType := g.currentFuncReturnType
	g.currentFuncReturnType = returnType

	// 生成函數體
	var bodyBuffer strings.Builder
	currentBuffer := g.buffer
	g.buffer = bodyBuffer

	for _, s := range expr.Body.Statements {
		g.generateStatement(s)
	}

	bodyContent := g.buffer.String()
	g.buffer = currentBuffer

	// 恢復上下文
	g.currentFuncReturnType = oldReturnType

	// 生成函數類型和主體
	paramDefs := make([]string, len(paramNames))
	for i := range paramNames {
		paramDefs[i] = fmt.Sprintf("%s %s", paramNames[i], paramTypes[i])
	}

	funcDef := fmt.Sprintf("func(%s) %s {\n%s\n}", strings.Join(paramDefs, ", "), returnType, bodyContent)

	return funcDef
}

// 生成結構體字面量
func (g *CodeGenerator) generateStructLiteral(expr *ast.StructLiteral) string {
	var fields []string

	for name, value := range expr.Fields {
		valueStr := g.generateExpression(value)
		fields = append(fields, fmt.Sprintf("%s: %s", name, valueStr))
	}

	return fmt.Sprintf("%s{%s}", expr.Type.Value, strings.Join(fields, ", "))
}

// 生成 spawn 表達式
func (g *CodeGenerator) generateSpawnExpression(expr *ast.SpawnExpression) string {
	// 導入 goroutine 相關的包
	g.imports["sync"] = ""

	// 生成異步函數調用代碼
	call := g.generateCallExpression(expr.Call)

	// 創建一個 channel 來等待結果
	resultVarName := g.nextTempVar()
	channelVarName := g.nextTempVar()

	// 函數返回值的類型
	resultType := "interface{}"

	// 創建異步調用
	g.writeLine(fmt.Sprintf("var %s %s", resultVarName, resultType))
	g.writeLine(fmt.Sprintf("%s := make(chan %s)", channelVarName, resultType))
	g.writeLine(fmt.Sprintf("go func() {"))
	g.indentLevel++
	g.writeLine(fmt.Sprintf("%s <- %s", channelVarName, call))
	g.indentLevel--
	g.writeLine(fmt.Sprintf("}()"))

	// 返回 channel，稍後可以使用 await 來獲取結果
	return channelVarName
}

// 生成 await 表達式
func (g *CodeGenerator) generateAwaitExpression(expr *ast.AwaitExpression) string {
	// 處理單個 future
	if len(expr.Futures) == 1 {
		future := g.generateExpression(expr.Futures[0])
		return fmt.Sprintf("<-%s", future)
	}

	// 處理多個 futures
	var results []string

	// 為每個 future 創建一個變數來存儲結果
	for _, future := range expr.Futures {
		resultVar := g.nextTempVar()
		futureExpr := g.generateExpression(future)
		g.writeLine(fmt.Sprintf("%s := <-%s", resultVar, futureExpr))
		results = append(results, resultVar)
	}

	// 如果有多個結果，創建一個結構體來存儲它們
	tupleType := fmt.Sprintf("struct {\n")
	for fieldIdx := range results {
		tupleType += fmt.Sprintf("\tItem%d interface{}\n", fieldIdx)
	}
	tupleType += "}"

	// 構建結構體初始化代碼
	var fieldAssignments []string
	for fieldIdx, resultVar := range results {
		fieldAssignments = append(fieldAssignments, fmt.Sprintf("Item%d: %s", fieldIdx, resultVar))
	}

	return fmt.Sprintf("%s{%s}", tupleType, strings.Join(fieldAssignments, ", "))
}
