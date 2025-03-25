package parser

import (
	"fmt"
	"glux/internal/ast"
	"glux/internal/lexer"
)

// 操作優先級常量，從低到高
const (
	_ int = iota
	LOWEST
	ASSIGN      // =
	CONDITIONAL // ? :
	LOGICAL_OR  // or ||
	LOGICAL_AND // and &&
	EQUALS      // == !=
	COMPARE     // < > <= >=
	SUM         // + -
	PRODUCT     // * / %
	PREFIX      // -X !X
	CALL        // myFunction(X)
	INDEX       // array[index]
	DOT         // obj.field
)

var precedences = map[lexer.TokenType]int{
	lexer.TokenEqual:        EQUALS,
	lexer.TokenNotEqual:     EQUALS,
	lexer.TokenLess:         COMPARE,
	lexer.TokenLessEqual:    COMPARE,
	lexer.TokenGreater:      COMPARE,
	lexer.TokenGreaterEqual: COMPARE,
	lexer.TokenPlus:         SUM,
	lexer.TokenMinus:        SUM,
	lexer.TokenMultiply:     PRODUCT,
	lexer.TokenDivide:       PRODUCT,
	lexer.TokenModulo:       PRODUCT,
	lexer.TokenLParen:       CALL,
	lexer.TokenLBracket:     INDEX,
	lexer.TokenDot:          DOT,
	lexer.TokenAnd:          LOGICAL_AND,
	lexer.TokenOr:           LOGICAL_OR,
	lexer.TokenQuestion:     CONDITIONAL,
	lexer.TokenAssign:       ASSIGN,
}

type (
	prefixParseFn func() ast.Expression
	infixParseFn  func(ast.Expression) ast.Expression
)

// Parser 定義了一個語法分析器
type Parser struct {
	tokens     []lexer.Token
	currentPos int
	peekPos    int
	currentTok lexer.Token
	peekTok    lexer.Token
	errors     []string

	prefixParseFns map[lexer.TokenType]prefixParseFn
	infixParseFns  map[lexer.TokenType]infixParseFn
}

// New 創建一個新的語法分析器
func New(tokens []lexer.Token) *Parser {
	p := &Parser{
		tokens:         tokens,
		currentPos:     0,
		errors:         []string{},
		prefixParseFns: make(map[lexer.TokenType]prefixParseFn),
		infixParseFns:  make(map[lexer.TokenType]infixParseFn),
	}

	// 註冊前綴解析函數
	p.registerPrefix(lexer.TokenIdent, p.parseIdentifier)
	p.registerPrefix(lexer.TokenNumber, p.parseNumberLiteral)
	p.registerPrefix(lexer.TokenString, p.parseStringLiteral)
	p.registerPrefix(lexer.TokenTrue, p.parseBooleanLiteral)
	p.registerPrefix(lexer.TokenFalse, p.parseBooleanLiteral)
	p.registerPrefix(lexer.TokenNull, p.parseNullLiteral)
	p.registerPrefix(lexer.TokenLParen, p.parseGroupedExpression)
	p.registerPrefix(lexer.TokenLBracket, p.parseListLiteral)
	p.registerPrefix(lexer.TokenLBrace, p.parseMapLiteral)
	p.registerPrefix(lexer.TokenMinus, p.parsePrefixExpression)
	p.registerPrefix(lexer.TokenNot, p.parsePrefixExpression)
	p.registerPrefix(lexer.TokenBitNot, p.parsePrefixExpression)
	p.registerPrefix(lexer.TokenBitAnd, p.parsePrefixExpression)
	p.registerPrefix(lexer.TokenFn, p.parseFunctionLiteral)
	p.registerPrefix(lexer.TokenSpawn, p.parseSpawnExpression)
	p.registerPrefix(lexer.TokenAwait, p.parseAwaitExpression)

	// 註冊中綴解析函數
	p.registerInfix(lexer.TokenPlus, p.parseInfixExpression)
	p.registerInfix(lexer.TokenMinus, p.parseInfixExpression)
	p.registerInfix(lexer.TokenMultiply, p.parseInfixExpression)
	p.registerInfix(lexer.TokenDivide, p.parseInfixExpression)
	p.registerInfix(lexer.TokenModulo, p.parseInfixExpression)
	p.registerInfix(lexer.TokenEqual, p.parseInfixExpression)
	p.registerInfix(lexer.TokenNotEqual, p.parseInfixExpression)
	p.registerInfix(lexer.TokenLess, p.parseInfixExpression)
	p.registerInfix(lexer.TokenLessEqual, p.parseInfixExpression)
	p.registerInfix(lexer.TokenGreater, p.parseInfixExpression)
	p.registerInfix(lexer.TokenGreaterEqual, p.parseInfixExpression)
	p.registerInfix(lexer.TokenAnd, p.parseInfixExpression)
	p.registerInfix(lexer.TokenOr, p.parseInfixExpression)
	p.registerInfix(lexer.TokenBitAnd, p.parseInfixExpression)
	p.registerInfix(lexer.TokenBitOr, p.parseInfixExpression)
	p.registerInfix(lexer.TokenBitXor, p.parseInfixExpression)
	p.registerInfix(lexer.TokenLParen, p.parseCallExpression)
	p.registerInfix(lexer.TokenLBracket, p.parseIndexExpression)
	p.registerInfix(lexer.TokenDot, p.parsePropertyExpression)
	p.registerInfix(lexer.TokenQuestion, p.parseConditionalExpression)
	p.registerInfix(lexer.TokenAssign, p.parseAssignmentExpression)

	// 讀取前兩個 token，設置 currentTok 和 peekTok
	p.nextToken()
	p.nextToken()

	return p
}

// 註冊前綴解析函數
func (p *Parser) registerPrefix(tokenType lexer.TokenType, fn prefixParseFn) {
	p.prefixParseFns[tokenType] = fn
}

// 註冊中綴解析函數
func (p *Parser) registerInfix(tokenType lexer.TokenType, fn infixParseFn) {
	p.infixParseFns[tokenType] = fn
}

// 獲取錯誤消息
func (p *Parser) Errors() []string {
	return p.errors
}

// 添加錯誤消息
func (p *Parser) addError(msg string) {
	errorMsg := fmt.Sprintf("Error at line %d, column %d: %s",
		p.currentTok.Line, p.currentTok.Column, msg)
	p.errors = append(p.errors, errorMsg)
}

// 前進到下一個 token
func (p *Parser) nextToken() {
	p.currentTok = p.peekTok

	if p.peekPos < len(p.tokens) {
		p.peekTok = p.tokens[p.peekPos]
	} else {
		p.peekTok = lexer.Token{Type: lexer.TokenEOF, Literal: ""}
	}

	p.currentPos = p.peekPos
	p.peekPos++
}

// 檢查當前 token 的類型
func (p *Parser) curTokenIs(t lexer.TokenType) bool {
	return p.currentTok.Type == t
}

// 檢查下一個 token 的類型
func (p *Parser) peekTokenIs(t lexer.TokenType) bool {
	return p.peekTok.Type == t
}

// 期望下一個 token 類型
func (p *Parser) expectPeek(t lexer.TokenType) bool {
	if p.peekTokenIs(t) {
		p.nextToken()
		return true
	}

	p.peekError(t)
	return false
}

// 下一個 token 類型錯誤
func (p *Parser) peekError(t lexer.TokenType) {
	msg := fmt.Sprintf("expected next token to be %s, got %s instead",
		lexer.GetTokenName(t), lexer.GetTokenName(p.peekTok.Type))
	p.addError(msg)
}

// 獲取當前 token 的優先級
func (p *Parser) curPrecedence() int {
	if p, ok := precedences[p.currentTok.Type]; ok {
		return p
	}
	return LOWEST
}

// 獲取下一個 token 的優先級
func (p *Parser) peekPrecedence() int {
	if p, ok := precedences[p.peekTok.Type]; ok {
		return p
	}
	return LOWEST
}

// Parse 解析 token 流，構建 AST
func Parse(tokens []lexer.Token) *ast.Program {
	p := New(tokens)
	return p.ParseProgram()
}

// ParseProgram 解析整個程序
func (p *Parser) ParseProgram() *ast.Program {
	program := &ast.Program{
		Statements: []ast.Statement{},
	}

	for !p.curTokenIs(lexer.TokenEOF) {
		stmt := p.parseStatement()
		if stmt != nil {
			// 檢查是否是main區塊
			if mainFunc, ok := stmt.(*ast.FunctionDefinition); ok && mainFunc != nil &&
				mainFunc.Name != nil && mainFunc.Name.Value == "main" && mainFunc.Receiver == nil {
				program.MainBlock = mainFunc.Body
			} else {
				program.Statements = append(program.Statements, stmt)
			}
		}
		p.nextToken()
	}

	return program
}

// parseStatement 根據當前 token 類型解析不同類型的語句
func (p *Parser) parseStatement() ast.Statement {
	switch p.currentTok.Type {
	case lexer.TokenDeclare:
		return p.parseVarStatement()
	case lexer.TokenConst:
		return p.parseConstStatement()
	case lexer.TokenReturn:
		return p.parseReturnStatement()
	case lexer.TokenIf:
		return p.parseIfStatement()
	case lexer.TokenWhile:
		return p.parseWhileStatement()
	case lexer.TokenFor:
		return p.parseForStatement()
	case lexer.TokenFn:
		return p.parseFunctionDefinition()
	case lexer.TokenStruct:
		return p.parseStructStatement()
	case lexer.TokenInterface:
		return p.parseInterfaceStatement()
	case lexer.TokenUnsafe:
		return p.parseUnsafeBlockStatement()
	case lexer.TokenImport:
		return p.parseImportStatement()
	case lexer.TokenIdent:
		// 特殊處理 main 區塊
		if p.currentTok.Literal == "main" && p.peekTokenIs(lexer.TokenLBrace) {
			return p.parseMainBlockStatement()
		}
		fallthrough
	default:
		return p.parseExpressionStatement()
	}
}

// 目前先實現表達式解析的幾個基本方法，後續再實現具體的語句和表達式解析函數

// parseExpression 解析表達式
func (p *Parser) parseExpression(precedence int) ast.Expression {
	prefix := p.prefixParseFns[p.currentTok.Type]
	if prefix == nil {
		p.addError(fmt.Sprintf("no prefix parse function for %s found", lexer.GetTokenName(p.currentTok.Type)))
		return nil
	}

	leftExp := prefix()

	for !p.peekTokenIs(lexer.TokenSemicolon) && precedence < p.peekPrecedence() {
		infix := p.infixParseFns[p.peekTok.Type]
		if infix == nil {
			return leftExp
		}

		p.nextToken()
		leftExp = infix(leftExp)
	}

	return leftExp
}

// parseExpressionStatement 解析表達式語句
func (p *Parser) parseExpressionStatement() *ast.ExpressionStatement {
	stmt := &ast.ExpressionStatement{Token: p.currentTok}
	stmt.Expression = p.parseExpression(LOWEST)

	if p.peekTokenIs(lexer.TokenSemicolon) {
		p.nextToken()
	}

	return stmt
}
