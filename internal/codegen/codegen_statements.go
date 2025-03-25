package codegen

import (
	"fmt"
	"glux/internal/ast"
	"strings"
)

// 生成變數宣告語句
func (g *CodeGenerator) generateVarStatement(stmt *ast.VarStatement) {
	name := g.safeVarName(stmt.Name.Value)
	value := g.generateExpression(stmt.Value)

	// 如果有明確的類型，使用該類型
	if stmt.Type != nil {
		typeName := g.goType(stmt.Type.String())
		g.writeLine(fmt.Sprintf("var %s %s = %s", name, typeName, value))
	} else {
		// 否則使用 := 進行自動類型推導
		g.writeLine(fmt.Sprintf("%s := %s", name, value))
	}
}

// 生成常數宣告語句
func (g *CodeGenerator) generateConstStatement(stmt *ast.ConstStatement) {
	name := g.safeVarName(stmt.Name.Value)
	value := g.generateExpression(stmt.Value)

	// 如果有明確的類型，使用該類型
	if stmt.Type != nil {
		typeName := g.goType(stmt.Type.String())
		g.writeLine(fmt.Sprintf("const %s %s = %s", name, typeName, value))
	} else {
		// 否則只使用常數
		g.writeLine(fmt.Sprintf("const %s = %s", name, value))
	}
}

// 生成返回語句
func (g *CodeGenerator) generateReturnStatement(stmt *ast.ReturnStatement) {
	if stmt.Value == nil {
		g.writeLine("return")
		return
	}

	value := g.generateExpression(stmt.Value)
	g.writeLine(fmt.Sprintf("return %s", value))
}

// 生成表達式語句
func (g *CodeGenerator) generateExpressionStatement(stmt *ast.ExpressionStatement) {
	if stmt.Expression == nil {
		return
	}

	expr := g.generateExpression(stmt.Expression)

	// 特殊處理函數調用
	if _, ok := stmt.Expression.(*ast.CallExpression); ok {
		g.writeLine(expr)
		return
	}

	// 某些表達式如賦值表達式不需要單獨一行
	switch stmt.Expression.(type) {
	case *ast.AssignmentStatement, *ast.InfixExpression:
		g.writeLine(expr)
	default:
		// 確保表達式的結果被正確處理，不浪費計算結果
		g.writeLine(fmt.Sprintf("_ = %s", expr))
	}
}

// 生成代碼塊
func (g *CodeGenerator) generateBlockStatement(stmt *ast.BlockStatement) string {
	oldBuffer := g.buffer
	var result strings.Builder
	g.buffer = result

	for _, s := range stmt.Statements {
		g.generateStatement(s)
	}

	blockContent := g.buffer.String()
	g.buffer = oldBuffer

	return blockContent
}

// 生成 if 語句
func (g *CodeGenerator) generateIfStatement(stmt *ast.IfStatement) {
	condition := g.generateExpression(stmt.Condition)

	// if 語句及其主體
	g.writeLine(fmt.Sprintf("if %s {", condition))
	g.indentLevel++

	for _, s := range stmt.Consequence.Statements {
		g.generateStatement(s)
	}

	g.indentLevel--

	// else 部分
	if stmt.Alternative != nil {
		g.writeLine("} else {")
		g.indentLevel++

		for _, s := range stmt.Alternative.Statements {
			g.generateStatement(s)
		}

		g.indentLevel--
	}

	g.writeLine("}")
}

// 生成 while 語句
func (g *CodeGenerator) generateWhileStatement(stmt *ast.WhileStatement) {
	condition := g.generateExpression(stmt.Condition)

	// Go 使用 for 來模擬 while
	g.writeLine(fmt.Sprintf("for %s {", condition))
	g.indentLevel++

	for _, s := range stmt.Body.Statements {
		g.generateStatement(s)
	}

	g.indentLevel--
	g.writeLine("}")
}

// 生成 for 語句
func (g *CodeGenerator) generateForStatement(stmt *ast.ForStatement) {
	// 處理不同類型的迭代
	if rangeExpr, ok := stmt.Iterable.(*ast.RangeExpression); ok {
		// 數字範圍循環
		valueName := g.safeVarName(stmt.Value.Value)
		start := g.generateExpression(rangeExpr.Start)
		end := g.generateExpression(rangeExpr.End)

		// 確定是否有步長
		var stepExpr string
		if rangeExpr.Step != nil {
			stepExpr = g.generateExpression(rangeExpr.Step)
		} else {
			stepExpr = "1"
		}

		// 生成循環
		g.writeLine(fmt.Sprintf("for %s := %s; %s < %s; %s += %s {",
			valueName, start, valueName, end, valueName, stepExpr))
	} else if stmt.Index != nil {
		// 帶索引的迭代（如 for i, v in items）
		indexName := g.safeVarName(stmt.Index.Value)
		valueName := g.safeVarName(stmt.Value.Value)
		iterable := g.generateExpression(stmt.Iterable)

		// 生成循環
		g.writeLine(fmt.Sprintf("for %s, %s := range %s {", indexName, valueName, iterable))
	} else {
		// 簡單迭代（如 for v in items）
		valueName := g.safeVarName(stmt.Value.Value)
		iterableName := g.nextTempVar()
		iterable := g.generateExpression(stmt.Iterable)

		// 先取得迭代物件
		g.writeLine(fmt.Sprintf("%s := %s", iterableName, iterable))
		// 再生成循環
		g.writeLine(fmt.Sprintf("for _, %s := range %s {", valueName, iterableName))
	}

	g.indentLevel++

	for _, s := range stmt.Body.Statements {
		g.generateStatement(s)
	}

	g.indentLevel--
	g.writeLine("}")
}

// 生成函數定義
func (g *CodeGenerator) generateFunctionDefinition(stmt *ast.FunctionDefinition) {
	// 函數名
	funcName := stmt.Name.Value

	// 處理參數
	var paramDefs []string
	for _, param := range stmt.Parameters {
		paramName := g.safeVarName(param.Name.Value)
		paramType := "interface{}"

		if param.Type != nil {
			paramType = g.goType(param.Type.String())
		}

		paramDefs = append(paramDefs, fmt.Sprintf("%s %s", paramName, paramType))
	}

	// 處理返回類型
	returnType := ""
	if stmt.ReturnType != nil {
		returnType = " " + g.goType(stmt.ReturnType.String())
	}

	// 處理方法定義（如果有接收者）
	if stmt.Receiver != nil {
		receiverName := g.safeVarName(stmt.Receiver.Name.Value)
		receiverType := "interface{}"

		if stmt.Receiver.Type != nil {
			receiverType = g.goType(stmt.Receiver.Type.String())
		}

		// 函數簽名
		g.writeLine(fmt.Sprintf("func (%s %s) %s(%s)%s {",
			receiverName, receiverType, funcName, strings.Join(paramDefs, ", "), returnType))
	} else {
		// 函數簽名
		g.writeLine(fmt.Sprintf("func %s(%s)%s {",
			funcName, strings.Join(paramDefs, ", "), returnType))
	}

	// 函數體
	g.indentLevel++
	oldReturnType := g.currentFuncReturnType

	if stmt.ReturnType != nil {
		g.currentFuncReturnType = g.goType(stmt.ReturnType.String())
	} else {
		g.currentFuncReturnType = ""
	}

	for _, s := range stmt.Body.Statements {
		g.generateStatement(s)
	}

	g.currentFuncReturnType = oldReturnType

	g.indentLevel--
	g.writeLine("}")
}

// 生成結構體定義
func (g *CodeGenerator) generateStructStatement(stmt *ast.StructStatement) {
	structName := stmt.Name.Value

	g.writeLine(fmt.Sprintf("type %s struct {", structName))
	g.indentLevel++

	// 處理字段
	for _, field := range stmt.Fields {
		fieldName := field.Name.Value

		// 確保字段名開頭大寫（在 Go 中表示公開）
		if field.IsPublic {
			if len(fieldName) > 0 && fieldName[0] >= 'a' && fieldName[0] <= 'z' {
				fieldName = strings.ToUpper(fieldName[:1]) + fieldName[1:]
			}
		}

		// 字段類型
		fieldType := "interface{}"
		if field.Type != nil {
			fieldType = g.goType(field.Type.String())
		}

		g.writeLine(fmt.Sprintf("%s %s", fieldName, fieldType))
	}

	g.indentLevel--
	g.writeLine("}")

	// 如果有預設值，需要添加構造函數
	hasDefaultValues := false
	for _, field := range stmt.Fields {
		if field.DefaultValue != nil {
			hasDefaultValues = true
			break
		}
	}

	if hasDefaultValues {
		g.writeLine("")
		g.writeLine(fmt.Sprintf("// New%s 創建 %s 的新實例並設置預設值", structName, structName))
		g.writeLine(fmt.Sprintf("func New%s() *%s {", structName, structName))
		g.indentLevel++
		g.writeLine(fmt.Sprintf("instance := &%s{}", structName))

		for _, field := range stmt.Fields {
			if field.DefaultValue != nil {
				fieldName := field.Name.Value
				if field.IsPublic {
					if len(fieldName) > 0 && fieldName[0] >= 'a' && fieldName[0] <= 'z' {
						fieldName = strings.ToUpper(fieldName[:1]) + fieldName[1:]
					}
				}

				defaultValue := g.generateExpression(field.DefaultValue)
				g.writeLine(fmt.Sprintf("instance.%s = %s", fieldName, defaultValue))
			}
		}

		g.writeLine("return instance")
		g.indentLevel--
		g.writeLine("}")
	}
}

// 生成接口定義
func (g *CodeGenerator) generateInterfaceStatement(stmt *ast.InterfaceStatement) {
	interfaceName := stmt.Name.Value

	g.writeLine(fmt.Sprintf("type %s interface {", interfaceName))
	g.indentLevel++

	// 處理方法簽名
	for _, method := range stmt.Methods {
		methodName := method.Name.Value

		// 處理參數
		var paramDefs []string
		for _, param := range method.Parameters {
			paramName := g.safeVarName(param.Name.Value)
			paramType := "interface{}"

			if param.Type != nil {
				paramType = g.goType(param.Type.String())
			}

			paramDefs = append(paramDefs, fmt.Sprintf("%s %s", paramName, paramType))
		}

		// 處理返回類型
		returnType := ""
		if method.ReturnType != nil {
			returnType = " " + g.goType(method.ReturnType.String())
		}

		g.writeLine(fmt.Sprintf("%s(%s)%s", methodName, strings.Join(paramDefs, ", "), returnType))
	}

	g.indentLevel--
	g.writeLine("}")
}

// 生成 unsafe 區塊
func (g *CodeGenerator) generateUnsafeBlockStatement(stmt *ast.UnsafeBlockStatement) {
	g.writeLine("// 註解：以下代碼在 Glux 中使用 unsafe 區塊包裹")
	g.writeLine("{")
	g.indentLevel++

	for _, s := range stmt.Body.Statements {
		g.generateStatement(s)
	}

	g.indentLevel--
	g.writeLine("}")
	g.writeLine("// 註解：unsafe 區塊結束")
}

// 生成導入語句
func (g *CodeGenerator) generateImportStatement(stmt *ast.ImportStatement) {
	if stmt.Source != nil {
		// 具名導入，如 import { a, b } from "模組"
		g.addError("Named imports are not supported in generated Go code")
	} else if stmt.Path != nil {
		// 直接導入，如 import "模組"
		g.imports[stmt.Path.Value] = ""
	}
}
