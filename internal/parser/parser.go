package parser

import (
	"glux/internal/ast"
	"glux/internal/lexer"
)

// Parse 會接收 lexer 產生的 token 列表並構建出 AST
func Parse(tokens []lexer.Token) *ast.Program {
	// 這裡僅提供簡單示範，實際解析器應包含錯誤處理與更複雜的語法規則
	program := &ast.Program{}
	return program
}
