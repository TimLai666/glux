package parser

import (
	"fmt"
	"glux/internal/ast"
	"glux/internal/lexer"
	"unicode"
)

// parseVarStatement 解析變量聲明語句
func (p *Parser) parseVarStatement() *ast.VarStatement {
	stmt := &ast.VarStatement{Token: p.currentTok}

	if !p.expectPeek(lexer.TokenIdent) {
		return nil
	}

	stmt.Name = &ast.IdentifierExpression{
		Token: p.currentTok,
		Value: p.currentTok.Literal,
	}

	// 可選的類型聲明
	if p.peekTokenIs(lexer.TokenColon) {
		p.nextToken()
		p.nextToken()
		stmt.Type = p.parseTypeExpression()
	}

	if !p.expectPeek(lexer.TokenDeclare) {
		return nil
	}

	p.nextToken()
	stmt.Value = p.parseExpression(LOWEST)

	if p.peekTokenIs(lexer.TokenSemicolon) {
		p.nextToken()
	}

	return stmt
}

// parseConstStatement 解析常量聲明語句
func (p *Parser) parseConstStatement() *ast.ConstStatement {
	stmt := &ast.ConstStatement{Token: p.currentTok}

	p.nextToken()

	if !p.curTokenIs(lexer.TokenIdent) {
		msg := fmt.Sprintf("expected identifier after const, got %s", lexer.GetTokenName(p.currentTok.Type))
		p.addError(msg)
		return nil
	}

	stmt.Name = &ast.IdentifierExpression{
		Token: p.currentTok,
		Value: p.currentTok.Literal,
	}

	// 可選的類型聲明
	if p.peekTokenIs(lexer.TokenColon) {
		p.nextToken()
		p.nextToken()
		stmt.Type = p.parseTypeExpression()
	}

	if !p.expectPeek(lexer.TokenAssign) {
		return nil
	}

	p.nextToken()
	stmt.Value = p.parseExpression(LOWEST)

	if p.peekTokenIs(lexer.TokenSemicolon) {
		p.nextToken()
	}

	return stmt
}

// parseReturnStatement 解析 return 語句
func (p *Parser) parseReturnStatement() *ast.ReturnStatement {
	stmt := &ast.ReturnStatement{Token: p.currentTok}

	p.nextToken()

	// 如果 return 後沒有跟表達式，則返回 null
	if p.curTokenIs(lexer.TokenSemicolon) || p.curTokenIs(lexer.TokenRBrace) {
		return stmt
	}

	stmt.Value = p.parseExpression(LOWEST)

	if p.peekTokenIs(lexer.TokenSemicolon) {
		p.nextToken()
	}

	return stmt
}

// parseBlockStatement 解析代碼塊
func (p *Parser) parseBlockStatement() *ast.BlockStatement {
	block := &ast.BlockStatement{Token: p.currentTok}
	block.Statements = []ast.Statement{}

	p.nextToken()

	for !p.curTokenIs(lexer.TokenRBrace) && !p.curTokenIs(lexer.TokenEOF) {
		stmt := p.parseStatement()
		if stmt != nil {
			block.Statements = append(block.Statements, stmt)
		}
		p.nextToken()
	}

	return block
}

// parseIfStatement 解析 if 語句
func (p *Parser) parseIfStatement() *ast.IfStatement {
	stmt := &ast.IfStatement{Token: p.currentTok}

	p.nextToken()
	stmt.Condition = p.parseExpression(LOWEST)

	if !p.expectPeek(lexer.TokenLBrace) {
		return nil
	}

	stmt.Consequence = p.parseBlockStatement()

	if p.peekTokenIs(lexer.TokenElse) {
		p.nextToken()

		if !p.expectPeek(lexer.TokenLBrace) {
			return nil
		}

		stmt.Alternative = p.parseBlockStatement()
	}

	return stmt
}

// parseWhileStatement 解析 while 語句
func (p *Parser) parseWhileStatement() *ast.WhileStatement {
	stmt := &ast.WhileStatement{Token: p.currentTok}

	p.nextToken()
	stmt.Condition = p.parseExpression(LOWEST)

	if !p.expectPeek(lexer.TokenLBrace) {
		return nil
	}

	stmt.Body = p.parseBlockStatement()

	return stmt
}

// parseForStatement 解析 for 語句
func (p *Parser) parseForStatement() *ast.ForStatement {
	stmt := &ast.ForStatement{Token: p.currentTok}

	p.nextToken()

	// 解析迭代變量
	if !p.curTokenIs(lexer.TokenIdent) {
		msg := fmt.Sprintf("expected identifier in for statement, got %s", lexer.GetTokenName(p.currentTok.Type))
		p.addError(msg)
		return nil
	}

	stmt.Value = &ast.IdentifierExpression{
		Token: p.currentTok,
		Value: p.currentTok.Literal,
	}

	// 檢查是否有雙迭代變量 (key, value)
	if p.peekTokenIs(lexer.TokenComma) {
		stmt.Index = stmt.Value
		p.nextToken()
		p.nextToken()

		if !p.curTokenIs(lexer.TokenIdent) {
			msg := fmt.Sprintf("expected second identifier after comma in for statement, got %s", lexer.GetTokenName(p.currentTok.Type))
			p.addError(msg)
			return nil
		}

		stmt.Value = &ast.IdentifierExpression{
			Token: p.currentTok,
			Value: p.currentTok.Literal,
		}
	}

	if !p.expectPeek(lexer.TokenIn) {
		return nil
	}

	p.nextToken()
	stmt.Iterable = p.parseExpression(LOWEST)

	if !p.expectPeek(lexer.TokenLBrace) {
		return nil
	}

	stmt.Body = p.parseBlockStatement()

	return stmt
}

// parseFunctionDefinition 解析函數定義
func (p *Parser) parseFunctionDefinition() *ast.FunctionDefinition {
	stmt := &ast.FunctionDefinition{Token: p.currentTok}

	// 檢查是否有接收者 (方法定義)
	if p.peekTokenIs(lexer.TokenLParen) {
		p.nextToken()
		p.nextToken()

		receiver := &ast.FunctionReceiver{
			Name: &ast.IdentifierExpression{
				Token: p.currentTok,
				Value: p.currentTok.Literal,
			},
		}

		// 接收者類型
		if p.peekTokenIs(lexer.TokenIdent) {
			p.nextToken()
			receiver.Type = p.parseTypeExpression()
		}

		if !p.expectPeek(lexer.TokenRParen) {
			return nil
		}

		stmt.Receiver = receiver
	}

	// 函數名稱
	if !p.expectPeek(lexer.TokenIdent) {
		return nil
	}

	stmt.Name = &ast.IdentifierExpression{
		Token: p.currentTok,
		Value: p.currentTok.Literal,
	}

	// 參數列表
	if !p.expectPeek(lexer.TokenLParen) {
		return nil
	}

	stmt.Parameters = p.parseFunctionParameters()

	// 可選的返回類型
	if p.peekTokenIs(lexer.TokenArrow) {
		p.nextToken()
		p.nextToken()
		stmt.ReturnType = p.parseTypeExpression()
	}

	// 函數體
	if !p.expectPeek(lexer.TokenLBrace) {
		return nil
	}

	stmt.Body = p.parseBlockStatement()

	return stmt
}

// parseStructStatement 解析結構體定義
func (p *Parser) parseStructStatement() *ast.StructStatement {
	stmt := &ast.StructStatement{Token: p.currentTok}

	if !p.expectPeek(lexer.TokenIdent) {
		return nil
	}

	stmt.Name = &ast.IdentifierExpression{
		Token: p.currentTok,
		Value: p.currentTok.Literal,
	}

	// 檢查可選的 extends 子句
	if p.peekTokenIs(lexer.TokenExtends) {
		p.nextToken()
		p.nextToken()

		if !p.curTokenIs(lexer.TokenIdent) {
			msg := fmt.Sprintf("expected identifier after extends, got %s", lexer.GetTokenName(p.currentTok.Type))
			p.addError(msg)
			return nil
		}

		stmt.Extends = append(stmt.Extends, &ast.IdentifierExpression{
			Token: p.currentTok,
			Value: p.currentTok.Literal,
		})

		// 多个继承
		for p.peekTokenIs(lexer.TokenComma) {
			p.nextToken()
			p.nextToken()

			if !p.curTokenIs(lexer.TokenIdent) {
				msg := fmt.Sprintf("expected identifier after comma in extends, got %s", lexer.GetTokenName(p.currentTok.Type))
				p.addError(msg)
				return nil
			}

			stmt.Extends = append(stmt.Extends, &ast.IdentifierExpression{
				Token: p.currentTok,
				Value: p.currentTok.Literal,
			})
		}
	}

	if !p.expectPeek(lexer.TokenLBrace) {
		return nil
	}

	// 解析結構體字段
	stmt.Fields = p.parseStructFields()

	if !p.expectPeek(lexer.TokenRBrace) {
		return nil
	}

	return stmt
}

// parseStructFields 解析結構體字段
func (p *Parser) parseStructFields() []*ast.StructField {
	var fields []*ast.StructField

	// 空結構體
	if p.peekTokenIs(lexer.TokenRBrace) {
		return fields
	}

	p.nextToken()

	field := p.parseStructField()
	if field != nil {
		fields = append(fields, field)
	}

	for p.peekTokenIs(lexer.TokenComma) {
		p.nextToken()

		if p.peekTokenIs(lexer.TokenRBrace) {
			break
		}

		p.nextToken()
		field := p.parseStructField()
		if field != nil {
			fields = append(fields, field)
		}
	}

	return fields
}

// parseStructField 解析單個結構體字段
func (p *Parser) parseStructField() *ast.StructField {
	field := &ast.StructField{}

	// 檢查是否有 override 修飾符
	if p.curTokenIs(lexer.TokenOverride) {
		field.IsOverride = true
		p.nextToken()
	}

	if !p.curTokenIs(lexer.TokenIdent) {
		msg := fmt.Sprintf("expected field name, got %s", lexer.GetTokenName(p.currentTok.Type))
		p.addError(msg)
		return nil
	}

	// 檢查首字母是否大寫（公開字段）
	fieldName := p.currentTok.Literal
	if len(fieldName) > 0 && unicode.IsUpper(rune(fieldName[0])) {
		field.IsPublic = true
	}

	field.Name = &ast.IdentifierExpression{
		Token: p.currentTok,
		Value: fieldName,
	}

	// 可選的類型聲明
	if p.peekTokenIs(lexer.TokenColon) {
		p.nextToken()
		p.nextToken()
		field.Type = p.parseTypeExpression()
	}

	// 可選的預設值
	if p.peekTokenIs(lexer.TokenAssign) {
		p.nextToken()
		p.nextToken()
		field.DefaultValue = p.parseExpression(LOWEST)
	}

	return field
}

// parseInterfaceStatement 解析介面定義
func (p *Parser) parseInterfaceStatement() *ast.InterfaceStatement {
	stmt := &ast.InterfaceStatement{Token: p.currentTok}

	if !p.expectPeek(lexer.TokenIdent) {
		return nil
	}

	stmt.Name = &ast.IdentifierExpression{
		Token: p.currentTok,
		Value: p.currentTok.Literal,
	}

	// 檢查可選的 extends 子句
	if p.peekTokenIs(lexer.TokenExtends) {
		p.nextToken()
		p.nextToken()

		if !p.curTokenIs(lexer.TokenIdent) {
			msg := fmt.Sprintf("expected identifier after extends, got %s", lexer.GetTokenName(p.currentTok.Type))
			p.addError(msg)
			return nil
		}

		stmt.Extends = append(stmt.Extends, &ast.IdentifierExpression{
			Token: p.currentTok,
			Value: p.currentTok.Literal,
		})

		// 多个继承
		for p.peekTokenIs(lexer.TokenComma) {
			p.nextToken()
			p.nextToken()

			if !p.curTokenIs(lexer.TokenIdent) {
				msg := fmt.Sprintf("expected identifier after comma in extends, got %s", lexer.GetTokenName(p.currentTok.Type))
				p.addError(msg)
				return nil
			}

			stmt.Extends = append(stmt.Extends, &ast.IdentifierExpression{
				Token: p.currentTok,
				Value: p.currentTok.Literal,
			})
		}
	}

	if !p.expectPeek(lexer.TokenLBrace) {
		return nil
	}

	// 解析介面方法
	stmt.Methods = p.parseInterfaceMethods()

	if !p.expectPeek(lexer.TokenRBrace) {
		return nil
	}

	return stmt
}

// parseInterfaceMethods 解析介面方法列表
func (p *Parser) parseInterfaceMethods() []*ast.InterfaceMethod {
	var methods []*ast.InterfaceMethod

	// 空介面
	if p.peekTokenIs(lexer.TokenRBrace) {
		return methods
	}

	p.nextToken()

	method := p.parseInterfaceMethod()
	if method != nil {
		methods = append(methods, method)
	}

	for !p.peekTokenIs(lexer.TokenRBrace) && !p.peekTokenIs(lexer.TokenEOF) {
		p.nextToken()
		method := p.parseInterfaceMethod()
		if method != nil {
			methods = append(methods, method)
		}
	}

	return methods
}

// parseInterfaceMethod 解析單個介面方法
func (p *Parser) parseInterfaceMethod() *ast.InterfaceMethod {
	if !p.curTokenIs(lexer.TokenIdent) {
		msg := fmt.Sprintf("expected method name, got %s", lexer.GetTokenName(p.currentTok.Type))
		p.addError(msg)
		return nil
	}

	method := &ast.InterfaceMethod{
		Name: &ast.IdentifierExpression{
			Token: p.currentTok,
			Value: p.currentTok.Literal,
		},
	}

	if !p.expectPeek(lexer.TokenLParen) {
		return nil
	}

	method.Parameters = p.parseFunctionParameters()

	// 可選的返回類型
	if p.peekTokenIs(lexer.TokenArrow) {
		p.nextToken()
		p.nextToken()
		method.ReturnType = p.parseTypeExpression()
	}

	return method
}

// parseUnsafeBlockStatement 解析 unsafe 代碼塊
func (p *Parser) parseUnsafeBlockStatement() *ast.UnsafeBlockStatement {
	stmt := &ast.UnsafeBlockStatement{Token: p.currentTok}

	if !p.expectPeek(lexer.TokenLBrace) {
		return nil
	}

	stmt.Body = p.parseBlockStatement()

	return stmt
}

// parseImportStatement 解析 import 語句
func (p *Parser) parseImportStatement() *ast.ImportStatement {
	stmt := &ast.ImportStatement{Token: p.currentTok}

	p.nextToken()

	// 檢查是多項導入還是單文件導入
	if p.curTokenIs(lexer.TokenIdent) {
		// 多項導入
		ident := &ast.IdentifierExpression{
			Token: p.currentTok,
			Value: p.currentTok.Literal,
		}
		stmt.Items = append(stmt.Items, ident)

		// 解析更多導入項
		for p.peekTokenIs(lexer.TokenComma) {
			p.nextToken()
			p.nextToken()

			if !p.curTokenIs(lexer.TokenIdent) {
				msg := fmt.Sprintf("expected identifier after comma in import, got %s", lexer.GetTokenName(p.currentTok.Type))
				p.addError(msg)
				return nil
			}

			ident := &ast.IdentifierExpression{
				Token: p.currentTok,
				Value: p.currentTok.Literal,
			}
			stmt.Items = append(stmt.Items, ident)
		}

		if !p.expectPeek(lexer.TokenFrom) {
			return nil
		}

		p.nextToken()

		if !p.curTokenIs(lexer.TokenString) {
			msg := fmt.Sprintf("expected string after from in import, got %s", lexer.GetTokenName(p.currentTok.Type))
			p.addError(msg)
			return nil
		}

		stmt.Source = &ast.StringLiteral{
			Token: p.currentTok,
			Value: p.currentTok.Literal,
		}
	} else if p.curTokenIs(lexer.TokenString) {
		// 單文件導入
		stmt.Path = &ast.StringLiteral{
			Token: p.currentTok,
			Value: p.currentTok.Literal,
		}
	} else {
		msg := fmt.Sprintf("expected identifier or string in import, got %s", lexer.GetTokenName(p.currentTok.Type))
		p.addError(msg)
		return nil
	}

	if p.peekTokenIs(lexer.TokenSemicolon) {
		p.nextToken()
	}

	return stmt
}
