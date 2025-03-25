package lexer

import (
	"fmt"
	"strings"
	"unicode"
	"unicode/utf8"
)

// TokenType 表示 token 的類型
type TokenType int

// Token 類型常量
const (
	TokenEOF TokenType = iota
	TokenIdent
	TokenNumber
	TokenString
	TokenPlus
	TokenMinus
	TokenMultiply
	TokenDivide
	TokenModulo
	TokenAssign
	TokenDeclare
	TokenEqual
	TokenNotEqual
	TokenLess
	TokenLessEqual
	TokenGreater
	TokenGreaterEqual
	TokenAnd
	TokenOr
	TokenNot
	TokenBitAnd
	TokenBitOr
	TokenBitXor
	TokenBitNot
	TokenLeftShift
	TokenRightShift
	TokenDot
	TokenComma
	TokenColon
	TokenSemicolon
	TokenLParen
	TokenRParen
	TokenLBrace
	TokenRBrace
	TokenLBracket
	TokenRBracket
	TokenArrow
	TokenQuestion
	TokenIf
	TokenElse
	TokenWhile
	TokenFor
	TokenIn
	TokenReturn
	TokenFn
	TokenStruct
	TokenInterface
	TokenExtends
	TokenImport
	TokenFrom
	TokenConst
	TokenTrue
	TokenFalse
	TokenSpawn
	TokenAwait
	TokenUnsafe
	TokenNull
	TokenOverride
)

// 保留字映射
var keywords = map[string]TokenType{
	"and":       TokenAnd,
	"await":     TokenAwait,
	"const":     TokenConst,
	"else":      TokenElse,
	"extends":   TokenExtends,
	"false":     TokenFalse,
	"fn":        TokenFn,
	"for":       TokenFor,
	"from":      TokenFrom,
	"if":        TokenIf,
	"import":    TokenImport,
	"in":        TokenIn,
	"interface": TokenInterface,
	"main":      TokenIdent, // 特殊處理
	"not":       TokenNot,
	"or":        TokenOr,
	"return":    TokenReturn,
	"spawn":     TokenSpawn,
	"struct":    TokenStruct,
	"true":      TokenTrue,
	"unsafe":    TokenUnsafe,
	"while":     TokenWhile,
	"override":  TokenOverride,
	"null":      TokenNull,
}

// Token 表示一個語法標記
type Token struct {
	Type    TokenType
	Literal string
	Line    int
	Column  int
}

// Lexer 處理源代碼的詞法分析
type Lexer struct {
	input        string
	position     int  // 當前位置
	readPosition int  // 下一個讀取位置
	ch           rune // 當前字符
	line         int  // 當前行號
	column       int  // 當前列號
}

// NewLexer 創建一個新的詞法分析器
func NewLexer(input string) *Lexer {
	l := &Lexer{
		input:  input,
		line:   1,
		column: 0,
	}
	l.readChar()
	return l
}

// readChar 讀取下一個字符
func (l *Lexer) readChar() {
	if l.readPosition >= len(l.input) {
		l.ch = 0
	} else {
		var size int
		l.ch, size = utf8.DecodeRuneInString(l.input[l.readPosition:])
		if l.ch == utf8.RuneError {
			l.ch = 0
		}
		l.readPosition += size
	}
	l.position = l.readPosition - 1
	l.column++
	if l.ch == '\n' {
		l.line++
		l.column = 0
	}
}

// peekChar 查看下一個字符但不移動位置
func (l *Lexer) peekChar() rune {
	if l.readPosition >= len(l.input) {
		return 0
	}
	r, _ := utf8.DecodeRuneInString(l.input[l.readPosition:])
	return r
}

// NextToken 返回下一個 token
func (l *Lexer) NextToken() Token {
	var tok Token

	l.skipWhitespace()

	// 記錄當前 token 的行列
	tok.Line = l.line
	tok.Column = l.column

	switch l.ch {
	case '=':
		if l.peekChar() == '=' {
			l.readChar()
			tok = Token{Type: TokenEqual, Literal: "=="}
		} else {
			tok = Token{Type: TokenAssign, Literal: string(l.ch)}
		}
	case '+':
		if l.peekChar() == '=' {
			l.readChar()
			tok = Token{Type: TokenAssign, Literal: "+="}
		} else {
			tok = Token{Type: TokenPlus, Literal: string(l.ch)}
		}
	case '-':
		if l.peekChar() == '=' {
			l.readChar()
			tok = Token{Type: TokenAssign, Literal: "-="}
		} else if l.peekChar() == '>' {
			l.readChar()
			tok = Token{Type: TokenArrow, Literal: "->"}
		} else {
			tok = Token{Type: TokenMinus, Literal: string(l.ch)}
		}
	case '*':
		if l.peekChar() == '=' {
			l.readChar()
			tok = Token{Type: TokenAssign, Literal: "*="}
		} else {
			tok = Token{Type: TokenMultiply, Literal: string(l.ch)}
		}
	case '/':
		if l.peekChar() == '=' {
			l.readChar()
			tok = Token{Type: TokenAssign, Literal: "/="}
		} else if l.peekChar() == '/' {
			// 單行註釋
			l.skipComment()
			return l.NextToken()
		} else if l.peekChar() == '*' {
			// 多行註釋
			l.skipMultilineComment()
			return l.NextToken()
		} else {
			tok = Token{Type: TokenDivide, Literal: string(l.ch)}
		}
	case '%':
		if l.peekChar() == '=' {
			l.readChar()
			tok = Token{Type: TokenAssign, Literal: "%="}
		} else {
			tok = Token{Type: TokenModulo, Literal: string(l.ch)}
		}
	case ':':
		if l.peekChar() == '=' {
			l.readChar()
			tok = Token{Type: TokenDeclare, Literal: ":="}
		} else {
			tok = Token{Type: TokenColon, Literal: string(l.ch)}
		}
	case ';':
		tok = Token{Type: TokenSemicolon, Literal: string(l.ch)}
	case ',':
		tok = Token{Type: TokenComma, Literal: string(l.ch)}
	case '.':
		tok = Token{Type: TokenDot, Literal: string(l.ch)}
	case '(':
		tok = Token{Type: TokenLParen, Literal: string(l.ch)}
	case ')':
		tok = Token{Type: TokenRParen, Literal: string(l.ch)}
	case '{':
		tok = Token{Type: TokenLBrace, Literal: string(l.ch)}
	case '}':
		tok = Token{Type: TokenRBrace, Literal: string(l.ch)}
	case '[':
		tok = Token{Type: TokenLBracket, Literal: string(l.ch)}
	case ']':
		tok = Token{Type: TokenRBracket, Literal: string(l.ch)}
	case '<':
		if l.peekChar() == '=' {
			l.readChar()
			tok = Token{Type: TokenLessEqual, Literal: "<="}
		} else if l.peekChar() == '<' {
			l.readChar()
			tok = Token{Type: TokenLeftShift, Literal: "<<"}
		} else {
			tok = Token{Type: TokenLess, Literal: string(l.ch)}
		}
	case '>':
		if l.peekChar() == '=' {
			l.readChar()
			tok = Token{Type: TokenGreaterEqual, Literal: ">="}
		} else if l.peekChar() == '>' {
			l.readChar()
			tok = Token{Type: TokenRightShift, Literal: ">>"}
		} else {
			tok = Token{Type: TokenGreater, Literal: string(l.ch)}
		}
	case '!':
		if l.peekChar() == '=' {
			l.readChar()
			tok = Token{Type: TokenNotEqual, Literal: "!="}
		} else {
			tok = Token{Type: TokenNot, Literal: string(l.ch)}
		}
	case '&':
		if l.peekChar() == '&' {
			l.readChar()
			tok = Token{Type: TokenAnd, Literal: "&&"}
		} else {
			tok = Token{Type: TokenBitAnd, Literal: string(l.ch)}
		}
	case '|':
		if l.peekChar() == '|' {
			l.readChar()
			tok = Token{Type: TokenOr, Literal: "||"}
		} else {
			tok = Token{Type: TokenBitOr, Literal: string(l.ch)}
		}
	case '^':
		tok = Token{Type: TokenBitXor, Literal: string(l.ch)}
	case '~':
		tok = Token{Type: TokenBitNot, Literal: string(l.ch)}
	case '?':
		tok = Token{Type: TokenQuestion, Literal: string(l.ch)}
	case '"', '\'':
		// 字符串字面量
		quote := l.ch
		tok.Type = TokenString
		tok.Literal = l.readString(quote)
	case '`':
		// 多行字符串
		tok.Type = TokenString
		tok.Literal = l.readRawString()
	case 0:
		tok.Type = TokenEOF
		tok.Literal = ""
	default:
		if unicode.IsLetter(l.ch) || l.ch == '_' {
			// 識別符或關鍵字
			tok.Literal = l.readIdentifier()
			tok.Type = lookupIdent(tok.Literal)
			return tok
		} else if unicode.IsDigit(l.ch) {
			// 數字字面量
			tok = l.readNumber()
			return tok
		} else {
			tok = Token{Type: TokenEOF, Literal: string(l.ch)}
		}
	}

	l.readChar()
	return tok
}

// skipWhitespace 跳過空白字符
func (l *Lexer) skipWhitespace() {
	for unicode.IsSpace(l.ch) {
		l.readChar()
	}
}

// skipComment 跳過單行註釋
func (l *Lexer) skipComment() {
	for l.ch != '\n' && l.ch != 0 {
		l.readChar()
	}
}

// skipMultilineComment 跳過多行註釋
func (l *Lexer) skipMultilineComment() {
	l.readChar() // 跳過 *
	for {
		if l.ch == '*' && l.peekChar() == '/' {
			l.readChar() // 跳過 *
			l.readChar() // 跳過 /
			break
		}
		if l.ch == 0 {
			// 未結束的註釋
			break
		}
		l.readChar()
	}
}

// readIdentifier 讀取識別符
func (l *Lexer) readIdentifier() string {
	position := l.position
	for unicode.IsLetter(l.ch) || unicode.IsDigit(l.ch) || l.ch == '_' {
		l.readChar()
	}
	return l.input[position:l.position]
}

// readNumber 讀取數字字面量
func (l *Lexer) readNumber() Token {
	position := l.position
	isFloat := false

	// 讀取數字部分
	for unicode.IsDigit(l.ch) || l.ch == '_' || l.ch == '.' {
		if l.ch == '.' {
			if isFloat {
				// 第二個小數點，中止
				break
			}
			isFloat = true
		}
		l.readChar()
	}

	literal := l.input[position:l.position]
	// 移除數字分隔符 _
	literal = strings.ReplaceAll(literal, "_", "")

	tok := Token{Literal: literal}
	if isFloat {
		tok.Type = TokenNumber // 浮點數
	} else {
		tok.Type = TokenNumber // 整數
	}

	return tok
}

// readString 讀取字符串字面量
func (l *Lexer) readString(quote rune) string {
	position := l.position + 1 // 跳過引號
	for {
		l.readChar()
		if l.ch == quote || l.ch == 0 {
			break
		}
		// 處理跳脫字符
		if l.ch == '\\' {
			l.readChar() // 跳過反斜線
		}
	}

	if l.position >= len(l.input) {
		return l.input[position:l.position]
	}

	return l.input[position:l.position]
}

// readRawString 讀取原始字符串（使用反引號）
func (l *Lexer) readRawString() string {
	position := l.position + 1 // 跳過反引號
	for {
		l.readChar()
		if l.ch == '`' || l.ch == 0 {
			break
		}
	}

	if l.position >= len(l.input) {
		return l.input[position:l.position]
	}

	return l.input[position:l.position]
}

// lookupIdent 檢查是否為關鍵字
func lookupIdent(ident string) TokenType {
	if tok, ok := keywords[ident]; ok {
		return tok
	}
	return TokenIdent
}

// Lex 對源代碼進行詞法分析，返回全部語法標記
func Lex(input string) []Token {
	l := NewLexer(input)
	var tokens []Token

	for {
		token := l.NextToken()
		tokens = append(tokens, token)
		if token.Type == TokenEOF {
			break
		}
	}

	return tokens
}

// GetTokenName 獲取 token 類型的名稱
func GetTokenName(tt TokenType) string {
	switch tt {
	case TokenEOF:
		return "EOF"
	case TokenIdent:
		return "IDENT"
	case TokenNumber:
		return "NUMBER"
	case TokenString:
		return "STRING"
	case TokenPlus:
		return "+"
	case TokenMinus:
		return "-"
	case TokenMultiply:
		return "*"
	case TokenDivide:
		return "/"
	case TokenModulo:
		return "%"
	case TokenAssign:
		return "="
	case TokenDeclare:
		return ":="
	case TokenEqual:
		return "=="
	case TokenNotEqual:
		return "!="
	case TokenLess:
		return "<"
	case TokenLessEqual:
		return "<="
	case TokenGreater:
		return ">"
	case TokenGreaterEqual:
		return ">="
	case TokenAnd:
		return "AND"
	case TokenOr:
		return "OR"
	case TokenNot:
		return "NOT"
	case TokenBitAnd:
		return "&"
	case TokenBitOr:
		return "|"
	case TokenBitXor:
		return "^"
	case TokenBitNot:
		return "~"
	case TokenLeftShift:
		return "<<"
	case TokenRightShift:
		return ">>"
	case TokenDot:
		return "."
	case TokenComma:
		return ","
	case TokenColon:
		return ":"
	case TokenSemicolon:
		return ";"
	case TokenLParen:
		return "("
	case TokenRParen:
		return ")"
	case TokenLBrace:
		return "{"
	case TokenRBrace:
		return "}"
	case TokenLBracket:
		return "["
	case TokenRBracket:
		return "]"
	case TokenArrow:
		return "->"
	case TokenQuestion:
		return "?"
	case TokenIf:
		return "if"
	case TokenElse:
		return "else"
	case TokenWhile:
		return "while"
	case TokenFor:
		return "for"
	case TokenIn:
		return "in"
	case TokenReturn:
		return "return"
	case TokenFn:
		return "fn"
	case TokenStruct:
		return "struct"
	case TokenInterface:
		return "interface"
	case TokenExtends:
		return "extends"
	case TokenImport:
		return "import"
	case TokenFrom:
		return "from"
	case TokenConst:
		return "const"
	case TokenTrue:
		return "true"
	case TokenFalse:
		return "false"
	case TokenSpawn:
		return "spawn"
	case TokenAwait:
		return "await"
	case TokenUnsafe:
		return "unsafe"
	case TokenOverride:
		return "override"
	case TokenNull:
		return "null"
	default:
		return fmt.Sprintf("UNKNOWN(%d)", tt)
	}
}

// String 返回 Token 的字符串表示
func (t Token) String() string {
	return fmt.Sprintf("Token(%s, '%s')", GetTokenName(t.Type), t.Literal)
}
