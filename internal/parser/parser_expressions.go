package parser

import (
	"fmt"
	"glux/internal/ast"
	"glux/internal/lexer"
	"strconv"
	"strings"
)

// parseIdentifier 解析識別符
func (p *Parser) parseIdentifier() ast.Expression {
	return &ast.IdentifierExpression{
		Token: p.currentTok,
		Value: p.currentTok.Literal,
	}
}

// parseNumberLiteral 解析數字字面量
func (p *Parser) parseNumberLiteral() ast.Expression {
	lit := &ast.IntegerLiteral{Token: p.currentTok}

	// 檢查是否為浮點數
	if strings.Contains(p.currentTok.Literal, ".") {
		value, err := strconv.ParseFloat(p.currentTok.Literal, 64)
		if err != nil {
			msg := fmt.Sprintf("could not parse %q as float", p.currentTok.Literal)
			p.addError(msg)
			return nil
		}

		floatLit := &ast.FloatLiteral{Token: p.currentTok, Value: value}
		return floatLit
	}

	// 解析整數
	value, err := strconv.ParseInt(p.currentTok.Literal, 0, 64)
	if err != nil {
		msg := fmt.Sprintf("could not parse %q as integer", p.currentTok.Literal)
		p.addError(msg)
		return nil
	}

	lit.Value = value
	return lit
}

// parseStringLiteral 解析字符串字面量
func (p *Parser) parseStringLiteral() ast.Expression {
	// 檢查是否是插值字符串
	if p.currentTok.Literal != "" && p.currentTok.Literal[0] == '`' {
		return p.parseStringInterpolation()
	}

	return &ast.StringLiteral{
		Token: p.currentTok,
		Value: p.currentTok.Literal,
	}
}

// parseStringInterpolation 解析字符串插值表達式
func (p *Parser) parseStringInterpolation() ast.Expression {
	interpolation := &ast.StringInterpolationExpression{
		Token: p.currentTok,
		Parts: []ast.Expression{},
	}

	// 獲取原始字符串內容，去掉開頭和結尾的反引號
	rawString := p.currentTok.Literal[1 : len(p.currentTok.Literal)-1]

	// 解析字符串中的插值部分
	var textStart, textEnd int
	var insideInterpolation bool
	var interpolationStart int

	for i := 0; i < len(rawString); i++ {
		if !insideInterpolation && i < len(rawString)-1 && rawString[i] == '$' && rawString[i+1] == '{' {
			// 找到插值開始位置
			textEnd = i

			// 添加前面的文本部分
			if textEnd > textStart {
				textPart := &ast.StringLiteral{
					Token: lexer.Token{Type: lexer.TokenString, Literal: rawString[textStart:textEnd]},
					Value: rawString[textStart:textEnd],
				}
				interpolation.Parts = append(interpolation.Parts, textPart)
			}

			insideInterpolation = true
			interpolationStart = i + 2 // 跳過 ${
			i++                        // 跳過 {
		} else if insideInterpolation && rawString[i] == '}' {
			// 找到插值結束位置
			interpolationExpr := rawString[interpolationStart:i]

			// 使用臨時字符串解析插值表達式
			tokens := lexer.Lex(interpolationExpr)
			subParser := New(tokens)
			expr := subParser.parseExpression(LOWEST)

			if expr != nil {
				interpolation.Parts = append(interpolation.Parts, expr)
			}

			insideInterpolation = false
			textStart = i + 1
		}
	}

	// 添加最後一部分文本（如果有）
	if !insideInterpolation && textStart < len(rawString) {
		textPart := &ast.StringLiteral{
			Token: lexer.Token{Type: lexer.TokenString, Literal: rawString[textStart:]},
			Value: rawString[textStart:],
		}
		interpolation.Parts = append(interpolation.Parts, textPart)
	}

	return interpolation
}

// parseBooleanLiteral 解析布爾字面量
func (p *Parser) parseBooleanLiteral() ast.Expression {
	return &ast.BooleanLiteral{
		Token: p.currentTok,
		Value: p.currentTok.Type == lexer.TokenTrue,
	}
}

// parseNullLiteral 解析 null 字面量
func (p *Parser) parseNullLiteral() ast.Expression {
	return &ast.NullLiteral{Token: p.currentTok}
}

// parsePrefixExpression 解析前綴表達式
func (p *Parser) parsePrefixExpression() ast.Expression {
	expression := &ast.PrefixExpression{
		Token:    p.currentTok,
		Operator: p.currentTok.Literal,
	}

	p.nextToken()

	expression.Right = p.parseExpression(PREFIX)

	return expression
}

// parseInfixExpression 解析中綴表達式
func (p *Parser) parseInfixExpression(left ast.Expression) ast.Expression {
	expression := &ast.InfixExpression{
		Token:    p.currentTok,
		Operator: p.currentTok.Literal,
		Left:     left,
	}

	precedence := p.curPrecedence()
	p.nextToken()
	expression.Right = p.parseExpression(precedence)

	return expression
}

// parseGroupedExpression 解析分組表達式 (括號)
func (p *Parser) parseGroupedExpression() ast.Expression {
	p.nextToken()

	exp := p.parseExpression(LOWEST)

	if !p.expectPeek(lexer.TokenRParen) {
		return nil
	}

	return exp
}

// parseConditionalExpression 解析三元運算子表達式
func (p *Parser) parseConditionalExpression(condition ast.Expression) ast.Expression {
	expression := &ast.ConditionalExpression{
		Token:     p.currentTok,
		Condition: condition,
	}

	p.nextToken()
	expression.IfTrue = p.parseExpression(LOWEST)

	if !p.expectPeek(lexer.TokenColon) {
		return nil
	}

	p.nextToken()
	expression.IfFalse = p.parseExpression(CONDITIONAL)

	return expression
}

// parseListLiteral 解析列表字面量
func (p *Parser) parseListLiteral() ast.Expression {
	list := &ast.ListLiteral{Token: p.currentTok}
	list.Elements = p.parseExpressionList(lexer.TokenRBracket)
	return list
}

// parseTupleLiteral 解析元組字面量
func (p *Parser) parseTupleLiteral() ast.Expression {
	tuple := &ast.TupleLiteral{Token: p.currentTok}
	tuple.Elements = p.parseExpressionList(lexer.TokenRParen)
	return tuple
}

// parseMapLiteral 解析映射字面量
func (p *Parser) parseMapLiteral() ast.Expression {
	mapLit := &ast.MapLiteral{
		Token: p.currentTok,
		Pairs: make(map[ast.Expression]ast.Expression),
	}

	// 空映射
	if p.peekTokenIs(lexer.TokenRBrace) {
		p.nextToken()
		return mapLit
	}

	p.nextToken()

	key := p.parseExpression(LOWEST)

	if !p.expectPeek(lexer.TokenColon) {
		return nil
	}

	p.nextToken()
	value := p.parseExpression(LOWEST)

	mapLit.Pairs[key] = value

	for p.peekTokenIs(lexer.TokenComma) {
		p.nextToken()

		if p.peekTokenIs(lexer.TokenRBrace) {
			break
		}

		p.nextToken()
		key := p.parseExpression(LOWEST)

		if !p.expectPeek(lexer.TokenColon) {
			return nil
		}

		p.nextToken()
		value := p.parseExpression(LOWEST)

		mapLit.Pairs[key] = value
	}

	if !p.expectPeek(lexer.TokenRBrace) {
		return nil
	}

	return mapLit
}

// parseExpressionList 解析表達式列表
func (p *Parser) parseExpressionList(end lexer.TokenType) []ast.Expression {
	var list []ast.Expression

	if p.peekTokenIs(end) {
		p.nextToken()
		return list
	}

	p.nextToken()
	list = append(list, p.parseExpression(LOWEST))

	for p.peekTokenIs(lexer.TokenComma) {
		p.nextToken()

		if p.peekTokenIs(end) {
			break
		}

		p.nextToken()
		list = append(list, p.parseExpression(LOWEST))
	}

	if !p.expectPeek(end) {
		return nil
	}

	return list
}

// parseCallExpression 解析函數調用表達式
func (p *Parser) parseCallExpression(function ast.Expression) ast.Expression {
	exp := &ast.CallExpression{
		Token:     p.currentTok,
		Function:  function,
		Arguments: []ast.Expression{},
		NamedArgs: make(map[string]ast.Expression),
	}

	// 解析參數
	if p.peekTokenIs(lexer.TokenRParen) {
		p.nextToken()
		return exp
	}

	p.nextToken()

	// 處理第一個參數
	if p.peekTokenIs(lexer.TokenAssign) && p.curTokenIs(lexer.TokenIdent) {
		// 具名參數
		name := p.currentTok.Literal
		p.nextToken() // 跳過 =
		p.nextToken() // 前往值
		exp.NamedArgs[name] = p.parseExpression(LOWEST)
	} else {
		// 位置參數
		exp.Arguments = append(exp.Arguments, p.parseExpression(LOWEST))
	}

	// 處理剩余參數
	for p.peekTokenIs(lexer.TokenComma) {
		p.nextToken()
		p.nextToken()

		if p.peekTokenIs(lexer.TokenAssign) && p.curTokenIs(lexer.TokenIdent) {
			// 具名參數
			name := p.currentTok.Literal
			p.nextToken() // 跳過 =
			p.nextToken() // 前往值
			exp.NamedArgs[name] = p.parseExpression(LOWEST)
		} else {
			// 位置參數
			exp.Arguments = append(exp.Arguments, p.parseExpression(LOWEST))
		}
	}

	if !p.expectPeek(lexer.TokenRParen) {
		return nil
	}

	return exp
}

// parseIndexExpression 解析索引表達式
func (p *Parser) parseIndexExpression(left ast.Expression) ast.Expression {
	exp := &ast.IndexExpression{
		Token: p.currentTok,
		Left:  left,
	}

	p.nextToken()
	exp.Index = p.parseExpression(LOWEST)

	if !p.expectPeek(lexer.TokenRBracket) {
		return nil
	}

	return exp
}

// parsePropertyExpression 解析屬性訪問表達式
func (p *Parser) parsePropertyExpression(object ast.Expression) ast.Expression {
	exp := &ast.PropertyExpression{
		Token:  p.currentTok,
		Object: object,
	}

	p.nextToken()

	if !p.curTokenIs(lexer.TokenIdent) {
		msg := fmt.Sprintf("expected property name after dot, got %s", lexer.GetTokenName(p.currentTok.Type))
		p.addError(msg)
		return nil
	}

	exp.Property = &ast.IdentifierExpression{
		Token: p.currentTok,
		Value: p.currentTok.Literal,
	}

	return exp
}

// parseFunctionLiteral 解析函數字面量
func (p *Parser) parseFunctionLiteral() ast.Expression {
	lit := &ast.FunctionLiteral{Token: p.currentTok}

	if !p.expectPeek(lexer.TokenLParen) {
		return nil
	}

	lit.Parameters = p.parseFunctionParameters()

	// 解析可選的返回類型
	if p.peekTokenIs(lexer.TokenArrow) {
		p.nextToken()
		p.nextToken()
		lit.ReturnType = p.parseTypeExpression()
	}

	if !p.expectPeek(lexer.TokenLBrace) {
		return nil
	}

	lit.Body = p.parseBlockStatement()

	return lit
}

// parseFunctionParameters 解析函數參數
func (p *Parser) parseFunctionParameters() []*ast.FunctionParameter {
	params := []*ast.FunctionParameter{}

	if p.peekTokenIs(lexer.TokenRParen) {
		p.nextToken()
		return params
	}

	p.nextToken()

	param := &ast.FunctionParameter{
		Name: &ast.IdentifierExpression{
			Token: p.currentTok,
			Value: p.currentTok.Literal,
		},
	}

	// 可選的參數類型
	if p.peekTokenIs(lexer.TokenColon) {
		p.nextToken()
		p.nextToken()
		param.Type = p.parseTypeExpression()
	}

	// 可選的預設值
	if p.peekTokenIs(lexer.TokenAssign) {
		p.nextToken()
		p.nextToken()
		param.DefaultValue = p.parseExpression(LOWEST)
	}

	params = append(params, param)

	for p.peekTokenIs(lexer.TokenComma) {
		p.nextToken()
		p.nextToken()

		param := &ast.FunctionParameter{
			Name: &ast.IdentifierExpression{
				Token: p.currentTok,
				Value: p.currentTok.Literal,
			},
		}

		// 可選的參數類型
		if p.peekTokenIs(lexer.TokenColon) {
			p.nextToken()
			p.nextToken()
			param.Type = p.parseTypeExpression()
		}

		// 可選的預設值
		if p.peekTokenIs(lexer.TokenAssign) {
			p.nextToken()
			p.nextToken()
			param.DefaultValue = p.parseExpression(LOWEST)
		}

		params = append(params, param)
	}

	if !p.expectPeek(lexer.TokenRParen) {
		return nil
	}

	return params
}

// parseTypeExpression 解析類型表達式
func (p *Parser) parseTypeExpression() *ast.TypeExpression {
	// 基本類型
	typeExp := &ast.TypeExpression{
		Token: p.currentTok,
		Name:  p.currentTok.Literal,
	}

	// 檢查是否是泛型類型
	if p.peekTokenIs(lexer.TokenLess) {
		p.nextToken() // 跳過 <
		p.nextToken()

		// 解析泛型參數
		var params []*ast.TypeExpression
		params = append(params, p.parseTypeExpression())

		for p.peekTokenIs(lexer.TokenComma) {
			p.nextToken()
			p.nextToken()
			params = append(params, p.parseTypeExpression())
		}

		if !p.expectPeek(lexer.TokenGreater) {
			return nil
		}

		typeExp.GenericParams = params
	}

	return typeExp
}

// parseStructLiteral 解析結構體字面量
func (p *Parser) parseStructLiteral(typeIdent *ast.IdentifierExpression) ast.Expression {
	lit := &ast.StructLiteral{
		Token:  p.currentTok,
		Type:   typeIdent,
		Fields: make(map[string]ast.Expression),
	}

	if !p.expectPeek(lexer.TokenLBrace) {
		return nil
	}

	// 空結構體
	if p.peekTokenIs(lexer.TokenRBrace) {
		p.nextToken()
		return lit
	}

	p.nextToken()

	// 解析字段賦值
	if !p.curTokenIs(lexer.TokenIdent) {
		msg := fmt.Sprintf("expected field name, got %s", lexer.GetTokenName(p.currentTok.Type))
		p.addError(msg)
		return nil
	}

	name := p.currentTok.Literal

	if !p.expectPeek(lexer.TokenColon) {
		return nil
	}

	p.nextToken()
	value := p.parseExpression(LOWEST)
	lit.Fields[name] = value

	for p.peekTokenIs(lexer.TokenComma) {
		p.nextToken()

		if p.peekTokenIs(lexer.TokenRBrace) {
			break
		}

		p.nextToken()

		if !p.curTokenIs(lexer.TokenIdent) {
			msg := fmt.Sprintf("expected field name, got %s", lexer.GetTokenName(p.currentTok.Type))
			p.addError(msg)
			return nil
		}

		name := p.currentTok.Literal

		if !p.expectPeek(lexer.TokenColon) {
			return nil
		}

		p.nextToken()
		value := p.parseExpression(LOWEST)
		lit.Fields[name] = value
	}

	if !p.expectPeek(lexer.TokenRBrace) {
		return nil
	}

	return lit
}

// parseAssignmentExpression 解析賦值表達式
func (p *Parser) parseAssignmentExpression(left ast.Expression) ast.Expression {
	// 檢查左側是否為合法的賦值目標
	switch left.(type) {
	case *ast.IdentifierExpression, *ast.IndexExpression, *ast.PropertyExpression:
		// 合法的賦值目標
	default:
		msg := "invalid assignment target"
		p.addError(msg)
		return nil
	}

	// 創建一個中綴表達式（而不是賦值語句）
	token := p.currentTok
	p.nextToken() // 跳過 '='
	value := p.parseExpression(LOWEST)

	// 返回中綴表達式
	return &ast.InfixExpression{
		Token:    token,
		Operator: token.Literal,
		Left:     left,
		Right:    value,
	}
}

// parseSpawnExpression 解析 spawn 表達式
func (p *Parser) parseSpawnExpression() ast.Expression {
	expr := &ast.SpawnExpression{Token: p.currentTok}

	p.nextToken()

	// spawn 後面必須是函數調用
	if !p.curTokenIs(lexer.TokenIdent) {
		msg := fmt.Sprintf("expected identifier after spawn, got %s", lexer.GetTokenName(p.currentTok.Type))
		p.addError(msg)
		return nil
	}

	// 構建函數調用表達式
	funcIdent := p.parseIdentifier()

	if !p.expectPeek(lexer.TokenLParen) {
		return nil
	}

	call := p.parseCallExpression(funcIdent).(*ast.CallExpression)
	expr.Call = call

	return expr
}

// parseAwaitExpression 解析 await 表達式
func (p *Parser) parseAwaitExpression() ast.Expression {
	expr := &ast.AwaitExpression{Token: p.currentTok}

	p.nextToken()

	// 解析第一個 future 表達式
	future := p.parseExpression(LOWEST)
	expr.Futures = append(expr.Futures, future)

	// 檢查是否有多個 future
	for p.peekTokenIs(lexer.TokenComma) {
		p.nextToken()
		p.nextToken()
		future := p.parseExpression(LOWEST)
		expr.Futures = append(expr.Futures, future)
	}

	return expr
}
