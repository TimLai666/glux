package codegen

import (
	"glux/internal/ast"
)

// Generate 將 AST 轉換成 Go 程式碼，並返回生成的程式碼字串
func Generate(program *ast.Program) (string, error) {
	// 此處僅作簡單示例，實際需根據 AST 遍歷生成對應的 Go 語法
	code := `// 這是由 Glux 編譯器生成的 Go 程式碼範例
package main

func main() {
	println("Hello, Glux!")
}
`
	return code, nil
}
