package codegen

import (
	"fmt"
	"glux/internal/ast"
	"strings"
)

// CodeGenerator 用於生成 Go 代碼
type CodeGenerator struct {
	imports     map[string]string
	buffer      strings.Builder
	indentLevel int
	errors      []string

	// 記錄目前生成的函數上下文，以便處理 return 語句
	currentFuncReturnType string

	// 用於追蹤生成的臨時變數名
	tempVarCount int
}

// NewCodeGenerator 創建一個新的代碼生成器
func NewCodeGenerator() *CodeGenerator {
	gen := &CodeGenerator{
		imports:     make(map[string]string),
		indentLevel: 0,
		errors:      []string{},
	}

	// 預設導入的包
	gen.imports["fmt"] = ""

	return gen
}

// Generate 將 AST 轉換為 Go 代碼
func Generate(node *ast.Program) (string, error) {
	gen := NewCodeGenerator()
	return gen.generate(node)
}

// generate 是內部方法，實際進行代碼生成
func (g *CodeGenerator) generate(node *ast.Program) (string, error) {
	var codeBuffer strings.Builder
	var mainLevelStatements []ast.Statement
	var otherStatements []ast.Statement

	// 分離頂層表達式語句和其他語句
	for _, stmt := range node.Statements {
		if _, ok := stmt.(*ast.ExpressionStatement); ok {
			mainLevelStatements = append(mainLevelStatements, stmt)
		} else {
			otherStatements = append(otherStatements, stmt)
		}
	}

	// 生成包聲明
	codeBuffer.WriteString("package main\n\n")

	// 處理非表達式的頂層語句（變數聲明、函數定義等）
	for _, stmt := range otherStatements {
		g.generateStatement(stmt)
	}

	// 處理 main 函數
	if node.MainBlock != nil {
		g.writeLine("")
		g.writeLine("func main() {")
		g.indentLevel++

		for _, stmt := range node.MainBlock.Statements {
			g.generateStatement(stmt)
		}

		g.indentLevel--
		g.writeLine("}")
	} else if len(mainLevelStatements) > 0 {
		// 如果有頂層表達式語句，創建main函數包含它們
		g.writeLine("")
		g.writeLine("func main() {")
		g.indentLevel++

		// 將頂層的表達式語句移到main函數中
		for _, stmt := range mainLevelStatements {
			g.generateStatement(stmt)
		}

		g.indentLevel--
		g.writeLine("}")
	}

	// 處理導入語句
	importBlock := g.generateImports()

	// 檢查錯誤
	if len(g.errors) > 0 {
		errorMsg := "Code generation errors:\n"
		for _, err := range g.errors {
			errorMsg += "- " + err + "\n"
		}
		return "", fmt.Errorf("%s", errorMsg)
	}

	// 返回生成的代碼，按正確順序組合
	return codeBuffer.String() + importBlock + g.buffer.String(), nil
}

// 生成導入語句
func (g *CodeGenerator) generateImports() string {
	if len(g.imports) == 0 {
		return ""
	}

	var result strings.Builder
	result.WriteString("import (\n")

	for imp, alias := range g.imports {
		if alias != "" {
			result.WriteString(fmt.Sprintf("\t%s \"%s\"\n", alias, imp))
		} else {
			result.WriteString(fmt.Sprintf("\t\"%s\"\n", imp))
		}
	}

	result.WriteString(")\n\n")
	return result.String()
}

// 生成一行帶有適當縮進的代碼
func (g *CodeGenerator) writeLine(line string) {
	if line == "" {
		g.buffer.WriteString("\n")
		return
	}

	for i := 0; i < g.indentLevel; i++ {
		g.buffer.WriteString("\t")
	}

	g.buffer.WriteString(line)
	g.buffer.WriteString("\n")
}

// 添加錯誤信息
func (g *CodeGenerator) addError(format string, args ...interface{}) {
	g.errors = append(g.errors, fmt.Sprintf(format, args...))
}

// 生成下一個臨時變數名
func (g *CodeGenerator) nextTempVar() string {
	g.tempVarCount++
	return fmt.Sprintf("_temp%d", g.tempVarCount)
}

// 為一個類型生成 Go 語言的類型名稱
func (g *CodeGenerator) goType(typeName string) string {
	switch typeName {
	case "int", "int8", "int16", "int32", "int64", "float32", "float64", "bool", "string":
		return typeName
	case "float":
		return "float32"
	case "list":
		return "[]interface{}"
	case "map":
		return "map[interface{}]interface{}"
	case "any":
		return "interface{}"
	default:
		return typeName
	}
}

// 轉換為 Go 的變數名稱
func (g *CodeGenerator) safeVarName(name string) string {
	// 處理可能與 Go 關鍵字衝突的變數名
	switch name {
	case "type", "func", "range", "map", "chan", "select", "go", "defer", "package", "import", "interface":
		return "glux_" + name
	default:
		return name
	}
}

// 生成語句
func (g *CodeGenerator) generateStatement(stmt ast.Statement) {
	switch s := stmt.(type) {
	case *ast.VarStatement:
		g.generateVarStatement(s)
	case *ast.ConstStatement:
		g.generateConstStatement(s)
	case *ast.ReturnStatement:
		g.generateReturnStatement(s)
	case *ast.ExpressionStatement:
		g.generateExpressionStatement(s)
	case *ast.BlockStatement:
		g.generateBlockStatement(s)
	case *ast.IfStatement:
		g.generateIfStatement(s)
	case *ast.WhileStatement:
		g.generateWhileStatement(s)
	case *ast.ForStatement:
		g.generateForStatement(s)
	case *ast.FunctionDefinition:
		g.generateFunctionDefinition(s)
	case *ast.StructStatement:
		g.generateStructStatement(s)
	case *ast.InterfaceStatement:
		g.generateInterfaceStatement(s)
	case *ast.UnsafeBlockStatement:
		g.generateUnsafeBlockStatement(s)
	case *ast.ImportStatement:
		g.generateImportStatement(s)
	default:
		g.addError("Unknown statement type: %T", stmt)
	}
}

// 生成表達式
func (g *CodeGenerator) generateExpression(expr ast.Expression) string {
	switch e := expr.(type) {
	case *ast.IdentifierExpression:
		return g.generateIdentifierExpression(e)
	case *ast.IntegerLiteral:
		return g.generateIntegerLiteral(e)
	case *ast.FloatLiteral:
		return g.generateFloatLiteral(e)
	case *ast.StringLiteral:
		return g.generateStringLiteral(e)
	case *ast.BooleanLiteral:
		return g.generateBooleanLiteral(e)
	case *ast.NullLiteral:
		return g.generateNullLiteral(e)
	case *ast.PrefixExpression:
		return g.generatePrefixExpression(e)
	case *ast.InfixExpression:
		return g.generateInfixExpression(e)
	case *ast.CallExpression:
		return g.generateCallExpression(e)
	case *ast.IndexExpression:
		return g.generateIndexExpression(e)
	case *ast.PropertyExpression:
		return g.generatePropertyExpression(e)
	case *ast.ListLiteral:
		return g.generateListLiteral(e)
	case *ast.TupleLiteral:
		return g.generateTupleLiteral(e)
	case *ast.MapLiteral:
		return g.generateMapLiteral(e)
	case *ast.FunctionLiteral:
		return g.generateFunctionLiteral(e)
	case *ast.StructLiteral:
		return g.generateStructLiteral(e)
	case *ast.ConditionalExpression:
		return g.generateConditionalExpression(e)
	case *ast.SpawnExpression:
		return g.generateSpawnExpression(e)
	case *ast.AwaitExpression:
		return g.generateAwaitExpression(e)
	default:
		g.addError("Unknown expression type: %T", expr)
		return fmt.Sprintf("/* ERROR: Unknown expression type: %T */", expr)
	}
}
