package ast

import (
	"bytes"
	"fmt"
	"glux/internal/lexer"
	"strings"
)

// Node 是所有 AST 節點的基本接口
type Node interface {
	TokenLiteral() string
	String() string
}

// Statement 表示不會產生值的陳述式
type Statement interface {
	Node
	statementNode()
}

// Expression 表示會產生值的表達式
type Expression interface {
	Node
	expressionNode()
}

// Program 是整個程式的根節點
type Program struct {
	Statements []Statement
	MainBlock  *BlockStatement
}

func (p *Program) TokenLiteral() string {
	if len(p.Statements) > 0 {
		return p.Statements[0].TokenLiteral()
	}
	return ""
}

func (p *Program) String() string {
	var out strings.Builder
	for _, s := range p.Statements {
		out.WriteString(s.String())
	}
	if p.MainBlock != nil {
		out.WriteString("\nmain ")
		out.WriteString(p.MainBlock.String())
	}
	return out.String()
}

// IdentifierExpression 表示識別符
type IdentifierExpression struct {
	Token lexer.Token
	Value string
}

func (ie *IdentifierExpression) expressionNode()      {}
func (ie *IdentifierExpression) TokenLiteral() string { return ie.Token.Literal }
func (ie *IdentifierExpression) String() string       { return ie.Value }

// IntegerLiteral 表示整數字面值
type IntegerLiteral struct {
	Token lexer.Token
	Value int64
}

func (il *IntegerLiteral) expressionNode()      {}
func (il *IntegerLiteral) TokenLiteral() string { return il.Token.Literal }
func (il *IntegerLiteral) String() string       { return fmt.Sprintf("%d", il.Value) }

// FloatLiteral 表示浮點數字面值
type FloatLiteral struct {
	Token lexer.Token
	Value float64
}

func (fl *FloatLiteral) expressionNode()      {}
func (fl *FloatLiteral) TokenLiteral() string { return fl.Token.Literal }
func (fl *FloatLiteral) String() string       { return fmt.Sprintf("%g", fl.Value) }

// StringLiteral 表示字符串字面值
type StringLiteral struct {
	Token lexer.Token
	Value string
}

func (sl *StringLiteral) expressionNode()      {}
func (sl *StringLiteral) TokenLiteral() string { return sl.Token.Literal }
func (sl *StringLiteral) String() string       { return fmt.Sprintf("%q", sl.Value) }

// StringInterpolationExpression 表示帶有變量插值的字符串表達式
// 例如: `Hello, ${name}!`
type StringInterpolationExpression struct {
	Token lexer.Token  // 開始標記
	Parts []Expression // 字符串各部分：字面量和插值表達式的混合
}

func (sie *StringInterpolationExpression) expressionNode()      {}
func (sie *StringInterpolationExpression) TokenLiteral() string { return sie.Token.Literal }
func (sie *StringInterpolationExpression) String() string {
	var out bytes.Buffer
	out.WriteString("`")

	for _, part := range sie.Parts {
		if strLit, ok := part.(*StringLiteral); ok {
			out.WriteString(strLit.Value)
		} else {
			out.WriteString("${")
			out.WriteString(part.String())
			out.WriteString("}")
		}
	}

	out.WriteString("`")
	return out.String()
}

// BooleanLiteral 表示布爾字面值
type BooleanLiteral struct {
	Token lexer.Token
	Value bool
}

func (bl *BooleanLiteral) expressionNode()      {}
func (bl *BooleanLiteral) TokenLiteral() string { return bl.Token.Literal }
func (bl *BooleanLiteral) String() string {
	if bl.Value {
		return "true"
	}
	return "false"
}

// NullLiteral 表示空值
type NullLiteral struct {
	Token lexer.Token
}

func (nl *NullLiteral) expressionNode()      {}
func (nl *NullLiteral) TokenLiteral() string { return nl.Token.Literal }
func (nl *NullLiteral) String() string       { return "null" }

// PrefixExpression 表示前綴表達式
type PrefixExpression struct {
	Token    lexer.Token
	Operator string
	Right    Expression
}

func (pe *PrefixExpression) expressionNode()      {}
func (pe *PrefixExpression) TokenLiteral() string { return pe.Token.Literal }
func (pe *PrefixExpression) String() string {
	return fmt.Sprintf("(%s%s)", pe.Operator, pe.Right.String())
}

// InfixExpression 表示中綴表達式
type InfixExpression struct {
	Token    lexer.Token
	Left     Expression
	Operator string
	Right    Expression
}

func (ie *InfixExpression) expressionNode()      {}
func (ie *InfixExpression) TokenLiteral() string { return ie.Token.Literal }
func (ie *InfixExpression) String() string {
	return fmt.Sprintf("(%s %s %s)", ie.Left.String(), ie.Operator, ie.Right.String())
}

// RangeExpression 表示範圍表達式 (用於 for 循環)
type RangeExpression struct {
	Token lexer.Token
	Start Expression
	End   Expression
	Step  Expression
}

func (re *RangeExpression) expressionNode()      {}
func (re *RangeExpression) TokenLiteral() string { return re.Token.Literal }
func (re *RangeExpression) String() string {
	if re.Step != nil {
		return fmt.Sprintf("range(%s, %s, %s)", re.Start.String(), re.End.String(), re.Step.String())
	}
	return fmt.Sprintf("range(%s, %s)", re.Start.String(), re.End.String())
}

// BlockStatement 表示代碼塊
type BlockStatement struct {
	Token      lexer.Token
	Statements []Statement
}

func (bs *BlockStatement) statementNode()       {}
func (bs *BlockStatement) TokenLiteral() string { return bs.Token.Literal }
func (bs *BlockStatement) String() string {
	var out strings.Builder
	out.WriteString("{\n")
	for _, s := range bs.Statements {
		out.WriteString(s.String())
	}
	out.WriteString("}\n")
	return out.String()
}

// VarStatement 表示變量聲明語句
type VarStatement struct {
	Token lexer.Token
	Name  *IdentifierExpression
	Type  *TypeExpression
	Value Expression
}

func (vs *VarStatement) statementNode()       {}
func (vs *VarStatement) TokenLiteral() string { return vs.Token.Literal }
func (vs *VarStatement) String() string {
	var out strings.Builder
	out.WriteString(vs.Name.String())
	if vs.Type != nil {
		out.WriteString(": " + vs.Type.String())
	}
	out.WriteString(" := ")
	if vs.Value != nil {
		out.WriteString(vs.Value.String())
	}
	out.WriteString("\n")
	return out.String()
}

// ConstStatement 表示常量聲明語句
type ConstStatement struct {
	Token lexer.Token
	Name  *IdentifierExpression
	Type  *TypeExpression
	Value Expression
}

func (cs *ConstStatement) statementNode()       {}
func (cs *ConstStatement) TokenLiteral() string { return cs.Token.Literal }
func (cs *ConstStatement) String() string {
	var out strings.Builder
	out.WriteString("const ")
	out.WriteString(cs.Name.String())
	if cs.Type != nil {
		out.WriteString(": " + cs.Type.String())
	}
	out.WriteString(" = ")
	if cs.Value != nil {
		out.WriteString(cs.Value.String())
	}
	out.WriteString("\n")
	return out.String()
}

// AssignmentStatement 表示賦值語句
type AssignmentStatement struct {
	Token lexer.Token
	Left  Expression
	Value Expression
}

func (as *AssignmentStatement) statementNode()       {}
func (as *AssignmentStatement) TokenLiteral() string { return as.Token.Literal }
func (as *AssignmentStatement) String() string {
	return fmt.Sprintf("%s = %s\n", as.Left.String(), as.Value.String())
}

func (as *AssignmentStatement) expressionNode() {}

// ReturnStatement 表示 return 語句
type ReturnStatement struct {
	Token lexer.Token
	Value Expression
}

func (rs *ReturnStatement) statementNode()       {}
func (rs *ReturnStatement) TokenLiteral() string { return rs.Token.Literal }
func (rs *ReturnStatement) String() string {
	var out strings.Builder
	out.WriteString("return ")
	if rs.Value != nil {
		out.WriteString(rs.Value.String())
	}
	out.WriteString("\n")
	return out.String()
}

// ExpressionStatement 表示表達式語句
type ExpressionStatement struct {
	Token      lexer.Token
	Expression Expression
}

func (es *ExpressionStatement) statementNode()       {}
func (es *ExpressionStatement) TokenLiteral() string { return es.Token.Literal }
func (es *ExpressionStatement) String() string {
	if es.Expression != nil {
		return es.Expression.String() + "\n"
	}
	return "\n"
}

// IfStatement 表示 if 語句
type IfStatement struct {
	Token       lexer.Token
	Condition   Expression
	Consequence *BlockStatement
	Alternative *BlockStatement
}

func (is *IfStatement) statementNode()       {}
func (is *IfStatement) TokenLiteral() string { return is.Token.Literal }
func (is *IfStatement) String() string {
	var out strings.Builder
	out.WriteString("if ")
	out.WriteString(is.Condition.String())
	out.WriteString(" ")
	out.WriteString(is.Consequence.String())
	if is.Alternative != nil {
		out.WriteString("else ")
		out.WriteString(is.Alternative.String())
	}
	return out.String()
}

// ConditionalExpression 表示三元運算子表達式
type ConditionalExpression struct {
	Token     lexer.Token
	Condition Expression
	IfTrue    Expression
	IfFalse   Expression
}

func (ce *ConditionalExpression) expressionNode()      {}
func (ce *ConditionalExpression) TokenLiteral() string { return ce.Token.Literal }
func (ce *ConditionalExpression) String() string {
	return fmt.Sprintf("(%s ? %s : %s)", ce.Condition.String(), ce.IfTrue.String(), ce.IfFalse.String())
}

// WhileStatement 表示 while 語句
type WhileStatement struct {
	Token     lexer.Token
	Condition Expression
	Body      *BlockStatement
}

func (ws *WhileStatement) statementNode()       {}
func (ws *WhileStatement) TokenLiteral() string { return ws.Token.Literal }
func (ws *WhileStatement) String() string {
	var out strings.Builder
	out.WriteString("while ")
	out.WriteString(ws.Condition.String())
	out.WriteString(" ")
	out.WriteString(ws.Body.String())
	return out.String()
}

// ForStatement 表示 for 語句
type ForStatement struct {
	Token    lexer.Token
	Index    *IdentifierExpression
	Value    *IdentifierExpression
	Iterable Expression
	Body     *BlockStatement
}

func (fs *ForStatement) statementNode()       {}
func (fs *ForStatement) TokenLiteral() string { return fs.Token.Literal }
func (fs *ForStatement) String() string {
	var out strings.Builder
	out.WriteString("for ")
	if fs.Index != nil && fs.Value != nil {
		out.WriteString(fs.Index.String() + ", " + fs.Value.String())
	} else {
		out.WriteString(fs.Value.String())
	}
	out.WriteString(" in ")
	out.WriteString(fs.Iterable.String())
	out.WriteString(" ")
	out.WriteString(fs.Body.String())
	return out.String()
}

// FunctionParameter 表示函數參數
type FunctionParameter struct {
	Name         *IdentifierExpression
	Type         *TypeExpression
	DefaultValue Expression
}

func (fp *FunctionParameter) String() string {
	var out strings.Builder
	out.WriteString(fp.Name.String())

	if fp.Type != nil {
		out.WriteString(": " + fp.Type.String())
	}

	if fp.DefaultValue != nil {
		out.WriteString(" = " + fp.DefaultValue.String())
	}

	return out.String()
}

// FunctionDefinition 表示函數定義
type FunctionDefinition struct {
	Token      lexer.Token
	Name       *IdentifierExpression
	Parameters []*FunctionParameter
	ReturnType *TypeExpression
	Body       *BlockStatement
	Receiver   *FunctionReceiver // 用於方法定義
}

func (fd *FunctionDefinition) statementNode()       {}
func (fd *FunctionDefinition) TokenLiteral() string { return fd.Token.Literal }
func (fd *FunctionDefinition) String() string {
	var out strings.Builder

	if fd.Receiver != nil {
		out.WriteString("fn (" + fd.Receiver.String() + ") ")
	} else {
		out.WriteString("fn ")
	}

	if fd.Name != nil {
		out.WriteString(fd.Name.String())
	}

	out.WriteString("(")

	params := []string{}
	for _, p := range fd.Parameters {
		params = append(params, p.String())
	}
	out.WriteString(strings.Join(params, ", "))
	out.WriteString(")")

	if fd.ReturnType != nil {
		out.WriteString(" -> ")
		out.WriteString(fd.ReturnType.String())
	}

	out.WriteString(" ")
	out.WriteString(fd.Body.String())

	return out.String()
}

// FunctionReceiver 表示方法的接收者
type FunctionReceiver struct {
	Name *IdentifierExpression
	Type *TypeExpression
}

func (fr *FunctionReceiver) String() string {
	var out strings.Builder
	out.WriteString(fr.Name.String())
	if fr.Type != nil {
		out.WriteString(" " + fr.Type.String())
	}
	return out.String()
}

// CallExpression 表示函數調用
type CallExpression struct {
	Token     lexer.Token
	Function  Expression
	Arguments []Expression
	NamedArgs map[string]Expression
}

func (ce *CallExpression) expressionNode()      {}
func (ce *CallExpression) TokenLiteral() string { return ce.Token.Literal }
func (ce *CallExpression) String() string {
	var out strings.Builder

	out.WriteString(ce.Function.String())
	out.WriteString("(")

	args := []string{}
	for _, a := range ce.Arguments {
		args = append(args, a.String())
	}

	for name, value := range ce.NamedArgs {
		args = append(args, name+"="+value.String())
	}

	out.WriteString(strings.Join(args, ", "))
	out.WriteString(")")

	return out.String()
}

// IndexExpression 表示索引表達式，用於訪問列表、數組、字典等
type IndexExpression struct {
	Token lexer.Token
	Left  Expression
	Index Expression
}

func (ie *IndexExpression) expressionNode()      {}
func (ie *IndexExpression) TokenLiteral() string { return ie.Token.Literal }
func (ie *IndexExpression) String() string {
	return fmt.Sprintf("(%s[%s])", ie.Left.String(), ie.Index.String())
}

// PropertyExpression 表示屬性訪問表達式
type PropertyExpression struct {
	Token    lexer.Token
	Object   Expression
	Property *IdentifierExpression
}

func (pe *PropertyExpression) expressionNode()      {}
func (pe *PropertyExpression) TokenLiteral() string { return pe.Token.Literal }
func (pe *PropertyExpression) String() string {
	return fmt.Sprintf("%s.%s", pe.Object.String(), pe.Property.String())
}

// ListLiteral 表示列表字面量
type ListLiteral struct {
	Token    lexer.Token
	Elements []Expression
}

func (ll *ListLiteral) expressionNode()      {}
func (ll *ListLiteral) TokenLiteral() string { return ll.Token.Literal }
func (ll *ListLiteral) String() string {
	var out strings.Builder

	elements := []string{}
	for _, el := range ll.Elements {
		elements = append(elements, el.String())
	}

	out.WriteString("[")
	out.WriteString(strings.Join(elements, ", "))
	out.WriteString("]")

	return out.String()
}

// TupleLiteral 表示元組字面量
type TupleLiteral struct {
	Token    lexer.Token
	Elements []Expression
}

func (tl *TupleLiteral) expressionNode()      {}
func (tl *TupleLiteral) TokenLiteral() string { return tl.Token.Literal }
func (tl *TupleLiteral) String() string {
	var out strings.Builder

	elements := []string{}
	for _, el := range tl.Elements {
		elements = append(elements, el.String())
	}

	out.WriteString("(")
	out.WriteString(strings.Join(elements, ", "))
	out.WriteString(")")

	return out.String()
}

// MapPair 表示字典中的鍵值對
type MapPair struct {
	Key   Expression
	Value Expression
}

// MapLiteral 表示字典字面量
type MapLiteral struct {
	Token lexer.Token
	Pairs map[Expression]Expression
}

func (ml *MapLiteral) expressionNode()      {}
func (ml *MapLiteral) TokenLiteral() string { return ml.Token.Literal }
func (ml *MapLiteral) String() string {
	var out strings.Builder

	pairs := []string{}
	for key, value := range ml.Pairs {
		pairs = append(pairs, key.String()+": "+value.String())
	}

	out.WriteString("{")
	out.WriteString(strings.Join(pairs, ", "))
	out.WriteString("}")

	return out.String()
}

// StructField 表示結構體的欄位
type StructField struct {
	Name         *IdentifierExpression
	Type         *TypeExpression
	DefaultValue Expression
	IsOverride   bool
	IsPublic     bool
}

func (sf *StructField) String() string {
	var out strings.Builder

	if sf.IsOverride {
		out.WriteString("override ")
	}

	out.WriteString(sf.Name.String())

	if sf.Type != nil {
		out.WriteString(": " + sf.Type.String())
	}

	if sf.DefaultValue != nil {
		out.WriteString(" = " + sf.DefaultValue.String())
	}

	return out.String()
}

// StructStatement 表示結構體定義
type StructStatement struct {
	Token   lexer.Token
	Name    *IdentifierExpression
	Fields  []*StructField
	Extends []*IdentifierExpression
}

func (ss *StructStatement) statementNode()       {}
func (ss *StructStatement) TokenLiteral() string { return ss.Token.Literal }
func (ss *StructStatement) String() string {
	var out strings.Builder

	out.WriteString("struct ")
	out.WriteString(ss.Name.String())

	if len(ss.Extends) > 0 {
		out.WriteString(" extends ")
		extendNames := []string{}
		for _, ext := range ss.Extends {
			extendNames = append(extendNames, ext.String())
		}
		out.WriteString(strings.Join(extendNames, ", "))
	}

	out.WriteString(" {\n")

	for _, field := range ss.Fields {
		out.WriteString("    " + field.String() + ",\n")
	}

	out.WriteString("}\n")

	return out.String()
}

// InterfaceMethod 表示介面中的方法簽名
type InterfaceMethod struct {
	Name       *IdentifierExpression
	Parameters []*FunctionParameter
	ReturnType *TypeExpression
}

func (im *InterfaceMethod) String() string {
	var out strings.Builder

	out.WriteString(im.Name.String())
	out.WriteString("(")

	params := []string{}
	for _, p := range im.Parameters {
		params = append(params, p.String())
	}

	out.WriteString(strings.Join(params, ", "))
	out.WriteString(")")

	if im.ReturnType != nil {
		out.WriteString(" -> ")
		out.WriteString(im.ReturnType.String())
	}

	return out.String()
}

// InterfaceStatement 表示介面定義
type InterfaceStatement struct {
	Token   lexer.Token
	Name    *IdentifierExpression
	Methods []*InterfaceMethod
	Extends []*IdentifierExpression
}

func (is *InterfaceStatement) statementNode()       {}
func (is *InterfaceStatement) TokenLiteral() string { return is.Token.Literal }
func (is *InterfaceStatement) String() string {
	var out strings.Builder

	out.WriteString("interface ")
	out.WriteString(is.Name.String())

	if len(is.Extends) > 0 {
		out.WriteString(" extends ")
		extendNames := []string{}
		for _, ext := range is.Extends {
			extendNames = append(extendNames, ext.String())
		}
		out.WriteString(strings.Join(extendNames, ", "))
	}

	out.WriteString(" {\n")

	for _, method := range is.Methods {
		out.WriteString("    " + method.String() + "\n")
	}

	out.WriteString("}\n")

	return out.String()
}

// TypeExpression 表示類型表達式
type TypeExpression struct {
	Token         lexer.Token
	Name          string
	GenericParams []*TypeExpression
}

func (te *TypeExpression) expressionNode()      {}
func (te *TypeExpression) TokenLiteral() string { return te.Token.Literal }
func (te *TypeExpression) String() string {
	if len(te.GenericParams) == 0 {
		return te.Name
	}

	var out strings.Builder
	out.WriteString(te.Name)
	out.WriteString("<")

	params := []string{}
	for _, p := range te.GenericParams {
		params = append(params, p.String())
	}

	out.WriteString(strings.Join(params, ", "))
	out.WriteString(">")

	return out.String()
}

// SpawnExpression 表示 spawn 表達式
type SpawnExpression struct {
	Token lexer.Token
	Call  *CallExpression
}

func (se *SpawnExpression) expressionNode()      {}
func (se *SpawnExpression) TokenLiteral() string { return se.Token.Literal }
func (se *SpawnExpression) String() string {
	return fmt.Sprintf("spawn %s", se.Call.String())
}

// AwaitExpression 表示 await 表達式
type AwaitExpression struct {
	Token   lexer.Token
	Futures []Expression
}

func (ae *AwaitExpression) expressionNode()      {}
func (ae *AwaitExpression) TokenLiteral() string { return ae.Token.Literal }
func (ae *AwaitExpression) String() string {
	var out strings.Builder
	out.WriteString("await ")

	futures := []string{}
	for _, f := range ae.Futures {
		futures = append(futures, f.String())
	}

	out.WriteString(strings.Join(futures, ", "))

	return out.String()
}

// UnsafeBlockStatement 表示 unsafe 區塊
type UnsafeBlockStatement struct {
	Token lexer.Token
	Body  *BlockStatement
}

func (ubs *UnsafeBlockStatement) statementNode()       {}
func (ubs *UnsafeBlockStatement) TokenLiteral() string { return ubs.Token.Literal }
func (ubs *UnsafeBlockStatement) String() string {
	var out strings.Builder
	out.WriteString("unsafe ")
	out.WriteString(ubs.Body.String())
	return out.String()
}

// MainBlockStatement 表示 main 區塊
type MainBlockStatement struct {
	Token lexer.Token
	Body  *BlockStatement
}

func (mbs *MainBlockStatement) statementNode()       {}
func (mbs *MainBlockStatement) TokenLiteral() string { return mbs.Token.Literal }
func (mbs *MainBlockStatement) String() string {
	var out strings.Builder
	out.WriteString("main ")
	out.WriteString(mbs.Body.String())
	return out.String()
}

// ImportStatement 表示 import 語句
type ImportStatement struct {
	Token  lexer.Token
	Path   *StringLiteral
	Items  []*IdentifierExpression
	Source *StringLiteral
}

func (is *ImportStatement) statementNode()       {}
func (is *ImportStatement) TokenLiteral() string { return is.Token.Literal }
func (is *ImportStatement) String() string {
	var out strings.Builder
	out.WriteString("import ")

	if is.Source != nil {
		items := []string{}
		for _, item := range is.Items {
			items = append(items, item.String())
		}
		out.WriteString(strings.Join(items, ", "))
		out.WriteString(" from ")
		out.WriteString(is.Source.String())
	} else {
		out.WriteString(is.Path.String())
	}

	out.WriteString("\n")
	return out.String()
}

// FunctionLiteral 表示函數字面值（匿名函數）
type FunctionLiteral struct {
	Token      lexer.Token
	Parameters []*FunctionParameter
	ReturnType *TypeExpression
	Body       *BlockStatement
}

func (fl *FunctionLiteral) expressionNode()      {}
func (fl *FunctionLiteral) TokenLiteral() string { return fl.Token.Literal }
func (fl *FunctionLiteral) String() string {
	var out strings.Builder

	out.WriteString("fn(")

	params := []string{}
	for _, p := range fl.Parameters {
		params = append(params, p.String())
	}

	out.WriteString(strings.Join(params, ", "))
	out.WriteString(")")

	if fl.ReturnType != nil {
		out.WriteString(" -> ")
		out.WriteString(fl.ReturnType.String())
	}

	out.WriteString(" ")
	out.WriteString(fl.Body.String())

	return out.String()
}

// StructLiteral 表示結構體實例化表達式
type StructLiteral struct {
	Token  lexer.Token
	Type   *IdentifierExpression
	Fields map[string]Expression
}

func (sl *StructLiteral) expressionNode()      {}
func (sl *StructLiteral) TokenLiteral() string { return sl.Token.Literal }
func (sl *StructLiteral) String() string {
	var out strings.Builder

	out.WriteString(sl.Type.String())
	out.WriteString(" { ")

	fields := []string{}
	for name, value := range sl.Fields {
		fields = append(fields, name+": "+value.String())
	}

	out.WriteString(strings.Join(fields, ", "))
	out.WriteString(" }")

	return out.String()
}

// ContinuousComparisonExpression 表示連續比較表達式，如 0 < x < 8
type ContinuousComparisonExpression struct {
	Token       lexer.Token
	Comparisons []struct {
		Left     Expression
		Operator string
		Right    Expression
	}
}

func (cce *ContinuousComparisonExpression) expressionNode()      {}
func (cce *ContinuousComparisonExpression) TokenLiteral() string { return cce.Token.Literal }
func (cce *ContinuousComparisonExpression) String() string {
	var out strings.Builder

	for i, comp := range cce.Comparisons {
		if i > 0 {
			out.WriteString(" ")
		}
		out.WriteString(comp.Left.String())
		out.WriteString(" " + comp.Operator + " ")
		out.WriteString(comp.Right.String())
	}

	return out.String()
}
