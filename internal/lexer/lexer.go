package lexer

// Token 定義了詞法分析器所產生的 token 類型
type Token struct {
	Type    string // token 的類型，如 IDENT、NUMBER、STRING 等
	Literal string // token 的原始字面值
}

// Lex 會將傳入的 Glux 原始程式碼轉換成一系列 Token
func Lex(source string) []Token {
	// 這裡僅提供簡單示例，實際需要根據 Glux 語法編寫完整的詞法規則
	tokens := []Token{
		{Type: "IDENT", Literal: "demo"},
	}
	return tokens
}
