package codegen

import (
	"fmt"
	"glux/internal/ast"
	"strings"
)

// 生成變量聲明語句
func (g *CodeGenerator) generateVarStatement(stmt *ast.VarStatement) {
	varName := g.safeVarName(stmt.Name.Value)
	valueCode := g.generateExpression(stmt.Value)

	if stmt.Type != nil {
		// 如果有明確類型聲明
		typeCode := g.goType(stmt.Type.Name)
		g.writeLine(fmt.Sprintf("var %s %s = %s", varName, typeCode, valueCode))
	} else {
		// 使用類型推導
		g.writeLine(fmt.Sprintf("%s := %s", varName, valueCode))
	}
}

// 生成常量聲明語句
func (g *CodeGenerator) generateConstStatement(stmt *ast.ConstStatement) {
	constName := g.safeVarName(stmt.Name.Value)
	valueCode := g.generateExpression(stmt.Value)

	if stmt.Type != nil {
		// 如果有明確類型聲明
		typeCode := g.goType(stmt.Type.Name)
		g.writeLine(fmt.Sprintf("const %s %s = %s", constName, typeCode, valueCode))
	} else {
		// 使用類型推導
		g.writeLine(fmt.Sprintf("const %s = %s", constName, valueCode))
	}
}

// 生成 return 語句
func (g *CodeGenerator) generateReturnStatement(stmt *ast.ReturnStatement) {
	if stmt.Value == nil {
		g.writeLine("return")
	} else {
		valueCode := g.generateExpression(stmt.Value)
		g.writeLine(fmt.Sprintf("return %s", valueCode))
	}
}

// 生成表達式語句
func (g *CodeGenerator) generateExpressionStatement(stmt *ast.ExpressionStatement) {
	if stmt.Expression == nil {
		return
	}

	exprCode := g.generateExpression(stmt.Expression)
	g.writeLine(exprCode)
}

// 生成代碼塊
func (g *CodeGenerator) generateBlockStatement(block *ast.BlockStatement) {
	g.writeLine("{")
	g.indentLevel++

	for _, stmt := range block.Statements {
		g.generateStatement(stmt)
	}

	g.indentLevel--
	g.writeLine("}")
}

// 生成 if 語句
func (g *CodeGenerator) generateIfStatement(stmt *ast.IfStatement) {
	conditionCode := g.generateExpression(stmt.Condition)
	g.writeLine(fmt.Sprintf("if %s {", conditionCode))
	g.indentLevel++

	for _, s := range stmt.Consequence.Statements {
		g.generateStatement(s)
	}

	g.indentLevel--

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
	conditionCode := g.generateExpression(stmt.Condition)
	g.writeLine(fmt.Sprintf("for %s {", conditionCode))
	g.indentLevel++

	for _, s := range stmt.Body.Statements {
		g.generateStatement(s)
	}

	g.indentLevel--
	g.writeLine("}")
}

// 生成 for 語句
func (g *CodeGenerator) generateForStatement(stmt *ast.ForStatement) {
	iterableCode := g.generateExpression(stmt.Iterable)

	if stmt.Index != nil {
		// 帶索引的迭代
		indexName := g.safeVarName(stmt.Index.Value)
		valueName := g.safeVarName(stmt.Value.Value)

		g.writeLine(fmt.Sprintf("for %s, %s := range %s {", indexName, valueName, iterableCode))
	} else {
		// 只有值的迭代
		valueName := g.safeVarName(stmt.Value.Value)

		// range 函數調用需要特殊處理
		if rangeCall, ok := stmt.Iterable.(*ast.CallExpression); ok && rangeCall.Function.(*ast.IdentifierExpression).Value == "range" {
			// 將 range 函數轉換為 Go 的 for 循環
			if len(rangeCall.Arguments) == 1 {
				// range(end)
				endCode := g.generateExpression(rangeCall.Arguments[0])
				g.writeLine(fmt.Sprintf("for %s := 0; %s < %s; %s++ {", valueName, valueName, endCode, valueName))
			} else if len(rangeCall.Arguments) == 2 {
				// range(start, end)
				startCode := g.generateExpression(rangeCall.Arguments[0])
				endCode := g.generateExpression(rangeCall.Arguments[1])
				g.writeLine(fmt.Sprintf("for %s := %s; %s < %s; %s++ {", valueName, startCode, valueName, endCode, valueName))
			} else if len(rangeCall.Arguments) == 3 {
				// range(start, end, step)
				startCode := g.generateExpression(rangeCall.Arguments[0])
				endCode := g.generateExpression(rangeCall.Arguments[1])
				stepCode := g.generateExpression(rangeCall.Arguments[2])
				g.writeLine(fmt.Sprintf("for %s := %s; %s < %s; %s += %s {", valueName, startCode, valueName, endCode, valueName, stepCode))
			} else {
				g.addError("Invalid range call: expected 1-3 arguments")
				g.writeLine(fmt.Sprintf("for %s := range %s { // ERROR: Invalid range call", valueName, iterableCode))
			}
		} else {
			// 一般的迭代
			g.writeLine(fmt.Sprintf("for _, %s := range %s {", valueName, iterableCode))
		}
	}

	g.indentLevel++

	for _, s := range stmt.Body.Statements {
		g.generateStatement(s)
	}

	g.indentLevel--
	g.writeLine("}")
}

// 生成函數定義
func (g *CodeGenerator) generateFunctionDefinition(fn *ast.FunctionDefinition) {
	// 保存當前函數返回類型
	prevReturnType := g.currentFuncReturnType

	fnName := fn.Name.Value

	// 處理參數列表
	params := []string{}
	for _, p := range fn.Parameters {
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
	if fn.ReturnType != nil {
		returnType = g.goType(fn.ReturnType.Name)
	}

	g.currentFuncReturnType = returnType

	// 處理接收者（如果有）
	if fn.Receiver != nil {
		receiverName := g.safeVarName(fn.Receiver.Name.Value)
		receiverType := "interface{}"

		if fn.Receiver.Type != nil {
			receiverType = g.goType(fn.Receiver.Type.Name)
		}

		// 生成方法
		g.writeLine(fmt.Sprintf("func (%s %s) %s(%s) %s {", receiverName, receiverType, fnName, paramsStr, returnType))
	} else {
		// 生成普通函數
		g.writeLine(fmt.Sprintf("func %s(%s) %s {", fnName, paramsStr, returnType))
	}

	// 生成函數體
	g.indentLevel++

	// 處理預設參數
	for _, p := range fn.Parameters {
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

	// 生成函數體內容
	for _, stmt := range fn.Body.Statements {
		g.generateStatement(stmt)
	}

	g.indentLevel--
	g.writeLine("}")

	// 還原之前的函數返回類型
	g.currentFuncReturnType = prevReturnType
}

// 生成結構體定義
func (g *CodeGenerator) generateStructStatement(stmt *ast.StructStatement) {
	structName := stmt.Name.Value

	// 處理繼承
	embedded := []string{}
	for _, ext := range stmt.Extends {
		embedded = append(embedded, ext.Value)
	}

	g.writeLine(fmt.Sprintf("type %s struct {", structName))
	g.indentLevel++

	// 先添加嵌入的結構體
	for _, emb := range embedded {
		g.writeLine(emb)
	}

	// 處理字段
	for _, field := range stmt.Fields {
		fieldName := field.Name.Value

		// 根據首字母大小寫決定可見性（大寫為公開）
		if len(fieldName) > 0 && strings.ToUpper(fieldName[:1]) == fieldName[:1] {
			// 公開字段，保持原樣
		} else {
			// 私有字段，改為小寫
			fieldName = strings.ToLower(fieldName[:1]) + fieldName[1:]
		}

		fieldType := "interface{}"
		if field.Type != nil {
			fieldType = g.goType(field.Type.Name)
		}

		// 輸出字段定義
		if field.DefaultValue != nil {
			// 有預設值的字段需要特殊處理
			// 在 Go 中結構體字段不能直接有預設值，需要在初始化時設置
			g.writeLine(fmt.Sprintf("%s %s // Default: %s", fieldName, fieldType, field.DefaultValue.String()))
		} else {
			g.writeLine(fmt.Sprintf("%s %s", fieldName, fieldType))
		}
	}

	g.indentLevel--
	g.writeLine("}")

	// 如果有預設值的字段，生成一個 New 函數
	hasDefaultFields := false
	for _, field := range stmt.Fields {
		if field.DefaultValue != nil {
			hasDefaultFields = true
			break
		}
	}

	if hasDefaultFields {
		g.writeLine("")
		g.writeLine(fmt.Sprintf("func New%s() *%s {", structName, structName))
		g.indentLevel++
		g.writeLine(fmt.Sprintf("result := &%s{}", structName))

		// 設置預設值
		for _, field := range stmt.Fields {
			if field.DefaultValue != nil {
				fieldName := field.Name.Value

				// 根據首字母大小寫決定可見性
				if len(fieldName) > 0 && strings.ToUpper(fieldName[:1]) == fieldName[:1] {
					// 公開字段，保持原樣
				} else {
					// 私有字段，改為小寫
					fieldName = strings.ToLower(fieldName[:1]) + fieldName[1:]
				}

				defaultValue := g.generateExpression(field.DefaultValue)
				g.writeLine(fmt.Sprintf("result.%s = %s", fieldName, defaultValue))
			}
		}

		g.writeLine("return result")
		g.indentLevel--
		g.writeLine("}")
	}
}

// 生成接口定義
func (g *CodeGenerator) generateInterfaceStatement(stmt *ast.InterfaceStatement) {
	interfaceName := stmt.Name.Value

	g.writeLine(fmt.Sprintf("type %s interface {", interfaceName))
	g.indentLevel++

	// 處理繼承的接口
	for _, ext := range stmt.Extends {
		g.writeLine(fmt.Sprintf("%s", ext.Value))
	}

	// 處理方法
	for _, method := range stmt.Methods {
		methodName := method.Name.Value

		// 處理參數
		params := []string{}
		for _, p := range method.Parameters {
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
		if method.ReturnType != nil {
			returnType = g.goType(method.ReturnType.Name)
		}

		g.writeLine(fmt.Sprintf("%s(%s) %s", methodName, paramsStr, returnType))
	}

	g.indentLevel--
	g.writeLine("}")
}

// 生成 unsafe 代碼塊
func (g *CodeGenerator) generateUnsafeBlockStatement(stmt *ast.UnsafeBlockStatement) {
	// Go 沒有直接對應的 unsafe 區塊概念，但可以在代碼中標記
	g.writeLine("// UNSAFE BLOCK")
	g.generateBlockStatement(stmt.Body)
}

// 生成導入語句
func (g *CodeGenerator) generateImportStatement(stmt *ast.ImportStatement) {
	// 簡單導入，例如：import "math"
	if stmt.Path != nil && stmt.Source == nil {
		path := stmt.Path.Value
		g.imports[path] = ""
		return
	}

	// 從特定文件導入多個項目，例如：import { sin, cos } from "math"
	if stmt.Source != nil && stmt.Items != nil {
		path := stmt.Source.Value
		alias := fmt.Sprintf("_import_%s", strings.Replace(path, "/", "_", -1))
		g.imports[path] = alias

		// 在 Go 中沒有直接等效的選擇性導入，但我們可以創建別名
		for _, item := range stmt.Items {
			itemName := item.Value
			g.writeLine(fmt.Sprintf("var %s = %s.%s", itemName, alias, itemName))
		}
	}
}
