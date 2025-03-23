use crate::ast::ASTNode;
use crate::error::{GluxError, glux_error};
use crate::lexer::Token;

pub struct Parser {
    tokens: Vec<Token>,
    pos: usize,
}

impl Parser {
    /// **建立一個新的 Parser**
    pub fn new(tokens: Vec<Token>) -> Self {
        Parser { tokens, pos: 0 }
    }

    /// **取得當前 token**（若超出範圍則回傳 `EOF`）
    fn current_token(&self) -> &Token {
        self.tokens.get(self.pos).unwrap_or(&Token::EOF)
    }

    /// **前進一個 token**
    fn advance(&mut self) {
        if self.pos < self.tokens.len() {
            self.pos += 1;
        }
    }

    /// **解析整個程式（目前只處理單一表達式）**
    pub fn parse(&mut self) -> Result<ASTNode, GluxError> {
        let expr = self.parse_expression()?;
        if let Token::EOF = self.current_token() {
            Ok(expr)
        } else {
            glux_error!(
                ParserError,
                "Unexpected token after expression: {:?}",
                self.current_token()
            )
        }
    }

    /// **解析表達式**（支援 `+`、`-`）
    pub fn parse_expression(&mut self) -> Result<ASTNode, GluxError> {
        let mut node = self.parse_term()?;
        while let Token::Operator(op) = self.current_token() {
            if op == "+" || op == "-" {
                let op_clone = op.clone();
                self.advance();
                let right = self.parse_term()?;
                node = ASTNode::BinaryOp {
                    op: op_clone,
                    left: Box::new(node),
                    right: Box::new(right),
                };
            } else {
                break;
            }
        }
        Ok(node)
    }

    /// **解析項（支援 `*`、`/`、`%`）**
    fn parse_term(&mut self) -> Result<ASTNode, GluxError> {
        let mut node = self.parse_factor()?;
        while let Token::Operator(op) = self.current_token() {
            if op == "*" || op == "/" || op == "%" {
                let op_clone = op.clone();
                self.advance();
                let right = self.parse_factor()?;
                node = ASTNode::BinaryOp {
                    op: op_clone,
                    left: Box::new(node),
                    right: Box::new(right),
                };
            } else {
                break;
            }
        }
        Ok(node)
    }

    /// **解析因子（數字、字串、識別符、括號、一元運算）**
    fn parse_factor(&mut self) -> Result<ASTNode, GluxError> {
        match self.current_token() {
            // **處理數字**
            Token::Number(n) => {
                let num = n.clone();
                self.advance();
                Ok(ASTNode::Number(num))
            }

            // **處理字串**
            Token::StringLiteral(s) => {
                let s_clone = s.clone();
                self.advance();
                Ok(ASTNode::StringLiteral(s_clone))
            }

            // **處理識別符（可能是變數或函數呼叫）**
            Token::Identifier(id) => {
                let id_clone = id.clone();
                self.advance();
                if let Token::Symbol('(') = self.current_token() {
                    self.parse_function_call(id_clone)
                } else {
                    Ok(ASTNode::Identifier(id_clone))
                }
            }

            // **處理括號 `(expr)`**
            Token::Symbol('(') => {
                self.advance();
                let expr = self.parse_expression()?;
                if let Token::Symbol(')') = self.current_token() {
                    self.advance();
                    Ok(expr)
                } else {
                    glux_error!(ParserError, "Expected ')'")
                }
            }

            // **處理一元運算子 `-5`、`+3`**
            Token::Operator(op) if op == "-" || op == "+" => {
                let op_clone = op.clone();
                self.advance();
                let right = self.parse_factor()?;
                Ok(ASTNode::BinaryOp {
                    op: op_clone,
                    left: Box::new(ASTNode::Number("0".to_string())), // `-x` 轉為 `0 - x`
                    right: Box::new(right),
                })
            }

            // **遇到意外的 token**
            token => glux_error!(ParserError, "Unexpected token in expression: {:?}", token),
        }
    }

    /// **解析函數呼叫（識別符後面有 `()`）**
    fn parse_function_call(&mut self, name: String) -> Result<ASTNode, GluxError> {
        self.advance(); // 跳過 `(`

        let mut args = Vec::new();
        if let Token::Symbol(')') = self.current_token() {
            self.advance(); // 跳過 `)`
            return Ok(ASTNode::Identifier(name)); // 暫時不處理函數參數
        }

        glux_error!(ParserError, "函數解析尚未實作")
    }
}

/// **外部解析函式：接收 Token 列表並返回 AST**
pub fn parse(tokens: Vec<Token>) -> Result<ASTNode, GluxError> {
    let mut parser = Parser::new(tokens);
    parser.parse()
}
