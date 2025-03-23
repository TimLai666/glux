package codegen

import (
	"glux/internal/ast"
)

// Generate 將 AST 轉換成 Go 程式碼，並返回生成的程式碼字串
func Generate(program *ast.Program) (string, error) {
	// 此處僅作簡單示例，實際需根據 AST 遍歷生成對應的 Go 語法
	code := ""
	imports := []string{}
	// todo
	importPackageStr := ""
	for _, imp := range imports {
		importPackageStr += "\"" + imp + "\"\n"
	}
	fullCode := "package main\nimport(" + importPackageStr + ")\nfunc main(){" + code + "}\n"
	return fullCode, nil
}
