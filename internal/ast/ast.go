package ast

// Program 是 AST 的根節點，代表整個 Glux 程式
type Program struct {
	Statements []Statement
}

// Statement 表示一個語句，實際上可以有多種具體語句型別（如變數宣告、函式定義等）
type Statement interface{}
