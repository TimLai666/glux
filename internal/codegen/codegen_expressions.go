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

	switch expr.Operator {
	case "+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=", "&&", "||", "&", "|", "^":
		// 直接使用Go中相同的運算符
		return fmt.Sprintf("(%s %s %s)", left, expr.Operator, right)
	case "=":
		// 處理賦值運算符
		return fmt.Sprintf("%s = %s", left, right)
	case "and":
		return fmt.Sprintf("(%s && %s)", left, right)
	case "or":
		return fmt.Sprintf("(%s || %s)", left, right)
	case "in":
		// 使用contains函數
		return fmt.Sprintf("contains(%s, %s)", right, left)
	case "**":
		// 冪運算在 Go 中需要使用 math.Pow
		g.imports["math"] = ""
		return fmt.Sprintf("math.Pow(float64(%s), float64(%s))", left, right)
	case "??":
		// Null 合併運算符
		// Go 中沒有直接等效的，使用三元運算符的模擬
		return fmt.Sprintf("(func() interface{} {\n\tif %s == nil {\n\t\treturn %s\n\t}\n\treturn %s\n}())",
			left, right, left)
	case "..":
		// 範圍運算符
		g.addError("Range operator (..) needs special handling in context")
		return fmt.Sprintf("/* ERROR: Range operator needs context */ []int{%s, %s}", left, right)
	case "<<", ">>":
		// 位移運算
		return fmt.Sprintf("(%s %s %s)", left, expr.Operator, right)
	default:
		g.addError("Unknown infix operator: %s", expr.Operator)
		return fmt.Sprintf("/* ERROR: Unknown infix operator: %s */", expr.Operator)
	}
}

// 生成函數調用表達式
func (g *CodeGenerator) generateCallExpression(expr *ast.CallExpression) string {
	function := g.generateExpression(expr.Function)

	// 處理特殊的內置函數
	if identExpr, ok := expr.Function.(*ast.IdentifierExpression); ok {
		switch identExpr.Value {
		case "print", "println":
			// 將 print/println 轉換為 fmt.Print/fmt.Println
			g.imports["fmt"] = ""
			function = "fmt." + strings.Title(identExpr.Value)
		case "len", "append", "make", "new", "panic", "recover", "close", "delete", "copy", "cap", "real", "imag", "complex":
			// 這些是 Go 內置函數，保持不變
		case "range":
			// 特殊處理 range 函數
			if len(expr.Arguments) == 1 {
				endValue := g.generateExpression(expr.Arguments[0])
				return fmt.Sprintf("make([]int, %s)", endValue)
			} else if len(expr.Arguments) == 2 {
				startValue := g.generateExpression(expr.Arguments[0])
				endValue := g.generateExpression(expr.Arguments[1])
				tempVar := g.nextTempVar()
				g.writeLine(fmt.Sprintf("var %s = make([]int, %s - %s)", tempVar, endValue, startValue))
				g.writeLine(fmt.Sprintf("for i := range %s {", tempVar))
				g.indentLevel++
				g.writeLine(fmt.Sprintf("%s[i] = int(%s) + i", tempVar, startValue))
				g.indentLevel--
				g.writeLine("}")
				return tempVar
			}
			// 其他情況使用預設處理
		}
	}

	// 生成參數列表
	args := []string{}
	for _, arg := range expr.Arguments {
		args = append(args, g.generateExpression(arg))
	}

	argsStr := strings.Join(args, ", ")
	return fmt.Sprintf("%s(%s)", function, argsStr)
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

	return fmt.Sprintf("%s.%s", object, property)
}

// 生成列表字面量
func (g *CodeGenerator) generateListLiteral(expr *ast.ListLiteral) string {
	elements := []string{}

	for _, elem := range expr.Elements {
		elements = append(elements, g.generateExpression(elem))
	}

	elementsStr := strings.Join(elements, ", ")

	// 如果知道列表元素的類型，可以使用具體類型
	if len(elements) > 0 {
		return fmt.Sprintf("[]interface{}{%s}", elementsStr)
	}

	return fmt.Sprintf("[]interface{}{%s}", elementsStr)
}

// 生成元組字面量
func (g *CodeGenerator) generateTupleLiteral(expr *ast.TupleLiteral) string {
	// Go 沒有原生的元組類型，使用結構體或切片來實現
	elements := []string{}

	for _, elem := range expr.Elements {
		elements = append(elements, g.generateExpression(elem))
	}

	elementsStr := strings.Join(elements, ", ")

	// 使用匿名結構體或切片，根據上下文選擇合適的實現
	return fmt.Sprintf("[]interface{}{%s}", elementsStr)
}

// 生成映射字面量
func (g *CodeGenerator) generateMapLiteral(expr *ast.MapLiteral) string {
	pairs := []string{}

	for key, value := range expr.Pairs {
		keyCode := g.generateExpression(key)
		valueCode := g.generateExpression(value)
		pairs = append(pairs, fmt.Sprintf("%s: %s", keyCode, valueCode))
	}

	pairsStr := strings.Join(pairs, ", ")

	return fmt.Sprintf("map[interface{}]interface{}{%s}", pairsStr)
}

// 生成函數字面量
func (g *CodeGenerator) generateFunctionLiteral(expr *ast.FunctionLiteral) string {
	// 處理參數列表
	params := []string{}
	for _, p := range expr.Parameters {
		paramName := g.safeVarName(p.Name.Value)
		paramType := "interface{}"

		if p.Type != nil {
			paramType = g.goType(p.Type.Name)
		}

		params = append(params, fmt.Sprintf("%s %s", paramName, paramType))
	}

	paramsStr := strings.Join(params, ", ")

	// 處理返回類型
	returnType := "interface{}"
	if expr.ReturnType != nil {
		returnType = g.goType(expr.ReturnType.Name)
	}

	// 保存當前函數返回類型並還原
	prevReturnType := g.currentFuncReturnType
	g.currentFuncReturnType = returnType

	// 生成函數體
	var bodyBuilder strings.Builder
	bodyBuilder.WriteString("{\n")
	g.indentLevel++

	// 處理參數的預設值
	for _, p := range expr.Parameters {
		if p.DefaultValue != nil {
			paramName := g.safeVarName(p.Name.Value)
			defaultValue := g.generateExpression(p.DefaultValue)

			g.writeLine(fmt.Sprintf("if %s == nil {", paramName))
			g.indentLevel++
			g.writeLine(fmt.Sprintf("%s = %s", paramName, defaultValue))
			g.indentLevel--
			g.writeLine("}")
		}
	}

	// 生成函數體
	for _, stmt := range expr.Body.Statements {
		g.generateStatement(stmt)
	}

	g.indentLevel--
	bodyBuilder.WriteString(g.buffer.String())
	bodyBuilder.WriteString("}")

	// 還原返回類型
	g.currentFuncReturnType = prevReturnType

	// 構建函數字面量
	return fmt.Sprintf("func(%s) %s %s", paramsStr, returnType, bodyBuilder.String())
}

// 生成結構體字面量
func (g *CodeGenerator) generateStructLiteral(expr *ast.StructLiteral) string {
	fields := []string{}

	for name, value := range expr.Fields {
		valueCode := g.generateExpression(value)
		fields = append(fields, fmt.Sprintf("%s: %s", name, valueCode))
	}

	fieldsStr := strings.Join(fields, ", ")

	return fmt.Sprintf("%s{%s}", expr.Type.Value, fieldsStr)
}

// 生成條件表達式 (三元運算符)
func (g *CodeGenerator) generateConditionalExpression(expr *ast.ConditionalExpression) string {
	// Go 沒有三元運算符，使用 if-else 語句代替
	tempVar := g.nextTempVar()
	condition := g.generateExpression(expr.Condition)
	ifTrue := g.generateExpression(expr.IfTrue)
	ifFalse := g.generateExpression(expr.IfFalse)

	g.writeLine(fmt.Sprintf("var %s interface{}", tempVar))
	g.writeLine(fmt.Sprintf("if %s {", condition))
	g.indentLevel++
	g.writeLine(fmt.Sprintf("%s = %s", tempVar, ifTrue))
	g.indentLevel--
	g.writeLine("} else {")
	g.indentLevel++
	g.writeLine(fmt.Sprintf("%s = %s", tempVar, ifFalse))
	g.indentLevel--
	g.writeLine("}")

	return tempVar
}

// 生成 spawn 表達式（用於並發）
func (g *CodeGenerator) generateSpawnExpression(expr *ast.SpawnExpression) string {
	// spawn 表達式在 Go 中轉換為 goroutine
	callExpr := expr.Call
	function := g.generateExpression(callExpr.Function)

	args := []string{}
	for _, arg := range callExpr.Arguments {
		args = append(args, g.generateExpression(arg))
	}

	argsStr := strings.Join(args, ", ")
	g.writeLine(fmt.Sprintf("go %s(%s)", function, argsStr))

	// 返回一個空的 channel 表示異步執行
	tempVar := g.nextTempVar()
	g.writeLine(fmt.Sprintf("var %s = make(chan interface{})", tempVar))
	return tempVar
}

// 生成 await 表達式
func (g *CodeGenerator) generateAwaitExpression(expr *ast.AwaitExpression) string {
	if len(expr.Futures) == 0 {
		g.addError("Await expression requires at least one future")
		return "nil /* ERROR: No futures to await */"
	}

	// 處理單個 future 的情況
	if len(expr.Futures) == 1 {
		exprCode := g.generateExpression(expr.Futures[0])

		// 在 Go 中使用 channel 接收結果來模擬 await
		tempVar := g.nextTempVar()
		g.writeLine(fmt.Sprintf("var %s = <-%s", tempVar, exprCode))
		return tempVar
	}

	// 處理多個 future 的情況
	tempVar := g.nextTempVar()
	g.writeLine(fmt.Sprintf("var %s []interface{}", tempVar))

	for _, future := range expr.Futures {
		exprCode := g.generateExpression(future)
		resultVar := g.nextTempVar()
		g.writeLine(fmt.Sprintf("var %s = <-%s", resultVar, exprCode))
		g.writeLine(fmt.Sprintf("%s = append(%s, %s)", tempVar, tempVar, resultVar))
	}

	return tempVar
}
